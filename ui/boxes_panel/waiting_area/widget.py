"""ANA WIDGET - Base ve Logic'i birleştirir"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer

from .base import WaitingAreaBase
from .logic import WaitingAreaLogic


class WaitingAreaWidget(WaitingAreaBase, QWidget):
    """Birleştirilmiş Waiting Area Widget"""
    
    def __init__(self, box_id, target_box_title, parent=None, is_left_side=False):
        super().__init__(box_id, target_box_title, parent, is_left_side)
        
        # Logic sınıfını başlat
        self.logic = WaitingAreaLogic(self)
    
    def showEvent(self, event):
        """Widget gösterildiğinde"""
        super().showEvent(event)
        self.logic.showEvent(event)
    
    # Logic sınıfına yönlendirilen metodlar
    def _add_dragged_card(self, word_id, source_widget=None):
        return self.logic._add_dragged_card(word_id, source_widget)
    
    def _remove_card_by_id(self, word_id, emit_signal=True):
        return self.logic._remove_card_by_id(word_id, emit_signal)
    
    def clear_cards(self):
        return self.logic.clear_cards()
    
    def get_cards(self):
        return self.logic.get_cards()
    
    def set_target_box_title(self, title):
        return self.logic.set_target_box_title(title)
    
    def _check_all_cards_validity(self):
        return self.logic._check_all_cards_validity()
    
    def _remove_dead_copy_card(self, word_id):
        return self.logic._remove_dead_copy_card(word_id)
    
    def _rearrange_cards_simple(self):
        return self.logic._rearrange_cards_simple()
    
    def _finalize_card_setup(self, card_view, word_id):
        return self.logic._finalize_card_setup(card_view, word_id)
    
    def _fix_delete_button_for_waiting_area(self, card_view, word_id, db, card_data):
        return self.logic._fix_delete_button_for_waiting_area(card_view, word_id, db, card_data)
    
    def _refresh_box_view_for_card(self, card_id):
        return self.logic._refresh_box_view_for_card(card_id)
    
    def _refresh_all_box_counts(self):
        return self.logic._refresh_all_box_counts()
    
    def _update_transfer_button(self):
        return self.logic._update_transfer_button()