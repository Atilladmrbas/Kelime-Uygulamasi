# file: ui/words_panel/button_and_cards/flashcard_factory.py
from PyQt6.QtCore import QTimer
from .flashcard_view import FlashCardView
from ..copy_flash_card_view import CopyFlashCardView
from ui.boxes_panel.overlay_observer import get_overlay_observer


class FlashCardFactory:
    """FlashCardView oluşturma fabrikası - overlay otomatik entegrasyonu"""
    
    @staticmethod
    def create_card(data=None, parent=None, db=None, is_copy=False):
        """Kart oluştur ve overlay observer'a kaydet"""
        if is_copy:
            card = CopyFlashCardView(data=data, parent=parent, db=db)
        else:
            card = FlashCardView(data=data, parent=parent, db=db)
            
            observer = get_overlay_observer()
            observer.register_original_card(card)
            
            def cleanup_hook():
                observer.unregister_original_card(card)
            
            card.destroyed.connect(lambda: cleanup_hook())
        
        return card
    
    @staticmethod
    def bind_existing_card(card_widget):
        """Mevcut kartı observer'a bağla"""
        if hasattr(card_widget, 'is_copy_card') and not card_widget.is_copy_card:
            observer = get_overlay_observer()
            observer.register_original_card(card_widget)
            
            original_destroyed = card_widget.destroyed
            def new_destroyed():
                observer.unregister_original_card(card_widget)
                if original_destroyed:
                    original_destroyed.emit()
            
            card_widget.destroyed = new_destroyed

    def initialize_card_overlay(card_widget, db):
        """Kart widget'ına overlay başlat"""
        if not card_widget or not hasattr(card_widget, 'card_id'):
            return
        
        if hasattr(card_widget, 'is_copy_card') and card_widget.is_copy_card:
            return
        
        try:
            from .color_overlay import ColorOverlayWidget
            from PyQt6.QtCore import QTimer
            
            card_widget.color_overlay = ColorOverlayWidget(parent_card=card_widget)
            card_widget.color_overlay.db = db
            
            QTimer.singleShot(500, lambda: card_widget.color_overlay.schedule_lazy_update())
            
        except ImportError:
            card_widget.color_overlay = None
        except Exception:
            card_widget.color_overlay = None