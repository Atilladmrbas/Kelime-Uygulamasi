"""SADECE WAITING AREA İÇİ DRAG-DROP İŞLEMLERİ"""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from .base_manager import DropTarget, DragSource, CardType
import traceback


class WaitingAreaManager:
    """Waiting area özel drag-drop yöneticisi"""
    
    def __init__(self, main_manager):
        self.main_manager = main_manager
    
    def start_drag_from_waiting_area(self, card_widget, event) -> bool:
        """Waiting area'dan drag başlat"""
        self.main_manager.current_operation = self.main_manager._create_operation()
        self.main_manager.current_operation.card_widget = card_widget
        self.main_manager.current_operation.source_type = DragSource.WAITING_AREA
        
        self._extract_source_waiting_area(card_widget)
        
        if not self._extract_card_info(card_widget):
            self.main_manager.current_operation = None
            return False
        
        return True
    
    def handle_drop_to_waiting_area(self, card_id, widget, db) -> bool:
        """Waiting area'ya drop işle"""
        waiting_area = self._find_waiting_area(widget)
        if not waiting_area:
            return False
        
        # ✅ YENİ KONTROL: Eğer kart zaten bu waiting area'daysa drop'u engelle
        if hasattr(waiting_area, 'cards') and card_id in waiting_area.cards:
            print(f"⚠️ Kart {card_id} zaten bu waiting area'da")
            self._cancel_drag_operation()
            return False
        
        # EĞER KART ZATEN BAŞKA BİR WAITING AREA'DAYSA, ÖNCE ORAYDAN KALDIR
        self._remove_card_from_other_waiting_areas(card_id, waiting_area)
        
        # YENİ KONTROL: Eğer kart aynı waiting area içinde farklı pozisyona taşınıyorsa engelle
        source_widget = None
        if (self.main_manager.current_operation and 
            self.main_manager.current_operation.source_widget):
            source_widget = self.main_manager.current_operation.source_widget
            
        # Eğer source ve target aynı waiting area ise (kart kendi içinde taşınıyorsa)
        if source_widget and source_widget == waiting_area:
            print(f"⚠️ Kart {card_id} aynı waiting area içinde taşınıyor - engelle")
            self._cancel_drag_operation()
            return False
        
        source_removed = False
        if (source_widget and 
            hasattr(source_widget, '_remove_card_by_id') and
            source_widget != waiting_area):
            
            try:
                source_widget._remove_card_by_id(card_id, emit_signal=False)
                source_removed = True
            except Exception:
                pass
        
        # ESKİ KART WIDGET'INI TAMAMEN SİL
        self._cleanup_old_card_widget(card_id)
        
        if hasattr(waiting_area, '_add_dragged_card'):
            try:
                # YENİ KART OLUŞTUR VE EKLE
                result = waiting_area._add_dragged_card(card_id, source_widget)
                
                if result:
                    if db:
                        try:
                            cursor = db.conn.cursor()
                            cursor.execute("UPDATE words SET box = NULL WHERE id = ?", (card_id,))
                            db.conn.commit()
                        except Exception:
                            pass
                    
                    if (self.main_manager.current_operation and 
                        self.main_manager.current_operation.source_type == DragSource.MEMORY_BOX_DISPLAYED):
                        
                        boxes_design = self._find_boxes_design(waiting_area)
                        if boxes_design and hasattr(boxes_design, 'remove_drawn_card'):
                            boxes_design.remove_drawn_card(card_id)
                    
                    self.cleanup_all_memory_box_borders()
                    
                    QTimer.singleShot(50, lambda: self._update_waiting_area_ui(waiting_area))
                    
                    return True
                else:
                    # Kart eklenemediyse, eski source'a geri dön
                    if source_removed and source_widget and source_widget != waiting_area:
                        try:
                            source_widget._add_dragged_card(card_id)
                        except Exception:
                            pass
                    
                    self._cancel_drag_operation()
                    return False
                    
            except Exception:
                # Hata durumunda da eski source'a geri dön
                if source_removed and source_widget and source_widget != waiting_area:
                    try:
                        source_widget._add_dragged_card(card_id)
                    except Exception:
                        pass
                
                self._cancel_drag_operation()
                return False
        
        # Eğer hiçbir koşul sağlanmazsa, eski source'a geri dön
        if source_removed and source_widget and source_widget != waiting_area:
            try:
                source_widget._add_dragged_card(card_id)
            except Exception:
                pass
        
        self._cancel_drag_operation()
        return False

    def _cancel_drag_operation(self):
        """Drag operasyonunu iptal et ve görsel efektleri temizle"""
        if self.main_manager.current_operation and self.main_manager.current_operation.card_widget:
            card_widget = self.main_manager.current_operation.card_widget
            
            # Drag efektini kaldır
            from .base_manager import remove_drag_effect
            remove_drag_effect(card_widget)
            
            # Widget'ı tekrar görünür yap
            card_widget.show()
            card_widget.setWindowOpacity(1.0)
            
            # Eğer widget'ın bir parent'ı varsa, onun layout'unda kalmasını sağla
            if card_widget.parent():
                card_widget.raise_()
                card_widget.update()
        
        # Operasyonu temizle
        self.main_manager.current_operation = None

    def _remove_card_from_other_waiting_areas(self, card_id, current_waiting_area):
        """Kartı diğer waiting area'lardan kaldır"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.allWidgets():
                if (hasattr(widget, '__class__') and 
                    'WaitingAreaWidget' in widget.__class__.__name__ and 
                    widget != current_waiting_area):
                    
                    if hasattr(widget, 'cards') and card_id in widget.cards:
                        if hasattr(widget, '_remove_card_by_id'):
                            widget._remove_card_by_id(card_id, emit_signal=False)
                        
        except Exception:
            pass

    def _cleanup_old_card_widget(self, card_id):
        """Eski kart widget'ını tamamen temizle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            # Önce mevcut drag operation'daki kartı temizle
            if (self.main_manager.current_operation and 
                self.main_manager.current_operation.card_widget):
                
                card_widget = self.main_manager.current_operation.card_widget
                
                # Eğer bu zaten başka bir waiting area'da ise, oradan kaldır
                parent = card_widget.parent()
                if parent and hasattr(parent, 'layout'):
                    layout = parent.layout()
                    if layout:
                        layout.removeWidget(card_widget)
                
                # Widget'ı gizle ve temizle
                card_widget.hide()
                card_widget.setParent(None)
                
                # Gecikmeli sil
                QTimer.singleShot(100, card_widget.deleteLater)
                
            # Diğer yüzen/transparan widget'ları temizle
            for widget in app.allWidgets():
                try:
                    if (hasattr(widget, 'card_id') and 
                        getattr(widget, 'card_id', None) == card_id and 
                        widget != self.main_manager.current_operation.card_widget):
                        
                        # Widget'ın görünürlüğünü kontrol et
                        if widget.isVisible():
                            parent = widget.parent()
                            if parent and hasattr(parent, 'layout'):
                                parent.layout().removeWidget(widget)
                            
                            widget.hide()
                            widget.setParent(None)
                            QTimer.singleShot(100, widget.deleteLater)
                            
                except Exception:
                    continue
                    
        except Exception:
            pass
    
    def _extract_card_info(self, card_widget) -> bool:
        """Kart bilgilerini çıkar"""
        if not hasattr(card_widget, 'card_id'):
            return False
        
        self.main_manager.current_operation.card_id = card_widget.card_id
        self.main_manager.current_operation.card_type = CardType.COPY
        
        return True
    
    def _extract_source_waiting_area(self, card_widget):
        """Kartın kaynak waiting area'sını bul"""
        parent = card_widget.parent()
        while parent:
            if hasattr(parent, '__class__') and 'WaitingAreaWidget' in parent.__class__.__name__:
                self.main_manager.current_operation.source_widget = parent
                return
            parent = parent.parent()
    
    def _find_waiting_area(self, widget):
        """Widget'tan waiting area bul"""
        current = widget
        while current:
            if hasattr(current, '__class__') and 'WaitingAreaWidget' in current.__class__.__name__:
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
    
    def _update_waiting_area_ui(self, waiting_area):
        """Waiting area UI'ını güncelle"""
        try:
            waiting_area.update()
            waiting_area.repaint()
            
            if hasattr(waiting_area, '_update_container_height'):
                waiting_area._update_container_height()
            
            if hasattr(waiting_area, '_scroll_to_bottom'):
                QTimer.singleShot(100, waiting_area._scroll_to_bottom)
            
            QApplication.processEvents()
            
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