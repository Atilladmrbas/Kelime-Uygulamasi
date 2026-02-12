# ui/words_panel/box_widgets/state/state_sync.py
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib


class StateSyncManager:
    """State ve veritabanı senkronizasyonunu yönetir"""
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        
    def sync_box_state(self, box_id: int, box_title: str, ui_index: int = 1) -> Dict:
        """Kutu state'ini veritabanı ile senkronize et"""
        try:
            if not self.db_connection:
                return self._create_empty_state(box_id, box_title)
            
            # State dosyasını yükle veya oluştur
            state_data = self._load_or_create_state(box_id, box_title, ui_index)
            
            # Veritabanından güncel verileri al
            db_cards = self._get_cards_from_database(box_id)
            
            # Senkronizasyon yap
            synced_state = self._perform_sync(state_data, db_cards, box_id, box_title)
            
            # State'i kaydet
            if self._has_changes(state_data, synced_state):
                self._save_state_file(synced_state, ui_index, box_title)
            
            return synced_state
            
        except Exception:
            return self._create_empty_state(box_id, box_title)
    
    def _load_or_create_state(self, box_id: int, title: str, ui_index: int) -> Dict:
        """State dosyasını yükle veya yeni oluştur"""
        state_file = self._get_state_file_path(ui_index, title)
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                if self._validate_state_file(state_data, box_id):
                    return state_data
                    
            except (json.JSONDecodeError, IOError):
                pass
        
        return self._create_new_state(box_id, title, ui_index)
    
    def _create_new_state(self, box_id: int, title: str, ui_index: int) -> Dict:
        """Yeni state dict oluştur"""
        return {
            "box_id": box_id,
            "box_title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 5,
            "ui_index": ui_index,
            "cards": [],
            "scroll_y": 0,
            "panel_width": None
        }
    
    def _create_empty_state(self, box_id: int, title: str) -> Dict:
        """Boş state oluştur"""
        return {
            "box_id": box_id,
            "box_title": title,
            "cards": []
        }
    
    def _get_cards_from_database(self, box_id: int) -> List[Tuple]:
        """Veritabanından kartları al"""
        if not self.db_connection:
            return []
        
        try:
            cursor = self.db_connection.conn.cursor()
            cursor.execute("""
                SELECT id, bucket 
                FROM words 
                WHERE box = ? 
                ORDER BY id
            """, (box_id,))
            
            return cursor.fetchall()
            
        except Exception:
            return []
    
    def _perform_sync(self, state_data: Dict, db_cards: List[Tuple], box_id: int, box_title: str) -> Dict:
        """State ve veritabanı arasında senkronizasyon yap"""
        synced_state = state_data.copy()
        synced_cards = []
        
        # State'teki mevcut kartları ID'ye göre map'le
        state_card_map = {card["id"]: card for card in state_data.get("cards", []) if "id" in card}
        
        # Veritabanındaki her kart için
        for db_row in db_cards:
            if len(db_row) >= 2:
                card_id = db_row[0]
                
                # Kart state'te var mı?
                if card_id in state_card_map:
                    card = state_card_map[card_id]
                    card["bucket"] = db_row[1]
                    synced_cards.append(card)
                    del state_card_map[card_id]
                else:
                    new_card = {
                        "id": card_id,
                        "bucket": db_row[1],
                        "rect": None,
                        "is_visible": True
                    }
                    synced_cards.append(new_card)
        
        # Güncellemeler
        synced_state["cards"] = synced_cards
        synced_state["updated_at"] = datetime.now().isoformat()
        synced_state["box_title"] = box_title
        
        return synced_state
    
    def _has_changes(self, old_state: Dict, new_state: Dict) -> bool:
        """State'te değişiklik olup olmadığını kontrol et"""
        old_cards = sorted(old_state.get("cards", []), key=lambda x: x.get("id", 0))
        new_cards = sorted(new_state.get("cards", []), key=lambda x: x.get("id", 0))
        
        return old_cards != new_cards
    
    def _save_state_file(self, state_data: Dict, ui_index: int, title: str):
        """State dosyasını kaydet - {ui_index}_{title}.state.json formatında"""
        state_file = self._get_state_file_path(ui_index, title)
        
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
        except Exception:
            pass
    
    def _get_state_file_path(self, ui_index: int, title: str) -> Path:
        """State dosya yolunu oluştur - {ui_index}_{title}.state.json formatında"""
        try:
            # Ana uygulama dizinini bul
            current_file = Path(__file__).resolve()
            
            # detail_window/states/state_json yolunu oluştur
            states_dir = current_file.parent.parent.parent / "detail_window" / "states" / "state_json"
            
            # Eğer bu dizin yoksa, oluştur
            if not states_dir.exists():
                # Alternatif: projenin kök dizininde ara
                cwd = Path.cwd()
                possible_paths = [
                    cwd / "ui" / "words_panel" / "detail_window" / "states" / "state_json",
                    cwd / "detail_window" / "states" / "state_json",
                ]
                
                for path in possible_paths:
                    if path.exists():
                        states_dir = path
                        break
                else:
                    # Hiçbiri yoksa, mevcut dosyanın göreli konumunda oluştur
                    states_dir.mkdir(parents=True, exist_ok=True)
            
            # Dosya adını oluştur
            safe_title = self._make_safe_filename(title)
            if not safe_title:
                safe_title = f"box_{ui_index}"
            
            filename = f"{ui_index}_{safe_title}.state.json"
            return states_dir / filename
            
        except Exception:
            # Fallback: geçerli dizinde oluştur
            safe_title = self._make_safe_filename(title)
            if not safe_title:
                safe_title = f"box_{ui_index}"
            return Path.cwd() / f"{ui_index}_{safe_title}.state.json"
    
    def _make_safe_filename(self, text: str) -> str:
        """Metni dosya adı için güvenli hale getir"""
        if not text:
            return ""
        
        turkish_chars = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 
                         'ş': 's', 'ü': 'u', 'Ç': 'C', 'Ğ': 'G', 
                         'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'}
        
        for old, new in turkish_chars.items():
            text = text.replace(old, new)
        
        safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()
        safe = safe.replace(' ', '_').replace('-', '_')
        
        while '__' in safe:
            safe = safe.replace('__', '_')
        
        safe = safe.lower()[:30]
        
        if not safe or all(c == '_' for c in safe):
            return ""
        
        return safe
    
    def _validate_state_file(self, state_data: Dict, box_id: int) -> bool:
        """State dosyasının geçerli olup olmadığını kontrol et"""
        if "box_id" not in state_data or "cards" not in state_data:
            return False
        
        if state_data.get("box_id") != box_id:
            return False
        
        return True