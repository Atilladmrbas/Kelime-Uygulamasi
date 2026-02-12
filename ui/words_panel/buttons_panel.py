# buttons_panel.py - GÜNCELLENMİŞ VERSİYON
from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QSizePolicy
)
from PyQt6.QtGui import QColor, QPainter, QBrush, QFont, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QTimer, QEvent
from PyQt6.QtCore import pyqtSignal


class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        self.base_width = 380
        self.base_height = 120
        self.min_width = 280
        self.min_height = 90
        
        self.setMinimumSize(self.min_width, self.min_height)
        
        self.intensity = 0.3
        self.target_intensity = 0.3
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_step)
        self.timer.start(16)
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(12)
        self.shadow.setOffset(0, 5)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(self.shadow)
        
        self.font = QFont()
        self.font.setPointSize(20)
        self.font.setWeight(QFont.Weight.Bold)
        self.setFont(self.font)
        
        self.setEnabled(False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        self.update_style()

    def set_responsive_size(self, width, height):
        self.setFixedSize(width, height)
        
        font_size = max(16, min(20, int(height * 0.17)))
        self.font.setPointSize(font_size)
        self.setFont(self.font)
        self.update()

    def animate_step(self):
        if abs(self.intensity - self.target_intensity) > 0.01:
            self.intensity += (self.target_intensity - self.intensity) * 0.25
            self.update_style()
            
            alpha = min(255, max(0, int(100 * self.intensity)))
            self.shadow.setColor(QColor(0, 0, 0, alpha))
            self.update()

    def update_style(self):
        alpha = min(255, max(0, int(255 * self.intensity)))
        current_height = self.height()
        
        border_radius = max(15, int(current_height * 0.15))
        
        if self.isEnabled():
            bg_alpha = alpha
            text_alpha = alpha
            border_alpha = min(255, int(alpha * 0.8))
            hover_bg_alpha = min(255, int(alpha * 1.15))
            hover_border_alpha = min(255, int(alpha * 0.95))
            
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 0, 0, {bg_alpha});
                    color: rgba(255, 255, 255, {text_alpha});
                    border: 2px solid rgba(0, 0, 0, {border_alpha});
                    border-radius: {border_radius}px;
                    padding: 15px 30px;
                    font-weight: bold;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 0, 0, {hover_bg_alpha});
                    border: 2px solid rgba(0, 0, 0, {hover_border_alpha});
                }}
                QPushButton:pressed {{
                    background-color: rgba(20, 20, 20, {bg_alpha});
                    border: 2px solid rgba(20, 20, 20, {bg_alpha});
                }}
            """)
        else:
            bg_alpha = min(255, int(alpha * 0.4))
            text_alpha = min(255, int(alpha * 0.6))
            
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 0, 0, {bg_alpha});
                    color: rgba(255, 255, 255, {text_alpha});
                    border: none;
                    border-radius: {border_radius}px;
                    padding: 15px 30px;
                    font-weight: bold;
                    text-align: center;
                }}
            """)

    def enterEvent(self, event):
        if self.isEnabled():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.isEnabled():
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.intensity < 0.15 or not self.isEnabled():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        ok_size = min(28, int(self.height() * 0.23))
        ok_margin = max(20, int(self.width() * 0.05))
        
        center_x = ok_margin + (ok_size // 2)
        center_y = self.height() // 2
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        
        points = [
            QPointF(center_x + (ok_size // 3), center_y - (ok_size // 3)),
            QPointF(center_x - (ok_size // 4), center_y),
            QPointF(center_x + (ok_size // 3), center_y + (ok_size // 3)),
        ]
        
        painter.drawPolygon(QPolygonF(points))

    def animate_opacity(self, target_intensity: float, enable_button: bool = False):
        self.target_intensity = min(1.0, max(0.0, target_intensity))
        self.setEnabled(enable_button)
        
        if enable_button:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)


class ButtonsPanel(QWidget):
    transfer_to_boxes_requested = pyqtSignal(list)
    switch_to_boxes_tab = pyqtSignal()
    copy_to_everyday_requested = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_boxes_count = 0
        self.selected_boxes = []

        self.btn_word = ModernButton("Sayfaya Geç", self)
        
        self.setMinimumHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(self.btn_word)
        layout.addStretch(1)

        self.btn_word.clicked.connect(self._handle_button_click)

    def _handle_button_click(self):
        if not self.btn_word.isEnabled():
            return
            
        if self.selected_boxes:
            self.copy_to_everyday_requested.emit(self.selected_boxes)
            
            self.switch_to_boxes_tab.emit()
            
            self.btn_word.setEnabled(False)
            self.btn_word.animate_opacity(0.3, enable_button=False)
            
            QTimer.singleShot(1000, self._reset_selection_and_button)
        else:
            pass

    def _reset_selection_and_button(self):
        for box in self.selected_boxes:
            if hasattr(box, 'checkbox'):
                box.checkbox.setChecked(False)
            box.is_selected = False
        
        self.btn_word.setEnabled(True)
        self.btn_word.animate_opacity(0.3, enable_button=False)
        self.selected_boxes.clear()
        self.selected_boxes_count = 0

    def _reset_button(self):
        self.btn_word.setEnabled(True)
        self.btn_word.animate_opacity(0.3, enable_button=False)
        self.selected_boxes.clear()
        self.selected_boxes_count = 0

    def update_opacity(self, selected_count: int):
        self.selected_boxes_count = selected_count
        
        if selected_count > 0:
            self.btn_word.animate_opacity(1.0, enable_button=True)
        else:
            self.btn_word.animate_opacity(0.3, enable_button=False)
    
    def update_selected_boxes(self, boxes):
        self.selected_boxes = boxes
        self.selected_boxes_count = len(boxes)
        
        if boxes:
            self.btn_word.animate_opacity(1.0, enable_button=True)
        else:
            self.btn_word.animate_opacity(0.3, enable_button=False)
    
    def set_button_size(self, width, height):
        if hasattr(self, 'btn_word'):
            self.btn_word.set_responsive_size(width, height)
            self.setMinimumHeight(height + 20)