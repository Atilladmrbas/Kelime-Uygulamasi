# boxes_window.py - DÜZELTİLMİŞ VERSİYON
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QPoint
from .scrollable_boxes_area import ScrollableBoxesArea


class BoxesWindow(QWidget):
    """Ana kutular layout'u - SADECE OTOMATİK SCROLL"""

    def __init__(self, db=None):
        super().__init__()
        
        self.db = db
        self.card_original_boxes = {}
        self.drawn_cards = {}
        
        # Otomatik scroll için değişkenler
        self.auto_scroll_timer = QTimer()
        self.auto_scroll_timer.timeout.connect(self._handle_auto_scroll)
        self.auto_scroll_timer.setInterval(30)
        
        # Scroll bölgeleri (üst ve alt)
        self.top_scroll_zone = 100
        self.bottom_scroll_zone = 100
        self.scroll_speed = 25
        
        # Drag kontrolü için
        self.drag_check_timer = QTimer()
        self.drag_check_timer.timeout.connect(self._check_drag_status)
        self.drag_check_timer.setInterval(100)
        
        # Drag durumu
        self.is_drag_active = False
        # Sekme değişimi durumu
        self.is_tab_changed = False
        # Timer'ların durumunu takip et
        self.timers_active = False

        if self.db:
            self._ensure_waiting_area_table()
        
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        self.update_counts_timer = QTimer()
        self.update_counts_timer.setSingleShot(True)
        self.update_counts_timer.timeout.connect(self._update_box_counts)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.scrollable_area = ScrollableBoxesArea(self)
        self.scrollable_area.create_boxes_with_waiting_areas(db)
        
        main_layout.addWidget(self.scrollable_area)
        
        self._connect_waiting_area_signals()
        
        self.scrollable_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self._update_all_card_positions)
        self.scroll_timer.start(50)
        
        # Timer'ları başlat
        self._start_timers()
    
    def _start_timers(self):
        """Timer'ları başlat"""
        if not self.timers_active:
            self.drag_check_timer.start()
            self.timers_active = True
    
    def _stop_timers(self):
        """Timer'ları durdur (sadece gerçek kapanma durumunda)"""
        if self.timers_active:
            if self.auto_scroll_timer.isActive():
                self.auto_scroll_timer.stop()
            if self.drag_check_timer.isActive():
                self.drag_check_timer.stop()
            self.timers_active = False
    
    def _check_drag_status(self):
        """Drag durumunu periyodik olarak kontrol et"""
        try:
            from ui.boxes_panel.drag_drop_manager.base_manager import get_drag_drop_manager
            drag_manager = get_drag_drop_manager()
            
            if drag_manager and hasattr(drag_manager, 'current_operation'):
                if drag_manager.current_operation and drag_manager.current_operation.card_widget:
                    if not self.is_drag_active:
                        self.is_drag_active = True
                        
                        if not self.auto_scroll_timer.isActive():
                            self.auto_scroll_timer.start()
                    return
            
            if self.is_drag_active:
                self.is_drag_active = False
                
                if self.auto_scroll_timer.isActive():
                    self.auto_scroll_timer.stop()
                    
        except Exception:
            pass
    
    def _handle_auto_scroll(self):
        """Drag sırasında fare pozisyonuna göre otomatik scroll"""
        try:
            if not self.is_drag_active:
                return
            
            from PyQt6.QtGui import QCursor
            cursor_pos = QCursor.pos()
            
            widget_pos = self.mapFromGlobal(cursor_pos)
            
            if not self.rect().contains(widget_pos):
                return
            
            if not hasattr(self, 'scrollable_area'):
                return
            
            scroll_area = self.scrollable_area
            scroll_bar = scroll_area.verticalScrollBar()
            
            if not scroll_bar or not scroll_bar.isEnabled():
                return
            
            if widget_pos.y() < self.top_scroll_zone:
                current_value = scroll_bar.value()
                new_value = max(scroll_bar.minimum(), current_value - self.scroll_speed)
                if new_value != current_value:
                    scroll_bar.setValue(new_value)
                    self._update_all_card_positions()
            
            elif widget_pos.y() > self.height() - self.bottom_scroll_zone:
                current_value = scroll_bar.value()
                new_value = min(scroll_bar.maximum(), current_value + self.scroll_speed)
                if new_value != current_value:
                    scroll_bar.setValue(new_value)
                    self._update_all_card_positions()
                    
        except Exception:
            pass

    def _connect_waiting_area_signals(self):
        """Waiting area signal'larını bağla"""
        for box_id in range(1, 6):
            waiting_areas = self.scrollable_area.get_waiting_areas(box_id)
            for i, waiting_area in enumerate(waiting_areas):
                if waiting_area:
                    waiting_area.db = self.db
                    waiting_area.card_dropped.connect(self._on_card_dropped_to_waiting)
                    
                    if i == 0:
                        waiting_area.button_clicked.connect(
                            lambda checked=False, b_id=box_id: 
                            self._on_transfer_button_clicked(b_id, "area1")
                        )
                    else:
                        waiting_area.button_clicked.connect(
                            lambda checked=False, b_id=box_id: 
                            self._on_transfer_button_clicked(b_id, "area2")
                        )

    def _force_immediate_count_update(self):
        """Kontrolleri hemen güncelle"""
        if hasattr(self, 'update_counts_timer'):
            self.update_counts_timer.stop()
        self._update_box_counts()

    def _update_box_counts(self):
        """Box sayılarını güncelle"""
        for box_id in range(1, 6):
            waiting_areas = self.scrollable_area.get_waiting_areas(box_id)
            if waiting_areas:
                pass

    def _on_scroll_changed(self, value):
        """Scroll değiştiğinde kart pozisyonlarını güncelle"""
        self._update_all_card_positions()
        
    def showEvent(self, event):
        """Widget gösterildiğinde"""
        super().showEvent(event)
        self._restore_drawn_cards_from_db()
        self._update_all_card_positions()
        # Sekme tekrar aktif olduğunda timer'ları başlat
        self._start_timers()
        self.is_tab_changed = False
    
    def hideEvent(self, event):
        """Widget gizlenirken - Temizlik"""
        # Sadece kart durumlarını kaydet, timer'ları DURDURMA
        self._save_drawn_cards_to_db()
        
        # Widget hala geçerliyse, sadece invalid widget'ları temizle
        if self.isVisible():
            self._cleanup_only_invalid_widgets()
        
        # Timer'ları durdurma - sadece gizleniyoruz, kapanmıyoruz
        # Eğer drag işlemi devam ediyorsa timer'lar çalışmaya devam etmeli
        self.is_tab_changed = True
        
        super().hideEvent(event)
    
    def resizeEvent(self, event):
        """Widget yeniden boyutlandırıldığında"""
        super().resizeEvent(event)
        QTimer.singleShot(100, self._update_all_card_positions)

    def _ensure_waiting_area_table(self):
        """waiting_area_cards tablosunun var olduğundan emin ol"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='waiting_area_cards'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE waiting_area_cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        card_id INTEGER NOT NULL UNIQUE,
                        target_box_id INTEGER NOT NULL,
                        area_index INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (card_id) REFERENCES words (id) ON DELETE CASCADE
                    )
                """)
                self.db.conn.commit()
                
        except Exception:
            pass

    def add_drawn_card(self, memory_box, card_widget):
        """Çekilmiş kartı sisteme ekle - VERİTABANINI DA GÜNCELLE"""
        card_id = getattr(card_widget, 'card_id', None)
        if not card_id:
            return
        
        if self.db and card_id not in self.card_original_boxes:
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT box FROM words WHERE id = ?", (card_id,))
                result = cursor.fetchone()
                if result:
                    original_box = result[0]
                    self.card_original_boxes[card_id] = original_box
                    
                    cursor.execute("UPDATE words SET is_drawn = 1 WHERE id = ?", (card_id,))
                    
                    card_data = self.db.get_word_by_id(card_id)
                    original_card_id = card_data.get('original_card_id', card_id)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO drawn_cards 
                        (original_card_id, copy_card_id, box_id, is_active) 
                        VALUES (?, ?, ?, 1)
                    """, (original_card_id, card_id, memory_box.box_id))
                    
                    self.db.conn.commit()
            except Exception:
                pass
        
        if card_widget.parent() != self:
            card_widget.setParent(self)
        
        card_widget.show()
        
        self.drawn_cards[card_id] = {
            'widget': card_widget,
            'box': memory_box
        }
        
        self._update_card_position(card_id)
        card_widget.raise_()
        
        for child in card_widget.findChildren(QWidget):
            child.setMouseTracking(True)

    def _restore_drawn_cards_from_db(self):
        """Veritabanından TÜM kartları geri yükle (çekilmiş + waiting area)"""
        if not self.db:
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("SELECT card_id, target_box_id, area_index FROM waiting_area_cards")
            waiting_cards = cursor.fetchall()
            
            for card_row in waiting_cards:
                card_id, target_box_id, area_index = card_row
                
                try:
                    waiting_areas = self.scrollable_area.get_waiting_areas(target_box_id)
                    if not waiting_areas or area_index >= len(waiting_areas):
                        continue
                    
                    waiting_area = waiting_areas[area_index]
                    if not waiting_area:
                        continue
                    
                    if hasattr(waiting_area, 'cards') and card_id in waiting_area.cards:
                        continue
                    
                    card_data = self.db.get_word_by_id(card_id)
                    if not card_data:
                        continue
                    
                    if hasattr(waiting_area, '_add_dragged_card'):
                        waiting_area._add_dragged_card(card_id)
                    
                except Exception:
                    continue
            
            cursor.execute("""
                SELECT id, box FROM words 
                WHERE is_drawn = 1 AND is_copy = 1 AND box IS NOT NULL
            """)
            
            drawn_cards_db = cursor.fetchall()
            
            already_loaded = set(self.drawn_cards.keys())
            
            for card_row in drawn_cards_db:
                card_id, box_id = card_row
                
                if card_id in already_loaded:
                    continue
                
                try:
                    card_data = self.db.get_word_by_id(card_id)
                    if not card_data:
                        continue
                    
                    memory_box = None
                    
                    for box_row in self.scrollable_area.box_rows:
                        if hasattr(box_row, 'memory_box'):
                            mb = box_row['memory_box']
                        else:
                            mb = box_row.get('memory_box')
                        
                        if mb and hasattr(mb, 'box_id') and mb.box_id == box_id:
                            memory_box = mb
                            break
                    
                    if not memory_box:
                        continue
                    
                    from ui.boxes_panel.copy_flash_card.copy_flash_card_view import CopyFlashCardView
                    
                    card_widget = CopyFlashCardView(
                        data=card_data,
                        parent=None,
                        db=self.db
                    )
                    
                    card_widget.setFixedSize(260, 120)
                    card_widget.bind_model(card_data)
                    
                    memory_box.current_card_widget = card_widget
                    memory_box.is_drawing_card = False
                    
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) FROM words 
                            WHERE box = ? AND is_copy = 1 AND is_drawn = 0
                        """, (box_id,))
                        undrawn_count = cursor.fetchone()[0]
                        memory_box.btn.setEnabled(undrawn_count > 0)
                    except Exception:
                        memory_box.btn.setEnabled(True)
                    
                    self.add_drawn_card(memory_box, card_widget)
                    
                    if card_id not in self.card_original_boxes:
                        self.card_original_boxes[card_id] = box_id
                    
                except Exception:
                    continue
            
            QTimer.singleShot(100, self.update_all_counts)
            
        except Exception:
            pass

    def _cleanup_all_drawn_cards(self):
        """Tüm çekilmiş kart widget'larını temizle"""
        for card_id, card_info in list(self.drawn_cards.items()):
            card_widget = card_info['widget']
            if card_widget:
                try:
                    if card_widget.parent() and hasattr(card_widget.parent(), 'layout'):
                        layout = card_widget.parent().layout()
                        if layout:
                            layout.removeWidget(card_widget)
                    
                    card_widget.hide()
                    card_widget.setParent(None)
                    card_widget.deleteLater()
                    
                except Exception:
                    pass
        
        self.drawn_cards.clear()
        
        for box_row in self.scrollable_area.box_rows:
            if hasattr(box_row, 'memory_box'):
                box_row.memory_box.current_card_widget = None
                box_row.memory_box.update_card_count()
    
    def _update_all_card_positions(self):
        """Tüm kartların pozisyonlarını güncelle - GÜVENLİ VERSİYON"""
        invalid_cards = []
        for card_id in list(self.drawn_cards.keys()):
            card_info = self.drawn_cards[card_id]
            card_widget = card_info['widget']
            
            try:
                if not card_widget or not hasattr(card_widget, 'isVisible'):
                    invalid_cards.append(card_id)
            except RuntimeError:
                invalid_cards.append(card_id)
        
        for card_id in invalid_cards:
            if card_id in self.drawn_cards:
                del self.drawn_cards[card_id]
        
        for card_id in list(self.drawn_cards.keys()):
            self._update_card_position(card_id)
    
    def _update_card_position(self, card_id):
        """Tek bir kartın pozisyonunu güncelle"""
        if card_id not in self.drawn_cards:
            return
        
        card_info = self.drawn_cards[card_id]
        card_widget = card_info['widget']
        
        try:
            if not card_widget or not hasattr(card_widget, 'isVisible'):
                del self.drawn_cards[card_id]
                return
        except RuntimeError:
            if card_id in self.drawn_cards:
                del self.drawn_cards[card_id]
            return
        
        try:
            memory_box = card_info['box']
            box_pos = memory_box.mapTo(self, QPoint(0, 0))
            box_width = 300
            box_height = 260
            card_width = 260
            card_height = 120
            
            card_x = box_pos.x() + (box_width - card_width) // 2
            card_y = box_pos.y() + box_height + 30
            
            card_widget.move(card_x, card_y)
            card_widget.raise_()
            
            card_widget.update()
            card_widget.repaint()
            
        except RuntimeError:
            if card_id in self.drawn_cards:
                del self.drawn_cards[card_id]
        except Exception:
            try:
                memory_box = card_info['box']
                box_global_pos = memory_box.mapToGlobal(QPoint(0, 0))
                self_global_pos = self.mapToGlobal(QPoint(0, 0))
                
                box_in_self_x = box_global_pos.x() - self_global_pos.x()
                box_in_self_y = box_global_pos.y() - self_global_pos.y()
                
                card_width = 260
                box_width = 300
                box_height = 260
                
                card_x = box_in_self_x + (box_width - card_width) // 2
                card_y = box_in_self_y + box_height + 30
                
                card_widget.move(card_x, card_y)
                card_widget.raise_()
                
            except Exception:
                if card_id in self.drawn_cards:
                    del self.drawn_cards[card_id]
    
    def remove_drawn_card(self, card_id):
        """Çekilmiş kartı sistemden HEMEN kaldır"""
        if card_id in self.drawn_cards:
            card_info = self.drawn_cards[card_id]
            card_widget = card_info['widget']
            
            if card_widget:
                try:
                    card_widget.hide()
                    if card_widget.parent() and hasattr(card_widget.parent(), 'layout'):
                        layout = card_widget.parent().layout()
                        if layout:
                            layout.removeWidget(card_widget)
                    
                    card_widget.setParent(None)
                    card_widget.deleteLater()
                    
                except Exception:
                    pass
                finally:
                    del self.drawn_cards[card_id]
    
    def _on_card_dropped_to_waiting(self, word_id, target_box_id):
        """Kart bekleme alanına bırakıldığında - DÜZGÜN TEMİZLİK YAP"""
        if self.db:
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT box FROM words WHERE id = ?", (word_id,))
                result = cursor.fetchone()
                if result:
                    self.card_original_boxes[word_id] = result[0]
            except Exception:
                pass
        
        if word_id in self.drawn_cards:
            try:
                card_info = self.drawn_cards[word_id]
                card_widget = card_info['widget']
                
                if card_widget:
                    card_widget.hide()
                    card_widget.setParent(None)
                    QTimer.singleShot(100, card_widget.deleteLater)
                
                del self.drawn_cards[word_id]
                
            except Exception:
                pass
        
        for box_row in self.scrollable_area.box_rows:
            memory_box = box_row['memory_box']
            if memory_box and memory_box.current_card_widget:
                card_id = getattr(memory_box.current_card_widget, 'card_id', None)
                if card_id == word_id:
                    memory_box.current_card_widget = None
                    memory_box.is_drawing_card = False
                    memory_box.btn.setEnabled(True)
                    break
    
    def _on_transfer_button_clicked(self, box_id, area_type):
        """Bekleme alanı butonuna tıklandığında - KALICI TRANSFER"""
        waiting_areas = self.scrollable_area.get_waiting_areas(box_id)
        if not waiting_areas:
            return
        
        waiting_area = None
        target_box_id = None
        
        if area_type == "area1" and len(waiting_areas) > 0:
            waiting_area = waiting_areas[0]
            button_text = waiting_area.transfer_button.text()
            
            if "Her gün" in button_text:
                target_box_id = 1
            elif "İki günde bir" in button_text:
                target_box_id = 2
            elif "Dört günde bir" in button_text:
                target_box_id = 3
            elif "Dokuz günde bir" in button_text:
                target_box_id = 4
            elif "On dört günde bir" in button_text:
                target_box_id = 5
                
        elif area_type == "area2" and len(waiting_areas) > 1:
            waiting_area = waiting_areas[1]
            button_text = waiting_area.transfer_button.text()
            
            if "Her gün" in button_text:
                target_box_id = 1
            elif "İki günde bir" in button_text:
                target_box_id = 2
            elif "Dört günde bir" in button_text:
                target_box_id = 3
            elif "Dokuz günde bir" in button_text:
                target_box_id = 4
            elif "On dört günde bir" in button_text:
                target_box_id = 5
        
        if not waiting_area or not target_box_id:
            return
        
        cards = waiting_area.get_cards()
        
        if not cards:
            return
        
        transferred_card_ids = []
        
        for card_id in cards:
            try:
                if self.db:
                    card_info = self.db.get_word_by_id(card_id)
                    if card_info:
                        is_copy = card_info.get('is_copy', 1) == 1
                        original_card_id = card_info.get('original_card_id')
                        
                        new_bucket = 1 if area_type == "area2" else 0
                        
                        if is_copy:
                            cursor = self.db.conn.cursor()
                            
                            cursor.execute("""
                                UPDATE words 
                                SET box = ?, bucket = ?, is_drawn = 0 
                                WHERE id = ?
                            """, (target_box_id, new_bucket, card_id))
                            
                            if original_card_id:
                                cursor.execute("""
                                    UPDATE words 
                                    SET box = ?, bucket = ?
                                    WHERE id = ?
                                """, (target_box_id, new_bucket, original_card_id))
                            
                            if original_card_id:
                                cursor.execute("""
                                    UPDATE drawn_cards 
                                    SET is_active = 0 
                                    WHERE (original_card_id = ? OR copy_card_id = ?) 
                                    AND is_active = 1
                                """, (original_card_id, card_id))
                                
                                cursor.execute("""
                                    INSERT INTO drawn_cards (original_card_id, copy_card_id, box_id, is_active)
                                    VALUES (?, ?, ?, 1)
                                """, (original_card_id, card_id, target_box_id))
                            
                            self.db.conn.commit()
                            
                        else:
                            cursor = self.db.conn.cursor()
                            
                            cursor.execute("""
                                UPDATE words 
                                SET box = ?, bucket = ?, is_drawn = 0 
                                WHERE id = ?
                            """, (target_box_id, new_bucket, card_id))
                            
                            self.db.conn.commit()
                        
                        transferred_card_ids.append(card_id)
                        
                        if card_id in self.card_original_boxes:
                            del self.card_original_boxes[card_id]
                
            except Exception:
                if self.db and hasattr(self.db, 'conn'):
                    self.db.conn.rollback()
        
        waiting_area.clear_cards()
        
        self.update_all_counts()
        
        for b_id in range(1, 6):
            if b_id != box_id:
                areas = self.scrollable_area.get_waiting_areas(b_id)
                for area in areas:
                    area_cards = area.get_cards()
                    for card_id in area_cards[:]:
                        if card_id in transferred_card_ids:
                            area._remove_card_by_id(card_id, emit_signal=False)
    
    def update_all_counts(self):
        """Tüm kutuların kart sayılarını güncelle"""
        self.scrollable_area.update_all_box_counts()
    
    def clear_all_waiting_areas(self):
        """Tüm bekleme alanlarını temizle"""
        self.scrollable_area.clear_all_waiting_areas()

    def restore_cards_to_original_boxes(self):
        """ESKİ METODU GÜNCELLE: Kartları orijinal durumlarına döndürme, sadece KAYDET!"""
        self._save_drawn_cards_to_db()

    def closeEvent(self, event):
        """Pencere kapanırken - Gerçek temizlik"""
        self._save_drawn_cards_to_db()
        
        # Bu sefer gerçekten kapanıyoruz, timer'ları durdur
        self._stop_timers()
        
        if hasattr(self, 'scroll_timer'):
            self.scroll_timer.stop()
        
        super().closeEvent(event)

    def _save_drawn_cards_to_db(self):
        """Çekilmiş kartların durumunu veritabanına kaydet"""
        if not self.db:
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("UPDATE words SET is_drawn = 0 WHERE is_copy = 1")
            
            for card_id, card_info in self.drawn_cards.items():
                try:
                    memory_box = card_info['box']
                    if memory_box and hasattr(memory_box, 'box_id'):
                        cursor.execute("UPDATE words SET is_drawn = 1, box = ? WHERE id = ?", 
                                    (memory_box.box_id, card_id))
                        
                        self.card_original_boxes[card_id] = memory_box.box_id
                        
                    else:
                        cursor.execute("UPDATE words SET is_drawn = 1 WHERE id = ?", (card_id,))
                        
                except Exception:
                    pass
            
            cursor.execute("DELETE FROM waiting_area_cards")
            
            for box_id in range(1, 6):
                waiting_areas = self.scrollable_area.get_waiting_areas(box_id)
                if waiting_areas:
                    for i, waiting_area in enumerate(waiting_areas):
                        if waiting_area and hasattr(waiting_area, 'get_cards'):
                            cards = waiting_area.get_cards()
                            for card_id in cards:
                                try:
                                    cursor.execute("UPDATE words SET box = NULL WHERE id = ?", (card_id,))
                                    
                                    cursor.execute("""
                                        INSERT INTO waiting_area_cards (card_id, target_box_id, area_index)
                                        VALUES (?, ?, ?)
                                    """, (card_id, box_id, i))
                                    
                                except Exception:
                                    pass
            
            self.db.conn.commit()
            
        except Exception:
            pass

    def _cleanup_only_invalid_widgets(self):
        """Sadece geçersiz/ölü widget'ları temizle, geçerli olanları KORU"""
        invalid_cards = []
        
        for card_id, card_info in list(self.drawn_cards.items()):
            card_widget = card_info['widget']
            
            try:
                if not card_widget:
                    invalid_cards.append(card_id)
                elif not hasattr(card_widget, 'isVisible'):
                    invalid_cards.append(card_id)
                    
            except RuntimeError:
                invalid_cards.append(card_id)
            except Exception:
                pass
        
        for card_id in invalid_cards:
            if card_id in self.drawn_cards:
                try:
                    del self.drawn_cards[card_id]
                except Exception:
                    pass

    def _preserve_card_states_in_db(self):
        """Veritabanında kart durumlarını koru"""
        if not self.db:
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            for card_id in self.drawn_cards:
                try:
                    cursor.execute("SELECT is_drawn FROM words WHERE id = ?", (card_id,))
                    result = cursor.fetchone()
                    if result:
                        current_drawn = result[0]
                        if current_drawn == 0:
                            cursor.execute("UPDATE words SET is_drawn = 1 WHERE id = ?", (card_id,))
                except Exception:
                    pass
            
            for box_id in range(1, 6):
                waiting_areas = self.scrollable_area.get_waiting_areas(box_id)
                if waiting_areas:
                    for waiting_area in waiting_areas:
                        if waiting_area:
                            cards = waiting_area.get_cards()
                            for card_id in cards:
                                try:
                                    cursor.execute("UPDATE words SET box = NULL WHERE id = ?", (card_id,))
                                except Exception:
                                    pass
            
            self.db.conn.commit()
            
        except Exception:
            if self.db and hasattr(self.db, 'conn'):
                self.db.conn.rollback()