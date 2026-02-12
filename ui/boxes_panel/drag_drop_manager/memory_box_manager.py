"""SADECE MEMORY BOX DRAG-DROP İŞLEMLERİ"""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from .base_manager import (
    DropTarget, DragSource, CardType,
    remove_drag_effect
)


class MemoryBoxManager:
    """Memory box özel drag-drop yöneticisi"""
    
    def __init__(self, main_manager):
        self.main_manager = main_manager
    
    def start_drag_from_memory_box(self, card_widget, event) -> bool:
        """Memory box'tan çekilmiş kartı sürükle"""
        self.main_manager.current_operation = self.main_manager._create_operation()
        self.main_manager.current_operation.card_widget = card_widget
        self.main_manager.current_operation.source_type = DragSource.MEMORY_BOX_DISPLAYED
        
        if not self._extract_card_info(card_widget):
            self.main_manager.current_operation = None
            return False
        
        return True
    
    def handle_drop_to_memory_box(self, card_id, widget, db) -> bool:
        """Kartı memory box'a geri at"""
        memory_box = self._find_memory_box(widget)
        if not memory_box:
            return False
        
        if db:
            try:
                cursor = db.conn.cursor()
                cursor.execute("SELECT box, is_copy, original_card_id FROM words WHERE id = ?", (card_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                current_box, is_copy, original_card_id = result
                
                try:
                    cursor.execute("UPDATE words SET box = ? WHERE id = ?", (memory_box.box_id, card_id))
                    cursor.execute("UPDATE words SET is_drawn = 0 WHERE id = ?", (card_id,))
                    
                    if is_copy == 1 and original_card_id:
                        cursor.execute("""
                            UPDATE drawn_cards 
                            SET is_active = 0 
                            WHERE copy_card_id = ? AND is_active = 1
                        """, (card_id,))
                        
                        cursor.execute("""
                            INSERT INTO drawn_cards (original_card_id, copy_card_id, box_id, is_active)
                            VALUES (?, ?, ?, 1)
                        """, (original_card_id, card_id, memory_box.box_id))
                    
                    db.conn.commit()
                    
                except Exception:
                    db.conn.rollback()
                    return False
                
                if self.main_manager.current_operation and self.main_manager.current_operation.card_widget:
                    card_widget = self.main_manager.current_operation.card_widget
                    self._immediately_remove_card_widget(card_widget)
                
                QTimer.singleShot(10, memory_box.update_card_count)
                
                if current_box and current_box != memory_box.box_id:
                    self._update_other_box_count(current_box, db)
                
                boxes_design = self._find_boxes_design(memory_box)
                if boxes_design and hasattr(boxes_design, 'remove_drawn_card'):
                    boxes_design.remove_drawn_card(card_id)
                
                if (self.main_manager.current_operation and 
                    self.main_manager.current_operation.source_type == DragSource.WAITING_AREA and
                    self.main_manager.current_operation.source_widget and 
                    hasattr(self.main_manager.current_operation.source_widget, '_remove_card_by_id')):
                    
                    self.main_manager.current_operation.source_widget._remove_card_by_id(card_id, emit_signal=False)
                
                self.cleanup_all_memory_box_borders()
                
                return True
                
            except Exception:
                self.cleanup_all_memory_box_borders()
                return False
        
        return False
    
    def _extract_card_info(self, card_widget) -> bool:
        """Kart bilgilerini çıkar"""
        if not hasattr(card_widget, 'card_id'):
            return False
        
        self.main_manager.current_operation.card_id = card_widget.card_id
        self.main_manager.current_operation.card_type = CardType.COPY
        
        return True
    
    def _find_memory_box(self, widget):
        """Widget'tan memory box bul"""
        current = widget
        while current:
            if hasattr(current, '__class__') and 'MemoryBox' in current.__class__.__name__:
                return current
            current = current.parent()
        return None
    
    def _find_boxes_design(self, widget):
        """Widget'tan BoxesDesign instance'ını bul"""
        parent = widget.parent()
        while parent:
            if hasattr(parent, '__class__') and 'BoxesDesign' in parent.__class__.__name__:
                return parent
            parent = parent.parent()
        return None
    
    def _immediately_remove_card_widget(self, card_widget):
        """Kart widget'ını HEMEN ve GÜVENLİ bir şekilde kaldır"""
        try:
            remove_drag_effect(card_widget)
            
            parent = card_widget.parent()
            if parent and hasattr(parent, 'layout'):
                layout = parent.layout()
                if layout:
                    layout.removeWidget(card_widget)
            
            card_widget.hide()
            card_widget.setParent(None)
            card_widget.deleteLater()
            
        except Exception:
            pass
    
    def _update_other_box_count(self, box_id, db):
        """Diğer kutunun sayacını güncelle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'design') and hasattr(widget.design, 'update_all_counts'):
                    QTimer.singleShot(100, widget.design.update_all_counts)
                    break
                elif hasattr(widget, 'update_all_counts'):
                    QTimer.singleShot(100, widget.update_all_counts)
                    break
                    
        except Exception:
            pass
    
    def cleanup_all_memory_box_borders(self):
        """Tüm MemoryBox widget'larının border'larını temizle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                    try:
                        if hasattr(widget, '_force_normal_style'):
                            widget._force_normal_style()
                        elif hasattr(widget, '_remove_drag_over_style'):
                            widget._remove_drag_over_style()
                        
                        if hasattr(widget, '_is_drag_over'):
                            widget._is_drag_over = False
                        
                    except Exception:
                        pass
            
        except Exception:
            pass