from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt


class CopyDragHandleIcon(QWidget):
    """Kopya kartlar için drag handle ikonu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        brush_color = QColor(0, 0, 0, 220)
        painter.setBrush(brush_color)
        
        r, gap, start = 2.2, 6, 4
        for row in range(3):
            for col in range(3):
                x, y = start + col * gap, start + row * gap
                painter.drawEllipse(int(x), int(y), int(r * 2), int(r * 2))
        
        painter.end()