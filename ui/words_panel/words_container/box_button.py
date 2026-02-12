from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QPainter, QPen, QColor


class AddBoxButton(QFrame):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.base_w = 270
        self.base_h = 230

        # Hover state
        self.hover = False

        # Animation values
        self.intensity = 0.0      # 0 = transparan, 1 = tam görünür
        self.scale = 1.0          # 1.0 = normal, 1.08 = max büyüme

        # Target values
        self.target_intensity = 0.0
        self.target_scale = 1.0

        # Animation update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_step)
        self.timer.start(16)  # ~60 FPS

        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Label
        self.label = QLabel("Yeni Kutu", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))

    # ------------------ HOVER ------------------
    def enterEvent(self, event):
        self.hover = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.target_intensity = 1.0   # görünür olsun
        self.target_scale = 1.08      # yumuşak büyüme

        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover = False
        self.unsetCursor()

        self.target_intensity = 0.0   # transparan olsun
        self.target_scale = 1.0       # anında küçülsün

        super().leaveEvent(event)

    # ------------------ ANIMATION ENGINE ------------------
    def animate_step(self):
        """Her frame'de intensity ve scale değerlerini hedefe doğru yaklaştırır."""
        changed = False

        # Fade
        if abs(self.intensity - self.target_intensity) > 0.01:
            self.intensity += (self.target_intensity - self.intensity) * 0.25
            changed = True
        else:
            self.intensity = self.target_intensity

        # Hover büyüme
        if abs(self.scale - self.target_scale) > 0.01:
            self.scale += (self.target_scale - self.scale) * 0.2
            changed = True
        else:
            self.scale = self.target_scale

        if changed:
            self.update()

    # ------------------ PAINT ------------------
    def paintEvent(self, event):
        super().paintEvent(event)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Scale uygulaması
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(self.scale, self.scale)
        p.translate(-self.width() / 2, -self.height() / 2)

        # Sabit alpha değerleri - HER ZAMAN GÖRÜNÜR OLSUN
        min_alpha = 180      # Normal halde %70 görünürlük (arttırıldı)
        max_alpha = 255     # hover'da tamamen canlı
        alpha = int(min_alpha + (max_alpha - min_alpha) * self.intensity)

        color = QColor(90, 90, 90, alpha)
        pen = QPen(color, 4)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)

        w, h = self.width(), self.height()
        margin = 12
        ox = margin
        oy = margin
        w2 = w - margin
        h2 = h - margin

        # Köşe yarıçapı ve çizgi uzunluğunu SABİT oranlarda hesapla
        # Bu sayede tüm boyutlarda aynı görünür
        min_dimension = min(w, h)
        r = int(min_dimension * 0.16)  # Köşe yarıçapı
        L = int(min_dimension * 0.22)  # Çizgi uzunluğu
        
        # Minimum değerleri koru
        r = max(r, 20)  # Köşe en az 20px
        L = max(L, 25)  # Çizgi en az 25px

        # SOL ÜST
        p.drawArc(ox, oy, r, r, 90 * 16, 90 * 16)
        p.drawLine(ox + r // 2, oy, ox + r // 2 + L, oy)
        p.drawLine(ox, oy + r // 2, ox, oy + r // 2 + L)

        # SAĞ ÜST
        p.drawArc(w2 - r, oy, r, r, 0, 90 * 16)
        p.drawLine(w2 - r // 2 - L, oy, w2 - r // 2, oy)
        p.drawLine(w2, oy + r // 2, w2, oy + r // 2 + L)

        # SOL ALT
        p.drawArc(ox, h2 - r, r, r, 180 * 16, 90 * 16)
        p.drawLine(ox, h2 - r // 2 - L, ox, h2 - r // 2)
        p.drawLine(ox + r // 2, h2, ox + r // 2 + L, h2)

        # SAĞ ALT
        p.drawArc(w2 - r, h2 - r, r, r, 270 * 16, 90 * 16)
        p.drawLine(w2 - r // 2 - L, h2, w2 - r // 2, h2)
        p.drawLine(w2, h2 - r // 2 - L, w2, h2 - r // 2)

        # Yazı da aynı alpha mantıkla fade olsun ama DAHA GÖRÜNÜR
        text_alpha = int(160 + (255 - 160) * self.intensity)  # Daha yüksek minimum alpha
        self.label.setStyleSheet(
            f"color: rgba(70,70,70,{text_alpha}); font-weight: 600;"
        )

    # ------------------ LABEL ------------------
    def resizeEvent(self, event):
        self.label.setGeometry(0, 0, self.width(), self.height())
        
        # Font boyutunu responsive yap ama minimum bir değer koru
        font_size = max(18, int(min(self.width(), self.height()) * 0.08))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        self.label.setFont(font)
        
        super().resizeEvent(event)

    def sizeHint(self):
        return QSize(self.base_w, self.base_h)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def _is_widget_valid(self):
        """Widget'ın hala geçerli olup olmadığını kontrol et"""
        try:
            return hasattr(self, 'isWidgetType') and self.isWidgetType()
        except RuntimeError:
            return False