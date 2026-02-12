# ui/boxes_panel/memory_boxes/memory_boxes_design_and_message_boxes.py - Tasarım ve Mesaj Kutuları
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QPushButton, QGraphicsDropShadowEffect, QMessageBox
from PyQt6.QtGui import QColor, QPainterPath, QRegion
from PyQt6.QtCore import Qt, QTimer
import random

# ✅ RENK PALETİ
BOX_BORDER_COLORS = [
    "#DADDE3",  # Box 1: Açık gri
    "#BFA2C6",  # Box 2: Lavanta
    "#7FB8CC",  # Box 3: Mavi
    "#E6D96A",  # Box 4: Sarı
    "#6FCF6C"   # Box 5: Yeşil
]

BOX_TITLES = [
    "Her gün",           # Box 1
    "İki günde bir",     # Box 2  
    "Dört günde bir",    # Box 3
    "Dokuz günde bir",   # Box 4
    "On dört günde bir"  # Box 5
]

class MemoryBoxDesign(QFrame):
    """Tek bir ezber kutusunun tasarım widget'ı"""
    
    def __init__(self, title, bg, border, box_id):
        super().__init__()
        
        self.box_id = box_id
        self.border_color = border
        self.fill_color = bg
        
        self.setFixedSize(300, 260)
        
        # ✅ NORMAL STİL
        self._normal_style = f"""
            MemoryBoxDesign {{
                background-color: {self.fill_color};
                border: 3px solid {self.border_color};
                border-radius: 12px;
                padding: 0px;
                margin: 0px;
            }}
        """
        
        self.setStyleSheet(self._normal_style)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(3)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(shadow)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(6)

        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(f"""
            QLabel {{
                background: white;
                border: 3px solid {border};
                border-radius: 6px;
                font-weight: 600;
                padding: 5px;
                font-family: 'Segoe UI';
                color: #2c3e50;
                font-size: 12px;
            }}
        """)
        self.title_lbl.setWordWrap(True)
        self.layout.addWidget(self.title_lbl)
        
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(10)
        title_shadow.setXOffset(1)
        title_shadow.setYOffset(3)
        title_shadow.setColor(QColor(0, 0, 0, 50))
        self.title_lbl.setGraphicsEffect(title_shadow)

        self.count_lbl = QLabel("0")
        self.count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_lbl.setMinimumHeight(40)
        self.count_lbl.setStyleSheet("""
            QLabel {
                border: none;
                font-weight: 700;
                font-family: 'Segoe UI';
                color: #333333;
                font-size: 28px;
            }
        """)
        self.layout.addWidget(self.count_lbl)

        self.layout.addStretch(1)

        self.btn = QPushButton("Kart çek")
        self.btn.setMinimumHeight(30)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {self.border_color};
                border-radius: 6px;
                font-weight: 600;
                font-family: 'Segoe UI';
                font-size: 12px;
                color: #2c3e50;
            }}
            QPushButton:hover {{
                background: #27ae60;
                color: white;
                border: 2px solid #229954;
            }}
            QPushButton:pressed {{
                background: #229954;
                color: white;
                border: 2px solid #1e8449;
            }}
        """)
        
        self.layout.addWidget(self.btn)
        
        self.reset_btn = QPushButton(f"Kutuyu Sıfırla")
        self.reset_btn.setMinimumHeight(30)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid #e74c3c;
                border-radius: 6px;
                font-weight: 600;
                font-family: 'Segoe UI';
                font-size: 12px;
                color: #e74c3c;
            }}
            QPushButton:hover {{
                background: #e74c3c;
                color: white;
                border: 2px solid #c0392b;
            }}
            QPushButton:pressed {{
                background: #c0392b;
                color: white;
                border: 2px solid #a93226;
            }}
        """)
        self.layout.addWidget(self.reset_btn)
        
        # Kart çekme durumu için flag
        self.is_drawing_card = False
        
        # SAYACI HEMEN GÜNCELLE
        QTimer.singleShot(50, self._immediate_count_update)
        
    def paintEvent(self, event):
        """Widget'ı yuvarlak köşeli yapmak için"""
        super().paintEvent(event)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        region = QRegion()
        region += QRegion(path.toFillPolygon().toPolygon())
        
        self.setMask(region)
        
        if not self.graphicsEffect():
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(2)
            shadow.setYOffset(4)
            shadow.setColor(QColor(0, 0, 0, 60))
            self.setGraphicsEffect(shadow)

    def _immediate_count_update(self):
        """SAYAÇ GÜNCELLEMESİNİ HEMEN YAP"""
        QTimer.singleShot(0, self.update_card_count)
        
    def update_card_count(self):
        """Kutudaki ÇEKİLMEMİŞ kopya kart sayısını göster"""
        # Bu metod memory_box.py'de implemente edilecek
        pass

    def show_card_immediately(self):
        """Kutudan rasgele bir KOPYA kart çek"""
        # Bu metod memory_box.py'de implemente edilecek
        pass

    def reset_box_confirm(self):
        """Kutuyu sıfırlamadan önce onay iste"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Kutuyu Sıfırla")
        msg.setText("Bu kutudaki tüm kopya kartları silmek istediğinize emin misiniz?\n\n"
                    "(bu kutunun altında çektiğiniz kart da silinir)")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
                font-family: 'Segoe UI';
            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 13px;
                line-height: 1.4;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 15px;
                color: #000000;
                font-weight: 500;
                min-width: 70px;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
            }
            QMessageBox QPushButton#qt_msgbox_yesbutton {
                background-color: #ffebee;
                color: #d32f2f;
                border: 1px solid #ffcdd2;
            }
            QMessageBox QPushButton#qt_msgbox_yesbutton:hover {
                background-color: #ffcdd2;
            }
            QMessageBox QPushButton#qt_msgbox_nobutton {
                background-color: #e8f5e9;
                color: #388e3c;
                border: 1px solid #c8e6c9;
            }
            QMessageBox QPushButton#qt_msgbox_nobutton:hover {
                background-color: #c8e6c9;
            }
        """)
        
        result = msg.exec()
        if result == QMessageBox.StandardButton.Yes:
            self.reset_box()
            
    def reset_box(self):
        """Kutudaki tüm KOPYA kartları sil"""
        # Bu metod memory_box.py'de implemente edilecek
        pass