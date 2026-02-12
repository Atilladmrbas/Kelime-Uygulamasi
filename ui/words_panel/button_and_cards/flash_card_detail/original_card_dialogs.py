"""
original_card_dialogs.py
Gerçek (orijinal) kartlar için dialog pencereleri
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor


class OriginalCardConfirmDialog(QDialog):
    """Öğrendiklerime taşıma onay dialog'u (sadece orijinal kartlar)"""
    
    confirmed = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, card_data=None, copy_count=0):
        super().__init__(parent)
        
        self.card_data = card_data
        self.copy_count = copy_count
        
        self.setWindowTitle("Kart Taşıma")
        self.setModal(True)
        self.setFixedSize(450, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 2px solid #333333;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Mesaj oluştur
        message = self._create_message()
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #222222;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(message_label)
        
        # Butonlar
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        self.yes_btn = QPushButton("Evet, Taşı")
        self.no_btn = QPushButton("Hayır, Vazgeç")
        
        self._setup_buttons()
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.yes_btn)
        button_layout.addWidget(self.no_btn)
        button_layout.addStretch(1)
        
        layout.addWidget(button_container)
        
        # Bağlantılar
        self.yes_btn.clicked.connect(self._on_yes_clicked)
        self.no_btn.clicked.connect(self._on_no_clicked)
        
        # Focus ayarları
        self.yes_btn.setAutoDefault(True)
        self.no_btn.setAutoDefault(False)
    
    def _create_message(self):
        """Dialog mesajını oluştur"""
        english_texts = [self.card_data.get('english', '')] if self.card_data.get('english') else []
        turkish_texts = [self.card_data.get('turkish', '')] if self.card_data.get('turkish') else []
        
        english_display = english_texts[0] if english_texts else "(boş)"
        turkish_display = turkish_texts[0] if turkish_texts else "(boş)"
        
        message = "Bu kartı 'öğrendiklerim' bölümüne taşımak istiyor musunuz?\n\n"
        
        if self.copy_count > 0:
            message += f"<b>UYARI:</b> Bu kartın <b>{self.copy_count}</b> adet kopyası var. "
            message += "Kopyalar otomatik olarak silinecek.\n\n"
        
        message += "Kart içeriği:\n"
        message += f"<b>İngilizce:</b> {english_display}\n"
        message += f"<b>Türkçe:</b> {turkish_display}"
        
        return message
    
    def _setup_buttons(self):
        """Butonları ayarla"""
        self.yes_btn.setFixedSize(100, 35)
        self.yes_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: white;
                border: 1px solid #000000;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #333333;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        
        self.no_btn.setFixedSize(100, 35)
        self.no_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.no_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #000000;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
    
    def _on_yes_clicked(self):
        """Evet butonuna tıklandığında"""
        self.confirmed.emit()
        self.accept()
    
    def _on_no_clicked(self):
        """Hayır butonuna tıklandığında"""
        self.cancelled.emit()
        self.reject()


class OriginalCardDeleteDialog(QDialog):
    """Gerçek kart silme onay dialog'u"""
    
    confirmed = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, card_data=None, copy_count=0):
        super().__init__(parent)
        
        self.card_data = card_data
        self.copy_count = copy_count
        
        self.setWindowTitle("Kart Silme")
        self.setModal(True)
        self.setFixedSize(450, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 2px solid #333333;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Mesaj oluştur
        message = self._create_message()
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #222222;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(message_label)
        
        # Butonlar
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        self.yes_btn = QPushButton("Evet, Sil")
        self.no_btn = QPushButton("Hayır, Vazgeç")
        
        self._setup_buttons()
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.yes_btn)
        button_layout.addWidget(self.no_btn)
        button_layout.addStretch(1)
        
        layout.addWidget(button_container)
        
        # Bağlantılar
        self.yes_btn.clicked.connect(self._on_yes_clicked)
        self.no_btn.clicked.connect(self._on_no_clicked)
        
        # Focus ayarları
        self.yes_btn.setAutoDefault(True)
        self.no_btn.setAutoDefault(False)
    
    def _create_message(self):
        """Dialog mesajını oluştur"""
        front_texts = self.card_data.get('front_texts', [])
        back_texts = self.card_data.get('back_texts', [])
        
        english_texts = [t for t in front_texts if t]
        turkish_texts = [t for t in back_texts if t]
        
        english_display = english_texts[0] if english_texts else "(boş)"
        turkish_display = turkish_texts[0] if turkish_texts else "(boş)"
        
        message = "Bu kartı silerseniz bubble ile birlikte "
        
        if self.copy_count > 0:
            message += "kopyalarıyla beraber "
        
        message += "kalıcı olarak silinecek.\n\n"
        message += "Kart içeriği:\n"
        message += f"<b>İngilizce:</b> {english_display}\n"
        message += f"<b>Türkçe:</b> {turkish_display}"
        
        if self.copy_count > 0:
            message += f"\n\nBu kartın <b>{self.copy_count}</b> adet kopyası bulunuyor."
        
        return message
    
    def _setup_buttons(self):
        """Butonları ayarla"""
        self.yes_btn.setFixedSize(100, 35)
        self.yes_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: white;
                border: 1px solid #000000;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #333333;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        
        self.no_btn.setFixedSize(100, 35)
        self.no_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.no_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #000000;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
    
    def _on_yes_clicked(self):
        """Evet butonuna tıklandığında"""
        self.confirmed.emit()
        self.accept()
    
    def _on_no_clicked(self):
        """Hayır butonuna tıklandığında"""
        self.cancelled.emit()
        self.reject()


# Helper fonksiyonlar
def show_original_card_confirm_dialog(parent, card_data, copy_count=0):
    """Öğrendiklerime taşıma dialog'u göster"""
    dialog = OriginalCardConfirmDialog(parent, card_data, copy_count)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted

def show_original_card_delete_dialog(parent, card_data, copy_count=0):
    """Silme dialog'u göster"""
    dialog = OriginalCardDeleteDialog(parent, card_data, copy_count)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted