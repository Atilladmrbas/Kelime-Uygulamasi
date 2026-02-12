# file: ui/boxes_panel/overlay_observer.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class OverlayObserver(QObject):
    """Kopya kart hareketlerini gözlemleyerek orijinal kart overlay'larını günceller"""
    
    copy_card_moved = pyqtSignal(int, int)  # original_card_id, target_box_id
    
    def __init__(self):
        super().__init__()
        self.original_cards = {}  # original_card_id -> [widget1, widget2, ...]
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._batch_update_overlays)
        self.update_timer.start(2000)
        self.db = None
    
    def register_original_card(self, card_widget):
        """Orijinal kart widget'ını kaydet"""
        if not hasattr(card_widget, 'card_id') or not card_widget.card_id:
            return
        
        card_id = card_widget.card_id
        if card_id not in self.original_cards:
            self.original_cards[card_id] = []
        
        if card_widget not in self.original_cards[card_id]:
            self.original_cards[card_id].append(card_widget)
            print(f"✅ [OverlayObserver] Kart kaydedildi: {card_id}")  # GEÇİCİ
    
    def unregister_original_card(self, card_widget):
        """Orijinal kart widget'ını kayıttan çıkar"""
        if not hasattr(card_widget, 'card_id') or not card_widget.card_id:
            return
        
        card_id = card_widget.card_id
        if card_id in self.original_cards:
            if card_widget in self.original_cards[card_id]:
                self.original_cards[card_id].remove(card_widget)
                print(f"✅ [OverlayObserver] Kart kaydı silindi: {card_id}")  # GEÇİCİ
            
            if not self.original_cards[card_id]:
                del self.original_cards[card_id]
    
    def notify_copy_moved(self, original_card_id, target_box_id):
        """Kopya kart hareket ettiğinde bildir - GÜÇLENDİRİLMİŞ"""
        print(f"🔵 [OverlayObserver] Kopya hareket etti - Orijinal: {original_card_id}, Kutu: {target_box_id}")
        
        # Önce kayıtlı kartları kontrol et
        updated = False
        if original_card_id in self.original_cards:
            for card_widget in self.original_cards[original_card_id]:
                if hasattr(card_widget, 'color_overlay') and card_widget.color_overlay:
                    try:
                        card_widget.color_overlay.update_for_card_move(target_box_id)
                        card_widget.color_overlay.show()
                        card_widget.color_overlay.raise_()
                        print(f"✅ [OverlayObserver] Kayıtlı kart güncellendi: {original_card_id}")
                        updated = True
                    except Exception as e:
                        print(f"❌ [OverlayObserver] Güncelleme hatası: {e}")
        
        # Kayıtlı değilse veya güncellenemediyse tüm widget'ları tara
        if not updated:
            print(f"🔍 [OverlayObserver] Widget taraması başlıyor: {original_card_id}")
            self._find_and_update_card(original_card_id, target_box_id)
        
        # 2 saniye sonra tekrar dene (geç yüklenen kartlar için)
        QTimer.singleShot(2000, lambda: self._delayed_update(original_card_id, target_box_id))

    def _delayed_update(self, original_card_id, target_box_id):
        """Gecikmeli güncelleme - geç yüklenen kartlar için"""
        print(f"⏰ [OverlayObserver] Gecikmeli güncelleme: {original_card_id}")
        self._find_and_update_card(original_card_id, target_box_id)
    
    def _find_and_update_card(self, original_card_id, target_box_id):
        """Tüm widget'ları tarayarak orijinal kartı bul ve güncelle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            from ui.words_panel.button_and_cards.flashcard_view import FlashCardView
            
            for widget in app.allWidgets():
                if isinstance(widget, FlashCardView):
                    if hasattr(widget, 'card_id') and widget.card_id == original_card_id:
                        if hasattr(widget, 'color_overlay') and widget.color_overlay:
                            widget.color_overlay.update_for_card_move(target_box_id)
                            print(f"✅ [OverlayObserver] Widget taraması ile güncellendi: {original_card_id}")  # GEÇİCİ
                            
                            # Otomatik kaydet
                            self.register_original_card(widget)
                            break
        except ImportError:
            pass
        except Exception as e:
            print(f"❌ [OverlayObserver] Hata: {e}")  # GEÇİCİ
    
    def _batch_update_overlays(self):
        """Toplu overlay güncellemesi"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            from ui.words_panel.button_and_cards.flashcard_view import FlashCardView
            
            for widget in app.allWidgets():
                if isinstance(widget, FlashCardView):
                    if hasattr(widget, 'is_copy_card') and not widget.is_copy_card:
                        if hasattr(widget, 'color_overlay') and widget.color_overlay:
                            widget.color_overlay.schedule_lazy_update()
        except ImportError:
            pass
        except Exception:
            pass


# Global observer instance
_global_observer = None

def get_overlay_observer():
    """Global overlay observer'ı getir"""
    global _global_observer
    if _global_observer is None:
        _global_observer = OverlayObserver()
        print("✅ [OverlayObserver] Global observer oluşturuldu")  # GEÇİCİ
    return _global_observer