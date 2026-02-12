# ui/words_panel/box_widgets/components/selection.py
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF, QTime
from PyQt6.QtWidgets import QCheckBox

class NotionCheckBox(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self._is_pressed = False
        self._last_click_time = QTime.currentTime()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        
        is_hover = self.underMouse()
        is_checked = self.isChecked()
        
        if is_checked:
            bg_color = QColor(59, 130, 246)
            border_color = QColor(37, 99, 235)
        elif is_hover:
            bg_color = QColor(240, 240, 240)
            border_color = QColor(200, 200, 200)
        else:
            bg_color = QColor(248, 249, 250)
            border_color = QColor(224, 224, 224)
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
        
        if is_checked:
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            points = [
                QPointF(center.x() - 6, center.y()),
                QPointF(center.x() - 2, center.y() + 4),
                QPointF(center.x() + 6, center.y() - 4)
            ]
            
            painter.drawPolyline(points)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            current_time = QTime.currentTime()
            
            if self._last_click_time.msecsTo(current_time) > 200:
                new_state = not self.isChecked()
                self.setChecked(new_state)
                
                if new_state:
                    self.stateChanged.emit(Qt.CheckState.Checked.value)
                else:
                    self.stateChanged.emit(Qt.CheckState.Unchecked.value)
                
                self._last_click_time = current_time
                self.update()
            
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._is_pressed = False
        super().mouseReleaseEvent(event)