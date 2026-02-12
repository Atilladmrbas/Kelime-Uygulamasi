# ui/words_panel/detail_window/box_detail_controller.py
"""BoxDetailContent için merkezi kontrol sistemi - KOPYA KART YÖNETİMİ"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class BoxDetailController(QObject):
    """BoxDetailContent için merkezi kontrol sınıfı"""
    
    # Sinyaller
    original_card_moved_to_learned = pyqtSignal(int)  # original_card_id
    copy_cards_updated = pyqtSignal()  # Kopya kartlar güncellendi
    
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.box_contents = {}  # box_id -> BoxDetailContent mapping
        self.card_to_box_map = {}  # card_id -> box_id mapping
        self.selected_cards = set()  # Seçili kart ID'leri
        
    def register_box_content(self, box_id, box_content):
        """BoxDetailContent'ı kaydet"""
        self.box_contents[box_id] = box_content
        
    def unregister_box_content(self, box_id):
        """BoxDetailContent'ı kayıttan sil"""
        if box_id in self.box_contents:
            del self.box_contents[box_id]
    
    def handle_card_transfer(self, card_id: int, from_type: str, to_type: str, box_content):
        """Kart transferini işle - KOPYALARI OTOMATİK SİLME YOK"""
        if not self.db:
            return False
        
        # Kartın orijinal mi kopya mı olduğunu kontrol et
        is_original = self._is_original_card(card_id)
        
        # Eğer kart öğrendiklerim'e taşınıyorsa
        if to_type == "learned" and is_original:
            # ✅ Kopya kartları otomatik silme - KALDIRILDI
            # Kullanıcı "Hızlı Taşı ve Sil" butonuna basmadığı sürece kopyalar kalır
            pass
        
        return True
    
    def move_original_to_learned(self, original_card_id: int):
        """Orijinal kartı öğrendiklerim'e taşı"""
        if not self.db or not original_card_id:
            return False
        
        try:
            # Orijinal kartın bucket'ını 1 yap (öğrendiklerim)
            cursor = self.db.conn.cursor()
            cursor.execute("UPDATE words SET bucket=1 WHERE id=?", (original_card_id,))
            self.db.conn.commit()
            
            # Tüm box_contents'lere bildir
            for box_id, content in self.box_contents.items():
                if hasattr(content, '_transfer_single_card'):
                    # Kart bu box'ta mı kontrol et
                    for container_type in ["unknown", "learned"]:
                        for card_widget in content.card_widgets[container_type]:
                            if hasattr(card_widget, 'card_id') and card_widget.card_id == original_card_id:
                                content._transfer_single_card(
                                    original_card_id,
                                    1,  # new_bucket
                                    "unknown",
                                    "learned"
                                )
                                break
            
            return True
        except Exception:
            return False
    
    def handle_card_learned(self, card_id: int, box_id: int):
        """Kart öğrenildiğinde çağrılır - KOPYALARI OTOMATİK SİLME YOK"""
        if not self.db:
            return
        
        # Kartın orijinal mi kontrol et
        is_original = self._is_original_card(card_id)
        if not is_original:
            return
        
        # ✅ Kopya kartları otomatik silme - KALDIRILDI
        # Kullanıcı seçimine bırak
    
    def _is_original_card(self, card_id: int) -> bool:
        """Kartın orijinal olup olmadığını kontrol et"""
        if not self.db:
            return True
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT is_copy FROM words WHERE id=?", (card_id,))
            row = cursor.fetchone()
            
            if row and row[0] == 1:
                return False
            return True
            
        except Exception:
            return True
    
    def _update_memory_box_counts(self):
        """Tüm memory box sayaçlarını güncelle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'boxes_window'):
                    if hasattr(widget.boxes_window, 'design'):
                        if hasattr(widget.boxes_window.design, 'update_all_counts'):
                            QTimer.singleShot(100, widget.boxes_window.design.update_all_counts)
                            return
        except Exception:
            pass
    
    def get_card_info(self, card_id: int):
        """Kart bilgilerini getir"""
        if not self.db:
            return None
        
        return self.db.get_word_by_id(card_id)
    
    def is_card_copy(self, card_id: int) -> bool:
        """Kart kopya mı?"""
        return not self._is_original_card(card_id)
    
    def get_original_card_id(self, copy_card_id: int):
        """Kopya kartın orijinal ID'sini getir"""
        if not self.db:
            return None
        
        return self.db.get_original_card_id(copy_card_id)
    
    def add_card_selection(self, card_id: int):
        """Kart seçimine ekle"""
        self.selected_cards.add(card_id)
    
    def remove_card_selection(self, card_id: int):
        """Kart seçiminden çıkar"""
        if card_id in self.selected_cards:
            self.selected_cards.remove(card_id)
    
    def clear_selection(self):
        """Tüm seçimleri temizle"""
        self.selected_cards.clear()
    
    def has_selection(self) -> bool:
        """Seçim var mı?"""
        return len(self.selected_cards) > 0
    
    def get_selected_cards(self):
        """Seçili kartları getir"""
        return list(self.selected_cards)
    
    def process_bulk_transfer(self, card_ids: list, from_type: str, to_type: str, box_content):
        """Toplu kart transferini işle"""
        if not self.db:
            return False
        
        # ✅ Kopya kartları otomatik silme - KALDIRILDI
        # Kullanıcı "Hızlı Taşı ve Sil" butonuna basmadığı sürece kopyalar kalır
        
        return True


# Global controller instance
_global_controller = None

def get_controller(db=None):
    """Global controller instance'ını al"""
    global _global_controller
    if _global_controller is None:
        _global_controller = BoxDetailController(db)
    elif db and not _global_controller.db:
        _global_controller.db = db
    
    return _global_controller

def init_controller(db):
    """Controller'ı başlat"""
    return get_controller(db)