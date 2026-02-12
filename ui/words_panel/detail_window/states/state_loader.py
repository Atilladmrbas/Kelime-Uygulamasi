# ui/words_panel/detail_window/internal/states/state_loader.py
from __future__ import annotations

import os
from typing import List, Optional

from .box_state import BoxDetailState
from .state_file_manager import StateFileManager


class BoxDetailStateLoader:
    """
    State yükleme ve yönetimi.
    BoxDetailState ve StateFileManager'ı koordine eder.
    """
    
    def __init__(self, db):
        self.db = db
        self.file_manager = StateFileManager()
    
    def load_or_create(self, box_id: int, title: str, ui_index: Optional[int] = None) -> BoxDetailState:
        """State yükle veya oluştur"""
        
        # UI index belirle
        if ui_index is None:
            ui_index = self._determine_ui_index(box_id)
        
        # State oluştur
        state = BoxDetailState(box_id, title, ui_index, self.db)
        
        # State yükle
        if not self._load_state(state):
            # Yüklenemedi, DB'den doldur
            self._populate_from_db(state)
            state.mark_dirty()
            self.file_manager.save_state_to_file(state)
        
        return state
    
    def _determine_ui_index(self, box_id: int) -> int:
        """Box ID'den UI index'ini belirle"""
        try:
            all_boxes = self.db.get_boxes()
            for index, (b_id, title) in enumerate(all_boxes, 1):
                if b_id == box_id:
                    return index
            return 1
        except Exception:
            return 1
    
    def _load_state(self, state: BoxDetailState) -> bool:
        """State'i dosyadan yükle"""
        
        # 1. Numaralı dosyayı ara
        current_path = self.file_manager.get_state_path(state)
        
        if self._try_load_from_file(state, current_path):
            return True
        
        # 2. Numarasız eski dosyayı ara
        safe_title = self.file_manager._safe_filename(state.box_title)
        if not safe_title:
            safe_title = f"box_{state.box_id}"
        
        old_filename = f"{safe_title}.state.json"
        old_path = os.path.join(self.file_manager.states_dir, old_filename)
        
        if os.path.exists(old_path) and self._try_load_from_file(state, old_path):
            # Başarıyla yüklendi, numaralı olarak kaydet
            state.mark_dirty()
            self.file_manager.save_state_to_file(state)
            # Eski dosyayı sil
            try:
                os.remove(old_path)
            except Exception:
                pass
            return True
        
        return False
    
    def _try_load_from_file(self, state: BoxDetailState, filepath: str) -> bool:
        """Belirli dosyadan state yükle"""
        
        if not os.path.exists(filepath):
            return False
        
        data = self.file_manager.load_state_from_file(filepath)
        if not data:
            return False
        
        version = data.get("version", 1)
        stored_box_id = data.get("box_id")
        stored_title = data.get("box_title", "")
        stored_ui_index = data.get("ui_index", 0)
        
        if stored_box_id != state.box_id:
            return False
        
        if version == BoxDetailState.VERSION:
            # v5 formatı
            state.cards = data.get("cards", [])
            state.scroll_y = data.get("scroll_y", 0)
            state.panel_width = data.get("panel_width")
            state._dirty = False
            return True
        else:
            # Eski versiyonlardan dönüşüm
            return self._convert_from_old_version(state, data, filepath)
    
    def _convert_from_old_version(self, state: BoxDetailState, data: dict, filepath: str) -> bool:
        """Eski versiyondan dönüşüm"""
        try:
            version = data.get("version", 1)
            
            if version == 1:
                # v1 -> v5
                old_cards = data.get("cards", [])
                old_buckets = data.get("buckets", {})
                
                for card_id in old_cards:
                    bucket = old_buckets.get(str(card_id), 0)
                    state.cards.append({
                        "id": int(card_id),
                        "bucket": int(bucket),
                        "rect": None
                    })
            elif version in [2, 3, 4]:
                # v2-v4 -> v5
                state.cards = data.get("cards", [])
            
            state.scroll_y = data.get("scroll_y", 0)
            state.panel_width = data.get("panel_width")
            
            # Kaydet ve eski dosyayı sil
            state.mark_dirty()
            self.file_manager.save_state_to_file(state)
            
            try:
                os.remove(filepath)
            except Exception:
                pass
            
            return True
        except Exception:
            return False
    
    def _populate_from_db(self, state: BoxDetailState):
        """DB'den kartları state'e yükle"""
        try:
            words = self.db.get_words_by_box(state.box_id)
            
            if not words:
                return
            
            for word in words:
                if isinstance(word, dict):
                    card_id = word.get("id")
                    bucket = word.get("bucket", 0)
                else:
                    card_id = getattr(word, "id", None)
                    bucket = getattr(word, "bucket", 0)
                
                if card_id:
                    state.cards.append({
                        "id": card_id,
                        "bucket": bucket,
                        "rect": None
                    })
            
            # 🔴 KRİTİK: State'i dirty olarak işaretle
            state.mark_dirty()
            
        except Exception:
            pass
    
    def resolve_models(self, state: BoxDetailState, bucket: int) -> List:
        """State'teki kartları FlashCardData'ya çevir"""
        models = []
        
        try:
            state.sync_with_db(self.db)
            
            bucket_cards = [c for c in state.cards if c.get("bucket") == bucket]
            
            for card in bucket_cards:
                card_id = card.get("id")
                if not card_id:
                    continue
                
                try:
                    word_data = self.db.get_word_by_id(int(card_id))
                    if word_data:
                        if not isinstance(word_data, dict):
                            word_dict = {
                                "id": getattr(word_data, "id", None),
                                "english": getattr(word_data, "english", ""),
                                "turkish": getattr(word_data, "turkish", ""),
                                "detail": getattr(word_data, "detail", "{}"),
                                "box_id": getattr(word_data, "box_id", None),
                                "bucket": getattr(word_data, "bucket", bucket)
                            }
                        else:
                            word_dict = word_data
                        
                        # FlashCardData import'u
                        from core.flashcard_model import FlashCardData
                        model = FlashCardData(
                            english=word_dict.get("english", ""),
                            turkish=word_dict.get("turkish", ""),
                            detail=word_dict.get("detail", "{}"),
                            box=word_dict.get("box_id"),
                            id=word_dict.get("id")
                        )
                        
                        model.bucket = bucket
                        models.append(model)
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        return models