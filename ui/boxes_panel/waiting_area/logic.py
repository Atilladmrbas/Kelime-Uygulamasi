"""İŞ MANTIĞI - Tüm karmaşık işlemler"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpacerItem, QSizePolicy, QApplication
)
from PyQt6.QtCore import QTimer, Qt
import json
from ..drag_drop_manager import get_drag_drop_manager

class WaitingAreaLogic:
    """Waiting Area iş mantığı"""
    
    def __init__(self, widget):
        self.widget = widget
    
    def showEvent(self, event):
        """Widget gösterildiğinde"""
        QTimer.singleShot(50, self._check_all_cards_validity)
    
    def _check_all_cards_validity(self):
        """Tüm kartların geçerliliğini kontrol et"""
        if not self.widget.db:
            return
        
        cards_to_check = list(self.widget.cards)
        
        for word_id in cards_to_check:
            try:
                cursor = self.widget.db.conn.cursor()
                cursor.execute("SELECT original_card_id, is_copy FROM words WHERE id = ?", (word_id,))
                result = cursor.fetchone()
                
                if result:
                    original_card_id, is_copy = result
                    
                    if is_copy == 1 and original_card_id:
                        cursor.execute("SELECT 1 FROM words WHERE id = ?", (original_card_id,))
                        original_exists = cursor.fetchone() is not None
                        
                        if not original_exists:
                            self._remove_dead_copy_card(word_id)
                            
            except Exception:
                continue

    def _remove_dead_copy_card(self, word_id):
        """Ölü kopya kartı hem veritabanından hem de UI'dan kaldır"""
        try:
            if self.widget.db:
                try:
                    self.widget.db.delete_word(word_id)
                except Exception:
                    pass
            
            if word_id in self.widget.card_widgets:
                card_info = self.widget.card_widgets[word_id]
                card_widget = card_info.get('widget')
                
                if card_widget:
                    if hasattr(self.widget, 'cards_layout') and self.widget.cards_layout:
                        self.widget.cards_layout.removeWidget(card_widget)
                    
                    card_widget.hide()
                    card_widget.setParent(None)
                    card_widget.deleteLater()
            
            if word_id in self.widget.cards:
                self.widget.cards.remove(word_id)
            
            if word_id in self.widget.card_widgets:
                del self.widget.card_widgets[word_id]
            
            self._rearrange_cards_simple()
            self._update_transfer_button()
            
            return True
            
        except Exception:
            return False

    def _rearrange_cards_simple(self):
        """Kartları yeniden düzenle - BASİT VERSİYON"""
        try:
            if not hasattr(self.widget, 'container_layout'):
                return
            
            while self.widget.container_layout.count():
                item = self.widget.container_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
            
            for word_id in self.widget.cards:
                if word_id in self.widget.card_widgets:
                    card_info = self.widget.card_widgets[word_id]
                    card_widget = card_info.get('widget')
                    
                    if card_widget:
                        if card_widget.parent() != self.widget.container_widget:
                            card_widget.setParent(self.widget.container_widget)
                        
                        self.widget.container_layout.addWidget(card_widget)
                        card_widget.show()
            
            if len(self.widget.cards) == 0:
                self.widget.empty_container.show()
                
                found = False
                for i in range(self.widget.container_layout.count()):
                    item = self.widget.container_layout.itemAt(i)
                    if item and item.widget() == self.widget.empty_container:
                        found = True
                        break
                
                if not found:
                    self.widget.container_layout.insertWidget(0, self.widget.empty_container, 
                                                            alignment=Qt.AlignmentFlag.AlignHCenter)
                
                if not self.widget.empty_container.isVisible():
                    self.widget.empty_container.show()
                    
                self.widget.container_layout.update()
                
            else:
                if self.widget.empty_container.isVisible():
                    self.widget.empty_container.hide()
            
            self.widget.container_widget.update()
            self.widget.update()
            
        except Exception:
            pass
            
    def _add_dragged_card(self, word_id, source_widget=None):
        """Kartı bekleme alanına ekle"""
        if word_id in self.widget.cards:
            return None
        
        if len(self.widget.cards) == 0:
            self.widget.hide_empty_container()
        
        try:
            db = self.widget.db
            
            card_data = None
            if db:
                try:
                    card_data = db.get_word_by_id(word_id)
                except Exception:
                    card_data = None
            
            if not card_data:
                card_data = {
                    'id': word_id,
                    'english': f'Kart {word_id}',
                    'turkish': '',
                    'detail': '{}',
                    'box': None,
                    'bucket': 0,
                    'original_card_id': None,
                    'is_copy': 1
                }
            
            try:
                from ...copy_flash_card.copy_flash_card_view import CopyFlashCardView
            except ImportError:
                try:
                    from ui.boxes_panel.copy_flash_card.copy_flash_card_view import CopyFlashCardView
                except ImportError:
                    return None
            
            if 'id' not in card_data:
                card_data['id'] = word_id
            if 'is_copy' not in card_data:
                card_data['is_copy'] = 1
            
            card_view = CopyFlashCardView(
                data=card_data,
                parent=None,
                db=db
            )
            
            card_view.setFixedSize(260, 120)
            card_view.is_in_waiting_area = True
            
            card_view.setParent(self.widget.container_widget)
            
            self.widget.container_layout.addWidget(card_view)
            
            card_view.show()
            card_view.setVisible(True)
            card_view.raise_()
            
            try:
                if hasattr(card_view, 'del_btn'):
                    if hasattr(self, '_fix_delete_button_for_waiting_area'):
                        self._fix_delete_button_for_waiting_area(card_view, word_id, db, card_data)
            except Exception:
                pass
            
            self.widget.cards.append(word_id)
            self.widget.card_widgets[word_id] = {
                'widget': card_view,
                'is_copy': card_data.get('is_copy') == 1,
                'db': db,
                'card_data': card_data,
                'original_card_id': card_data.get('original_card_id')
            }
            
            self.widget._update_container_height()
            
            QTimer.singleShot(50, self.widget._scroll_to_bottom)
            
            QApplication.processEvents()
            
            self.widget.container_widget.update()
            self.widget.update()
            
            return card_view
                
        except Exception:
            return None

    def _fix_delete_button_for_waiting_area(self, card_view, word_id, db, card_data):
        """Waiting area için delete butonunu düzenle"""
        if hasattr(card_view, 'del_btn'):
            
            def waiting_area_delete_handler():
                # Kartın hala waiting area'da olup olmadığını kontrol et
                if word_id not in self.widget.cards:
                    return
                
                try:
                    # Orjinal delete dialog'unu çağır
                    card_view.on_delete_clicked()
                    
                    # Dialog kapandıktan sonra kartın hala var olup olmadığını kontrol et
                    def check_and_remove():
                        # Kart hala waiting area'da mı?
                        if word_id in self.widget.cards:
                            # Kart veritabanında hala var mı?
                            if self.widget.db:
                                try:
                                    cursor = self.widget.db.conn.cursor()
                                    cursor.execute("SELECT 1 FROM words WHERE id = ?", (word_id,))
                                    card_exists = cursor.fetchone() is not None
                                    
                                    if not card_exists:
                                        self._remove_card_by_id(word_id, emit_signal=True)
                                except Exception:
                                    pass
                            else:
                                self._remove_card_by_id(word_id, emit_signal=True)
                    
                    # 500ms sonra kontrol et (dialog'un kapanması için zaman ver)
                    QTimer.singleShot(500, check_and_remove)
                    
                except Exception:
                    # Hata durumunda waiting area'dan kaldırmaya çalış
                    QTimer.singleShot(100, lambda: self._safe_remove_from_waiting_area(word_id))
            
            # Eski bağlantıları kes ve yenisini bağla
            try:
                card_view.del_btn.clicked.disconnect()
            except:
                pass
            
            card_view.del_btn.clicked.connect(waiting_area_delete_handler)

    def _safe_remove_from_waiting_area(self, word_id):
        """Waiting area'dan kartı güvenli bir şekilde kaldır"""
        # Kart hala waiting area'da mı kontrol et
        if word_id not in self.widget.cards:
            return
        
        # Kartı waiting area'dan kaldır
        self._remove_card_by_id(word_id, emit_signal=True)
        
        # Layout'ta empty_container kontrol et
        found = False
        for i in range(self.widget.container_layout.count()):
            item = self.widget.container_layout.itemAt(i)
            if item and item.widget() == self.widget.empty_container:
                found = True
                break
        
        if not found and len(self.widget.cards) == 0:
            self.widget.container_layout.insertWidget(0, self.widget.empty_container, 
                                                    alignment=Qt.AlignmentFlag.AlignHCenter)
            self.widget.empty_container.show()
            self.widget.empty_container.raise_()

    def _refresh_box_view_for_card(self, card_id):
        """Kartın bulunduğu BoxView'ı refresh et"""
        try:
            if not self.widget.db:
                return
            
            cursor = self.widget.db.conn.cursor()
            cursor.execute("SELECT box FROM words WHERE id=?", (card_id,))
            row = cursor.fetchone()
            
            if row:
                box_id = row[0]
                app = QApplication.instance()
                if not app:
                    return
                
                for widget in app.allWidgets():
                    if hasattr(widget, '__class__') and 'BoxView' in widget.__class__.__name__:
                        if hasattr(widget, 'db_id') and widget.db_id == box_id:
                            if hasattr(widget, 'refresh_card_counts'):
                                widget.refresh_card_counts()
                                return
        except Exception:
            pass

    def _refresh_all_box_counts(self):
        """Tüm box sayılarını güncelle"""
        try:
            parent = self.widget.parent()
            while parent:
                if hasattr(parent, 'update_all_counts'):
                    parent.update_all_counts()
                    break
                parent = parent.parent()
        except:
            pass

    def _remove_card_by_id(self, word_id, emit_signal=True):
        """ID'ye göre kartı waiting area'dan kaldır - VERİTABANINDAN DA SİL"""
        if word_id not in self.widget.card_widgets:
            return
        
        card_info = self.widget.card_widgets[word_id]
        card_widget = card_info.get('widget')
        
        # Widget hala var mı kontrol et
        if not card_widget:
            if word_id in self.widget.cards:
                self.widget.cards.remove(word_id)
            
            if word_id in self.widget.card_widgets:
                del self.widget.card_widgets[word_id]
            
            # Kart kaldırıldıktan sonra empty_container kontrolü
            if len(self.widget.cards) == 0:
                self._show_empty_container_immediately()
            
            return
        
        # Kart widget'ı layout'ta ara
        for i in range(self.widget.container_layout.count()):
            item = self.widget.container_layout.itemAt(i)
            if item and item.widget() == card_widget:
                self.widget.container_layout.removeWidget(card_widget)
                break
        
        if word_id in self.widget.cards:
            self.widget.cards.remove(word_id)
        
        if word_id in self.widget.card_widgets:
            del self.widget.card_widgets[word_id]
        
        # Widget'ı temizle
        try:
            card_widget.hide()
            card_widget.setParent(None)
            QTimer.singleShot(100, card_widget.deleteLater)
        except RuntimeError:
            pass
        
        self.widget._update_container_height()
        
        # Kart kaldırıldıktan sonra empty_container kontrolü
        if len(self.widget.cards) == 0:
            self._show_empty_container_immediately()
        
        # VERİTABANINDAN DA SİL
        if self.widget.db:
            try:
                cursor = self.widget.db.conn.cursor()
                
                # waiting_area_cards tablosundan sil
                cursor.execute("DELETE FROM waiting_area_cards WHERE card_id = ?", (word_id,))
                
                self.widget.db.conn.commit()
                
            except Exception:
                if self.widget.db and hasattr(self.widget.db, 'conn'):
                    self.widget.db.conn.rollback()
        
        if emit_signal:
            self.widget.card_dragged_out.emit(word_id)

    def _show_empty_container_immediately(self):
        """Empty container'ı hemen göster"""
        # HEMEN göster
        self.widget.empty_container.show()
        self.widget.empty_container.raise_()
        
        # Layout'ta olduğundan emin ol
        found = False
        for i in range(self.widget.container_layout.count()):
            item = self.widget.container_layout.itemAt(i)
            if item and item.widget() == self.widget.empty_container:
                found = True
                break
        
        if not found:
            self.widget.container_layout.insertWidget(0, self.widget.empty_container, 
                                                    alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Son bir görünürlük kontrolü
        if not self.widget.empty_container.isVisible():
            self.widget.empty_container.setVisible(True)
    
    def clear_cards(self):
        """Tüm kartları temizle"""
        for word_id in list(self.widget.card_widgets.keys()):
            self._remove_card_by_id(word_id, emit_signal=False)
        
        self.widget.cards.clear()
        self.widget.card_widgets.clear()
        
        self.widget.empty_container.show()
        
        found = False
        for i in range(self.widget.container_layout.count()):
            item = self.widget.container_layout.itemAt(i)
            if item and item.widget() == self.widget.empty_container:
                found = True
                self.widget.container_layout.insertWidget(0, self.widget.empty_container)
                break
        
        if not found:
            self.widget.container_layout.insertWidget(0, self.widget.empty_container, 
                                                    alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.widget._update_container_height()
        self.widget.container_widget.update()
        self.widget.update()
        
    def get_cards(self):
        """Slot'lardaki kart ID'lerini getir"""
        return self.widget.cards.copy()
        
    def set_target_box_title(self, title):
        """Hedef kutu başlığını güncelle"""
        self.widget.target_box_title = title
        self.widget._update_button_text()
    
    def _update_transfer_button(self):
        """Transfer butonunu güncelle"""
        pass