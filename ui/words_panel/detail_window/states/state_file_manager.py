# ui/words_panel/detail_window/internal/states/state_file_manager.py
from __future__ import annotations

import os
import json
import glob
from pathlib import Path
from typing import List, Tuple, Dict, Optional, TYPE_CHECKING

# Circular import'u önlemek için TYPE_CHECKING
if TYPE_CHECKING:
    from .box_state import BoxDetailState


class StateFileManager:
    """
    State dosya işlemleri:
    - Dosya yolları
    - Temizlik (orphaned states)
    - Onarım (repair)
    - Yeniden sıralama (reorder)
    """
    
    def __init__(self, states_dir: Optional[str] = None):
        self.states_dir = states_dir or self._default_states_dir()
        Path(self.states_dir).mkdir(exist_ok=True)
    
    def _default_states_dir(self) -> str:
        """State dosyalarının varsayılan dizini - state_json"""
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "state_json")  # DÜZELTİLDİ: states_json -> state_json
    
    def get_state_path(self, state: BoxDetailState) -> str:
        """State için dosya yolunu oluştur"""
        safe_title = self._safe_filename(state.box_title)
        if not safe_title:
            safe_title = f"box_{state.box_id}"
        
        filename = f"{state.ui_index}_{safe_title}.state.json"
        return os.path.join(self.states_dir, filename)
    
    def get_state_path_for_params(self, box_id: int, title: str, ui_index: int) -> str:
        """Parametrelerden dosya yolunu oluştur"""
        safe_title = self._safe_filename(title)
        if not safe_title:
            safe_title = f"box_{box_id}"
        
        filename = f"{ui_index}_{safe_title}.state.json"
        return os.path.join(self.states_dir, filename)
    
    @staticmethod
    def _safe_filename(text: str) -> str:
        """Metni dosya adı için güvenli hale getir"""
        safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).strip()
        safe = safe.replace(' ', '_').lower()[:50]
        return safe
    
    def load_state_from_file(self, filepath: str) -> Optional[Dict]:
        """Dosyadan state verilerini yükle"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_state_to_file(self, state: BoxDetailState) -> bool:
        """State'i dosyaya kaydet"""
        try:
            data = {
                "version": BoxDetailState.VERSION,
                "box_id": state.box_id,
                "box_title": state.box_title,
                "ui_index": state.ui_index,
                "cards": state.cards,
                "scroll_y": state.scroll_y,
                "panel_width": state.panel_width,
            }
            
            filepath = self.get_state_path(state)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            state._dirty = False
            return True
        except Exception:
            return False
    
    def rename_state_file(self, state: BoxDetailState, new_title: str, new_ui_index: Optional[int] = None) -> bool:
        """State dosyasını yeniden adlandır"""
        old_path = self.get_state_path(state)
        
        # Yeni parametreler
        new_ui_index = new_ui_index or state.ui_index
        new_path = self.get_state_path_for_params(state.box_id, new_title, new_ui_index)
        
        if old_path == new_path:
            return True
        
        try:
            # Yeni dosya varsa sil
            if os.path.exists(new_path):
                os.remove(new_path)
            
            # Dosyayı taşı
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
            
            return True
        except Exception:
            return False
    
    def delete_state_file(self, state: BoxDetailState) -> bool:
        """State dosyasını sil"""
        try:
            filepath = self.get_state_path(state)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False
    
    def cleanup_orphaned_states(self, valid_box_ids: set) -> int:
        """Database'de olmayan kutuların state dosyalarını temizle"""
        deleted_count = 0
        pattern = os.path.join(self.states_dir, "*.state.json")
        
        for filepath in glob.glob(pattern):
            try:
                data = self.load_state_from_file(filepath)
                if data:
                    stored_box_id = data.get("box_id")
                    if stored_box_id not in valid_box_ids:
                        os.remove(filepath)
                        deleted_count += 1
            except Exception:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        
        return deleted_count
    
    def repair_all_states(self, box_order: List[Tuple[int, str, int]]) -> int:
        """Tüm state dosyalarını onar ve numaralandır"""
        repaired_count = 0
        
        for box_id, title, ui_index in box_order:
            # State dosyasını bul
            pattern = os.path.join(self.states_dir, "*.state.json")
            found_file = None
            state_data = None
            
            for filepath in glob.glob(pattern):
                data = self.load_state_from_file(filepath)
                if data and data.get("box_id") == box_id:
                    found_file = filepath
                    state_data = data
                    break
            
            if found_file and state_data:
                # Yeni dosya adı
                new_path = self.get_state_path_for_params(box_id, title, ui_index)
                
                # State verisini güncelle
                state_data["version"] = BoxDetailState.VERSION
                state_data["ui_index"] = ui_index
                state_data["box_title"] = title
                
                # Dosyayı yeniden adlandır/güncelle
                try:
                    if found_file != new_path:
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        
                        os.rename(found_file, new_path)
                    
                    # İçeriği güncelle
                    with open(new_path if found_file != new_path else found_file, 
                              'w', encoding='utf-8') as f:
                        json.dump(state_data, f, indent=2, ensure_ascii=False)
                    
                    repaired_count += 1
                except Exception:
                    continue
        
        return repaired_count