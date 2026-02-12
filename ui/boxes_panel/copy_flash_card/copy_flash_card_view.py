from __future__ import annotations
import time
import json
from PyQt6.QtWidgets import QFrame, QPushButton, QWidget, QGraphicsOpacityEffect, QApplication
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QDrag, QPixmap, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QByteArray, QPoint
from .copy_drag_handle import CopyDragHandleIcon
from .copy_dynamic_field import CopyDynamicField
from .copy_dialogs import show_copy_delete_dialog

try:
    from ..drag_drop_manager.decorators import draggable_card
except ImportError:
    def draggable_card():
        def decorator(cls):
            original_mouse_press = cls.mousePressEvent
            original_mouse_move = cls.mouseMoveEvent
            
            def new_mouse_press(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_start_pos = event.position().toPoint()
                    event.accept()
                    return
                
                if original_mouse_press:
                    original_mouse_press(self, event)
            
            def new_mouse_move(self, event):
                if (event.buttons() & Qt.MouseButton.LeftButton and 
                    hasattr(self, '_drag_start_pos')):
                    manhattan_length = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                    if manhattan_length >= 10:
                        self._start_simple_drag(event)
                        self._drag_start_pos = None
                        return
                
                if original_mouse_move:
                    original_mouse_move(self, event)
            
            cls.mousePressEvent = new_mouse_press
            cls.mouseMoveEvent = new_mouse_move
            
            return cls
        return decorator

# Overlay observer import
try:
    from ui.boxes_panel.overlay_observer import get_overlay_observer
    OVERLAY_OBSERVER_AVAILABLE = True
except ImportError:
    OVERLAY_OBSERVER_AVAILABLE = False
    def get_overlay_observer(): return None

@draggable_card()
class CopyFlashCardView(QFrame):
    """KOPYA KARTLAR İÇİN ÖZELLEŞTİRİLMİŞ FLASH CARD VIEW"""
    
    card_clicked = pyqtSignal(object)
    card_moved_to_box = pyqtSignal(object, int)  # ✅ YENİ: (kopya_kart, hedef_kutu_id)
    
    # GLOBAL DRAG TAKİP - TÜM İNSTANCE'LAR İÇİN
    _global_dragging_cards = set()  # {card_id1, card_id2, ...}
    
    def __init__(self, data=None, parent=None, db=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)

        self.data = data
        self.db = db
        self.card_id = None
        self.box_id = None
        self.bucket_id = 0
        self.front = True
        self.bubble_open = False
        
        self.is_copy_card = True
        self.original_card_id = None
        
        self.drag_clone = None
        self._was_transparent = False
        self._drag_start_pos = None
        self._is_dragging_from_icon = False
        self._drag_in_progress = False
        
        self.is_in_waiting_area = False
        self._setup_drag_for_waiting_area()
        
        self.teleporter = None
        
        self.W, self.H = 260, 120
        self.setFixedSize(self.W, self.H)
        
        self.drag_icon = CopyDragHandleIcon(self)
        
        self.front_fields = []
        self.back_fields = []
        
        self.plus_front = None
        self.plus_back = None
        
        self.flip_btn = QPushButton("↺", self)
        self.del_btn = QPushButton("🗑", self)
        self.note_btn = QPushButton("T", self)
        
        for btn in (self.flip_btn, self.del_btn, self.note_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self._apply_action_button_style(btn)
        
        self.flip_btn.clicked.connect(self.toggle)
        self.del_btn.clicked.connect(self.on_delete_clicked)
        self.note_btn.clicked.connect(self.toggle_bubble)
        
        self.sync_manager = None
        
        if data is None:
            self._create_field(True, "")
            self._create_field(False, "")
        else:
            self._initial_bind_model(data)
        
        self.bubble = None
        self._initialize_bubble()
        
        if data is not None:
            self._final_bind_model(data)
        
        self._relayout()
        
        if data is None:
            self.is_newly_created = False
    
    def _initial_bind_model(self, model):
        """İlk temel binding - bubble'dan önce"""
        if not model: 
            return
            
        if isinstance(model, dict):
            card_id = model.get("id")
            self.box_id = model.get("box_id", model.get("box"))
            self.bucket_id = model.get("bucket", 0)
            detail_raw = model.get("detail", "{}")
            english = model.get("english", "")
            turkish = model.get("turkish", "")
            is_copy = model.get("is_copy", 1) == 1
            self.original_card_id = model.get("original_card_id")
        else:
            card_id = getattr(model, "id", None)
            self.box_id = getattr(model, "box_id", getattr(model, "box", None))
            self.bucket_id = getattr(model, "bucket", 0)
            detail_raw = getattr(model, "detail", "{}")
            english = getattr(model, "english", "")
            turkish = getattr(model, "turkish", "")
            is_copy = getattr(model, "is_copy", True)
            self.original_card_id = getattr(model, "original_card_id", None)
        
        self.data = model
        self.card_id = card_id
        self.is_copy_card = is_copy
        
        current_front_text = self.front_fields[0].text() if self.front_fields else ""
        current_back_text = self.back_fields[0].text() if self.back_fields else ""
        
        front_texts = []
        back_texts = []
        
        try:
            if detail_raw and detail_raw.strip() and detail_raw != "{}":
                detail = json.loads(detail_raw)
                front_texts = detail.get("front_fields", [])
                back_texts = detail.get("back_fields", [])
        except Exception:
            front_texts = []
            back_texts = []
        
        if not front_texts:
            if english:
                front_texts = [english]
            elif current_front_text:
                front_texts = [current_front_text]
            else:
                front_texts = [""]
        
        if not back_texts:
            if turkish:
                back_texts = [turkish]
            elif current_back_text:
                back_texts = [current_back_text]
            else:
                back_texts = [""]
        
        for field in self.front_fields + self.back_fields:
            try:
                field.hide()
                field.deleteLater()
            except:
                pass
        
        self.front_fields.clear()
        self.back_fields.clear()
        
        for text in front_texts:
            field = self._create_field(True, str(text) if text else "")
        
        for text in back_texts:
            field = self._create_field(False, str(text) if text else "")

    def _find_boxes_design(self):
        """Parent zincirinde BoxesWindow'u bul"""
        try:
            parent = self.parent()
            depth = 0
            while parent and depth < 20:
                class_name = parent.__class__.__name__
                if 'BoxesWindow' in class_name or 'BoxesDesign' in class_name:
                    return parent
                parent = parent.parent()
                depth += 1
            return None
        except Exception:
            return None
    
    def _initialize_bubble(self):
        """Bubble'ı başlat"""
        try:
            from .copy_bubble.copy_note_bubble import CopyNoteBubble
            
            if self.card_id and self.card_id in CopyNoteBubble._global_bubble_instances:
                existing_bubble = CopyNoteBubble._global_bubble_instances[self.card_id]
                self.bubble = existing_bubble
                return
            
            is_in_waiting_area = getattr(self, 'is_in_waiting_area', False)
            
            if is_in_waiting_area:
                parent = self.window() if self.window() else self
            else:
                parent = self._find_boxes_design()
                if not parent:
                    parent = self.window() if self.window() else self
            
            self.bubble = CopyNoteBubble(
                parent=parent,
                card_view=self,
                db=self.db
            )
            
        except ImportError:
            try:
                from ui.words_panel.button_and_cards.bubble.note_bubble import NoteBubble
                self.bubble = NoteBubble(
                    parent=self.window() if self.window() else self,
                    card_view=self,
                    state=None,
                    db=self.db,
                    is_copy=True
                )
            except Exception:
                self.bubble = None
        except Exception:
            self.bubble = None

        if self.bubble:
            self.bubble.hide()
    
    def _final_bind_model(self, model):
        """Tam binding - bubble oluştuktan sonra"""
        if self.bubble and hasattr(self.bubble, 'original_card_id'):
            self.bubble.original_card_id = self.original_card_id
        
        if self.original_card_id and self.card_id:
            try:
                self._sync_from_original_immediately(self.original_card_id)
            except Exception:
                pass
    
    def bind_model(self, model):
        """Kopya kartlar için model binding"""
        if not model: 
            return
        
        self._initial_bind_model(model)
        
        if self.bubble is None:
            self._initialize_bubble()
        
        self._final_bind_model(model)
        
        self._relayout()
        self.update_fields()
    
    def _apply_light_drag_effect(self):
        """Hafif drag efekti"""
        try:
            self.setWindowOpacity(0.8)
            self.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border: 2px dashed #888888;
                    border-radius: 8px;
                }
            """)
            self.update()
        except Exception:
            pass
    
    def _remove_drag_effect_immediately(self):
        """Drag efektini hemen kaldır"""
        try:
            self.setWindowOpacity(1.0)
            self.setStyleSheet("")
            self.setGraphicsEffect(None)
            self.update()
            self.repaint()
        except Exception:
            pass
    
    def _cleanup_drag_clones_after_drop(self):
        """Drag klonlarını temizle"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            current_id = id(self)
            current_card_id = self.card_id
            
            widgets_to_remove = []
            
            for widget in app.allWidgets():
                try:
                    if (hasattr(widget, 'card_id') and 
                        getattr(widget, 'card_id', None) == current_card_id and
                        hasattr(widget, 'is_copy_card') and widget.is_copy_card):
                        
                        widget_id = id(widget)
                        
                        if widget_id != current_id:
                            is_clone = (
                                not widget.isVisible() or
                                widget.windowOpacity() < 0.5 or
                                not widget.parent()
                            )
                            
                            if is_clone:
                                widgets_to_remove.append(widget)
                                
                except Exception:
                    continue
            
            for widget in widgets_to_remove:
                try:
                    widget.hide()
                    
                    parent = widget.parent()
                    if parent:
                        if hasattr(parent, 'layout') and parent.layout():
                            parent.layout().removeWidget(widget)
                    
                    widget.setParent(None)
                    widget.deleteLater()
                    
                except Exception:
                    pass
            
        except Exception:
            pass
    
    def _safe_self_destruct(self):
        """Widget'ı güvenli yok et"""
        try:
            try:
                self.disconnect()
            except:
                pass
            
            if self.bubble:
                try:
                    if hasattr(self.bubble, 'cleanup'):
                        self.bubble.cleanup()
                    else:
                        self.bubble.hide()
                        self.bubble.setParent(None)
                        self.bubble.deleteLater()
                    self.bubble = None
                except Exception:
                    pass
            
            for child in self.children():
                try:
                    if hasattr(child, 'hide'):
                        child.hide()
                    child.setParent(None)
                except:
                    pass
            
            parent = self.parent()
            if parent:
                if hasattr(parent, 'layout') and parent.layout():
                    try:
                        parent.layout().removeWidget(self)
                    except:
                        pass
            
            self.hide()
            self.setParent(None)
            
            QTimer.singleShot(100, self.deleteLater)
            
        except Exception:
            pass
    
    def _setup_drag_for_waiting_area(self):
        """Bekleme alanları için drag özelliğini kur"""
        parent = self.parent()
        while parent:
            if hasattr(parent, '__class__') and 'WaitingAreaWidget' in parent.__class__.__name__:
                self.is_in_waiting_area = True
                break
            parent = parent.parent()
        
        if self.is_in_waiting_area:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if hasattr(self, 'drag_icon'):
                self.drag_icon.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def reset_drag_effect(self):
        """Drag efektini sıfırla"""
        try:
            self.setGraphicsEffect(None)
            self.setWindowOpacity(1.0)
            self.setStyleSheet("")
            
            def apply_default_style():
                try:
                    self.setStyleSheet("""
                        QFrame {
                            background-color: #f5f5f5;
                            border: 1px solid #cccccc;
                            border-radius: 8px;
                        }
                    """)
                    self.update()
                except:
                    pass
            
            QTimer.singleShot(10, apply_default_style)
            self.repaint()
            self.update()
            
        except Exception:
            pass
    
    def paintEvent(self, event):
        """Kopya kartlar için özel paint"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.windowOpacity() < 0.1:
            painter.setOpacity(0.05)
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor("#f5f5f5"))
            grad.setColorAt(1, QColor("#e0e0e0"))
            
            painter.setBrush(grad)
            painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)
            
        else:
            painter.setPen(QColor(180, 180, 180))
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0, QColor("#f5f5f5"))
            grad.setColorAt(1, QColor("#e0e0e0"))
            
            painter.setBrush(grad)
            painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)
            
            painter.save()
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(self.width() - 50, 15, "KOPYA")
            painter.restore()
        
        painter.end()
    
    def mousePressEvent(self, event):
        """Kopya kartlar için mouse press"""
        self.setFocus()
        
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_in_waiting_area and not self.drag_icon.underMouse():
                self.card_clicked.emit(self)
                event.accept()
                return
            
            self._drag_start_pos = event.position().toPoint()
            self._is_dragging_from_icon = self.drag_icon.underMouse()
            
            if self.is_in_waiting_area and not self._is_dragging_from_icon:
                self._is_dragging_from_icon = True
            
            event.accept()
            return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Mouse hareket ettiğinde"""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Kopya kartlar için mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = None
            self._is_dragging_from_icon = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def _start_simple_drag(self, event):
        """Basit drag başlatma"""
        try:
            if not self.card_id:
                return
            
            if self.card_id in self.__class__._global_dragging_cards:
                return
            
            if not self.isVisible() or not self.isEnabled() or not self.parent():
                return
            
            if hasattr(self, '_drag_in_progress') and self._drag_in_progress:
                return
            
            self.__class__._global_dragging_cards.add(self.card_id)
            self._drag_in_progress = True
            
            pixmap = self.grab()
            if pixmap.isNull():
                self._cleanup_drag()
                return
            
            mime_data = QMimeData()
            drag_data = {
                'card_id': self.card_id,
                'card_type': 'copy',
                'source_type': 'waiting_area' if self.is_in_waiting_area else 'memory_box',
                'source_widget_id': id(self),
                'is_direct_drag': True,
                'prevent_cloning': True,
                'original_card_id': self.original_card_id,  # ✅ BURASI ÇOK ÖNEMLİ
                'timestamp': time.time()
            }
            
            # DEBUG: original_card_id kontrolü
            print(f"🐉 DRAG BAŞLATILDI - Kart ID: {self.card_id}, Orijinal ID: {self.original_card_id}")
            
            mime_data.setData(
                "application/x-flashcard-operation",
                QByteArray(json.dumps(drag_data).encode())
            )
            
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            if not pixmap.isNull():
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.position().toPoint())
            
            self._apply_light_drag_effect()
            
            result = drag.exec(Qt.DropAction.MoveAction)
            
            self._cleanup_drag()
            
            if result == Qt.DropAction.MoveAction:
                if self.is_in_waiting_area:
                    self._safe_self_destruct()
                else:
                    self.reset_drag_effect()
            else:
                self.reset_drag_effect()
                    
        except Exception as e:
            print(f"❌ Drag hatası: {e}")
            self._cleanup_drag()
    
    def _cleanup_drag(self):
        """Drag sonrası temizlik"""
        try:
            if hasattr(self, 'card_id') and self.card_id:
                self.__class__._global_dragging_cards.discard(self.card_id)
            
            self._remove_drag_effect_immediately()
            
            if hasattr(self, '_drag_in_progress'):
                self._drag_in_progress = False
            
        except Exception:
            pass
    
    def _sync_from_original_immediately(self, original_id):
        """Orijinal kartın son halini hemen senkronize et"""
        try:
            if not self.db:
                return
            
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT english, turkish, detail FROM words WHERE id = ?",
                (original_id,)
            )
            row = cursor.fetchone()
            
            if row:
                english, turkish, detail = row
                
                if self.front_fields:
                    self.front_fields[0].setText(english)
                    if hasattr(self.front_fields[0], '_original_text'):
                        self.front_fields[0]._original_text = english
                
                if self.back_fields:
                    self.back_fields[0].setText(turkish)
                    if hasattr(self.back_fields[0], '_original_text'):
                        self.back_fields[0]._original_text = turkish
                
                if detail and detail.strip() and detail != "{}":
                    try:
                        detail_dict = json.loads(detail)
                        front_texts = detail_dict.get('front_fields', [])
                        back_texts = detail_dict.get('back_fields', [])
                        
                        for i, text in enumerate(front_texts):
                            if i < len(self.front_fields):
                                self.front_fields[i].setText(text)
                        
                        for i, text in enumerate(back_texts):
                            if i < len(self.back_fields):
                                self.back_fields[i].setText(text)
                                
                    except Exception:
                        pass
                
                self._relayout()
                
        except Exception:
            pass
    
    # ============== OVERLAY BİLDİRİM METODU ==============
    def notify_moved_to_box(self, box_id):
        """Kopya kart bir kutuya taşındığında orijinal kartın overlay'ini güncelle"""
        if not self.original_card_id:
            return
            
        # 1. Signal ile bildir
        self.card_moved_to_box.emit(self, box_id)
        
        # 2. Overlay observer ile bildir
        if OVERLAY_OBSERVER_AVAILABLE:
            try:
                observer = get_overlay_observer()
                if observer:
                    observer.notify_copy_moved(self.original_card_id, box_id)
            except Exception:
                pass
        
        # 3. Doğrudan DB'den kontrol et (acil durum için)
        try:
            if self.db and self.original_card_id:
                # Tüm orijinal kart widget'larını bul ve güncelle
                app = QApplication.instance()
                if app:
                    from ui.words_panel.button_and_cards.flashcard_view import FlashCardView
                    for widget in app.allWidgets():
                        if isinstance(widget, FlashCardView):
                            if hasattr(widget, 'card_id') and widget.card_id == self.original_card_id:
                                if hasattr(widget, 'color_overlay') and widget.color_overlay:
                                    widget.color_overlay.update_for_card_move(box_id)
        except Exception:
            pass
    # ====================================================
    
    def _relayout(self):
        """Kopya kartlar için layout"""
        fw, fh, gap = 180, 22, 8
        cx = (self.W - fw) // 2

        def place(fields):
            n = len(fields)
            total_h = n * fh + (n - 1) * gap
            start_y = (self.H - total_h) // 2
            for i, f in enumerate(fields):
                f.setGeometry(cx, int(start_y + i * (fh + gap)), fw, fh)

        place(self.front_fields)
        place(self.back_fields)

        self.flip_btn.setGeometry(self.W - 35, self.H - 28, 30, 24)
        self.del_btn.setGeometry(5, self.H - 28, 30, 24)
        self.note_btn.setGeometry(self.W - 35, 5, 30, 24)
        self.drag_icon.move(6, 6)

        self.update_fields()
        
        self.note_btn.raise_()
        self.flip_btn.raise_()
        self.del_btn.raise_()
        self.drag_icon.raise_()
    
    def toggle(self):
        """Kopya kartları çevir"""
        self.front = not self.front
        self._relayout()
    
    def update_fields(self):
        """Kopya kart field'larını güncelle"""
        for f in self.front_fields: 
            f.setVisible(self.front)
        for f in self.back_fields: 
            f.setVisible(not self.front)
    
    def toggle_bubble(self):
        """Kopya kartlarda bubble"""
        if not self.card_id:
            return
        
        if not self._is_widget_still_valid():
            return
        
        if self.bubble is None:
            self._initialize_bubble()
        
        if not self.bubble:
            return
        
        try:
            from ui.words_panel.button_and_cards.bubble.bubble_opening import BubbleStateManager
            bubble_is_open = BubbleStateManager.get_bubble_state(self)
            
            if not bubble_is_open:
                self.bubble._anchor_card = self
                
                if hasattr(self.bubble, 'open_with_animation'):
                    self.bubble.open_with_animation()
                else:
                    self.bubble.show()
                    self.bubble.raise_()
                    
                    main_window = self.window()
                    if main_window:
                        self.bubble.setParent(main_window)
                        card_global_pos = self.mapToGlobal(QPoint(0, 0))
                        bubble_global_pos = main_window.mapFromGlobal(card_global_pos)
                        self.bubble.move(bubble_global_pos + QPoint(self.width() + 12, 0))
            else:
                if hasattr(self.bubble, 'close_with_animation'):
                    self.bubble.close_with_animation()
                else:
                    self.bubble.hide()
                    
        except RuntimeError:
            if self.bubble:
                try:
                    self.bubble.cleanup()
                except:
                    pass
                self.bubble = None
        except Exception:
            pass

    def _is_widget_still_valid(self):
        """Widget'ın hala geçerli olup olmadığını kontrol et"""
        try:
            test = self.objectName()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False
    
    def on_delete_clicked(self):
        """Kopya kart silme butonu"""
        if not self.card_id or not self.db:
            return
        
        show_copy_delete_dialog(self, self)

    def _remove_self(self):
        """Kendini widget tree'den kaldır"""
        try:
            if self.parent():
                parent_layout = self.parent().layout()
                if parent_layout:
                    parent_layout.removeWidget(self)
                
                self.hide()
                self.setParent(None)
                QTimer.singleShot(100, self.deleteLater)
        except Exception:
            pass
    
    def _apply_action_button_style(self, btn):
        """Kopya kart buton stilleri"""
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.8);
                border: 1px solid rgba(0,0,0,0.15);
                border-radius: 6px;
                font-size: 13px;
                color: #555;
            }
            QPushButton:hover { 
                background: #ffffff; 
                border: 1px solid #888; 
            }
        """)
    
    def _create_field(self, is_front, text=""):
        """Kopya kartlar için field oluştur"""
        fld = CopyDynamicField(self)
        fld.setText(str(text).strip() if text else "")
        fld.setReadOnly(True)
        fld.setCursor(Qt.CursorShape.ArrowCursor)
        
        if is_front:
            self.front_fields.append(fld)
        else:
            self.back_fields.append(fld)
        
        return fld
    
    def get_card_data(self):
        """Kopya kart verilerini dictionary olarak döndür"""
        return {
            'id': self.card_id,
            'english': self.front_fields[0].text() if self.front_fields else '',
            'turkish': self.back_fields[0].text() if self.back_fields else '',
            'detail': json.dumps({
                'front_fields': [f.text() for f in self.front_fields],
                'back_fields': [f.text() for f in self.back_fields]
            }) if self.front_fields or self.back_fields else '{}',
            'box_id': self.box_id,
            'bucket': self.bucket_id,
            'is_copy': True
        }
    
    def _on_card_text_updated(self, original_id, updates):
        """Orijinal kart metinleri güncellendiğinde çağrılır"""
        try:
            if not hasattr(self, 'sync_manager') or not self.sync_manager:
                return
                
            my_original = self.sync_manager.get_original_of_copy(self.card_id)
            
            if my_original != original_id:
                return
            
            if 'english' in updates:
                new_text = str(updates['english'])
                
                if hasattr(self, 'front_fields') and self.front_fields:
                    if len(self.front_fields) > 0:
                        current_text = self.front_fields[0].text()
                        if current_text != new_text:
                            self.front_fields[0].setText(new_text)
            
            if 'turkish' in updates:
                new_text = str(updates['turkish'])
                
                if hasattr(self, 'back_fields') and self.back_fields:
                    if len(self.back_fields) > 0:
                        current_text = self.back_fields[0].text()
                        if current_text != new_text:
                            self.back_fields[0].setText(new_text)
            
            if 'detail' in updates:
                detail_json = updates['detail']
                if detail_json and detail_json.strip():
                    try:
                        detail = json.loads(detail_json)
                        front_texts = detail.get('front_fields', [])
                        back_texts = detail.get('back_fields', [])
                        
                        if hasattr(self, 'front_fields'):
                            for i, text in enumerate(front_texts):
                                text_str = str(text)
                                if i < len(self.front_fields):
                                    if self.front_fields[i].text() != text_str:
                                        self.front_fields[i].setText(text_str)
                        
                        if hasattr(self, 'back_fields'):
                            for i, text in enumerate(back_texts):
                                text_str = str(text)
                                if i < len(self.back_fields):
                                    if self.back_fields[i].text() != text_str:
                                        self.back_fields[i].setText(text_str)
                                        
                    except Exception:
                        pass
            
            self.update()
            
            if hasattr(self, '_relayout'):
                self._relayout()
            
            if hasattr(self, 'update_fields'):
                self.update_fields()
            
            if hasattr(self, 'data') and self.data:
                try:
                    if isinstance(self.data, dict):
                        if 'english' in updates:
                            self.data['english'] = updates['english']
                        if 'turkish' in updates:
                            self.data['turkish'] = updates['turkish']
                        if 'detail' in updates:
                            self.data['detail'] = updates['detail']
                except Exception:
                    pass
            
        except Exception:
            pass
    
    def _on_bubble_content_updated(self, original_id, html_content):
        """Orijinal kart bubble'ı güncellendiğinde çağrılır"""
        try:
            my_original = self.sync_manager.get_original_of_copy(self.card_id) if self.sync_manager else None
            if my_original != original_id:
                return
            
            if self.bubble and self.bubble.isVisible():
                if hasattr(self.bubble, 'on_original_bubble_updated'):
                    self.bubble.on_original_bubble_updated(original_id, html_content)
                elif hasattr(self.bubble, 'text'):
                    self.bubble.text.setHtml(html_content)
            
        except Exception:
            pass
    
    def cleanup(self):
        """Temizlik yap"""
        try:
            if self.bubble:
                try:
                    if hasattr(self.bubble, '_anchor_card'):
                        self.bubble._anchor_card = None
                    
                    if hasattr(self.bubble, 'cleanup'):
                        self.bubble.cleanup()
                    else:
                        self.bubble.hide()
                        self.bubble.setParent(None)
                        self.bubble.deleteLater()
                except Exception:
                    pass
                finally:
                    self.bubble = None
            
            if self.card_id and self.card_id in self.__class__._global_dragging_cards:
                self.__class__._global_dragging_cards.discard(self.card_id)
                
            try:
                from ui.words_panel.button_and_cards.bubble.bubble_opening import BubbleStateManager
                BubbleStateManager.cleanup(self)
            except:
                pass
            
        except Exception:
            pass