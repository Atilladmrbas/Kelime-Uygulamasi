# ui/words_panel/box_widgets/state/state_manager.py
import os
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QTimer
from .state_sync import StateSyncManager

class BoxStateManager:
    def __init__(self, box_view):
        self.box_view = box_view
        self.db_id = box_view.db_id
        self.db_connection = box_view.db_connection
        self.title = box_view.title
        self.ui_index = getattr(box_view, 'ui_index', 1)
        
        # Sync manager'ı başlat
        self.sync_manager = StateSyncManager(self.db_connection)
        
        self._last_state_hash = None
        self._state_check_timer = QTimer()
        self._state_check_timer.timeout.connect(self._check_state_changes)
        self._state_check_timer.start(30000)

    def load_counts_with_sync(self):
        """State ve veritabanını senkronize ederek sayaçları yükle"""
        if self.box_view._deleted:
            return 0, 0
        
        try:
            if self.db_id is not None and self.db_connection:
                # StateSyncManager ile senkronizasyon yap
                synced_state = self.sync_manager.sync_box_state(
                    self.db_id, 
                    self.title, 
                    self.ui_index
                )
                
                # Sayaçları hesapla
                unknown_count = len([c for c in synced_state.get("cards", []) 
                                   if c.get("bucket", 0) == 0])
                known_count = len([c for c in synced_state.get("cards", []) 
                                 if c.get("bucket", 0) == 1])
                
                # UI'yi güncelle
                self.box_view.update_card_counter(unknown_count, known_count)
                
                # Hash'i güncelle
                self._last_state_hash = self._calculate_state_hash(synced_state)
                
                return unknown_count, known_count
                
        except Exception:
            # Hata durumunda fallback yöntem
            return self._fallback_load_counts()
        
        return self._get_counts_from_database()

    def _fallback_load_counts(self):
        """Sync manager hatası durumunda eski yöntemle yükle"""
        try:
            if self.db_id is not None and self.db_connection:
                # BoxDetailStateLoader kullan
                try:
                    from ui.words_panel.detail_window.states.state_loader import BoxDetailStateLoader
                    state_loader = BoxDetailStateLoader(self.db_connection)
                except ImportError:
                    state_loader = self._create_simple_state_loader()
                
                state = state_loader.load_or_create(self.db_id, self.title, self.ui_index)
                
                # Database counts
                db_unknown, db_known = self._get_counts_from_database()
                
                # Sync if different
                if state_loader:
                    self.sync_state_with_database(state)
                
                # UI güncelle
                self.box_view.update_card_counter(db_unknown, db_known)
                
                return db_unknown, db_known
                
        except Exception:
            pass
        
        return 0, 0

    def _get_counts_from_database(self):
        """Veritabanından direkt sayıları al"""
        if not self.db_connection or not self.db_id:
            return 0, 0
        
        try:
            cursor = self.db_connection.conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM words 
                WHERE box = ? AND bucket = 0
            """, (self.db_id,))
            unknown_count = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM words 
                WHERE box = ? AND bucket = 1
            """, (self.db_id,))
            known_count = cursor.fetchone()[0] or 0
            
            return unknown_count, known_count
            
        except Exception:
            return 0, 0

    def sync_state_with_database(self, state):
        """State'i veritabanı ile senkronize et"""
        try:
            if not self.db_connection or not self.db_id:
                return
            
            cursor = self.db_connection.conn.cursor()
            cursor.execute("SELECT id, bucket FROM words WHERE box = ?", (self.db_id,))
            db_rows = cursor.fetchall()
            
            # Veritabanındaki kart ID'leri
            db_card_ids = set()
            for row in db_rows:
                if isinstance(row, tuple):
                    card_id = row[0]
                elif hasattr(row, '__getitem__'):
                    card_id = row[0] if row[0] is not None else 0
                elif hasattr(row, 'id'):
                    card_id = row.id
                else:
                    continue
                    
                if card_id is not None:
                    db_card_ids.add(card_id)
            
            # State'teki mevcut kartlar
            state_card_ids = {card.get("id") for card in state.cards if card.get("id")}
            
            # Yeni kartlar ekle
            for row in db_rows:
                if isinstance(row, tuple):
                    card_id, bucket = row[0], row[1]
                elif hasattr(row, '__getitem__'):
                    card_id = row[0] if row[0] is not None else 0
                    bucket = row[1] if row[1] is not None else 0
                elif hasattr(row, 'id') and hasattr(row, 'bucket'):
                    card_id = row.id
                    bucket = row.bucket
                else:
                    continue
                    
                if card_id is not None and card_id not in state_card_ids:
                    state.cards.append({
                        "id": card_id,
                        "bucket": bucket,
                        "rect": None
                    })
            
            # Eski kartları kaldır
            state.cards = [card for card in state.cards if card.get("id") in db_card_ids]
            
            # Değişiklikleri kaydet
            if hasattr(state, 'mark_dirty'):
                state.mark_dirty()
            
            if hasattr(state, 'save'):
                state.save()
            
        except Exception:
            pass

    def _calculate_state_hash(self, state_data):
        """State için hash hesapla"""
        try:
            if state_data and "cards" in state_data:
                card_data = [(c.get("id", 0), c.get("bucket", 0)) 
                           for c in state_data["cards"]]
                return hash(str(sorted(card_data)))
        except Exception:
            pass
        return None

    def _check_state_changes(self):
        """State değişikliklerini kontrol et"""
        if self.db_id is None or self.box_view._deleted:
            return
            
        try:
            current_hash = self._get_state_file_hash()
            
            if current_hash != self._last_state_hash:
                self._last_state_hash = current_hash
                self.load_counts_with_sync()
                
        except Exception:
            pass

    def _get_state_file_hash(self):
        """State dosyasının hash'ini al"""
        try:
            # BoxDetailStateLoader kullanarak state dosyasını oku
            try:
                from ui.words_panel.detail_window.states.state_loader import BoxDetailStateLoader
                state_loader = BoxDetailStateLoader(self.db_connection)
                state = state_loader.load_or_create(self.db_id, self.title, self.ui_index)
                
                # State'teki kartlardan hash oluştur
                if state and hasattr(state, 'cards'):
                    card_data = [(c.get("id", 0), c.get("bucket", 0)) 
                               for c in state.cards]
                    return hash(str(sorted(card_data)))
            except ImportError:
                pass
                
        except Exception:
            pass
        return None

    def refresh_card_counts(self):
        """Kart sayılarını yenile"""
        if not self.box_view._deleted:
            self.load_counts_with_sync()

    def update_title(self, new_title: str, old_title: str = None):
        """Başlık güncelleme - BoxDetailStateLoader ile"""
        try:
            if self.db_id is not None and self.db_connection:
                try:
                    from ui.words_panel.detail_window.states.state_loader import BoxDetailStateLoader
                    state_loader = BoxDetailStateLoader(self.db_connection)
                    
                    # State'i yükle
                    state = state_loader.load_or_create(self.db_id, old_title or self.title, self.ui_index)
                    
                    # Başlığı güncelle
                    if hasattr(state, 'rename'):
                        state.rename(new_title)
                    
                    # Database ile sync yap
                    self.sync_state_with_database(state)
                    
                except ImportError:
                    # Basit yöntem
                    old_state_file = self._find_state_file(self.db_id, self.ui_index, old_title or self.title)
                    if old_state_file and old_state_file.exists():
                        try:
                            with open(old_state_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            data["box_title"] = new_title
                            data["updated_at"] = datetime.now().isoformat()
                            
                            # Yeni dosya adı ile kaydet
                            safe_title = self._make_safe_filename(new_title)
                            if not safe_title:
                                safe_title = f"box_{self.db_id}"
                            
                            new_filename = f"{self.ui_index}_{safe_title}.state.json"
                            new_path = old_state_file.parent / new_filename
                            
                            with open(new_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            # Eski dosyayı sil
                            if old_state_file != new_path:
                                old_state_file.unlink()
                                
                        except Exception:
                            pass
                
        except Exception:
            pass

    def _find_state_file(self, box_id: int, ui_index: int, title: str) -> Path:
        """State dosyasını bul"""
        try:
            states_dir = self._get_states_dir()
            
            # Önce tam uyumlu dosyayı ara
            safe_title = self._make_safe_filename(title)
            if safe_title:
                filename = f"{ui_index}_{safe_title}.state.json"
                filepath = states_dir / filename
                if filepath.exists():
                    return filepath
            
            # Box ID ile ara
            for filepath in states_dir.glob("*.state.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get("box_id") == box_id:
                        return filepath
                except Exception:
                    continue
                    
        except Exception:
            pass
        return None

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

    def request_delete(self):
        """State dosyalarını sil"""
        self._state_check_timer.stop()
        
        if self.db_id is not None and self.db_connection:
            try:
                states_dir = self._get_states_dir()
                
                if states_dir.exists():
                    # Tüm state dosyalarını ara
                    for filepath in states_dir.glob("*.state.json"):
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            if data.get("box_id") == self.db_id:
                                os.remove(filepath)
                        except Exception:
                            # JSON okunamazsa bile sil
                            try:
                                os.remove(filepath)
                            except Exception:
                                pass
            except Exception:
                pass

    def _get_states_dir(self) -> Path:
        """State dosyalarının bulunduğu dizini al"""
        try:
            # Ana uygulama dizinini bul
            current_file = Path(__file__).resolve()
            
            # detail_window/states/state_json yolunu oluştur
            states_dir = current_file.parent.parent.parent / "detail_window" / "states" / "state_json"
            
            # Eğer bu dizin yoksa, oluştur
            if not states_dir.exists():
                # Alternatif yolları dene
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
                    # Hiçbiri yoksa, oluştur
                    states_dir.mkdir(parents=True, exist_ok=True)
            
            return states_dir
            
        except Exception:
            # Fallback: geçerli dizinde oluştur
            return Path.cwd() / "state_json"

    def cleanup(self):
        """Temizlik işlemleri"""
        try:
            self._state_check_timer.stop()
        except Exception:
            pass

    def _create_simple_state_loader(self):
        """Basit bir state loader oluştur"""
        class SimpleStateLoader:
            def __init__(self, db):
                self.db = db
            def load_or_create(self, box_id, title, ui_index=1):
                class SimpleState:
                    def __init__(self, box_id, title):
                        self.cards = []
                        self.box_title = title
                        self.box_id = box_id
                        self.dirty = False
                    def save(self): 
                        if self.dirty:
                            self.dirty = False
                            return True
                        return False
                    def mark_dirty(self): 
                        self.dirty = True
                    def rename(self, new_title):
                        self.box_title = new_title
                        self.mark_dirty()
                return SimpleState(box_id, title)
        return SimpleStateLoader(self.db_connection)