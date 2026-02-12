# day_multi_select_cell.py
# 5 slot - responsive height with "+" button and notion-like multi-select
# Shows text on colored slots and saves values persistently

from __future__ import annotations

from typing import Callable, List, Optional, Tuple, Dict
from enum import Enum

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QSizePolicy,
    QLabel,
    QMenu,
    QApplication,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QAction, QPen


# --------------------------------------------------
# REPEAT TYPES ENUM
# --------------------------------------------------
# --------------------------------------------------
# REPEAT TYPES ENUM
# --------------------------------------------------
class RepeatType(Enum):
    DAILY = ("Her gün tekrar edildi", QColor(255, 255, 255))  # Beyaz - "Günlük" yerine "Her gün"
    EVERY_2_DAYS = ("2 Günde bir tekrar edildi", QColor(233, 213, 255))  # Açık mor
    EVERY_4_DAYS = ("4 Günde bir tekrar edildi", QColor(219, 234, 254))  # Açık mavi
    EVERY_9_DAYS = ("9 Günde bir tekrar edildi", QColor(254, 249, 195))  # Sarı
    EVERY_14_DAYS = ("14 Günde bir tekrar edildi", QColor(220, 252, 231))  # Yeşil
    
    def __init__(self, display_text: str, color: QColor):
        self.display_text = display_text
        self.color = color
        self.full_text = self.get_full_text(display_text)
    
    @staticmethod
    def get_full_text(short_text: str) -> str:
        mapping = {
            "Her gün": "Her gün kutusu tekrar edildi",
            "2 Gün": "2 Günde bir kutusu tekrar edildi",
            "4 Gün": "4 Günde bir kutusu tekrar edildi",
            "9 Gün": "9 Günde bir kutusu tekrar edildi",
            "14 Gün": "14 Günde bir kutusu tekrar edildi"
        }
        return mapping.get(short_text, short_text)
    
    @classmethod
    def get_color(cls, value: Optional[str]) -> QColor:
        if not value:
            return QColor(255, 255, 255)  # Default beyaz
        try:
            return cls[value].color
        except:
            return QColor(255, 255, 255)

# --------------------------------------------------
# SINGLE SLOT WIDGET WITH "+" BUTTON AND TEXT
# --------------------------------------------------
class _Slot(QFrame):
    clicked = pyqtSignal(int)  # Slot index'ini yayınla
    
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.is_empty = True
        self.repeat_type: Optional[RepeatType] = None
        self.display_text = ""
        
        self.setObjectName(f"DaySlot_{index}")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # Tıklanabilir göster

        # Slot görünümü (hafif yuvarlak, ince border)
        self.update_style()

    def update_style(self):
        if self.is_empty:
            # Boş slot: transparan "+" işareti
            self.setStyleSheet(f"""
                QFrame#{self.objectName()} {{
                    background: rgba(255, 255, 255, 0.3);
                    border: 1px dashed #d1d5db;
                    border-radius: 6px;
                }}
                QFrame#{self.objectName()}:hover {{
                    background: rgba(255, 255, 255, 0.5);
                    border: 1px solid #9ca3af;
                }}
            """)
        else:
            # Dolu slot: renkli arkaplan
            color = self.repeat_type.color if self.repeat_type else QColor(255, 255, 255)
            color_name = f"rgba({color.red()}, {color.green()}, {color.blue()}, 0.8)"
            
            self.setStyleSheet(f"""
                QFrame#{self.objectName()} {{
                    background: {color_name};
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                }}
                QFrame#{self.objectName()}:hover {{
                    border: 1px solid #9ca3af;
                    opacity: 0.9;
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.is_empty:
            # "+" işaretini çiz (sadece boş slotlarda)
            # Yarı transparan gri "+" işareti
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(100, 100, 100, 150)))  # Hafif transparan gri
            
            # Merkezi hesapla
            center_x = self.width() // 2
            center_y = self.height() // 2
            
            # "+" işareti boyutları
            cross_size = min(self.width(), self.height()) // 3
            line_width = max(1, cross_size // 6)
            
            # Dikey çizgi
            painter.drawRect(center_x - line_width // 2, 
                           center_y - cross_size // 2, 
                           line_width, cross_size)
            
            # Yatay çizgi
            painter.drawRect(center_x - cross_size // 2, 
                           center_y - line_width // 2, 
                           cross_size, line_width)
        else:
            # Renkli slotlarda metni çiz
            if self.display_text:
                # Metin rengini belirle (koyu veya açık)
                bg_color = self.repeat_type.color if self.repeat_type else QColor(255, 255, 255)
                brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
                text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)
                
                # Metni çiz
                painter.setPen(QPen(text_color))
                font = QFont()
                font.setPointSize(8)
                font.setWeight(QFont.Weight.Bold)
                painter.setFont(font)
                
                # Metni merkezle
                text_rect = painter.fontMetrics().boundingRect(self.display_text)
                text_x = (self.width() - text_rect.width()) // 2
                text_y = (self.height() + text_rect.height() // 2) // 2
                
                painter.drawText(text_x, text_y, self.display_text)
        
        painter.end()

    def set_repeat_type(self, repeat_type: Optional[RepeatType]):
        self.is_empty = (repeat_type is None)
        self.repeat_type = repeat_type
        self.display_text = repeat_type.display_text if repeat_type else ""
        self.update_style()
        self.update()  # Yeniden çiz


# --------------------------------------------------
# DAY CELL CONTENT (5 SLOTS) WITH MULTI-SELECT
# --------------------------------------------------
class DayMultiSelectContent(QWidget):
    SLOT_COUNT = 5
    MIN_SLOT_H = 12
    MAX_SLOT_H = 22
    
    # Signal emitted when slot values change
    values_changed = pyqtSignal(str, list)
    
    # Optimal heights
    SMALL_SCREEN_HEIGHT = 14
    MEDIUM_SCREEN_HEIGHT = 18
    LARGE_SCREEN_HEIGHT = 22

    def __init__(self):
        super().__init__()

        self.slots: List[_Slot] = []
        self.current_values: List[Optional[str]] = [None] * self.SLOT_COUNT
        
        # Widget ayarları
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Layout
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 2, 0, 0)
        self.root.setSpacing(2)

        # Slotları oluştur
        for i in range(self.SLOT_COUNT):
            slot = _Slot(i)
            slot.clicked.connect(self.on_slot_clicked)
            self.root.addWidget(slot)
            self.slots.append(slot)

        # Store bağlantıları
        self._date_key: Optional[str] = None
        self._get_values_cb: Optional[Callable[[str], list]] = None
        self._set_values_cb: Optional[Callable[[str, list], None]] = None
        
        # Context menu için
        self.context_menu = QMenu(self)
        self.setup_context_menu()

    def setup_context_menu(self):
        """Notion tarzı multi-select menüsünü oluştur"""
        self.context_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
                color: #374151;
            }
            QMenu::item:selected {
                background-color: #f3f4f6;
            }
            QMenu::separator {
                height: 1px;
                background: #e5e7eb;
                margin: 4px 8px;
            }
        """)
        
        # Her seçenek için action oluştur
        for repeat_type in RepeatType:
            action = QAction(repeat_type.full_text, self)  # Tam metni göster
            
            # Action'ın rengini ayarla (menüde küçük renk göstergesi)
            color = repeat_type.color
            color_name = f"rgb({color.red()}, {color.green()}, {color.blue()})"
            
            # Menü öğesine renk ekle
            action.setData(repeat_type.name)
            
            # Lambda'da doğru değeri yakalamak için
            action.triggered.connect(lambda checked, rt=repeat_type: self.on_repeat_type_selected(rt))
            self.context_menu.addAction(action)
        
        # Ayırıcı
        self.context_menu.addSeparator()
        
        # Temizle seçeneği
        clear_action = QAction("Temizle", self)
        clear_action.triggered.connect(self.clear_current_slot)
        self.context_menu.addAction(clear_action)

    def on_slot_clicked(self, slot_index: int):
        """Slot tıklandığında context menu göster"""
        self.current_slot_index = slot_index
        
        # Context menu pozisyonunu ayarla
        slot = self.slots[slot_index]
        pos = slot.mapToGlobal(slot.rect().bottomLeft())
        self.context_menu.exec(pos)

    def on_repeat_type_selected(self, repeat_type: RepeatType):
        """Seçilen tekrar tipini uygula"""
        if hasattr(self, 'current_slot_index'):
            self.set_slot_value(self.current_slot_index, repeat_type.name)
            
            # Store'a kaydet
            if self._date_key and self._set_values_cb:
                self._set_values_cb(self._date_key, self.current_values)
            
            # Değişiklik sinyali gönder
            self.values_changed.emit(self._date_key, self.current_values)
            
            # Değişikliği hemen görselleştir
            QApplication.processEvents()

    def clear_current_slot(self):
        """Mevcut slotu temizle"""
        if hasattr(self, 'current_slot_index'):
            self.set_slot_value(self.current_slot_index, None)
            
            # Store'a kaydet
            if self._date_key and self._set_values_cb:
                self._set_values_cb(self._date_key, self.current_values)
            
            # Değişiklik sinyali gönder
            self.values_changed.emit(self._date_key, self.current_values)
            
            # Değişikliği hemen görselleştir
            QApplication.processEvents()

    def set_slot_value(self, index: int, value: Optional[str]):
        """Slot değerini ayarla"""
        if 0 <= index < self.SLOT_COUNT:
            self.current_values[index] = value
            
            # RepeatType'a çevir
            repeat_type = None
            if value:
                try:
                    repeat_type = RepeatType[value]
                except:
                    pass
            
            # Slot'u güncelle
            self.slots[index].set_repeat_type(repeat_type)
            
            # Hemen yeniden çiz
            self.slots[index].update()

    # --------------------------------------------------
    # STORE BINDING & PERSISTENT STORAGE
    # --------------------------------------------------
    def bind_store(self, date_key: str, get_values_cb, set_values_cb):
        """Store'u bağla ve kayıtlı değerleri yükle"""
        self._date_key = date_key
        self._get_values_cb = get_values_cb
        self._set_values_cb = set_values_cb
        self.reload_from_store()

    def reload_from_store(self):
        """Store'dan kayıtlı değerleri yükle"""
        if self._date_key and self._get_values_cb:
            try:
                values = self._get_values_cb(self._date_key)
                if values and isinstance(values, list):
                    self.current_values = values
                    
                    # Slotları kayıtlı değerlerle güncelle
                    for i, value in enumerate(values):
                        self.set_slot_value(i, value)
            except Exception as e:
                print(f"Error loading from store: {e}")
                self.current_values = [None] * self.SLOT_COUNT

    def set_values(self, values):
        """Harici olarak değerleri ayarla ve kaydet"""
        if not isinstance(values, list):
            values = [None] * self.SLOT_COUNT
        
        # 5 değere tamamla
        values = (values + [None] * self.SLOT_COUNT)[:self.SLOT_COUNT]
        self.current_values = values
        
        # Slotları güncelle
        for i, value in enumerate(values):
            self.set_slot_value(i, value)
        
        # Store'a kaydet
        if self._date_key and self._set_values_cb:
            try:
                self._set_values_cb(self._date_key, values)
            except Exception as e:
                print(f"Error saving to store: {e}")
        
        # Değişiklik sinyali gönder
        self.values_changed.emit(self._date_key, values)

    def get_values(self):
        """Mevcut değerleri getir"""
        return self.current_values.copy()

    # --------------------------------------------------
    # RESPONSIVE SLOT HEIGHT FOR ALL SCREENS
    # --------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Calculate available height
        margins = self.root.contentsMargins()
        total_vertical_margins = margins.top() + margins.bottom()
        total_spacing = self.root.spacing() * (self.SLOT_COUNT - 1)
        available = max(0, self.height() - total_vertical_margins - total_spacing)
        
        # Calculate optimal height
        if available <= 0:
            slot_h = self.SMALL_SCREEN_HEIGHT
        else:
            slot_h = available // self.SLOT_COUNT
            
            # Apply scaling
            if slot_h < 15:
                slot_h = self.SMALL_SCREEN_HEIGHT
            elif slot_h < 20:
                slot_h = self.MEDIUM_SCREEN_HEIGHT
            else:
                slot_h = self.LARGE_SCREEN_HEIGHT
        
        # Ensure within bounds
        slot_h = max(self.MIN_SLOT_H, min(self.MAX_SLOT_H, slot_h))
        
        # Apply to all slots
        for s in self.slots:
            s.setFixedHeight(slot_h)
        
        self.root.update()
    
    def minimumSizeHint(self) -> QSize:
        margins = self.root.contentsMargins()
        spacing = self.root.spacing() * (self.SLOT_COUNT - 1)
        min_height = (self.SMALL_SCREEN_HEIGHT * self.SLOT_COUNT) + spacing + margins.top() + margins.bottom()
        min_width = 100
        return QSize(min_width, min_height)
    
    def sizeHint(self) -> QSize:
        margins = self.root.contentsMargins()
        spacing = self.root.spacing() * (self.SLOT_COUNT - 1)
        preferred_height = (self.MEDIUM_SCREEN_HEIGHT * self.SLOT_COUNT) + spacing + margins.top() + margins.bottom()
        preferred_width = 150
        return QSize(preferred_width, preferred_height)
    
    def save_state(self):
        """Mevcut durumu kaydet (opsiyonel)"""
        if self._date_key and self._set_values_cb:
            self._set_values_cb(self._date_key, self.current_values)