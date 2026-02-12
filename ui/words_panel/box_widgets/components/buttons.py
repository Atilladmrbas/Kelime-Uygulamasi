# ui/words_panel/box_widgets/components/buttons.py
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from .icons import make_trash_icon, make_arrow_icon

class DeleteButton(QPushButton):
    def __init__(self, parent=None, size=38):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setIcon(make_trash_icon())
        self.setIconSize(QSize(size - 16, size - 16))
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
                border: 1px solid #b0b0b0;
            }
        """)


class EnterButton(QPushButton):
    def __init__(self, parent=None, size=38):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setIcon(make_arrow_icon())
        self.setIconSize(QSize(size - 16, size - 16))
        
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
                border: 1px solid #b0b0b0;
            }
        """)