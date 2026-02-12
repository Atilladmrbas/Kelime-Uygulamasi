"""
copy_bubble/copy_note_bubble.py
KOPYA KARTLAR İÇİN ÖZELLEŞTİRİLMİŞ BUBBLE
- Sadece okuma modu
- Kırmızı border
- Gerçek kartlarla aynı animasyon ve davranışlar
- ✅ CopyBubbleSyncManager ile senkronizasyon
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer, QEvent, QObject
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QRect, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QApplication

from ui.words_panel.button_and_cards.bubble.bubble_text import BubbleText
from ui.words_panel.button_and_cards.bubble.bubble_opening import (
    BubbleStateManager, place_bubble_next_to_card_fast
)

from .copy_bubble_sync import CopyBubbleSyncManager


class CopyNoteBubble(QWidget):
    """KOPYA KARTLAR İÇİN ÖZELLEŞTİRİLMİŞ BUBBLE - SADECE GÖRSEL VE DAVRANIŞ"""
    
    bubble_closed = pyqtSignal()
    resized = pyqtSignal(int, int)
    
    MIN_W = 320
    MIN_H = 200
    SCREEN_PAD = 24
    CONTENT_PAD_W = 48
    CONTENT_PAD_H = 48
    
    _global_bubble_instances = {}
    
    def __init__(self, parent=None, card_view=None, db=None):
        super().__init__(parent)
        
        self.db = db
        self.card_view = card_view
        self.card_id = card_view.card_id if card_view else None
        self.original_card_id = None
        
        if self.card_id and self.card_id in self.__class__._global_bubble_instances:
            existing_bubble = self.__class__._global_bubble_instances[self.card_id]
            self.__dict__ = existing_bubble.__dict__
            self.hide()
            self.setParent(None)
            QTimer.singleShot(0, self.deleteLater)
            return
        
        self._is_clone = False
        
        if self.card_id and self.db:
            self._find_original_card_id()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self._read_only = True
        self._is_copy_bubble = True
        self._bubble_open = False
        self._animating = False
        self._close_filter = None
        self._anchor_card = card_view
        
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.resize(self.MIN_W, self.MIN_H)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        
        self.text = BubbleText(self)
        self.text.setReadOnly(True)
        self.text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        if hasattr(self.text, 'toolbar'):
            self.text.toolbar.setEnabled(False)
            self.text.toolbar.hide()
        
        layout.addWidget(self.text)
        
        self.text.document().contentsChanged.connect(self._auto_resize_to_text)
        
        if self.card_id and not self._is_clone:
            self.__class__._global_bubble_instances[self.card_id] = self
        
        self._register_to_sync_manager()
        
        if self.card_id and not self._is_clone:
            QTimer.singleShot(100, self._load_content_delayed)
    
    def _register_to_sync_manager(self):
        try:
            self.sync_manager = CopyBubbleSyncManager.instance()
            
            if self.card_id and self.original_card_id:
                self.sync_manager.register_copy_bubble(
                    copy_card_id=self.card_id,
                    original_card_id=self.original_card_id,
                    bubble_widget=self
                )
        
        except Exception:
            self.sync_manager = None
    
    def _find_original_card_id(self):
        try:
            if not self.card_id or not self.db:
                return
            
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT original_card_id FROM words WHERE id=?", (self.card_id,))
            row = cursor.fetchone()
            
            if row and row[0]:
                self.original_card_id = row[0]
        
        except Exception:
            pass
    
    def _load_content_delayed(self):
        try:
            if not self.card_id:
                return
            
            if self.original_card_id:
                from ui.words_panel.button_and_cards.bubble.bubble_persistence import load_bubble
                
                original_data = load_bubble(self.original_card_id)
                
                if original_data and original_data.get("html"):
                    html = original_data.get("html", "")
                    w = max(self.MIN_W, int(original_data.get("width", self.MIN_W)))
                    h = max(self.MIN_H, int(original_data.get("height", self.MIN_H)))
                    
                    self.text.setHtml(html)
                    self.resize(w, h)
                else:
                    self.text.setHtml("<p></p>")
            else:
                self.text.setHtml("<p></p>")
        
        except Exception:
            self.text.setHtml("<p></p>")
    
    def _auto_resize_to_text(self):
        try:
            if not hasattr(self, 'text'):
                return
                
            text_widget = self.text
            had_focus = text_widget.hasFocus()

            fm = text_widget.fontMetrics()
            plain = text_widget.document().toPlainText()
            lines = plain.splitlines() or [""]

            max_line_width = max(fm.horizontalAdvance(line) for line in lines)
            content_w = max_line_width + self.CONTENT_PAD_W

            line_height = fm.lineSpacing()
            content_h = (len(lines) * line_height) + self.CONTENT_PAD_H

            target_w = max(self.MIN_W, content_w)
            target_h = max(self.MIN_H, content_h)

            geo = self.geometry()
            screen = self.window().screen().availableGeometry()

            x, y = geo.x(), geo.y()
            cur_w, cur_h = geo.width(), geo.height()

            dw = target_w - cur_w
            if dw != 0:
                if dw > 0:
                    space_right = screen.right() - geo.right()
                    space_left = geo.left() - screen.left()

                    if space_right >= dw:
                        pass
                    elif space_left >= dw:
                        x -= dw
                    else:
                        dw = min(dw, space_left + space_right)
                        x -= dw // 2
                        target_w = cur_w + dw
                else:
                    target_w = max(self.MIN_W, target_w)

            dh = target_h - cur_h
            if dh != 0:
                if dh > 0:
                    space_down = screen.bottom() - geo.bottom()
                    space_up = geo.top() - screen.top()

                    if space_down >= dh:
                        pass
                    elif space_up >= dh:
                        y -= dh
                    else:
                        dh = min(dh, space_up + space_down)
                        y -= dh // 2
                        target_h = cur_h + dh
                else:
                    target_h = max(self.MIN_H, target_h)

            max_w_here = max(self.MIN_W, (screen.right() - x - self.SCREEN_PAD))
            max_h_here = max(self.MIN_H, (screen.bottom() - y - self.SCREEN_PAD))
            target_w = min(target_w, max_w_here)
            target_h = min(target_h, max_h_here)

            if target_w != cur_w or target_h != cur_h or x != geo.x() or y != geo.y():
                self.setGeometry(x, y, target_w, target_h)
                if had_focus:
                    QTimer.singleShot(0, text_widget.setFocus)

                QTimer.singleShot(0, self._snap_back_next_to_card)
                
        except Exception:
            pass
    
    def _snap_back_next_to_card(self):
        try:
            if self._animating:
                return
                
            card = getattr(self, "_anchor_card", None)
            parent = self.parentWidget() or self.parent()

            if not card or not parent:
                return

            place_bubble_next_to_card_fast(self, card, parent)

        except Exception:
            pass
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        radius = 18
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawRoundedRect(self.rect(), radius, radius)
        
        pen = QPen(QColor(220, 53, 69))
        pen.setWidth(3)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = self.rect().adjusted(2, 2, -2, -2)
        p.drawRoundedRect(rect, radius, radius)
        
        p.end()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        width = event.size().width()
        height = event.size().height()
        
        self.resized.emit(width, height)
    
    def closeEvent(self, event):
        if hasattr(self, 'text') and self.text:
            if hasattr(self.text, 'toolbar'):
                toolbar = self.text.toolbar
                if toolbar:
                    if hasattr(toolbar, 'color_popup') and toolbar.color_popup:
                        toolbar.color_popup.hide()
                    
                    toolbar.close_all(force=True)
        
        if hasattr(self, '_anchor_card') and self._anchor_card:
            try:
                BubbleStateManager.set_bubble_state(self._anchor_card, False)
            except:
                pass
        
        self.bubble_closed.emit()
        super().closeEvent(event)
    
    def _create_open_animation(self, parent):
        try:
            final_rect = self._calculate_bubble_position(parent)
            
            if not final_rect:
                final_rect = QRect(100, 100, self.MIN_W, self.MIN_H)
            
            center_x = final_rect.center().x()
            center_y = final_rect.center().y()
            start_rect = QRect(center_x, center_y, 1, 1)
            
            self.setGeometry(start_rect)
            self.show()
            
            group = QParallelAnimationGroup(self)
            
            scale_anim = QPropertyAnimation(self, b"geometry")
            scale_anim.setDuration(120)
            scale_anim.setStartValue(start_rect)
            scale_anim.setEndValue(final_rect)
            scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            opacity_effect = QGraphicsOpacityEffect(self)
            opacity_effect.setOpacity(0.0)
            self.setGraphicsEffect(opacity_effect)
            
            fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
            fade_anim.setDuration(100)
            fade_anim.setStartValue(0.0)
            fade_anim.setEndValue(1.0)
            fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            
            group.addAnimation(scale_anim)
            group.addAnimation(fade_anim)
            
            return group
            
        except Exception:
            return None

    def _calculate_bubble_position(self, parent):
        try:
            if not self._is_anchor_card_valid() or not parent:
                return None
            
            try:
                card_global_pos = self._anchor_card.mapToGlobal(QPoint(0, 0))
            except RuntimeError:
                return None
            
            try:
                parent_global_pos = parent.mapToGlobal(QPoint(0, 0))
            except RuntimeError:
                return None
            
            card_rel_x = card_global_pos.x() - parent_global_pos.x()
            card_rel_y = card_global_pos.y() - parent_global_pos.y()
            
            bubble_w = self.width() if self.width() > 0 else self.MIN_W
            bubble_h = self.height() if self.height() > 0 else self.MIN_H
            
            MARGIN = 12
            PAD = 8
            
            target_x = card_rel_x + self._anchor_card.width() + MARGIN
            target_y = card_rel_y + self._anchor_card.height() // 2 - bubble_h // 2
            
            if target_x + bubble_w > parent.width() - PAD:
                target_x = card_rel_x - bubble_w - MARGIN
            
            if target_x < PAD:
                target_x = max(PAD, card_rel_x + self._anchor_card.width() // 2 - bubble_w // 2)
                target_y = card_rel_y + self._anchor_card.height() + MARGIN
            
            if target_y + bubble_h > parent.height() - PAD:
                target_y = card_rel_y - bubble_h - MARGIN
            
            target_x = max(PAD, min(target_x, parent.width() - bubble_w - PAD))
            target_y = max(PAD, min(target_y, parent.height() - bubble_h - PAD))
            
            return QRect(int(target_x), int(target_y), bubble_w, bubble_h)
            
        except Exception:
            return None
    
    def _create_close_animation(self, callback=None):
        group = QParallelAnimationGroup(self)
        
        current_rect = self.geometry()
        center_x = current_rect.center().x()
        center_y = current_rect.center().y()
        
        end_rect = QRect(center_x, center_y, 1, 1)
        
        scale_anim = QPropertyAnimation(self, b"geometry")
        scale_anim.setDuration(100)
        scale_anim.setStartValue(current_rect)
        scale_anim.setEndValue(end_rect)
        scale_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        opacity_effect = self.graphicsEffect()
        if not opacity_effect:
            opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(opacity_effect)
        
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
    
    def open_with_animation(self):
        try:
            if not self._is_anchor_card_valid():
                self.cleanup()
                return
            
            if not self._anchor_card:
                return
            
            self._load_content_delayed()
            
            if not BubbleStateManager.can_click(self._anchor_card, 150):
                return
            
            bubble_is_open = BubbleStateManager.get_bubble_state(self._anchor_card)
            
            if bubble_is_open:
                self.close_with_animation()
                return
            
            main_window = None
            
            try:
                anchor_window = self._anchor_card.window()
                if anchor_window and hasattr(anchor_window, 'isWindow') and anchor_window.isWindow():
                    main_window = anchor_window
            except RuntimeError:
                pass
            
            if not main_window:
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        try:
                            if hasattr(widget, 'isWindow') and widget.isWindow() and widget.isVisible():
                                main_window = widget
                                break
                        except RuntimeError:
                            continue
            
            if not main_window:
                return
            
            if self.parent() != main_window:
                self.setParent(main_window)
            
            BubbleStateManager.set_bubble_state(self._anchor_card, True)
            
            self._animating = True
            self._bubble_open = True
            
            anim = self._create_open_animation(main_window)
            
            if not anim:
                final_rect = self._calculate_bubble_position(main_window)
                if final_rect:
                    self.setGeometry(final_rect)
                self.show()
                self.raise_()
                self.activateWindow()
                self._animating = False
                if hasattr(self, "text") and self.text:
                    self.text.setFocus()
                self._setup_close_filter()
                return
            
            def on_anim_finished():
                self._animating = False
                if hasattr(self, "text") and self.text:
                    self.text.setFocus()
                self._setup_close_filter()
            
            anim.finished.connect(on_anim_finished)
            anim.start()
                
        except RuntimeError:
            self.cleanup()
        except Exception:
            pass

    def _is_anchor_card_valid(self):
        try:
            if not self._anchor_card:
                return False
            
            test = self._anchor_card.objectName()
            return True
        except (RuntimeError, Exception):
            return False
    
    def close_with_animation(self):
        try:
            if not self._anchor_card:
                self._on_close_complete()
                return
            
            try:
                bubble_is_open = BubbleStateManager.get_bubble_state(self._anchor_card)
            except:
                bubble_is_open = self._bubble_open
            
            if not bubble_is_open:
                self._on_close_complete()
                return
            
            try:
                BubbleStateManager.set_bubble_state(self._anchor_card, False)
            except:
                pass
            
            if self._animating:
                return
            
            self._animating = True
            
            anim = self._create_close_animation(callback=self._on_close_complete)
            
            if anim:
                anim.start()
            else:
                self._on_close_complete()
            
        except Exception:
            self._on_close_complete()
    
    def _on_close_complete(self):
        try:
            if hasattr(self, "text") and self.text:
                if hasattr(self.text, "toolbar"):
                    toolbar = self.text.toolbar
                    if toolbar:
                        toolbar.close_all(force=True)
                        if hasattr(toolbar, 'cleanup'):
                            toolbar.cleanup()
            
            self.hide()
            self._cleanup_close_filter()
            
            if self.graphicsEffect():
                self.setGraphicsEffect(None)
            
            self._animating = False
            self._bubble_open = False
            
        except Exception:
            pass
    
    def _setup_close_filter(self):
        try:
            self._cleanup_close_filter()
            self._close_filter = CopyBubbleCloseFilter(self)
            QApplication.instance().installEventFilter(self._close_filter)
        except Exception:
            pass
    
    def _cleanup_close_filter(self):
        try:
            if hasattr(self, "_close_filter"):
                QApplication.instance().removeEventFilter(self._close_filter)
                delattr(self, "_close_filter")
        except:
            pass
    
    def open_near(self, anchor_widget):
        self.open_with_animation()
    
    def set_bubble_open(self, open_state):
        self._bubble_open = open_state
    
    def set_animation_state(self, animating):
        self._animating = animating
    
    def cleanup(self):
        try:
            if hasattr(self, 'sync_manager') and self.sync_manager and self.card_id:
                self.sync_manager.unregister_copy_bubble(self.card_id)
            
            if self.card_id and self.card_id in self.__class__._global_bubble_instances:
                if self.__class__._global_bubble_instances[self.card_id] == self:
                    del self.__class__._global_bubble_instances[self.card_id]
            
            self._cleanup_close_filter()
            
            if hasattr(self, 'text') and self.text:
                if hasattr(self.text, 'toolbar'):
                    toolbar = self.text.toolbar
                    if toolbar:
                        if hasattr(toolbar, 'color_popup') and toolbar.color_popup:
                            toolbar.color_popup.hide()
                        toolbar.close_all(force=True)
            
            self.hide()
            self.setParent(None)
            self.deleteLater()
            
            if self._anchor_card:
                try:
                    BubbleStateManager.cleanup(self._anchor_card)
                except:
                    pass
            
        except Exception:
            pass


class CopyBubbleCloseFilter(QObject):
    def __init__(self, bubble):
        super().__init__()
        self.bubble = bubble
    
    def eventFilter(self, obj, event):
        if not self.bubble or not hasattr(self.bubble, "_anchor_card"):
            return False
        
        try:
            _ = self.bubble.window()
        except RuntimeError:
            return False
        
        flashcard = self.bubble._anchor_card
        
        try:
            if not flashcard:
                return False
            
            bubble_state = BubbleStateManager.get_bubble_state(flashcard)
            if not bubble_state:
                return False
        except:
            return False
        
        if event.type() == QEvent.Type.MouseButtonPress:
            try:
                pos = event.globalPosition().toPoint()
                
                if self._is_point_in_widget(self.bubble, pos):
                    return False
                
                if hasattr(self.bubble, "text") and self.bubble.text:
                    if self._is_point_in_widget(self.bubble.text.viewport(), pos):
                        return False
                
                if hasattr(self.bubble, "text") and hasattr(self.bubble.text, 'toolbar'):
                    toolbar = self.bubble.text.toolbar
                    if toolbar and toolbar.isVisible():
                        if self._is_point_in_widget(toolbar, pos):
                            return False
                        
                        if hasattr(toolbar, 'color_popup') and toolbar.color_popup:
                            if toolbar.color_popup.isVisible():
                                if self._is_point_in_widget(toolbar.color_popup, pos):
                                    return False
                
                QTimer.singleShot(0, self.bubble.close_with_animation)
                return True
                
            except Exception:
                return False
        
        return False
    
    def _is_point_in_widget(self, widget, global_point):
        if not widget:
            return False
        
        try:
            if not widget.isVisible():
                return False
            
            _ = widget.window()
            
            widget_global_pos = widget.mapToGlobal(QPoint(0, 0))
            widget_rect = QRect(widget_global_pos, widget.size())
            return widget_rect.contains(global_point)
        except (RuntimeError, Exception):
            return False