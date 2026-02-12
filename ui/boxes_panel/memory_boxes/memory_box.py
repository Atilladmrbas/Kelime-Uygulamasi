# ui/boxes_panel/memory_boxes/memory_box.py - İşlevsel Kodlar
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt, QTimer
import traceback
import random

# ✅ Tasarım sınıfını import et
from .memory_boxes_design_and_message_boxes import MemoryBoxDesign, BOX_BORDER_COLORS, BOX_TITLES

# ✅ Kart animasyon manager'ını import et
try:
    from ..card_animation_manager import CardAnimationManager
except ImportError:
    CardAnimationManager = None

# ✅ DRAG_DROP_MANAGER IMPORT'U - PARENT KLASÖRDEN AL
try:
    from ..drag_drop_manager.decorators import drop_target
    from ..drag_drop_manager.base_manager import DropTarget, get_drag_drop_manager
except ImportError:
    # Minimal fallback definitions
    class DropTarget:
        MEMORY_BOX = "memory_box"
    
    def drop_target(target_type):
        def decorator(cls):
            return cls
        return decorator
    
    def get_drag_drop_manager():
        return None

@drop_target(DropTarget.MEMORY_BOX)
class MemoryBox(MemoryBoxDesign):
    """Tek bir ezber kutu widget'ı - İşlevsel kodlar"""
    
    def __init__(self, title, bg, border, box_id, db=None):
        super().__init__(title, bg, border, box_id)
        
        self.db = db
        
        # ✅ DRAG STATE TRACKING - GÜNCELLENDİ
        self._is_drag_over = False
        self._last_drag_enter_time = 0
        
        # ✅ ORJİNAL BORDER RENGİNİ KAYDET
        self.original_border_color = border
        
        # ✅ NORMAL STİL - SADECE BORDER
        self._normal_style = f"""
            QFrame {{
                border: 3px solid {self.original_border_color};
                border-radius: 12px;
                background-color: #ffffff;
            }}
        """
        
        # ✅ DRAG OVER STİL - SADECE BORDER DEĞİŞSİN, ARKA PLAN AYNI KALSIN
        self._drag_over_style = f"""
            QFrame {{
                border: 3px dashed {self.original_border_color};
                border-radius: 12px;
                background-color: #ffffff !important;
            }}
        """
        
        self.setAcceptDrops(True)
        
        # Buton bağlantılarını kur
        self.btn.clicked.connect(self.show_card_immediately)
        self.reset_btn.clicked.connect(self.reset_box_confirm)
        
        self.current_card_widget = None
        
        # ✅ ANİMASYON MANAGER
        self.animation_manager = None
        
        # ✅ AUTOMATIC DRAG CLEANUP TIMER
        self.drag_cleanup_timer = QTimer()
        self.drag_cleanup_timer.timeout.connect(self._auto_cleanup_drag_style)
        self.drag_cleanup_timer.start(500)
        
        self.update_card_count()
        
        # ✅ BAŞLANGIÇTA NORMAL STİLİ UYGULA
        self._apply_normal_style()

    # ==================== DRAG-DROP EVENT'LERİ - GÜNCELLENDİ ====================
    
    def dragEnterEvent(self, event):
        """Drag olayını kabul et - GÜNCELLENDİ"""
        if event.mimeData().hasFormat("application/x-flashcard-operation"):
            event.acceptProposedAction()
            self._is_drag_over = True
            self._last_drag_enter_time = QTimer().remainingTime()
            # ✅ SADECE BORDER STİLİNİ DEĞİŞTİR
            self.setStyleSheet(self._drag_over_style)
            self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Drag hareket ederken - GÜNCELLENDİ"""
        if event.mimeData().hasFormat("application/x-flashcard-operation"):
            event.acceptProposedAction()
            if not self._is_drag_over:
                self._is_drag_over = True
                # ✅ SADECE BORDER STİLİNİ DEĞİŞTİR
                self.setStyleSheet(self._drag_over_style)
                self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Drag alanından çıkıldığında - GÜNCELLENDİ"""
        self._is_drag_over = False
        # ✅ HEMEN NORMAL STİLE DÖN
        self._apply_normal_style()
        event.accept()

    def dropEvent(self, event):
        """Kart bırakıldığında"""
        self._is_drag_over = False
        self._apply_normal_style()
        
        manager = get_drag_drop_manager()
        if not manager:
            event.ignore()
            return
        
        success = manager.process_drop(self, event, self.db)
        
        if success:
            # ============= OVERLAY BİLDİRİMİ - DÜZELTİLDİ =============
            try:
                import json
                from PyQt6.QtWidgets import QApplication
                
                mime_data = event.mimeData()
                if mime_data.hasFormat("application/x-flashcard-operation"):
                    data = json.loads(mime_data.data("application/x-flashcard-operation").data().decode())
                    
                    # 1. MIME data'dan original_card_id al
                    original_id = data.get('original_card_id')
                    
                    # 2. Eğer yoksa, kart ID'sinden bul
                    if not original_id:
                        card_id = data.get('card_id')
                        if card_id and self.db:
                            try:
                                cursor = self.db.conn.cursor()
                                cursor.execute("SELECT original_card_id FROM words WHERE id = ?", (card_id,))
                                row = cursor.fetchone()
                                if row and row[0]:
                                    original_id = row[0]
                                    print(f"🔍 DB'den original_card_id bulundu: {original_id}")
                            except Exception as e:
                                print(f"❌ DB sorgusu hatası: {e}")
                    
                    # BİLDİRİM GÖNDER
                    if original_id:
                        print(f"🚀 Overlay bildirimi: Orijinal={original_id}, Kutu={self.box_id}")
                        
                        from ui.boxes_panel.overlay_observer import get_overlay_observer
                        observer = get_overlay_observer()
                        observer.notify_copy_moved(original_id, self.box_id)
                        
            except Exception as e:
                print(f"❌ Overlay bildirimi hatası: {e}")
            # ============================================================
            
            QTimer.singleShot(50, self.update_card_count)
        
        event.acceptProposedAction()
        QTimer.singleShot(10, self._apply_normal_style)

    def _apply_normal_style(self):
        """Normal stili kesinlikle uygula - GÜNCELLENDİ"""
        self._is_drag_over = False
        current_style = self.styleSheet()
        
        if self._drag_over_style not in current_style and self._normal_style not in current_style:
            self.setStyleSheet(self._normal_style)
            self.repaint()
        elif self._drag_over_style in current_style:
            self.setStyleSheet(self._normal_style)
            self.repaint()

    def _force_normal_style(self):
        """Normal stili kesinlikle uygula (eski metod)"""
        self._apply_normal_style()

    def _auto_cleanup_drag_style(self):
        """Otomatik drag style temizleme"""
        if self._is_drag_over:
            current_time = QTimer().remainingTime()
            time_since_drag = abs(current_time - self._last_drag_enter_time)
            
            if time_since_drag > 2000:
                self._is_drag_over = False
                self._apply_normal_style()

    # ==================== KART ÇEKME İŞLEMLERİ ====================

    def show_card_immediately(self):
        """Kutudan rasgele bir KOPYA kart çek - ANİMASYON DESTEKLİ"""
        
        # Aynı anda sadece bir kart çekilebilir
        if self.is_drawing_card:
            return
        
        if self.current_card_widget is not None and self._is_card_widget_still_valid():
            msg = QMessageBox(self)
            msg.setWindowTitle("Önceki Kartı İşleyin")
            msg.setText("Önce çekilen kartı bir bekleme alanına taşıyın veya silin.")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                    font-family: 'Segoe UI';
                }
                QMessageBox QLabel {
                    color: #000000;
                    font-size: 13px;
                }
                QMessageBox QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px 15px;
                    color: #000000;
                    font-weight: 500;
                }
                QMessageBox QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            
            msg.exec()
            return
            
        if not self.db:
            return
        
        self.btn.setEnabled(False)
        self.is_drawing_card = True
            
        try:
            cards = self.db.get_undrawn_copy_cards_in_box(self.box_id)
            
            if not cards:
                self.btn.setEnabled(True)
                self.is_drawing_card = False
                return
            
            selected_card = random.choice(cards)
            card_id = selected_card.get('id')
            original_card_id = selected_card.get('original_card_id')
            
            success = False
            try:
                success = self.db.mark_copy_as_drawn(original_card_id, card_id, self.box_id)
            except Exception:
                pass
            
            if not success:
                self.btn.setEnabled(True)
                self.is_drawing_card = False
                return
            
            self.update_card_count()
            
            QTimer.singleShot(50, lambda: self._create_and_show_card(selected_card))
            
        except Exception:
            self.btn.setEnabled(True)
            self.is_drawing_card = False

    def _is_card_widget_still_valid(self):
        """Kart widget'ı hala geçerli mi kontrol et"""
        try:
            if self.current_card_widget is None:
                return False
            
            if not self.current_card_widget.parent():
                return False
            
            return self.current_card_widget.isVisible()
            
        except Exception:
            return False

    def _create_and_show_card(self, card_data):
        """Kart widget'ını oluştur ve ANİMASYON ile göster - KLON KONTROLLÜ"""
        try:
            # ✅ ÖNCE QApplication İMPORT ET
            from PyQt6.QtWidgets import QApplication
            
            # ✅ TEMEL KONTROLLER
            card_id = card_data.get('id')
            if not card_id:
                self.is_drawing_card = False
                self.btn.setEnabled(True)
                return
            
            print(f"🔵 [_create_and_show_card] Kart oluşturma başlıyor: {card_id}")
            
            # ✅ AKTİF WIDGET'LARI KONTROL ET - DAHA AZ AGGRESİF
            app = QApplication.instance()
            visible_duplicates = []
            
            if app:
                for widget in app.topLevelWidgets():  # Sadece top-level widget'lara bak
                    try:
                        if (hasattr(widget, 'card_id') and 
                            getattr(widget, 'card_id', None) == card_id and
                            widget.isVisible() and
                            widget.parent()):
                            
                            print(f"⚠️ [_create_and_show_card] Bu kart zaten görünür: {card_id}")
                            visible_duplicates.append(widget)
                            
                    except Exception:
                        continue
            
            # ✅ EĞER KART ZATEN GÖRÜNÜYORSA, ONU FOCUSLA VE ÇIK
            if visible_duplicates:
                for widget in visible_duplicates:
                    try:
                        widget.raise_()
                        widget.activateWindow()
                        widget.setFocus()
                    except:
                        pass
                
                self.btn.setEnabled(True)
                self.is_drawing_card = False
                return
            
            # ✅ IMPORT İÇİN DOĞRU YOLU BUL
            import sys
            import os
            
            # Mevcut dosyanın yolunu bul
            current_file = os.path.abspath(__file__)
            memory_boxes_dir = os.path.dirname(current_file)
            boxes_panel_dir = os.path.dirname(memory_boxes_dir)
            ui_dir = os.path.dirname(boxes_panel_dir)
            project_root = os.path.dirname(ui_dir)
            
            # Tüm gerekli yolları ekle
            for path in [project_root, ui_dir, boxes_panel_dir, memory_boxes_dir]:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            print(f"🔵 [_create_and_show_card] Import yolları eklendi")
            
            # ✅ RELATIVE IMPORT DENE, BAŞARISIZ OLURSA ABSOLUTE IMPORT
            try:
                from ..copy_flash_card import CopyFlashCardView
                print(f"✅ [_create_and_show_card] Relative import başarılı")
            except ImportError as e:
                print(f"⚠️ [_create_and_show_card] Relative import hatası: {e}")
                # Absolute import deneyelim
                try:
                    from ui.boxes_panel.copy_flash_card import CopyFlashCardView
                    print(f"✅ [_create_and_show_card] Absolute import başarılı")
                except ImportError as e2:
                    print(f"❌ [_create_and_show_card] Absolute import da başarısız: {e2}")
                    self.btn.setEnabled(True)
                    self.is_drawing_card = False
                    return
            
            boxes_design = self._find_boxes_design()
            if not boxes_design:
                print(f"❌ [_create_and_show_card] BoxesDesign bulunamadı")
                self.is_drawing_card = False
                self.btn.setEnabled(True)
                return

            print(f"✅ [_create_and_show_card] CopyFlashCardView oluşturuluyor...")
            
            # ✅ KART WIDGET'INI OLUŞTUR
            card_widget = CopyFlashCardView(
                data=card_data,
                parent=boxes_design,
                db=self.db
            )
            
            # ✅ KLON KONTROLÜNÜ DÜZELT - DAHA AZ RESTRİKTİF
            # Sadece aynı parent'ta ve görünür olan klonları kontrol et
            is_duplicate = False
            
            # Mevcut card widget'larını kontrol et
            if hasattr(boxes_design, 'drawn_cards'):
                for existing_card in boxes_design.drawn_cards:
                    try:
                        if (hasattr(existing_card, 'card_id') and 
                            existing_card.card_id == card_id and
                            existing_card.isVisible() and
                            existing_card.parent() == boxes_design):
                            print(f"⚠️ [_create_and_show_card] Aynı parent'ta zaten kart var")
                            is_duplicate = True
                            break
                    except Exception:
                        continue
            
            if is_duplicate:
                print(f"❌ [_create_and_show_card] Kart zaten gösteriliyor - iptal edildi")
                card_widget.deleteLater()
                self.btn.setEnabled(True)
                self.is_drawing_card = False
                return
            
            # ✅ KART ID'SİNİ DOĞRULA
            if not hasattr(card_widget, 'card_id') or not card_widget.card_id:
                print(f"⚠️ [_create_and_show_card] Kart ID'si atanmamış, bind_model çağrılıyor")
                card_widget.bind_model(card_data)
            
            print(f"✅ [_create_and_show_card] Kart oluşturuldu: {card_widget.card_id}")
            
            # ✅ DÜZELTİLDİ: on_card_removed_or_moved fonksiyonunu tanımla
            def on_card_removed_or_moved():
                """Kart kaldırıldığında/silindiğinde çağrılır"""
                print(f"🔵 [on_card_removed_or_moved] Kart temizleniyor")
                self.current_card_widget = None
                self.is_drawing_card = False
                QTimer.singleShot(100, self.update_card_count)
                QTimer.singleShot(100, lambda: self.btn.setEnabled(True))
            
            # Sinyalleri bağla
            card_widget.card_clicked.connect(on_card_removed_or_moved)
            
            if hasattr(card_widget, 'set_dragged_out_callback'):
                card_widget.set_dragged_out_callback(on_card_removed_or_moved)
            
            self.current_card_widget = card_widget
            
            # ✅ ANİMASYON MANAGER KONTROLÜ
            if CardAnimationManager:
                print(f"✅ [_create_and_show_card] Animasyon manager kullanılıyor")
                self.animation_manager = CardAnimationManager(self, boxes_design)
                self.animation_manager.show_copy_card_with_slide_animation(card_widget, card_data)
            else:
                print(f"⚠️ [_create_and_show_card] Animasyon manager yok, direkt ekleniyor")
                if hasattr(boxes_design, 'add_drawn_card'):
                    boxes_design.add_drawn_card(self, card_widget)
            
            self.btn.setEnabled(True)
            self.is_drawing_card = False
            
            print(f"✅ [_create_and_show_card] Kart başarıyla gösterildi")
            
        except Exception as e:
            print(f"❌ [_create_and_show_card] KRİTİK HATA: {e}")
            import traceback
            traceback.print_exc()
            self.btn.setEnabled(True)
            self.is_drawing_card = False
    
    def _ensure_card_visible(self, card_widget, parent_widget):
        """Kartın görünür olduğundan emin ol"""
        if not card_widget:
            return
        
        try:
            box_pos = self.mapTo(parent_widget, self.pos())
            card_widget.move(box_pos.x() + 50, box_pos.y() + self.height() + 10)
            
            card_widget.raise_()
            card_widget.repaint()
            
        except Exception:
            card_widget.move(200, 200)
            card_widget.raise_()
            card_widget.repaint()
    
    def _position_card(self, card_widget, parent_widget):
        """Kartın pozisyonunu ayarla"""
        try:
            if not card_widget or not parent_widget:
                return
                
            card_widget.move(100, 100)
            
            card_widget.raise_()
            card_widget.update()
            card_widget.repaint()
            
        except Exception:
            pass

    def _on_card_removed_or_moved(self, card_widget=None):
        """Kart silindiğinde veya bekleme alanına taşındığında çağrılır"""
        self.current_card_widget = None
        self.is_drawing_card = False
        QTimer.singleShot(100, self.update_card_count)
        QTimer.singleShot(100, lambda: self.btn.setEnabled(True))

    def clear_current_card(self):
        """Mevcut kartı UI'dan TAMAMEN temizle"""
        print(f"🔵 [clear_current_card] Başlıyor - current_card_widget: {self.current_card_widget}")
        
        if self.current_card_widget:
            try:
                # 1. Önce boxes_design'den kaldır
                boxes_design = self._find_boxes_design()
                if boxes_design and hasattr(boxes_design, 'remove_drawn_card'):
                    card_id = getattr(self.current_card_widget, 'card_id', None)
                    if card_id:
                        print(f"🔵 [clear_current_card] boxes_design'den kaldırılıyor: {card_id}")
                        boxes_design.remove_drawn_card(card_id)
                
                # 2. Parent'tan kaldır
                if self.current_card_widget.parent():
                    print(f"🔵 [clear_current_card] Parent'tan kaldırılıyor")
                    parent = self.current_card_widget.parent()
                    if parent.layout():
                        parent.layout().removeWidget(self.current_card_widget)
                
                # 3. Widget'ı gizle ve temizle
                print(f"🔵 [clear_current_card] Widget gizleniyor ve temizleniyor")
                self.current_card_widget.hide()
                self.current_card_widget.setParent(None)
                
                # 4. Delete later ile tamamen sil
                self.current_card_widget.deleteLater()
                
                print(f"✅ [clear_current_card] Kart UI'dan tamamen kaldırıldı")
                
            except Exception as e:
                print(f"❌ [clear_current_card] Hata: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.current_card_widget = None
                self.is_drawing_card = False
        
        # Butonu etkinleştir ve sayacı güncelle
        QTimer.singleShot(100, self.update_card_count)
        QTimer.singleShot(100, lambda: self.btn.setEnabled(True))

    # ==================== DİĞER METODLAR ====================

    def reset_box(self):
        """Kutudaki tüm KOPYA kartları sil"""
        if not self.db:
            return
            
        try:
            self.clear_current_card()
            
            copy_cards = self.db.get_copy_cards_in_box(self.box_id)
            
            if not copy_cards:
                return
                
            for card in copy_cards:
                card_id = card.get('id')
                if card_id:
                    try:
                        self.db.delete_word(card_id)
                    except Exception:
                        pass
            
            self.update_card_count()
            
        except Exception:
            pass

    def _find_boxes_design(self):
        """Parent zincirinde BoxesWindow'u bul"""
        parent = self.parent()
        while parent:
            class_name = parent.__class__.__name__
            if 'BoxesWindow' in class_name or 'BoxesDesign' in class_name:
                return parent
            parent = parent.parent()
        return None

    def update_card_count(self):
        """Kutudaki ÇEKİLMEMİŞ kopya kart sayısını göster"""
        if not self.db:
            self.count_lbl.setText("0")
            self.btn.setEnabled(False)
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM words 
                WHERE box = ? AND is_copy = 1 AND is_drawn = 0
            """, (self.box_id,))
            
            result = cursor.fetchone()
            undrawn_count = result[0] if result else 0
            
            self.count_lbl.setText(f"{undrawn_count}")
            
            is_enabled = undrawn_count > 0 and not self.is_drawing_card
            self.btn.setEnabled(is_enabled)
            
            self.count_lbl.update()
            self.btn.update()
            self.update()
            
        except Exception:
            self.btn.setEnabled(True)