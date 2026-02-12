# ui/words_panel/detail_window/internal/states/box_state.py
from __future__ import annotations

import os
from typing import Dict, List, Optional, TYPE_CHECKING

# Circular import'u önlemek için TYPE_CHECKING kullan
if TYPE_CHECKING:
    from .state_file_manager import StateFileManager


class BoxDetailState:
    """
    🔑 Detail window'un TEK GERÇEĞİ (STATE)
    Sadece state yönetimi - dosya işlemleri StateFileManager'a devredilir
    """
    
    VERSION = 5
    
    def __init__(self, box_id: int, box_title: str, ui_index: int, db=None):
        self.box_id = int(box_id)
        self.box_title = str(box_title)
        self.ui_index = int(ui_index)
        self.db = db
        
        # State data
        self.cards: List[Dict] = []
        self.scroll_y: int = 0
        self.panel_width: Optional[int] = None
        self._dirty = False
        
        # File manager - lazy loading ile circular import'u önle
        self._file_manager = None
    
    @property
    def file_manager(self):
        """Lazy loading ile file manager'ı al"""
        if self._file_manager is None:
            from .state_file_manager import StateFileManager
            self._file_manager = StateFileManager()
        return self._file_manager
    
    # State işlemleri (kart ekleme/çıkarma/güncelleme)
    def mark_dirty(self):
        self._dirty = True
    
    def save(self):
        """State'i dosyaya kaydet"""
        if self.file_manager.save_state_to_file(self):
            self._dirty = False
            return True
        return False
    
    def delete(self):
        """State dosyasını sil"""
        return self.file_manager.delete_state_file(self)
    
    def rename(self, new_title: str):
        """State'i yeniden adlandır"""
        old_title = self.box_title
        self.box_title = new_title
        self.mark_dirty()
        return self.file_manager.rename_state_file(self, new_title)
    
    def update_ui_index(self, new_index: int):
        """UI index'ini güncelle"""
        old_index = self.ui_index
        self.ui_index = new_index
        self.mark_dirty()
        return self.file_manager.rename_state_file(self, self.box_title, new_index)
    
    def remove_card(self, card_id: int):
        """Kartı state'ten kaldır"""
        for i, card in enumerate(self.cards):
            if card.get("id") == card_id:
                self.cards.pop(i)
                self.mark_dirty()
                return True
        return False
    
    def add_card(self, card_id: int, bucket: int = 0):
        """Kartı state'e ekle"""
        # Eğer kart zaten varsa, bucket'ını güncelle
        for card in self.cards:
            if card.get("id") == card_id:
                card["bucket"] = bucket
                self.mark_dirty()
                return False
        
        # Yoksa yeni ekle
        self.cards.append({
            "id": card_id,
            "bucket": bucket,
            "rect": None
        })
        self.mark_dirty()
        return True
    
    def sync_with_db(self, db=None):
        """DB'den kartları al ve state'i güncelle"""
        db = db or self.db
        if not db:
            return
        
        try:
            # DB'den güncel kartları al
            words = db.get_words_by_box(self.box_id)
            if not words:
                # DB'de kart yoksa state'i temizle
                if self.cards:
                    self.cards.clear()
                    self.mark_dirty()
                return
            
            # DB'deki kart ID'lerini topla
            db_card_ids = set()
            for word in words:
                if isinstance(word, dict):
                    card_id = word.get("id")
                    bucket = word.get("bucket", 0)
                else:
                    card_id = getattr(word, "id", None)
                    bucket = getattr(word, "bucket", 0)
                
                if card_id:
                    db_card_ids.add(card_id)
                    # Eğer state'te yoksa ekle
                    if not any(c.get("id") == card_id for c in self.cards):
                        self.cards.append({
                            "id": card_id,
                            "bucket": bucket,
                            "rect": None
                        })
                        self.mark_dirty()
            
            # DB'de olmayan kartları state'ten çıkar
            self.cards = [card for card in self.cards if card.get("id") in db_card_ids]
            
            if self._dirty:
                self.save()
                
        except Exception:
            pass
    
    def get_card_counts(self):
        """Bilinmeyen ve bilinen kart sayılarını döndür"""
        unknown = len([c for c in self.cards if c.get("bucket", 0) == 0])
        known = len([c for c in self.cards if c.get("bucket", 0) == 1])
        return unknown, known
    
    def __str__(self):
        return f"BoxDetailState(box_id={self.box_id}, title='{self.box_title}', " \
               f"ui_index={self.ui_index}, cards={len(self.cards)})"
    
    def __repr__(self):
        return self.__str__()