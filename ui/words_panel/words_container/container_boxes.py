# ui/words_panel/words_container/container_boxes.py
from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, pyqtSignal
from PyQt6.QtCore import Qt

from ui.words_panel.words_container.container_core import WordsContainerCore
from ui.words_panel.box_widgets.box_view import BoxView
from ui.words_panel.words_container.box_button import AddBoxButton


class WordsContainer(WordsContainerCore):
    selection_changed = pyqtSignal(list)
    
    def __init__(self, db=None, parent=None):
        super().__init__(parent)

        self.db = db
        self.boxes: list[BoxView] = []
        self.selected_boxes: list[BoxView] = []

        self.add_button = AddBoxButton()
        self.add_button.clicked.connect(self._add_new_box_clicked)
        
        self.box_added_callback = None
        self.box_selection_changed = self.selection_changed

    def _add_new_box_clicked(self):
        self.add_box()

    def rearrange(self):
        items = self.boxes + [self.add_button]
        self.rearrange_grid(items)

    def load_boxes_from_db(self):
        if not self.db:
            return

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget and widget != self.add_button:
                try:
                    widget.deleteLater()
                except:
                    pass

        self.boxes.clear()
        self.selected_boxes.clear()

        self._cleanup_orphaned_states()

        try:
            db_boxes = self.db.get_boxes()
            
            for idx, (db_id, title) in enumerate(db_boxes, 1):
                self._ensure_state_file_exists(db_id, title, idx)
                
                box = BoxView(
                    title=str(title),
                    db_id=db_id,
                    db_connection=self.db,
                    ui_index=idx
                )
                
                box.ui_index = idx
                
                box.delete_requested.connect(lambda b=box: self.remove_box(b))
                box.title_changed.connect(
                    lambda new_title, b=box: self.update_box_title(b, new_title)
                )
                box.selection_changed.connect(self.on_box_selection_changed)
                
                if hasattr(box, 'enter_requested'):
                    box.enter_requested.connect(lambda b=box: self._forward_enter_request(b))

                self.boxes.append(box)
                
                if hasattr(box, 'label') and box.label:
                    box.label.setText(str(title))
                    
        except Exception:
            pass

        self.rearrange()
        
        if self._is_widget_valid(self.add_button):
            self.add_button.show()
            self.add_button.raise_()

    def _get_states_dir(self) -> Path:
        """State dosyalarının bulunduğu dizini al - detail_window/states/state_json"""
        try:
            current_file = Path(__file__).resolve()
            
            # detail_window/states/state_json yolunu oluştur
            ui_words_panel_dir = current_file.parent.parent
            states_dir = ui_words_panel_dir / "detail_window" / "states" / "state_json"
            
            if states_dir.exists():
                return states_dir
            
            # Alternatif yolları dene
            cwd = Path.cwd()
            possible_paths = [
                cwd / "ui" / "words_panel" / "detail_window" / "states" / "state_json",
                cwd / "detail_window" / "states" / "state_json",
            ]
            
            for path in possible_paths:
                if path.exists():
                    return path
            
            # Hiçbiri yoksa, oluştur
            states_dir.mkdir(parents=True, exist_ok=True)
            return states_dir
            
        except Exception:
            # Fallback
            return Path.cwd() / "state_json"

    def _create_state_file_for_box(self, box_id: int, title: str, ui_index: int):
        try:
            states_dir = self._get_states_dir()
            states_dir.mkdir(parents=True, exist_ok=True)
            
            safe_title = self._make_safe_filename(title)
            if not safe_title:
                safe_title = f"box_{box_id}"
            
            filename = f"{ui_index}_{safe_title}.state.json"
            filepath = states_dir / filename
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data["box_title"] = title
                data["updated_at"] = datetime.now().isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return
            
            state_data = {
                "version": 5,
                "box_id": box_id,
                "box_title": title,
                "ui_index": ui_index,
                "cards": [],
                "scroll_y": 0,
                "panel_width": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass

    def _ensure_state_file_exists(self, box_id: int, title: str, ui_index: int):
        try:
            states_dir = self._get_states_dir()
            
            safe_title = self._make_safe_filename(title)
            if not safe_title:
                safe_title = f"box_{box_id}"
            
            pattern1 = f"{ui_index}_{safe_title}.state.json"
            filepath1 = states_dir / pattern1
            
            if filepath1.exists():
                return True
            
            # Eski dosyaları ara (farklı formatlarda olabilir)
            for filepath in states_dir.glob("*.state.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get("box_id") == box_id:
                        # Eski dosyayı yeni formatla güncelle
                        data["box_title"] = title
                        data["ui_index"] = ui_index
                        data["updated_at"] = datetime.now().isoformat()
                        
                        new_filename = f"{ui_index}_{safe_title}.state.json"
                        new_path = states_dir / new_filename
                        
                        with open(new_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        # Eski dosyayı sil (yenisi farklı isimdeyse)
                        if filepath != new_path and filepath.exists():
                            filepath.unlink()
                        
                        return True
                        
                except Exception:
                    continue
            
            # Hiç dosya bulunamazsa yeni oluştur
            self._create_state_file_for_box(box_id, title, ui_index)
            return True
            
        except Exception:
            return False

    def _make_safe_filename(self, text: str) -> str:
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
        
        safe = safe.lower()[:50]
        
        if not safe or all(c == '_' for c in safe):
            return ""
        
        return safe

    def _cleanup_orphaned_states(self):
        """Database'de olmayan kutuların state dosyalarını temizle"""
        try:
            states_dir = self._get_states_dir()
            if not states_dir.exists():
                return
            
            db_boxes = self.db.get_boxes()
            valid_box_ids = {box[0] for box in db_boxes}
            
            for filepath in states_dir.glob("*.state.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    box_id = data.get("box_id")
                    if box_id not in valid_box_ids:
                        filepath.unlink()
                        
                except Exception:
                    try:
                        filepath.unlink()
                    except:
                        pass
                
        except Exception:
            pass

    def add_box(self, title="Yeni Kutu"):
        db_id = self.db.add_box(title)
        
        if not db_id:
            return
        
        new_ui_index = len(self.boxes) + 1
        
        self._create_state_file_for_box(db_id, title, new_ui_index)
        
        box = BoxView(
            title=str(title),
            db_id=db_id,
            db_connection=self.db,
            ui_index=new_ui_index
        )
        
        box.ui_index = new_ui_index

        box.delete_requested.connect(lambda b=box: self.remove_box(b))
        box.title_changed.connect(
            lambda new_title, b=box: self.update_box_title(b, new_title)
        )
        box.selection_changed.connect(self.on_box_selection_changed)
        
        if hasattr(box, 'enter_requested'):
            box.enter_requested.connect(lambda b=box: self._forward_enter_request(b))

        self.boxes.append(box)

        if self.box_added_callback:
            self.box_added_callback(box)

        if hasattr(box, 'label') and box.label:
            box.label.setText(str(title))

        self.rearrange()
        
        return box

    def update_box_title(self, box: BoxView, new_title: str):
        if not box.db_id or not box.title:
            return
        
        old_title = box.title
        
        self.db.update_box_title(box.db_id, new_title)
        
        box.title = new_title
        
        if hasattr(box, 'label') and box.label:
            box.label.setText(new_title)
        
        success = self._rename_state_file(box.db_id, old_title, new_title, box.ui_index)
        
        if not success:
            self._create_state_file_for_box(box.db_id, new_title, box.ui_index)

    def _rename_state_file(self, box_id: int, old_title: str, new_title: str, ui_index: int) -> bool:
        try:
            states_dir = self._get_states_dir()
            if not states_dir.exists():
                states_dir.mkdir(parents=True, exist_ok=True)
                return False
            
            old_safe_title = self._make_safe_filename(old_title)
            new_safe_title = self._make_safe_filename(new_title)
            
            if not old_safe_title:
                old_safe_title = f"box_{box_id}"
            if not new_safe_title:
                new_safe_title = f"box_{box_id}"
            
            old_filename = f"{ui_index}_{old_safe_title}.state.json"
            new_filename = f"{ui_index}_{new_safe_title}.state.json"
            
            old_path = states_dir / old_filename
            new_path = states_dir / new_filename
            
            # Eski dosyayı bul
            if not old_path.exists():
                for filepath in states_dir.glob("*.state.json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data.get("box_id") == box_id:
                            old_path = filepath
                            break
                    except Exception:
                        continue
            
            # Eski dosya yoksa yeni oluştur
            if not old_path.exists():
                self._create_state_file_for_box(box_id, new_title, ui_index)
                return True
            
            # Aynı dosyaysa sadece içeriği güncelle
            if old_path == new_path:
                with open(old_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data["box_title"] = new_title
                data["updated_at"] = datetime.now().isoformat()
                
                with open(old_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            
            # Yeni dosya varsa sil
            if new_path.exists():
                new_path.unlink()
            
            # Eski dosyayı oku ve güncelle
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data["box_title"] = new_title
            data["updated_at"] = datetime.now().isoformat()
            
            # Yeni dosyaya yaz
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Eski dosyayı sil
            old_path.unlink()
            
            return True
            
        except Exception:
            return False

    def remove_box(self, box):
        try:
            states_dir = self._get_states_dir()
            
            safe_title = self._make_safe_filename(box.title)
            if not safe_title:
                safe_title = f"box_{box.db_id}"
            
            filename = f"{box.ui_index}_{safe_title}.state.json"
            filepath = states_dir / filename
            
            if filepath.exists():
                filepath.unlink()
            else:
                # Farklı isimdeki dosyayı bul ve sil
                for fpath in states_dir.glob("*.state.json"):
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data.get("box_id") == box.db_id:
                            fpath.unlink()
                            break
                    except Exception:
                        continue
                
        except Exception:
            pass
        
        if box in self.boxes:
            self.boxes.remove(box)
        
        if box in self.selected_boxes:
            self.selected_boxes.remove(box)
        
        try:
            box.deleteLater()
        except:
            pass
        
        if hasattr(box, 'db_id') and box.db_id:
            try:
                self.db.delete_box(box.db_id)
            except Exception:
                pass
        
        self._reindex_boxes_after_deletion()
        
        self.rearrange()
        self.selection_changed.emit(self.selected_boxes)

    def _reindex_boxes_after_deletion(self):
        """Box silindikten sonra kalan box'ları yeniden indeksle"""
        try:
            states_dir = self._get_states_dir()
            
            box_order = []
            for idx, box in enumerate(self.boxes, 1):
                if hasattr(box, 'db_id') and box.db_id:
                    box.ui_index = idx
                    box_order.append((box.db_id, box.title, idx))
            
            # Tüm state dosyalarını güncelle
            for db_id, title, new_index in box_order:
                for filepath in states_dir.glob("*.state.json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data.get("box_id") == db_id:
                            data["ui_index"] = new_index
                            data["box_title"] = title
                            data["updated_at"] = datetime.now().isoformat()
                            
                            safe_title = self._make_safe_filename(title)
                            if not safe_title:
                                safe_title = f"box_{db_id}"
                            
                            new_filename = f"{new_index}_{safe_title}.state.json"
                            new_path = states_dir / new_filename
                            
                            # Yeni dosyaya yaz
                            with open(new_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            # Eski dosyayı sil (farklı isimdeyse)
                            if filepath != new_path and filepath.exists():
                                filepath.unlink()
                            
                            break
                            
                    except Exception:
                        continue
                        
        except Exception:
            pass

    def _forward_enter_request(self, box):
        """Enter tuşuna basıldığında detail window aç - DÜZELTİLMİŞ"""
        print(f"➡️ WordsContainer: Enter tuşuna basıldı: {box.db_id} - {box.title}")
        
        # Önce parent window'ı bul
        parent_window = self.window()
        
        print(f"🔍 WordsContainer: Parent window: {parent_window}")
        print(f"🔍 WordsContainer: Parent has open_box_detail: {hasattr(parent_window, 'open_box_detail')}")
        print(f"🔍 WordsContainer: Parent DB var mı: {hasattr(parent_window, 'db') and parent_window.db is not None}")
        
        if parent_window and hasattr(parent_window, 'open_box_detail'):
            try:
                # DB'yi kontrol et
                if not hasattr(parent_window, 'db') or not parent_window.db:
                    print(f"❌ WordsContainer: Parent window'da DB yok!")
                    return
                
                detail_window = parent_window.open_box_detail(box)
                if detail_window:
                    print(f"✅ WordsContainer: Detail window açıldı: {box.db_id}")
            except Exception as e:
                print(f"❌ WordsContainer: Detail window açma hatası: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ WordsContainer: open_box_detail metodu bulunamadı, alternatif yöntem deneniyor...")
            
            # Alternatif: direkt BoxDetailWindow oluştur
            try:
                from ui.words_panel.detail_window.box_detail_window import BoxDetailWindow
                
                # DB'yi bul
                db = self.db
                if not db and parent_window and hasattr(parent_window, 'db'):
                    db = parent_window.db
                
                if not db:
                    print(f"❌ WordsContainer: DB bulunamadı!")
                    return
                
                print(f"🔧 WordsContainer: Alternatif yöntemle DB kullanılıyor: {db is not None}")
                
                window = BoxDetailWindow.get_or_create_window(
                    parent=parent_window,
                    db=db,
                    box_id=box.db_id,
                    box_title=box.title,
                    origin_widget=box
                )
                
                window.open_window()
                print(f"✅ WordsContainer: Alternatif yöntemle detail window açıldı")
                
            except Exception as e:
                print(f"❌ WordsContainer: Alternatif yöntem hatası: {e}")
                import traceback
                traceback.print_exc()

    def on_box_selection_changed(self, box: BoxView, is_selected: bool):
        if not self._is_widget_valid(box):
            return
        
        if is_selected:
            if box not in self.selected_boxes:
                self.selected_boxes.append(box)
        else:
            if box in self.selected_boxes:
                self.selected_boxes.remove(box)
        
        self.selection_changed.emit(self.selected_boxes)
        
        parent = self.parent()
        while parent:
            if hasattr(parent, '_handle_box_selection'):
                parent._handle_box_selection(box, is_selected)
                break
            parent = parent.parent()
    
    def _is_widget_valid(self, widget):
        if widget is None:
            return False
            
        try:
            _ = widget.__class__.__name__
            
            if isinstance(widget, BoxView) and hasattr(widget, 'isDeleted'):
                if widget.isDeleted():
                    return False
            
            return hasattr(widget, 'isWidgetType') and widget.isWidgetType()
            
        except RuntimeError:
            return False
        except Exception:
            return False

    def resizeEvent(self, event):
        try:
            super().resizeEvent(event)

            if not self._initial or not hasattr(self, "boxes"):
                return

            box_w, box_h, spacing = self.compute_responsive()
            
            if hasattr(self, 'add_button'):
                try:
                    if self._is_widget_valid(self.add_button):
                        self.add_button.setFixedSize(box_w, box_h)
                        self.add_button.update()
                except Exception:
                    pass
            
            font_size = max(16, min(28, int(16 + (box_w - 160) * 0.1)))
            
            for box in self.boxes:
                if not self._is_widget_valid(box):
                    continue
                
                if hasattr(box, 'update_card_counter_font_size'):
                    box.update_card_counter_font_size(font_size)
                
                if hasattr(box, 'anim') and box.anim and box.anim.state() == QPropertyAnimation.State.Running:
                    box.anim.stop()
                
                if hasattr(box, 'is_selected') and box.is_selected:
                    if hasattr(box, 'card') and hasattr(box, 'card_expanded_rect'):
                        box.card.setGeometry(box.card_expanded_rect)
                        box.is_expanded = True
                    
        except Exception:
            super().resizeEvent(event)