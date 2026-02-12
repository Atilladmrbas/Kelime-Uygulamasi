# core/card_mover.py
from .database import Database
from .bubble_db import BubbleDatabase


class CardMover:
    """Kartları kutular arası taşıma sistemi"""
    
    def __init__(self):
        self.main_db = Database()
        self.bubble_db = BubbleDatabase()
    
    def move_card(self, card_id, from_box_id, to_box_id, bucket=0):
        """
        Kartı bir kutudan diğerine taşı
        """
        try:
            # 1. Ana DB'de kartın box'ını güncelle
            success = self.main_db.update_word_box(card_id, to_box_id, bucket)
            
            if not success:
                return False
            
            # 2. Bubble DB'de box_id güncelle
            self._update_bubble_db(card_id, to_box_id)
            
            # 3. State dosyalarını güncelle
            self._update_state_files(card_id, from_box_id, to_box_id, bucket)
            
            return True
            
        except Exception:
            return False
    
    def move_card_to_panel(self, card_id, from_box_id):
        """
        Kartı panele geri taşı (box = NULL)
        """
        try:
            # 1. Ana DB'de kartın box'ını NULL yap
            success = self.main_db.unassign_card_from_box(card_id)
            
            if not success:
                return False
            
            # 2. Bubble DB'de box_id NULL yap
            self._update_bubble_db(card_id, None)
            
            # 3. State dosyasından sil
            self._remove_from_state(card_id, from_box_id)
            
            return True
            
        except Exception:
            return False
    
    def move_card_within_box(self, card_id, box_id, to_bucket):
        """
        Kartı aynı kutu içinde başka bucket'a taşı
        """
        try:
            # 1. Ana DB'de bucket'ı güncelle
            success = self.main_db.update_word_bucket(card_id, to_bucket)
            
            if not success:
                return False
            
            # 2. State dosyasını güncelle
            self._update_card_bucket_in_state(card_id, box_id, to_bucket)
            
            return True
            
        except Exception:
            return False
    
    def move_card_between_containers(self, card_id, from_box_id, to_box_id, to_bucket=0):
        """
        Kartı container'dan container'a taşı
        """
        try:
            # 1. Ana DB'de kartın box'ını güncelle
            success = self.main_db.move_card_between_boxes(card_id, from_box_id, to_box_id, to_bucket)
            
            if not success:
                return False
            
            # 2. Bubble DB'de box_id güncelle
            self._update_bubble_db(card_id, to_box_id)
            
            # 3. State dosyalarını güncelle
            self._update_state_files(card_id, from_box_id, to_box_id, to_bucket)
            
            return True
            
        except Exception:
            return False
    
    def _update_bubble_db(self, card_id, to_box_id):
        """Bubble DB'de box_id güncelle"""
        try:
            self.bubble_db.update_box_id(card_id, to_box_id)
        except Exception:
            pass
    
    def _update_state_files(self, card_id, from_box_id, to_box_id, bucket=0):
        """
        State dosyalarını güncelle
        """
        try:
            # FROM state'i yükle ve kartı sil
            from_state = self._load_box_state(from_box_id)
            if from_state:
                from_state.remove_card(card_id)
                from_state.save()
            
            # TO state'i yükle ve kartı ekle
            to_state = self._load_box_state(to_box_id)
            if to_state:
                existing_card = None
                for card in to_state.cards:
                    if card.get("id") == card_id:
                        existing_card = card
                        break
                
                if existing_card:
                    existing_card["bucket"] = bucket
                else:
                    to_state.cards.append({
                        "id": int(card_id),
                        "bucket": bucket,
                        "rect": None
                    })
                
                to_state.save()
            
            return True
            
        except Exception:
            return False
    
    def _update_card_bucket_in_state(self, card_id, box_id, new_bucket):
        """State dosyasında kartın bucket'ını güncelle"""
        try:
            state = self._load_box_state(box_id)
            if state:
                for card in state.cards:
                    if card.get("id") == card_id:
                        card["bucket"] = new_bucket
                        state.save()
                        return True
            return False
            
        except Exception:
            return False
    
    def _remove_from_state(self, card_id, from_box_id):
        """State dosyasından kartı sil"""
        try:
            from_state = self._load_box_state(from_box_id)
            if from_state:
                from_state.remove_card(card_id)
                from_state.save()
                return True
            return False
            
        except Exception:
            return False
    
    def _load_box_state(self, box_id):
        """
        BoxDetailState objesini yükle
        """
        try:
            from ui.words_panel.detail_window.states.box_detail_state import BoxDetailState
            
            boxes = self.main_db.get_boxes()
            box_title = None
            for bid, title in boxes:
                if bid == box_id:
                    box_title = title
                    break
            
            if not box_title:
                return None
            
            state = BoxDetailState(box_id, box_title)
            if state.load():
                return state
            else:
                state.mark_dirty()
                return state
                
        except Exception:
            return None
    
    def get_available_target_boxes(self, current_box_id):
        """
        Mevcut kutu hariç tüm kutuları getir
        """
        boxes = self.main_db.get_boxes()
        return [(bid, title) for bid, title in boxes if bid != current_box_id]
    
    def get_card_info(self, card_id):
        """
        Kart bilgilerini getir
        """
        return self.main_db.get_card_info(card_id)
    
    def get_boxes_list(self):
        """
        Tüm kutuları getir
        """
        return self.main_db.get_boxes()