"""TEMEL DRAG-DROP SINIFLARI ve ENUMLAR"""
from PyQt6.QtCore import Qt, QMimeData, QByteArray, QPoint, QTimer
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import QApplication, QGraphicsOpacityEffect
import json
from enum import Enum
from typing import Optional, Dict, Any, Callable


class CardType(Enum):
    """Kart türleri"""
    ORIGINAL = "original"
    COPY = "copy"
    UNKNOWN = "unknown"


class DropTarget(Enum):
    """Bırakma hedefleri"""
    MEMORY_BOX = "memory_box"
    WAITING_AREA = "waiting_area"
    BOX_DETAIL = "box_detail"
    ROOT_WINDOW = "root_window"
    OTHER = "other"


class DragSource(Enum):
    """Sürükleme kaynakları"""
    MEMORY_BOX_DISPLAYED = "memory_box_displayed"
    WAITING_AREA = "waiting_area"
    BOX_DETAIL = "box_detail"


class DragOperation:
    """Tek bir drag-drop operasyonunu temsil eden sınıf"""
    
    def __init__(self):
        self.card_id: Optional[int] = None
        self.card_type: CardType = CardType.UNKNOWN
        self.source_type: Optional[DragSource] = None
        self.source_widget: Optional[Any] = None
        self.target_widget: Optional[Any] = None
        self.target_type: Optional[DropTarget] = None
        self.card_widget: Optional[Any] = None
        self.db = None
        self.success: bool = False
        self.start_time: int = 0
        self.end_time: int = 0
        self.original_box_id: Optional[int] = None
        
    def to_dict(self) -> Dict:
        """Dictionary'e çevir"""
        return {
            'card_id': self.card_id,
            'card_type': self.card_type.value,
            'source_type': self.source_type.value if self.source_type else None,
            'target_type': self.target_type.value if self.target_type else None,
            'success': self.success,
            'duration_ms': self.end_time - self.start_time
        }


_drag_drop_manager = None

def get_drag_drop_manager():
    """Global DragDropManager instance'ını al"""
    global _drag_drop_manager
    if _drag_drop_manager is None:
        from .main_coordinator import DragDropManager
        _drag_drop_manager = DragDropManager()
    return _drag_drop_manager


def create_drag_pixmap(card_widget) -> QPixmap:
    """Drag için görsel oluştur"""
    size = card_widget.size()
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setOpacity(1.0)
    
    if hasattr(card_widget, 'palette'):
        bg_color = card_widget.palette().window().color()
        painter.fillRect(pixmap.rect(), bg_color)
    
    card_widget.render(painter, QPoint(0, 0))
    
    painter.setOpacity(0.9)
    painter.setPen(QPen(QColor(100, 100, 100, 100), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(0, 0, size.width() - 1, size.height() - 1, 8, 8)
    
    painter.end()
    return pixmap


def apply_drag_effect(card_widget):
    """Drag efektini uygula"""
    try:
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.05)
        card_widget.setGraphicsEffect(effect)
        
        if hasattr(card_widget, 'setStyleSheet'):
            original_style = card_widget.styleSheet() or ""
            card_widget.setStyleSheet(f"""
                {original_style}
                QFrame {{
                    opacity: 0.05;
                    background-color: rgba(255, 255, 255, 0.05);
                }}
                QFrame * {{
                    opacity: 0.05;
                }}
            """)
    except Exception:
        pass


def remove_drag_effect(card_widget):
    """Drag efektini kaldır"""
    try:
        card_widget.setGraphicsEffect(None)
        
        if hasattr(card_widget, 'setStyleSheet'):
            current_style = card_widget.styleSheet() or ""
            lines = current_style.split('\n')
            cleaned_lines = []
            for line in lines:
                if 'opacity:' not in line and 'background-color:' not in line:
                    cleaned_lines.append(line)
            cleaned_style = '\n'.join(cleaned_lines)
            card_widget.setStyleSheet(cleaned_style)
            
            card_widget.setWindowOpacity(1.0)
    except Exception:
        pass