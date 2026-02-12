# ui/words_panel/box_widgets/managers/event_handler.py
from ..design.style_manager import BoxStyleManager

class EventHandler:
    """BoxView event'lerini yönetir"""
    
    def __init__(self, box_view):
        self.box_view = box_view
    
    def handle_resize(self, e):
        """Boyutlandırma event'i"""
        if self.box_view._deleted:
            return
            
        # Parent'ın resizeEvent'ini çağır
        from PyQt6.QtWidgets import QFrame
        QFrame.resizeEvent(self.box_view, e)
        
        outer = self.box_view.rect()
        
        # Style manager'dan boyutları al
        base_margin = BoxStyleManager.SIZES['card_margin']
        expanded_margin = BoxStyleManager.SIZES['expanded_margin']
        
        # Rect'leri hesapla
        self.box_view.card_base_rect = outer.adjusted(
            base_margin, base_margin, -base_margin, -base_margin
        )
        self.box_view.card_expanded_rect = outer.adjusted(
            expanded_margin, expanded_margin, -expanded_margin, -expanded_margin
        )
        
        # Duruma göre kart boyutunu ayarla
        if self.box_view._force_expanded or self.box_view.is_selected:
            self.box_view.card.setGeometry(self.box_view.card_expanded_rect)
            self.box_view.is_expanded = True
        else:
            self.box_view.card.setGeometry(self.box_view.card_base_rect)
            self.box_view.is_expanded = False
    
    def handle_enter(self, e):
        """Fare giriş event'i"""
        if self.box_view._deleted:
            return
            
        if self.box_view._hover_active and not self.box_view._force_expanded:
            self.box_view.animation_manager.expand()
        
        # Parent'ın enterEvent'ini çağır
        from PyQt6.QtWidgets import QFrame
        QFrame.enterEvent(self.box_view, e)
    
    def handle_leave(self, e):
        """Fare çıkış event'i"""
        if self.box_view._deleted:
            return
            
        if self.box_view._hover_active and not self.box_view._force_expanded:
            self.box_view.animation_manager.shrink()
        
        # Parent'ın leaveEvent'ini çağır
        from PyQt6.QtWidgets import QFrame
        QFrame.leaveEvent(self.box_view, e)