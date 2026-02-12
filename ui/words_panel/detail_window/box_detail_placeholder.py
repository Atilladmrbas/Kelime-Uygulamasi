# ui/words_panel/detail_window/box_detail_placeholder.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor


class BoxDetailPlaceholder(QWidget):
    """BoxDetailWindow için loading placeholder"""
    
    # Sinyaller
    fade_out_completed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.opacity_animation = None
        self.current_opacity = 1.0
        self.setup_ui()
        
    def setup_ui(self):
        # Ana container - yarı saydam
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Ana layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Yükleniyor label'ı
        self.loading_label = QLabel("Kartlar Yükleniyor")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #4b5563;
                font-size: 16px;
                font-weight: 500;
                padding: 0;
                margin: 0;
                background-color: transparent;
            }
        """)
        
        # Font ayarla
        font = QFont()
        font.setFamily("Segoe UI" if hasattr(QFont, 'Segoe UI') else "Arial")
        font.setWeight(QFont.Weight.Medium)
        self.loading_label.setFont(font)
        
        layout.addWidget(self.loading_label)
        
        # Başlangıçta tamamen saydam
        self.setWindowOpacity(0.0)
    
    def set_opacity(self, opacity):
        """Widget ve label opaklığını ayarla"""
        self.current_opacity = opacity
        self.setWindowOpacity(opacity)
        
        # Label'ın opaklığını da ayarla
        label_opacity = opacity
        color = f"rgba(75, 85, 99, {label_opacity})"
        
        self.loading_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: 500;
                padding: 0;
                margin: 0;
                background-color: transparent;
            }}
        """)
    
    def show_animated(self, duration=300):
        """Animasyonlu göster - yumuşak fade-in"""
        self.show()
        self.raise_()
        
        if self.opacity_animation:
            self.opacity_animation.stop()
        
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(duration)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        
        # Opaklık değişimini takip et
        def on_value_changed(value):
            self.set_opacity(value)
        
        self.opacity_animation.valueChanged.connect(on_value_changed)
        self.opacity_animation.start()
    
    def hide_animated(self, duration=500):
        """Animasyonlu gizle - yumuşak fade-out"""
        if self.opacity_animation:
            self.opacity_animation.stop()
        
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(duration)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Mevcut opaklıktan başla
        self.opacity_animation.setStartValue(self.current_opacity)
        self.opacity_animation.setEndValue(0.0)
        
        # Opaklık değişimini takip et
        def on_value_changed(value):
            self.set_opacity(value)
        
        def on_finished():
            self.hide()
            self.opacity_animation = None
            self.fade_out_completed.emit()
        
        self.opacity_animation.valueChanged.connect(on_value_changed)
        self.opacity_animation.finished.connect(on_finished)
        self.opacity_animation.start()
    
    def hide_immediate(self):
        """Hemen gizle"""
        if self.opacity_animation:
            self.opacity_animation.stop()
            self.opacity_animation = None
        self.set_opacity(0.0)
        self.hide()
    
    def resize_to_parent(self):
        """Parent boyutuna göre resize et"""
        if self.parent():
            self.setGeometry(self.parent().rect())
    
    def paintEvent(self, event):
        """Özel boyama - yumuşak beyaz arkaplan"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Opaklığa göre arkaplan rengi
        bg_color = QColor(255, 255, 255, int(self.current_opacity * 245))
        painter.fillRect(self.rect(), bg_color)
        
        super().paintEvent(event)