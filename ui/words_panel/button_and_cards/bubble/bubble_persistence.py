# bubble_persistence.py - TAM KAYIT SİSTEMİ (GÜNCELLENMİŞ)
from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtCore import QTimer
import json
import re

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

# Global flag - özyinelemeyi önle
_SAVING_IN_PROGRESS = False

def save_bubble(bubble: QWidget) -> bool:
    """
    BUBBLE KAYDET - BOYUT DAHİL!
    """
    global _SAVING_IN_PROGRESS
    
    if _SAVING_IN_PROGRESS:
        return False
    
    _SAVING_IN_PROGRESS = True
    
    try:
        # 1. Kart ID'sini al
        card_id = _get_card_id(bubble)
        if not card_id:
            _SAVING_IN_PROGRESS = False
            return False

        # 2. Bubble içeriğini al
        html_content = _get_bubble_html_content(bubble)
        
        # 3. Boş içerik kontrolü
        if _is_empty_html(html_content):
            html_content = ""

        # 4. Diğer bilgileri al
        box_id = _get_box_id(bubble)
        
        # ✅ BOYUT BİLGİSİNİ AL!
        width = bubble.width() if hasattr(bubble, 'width') else 320
        height = bubble.height() if hasattr(bubble, 'height') else 200

        # 5. Bubble veritabanına bağlan
        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()

        # 6. BOYUTLA BİRLİKTE KAYDET!
        result = bubble_db.save_bubble(
            card_id=card_id,
            html_content=html_content,
            box_id=box_id,
            width=width,
            height=height
        )
        
        if result:
            print(f"✅ [save_bubble] Bubble kaydedildi - ID: {card_id}, Boyut: {width}x{height}, HTML: {len(html_content)}")
            
            # 7. ORİJİNAL KART İSE SENKRONİZASYON
            if _is_original_card(bubble):
                _notify_copy_bubbles_updated(card_id, html_content, bubble)
        
        return result

    except Exception as e:
        print(f"❌ [save_bubble] Hata: {e}")
        return False
    finally:
        _SAVING_IN_PROGRESS = False

def _get_original_card_id(card_id, bubble=None):
    """Kopya kartın orijinal ID'sini bul"""
    try:
        db = _get_db_connection(bubble) if bubble else None
        if not db:
            return None
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT original_card_id FROM words WHERE id=?", (card_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except:
        return None

def _notify_copy_bubbles_updated(original_id, html_content, bubble_widget):
    """Orijinal kart bubble'ı güncellendi - KOPYA BUBBLE'LARA BİLDİR"""
    try:
        # ✅ YENİ SİSTEM: CopyBubbleSyncManager kullan (copy_flash_card/copy_bubble klasöründe)
        try:
            from ui.boxes_panel.copy_flash_card.copy_bubble.copy_bubble_sync import CopyBubbleSyncManager
            sync_manager = CopyBubbleSyncManager.instance()
            
            width = bubble_widget.width() if hasattr(bubble_widget, 'width') else 320
            height = bubble_widget.height() if hasattr(bubble_widget, 'height') else 200
            
            sync_manager.notify_original_updated(
                original_card_id=original_id,
                html_content=html_content,
                width=width,
                height=height
            )
            print(f"✅ [_notify_copy_bubbles_updated] Kopya bubble'lara bildirildi: {original_id}")
            
        except ImportError as e:
            print(f"⚠️ [_notify_copy_bubbles_updated] CopyBubbleSyncManager bulunamadı: {e}")
            
    except Exception as e:
        print(f"❌ [_notify_copy_bubbles_updated] Hata: {e}")

def _save_to_copy_bubbles_old(bubble, original_id, html_content):
    """Eski sistem - Geriye dönük uyumluluk"""
    try:
        db = _get_db_connection(bubble)
        if not db:
            return
        
        # Kopya kartları bul
        cursor = db.conn.cursor()
        cursor.execute("SELECT id, box FROM words WHERE original_card_id=? AND is_copy=1", 
                     (original_id,))
        copy_rows = cursor.fetchall()
        
        if not copy_rows:
            return
        
        # BubbleDatabase'e bağlan
        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()
        
        for row in copy_rows:
            copy_id = row[0]
            copy_box_id = row[1]
            
            try:
                # Kopya bubble'ı kaydet
                bubble_db.save_bubble(
                    card_id=copy_id,
                    html_content=html_content,
                    box_id=copy_box_id
                )
            except Exception:
                continue
                    
    except Exception:
        pass

# ==================== DİĞER FONKSİYONLAR (Aynı kalacak) ====================

def _get_bubble_html_content(bubble: QWidget) -> str:
    """Bubble'dan HTML içeriğini güvenli şekilde al"""
    try:
        # BubbleText için özel kontrol
        if hasattr(bubble, "text"):
            text_widget = bubble.text
            if hasattr(text_widget, "toHtml"):
                return text_widget.toHtml()
        
        # Doğrudan bubble'dan dene
        if hasattr(bubble, "toHtml"):
            return bubble.toHtml()

        # html() metodundan dene
        if hasattr(bubble, "html"):
            return bubble.html()

        return ""
        
    except Exception:
        return ""

def _is_empty_html(html_content: str) -> bool:
    """HTML içeriğinin boş olup olmadığını kontrol et"""
    if not html_content or html_content.strip() == "":
        return True
    
    empty_patterns = [
        "<html><head></head><body></body></html>",
        "<html><head></head><body><p></p></body></html>",
        "<html><body></body></html>",
        "<body></body>",
    ]
    
    for pattern in empty_patterns:
        if html_content.strip() == pattern:
            return True
    
    # Sadece whitespace'ler mi kontrol et
    text_only = re.sub(r'<[^>]+>', '', html_content)
    if text_only.strip() == "":
        return True
    
    return False

def _is_original_card(bubble: QWidget) -> bool:
    """Kartın orijinal olup olmadığını kontrol et"""
    try:
        card_id = _get_card_id(bubble)
        if not card_id:
            return False
        
        db = _get_db_connection(bubble)
        if not db:
            return False
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT is_copy FROM words WHERE id=?", (card_id,))
        row = cursor.fetchone()
        
        if row:
            return row[0] == 0
        
        return False
        
    except Exception:
        return False

def load_bubble(card_id: int | str) -> dict:
    """
    BUBBLE YÜKLE - ORİJİNAL ÖNCELİKLİ
    """
    try:
        if not card_id:
            return {"html": "", "width": 320, "height": 200}

        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()

        # 1. ÖNCE BU KARTIN KENDİ BUBBLE'INI DENE
        bubble_data = bubble_db.get_bubble(card_id)
        
        if bubble_data and bubble_data.get("html_content"):
            html = bubble_data.get("html_content", "") or ""
            width = bubble_data.get("width", 320) or 320
            height = bubble_data.get("height", 200) or 200
            
            return {"html": html, "width": width, "height": height}
        
        # 2. EĞER BUBBLE YOKSA, KARTIN ORİJİNALİNİ KONTROL ET
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            db = None
            
            if app:
                for widget in app.allWidgets():
                    if hasattr(widget, 'db') and widget.db:
                        db = widget.db
                        break
            
            if db:
                cursor = db.conn.cursor()
                cursor.execute("SELECT original_card_id, is_copy FROM words WHERE id=?", (card_id,))
                row = cursor.fetchone()
                
                if row:
                    original_id = row[0]
                    is_copy = row[1] == 1
                    
                    if is_copy and original_id:
                        # Orijinal kartın bubble'ını yükle
                        original_bubble_data = bubble_db.get_bubble(original_id)
                        if original_bubble_data and original_bubble_data.get("html_content"):
                            html = original_bubble_data.get("html_content", "") or ""
                            width = original_bubble_data.get("width", 320) or 320
                            height = original_bubble_data.get("height", 200) or 200
                            
                            return {"html": html, "width": width, "height": height}
                
        except Exception:
            pass
        
        return {"html": "", "width": 320, "height": 200}

    except Exception:
        return {"html": "", "width": 320, "height": 200}

# ==================== HELPER FONKSİYONLAR (Aynı kalacak) ====================

def _get_card_id(bubble: QWidget) -> int | str | None:
    try:
        # 1. Doğrudan bubble'dan
        if hasattr(bubble, "card_id") and bubble.card_id:
            return bubble.card_id

        # 2. _anchor_card'tan
        flashcard = getattr(bubble, "_anchor_card", None)
        if flashcard:
            if hasattr(flashcard, "card_id") and flashcard.card_id:
                return flashcard.card_id
            if hasattr(flashcard, "data") and hasattr(flashcard.data, "id"):
                return flashcard.data.id

        # 3. card_view'tan
        card_view = getattr(bubble, "card_view", None)
        if card_view:
            if hasattr(card_view, "card_id") and card_view.card_id:
                return card_view.card_id
            if hasattr(card_view, "data") and hasattr(card_view.data, "id"):
                return card_view.data.id

        # 4. Parent'tan
        parent = bubble.parent()
        if parent and hasattr(parent, "card_id") and parent.card_id:
            return parent.card_id

        return None

    except Exception:
        return None

def _get_box_id(bubble: QWidget) -> int | None:
    try:
        if hasattr(bubble, "box_id") and bubble.box_id is not None:
            return bubble.box_id

        flashcard = getattr(bubble, "_anchor_card", None)
        if flashcard:
            if hasattr(flashcard, "box_id") and flashcard.box_id is not None:
                return flashcard.box_id
            if hasattr(flashcard, "data"):
                return getattr(flashcard.data, "box", None)

        card_view = getattr(bubble, "card_view", None)
        if card_view and hasattr(card_view, "box_id"):
            return card_view.box_id

        return None

    except Exception:
        return None

def _get_db_connection(bubble: QWidget):
    """Bubble'dan veritabanı bağlantısını al"""
    try:
        # 1. _anchor_card'tan deneyelim
        if hasattr(bubble, "_anchor_card"):
            anchor = bubble._anchor_card
            if hasattr(anchor, 'db') and anchor.db:
                return anchor.db
        
        # 2. card_view'tan deneyelim
        if hasattr(bubble, "card_view"):
            card_view = bubble.card_view
            if hasattr(card_view, 'db') and card_view.db:
                return card_view.db
        
        # 3. Parent'larda ara
        parent = bubble.parent()
        search_depth = 0
        while parent and search_depth < 10:
            if hasattr(parent, 'db') and parent.db:
                return parent.db
            parent = parent.parent()
            search_depth += 1
        
        # 4. Main window'da ara
        main_window = bubble.window()
        if main_window and hasattr(main_window, 'db') and main_window.db:
            return main_window.db
        
        # 5. QApplication üzerinden ara
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'db') and widget.db:
                    return widget.db
            
        return None
        
    except Exception:
        return None

def delete_bubble(card_id: int | str) -> bool:
    """Bubble sil"""
    try:
        if not card_id:
            return False

        from core.bubble_db import BubbleDatabase
        bubble_db = BubbleDatabase()
        return bubble_db.delete_bubble(card_id)

    except Exception:
        return False