from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QGraphicsDropShadowEffect, QFrame
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt


class FloatingToolbarUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ✅ TRANSPARENT BACKGROUND
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        # ✅ CONTAINER
        self.container = QFrame(self)
        self.container.setObjectName("toolbarContainer")
        
        # STYLESHEET - SİYAH HARFLER İÇİN GÜNCELLENDİ
        self.container.setStyleSheet("""
            QFrame#toolbarContainer {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
            QPushButton {
                background: transparent;
                border: none;
                padding: 6px;
                min-width: 26px;
                min-height: 26px;
                font-size: 13px;
                border-radius: 8px;
                color: #000000;  /* HARFLER SİYAH */
            }
            QPushButton:hover { 
                background: #f1f3f5; 
                color: #000000;  /* HOVER'DA DA SİYAH */
            }
            QPushButton[active="true"] { 
                background: #e7f5ff; 
                font-weight: bold;
                color: #000000;  /* ACTIVE'DE DE SİYAH */
            }
            QPushButton[active="true"]:hover { 
                background: #d0ebff; 
                color: #000000;  /* ACTIVE HOVER'DA DA SİYAH */
            }
        """)

        # ✅ GÜÇLÜ GÖLGE EFEKTİ
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(35)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        # LAYOUT
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # BUTONLAR - SİYAH HARFLERLE
        self.btn_b = QPushButton("B")
        self.btn_i = QPushButton("I")
        self.btn_u = QPushButton("U")
        self.btn_s = QPushButton("S")
        self.btn_color = QPushButton("🎨")  # Emoji ile daha görünür

        # BUTON STYLLERI - HARF RENKLERİNİ MANUEL AYARLA
        for b in (self.btn_b, self.btn_i, self.btn_u, self.btn_s, self.btn_color):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setMinimumSize(32, 32)
            
            # Butonun metin rengini manuel siyah yap
            b.setStyleSheet("""
                QPushButton {
                    color: #000000;
                    font-weight: normal;
                }
                QPushButton:hover {
                    color: #000000;
                }
                QPushButton:pressed {
                    color: #000000;
                }
            """)
            
            layout.addWidget(b)

        # ROOT LAYOUT
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.container)

    # ✅ PAINT EVENT'İ BASİT TUT - SİYAH KÖŞE SORUNU ÇÖZÜLDÜ
    def paintEvent(self, event):
        """Basit paint event - siyah köşeleri engelle"""
        # Sadece parent'ın paintEvent'ini çağır
        super().paintEvent(event)