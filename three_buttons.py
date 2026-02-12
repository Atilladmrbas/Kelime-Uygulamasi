# three_buttons.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox, QDialog, QVBoxLayout, QRadioButton, QButtonGroup, QLabel
from PyQt6.QtCore import Qt, pyqtSignal


class ThreeButtons(QWidget):
    """Ana pencerede kullanılacak 3 butonu içeren widget"""
    
    delete_all_copy_cards = pyqtSignal()
    move_all_cards_to_selected_box = pyqtSignal(int)  # box_id parametresi
    move_all_cards_to_last_locations = pyqtSignal()
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()
    
    def _setup_ui(self):
        """UI'ı oluştur"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)
        
        # 1. Mavi Buton: Tüm Kartları Seçili Kutuya Taşı
        self.move_to_selected_box_btn = QPushButton("Tüm Kartları Seçili Kutuya Taşı")
        self.move_to_selected_box_btn.setFixedHeight(45)
        self.move_to_selected_box_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.move_to_selected_box_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 2px solid #3498db;
                border-radius: 8px;
                font-weight: 600;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: #3498db;
                padding: 0 30px;
            }
            QPushButton:hover {
                background: #3498db;
                color: white;
                border: 2px solid #2980b9;
            }
            QPushButton:pressed {
                background: #2980b9;
                color: white;
                border: 2px solid #2471a3;
            }
        """)
        self.move_to_selected_box_btn.clicked.connect(self._show_box_selection_dialog)
        
        # 2. Turuncu Buton: Tüm Kopya Kartları Sil
        self.delete_copy_cards_btn = QPushButton("Tüm Kopya Kartları Sil")
        self.delete_copy_cards_btn.setFixedHeight(45)
        self.delete_copy_cards_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_copy_cards_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 2px solid #e67e22;
                border-radius: 8px;
                font-weight: 600;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: #e67e22;
                padding: 0 30px;
            }
            QPushButton:hover {
                background: #e67e22;
                color: white;
                border: 2px solid #d35400;
            }
            QPushButton:pressed {
                background: #d35400;
                color: white;
                border: 2px solid #ba4a00;
            }
        """)
        self.delete_copy_cards_btn.clicked.connect(self._confirm_delete_all_copy_cards)
        
        # 3. Kırmızı Buton: Tüm Kartları En Sonki Yerlerine Taşı
        self.move_to_last_locations_btn = QPushButton("Tüm kartları en son ki yerlerine taşı")
        self.move_to_last_locations_btn.setFixedHeight(45)
        self.move_to_last_locations_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.move_to_last_locations_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                font-weight: 600;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: #e74c3c;
                padding: 0 30px;
            }
            QPushButton:hover {
                background: #e74c3c;
                color: white;
                border: 2px solid #c0392b;
            }
            QPushButton:pressed {
                background: #c0392b;
                color: white;
                border: 2px solid #a93226;
            }
        """)
        self.move_to_last_locations_btn.clicked.connect(self._confirm_move_to_last_locations)
        
        main_layout.addStretch()
        main_layout.addWidget(self.move_to_selected_box_btn)
        main_layout.addWidget(self.delete_copy_cards_btn)
        main_layout.addWidget(self.move_to_last_locations_btn)
        main_layout.addStretch()
    
    def _show_box_selection_dialog(self):
        """Kutu seçim dialog'unu göster"""
        if not self.db:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Kartları Taşı")
        dialog.setFixedSize(460, 420)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Ana container
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        
        # Başlık
        title_label = QLabel("Tüm kartları hangi kutuya taşımak istiyorsunuz?")
        title_label.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont;
                font-size: 18px;
                font-weight: 600;
                color: #37352f;
                padding: 0;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Açıklama
        desc_label = QLabel("Çekilmiş tüm kartlar ve bekleme alanındaki kartlar seçilen kutuya taşınacaktır.")
        desc_label.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont;
                font-size: 13px;
                color: #8a8a8a;
                padding: 0;
                line-height: 1.4;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Checkbox container
        checkbox_container = QWidget()
        checkbox_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 12px;
            }
        """)
        
        checkbox_layout = QVBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 8, 0, 8)
        checkbox_layout.setSpacing(8)
        
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        # Kutu bilgileri
        boxes_info = [
            (1, "Her gün Kutusu"),
            (2, "İki günde bir Kutusu"),
            (3, "Dört günde bir Kutusu"),
            (4, "Dokuz günde bir Kutusu"),
            (5, "On dört günde bir Kutusu")
        ]
        
        # Seçilen checkbox'ı takip etmek için
        self.selected_checkbox = None
        
        for box_id, title in boxes_info:
            # Her bir checkbox için container
            checkbox_widget = QWidget()
            checkbox_widget.setFixedHeight(56)
            checkbox_widget.setCursor(Qt.CursorShape.PointingHandCursor)
            checkbox_widget.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border-radius: 10px;
                    border: 1px solid transparent;
                }
            """)
            
            checkbox_layout_widget = QHBoxLayout(checkbox_widget)
            checkbox_layout_widget.setContentsMargins(16, 0, 16, 0)
            checkbox_layout_widget.setSpacing(16)
            
            # Notion tarzı checkbox - container
            checkbox_container_circle = QWidget()
            checkbox_container_circle.setFixedSize(22, 22)
            checkbox_container_circle.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border-radius: 4px;
                    border: 1.5px solid #d1d1d1;
                }
            """)
            
            # Checkmark için label (başlangıçta görünmez)
            checkmark_label = QLabel(checkbox_container_circle)
            checkmark_label.setFixedSize(22, 22)
            checkmark_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                }
            """)
            checkmark_label.setText("✓")
            checkmark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkmark_label.hide()
            
            # Arka plan (seçildiğinde görünecek)
            background_circle = QWidget(checkbox_container_circle)
            background_circle.setFixedSize(22, 22)
            background_circle.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border-radius: 4px;
                    border: none;
                }
            """)
            background_circle.lower()
            
            # Checkbox'ı temsil eden radio button (görünmez)
            checkbox = QRadioButton()
            checkbox.setStyleSheet("""
                QRadioButton {
                    width: 0px;
                    height: 0px;
                    opacity: 0;
                }
            """)
            checkbox.box_id = box_id
            self.button_group.addButton(checkbox, box_id)
            
            # Checkbox animasyon fonksiyonu
            def make_toggle_func(cb, background, checkmark, widget):
                def toggle_func():
                    if cb.isChecked():
                        # Arka planı mavi yap
                        background.setStyleSheet("""
                            QWidget {
                                background-color: #10b981;
                                border-radius: 4px;
                                border: none;
                            }
                        """)
                        checkmark.show()
                        
                        # Widget border'ını güncelle
                        widget.setStyleSheet("""
                            QWidget {
                                background-color: transparent;
                                border-radius: 10px;
                                border: 1px solid transparent;
                            }
                        """)
                    else:
                        # Arka planı temizle
                        background.setStyleSheet("""
                            QWidget {
                                background-color: transparent;
                                border-radius: 4px;
                                border: none;
                            }
                        """)
                        checkmark.hide()
                        
                        # Widget border'ını temizle
                        widget.setStyleSheet("""
                            QWidget {
                                background-color: transparent;
                                border-radius: 10px;
                                border: 1px solid transparent;
                            }
                        """)
                return toggle_func
            
            checkbox.toggled.connect(make_toggle_func(checkbox, background_circle, checkmark_label, checkbox_widget))
            
            # Metin label'ı
            text_label = QLabel(title)
            text_label.setStyleSheet("""
                QLabel {
                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont;
                    font-size: 15px;
                    font-weight: 400;
                    color: #37352f;
                    padding: 0;
                }
            """)
            
            # Layout'a ekle
            checkbox_layout_widget.addWidget(checkbox_container_circle)
            checkbox_layout_widget.addWidget(text_label)
            checkbox_layout_widget.addStretch()
            
            # Tüm widget'a tıklanabilirlik ekle
            def make_click_func(cb):
                def click_func(event=None):
                    cb.setChecked(True)
                    # Seçilen checkbox'ı güncelle
                    self.selected_checkbox = cb
                return click_func
            
            checkbox_widget.mousePressEvent = lambda event, cb=checkbox: make_click_func(cb)(event)
            
            # Ayrıca text label'a da tıklanabilirlik ekle
            text_label.mousePressEvent = lambda event, cb=checkbox: make_click_func(cb)(event)
            text_label.setCursor(Qt.CursorShape.PointingHandCursor)
            
            checkbox_layout.addWidget(checkbox_widget)
        
        # İlk kutuyu seçili yap
        if self.button_group.buttons():
            first_checkbox = self.button_group.buttons()[0]
            first_checkbox.setChecked(True)
            self.selected_checkbox = first_checkbox
            # İlk checkbox'ın stilini tetikle
            first_checkbox.toggled.emit(True)
        
        layout.addWidget(checkbox_container)
        layout.addStretch()
        
        # Butonlar
        button_container = QWidget()
        button_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                padding-top: 8px;
                border-top: 1px solid #f0f0f0;
            }
        """)
        
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 16, 0, 0)
        button_layout.setSpacing(12)
        
        # İptal butonu
        cancel_button = QPushButton("İptal")
        cancel_button.setFixedSize(130, 44)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                font-weight: 500;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont;
                font-size: 14px;
                color: #666666;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #f7f7f7;
                border: 1px solid #d0d0d0;
                color: #444444;
            }
            QPushButton:pressed {
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        
        # Taşı butonu
        move_button = QPushButton("Taşı")
        move_button.setFixedSize(130, 44)
        move_button.setCursor(Qt.CursorShape.PointingHandCursor)
        move_button.setStyleSheet("""
            QPushButton {
                background-color: #37352f;
                border: none;
                border-radius: 10px;
                font-weight: 500;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont;
                font-size: 14px;
                color: white;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #444444;
                border: none;
            }
            QPushButton:pressed {
                background-color: #2a2924;
                border: none;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999999;
            }
        """)
        move_button.clicked.connect(lambda: self._on_move_to_selected_box(dialog))
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(move_button)
        
        layout.addWidget(button_container)
        
        # Dialog'a container'ı ekle
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_container)
        
        dialog.exec()
    
    def _on_move_to_selected_box(self, dialog):
        """Seçili kutuya taşıma işlemini başlat"""
        selected_button = self.button_group.checkedButton()
        if selected_button:
            box_id = selected_button.box_id
            self.move_all_cards_to_selected_box.emit(box_id)
            dialog.accept()
    
    def _confirm_delete_all_copy_cards(self):
        """Tüm kopya kartları silmeyi onayla"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Tüm Kopya Kartları Sil")
        msg_box.setText("TÜM kopya kartları silmek istediğinize emin misiniz?\n\n"
                        "Sadece kopya kartlar silinecek, gerçek kartlar etkilenmeyecek.\n\n"
                        "Bu işlem geri alınamaz!")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                font-family: 'Segoe UI';
                border-radius: 8px;
            }
            QMessageBox QLabel {
                color: #333333;
                font-size: 14px;
                line-height: 1.4;
                padding: 5px;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 24px;
                min-width: 90px;
                font-size: 14px;
                font-weight: 500;
                color: #333333;
                margin: 5px;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #bbbbbb;
            }
            QMessageBox QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QMessageBox QPushButton#yesButton {
                background-color: #e67e22;
                color: white;
                border: 1px solid #d35400;
                font-weight: 600;
            }
            QMessageBox QPushButton#yesButton:hover {
                background-color: #d35400;
                border: 1px solid #c0392b;
            }
            QMessageBox QPushButton#yesButton:pressed {
                background-color: #c0392b;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_all_copy_cards.emit()
    
    def _confirm_move_to_last_locations(self):
        """En sonki yerlerine taşıma işlemini onayla"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Onay")
        msg_box.setText("Tüm kartları en son ki yerlerine taşımak istediğinize emin misiniz?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: white;
                font-family: 'Segoe UI';
            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px 20px;
                min-width: 80px;
                font-size: 13px;
                color: #000000;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
            }
            QMessageBox QPushButton:focus {
                outline: none;
                border: 2px solid #3498db;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.move_all_cards_to_last_locations.emit()
    
    def _execute_move_to_last_locations(self, boxes_window):
        """Tüm kopya kartları (is_copy=1) veritabanındaki son box değerlerine geri taşı"""
        try:
            cursor = self.db.conn.cursor()
            
            # 1. ÖNCE: drawn_cards tablosundaki AKTİF çekilmiş kopya kartları bul (TEKİLLİK)
            cursor.execute("""
                SELECT DISTINCT dc.copy_card_id, dc.box_id, dc.original_card_id
                FROM drawn_cards dc
                WHERE dc.is_active = 1
            """)
            
            active_drawn_cards = cursor.fetchall()
            
            # 2. Aktif çekilmiş kopya kartların box değerlerini ÇEKİLDİKLERİ KUTUYA AYARLA
            for copy_card_id, box_id, original_card_id in active_drawn_cards:
                if box_id:
                    cursor.execute("UPDATE words SET box = ?, is_drawn = 0 WHERE id = ?", 
                                (box_id, copy_card_id))
                else:
                    cursor.execute("SELECT box FROM words WHERE id = ?", (original_card_id,))
                    original_result = cursor.fetchone()
                    
                    if original_result and original_result[0]:
                        original_box = original_result[0]
                        cursor.execute("UPDATE words SET box = ?, is_drawn = 0 WHERE id = ?", 
                                    (original_box, copy_card_id))
            
            # 3. TÜM kopya kartların is_drawn değerini sıfırla
            cursor.execute("UPDATE words SET is_drawn = 0 WHERE is_copy = 1")
            
            # 4. drawn_cards tablosundaki TÜM AKTİF kayıtları pasif yap
            cursor.execute("UPDATE drawn_cards SET is_active = 0 WHERE is_active = 1")
            
            # 5. waiting_area_cards tablosunu temizle
            cursor.execute("DELETE FROM waiting_area_cards")
            
            # 6. Box değeri NULL olan kopya kartları düzelt
            cursor.execute("SELECT id, original_card_id FROM words WHERE is_copy = 1 AND box IS NULL")
            null_box_cards = cursor.fetchall()
            
            for card_id, original_id in null_box_cards:
                cursor.execute("""
                    SELECT box_id FROM drawn_cards 
                    WHERE copy_card_id = ? 
                    ORDER BY drawn_date DESC 
                    LIMIT 1
                """, (card_id,))
                box_result = cursor.fetchone()
                
                if box_result and box_result[0]:
                    box_value = box_result[0]
                    cursor.execute("UPDATE words SET box = ? WHERE id = ?", (box_value, card_id))
                elif original_id:
                    cursor.execute("SELECT box FROM words WHERE id = ?", (original_id,))
                    original_box_result = cursor.fetchone()
                    
                    if original_box_result and original_box_result[0]:
                        box_value = original_box_result[0]
                        cursor.execute("UPDATE words SET box = ? WHERE id = ?", (box_value, card_id))
                else:
                    cursor.execute("UPDATE words SET box = 1 WHERE id = ?", (card_id,))
            
            # 7. Kopya kartların box değerleri 1-5 arasında olmalı
            cursor.execute("SELECT id, box FROM words WHERE is_copy = 1")
            all_copy_cards = cursor.fetchall()
            
            for card_id, box_id in all_copy_cards:
                if box_id is None or box_id < 1 or box_id > 5:
                    cursor.execute("UPDATE words SET box = 1 WHERE id = ?", (card_id,))
            
            self.db.conn.commit()
            
            # 8. UI'ı güncelle
            if hasattr(boxes_window, 'clear_all_waiting_areas'):
                boxes_window.clear_all_waiting_areas()
            
            if hasattr(boxes_window, '_cleanup_all_drawn_cards'):
                boxes_window._cleanup_all_drawn_cards()
            
            if hasattr(boxes_window, 'update_all_counts'):
                boxes_window.update_all_counts()
                
        except Exception:
            if self.db and hasattr(self.db, 'conn'):
                self.db.conn.rollback()
                raise
    
    def _execute_delete_all_copy_cards(self, boxes_window):
        """Veritabanındaki TÜM kopya kartları sil"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM words WHERE is_copy = 1")
            total_copy_cards = cursor.fetchone()[0]
            
            if total_copy_cards == 0:
                return
            
            cursor.execute("DELETE FROM words WHERE is_copy = 1")
            cursor.execute("DELETE FROM waiting_area_cards")
            cursor.execute("DELETE FROM drawn_cards")
            
            self.db.conn.commit()
            
            if hasattr(boxes_window, '_cleanup_all_drawn_cards'):
                boxes_window._cleanup_all_drawn_cards()
            
            if hasattr(boxes_window, 'clear_all_waiting_areas'):
                boxes_window.clear_all_waiting_areas()
            
            if hasattr(boxes_window, 'update_all_counts'):
                boxes_window.update_all_counts()
                
        except Exception:
            if self.db and hasattr(self.db, 'conn'):
                self.db.conn.rollback()
                raise
    
    def _execute_move_to_selected_box(self, box_id, boxes_window):
        """Tüm çekilmiş ve waiting area'daki kopya kartları seçili kutuya taşı"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("UPDATE words SET box = ?, is_drawn = 0 WHERE is_copy = 1", (box_id,))
            cursor.execute("UPDATE drawn_cards SET box_id = ?, is_active = 1 WHERE is_active = 1", (box_id,))
            cursor.execute("DELETE FROM waiting_area_cards")
            
            self.db.conn.commit()
            
            if hasattr(boxes_window, '_cleanup_all_drawn_cards'):
                boxes_window._cleanup_all_drawn_cards()
            
            if hasattr(boxes_window, 'clear_all_waiting_areas'):
                boxes_window.clear_all_waiting_areas()
            
            if hasattr(boxes_window, 'update_all_counts'):
                boxes_window.update_all_counts()
                
        except Exception:
            if self.db and hasattr(self.db, 'conn'):
                self.db.conn.rollback()
                raise