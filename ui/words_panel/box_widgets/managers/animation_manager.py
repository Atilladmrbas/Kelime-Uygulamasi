# ui/words_panel/box_widgets/managers/animation_manager.py
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect

class AnimationManager:
    """BoxView animasyonlarını yönetir"""
    
    def __init__(self, box_view):
        self.box_view = box_view
        self.card = box_view.card
        self.anim = None
        self._setup_animation()
        
        # Rect'leri tanımla
        self.box_view.card_base_rect = QRect()
        self.box_view.card_expanded_rect = QRect()
        self.box_view.is_expanded = False
        
    def _setup_animation(self):
        """Animasyonu kur"""
        self.anim = QPropertyAnimation(self.card, b"geometry")
        self.anim.setDuration(120)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
    
    def expand(self, immediate: bool = False):
        """Kartı genişlet"""
        if self.box_view._deleted or (self.box_view.is_expanded and not self.box_view._force_expanded):
            return
        
        if immediate:
            self.anim.stop()
            self.card.setGeometry(self.box_view.card_expanded_rect)
            self.box_view.is_expanded = True
            return
        
        if not self.box_view._force_expanded:
            self.anim.stop()
            self.box_view.is_expanded = True
            self.anim.setStartValue(self.card.geometry())
            self.anim.setEndValue(self.box_view.card_expanded_rect)
            self.anim.start()
    
    def shrink(self, immediate: bool = False):
        """Kartı küçült"""
        if self.box_view._deleted or (not self.box_view.is_expanded or self.box_view._force_expanded):
            return
        
        if immediate:
            self.anim.stop()
            self.card.setGeometry(self.box_view.card_base_rect)
            self.box_view.is_expanded = False
            return
        
        self.anim.stop()
        self.box_view.is_expanded = False
        self.anim.setStartValue(self.card.geometry())
        self.anim.setEndValue(self.box_view.card_base_rect)
        self.anim.start()
    
    def stop(self):
        """Animasyonu durdur"""
        if self.anim:
            self.anim.stop()