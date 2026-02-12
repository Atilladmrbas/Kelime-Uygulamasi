# ui/words_panel/detail_window/filter_widgets.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFrame, 
    QVBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


def normalize_turkish(text):
    """
    Türkçe karakterleri normalize et, büyük/küçük harf duyarsız yap
    Örnek: 'İstanbul' -> 'istanbul', 'ÇALIŞKAN' -> 'caliskan'
    """
    if not text:
        return text
    
    # Önce küçük harfe çevir
    text = text.lower()
    
    # Türkçe karakter dönüşümleri
    replacements = {
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
        'İ': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


# ========== 1. ContainerSearchBar Sınıfı ==========
class ContainerSearchBar(QLineEdit):
    search_changed = pyqtSignal(str)
    
    def __init__(self, container_type="unknown", parent=None):
        super().__init__(parent)
        self.container_type = container_type
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._emit_search)
        self.setup_ui()
    
    def setup_ui(self):
        placeholder = "Baş harfe göre ara... (örn: 't' veya 'ta')" if self.container_type == "unknown" else "Baş harfe göre ara..."
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(32)
        self.setMinimumWidth(160)
        self.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 13px;
                color: #2d3748;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                border-width: 1px;
            }
            QLineEdit:hover {
                border-color: #94a3b8;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
                font-size: 12px;
                font-style: italic;
            }
        """)
        self.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self, text):
        if self.debounce_timer.isActive():
            self.debounce_timer.stop()
        self.debounce_timer.start(300)
    
    def _emit_search(self):
        search_text = self.text().strip()
        self.search_changed.emit(search_text)


# ========== 2. ColorFilterButton Sınıfı ==========
class ColorFilterButton(QPushButton):
    color_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.selected_color_id = None
        self.color_buttons = []
        self.box_colors = {
            1: QColor(218, 221, 227, 255),
            2: QColor(191, 162, 198, 255),
            3: QColor(127, 184, 204, 255),
            4: QColor(230, 217, 106, 255),
            5: QColor(111, 207, 108, 255)
        }
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
        """)
        
        self.popup = QFrame(self.window() if self.window() else None)
        self.popup.setWindowFlags(Qt.WindowType.Popup)
        self.popup.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(8, 8, 8, 8)
        popup_layout.setSpacing(6)
        
        title_label = QLabel("Renk Filtresi")
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #2d3748;
                font-size: 12px;
            }
        """)
        popup_layout.addWidget(title_label)
        
        colors_layout = QHBoxLayout()
        colors_layout.setSpacing(4)
        
        for box_id, color in self.box_colors.items():
            color_btn = QPushButton()
            color_btn.setFixedSize(24, 24)
            color_btn.setProperty("box_id", box_id)
            color_btn.setProperty("selected", False)
            css_color = f"rgb({color.red()}, {color.green()}, {color.blue()})"
            color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {css_color};
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: #475569;
                    border-width: 2px;
                }}
                QPushButton[selected="true"] {{
                    border-color: #0f172a;
                    border-width: 2px;
                }}
            """)
            color_btn.clicked.connect(lambda checked, bid=box_id: self._on_color_clicked(bid))
            colors_layout.addWidget(color_btn)
            self.color_buttons.append(color_btn)
        
        clear_btn = QPushButton("Tümünü Göster")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
                margin-top: 6px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        clear_btn.clicked.connect(self._clear_filter)
        
        popup_layout.addLayout(colors_layout)
        popup_layout.addWidget(clear_btn)
        self.popup.hide()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = 3
        colors = [QColor("#ef4444"), QColor("#10b981"), QColor("#3b82f6"), QColor("#f59e0b")]
        positions = [
            (center.x() - radius, center.y() - radius),
            (center.x() + radius, center.y() - radius),
            (center.x() - radius, center.y() + radius),
            (center.x() + radius, center.y() + radius)
        ]
        
        for i, (x, y) in enumerate(positions):
            painter.setBrush(colors[i])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x), int(y), radius * 2, radius * 2)
        painter.end()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_popup()
    
    def _toggle_popup(self):
        if self.is_expanded:
            self.popup.hide()
        else:
            pos = self.mapToGlobal(self.rect().bottomLeft())
            self.popup.move(pos.x(), pos.y() + 2)
            self.popup.show()
            self.popup.raise_()
        self.is_expanded = not self.is_expanded
    
    def _on_color_clicked(self, box_id):
        self.selected_color_id = box_id
        for btn in self.color_buttons:
            is_selected = (btn.property("box_id") == box_id)
            btn.setProperty("selected", is_selected)
            btn.style().polish(btn)
        self.color_selected.emit(box_id)
        self.popup.hide()
        self.is_expanded = False
    
    def _clear_filter(self):
        self.selected_color_id = None
        for btn in self.color_buttons:
            btn.setProperty("selected", False)
            btn.style().polish(btn)
        self.color_selected.emit(0)
        self.popup.hide()
        self.is_expanded = False
    
    def clear_selection(self):
        """Dışarıdan çağrılan temizleme metodu"""
        self._clear_filter()


# ========== 3. ContainerFilterWidgets ==========
class ContainerFilterWidgets(QWidget):
    """TÜM filtre widget'larını ve state'ini yönetir"""
    
    class FilterState:
        def __init__(self, container_type):
            self.container_type = container_type
            self.search_text = ""
            self.color_id = 0
            self.is_filtering = False
    
    filter_changed = pyqtSignal(str, int, bool)  # search_text, color_id, is_filtering
    
    def __init__(self, container_type="unknown", parent=None):
        super().__init__(parent)
        self.container_type = container_type
        self.state = self.FilterState(container_type)
        
        # Search Bar
        self.search_bar = ContainerSearchBar(container_type)
        self.search_bar.search_changed.connect(self._on_search_changed)
        
        # Color Filter - SADECE unknown container için
        self.color_filter_btn = None
        if container_type == "unknown":
            self.color_filter_btn = ColorFilterButton()
            self.color_filter_btn.color_selected.connect(self._on_color_selected)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        layout.addWidget(self.search_bar, 1)
        
        if self.color_filter_btn:
            layout.addWidget(self.color_filter_btn, 0)
        
        self.setFixedHeight(40)
    
    def _on_search_changed(self, search_text):
        """Arama metni değiştiğinde"""
        self.state.search_text = search_text
        self._update_filtering_state()
        self._emit_filter_changed()
    
    def _on_color_selected(self, color_id):
        """Renk filtresi değiştiğinde"""
        self.state.color_id = color_id
        self._update_filtering_state()
        self._emit_filter_changed()
    
    def _update_filtering_state(self):
        """Filtreleme durumunu güncelle"""
        if self.container_type == "unknown":
            self.state.is_filtering = (
                self.state.search_text != "" or 
                self.state.color_id != 0
            )
        else:
            self.state.is_filtering = (self.state.search_text != "")
    
    def _emit_filter_changed(self):
        """Filtre değişikliğini bildir"""
        self.filter_changed.emit(
            self.state.search_text,
            self.state.color_id,
            self.state.is_filtering
        )
    
    def clear_filters(self):
        """Tüm filtreleri temizle"""
        self.search_bar.clear()
        self.state.search_text = ""
        
        if self.color_filter_btn:
            self.color_filter_btn.clear_selection()
            self.state.color_id = 0
        
        self.state.is_filtering = False
        self._emit_filter_changed()
    
    def get_filter_state(self):
        """Mevcut filtre durumunu döndür"""
        return {
            'search_text': self.state.search_text,
            'color_id': self.state.color_id,
            'is_filtering': self.state.is_filtering
        }
    
    # ========== BAŞ HARFE GÖRE FİLTRELEME (GÜNCELLENDİ!) ==========
    @staticmethod
    def card_matches_filter(card_data, search_text="", color_id=0, db=None):
        """
        Kartın filtreye uyup uymadığını kontrol et
        ✅ BAŞ HARFE GÖRE FİLTRELEME!
        ✅ TÜRKÇE KARAKTER DESTEĞİ!
        ✅ BÜYÜK/KÜÇÜK HARF DUYARSIZ!
        """
        matches_search = True
        matches_color = True
        
        # ===== Arama filtresi - BAŞ HARFE GÖRE! =====
        if search_text:
            english = card_data.get('english', '')
            turkish = card_data.get('turkish', '')
            
            if not english and not turkish:
                matches_search = False
            else:
                # Tüm metinleri normalize et (Türkçe karakter + küçük harf)
                english_norm = normalize_turkish(english)
                turkish_norm = normalize_turkish(turkish)
                search_norm = normalize_turkish(search_text)
                
                # BAŞ HARF KONTROLÜ - .startswith() kullan!
                matches_search = (
                    english_norm.startswith(search_norm) or 
                    turkish_norm.startswith(search_norm)
                )
        
        # ===== Renk filtresi =====
        if color_id > 0 and db and card_data.get('bucket', 0) == 0:
            try:
                card_id = card_data.get('id')
                if card_id:
                    cursor = db.conn.cursor()
                    cursor.execute("""
                        SELECT box FROM words 
                        WHERE original_card_id = ? AND is_copy = 1 AND is_drawn = 0
                        LIMIT 1
                    """, (card_id,))
                    row = cursor.fetchone()
                    if row:
                        card_box_id = row[0]
                        matches_color = (card_box_id == color_id)
                    else:
                        matches_color = False
            except Exception:
                matches_color = False
        
        return matches_search and matches_color
    
    @staticmethod
    def create_filter_widgets(container_type, parent):
        """Factory method: Container için filtre widget'ları oluştur"""
        return ContainerFilterWidgets(container_type, parent)