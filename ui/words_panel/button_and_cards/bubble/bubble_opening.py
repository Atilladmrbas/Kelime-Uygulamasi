from PyQt6.QtCore import (
    QRect, QPoint, QEvent, QObject,
    QEasingCurve, QPropertyAnimation, QTimer,
    QParallelAnimationGroup, QDateTime
)
from PyQt6.QtWidgets import QApplication, QWidget, QGraphicsOpacityEffect

MARGIN = 12
PAD = 8

# =====================================================
# GLOBAL STATE YÖNETİCİ - ÇİFT TIKLAMA SORUNU İÇİN
# =====================================================
class BubbleStateManager:
    """Merkezi state yöneticisi - tüm bubble'lar için"""
    
    _bubble_states = {}  # flashcard_id -> bubble_state
    _last_click_times = {}  # flashcard_id -> last_click_time
    
    @staticmethod
    def get_bubble_state(flashcard):
        """Flashcard'ın bubble state'ini getir"""
        flashcard_id = id(flashcard)
        return BubbleStateManager._bubble_states.get(flashcard_id, False)
    
    @staticmethod
    def set_bubble_state(flashcard, state):
        """Flashcard'ın bubble state'ini ayarla"""
        flashcard_id = id(flashcard)
        BubbleStateManager._bubble_states[flashcard_id] = state
        
        # Flashcard'ın kendi state'ini de güncelle
        if hasattr(flashcard, "bubble_open"):
            flashcard.bubble_open = state
        
        # Bubble'ın state'ini de güncelle
        if hasattr(flashcard, "bubble") and flashcard.bubble:
            flashcard.bubble._bubble_open = state
    
    @staticmethod
    def can_click(flashcard, cooldown_ms=150):
        """Tıklamaya izin veriliyor mu?"""
        flashcard_id = id(flashcard)
        current_time = QDateTime.currentMSecsSinceEpoch()
        
        last_time = BubbleStateManager._last_click_times.get(flashcard_id, 0)
        
        if current_time - last_time < cooldown_ms:
            return False
        
        BubbleStateManager._last_click_times[flashcard_id] = current_time
        return True
    
    @staticmethod
    def cleanup(flashcard):
        """Flashcard silinirken temizlik"""
        flashcard_id = id(flashcard)
        BubbleStateManager._bubble_states.pop(flashcard_id, None)
        BubbleStateManager._last_click_times.pop(flashcard_id, None)


# =====================================================
# YERLEŞTİRME FONKSİYONU
# =====================================================
def place_bubble_next_to_card_fast(bubble, card, parent):
    """Kartın yanına yerleştir"""
    if not parent or not card:
        return
    
    try:
        # Kartın parent içindeki pozisyonu
        card_pos = card.mapTo(parent, QPoint(0, 0))
        card_rect = QRect(card_pos.x(), card_pos.y(), card.width(), card.height())
        
        # Bubble boyutları
        bw = bubble.width()
        bh = bubble.height()
        
        # SAĞ tarafa yerleştir
        target_x = card_rect.right() + MARGIN
        target_y = card_rect.center().y() - bh // 2
        
        # SAĞ'a sığmazsa SOL
        if target_x + bw > parent.width() - PAD:
            target_x = card_rect.left() - bw - MARGIN
        
        # SOL'a da sığmazsa ALT
        if target_x < PAD:
            target_x = max(PAD, card_rect.center().x() - bw // 2)
            target_y = card_rect.bottom() + MARGIN
        
        # ALT'a da sığmazsa ÜST
        if target_y + bh > parent.height() - PAD:
            target_y = card_rect.top() - bh - MARGIN
        
        # Sınır kontrolleri
        target_x = max(PAD, min(target_x, parent.width() - bw - PAD))
        target_y = max(PAD, min(target_y, parent.height() - bh - PAD))
        
        bubble.move(int(target_x), int(target_y))
        
    except Exception:
        bubble.move(100, 100)


# =====================================================
# ANİMASYON SİSTEMİ - İÇERİDEN DIŞARI BÜYÜME
# =====================================================
class BubbleAnimation:
    """İçeriden dışarı büyüme/küçülme animasyonu"""
    
    @staticmethod
    def create_open_animation(bubble, card, parent):
        """İçeriden dışarı büyüme (merkezden)"""
        # Önce pozisyonu ayarla
        place_bubble_next_to_card_fast(bubble, card, parent)
        final_rect = bubble.geometry()
        
        # MERKEZDEN başla (1x1 px)
        center_x = final_rect.center().x()
        center_y = final_rect.center().y()
        start_rect = QRect(center_x, center_y, 1, 1)
        
        # Animasyon grubu
        group = QParallelAnimationGroup(bubble)
        
        # SCALE animasyonu (120ms) - içeriden dışarı
        scale_anim = QPropertyAnimation(bubble, b"geometry")
        scale_anim.setDuration(120)
        scale_anim.setStartValue(start_rect)
        scale_anim.setEndValue(final_rect)
        scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)  # Yumuşak, zıplama yok
        
        # FADE IN animasyonu (100ms)
        opacity_effect = QGraphicsOpacityEffect(bubble)
        opacity_effect.setOpacity(0.0)
        bubble.setGraphicsEffect(opacity_effect)
        
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        fade_anim.setDuration(100)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        group.addAnimation(scale_anim)
        group.addAnimation(fade_anim)
        
        return group
    
    @staticmethod
    def create_close_animation(bubble, callback=None):
        """Dıştan içe küçülme (merkeze doğru)"""
        group = QParallelAnimationGroup(bubble)
        
        current_rect = bubble.geometry()
        center_x = current_rect.center().x()
        center_y = current_rect.center().y()
        
        # MERKEZE doğru küçül (1x1 px)
        end_rect = QRect(center_x, center_y, 1, 1)
        
        # SCALE animasyonu (100ms) - dıştan içe
        scale_anim = QPropertyAnimation(bubble, b"geometry")
        scale_anim.setDuration(100)
        scale_anim.setStartValue(current_rect)
        scale_anim.setEndValue(end_rect)
        scale_anim.setEasingCurve(QEasingCurve.Type.InCubic)  # Yumuşak, zıplama yok
        
        # FADE OUT animasyonu (80ms)
        opacity_effect = bubble.graphicsEffect()
        if not opacity_effect:
            opacity_effect = QGraphicsOpacityEffect(bubble)
            bubble.setGraphicsEffect(opacity_effect)
        
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        fade_anim.setDuration(80)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        group.addAnimation(scale_anim)
        group.addAnimation(fade_anim)
        
        if callback:
            group.finished.connect(callback)
        
        return group


# =====================================================
# ANA AÇMA/KAPAMA FONKSİYONLARI - ÇİFT TIKLAMA ÇÖZÜMLÜ
# =====================================================
def open_bubble(flashcard):
    """
    ÇİFT TIKLAMA SORUNU ÇÖZÜLMÜŞ açılış
    """
    # 1. Debounce kontrolü
    if not BubbleStateManager.can_click(flashcard, 150):
        return
    
    # 2. Bubble'ı kontrol et
    if not hasattr(flashcard, "bubble") or not flashcard.bubble:
        return
    
    bubble = flashcard.bubble
    
    # 3. MERKEZİ STATE kontrolü
    bubble_is_open = BubbleStateManager.get_bubble_state(flashcard)
    
    if bubble_is_open:
        close_bubble(bubble)
        return
    
    # 4. Ana pencereyi bul
    main_window = flashcard.window()
    if not main_window:
        return
    
    # 5. Parent ayarla (ÖNEMLİ!)
    if bubble.parent() != main_window:
        bubble.setParent(main_window)
    
    # 6. MERKEZİ STATE'i ayarla (HEMEN!)
    BubbleStateManager.set_bubble_state(flashcard, True)
    
    # 7. Bubble'ın kendi state'lerini ayarla
    bubble._anchor_card = flashcard
    bubble._animating = True
    
    # 8. HEMEN GÖSTER (UI responsivenes için)
    bubble.show()
    bubble.raise_()
    bubble.activateWindow()
    
    # 9. HEMEN yerleştir
    place_bubble_next_to_card_fast(bubble, flashcard, main_window)
    
    # 10. ANİMASYONU BAŞLAT
    anim = BubbleAnimation.create_open_animation(bubble, flashcard, main_window)
    
    def on_anim_finished():
        bubble._animating = False
        
        # Text focus
        if hasattr(bubble, "text") and bubble.text:
            bubble.text.setFocus()
        
        # Event filter'ları kur
        setup_event_filters(bubble, flashcard)
    
    anim.finished.connect(on_anim_finished)
    anim.start()


def close_bubble(bubble):
    """
    ÇİFT TIKLAMA SORUNU ÇÖZÜLMÜŞ kapanış
    """
    # 1. Flashcard'ı bul
    if not hasattr(bubble, "_anchor_card"):
        return
    
    flashcard = bubble._anchor_card
    
    # 2. MERKEZİ STATE kontrolü
    bubble_is_open = BubbleStateManager.get_bubble_state(flashcard)
    
    if not bubble_is_open:
        return
    
    # 3. MERKEZİ STATE'i HEMEN kapat (çift tıklama için önemli!)
    BubbleStateManager.set_bubble_state(flashcard, False)
    
    # 4. Bubble'ın animasyon state'ini ayarla
    bubble._animating = True
    
    # 5. ANİMASYONU BAŞLAT
    anim = BubbleAnimation.create_close_animation(
        bubble,
        callback=lambda: on_close_complete(bubble, flashcard)
    )
    anim.start()


def on_close_complete(bubble, flashcard):
    """
    Kapanış tamamlandığında - TEMİZLİK
    """
    # 1. Toolbar ve popup'ları temizle
    if hasattr(bubble, "text") and bubble.text:
        if hasattr(bubble.text, "toolbar"):
            toolbar = bubble.text.toolbar
            if toolbar:
                toolbar.close_all(force=True)
                toolbar.cleanup()
    
    # 2. Gizle
    bubble.hide()
    
    # 3. Event filter'ları temizle
    cleanup_event_filters(bubble)
    
    # 4. Graphics effect'i temizle
    if bubble.graphicsEffect():
        bubble.setGraphicsEffect(None)
    
    # 5. Bubble state'lerini temizle
    bubble._animating = False


# =====================================================
# EVENT FİLTER YÖNETİMİ
# =====================================================
def setup_event_filters(bubble, flashcard):
    """Event filter kur"""
    try:
        # Önce temizle
        cleanup_event_filters(bubble)
        
        # Yeni filter'lar
        bubble._card_filter = CardFollowFilter(bubble, flashcard)
        flashcard.installEventFilter(bubble._card_filter)
        
        bubble._close_filter = BubbleCloseFilter(bubble)
        QApplication.instance().installEventFilter(bubble._close_filter)
        
    except Exception:
        pass


def cleanup_event_filters(bubble):
    """Event filter temizle"""
    try:
        if hasattr(bubble, "_card_filter") and hasattr(bubble, "_anchor_card"):
            bubble._anchor_card.removeEventFilter(bubble._card_filter)
    except:
        pass
    
    try:
        if hasattr(bubble, "_close_filter"):
            QApplication.instance().removeEventFilter(bubble._close_filter)
    except:
        pass
    
    # Attribute'ları sil
    for attr in ["_card_filter", "_close_filter"]:
        if hasattr(bubble, attr):
            try:
                delattr(bubble, attr)
            except:
                pass


# =====================================================
# EVENT FİLTER SINIFLARI
# =====================================================
class CardFollowFilter(QObject):
    """Kart takip filter'ı"""
    def __init__(self, bubble, card):
        super().__init__()
        self.bubble = bubble
        self.card = card
    
    def eventFilter(self, obj, event):
        if obj is self.card and BubbleStateManager.get_bubble_state(self.card):
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                QTimer.singleShot(50, self._update_position)
        return False
    
    def _update_position(self):
        try:
            if BubbleStateManager.get_bubble_state(self.card):
                parent = self.bubble.parent()
                if parent:
                    place_bubble_next_to_card_fast(self.bubble, self.card, parent)
        except:
            pass


class BubbleCloseFilter(QObject):
    """Dışarı tıklanınca kapatma filter'ı"""
    def __init__(self, bubble):
        super().__init__()
        self.bubble = bubble
    
    def eventFilter(self, obj, event):
        if not hasattr(self.bubble, "_anchor_card"):
            return False
        
        flashcard = self.bubble._anchor_card
        if not BubbleStateManager.get_bubble_state(flashcard):
            return False
        
        if event.type() == QEvent.Type.MouseButtonPress:
            try:
                pos = event.globalPosition().toPoint()
                
                # Bubble içinde mi?
                if is_point_in_widget(self.bubble, pos):
                    return False
                
                # Text içinde mi?
                if hasattr(self.bubble, "text"):
                    if is_point_in_widget(self.bubble.text.viewport(), pos):
                        return False
                
                # Toolbar/popup içinde mi?
                toolbar = getattr(getattr(self.bubble, "text", None), "toolbar", None)
                if toolbar and toolbar.isVisible():
                    if is_point_in_widget(toolbar, pos):
                        return False
                    
                    popup = getattr(toolbar, "color_popup", None)
                    if popup and popup.isVisible():
                        if is_point_in_widget(popup, pos):
                            return False
                
                # Dışarı tıklandı - KAPAT
                close_bubble(self.bubble)
                return True
                
            except:
                pass
        
        return False


def is_point_in_widget(widget, global_point):
    """Nokta widget içinde mi?"""
    if not widget or not widget.isVisible():
        return False
    
    try:
        widget_global_pos = widget.mapToGlobal(QPoint(0, 0))
        widget_rect = QRect(widget_global_pos, widget.size())
        return widget_rect.contains(global_point)
    except:
        return False


# =====================================================
# TEMİZLİK FONKSİYONU
# =====================================================
def cleanup_bubble(flashcard):
    """Flashcard silinirken bubble'ı temizle"""
    if hasattr(flashcard, "bubble") and flashcard.bubble:
        try:
            # Bubble'ı gizle ve temizle
            bubble = flashcard.bubble
            bubble.hide()
            cleanup_event_filters(bubble)
            
            if bubble.graphicsEffect():
                bubble.setGraphicsEffect(None)
            
            bubble.setParent(None)
            bubble.deleteLater()
            flashcard.bubble = None
            
            # State manager'dan temizle
            BubbleStateManager.cleanup(flashcard)
            
        except Exception:
            pass