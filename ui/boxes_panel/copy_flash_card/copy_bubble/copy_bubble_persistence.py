"""
copy_bubble/copy_bubble_persistence.py
KOPYA BUBBLE VERİTABANI İŞLEMLERİ
"""

import json


def save_copy_bubble(self, copy_card_id, html_content, width=None, height=None, original_card_id=None):
    """Kopya kart bubble'ını kaydet - BOYUT OPSİYONEL"""
    try:
        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()
        
        if width is None or height is None:
            pass
        else:
            result = bubble_db.save_bubble(
                card_id=copy_card_id,
                html_content=html_content,
                width=width,
                height=height
            )
        
        return result
        
    except Exception:
        return False


def load_copy_bubble(copy_card_id):
    """Kopya kart bubble'ını yükle - HTML + BOYUT (orijinal senkronizasyonu için)"""
    try:
        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()
        
        bubble_data = bubble_db.get_bubble(copy_card_id)
        
        if bubble_data:
            return {
                "html": bubble_data.get("html_content", ""),
                "width": bubble_data.get("width", 320),
                "height": bubble_data.get("height", 200)
            }
        
        return None
        
    except Exception:
        return None


def delete_copy_bubble(copy_card_id):
    """Kopya kart bubble'ını sil"""
    try:
        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()
        
        return bubble_db.delete_bubble(copy_card_id)
        
    except Exception:
        return False


def _notify_copy_bubbles_updated(original_id, html_content, bubble_widget):
    """Orijinal kart bubble'ı güncellendi - KOPYA BUBBLE'LARA BİLDİR"""
    try:
        try:
            from copy_flash_card.copy_bubble.copy_bubble_sync import CopyBubbleSyncManager
            sync_manager = CopyBubbleSyncManager.instance()
            
            width = bubble_widget.width() if hasattr(bubble_widget, 'width') else 320
            height = bubble_widget.height() if hasattr(bubble_widget, 'height') else 200
            
            sync_manager.notify_original_updated(
                original_card_id=original_id,
                html_content=html_content,
                width=width,
                height=height
            )
            
        except ImportError:
            _save_to_copy_bubbles_old(bubble_widget, original_id, html_content)
            
    except Exception:
        pass