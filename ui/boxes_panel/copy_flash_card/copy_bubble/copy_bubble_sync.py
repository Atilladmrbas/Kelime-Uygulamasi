"""
copy_bubble/copy_bubble_sync.py
ORİJİNAL'den KOPYA'ya BUBBLE SENKRONİZASYON YÖNETİCİSİ
- TÜM SENKRONİZASYON MANTIĞI BURADA
- CopyNoteBubble SADECE kayıt, DİNLEME YOK!
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class CopyBubbleSyncManager(QObject):
    """ORİJİNAL KART BUBBLE'LARINDAN KOPYA BUBBLE'LARA SENKRONİZASYON"""
    
    _instance = None
    
    original_bubble_updated = pyqtSignal(int, str, int, int)
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = CopyBubbleSyncManager()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        
        self.original_to_copies = {}
        self.copy_to_original = {}
        self.copy_bubbles = {}
        
        self.sync_enabled = True
        self.sync_delay = 50
    
    def register_copy_bubble(self, copy_card_id, original_card_id, bubble_widget):
        try:
            if not copy_card_id or not original_card_id or not bubble_widget:
                return
            
            if original_card_id not in self.original_to_copies:
                self.original_to_copies[original_card_id] = []
            
            if bubble_widget not in self.original_to_copies[original_card_id]:
                self.original_to_copies[original_card_id].append(bubble_widget)
                self.copy_to_original[copy_card_id] = original_card_id
                self.copy_bubbles[copy_card_id] = bubble_widget
        
        except Exception:
            pass
    
    def unregister_copy_bubble(self, copy_card_id):
        try:
            if copy_card_id in self.copy_bubbles:
                bubble_widget = self.copy_bubbles[copy_card_id]
                
                original_id = self.copy_to_original.get(copy_card_id)
                if original_id and original_id in self.original_to_copies:
                    if bubble_widget in self.original_to_copies[original_id]:
                        self.original_to_copies[original_id].remove(bubble_widget)
                    
                    if not self.original_to_copies[original_id]:
                        del self.original_to_copies[original_id]
                
                self.copy_to_original.pop(copy_card_id, None)
                self.copy_bubbles.pop(copy_card_id, None)
        
        except Exception:
            pass
    
    def notify_original_updated(self, original_card_id, html_content, width, height):
        if not self.sync_enabled:
            return
        
        try:
            if original_card_id in self.original_to_copies:
                for bubble_widget in self.original_to_copies[original_card_id]:
                    try:
                        self._sync_single_bubble(
                            bubble_widget, 
                            original_card_id, 
                            html_content, 
                            width, 
                            height
                        )
                    except Exception:
                        pass
        
        except Exception:
            pass
    
    def _sync_single_bubble(self, bubble_widget, original_id, html_content, width, height):
        try:
            if hasattr(bubble_widget, 'text') and bubble_widget.text:
                bubble_widget.text.setHtml(html_content)
            
            if width > 0 and height > 0:
                w = max(bubble_widget.MIN_W, width)
                h = max(bubble_widget.MIN_H, height)
                bubble_widget.resize(w, h)
            
        except Exception:
            pass
    
    def _safe_auto_resize(self, bubble_widget):
        try:
            if hasattr(bubble_widget, '_auto_resize_to_text'):
                _ = bubble_widget.window()
                bubble_widget._auto_resize_to_text()
        except (RuntimeError, Exception):
            pass
    
    def set_sync_enabled(self, enabled):
        self.sync_enabled = enabled
    
    def get_copy_count(self, original_card_id):
        return len(self.original_to_copies.get(original_card_id, []))
    
    def get_all_copy_ids(self, original_card_id):
        bubbles = self.original_to_copies.get(original_card_id, [])
        copy_ids = []
        
        for bubble in bubbles:
            if hasattr(bubble, 'card_id') and bubble.card_id:
                copy_ids.append(bubble.card_id)
        
        return copy_ids
    
    def cleanup(self):
        try:
            self.original_to_copies.clear()
            self.copy_to_original.clear()
            self.copy_bubbles.clear()
        except Exception:
            pass