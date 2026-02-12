"""
Kart ışınlama (teleportation) işlemleri - SEÇİM SENKRONİZASYONU
"""

import json
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from core.database import Database


class CardTeleporter(QObject):
    """Kart ışınlama işlemlerini yönetir"""
    
    card_moved = pyqtSignal(int, int)  # (card_id, new_box_id)
    box_counters_updated = pyqtSignal()  # Sayaçlar güncellendi
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        super().__init__()
        self.parent_widget = parent_widget
        self.db = Database()
        self.selected_cards = set()
        self.card_widgets = {}  # card_id -> widget mapping
        self.window_card_mapping = {}  # window_box_id -> [card_ids]
        
    # ==================== SEÇİM YÖNETİMİ ====================
    
    def add_card_selection(self, card_id: int, card_widget):
        """Kart seçimini ekle"""
        # Önce widget'ın geçerli olup olmadığını kontrol et
        if not self._is_widget_valid(card_widget):
            return
            
        self.selected_cards.add(card_id)
        self.card_widgets[card_id] = card_widget
        
        # Kartın hangi pencereye ait olduğunu kaydet
        window_box_id = self._get_widget_window_id(card_widget)
        if window_box_id:
            if window_box_id not in self.window_card_mapping:
                self.window_card_mapping[window_box_id] = set()
            self.window_card_mapping[window_box_id].add(card_id)
        
        if hasattr(card_widget, '_apply_selection_effect'):
            card_widget._apply_selection_effect()
    
    def remove_card_selection(self, card_id: int):
        """Kart seçimini kaldır"""
        if card_id in self.selected_cards:
            self.selected_cards.remove(card_id)
        
        if card_id in self.card_widgets:
            widget = self.card_widgets[card_id]
            
            # Widget hala geçerli mi kontrol et
            if self._is_widget_valid(widget) and hasattr(widget, '_remove_selection_effect'):
                widget._remove_selection_effect()
            
            del self.card_widgets[card_id]
            
            # Window mapping'den de kaldır
            self._remove_card_from_window_mapping(card_id)
    
    def _remove_card_from_window_mapping(self, card_id: int):
        """Kartı window mapping'den kaldır"""
        for window_id, card_set in list(self.window_card_mapping.items()):
            if card_id in card_set:
                card_set.remove(card_id)
                if not card_set:  # Eğer boşsa, window'u da kaldır
                    del self.window_card_mapping[window_id]
                break
    
    def clear_selection(self):
        """Tüm seçimleri temizle"""
        # Sadece geçerli widget'ların selection efektini kaldır
        for card_id, widget in list(self.card_widgets.items()):
            if self._is_widget_valid(widget) and hasattr(widget, '_remove_selection_effect'):
                widget._remove_selection_effect()
        
        self.selected_cards.clear()
        self.card_widgets.clear()
        self.window_card_mapping.clear()
    
    def has_selection(self) -> bool:
        """Seçim var mı?"""
        return len(self.selected_cards) > 0
    
    def toggle_card_selection(self, card_view):
        """Kart seçimini aç/kapat"""
        # Önce widget'ın geçerli olup olmadığını kontrol et
        if not self._is_widget_valid(card_view):
            self._cleanup_invalid_selections()
            return
        
        card_id = self._get_card_identifier(card_view)
        if not card_id:
            return
        
        if card_id in self.selected_cards:
            self.remove_card_selection(card_id)
        else:
            self.add_card_selection(card_id, card_view)
        
        card_view.update()
    
    def _is_widget_valid(self, widget) -> bool:
        """Widget'ın hala geçerli (silinmemiş) olup olmadığını kontrol et"""
        try:
            if widget is None:
                return False
            
            widget.objectName()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False
    
    def _cleanup_invalid_selections(self):
        """Geçersiz (silinmiş) widget'ları seçimlerden temizle"""
        valid_card_ids = []
        
        for card_id, widget in list(self.card_widgets.items()):
            if self._is_widget_valid(widget):
                valid_card_ids.append(card_id)
            else:
                # Geçersiz widget'ı listeden kaldır
                if card_id in self.selected_cards:
                    self.selected_cards.remove(card_id)
                if card_id in self.card_widgets:
                    del self.card_widgets[card_id]
                self._remove_card_from_window_mapping(card_id)
        
        # Sadece geçerli kartları koru
        self.selected_cards = set(valid_card_ids)
    
    def notify_window_closed(self, window_box_id: int):
        """Bir pencere kapatıldığında bu pencereye ait seçimleri temizle"""
        try:
            # ✅ DÜZELTME: Önce pencere ID'sinin mapping'de olup olmadığını kontrol et
            if window_box_id in self.window_card_mapping:
                # Bu pencereye ait tüm kartları bul
                cards_in_window = list(self.window_card_mapping[window_box_id])
                
                for card_id in cards_in_window:
                    self.remove_card_selection(card_id)
                
                # Window mapping'den kaldır
                del self.window_card_mapping[window_box_id]
            
            # ✅ DÜZELTME: Ayrıca pencereye ait tüm kartları da temizle
            # Eşleşen tüm kartları bul
            cards_to_remove = []
            for card_id, widget in list(self.card_widgets.items()):
                try:
                    if self._is_widget_valid(widget):
                        widget_window_id = self._get_widget_window_id(widget)
                        if widget_window_id == window_box_id:
                            cards_to_remove.append(card_id)
                    else:
                        # Geçersiz widget'ı da kaldır
                        cards_to_remove.append(card_id)
                except Exception:
                    cards_to_remove.append(card_id)
            
            # Bulunan kartları temizle
            for card_id in cards_to_remove:
                if card_id in self.selected_cards:
                    self.selected_cards.remove(card_id)
                if card_id in self.card_widgets:
                    # Widget hala geçerliyse selection efektini kaldır
                    widget = self.card_widgets[card_id]
                    if self._is_widget_valid(widget) and hasattr(widget, '_remove_selection_effect'):
                        widget._remove_selection_effect()
                    del self.card_widgets[card_id]
                
            # Her ihtimale karşı tüm geçersiz seçimleri temizle
            self._cleanup_invalid_selections()
            
        except Exception:
            # Hata durumunda sadece temizleme yap
            self._cleanup_invalid_selections()
    
    def _get_widget_window_id(self, widget) -> Optional[int]:
        """Widget'ın ait olduğu pencere ID'sini bul"""
        try:
            parent = widget
            while parent:
                if hasattr(parent, 'box_id') and parent.box_id:
                    return parent.box_id
                parent = parent.parent()
        except RuntimeError:
            pass
        return None
    
    # ==================== CONTEXT MENU ====================
    
    def create_context_menu(self, card_view, position) -> Optional[QMenu]:
        app = QApplication.instance()
        if app and (app.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier):
            return None
        
        # Önce geçersiz seçimleri temizle
        self._cleanup_invalid_selections()
        
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #cccccc; border-radius: 6px; padding: 4px; }
            QMenu::item { background-color: transparent; color: black; padding: 6px 16px; margin: 2px; 
                         border-radius: 4px; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
            QMenu::item:disabled { color: #666666; }
            QMenu::item:selected { background-color: #e3f2fd; color: black; }
            QMenu::separator { height: 1px; background-color: #eeeeee; margin: 4px 8px; }
        """)
        
        self._populate_direct_menu(menu, card_view)
        return menu
    
    def _get_card_identifier(self, card_view):
        if hasattr(card_view, 'card_id') and card_view.card_id:
            return card_view.card_id
        elif hasattr(card_view, 'temp_id') and card_view.temp_id:
            return f"temp_{card_view.temp_id}"
        return None
    
    # ==================== KUTU LİSTESİ ====================
    
    def _get_boxes_with_names(self):
        try:
            boxes_result = self.db.get_boxes()
            boxes_with_details = []
            
            for item in boxes_result:
                try:
                    if isinstance(item, tuple) and len(item) >= 2:
                        box_id, title = item[0], item[1]
                    elif isinstance(item, dict):
                        box_id, title = item.get('id'), item.get('title', f'Kutu {item.get("id")}')
                    else:
                        box_id, title = item, f'Kutu {item}'
                    
                    box_id = int(box_id)
                    if '📦' in title:
                        title = title.replace('📦', '').strip()
                    if not title or title == 'None':
                        title = f'Kutu {box_id}'
                    
                    boxes_with_details.append((box_id, title.strip()))
                except Exception:
                    continue
            
            return boxes_with_details
        except Exception:
            return []
    
    def _populate_direct_menu(self, menu: QMenu, card_view) -> None:
        try:
            boxes = self._get_boxes_with_names()
            if not boxes:
                action = QAction("📦 Hiç kutu yok", menu)
                action.setEnabled(False)
                menu.addAction(action)
                return
            
            # Başlık
            title_text = f"📤 {len(self.selected_cards)} Seçili Kartı Taşı:" if self.has_selection() else "📤 Kartı Taşı:"
            title_action = QAction(title_text, menu)
            title_action.setEnabled(False)
            menu.addAction(title_action)
            menu.addSeparator()
            
            # Mevcut kutu
            current_box_id = getattr(card_view, 'box_id', None) or self._find_card_box_id(card_view)
            
            for box_id, title in boxes:
                clean_title = title.strip() or f'Kutu {box_id}'
                is_current = False
                
                try:
                    current_id_int = int(current_box_id) if current_box_id else None
                    box_id_int = int(box_id)
                    is_current = (current_id_int is not None and current_id_int == box_id_int)
                except (ValueError, TypeError):
                    pass
                
                if is_current:
                    action_text = f"📦 {clean_title} (Seçililerin Şimdiki Kutusu)" if self.has_selection() else f"📦 {clean_title} (Mevcut)"
                    action = QAction(action_text, menu)
                    action.setEnabled(False)
                    menu.addAction(action)
                else:
                    action = QAction(f"📦 {clean_title}", menu)
                    if self.has_selection():
                        action.triggered.connect(lambda checked=False, b_id=box_id, b_title=clean_title: 
                                                self._teleport_selected_to_box(b_id, b_title))
                    else:
                        action.triggered.connect(lambda checked=False, b_id=box_id, c_view=card_view, b_title=clean_title: 
                                                self._teleport_single_card(c_view, b_id, b_title))
                    menu.addAction(action)
            
            if self.has_selection():
                menu.addSeparator()
                clear_action = QAction("🗑️ Seçimleri Temizle", menu)
                clear_action.triggered.connect(self.clear_selection)
                menu.addAction(clear_action)
            
            menu.addSeparator()
            
        except Exception:
            action = QAction("⚠️ Kutular yüklenemedi", menu)
            action.setEnabled(False)
            menu.addAction(action)
    
    # ==================== KART TAŞIMA ====================
    
    def _teleport_selected_to_box(self, target_box_id: int, box_title: str):
        # Önce geçersiz seçimleri temizle
        self._cleanup_invalid_selections()
        
        if not self.has_selection():
            return
        
        selected_widgets = []
        for card_id in self.selected_cards:
            widget = self.card_widgets.get(card_id)
            if widget and self._is_widget_valid(widget):
                selected_widgets.append(widget)
        
        if selected_widgets:
            self._teleport_cards_to_box(selected_widgets, target_box_id, box_title)
            self.clear_selection()
    
    def _teleport_single_card(self, card_view, target_box_id: int, box_title: str):
        if not self._is_widget_valid(card_view):
            return
        
        self._teleport_cards_to_box([card_view], target_box_id, box_title)
        if self.has_selection():
            self.clear_selection()

    def _notify_all_containers_before_removal(self, card_ids: List[int]):
        """Tüm açık BoxDetailContent pencerelerini kartların kaldırılacağı konusunda bilgilendir"""
        try:
            from PyQt6.QtWidgets import QApplication
            
            app = QApplication.instance()
            if not app:
                return
            
            # Tüm BoxDetailContent widget'larını bul
            for widget in app.allWidgets():
                try:
                    if hasattr(widget, '__class__') and widget.__class__.__name__ == 'BoxDetailContent':
                        # Her kart için container'ı güncelle
                        for card_id in card_ids:
                            QTimer.singleShot(10, lambda w=widget, cid=card_id: w._remove_card_immediately(cid))
                except RuntimeError:
                    continue  # Widget silinmiş olabilir
        except Exception as e:
            print(f"❌ Container bildirimi hatası: {e}")
    
    def _teleport_cards_to_box(self, card_widgets: List, target_box_id: int, box_title: str) -> bool:
        # Önce geçerli widget'ları filtrele
        valid_widgets = []
        for widget in card_widgets:
            if self._is_widget_valid(widget):
                valid_widgets.append(widget)
        
        if not valid_widgets:
            return False
        
        moved_cards = []
        original_box_ids = set()
        
        # Veritabanını güncelle
        for card_view in valid_widgets:
            try:
                card_id = getattr(card_view, 'card_id', None)
                if not card_id:
                    continue
                
                card_data = self._get_card_data(card_view)
                if not card_data:
                    continue
                
                current_box_id = card_data.get('box_id')
                if current_box_id:
                    original_box_ids.add(current_box_id)
                
                if current_box_id and int(current_box_id) == int(target_box_id):
                    continue
                
                # Veritabanı güncellemesi
                self.db.update_word(
                    word_id=int(card_id),
                    english=card_data.get('english', '') or "",
                    turkish=card_data.get('turkish', '') or "",
                    detail=card_data.get('detail', '{}') or "{}",
                    box_id=int(target_box_id),
                    bucket=0
                )
                
                moved_cards.append(card_id)
            except Exception:
                continue
        
        if not moved_cards:
            return False
        
        # State dosyalarını güncelle
        self._bulk_update_state_files(moved_cards, list(original_box_ids), target_box_id)
        
        # ✅ ÖNEMLİ: Önce tüm UI container'larını güncelle
        self._notify_all_containers_before_removal(moved_cards)
        
        # Kartları orijinal konumlarından kaldır
        for card_view in valid_widgets:
            try:
                card_id = getattr(card_view, 'card_id', None)
                if card_id:
                    card_data = self._get_card_data(card_view)
                    current_box_id = card_data.get('box_id') if card_data else None
                    self._completely_remove_card_from_origin(card_view, current_box_id)
            except Exception:
                continue
        
        # Hedef kutu açıksa ekle
        self._bulk_add_to_target_box_if_open(moved_cards, target_box_id, valid_widgets)
        
        # KRİTİK: Sayaçları güncelle
        self._update_box_counters_immediately(original_box_ids, target_box_id)
        
        # Sinyal gönder
        for card_id in moved_cards:
            self.card_moved.emit(card_id, target_box_id)
        self.box_counters_updated.emit()
        
        return True
    
    def _update_box_counters_immediately(self, original_box_ids: set, target_box_id: int):
        """İki kutunun da sayacını ANINDA güncelle"""
        try:
            # 1. Ana pencereyi bul ve refresh_all_boxes metodunu çağır
            main_window = self.parent_widget
            while main_window and not hasattr(main_window, 'refresh_all_boxes'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'refresh_all_boxes'):
                main_window.refresh_all_boxes()
                return True
            
            # 2. Alternatif: WordsWindow'daki container'ı bul
            words_window = self._find_words_window()
            if words_window and hasattr(words_window, 'container'):
                for box in words_window.container.boxes:
                    if hasattr(box, 'db_id'):
                        if box.db_id == target_box_id or box.db_id in original_box_ids:
                            if hasattr(box, 'refresh_card_counts_from_database'):
                                box.refresh_card_counts_from_database()
            
            # 3. Direct DB query ile güncelle
            self._force_refresh_box_counters(list(original_box_ids), target_box_id)
            
            return True
        except Exception:
            return False
    
    def _force_refresh_box_counters(self, old_box_ids: List[int], new_box_id: int):
        """DB sorgusu ile zorla sayaçları güncelle"""
        try:
            # Tüm kutuların sayaçlarını güncelle
            all_box_ids = set(old_box_ids + [new_box_id])
            
            for box_id in all_box_ids:
                if not box_id:
                    continue
                    
                # BoxView'ı bul
                box_view = self._find_box_view_by_id(box_id)
                if box_view:
                    QTimer.singleShot(100, box_view.refresh_card_counts)
                else:
                    QTimer.singleShot(200, lambda b_id=box_id: self._refresh_box_from_db(b_id))
            
        except Exception:
            pass
    
    def _find_box_view_by_id(self, box_id: int):
        """Box ID'ye göre BoxView'ı bul"""
        try:
            words_window = self._find_words_window()
            if words_window and hasattr(words_window, 'container'):
                for box in words_window.container.boxes:
                    if hasattr(box, 'db_id') and box.db_id == box_id:
                        return box
        except Exception:
            pass
        return None
    
    def _refresh_box_from_db(self, box_id: int):
        """Box'ı direkt DB'den güncelle"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM words WHERE box_id = ? AND bucket = 0", (box_id,))
            unknown_result = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) FROM words WHERE box_id = ? AND bucket = 1", (box_id,))
            known_result = cursor.fetchone()
            
        except Exception:
            pass
    
    # ==================== YARDIMCI METODLAR ====================
    
    def _find_card_box_id(self, card_view):
        try:
            # Önce card_view'dan al
            if hasattr(card_view, 'box_id') and card_view.box_id:
                return card_view.box_id
            
            # Sonra card_view'ın data'sından al
            if hasattr(card_view, 'data') and card_view.data:
                if isinstance(card_view.data, dict):
                    return card_view.data.get('box_id') or card_view.data.get('box')
                else:
                    return getattr(card_view.data, 'box_id', None) or getattr(card_view.data, 'box', None)
            
            # Parent'lardan ara
            parent = card_view.parent()
            while parent:
                if hasattr(parent, 'box_id') and parent.box_id:
                    return parent.box_id
                parent = parent.parent()
        except Exception:
            pass
        return None
    
    def _find_words_window(self):
        try:
            main_window = self.parent_widget
            while main_window and not hasattr(main_window, 'words_window'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'words_window'):
                return main_window.words_window
        except Exception:
            return None
    
    def _get_card_data(self, card_view) -> Dict[str, Any]:
        card_data = {'english': '', 'turkish': '', 'detail': '{}', 'box_id': None, 'id': None}
        
        try:
            if hasattr(card_view, 'data') and card_view.data:
                if isinstance(card_view.data, dict):
                    box_id = card_view.data.get('box_id') or card_view.data.get('box')
                    card_data.update({
                        'english': card_view.data.get('english', ''),
                        'turkish': card_view.data.get('turkish', ''),
                        'detail': card_view.data.get('detail', '{}'),
                        'box_id': box_id,
                        'id': card_view.data.get('id')
                    })
                else:
                    box_id = getattr(card_view.data, 'box_id', None) or getattr(card_view.data, 'box', None)
                    card_data.update({
                        'english': getattr(card_view.data, 'english', ''),
                        'turkish': getattr(card_view.data, 'turkish', ''),
                        'detail': getattr(card_view.data, 'detail', '{}'),
                        'box_id': box_id,
                        'id': getattr(card_view.data, 'id', None)
                    })
            
            if not card_data['english'] and hasattr(card_view, 'front_fields'):
                if card_view.front_fields and card_view.front_fields[0].text():
                    card_data['english'] = card_view.front_fields[0].text()
            
            if not card_data['turkish'] and hasattr(card_view, 'back_fields'):
                if card_view.back_fields and card_view.back_fields[0].text():
                    card_data['turkish'] = card_view.back_fields[0].text()
            
            if not card_data['id']:
                card_data['id'] = getattr(card_view, 'card_id', None)
            
            if not card_data['box_id']:
                card_data['box_id'] = self._find_card_box_id(card_view)
                
        except Exception:
            pass
        
        return card_data
    
    # ==================== STATE GÜNCELLEME ====================
    
    def _bulk_update_state_files(self, card_ids: List[int], old_box_ids: List[int], new_box_id: int):
        try:
            from ui.words_panel.detail_window.states.box_detail_state_loader import BoxDetailStateLoader
            
            state_loader = BoxDetailStateLoader(self.db)
            
            # Yeni kutu state'ine kartları ekle
            try:
                box_title = f"Kutu {new_box_id}"
                boxes = self._get_boxes_with_names()
                for bid, title in boxes:
                    if bid == new_box_id:
                        box_title = title
                        break
                
                ui_index = 1
                boxes_list = self.db.get_boxes()
                for idx, (bid, _) in enumerate(boxes_list, 1):
                    if bid == new_box_id:
                        ui_index = idx
                        break
                
                new_state = state_loader.load_or_create(new_box_id, box_title, ui_index)
                if not new_state:
                    from ui.words_panel.detail_window.states.box_detail_state import BoxDetailState
                    new_state = BoxDetailState(new_box_id, box_title, ui_index, self.db)
                    new_state.cards = []
                
                for card_id in card_ids:
                    card_exists = False
                    for card in new_state.cards:
                        if card.get('id') == card_id:
                            card['bucket'] = 0
                            card_exists = True
                            break
                    
                    if not card_exists:
                        new_state.cards.append({'id': card_id, 'bucket': 0, 'rect': None})
                
                new_state.mark_dirty()
                new_state.save()
                
            except Exception:
                pass
            
            # Eski kutu state'lerinden kartları kaldır
            for old_box_id in old_box_ids:
                if old_box_id:
                    try:
                        old_box_title = f"Kutu {old_box_id}"
                        boxes = self._get_boxes_with_names()
                        for bid, title in boxes:
                            if bid == old_box_id:
                                old_box_title = title
                                break
                        
                        old_ui_index = 1
                        boxes_list = self.db.get_boxes()
                        for idx, (bid, _) in enumerate(boxes_list, 1):
                            if bid == old_box_id:
                                old_ui_index = idx
                                break
                        
                        old_state = state_loader.load_or_create(old_box_id, old_box_title, old_ui_index)
                        if old_state:
                            old_state.cards = [c for c in old_state.cards if c.get('id') not in card_ids]
                            old_state.mark_dirty()
                            old_state.save()
                    except Exception:
                        pass
                        
        except Exception:
            pass
    
    # ==================== UI GÜNCELLEME ====================
    
    def _bulk_add_to_target_box_if_open(self, card_ids: List[int], target_box_id: int, card_widgets: List) -> bool:
        try:
            from ui.words_panel.detail_window.slide_bar_handle import SidebarHandle
            
            if not hasattr(SidebarHandle, '_all_windows'):
                return False
            
            open_window = None
            for window_box_id, window in SidebarHandle._all_windows.items():
                if window and hasattr(window, 'box_id'):
                    try:
                        if int(window.box_id) == int(target_box_id):
                            open_window = window
                            break
                    except (ValueError, TypeError):
                        continue
            
            if not open_window or not hasattr(open_window, 'content') or not open_window.content:
                return False
            
            # Kart verilerini topla
            all_card_data = []
            for card_view in card_widgets:
                card_id = getattr(card_view, 'card_id', None)
                if card_id:
                    card_data = self._get_card_data(card_view)
                    if card_data:
                        card_data.update({'box_id': target_box_id, 'bucket': 0, 'id': card_id})
                        all_card_data.append(card_data)
            
            if not all_card_data:
                return False
            
            # Sol containera ekle
            if hasattr(open_window.content, 'left_container'):
                if hasattr(open_window.content.left_container, '_data'):
                    current_data = list(open_window.content.left_container._data)
                    existing_ids = {item.get('id') if isinstance(item, dict) else getattr(item, 'id', None) 
                                   for item in current_data}
                    
                    added = False
                    for card_data in all_card_data:
                        if card_data['id'] not in existing_ids:
                            current_data.append(card_data)
                            added = True
                    
                    if added:
                        open_window.content.left_container.set_data(current_data)
                        if hasattr(open_window.content.left_container, '_ensure_built'):
                            open_window.content.left_container._ensure_built()
                        if hasattr(open_window.content.left_container, '_update_visible'):
                            open_window.content.left_container._update_visible(force=True)
                        if hasattr(open_window.content, 'finalize_all_layouts'):
                            open_window.content.finalize_all_layouts()
                        return True
            
            return False
                
        except Exception:
            return False
    
    # card_teleporter.py dosyasında şu metodu güncelle:

    def _completely_remove_card_from_origin(self, card_view, original_box_id):
        """Kartı orijinal konumundan temizle - UI güncellemesi artık başka yerde yapılıyor"""
        try:
            card_id = getattr(card_view, 'card_id', None)
            if not card_id:
                return
            
            # Sadece widget'ı temizle, UI güncellemesi _notify_all_containers_before_removal'da yapılıyor
            card_view.hide()
            try:
                card_view.setParent(None)
                card_view.deleteLater()
            except:
                pass
                
        except Exception as e:
            print(f"❌ Kart temizleme hatası: {e}")
    
    def _delete_from_detail_window(self, card_view):
        try:
            card_id = getattr(card_view, 'card_id', None)
            if not card_id:
                return
            
            # Detail window'u bul
            parent = card_view.parent()
            detail_window = None
            while parent:
                if hasattr(parent, 'delete_card_from_detail'):
                    detail_window = parent
                    break
                parent = parent.parent()
            
            if detail_window:
                # State'ten kaldır
                if hasattr(detail_window, 'state') and detail_window.state:
                    detail_window.state.remove_card(card_id)
                    detail_window.state.mark_dirty()
                    detail_window.state.save()
                
                # Content'ten kaldır
                if hasattr(detail_window, 'content') and detail_window.content:
                    if hasattr(detail_window.content, 'delete_card'):
                        detail_window.content.delete_card(card_id)
                
                # UI'yi yenile
                if hasattr(detail_window.content, 'finalize_all_layouts'):
                    QTimer.singleShot(100, detail_window.content.finalize_all_layouts)
                
        except Exception:
            pass