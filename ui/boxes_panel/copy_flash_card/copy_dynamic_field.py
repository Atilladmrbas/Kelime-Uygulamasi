from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal


class CopyDynamicField(QLineEdit):
    """Kopya kartlar için dynamic field - SADECE OKUMA MODUNDA"""
    
    delete_requested = pyqtSignal(object)
    text_changed_signal = pyqtSignal()
    text_committed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 10))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setReadOnly(True)
        
        self.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid rgba(0,0,0,0.1);
                border-radius: 6px;
                color: #555;
                padding: 1px 2px;
                margin: 0px;
            }
        """)
        
        self.textChanged.connect(self._on_text_changed)
        
        self._original_text = ""
        self._is_modified = False
        self._last_saved_text = ""

    def _on_text_changed(self):
        current_text = self.text()
        if current_text != self._original_text:
            self._is_modified = True
            self.text_changed_signal.emit()
        else:
            self._is_modified = False

    def mouseDoubleClickEvent(self, e):
        self.selectAll()
        self.setFocus()
        super().mouseDoubleClickEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)

    def setText(self, text: str):
        super().setText(text)
        self._original_text = text
        self._last_saved_text = text
        self._is_modified = False

    def get_original_text(self):
        return self._original_text

    def get_is_modified(self):
        return self._is_modified