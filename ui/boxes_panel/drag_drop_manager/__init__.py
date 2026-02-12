"""
Drag-Drop Manager Package - Tüm gerekli export'lar
"""
from .base_manager import (
    CardType, 
    DropTarget, 
    DragSource, 
    DragOperation,
    get_drag_drop_manager  # ✅ BU SATIR EKLENDİ
)
from .decorators import draggable_card, drop_target
from .main_coordinator import DragDropManager

# Tüm export'lar
__all__ = [
    'CardType', 
    'DropTarget', 
    'DragSource', 
    'DragOperation',
    'get_drag_drop_manager',  # ✅ BU SATIR EKLENDİ
    'draggable_card', 
    'drop_target',
    'DragDropManager'
]

# Eski kodla uyumluluk için
CardType = CardType
DropTarget = DropTarget
DragSource = DragSource
DragOperation = DragOperation
get_drag_drop_manager = get_drag_drop_manager  # ✅ BU SATIR EKLENDİ
draggable_card = draggable_card
drop_target = drop_target
DragDropManager = DragDropManager