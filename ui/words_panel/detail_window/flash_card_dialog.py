"""
FlashCardView için dialog'lar - GLOBAL ÇİFT DUPLICATE kontrolü
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, 
    QWidget, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal


class GlobalPairDuplicateDialog(QDialog):
    """
    Global çift duplicate uyarı dialog'u
    SADE ve TEMİZ TASARIM
    """
    
    def __init__(self, duplicate_info, parent=None):
        super().__init__(parent)
        self.duplicate_info = duplicate_info
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Aynı Çift Bulundu")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # ÜST BÖLÜM - Ana bilgi
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                padding: 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        
        # Uyarı başlığı
        title_label = QLabel("⚠️ Bu çift zaten mevcut")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 700;
                color: #d97706;
                padding: 0;
                margin: 0;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Kelime çifti
        front, back = self.duplicate_info.get('word_pair', ('', ''))
        pair_label = QLabel(f"<span style='color: #202020; font-size: 16px; font-weight: 600;'>{front}</span> <span style='color: #64748b;'>→</span> <span style='color: #202020; font-size: 16px; font-weight: 600;'>{back}</span>")
        pair_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                background-color: #f8f9fa;
                border-radius: 6px;
                border: 1px solid #f1f5f9;
            }
        """)
        pair_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(pair_label)
        
        # Özet bilgisi
        summary = self._create_summary()
        if summary:
            summary_label = QLabel(summary)
            summary_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #64748b;
                    padding: 8px 0;
                    font-weight: 500;
                }
            """)
            summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(summary_label)
        
        main_layout.addWidget(header_frame)
        
        # ORTA BÖLÜM - Detaylar (SADECE KELİME KUTULARI)
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0)
        
        # Detaylar başlığı
        total_count = self.duplicate_info.get('total_count', 0)
        details_header = QLabel(f"Bulunduğu kelime kutuları: {total_count} adet")
        details_header.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 600;
                color: #374151;
                padding: 16px 20px;
                border-bottom: 1px solid #f1f5f9;
                background-color: #f8fafc;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        details_layout.addWidget(details_header)
        
        # SCROLL AREA - YATAY SCROLL KAPALI
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
        """)
        
        # Scroll içeriği
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 16, 20, 20)
        scroll_layout.setSpacing(12)
        
        found_locations = self.duplicate_info.get('found_locations', [])
        
        # Box'lara göre grupla - TEKİLLEŞTİR ve SADECE KELİME KUTULARI
        box_groups = {}
        unique_cards = set()
        
        for location in found_locations:
            card_id = location.get('card_id')
            if card_id in unique_cards:
                continue
                
            unique_cards.add(card_id)
            
            box_id = location.get('box_id', 0)
            box_title = location.get('box_title', f'Kutu {box_id}')
            
            # EZBER KUTULARINI FİLTRELE (Box ID 100'den büyük olanlar ezber kutusudur)
            if box_id >= 100:
                continue
                
            if box_title not in box_groups:
                box_groups[box_title] = {'unknown': 0, 'learned': 0}
            
            container_type = location.get('container', 'unknown')
            if container_type == 'unknown':
                box_groups[box_title]['unknown'] += 1
            else:
                box_groups[box_title]['learned'] += 1
        
        # Her box için bir satır göster
        for box_title, counts in box_groups.items():
            box_row = self._create_box_row(box_title, counts)
            scroll_layout.addWidget(box_row)
        
        # Eğer hiç kelime kutusu yoksa mesaj göster
        if not box_groups:
            no_data_label = QLabel("Sadece kelime kutuları gösteriliyor (ezber kutuları hariç)")
            no_data_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #94a3b8;
                    font-style: italic;
                    padding: 20px;
                    text-align: center;
                }
            """)
            scroll_layout.addWidget(no_data_label)
        
        # Eğer çok fazla varsa boşluk ekle
        if len(box_groups) > 8:
            scroll_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        scroll_area.setWidget(scroll_content)
        details_layout.addWidget(scroll_area, 1)
        
        main_layout.addWidget(details_frame, 1)
        
        # ALT BÖLÜM - Buton
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding-top: 8px;
            }
        """)
        
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        ok_button = QPushButton("Tamam")
        ok_button.setFixedSize(120, 40)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
                padding-top: 2px;
            }
        """)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        main_layout.addWidget(button_frame)
        
        ok_button.setDefault(True)
        ok_button.setAutoDefault(True)
    
    def _create_summary(self):
        """Özet bilgisini oluştur"""
        found_locations = self.duplicate_info.get('found_locations', [])
        
        if not found_locations:
            return ""
        
        # Box sayısı - SADECE KELİME KUTULARI
        box_ids = set()
        for loc in found_locations:
            box_id = loc.get('box_id', 0)
            if box_id >= 100:  # Ezber kutularını atla
                continue
            box_ids.add(box_id)
        
        box_count = len(box_ids)
        
        # Container sayıları - TEKİLLEŞTİR ve SADECE KELİME KUTULARI
        unique_cards = set()
        unknown_count = 0
        learned_count = 0
        
        for loc in found_locations:
            box_id = loc.get('box_id', 0)
            if box_id >= 100:  # Ezber kutularını atla
                continue
                
            card_id = loc.get('card_id')
            if card_id in unique_cards:
                continue
            unique_cards.add(card_id)
            
            if loc.get('container') == 'unknown':
                unknown_count += 1
            else:
                learned_count += 1
        
        parts = []
        if box_count > 0:
            parts.append(f"{box_count} kelime kutusunda")
        
        if unknown_count > 0:
            parts.append(f"{unknown_count} bilmediklerim")
        
        if learned_count > 0:
            parts.append(f"{learned_count} öğrendiklerim")
        
        return " • ".join(parts)
    
    def _create_box_row(self, box_title: str, counts: dict) -> QWidget:
        """Her box için bir satır oluştur"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #f1f5f9;
                border-radius: 8px;
                padding: 14px 16px;
            }
            /* HOVER EFEKTİ KALDIRILDI */
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Box adı
        title_label = QLabel(box_title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #202020;
            }
        """)
        layout.addWidget(title_label, 1)
        
        # Container istatistikleri
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(12)
        
        # Bilmediklerim ve Öğrendiklerim - İKİSİ DE AYNI AÇIK GRİ RENK, İÇ BORDER YOK
        container_color = "#64748b"  # Açık gri renk
        
        if counts.get('unknown', 0) > 0:
            unknown_widget = self._create_stat_widget("Bilmediklerim", counts['unknown'], container_color)
            stats_layout.addWidget(unknown_widget)
        
        if counts.get('learned', 0) > 0:
            learned_widget = self._create_stat_widget("Öğrendiklerim", counts['learned'], container_color)
            stats_layout.addWidget(learned_widget)
        
        layout.addWidget(stats_widget, 0, Qt.AlignmentFlag.AlignRight)
        
        return widget
    
    def _create_stat_widget(self, label: str, count: int, color: str) -> QFrame:
        """İstatistik widget'ı oluştur - İÇ BORDER YOK, SADECE METİN"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;  /* İÇ BORDER KALDIRILDI */
                padding: 0;
            }}
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Etiket ve sayı - SADECE METİN, BORDER YOK
        text_label = QLabel(f"{label}: {count}")
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(text_label)
        
        return widget


class CopyCardWarningDialog(QDialog):
    """Kopya kartlar için onay dialog'u - YENİ TASARIM: SADECE METİN, ORTALI"""
    
    def __init__(self, copy_cards_in_boxes, parent=None):
        super().__init__(parent)
        self.copy_cards_in_boxes = copy_cards_in_boxes
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Kopya Kart Uyarısı")
        self.setFixedSize(450, 240)
        
        # Tüm dialog için arka plan rengi
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                border: none !important;
                padding: 0 !important;
                margin: 0 !important;
                background-color: transparent !important;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Başlık - SİYAH ve ORTALI, TAMAMEN BORDER YOK
        title_label = QLabel("⚠️ Kopya Kart Bulundu")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 700;
                color: #000000;
                text-align: center;
                border: none;
                padding: 0;
                margin: 0;
                background-color: transparent;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # İçerik - SADECE METİNLER, BORDER YOK
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: none;
                padding: 0;
            }
        """)
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        
        total_copies = sum(len(cards) for cards in self.copy_cards_in_boxes.values())
        
        # Ana mesaj
        main_label = QLabel(f"Bu kartın <b>{total_copies}</b> adet kopyası bulunuyor.")
        main_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #000000;
                font-weight: 500;
                text-align: center;
                border: none;
                padding: 8px 0;
                background-color: transparent;
            }
        """)
        main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(main_label)
        
        # Uyarı mesajı
        warning_label = QLabel("Bu kartı öğrendiklerim'e taşırsanız, kopyası silinecektir.")
        warning_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #000000;
                font-weight: 600;
                text-align: center;
                border: none;
                padding: 8px 0;
                background-color: transparent;
            }
        """)
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(warning_label)
        
        layout.addWidget(content_frame, 1)
        
        # Butonlar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_button = QPushButton("İptal")
        cancel_button.setFixedSize(100, 36)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #64748b;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
            QPushButton:pressed {
                background-color: #cbd5e1;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        ok_button = QPushButton("Taşı ve Sil")
        ok_button.setFixedSize(120, 36)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        ok_button.setDefault(True)


class SimpleMessageDialog(QDialog):
    """Basit mesaj dialog'u"""
    
    def __init__(self, title, message, button_text="Tamam", parent=None):
        super().__init__(parent)
        self.title = title
        self.message = message
        self.button_text = button_text
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(self.title)
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Mesaj
        message_label = QLabel(self.message)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #374151;
                padding: 20px;
                background-color: #f8fafc;
                border-radius: 8px;
                border: 1px solid #f1f5f9;
                qproperty-wordWrap: true;
                font-weight: 500;
            }
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label, 1)
        
        # Buton
        ok_button = QPushButton(self.button_text)
        ok_button.setFixedSize(100, 36)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        ok_button.clicked.connect(self.accept)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        ok_button.setDefault(True)