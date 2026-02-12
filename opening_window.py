# opening_window.py - GÜNCELLENMİŞ
import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Root path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "ui"))

# Import main modules
from main_app_window import create_main_app_window


# ====================================================
# AÇILIŞ PENCERESİ (Dil Seçimi)
# ====================================================
class OpeningWindow(QWidget):
    """
    Dil seçimi için açılış penceresi.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kelime Uygulaması - Dil Seçimi")
        self.setFixedSize(500, 400)
        
        # Pencereyi ekranın ortasına yerleştir
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        self.setup_ui()
        self.btn_english.clicked.connect(self.open_main_app)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Logo/başlık
        title = QLabel("📚 Kelime Uygulaması")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)

        # Alt başlık
        subtitle = QLabel("Çalışmak istediğiniz dili seçin")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 16))
        subtitle.setStyleSheet("color: #7f8c8d; margin-bottom: 40px;")
        layout.addWidget(subtitle)

        # İngilizce butonu
        self.btn_english = QPushButton("🇬🇧 İngilizce")
        self.btn_english.setMinimumHeight(60)
        self.btn_english.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        self.btn_english.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c598a;
            }
        """)
        self.btn_english.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_english)

        # Boşluk
        layout.addStretch(1)

        # Footer bilgisi
        footer = QLabel("Kelime Öğrenme Uygulaması v1.0")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Segoe UI", 10))
        footer.setStyleSheet("color: #95a5a6; margin-top: 20px;")
        layout.addWidget(footer)

    def open_main_app(self):
        """Ana uygulamayı aç"""
        # Butonu geçici olarak devre dışı bırak
        self.btn_english.setEnabled(False)
        self.btn_english.setText("Açılıyor...")
        
        # Ana pencereyi oluştur ve göster
        self.main_window = create_main_app_window()
        
        # Ana pencereyi ekranın ortasına yerleştir
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.main_window.width()) // 2
        y = (screen.height() - self.main_window.height()) // 2
        self.main_window.move(x, y)
        
        self.main_window.show()
        
        # Bu pencereyi kapat
        self.close()


# ====================================================
# ANA UYGULAMA BAŞLATICI
# ====================================================
def main():
    app = QApplication(sys.argv)
    
    # Uygulama stilini ayarla
    app.setStyle("Fusion")
    
    # Global stil - TAB BAR BEYAZ VE SİYAH YAZI
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background: #ffffff;
            border-radius: 4px;
        }
        QTabBar {
            background: #ffffff;
        }
        QTabBar::tab {
            background: #ffffff;
            padding: 12px 24px;
            margin-right: 2px;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-family: 'Segoe UI';
            font-size: 14px;
            color: #333333;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            font-weight: bold;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
        }
        QTabBar::tab:hover {
            background: #f8f9fa;
        }
    """)
    
    # Açılış penceresini göster
    win = OpeningWindow()
    win.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()