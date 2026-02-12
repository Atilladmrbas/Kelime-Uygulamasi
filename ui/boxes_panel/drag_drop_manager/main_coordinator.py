"""ANA DRAG-DROP KOORDİNATÖRÜ"""
from PyQt6.QtCore import Qt, QMimeData, QByteArray, QTimer, QPoint
import json
from typing import Optional, Dict, Any, Callable
from PyQt6.QtGui import QDrag

from .base_manager import (
    CardType, DropTarget, DragSource, DragOperation,
    create_drag_pixmap, apply_drag_effect, remove_drag_effect
)
from .waiting_area_manager import WaitingAreaManager
from .memory_box_manager import MemoryBoxManager


class DragDropManager:
    """ANA KOORDİNATÖR - Eski DragDropManager ile aynı interface"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        self.waiting_area_manager = WaitingAreaManager(self)
        self.memory_box_manager = MemoryBoxManager(self)
        
        self.current_operation: Optional[DragOperation] = None
        self.operation_history = []
        self.drop_targets: Dict[Any, DropTarget] = {}
        
        self.on_drag_start_callbacks = []
        self.on_drag_end_callbacks = []
        self.on_drop_success_callbacks = []
        self.on_drop_fail_callbacks = []
    
    def start_drag(self, card_widget, event) -> bool:
        """DRAG İŞLEMİNİ BAŞLAT"""
        source_type = self._get_source_type(card_widget)
        
        if source_type == DragSource.WAITING_AREA:
            return self._start_with_waiting_area_manager(card_widget, event)
        elif source_type == DragSource.MEMORY_BOX_DISPLAYED:
            return self._start_with_memory_box_manager(card_widget, event)
        else:
            return False
    
    def process_drop(self, widget, event, db=None) -> bool:
        """DROP İŞLEMİNİ İŞLE"""
        card_id = self._parse_mime_data(event.mimeData())
        if not card_id:
            return False
        
        target_type = self._identify_drop_target(widget)
        
        if target_type == DropTarget.WAITING_AREA:
            success = self.waiting_area_manager.handle_drop_to_waiting_area(card_id, widget, db)
        elif target_type == DropTarget.MEMORY_BOX:
            success = self.memory_box_manager.handle_drop_to_memory_box(card_id, widget, db)
        else:
            success = False
        
        self._finish_drag_operation(success)
        
        return success
    
    def _create_operation(self):
        """Yeni drag operation oluştur"""
        operation = DragOperation()
        operation.start_time = QTimer().remainingTime()
        return operation
    
    def _get_source_type(self, card_widget) -> DragSource:
        """Kaynak türünü belirle"""
        parent = card_widget.parent()
        while parent:
            if hasattr(parent, '__class__'):
                if 'WaitingAreaWidget' in parent.__class__.__name__:
                    return DragSource.WAITING_AREA
                elif 'MemoryBox' in parent.__class__.__name__:
                    return DragSource.MEMORY_BOX_DISPLAYED
            
            parent = parent.parent()
        
        return DragSource.MEMORY_BOX_DISPLAYED
    
    def _start_with_waiting_area_manager(self, card_widget, event) -> bool:
        """Waiting area manager ile drag başlat"""
        if not self.waiting_area_manager.start_drag_from_waiting_area(card_widget, event):
            return False
        
        mime_data = self._create_mime_data()
        if not mime_data:
            self.current_operation = None
            return False
        
        return self._execute_drag(card_widget, mime_data)
    
    def _start_with_memory_box_manager(self, card_widget, event) -> bool:
        """Memory box manager ile drag başlat"""
        if not self.memory_box_manager.start_drag_from_memory_box(card_widget, event):
            return False
        
        if self.current_operation.card_id and self.current_operation.db:
            try:
                cursor = self.current_operation.db.conn.cursor()
                cursor.execute("SELECT box FROM words WHERE id = ?", (self.current_operation.card_id,))
                result = cursor.fetchone()
                if result:
                    self.current_operation.original_box_id = result[0]
            except Exception:
                pass
        
        mime_data = self._create_mime_data()
        if not mime_data:
            self.current_operation = None
            return False
        
        return self._execute_drag(card_widget, mime_data)
    
    def _execute_drag(self, card_widget, mime_data) -> bool:
        """DRAG BAŞLAT"""
        from PyQt6.QtWidgets import QApplication
        
        drag = QDrag(card_widget)
        drag.setMimeData(mime_data)
        
        pixmap = create_drag_pixmap(card_widget)
        if pixmap and not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        apply_drag_effect(card_widget)
        self._call_drag_start_callbacks()
        
        try:
            result = drag.exec(Qt.DropAction.MoveAction)
            
            if self.current_operation and self.current_operation.card_widget:
                remove_drag_effect(self.current_operation.card_widget)
            
            self._finish_drag_operation(result == Qt.DropAction.MoveAction)
            self.cleanup_all_memory_box_borders()
            
            return result == Qt.DropAction.MoveAction
            
        except Exception:
            if self.current_operation and self.current_operation.card_widget:
                remove_drag_effect(self.current_operation.card_widget)
            
            self.cleanup_all_memory_box_borders()
            self.current_operation = None
            
            return False
    
    def _create_mime_data(self) -> Optional[QMimeData]:
        """MIME data oluştur"""
        if not self.current_operation:
            return None
        
        mime_data = QMimeData()
        
        drag_data = {
            'operation_id': id(self.current_operation),
            'card_id': self.current_operation.card_id,
            'card_type': self.current_operation.card_type.value,
            'source_type': self.current_operation.source_type.value if self.current_operation.source_type else None,
            'original_box_id': self.current_operation.original_box_id,
            'requires_cleanup': True
        }
        
        mime_data.setData(
            "application/x-flashcard-operation",
            QByteArray(json.dumps(drag_data).encode())
        )
        
        mime_data.setText(f"card:{self.current_operation.card_id}")
        
        return mime_data
    
    def _parse_mime_data(self, mime_data) -> Optional[int]:
        """MIME data'dan kart ID'sini parse et"""
        try:
            if mime_data.hasFormat("application/x-flashcard-operation"):
                data = mime_data.data("application/x-flashcard-operation")
                operation_data = json.loads(data.data().decode())
                return operation_data.get('card_id')
            
            text = mime_data.text()
            if text.startswith("card:"):
                return int(text.split(":")[1])
            
        except Exception:
            pass
        
        return None
    
    def _identify_drop_target(self, widget) -> DropTarget:
        """Drop target'ı tanımla"""
        for target_widget, target_type in self.drop_targets.items():
            if widget == target_widget or self._is_child_of(widget, target_widget):
                return target_type
        
        widget_class = widget.__class__.__name__
        
        if 'WaitingAreaWidget' in widget_class:
            return DropTarget.WAITING_AREA
        elif 'MemoryBox' in widget_class:
            return DropTarget.MEMORY_BOX
        elif 'BoxDetailContent' in widget_class:
            return DropTarget.BOX_DETAIL
        
        return DropTarget.OTHER
    
    def _is_child_of(self, child, parent) -> bool:
        """Child, parent'ın alt öğesi mi?""" 
        current = child
        while current:
            if current == parent:
                return True
            current = current.parent()
        return False
    
    def _finish_drag_operation(self, success: bool):
        """Drag operasyonunu sonlandır"""
        if not self.current_operation:
            return
        
        self.current_operation.end_time = QTimer().remainingTime()
        self.current_operation.success = success
        
        if success:
            self._call_drop_success_callbacks()
        else:
            self._call_drop_fail_callbacks()
        
        self.operation_history.append(self.current_operation.to_dict())
        
        if len(self.operation_history) > 50:
            self.operation_history.pop(0)
        
        self.current_operation = None
    
    def cleanup_all_memory_box_borders(self):
        """Tüm MemoryBox border'larını temizle"""
        self.waiting_area_manager.cleanup_all_memory_box_borders()
    
    def register_drop_target(self, widget, target_type: DropTarget):
        """Widget'ı drop target olarak kaydet"""
        self.drop_targets[widget] = target_type
    
    def unregister_drop_target(self, widget):
        """Widget'ı drop target'tan çıkar"""
        if widget in self.drop_targets:
            del self.drop_targets[widget]
    
    def add_drag_start_callback(self, callback: Callable):
        """Drag başlangıcı callback'i ekle"""
        self.on_drag_start_callbacks.append(callback)
    
    def add_drop_success_callback(self, callback: Callable):
        """Başarılı drop callback'i ekle"""
        self.on_drop_success_callbacks.append(callback)
    
    def _call_drag_start_callbacks(self):
        for callback in self.on_drag_start_callbacks:
            try:
                callback(self.current_operation)
            except:
                pass
    
    def _call_drop_success_callbacks(self):
        for callback in self.on_drop_success_callbacks:
            try:
                callback(self.current_operation)
            except:
                pass
    
    def _call_drop_fail_callbacks(self):
        for callback in self.on_drop_fail_callbacks:
            try:
                callback(self.current_operation)
            except:
                pass