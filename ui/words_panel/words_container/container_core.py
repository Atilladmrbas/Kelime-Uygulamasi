from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QSizePolicy
from PyQt6.QtCore import Qt, QTimer


class WordsContainerCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background: #f7f7f7;
                border-radius: 22px;
            }
        """)

        # SABİT 6 SÜTUN
        self.columns = 6
        
        self.min_box_w = 160
        self.max_box_w = 270
        self.min_box_h = 120
        self.max_box_h = 230

        self.min_spacing = 15
        self.max_spacing = 50  # DAHA FAZLA: 40 -> 50
        
        # Debouncing için timer
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._delayed_resize)
        self._pending_resize = False

        # ANA LAYOUT - TAM GENİŞLİK
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # GRID LAYOUT - DOĞRUDAN, CONTAINER YOK
        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.grid.setContentsMargins(20, 8, 20, 15)
        self.grid.setHorizontalSpacing(self.min_spacing)
        self.grid.setVerticalSpacing(self.min_spacing)
        
        self.main_layout.addLayout(self.grid, stretch=1)

        self._initial = False
        QTimer.singleShot(0, self._initial_layout)


    def _initial_layout(self):
        if hasattr(self, "rearrange"):
            self.rearrange()
        self._initial = True


    def compute_responsive(self):
        container_w = self.width()
        margins = self.grid.contentsMargins()
        usable_w = container_w - margins.left() - margins.right()

        # SABİT 6 SÜTUN
        cols = self.columns
        
        # Kutu genişliğini hesapla
        base_box_w = usable_w // cols
        
        # Minimum ve maksimum arasında kal
        box_w = min(self.max_box_w, max(self.min_box_w, base_box_w))
        
        # Kalan boşluğu spacing olarak dağıt
        total_boxes_w = box_w * cols
        remaining_space = usable_w - total_boxes_w
        
        if remaining_space > 0:
            # Mevcut boşluğu spacing olarak dağıt
            max_possible_spacing = remaining_space // (cols - 1) if cols > 1 else 0
            
            # EKRAN BOYUTUNA GÖRE SPACING AYARLA
            if container_w > 1800:  # ÇOK BÜYÜK EKRAN
                # Maksimum spacing kullan
                spacing = min(self.max_spacing, max_possible_spacing)
                spacing = max(35, spacing)  # Minimum 35px
            elif container_w > 1400:  # BÜYÜK EKRAN
                # Orta seviye spacing
                spacing = min(self.max_spacing - 10, max_possible_spacing)
                spacing = max(30, spacing)  # Minimum 30px
            elif container_w > 1000:  # ORTA BOY EKRAN
                # Normal spacing
                spacing = min(self.max_spacing - 15, max_possible_spacing)
                spacing = max(25, spacing)  # Minimum 25px
            else:  # KÜÇÜK EKRAN
                # Minimum spacing
                spacing = min(self.max_spacing - 20, max_possible_spacing)
                spacing = max(self.min_spacing, spacing)  # Minimum 15px
            
            # Spacing ayarlandıktan sonra hala boşluk varsa
            used_space = total_boxes_w + (spacing * (cols - 1))
            extra_space = usable_w - used_space
            
            if extra_space > 0 and box_w < self.max_box_w:
                # Ekstra boşluğu kutulara ekle
                extra_per_box = extra_space // cols
                box_w += extra_per_box
                box_w = min(box_w, self.max_box_w)
        else:
            # Yeterli alan yoksa minimum spacing
            spacing = self.min_spacing
        
        # Kutu yüksekliğini hesapla
        width_range = self.max_box_w - self.min_box_w
        h_ratio = (box_w - self.min_box_w) / max(width_range, 1)
        box_h = int(self.min_box_h + (self.max_box_h - self.min_box_h) * h_ratio)

        return box_w, box_h, spacing


    def rearrange_grid(self, boxes):
        box_w, box_h, spacing = self.compute_responsive()

        self.grid.setHorizontalSpacing(spacing)
        self.grid.setVerticalSpacing(spacing)

        # Mevcut widget'ları temizle
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                if not hasattr(widget, 'db_id') and not hasattr(widget, 'clicked'):
                    widget.deleteLater()

        # Yeni widget'ları ekle
        for i, box in enumerate(boxes):
            if not self._is_widget_valid(box):
                continue
                
            if box.parent() == self:
                box.setFixedSize(box_w, box_h)
            else:
                box.setFixedSize(box_w, box_h)
                box.setParent(self)
            
            r, c = divmod(i, self.columns)
            self.grid.addWidget(box, r, c, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    
    def _is_widget_valid(self, widget):
        """Widget'ın hala geçerli olup olmadığını kontrol et"""
        if widget is None:
            return False
            
        try:
            return hasattr(widget, 'isWidgetType') and widget.isWidgetType()
        except RuntimeError:
            return False

    def _delayed_resize(self):
        """Gecikmeli resize işlemi"""
        if not self._initial or not self._pending_resize:
            return
        
        self._pending_resize = False
        
        box_w, box_h, spacing = self.compute_responsive()

        if self.grid.horizontalSpacing() != spacing:
            self.grid.setHorizontalSpacing(spacing)
            self.grid.setVerticalSpacing(spacing)

        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'db_id') or hasattr(widget, 'clicked'):
                    current_size = widget.size()
                    if current_size.width() != box_w or current_size.height() != box_h:
                        widget.setFixedSize(box_w, box_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if not self._initial:
            return

        self._pending_resize = True
        self._resize_timer.start(50)