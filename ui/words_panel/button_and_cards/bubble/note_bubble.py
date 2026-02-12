from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QPainter, QColor, QPen

from .bubble_text import BubbleText
from .bubble_persistence import save_bubble, load_bubble


class NoteBubble(QWidget):
    """KARTLAR İÇİN BUBBLE - SENKRONİZASYON YOK, BASİT VERSİYON"""

    bubble_closed = pyqtSignal()
    resized = pyqtSignal(int, int)

    # SIZE LIMITS
    MIN_W = 320
    MIN_H = 200
    SCREEN_PAD = 24
    CONTENT_PAD_W = 48
    CONTENT_PAD_H = 48

    def __init__(self, parent=None, card_view=None, state=None, db=None, is_copy=False):
        super().__init__(parent)
        
        # STATE / DB / CARD
        self.state = state
        self.db = db
        self.card_view = card_view
        self.card_id = None
        self.is_copy = is_copy  # ✅ KOPYA KART MI?

        if card_view and hasattr(card_view, "card_id"):
            self.card_id = card_view.card_id
        elif card_view and hasattr(card_view, "data"):
            if hasattr(card_view.data, "id"):
                self.card_id = getattr(card_view.data, "id", None)

        self._anchor_card = card_view

        # WINDOW FLAGS
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self._animating = False
        self._bubble_open = False

        # SIZE POLICY
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.resize(self.MIN_W, self.MIN_H)

        # LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        # TEXT WIDGET
        self.text = BubbleText(self)
        self.text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # ✅ KOPYA KARTLAR İÇİN: SADECE OKUMA MODU
        if self.is_copy:
            self.text.setReadOnly(True)
            if hasattr(self.text, 'toolbar'):
                self.text.toolbar.setEnabled(False)
                self.text.toolbar.hide()
        
        layout.addWidget(self.text)

        # AUTO RESIZE
        self.text.document().contentsChanged.connect(self._auto_resize_to_text)

        # AUTO SAVE SYSTEM - ✅ SADECE ORİJİNAL KARTLAR İÇİN
        if not self.is_copy:
            self.text.textChanged.connect(self._start_auto_save_timer)
            self._auto_save_timer = QTimer(self)
            self._auto_save_timer.setSingleShot(True)
            self._auto_save_timer.setInterval(500)
            self._auto_save_timer.timeout.connect(self._perform_auto_save)
            self._last_saved_html = ""
            self._last_saved_size = (self.width(), self.height())
        else:
            self._auto_save_timer = None

        # ✅ SENKRONİZASYON YOK - BASİT
        print(f"✅ [NoteBubble] Oluşturuldu - card_id: {self.card_id}, is_copy: {is_copy}")

        # LOAD SAVED CONTENT
        if self.card_id:
            QTimer.singleShot(400, self._load_saved_content_delayed)

        # EVENT FILTERS
        if parent:
            parent.installEventFilter(self)
        self.installEventFilter(self)

    def resizeEvent(self, event):
        """Boyut değiştiğinde - SENKRONİZASYON YOK"""
        super().resizeEvent(event)
        
        width = event.size().width()
        height = event.size().height()
        
        self.resized.emit(width, height)

    def closeEvent(self, event):
        """Bubble kapanırken"""
        # Toolbar temizliği
        if hasattr(self, 'text') and self.text:
            if hasattr(self.text, 'toolbar'):
                toolbar = self.text.toolbar
                if toolbar:
                    if hasattr(toolbar, 'color_popup') and toolbar.color_popup:
                        toolbar.color_popup.hide()
                    
                    toolbar.close_all(force=True)
        
        # Veriyi kaydet - ✅ SADECE ORİJİNAL KARTLAR
        if not self.is_copy:
            self._force_save_immediately()
        
        self.bubble_closed.emit()
        super().closeEvent(event)

    def _auto_resize_to_text(self):
        """Auto-resize fonksiyonu"""
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
                
        except Exception as e:
            print(f"❌ [NoteBubble._auto_resize_to_text] Hata: {e}")

    def _snap_back_next_to_card(self):
        """Bubble açıkken, resize sonrası tekrar kartın yanına hizalar."""
        try:
            if self._animating:
                return
                
            card = getattr(self, "_anchor_card", None)
            parent = self.parentWidget() or self.parent()

            if not card or not parent:
                return

            from ui.words_panel.button_and_cards.bubble.bubble_opening import place_bubble_next_to_card
            place_bubble_next_to_card(self, card, parent)

        except Exception:
            pass

    def _start_auto_save_timer(self):
        """Auto-save timer başlat - ✅ SADECE ORİJİNAL"""
        if self.is_copy:
            return
        
        if self._auto_save_timer:
            self._auto_save_timer.stop()
            self._auto_save_timer.start()

    def _perform_auto_save(self):
        """Orijinal bubble kaydet - ✅ SADECE ORİJİNAL"""
        if self.is_copy:
            return
            
        try:
            if not self.card_id:
                if hasattr(self, '_anchor_card') and self._anchor_card:
                    if hasattr(self._anchor_card, 'card_id') and self._anchor_card.card_id:
                        self.card_id = self._anchor_card.card_id
            
            if not self.card_id:
                return
            
            html_content = ""
            if hasattr(self, 'text'):
                html_content = self.text.toHtml()
            
            if not html_content or html_content.strip() == "":
                return
            
            # Değişiklik kontrolü
            if html_content == self._last_saved_html and \
               (self.width(), self.height()) == self._last_saved_size:
                return
            
            saved = save_bubble(self)
            
            if saved:
                self._last_saved_html = html_content
                self._last_saved_size = (self.width(), self.height())
                
        except Exception as e:
            print(f"❌ [NoteBubble._perform_auto_save] Hata: {e}")

    def _force_save_immediately(self):
        """Hemen kaydet - ✅ SADECE ORİJİNAL"""
        if self.is_copy:
            return
            
        try:
            if not self.card_id and self._anchor_card and hasattr(self._anchor_card, "card_id"):
                self.card_id = self._anchor_card.card_id
                
            if self.card_id:
                save_bubble(self)
        except Exception as e:
            print(f"❌ [NoteBubble._force_save_immediately] Hata: {e}")

    def _load_saved_content_delayed(self):
        """Kaydedilmiş içeriği yükle"""
        try:
            if not self.card_id:
                return

            # KOPYA KARTLAR İÇİN ÖZEL YÜKLEME
            if self.is_copy and self.db:
                data = load_bubble(self.card_id)
                
                html_content = ""
                if data and isinstance(data, dict) and data.get("html"):
                    html_content = data.get("html", "")
                
                # ✅ KOPYA KART İÇİN ORİJİNALİN BUBBLE'INI DA DENE
                if not html_content or html_content.strip() == "":
                    try:
                        cursor = self.db.conn.cursor()
                        cursor.execute("SELECT original_card_id FROM words WHERE id=?", (self.card_id,))
                        row = cursor.fetchone()
                        
                        if row and row[0]:
                            original_id = row[0]
                            original_data = load_bubble(original_id)
                            if original_data and original_data.get("html"):
                                html_content = original_data.get("html", "")
                                print(f"✅ [NoteBubble] Kopya kart için orijinal bubble yüklendi: {original_id}")
                    except Exception as e:
                        print(f"⚠️ [NoteBubble] Orijinal bubble yükleme hatası: {e}")
                
                if html_content:
                    self.text.setHtml(html_content)
                else:
                    self.text.setHtml("<p></p>")
                
                w = max(self.MIN_W, int(data.get("width", self.MIN_W) or self.MIN_W)) if data else self.MIN_W
                h = max(self.MIN_H, int(data.get("height", self.MIN_H) or self.MIN_H)) if data else self.MIN_H
                self.resize(w, h)
                
                print(f"✅ [NoteBubble] Kopya kart bubble içeriği yüklendi")
                
            else:
                # ORİJİNAL KARTLAR İÇİN NORMAL YÜKLEME
                data = load_bubble(self.card_id)

                if isinstance(data, dict):
                    self.text.setHtml(data.get("html", ""))
                    w = max(self.MIN_W, int(data.get("width", self.MIN_W) or self.MIN_W))
                    h = max(self.MIN_H, int(data.get("height", self.MIN_H) or self.MIN_H))
                    self.resize(w, h)
                    
                    self._last_saved_html = data.get("html", "")
                    self._last_saved_size = (w, h)
                    
                    print(f"✅ [NoteBubble] Orijinal kart bubble içeriği yüklendi")
                    
                elif isinstance(data, str):
                    self.text.setHtml(data)
                    self._auto_resize_to_text()
                else:
                    self.text.setHtml("<p></p>")

        except Exception as e:
            print(f"❌ [NoteBubble._load_saved_content_delayed] Hata: {e}")
            self.text.setHtml("<p></p>")

    def paintEvent(self, event):
        """Paint event - KOPYA KARTLAR KIRMIZI BORDER"""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        radius = 18

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawRoundedRect(self.rect(), radius, radius)

        # Border - ✅ KOPYA KARTLAR İÇİN KIRMIZI
        if self.is_copy:
            pen = QPen(QColor(220, 53, 69))  # Kırmızı
            pen.setWidth(3)
        else:
            pen = QPen(QColor(95, 95, 95))   # Gri
            pen.setWidth(4)
            
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = self.rect().adjusted(2, 2, -2, -2)
        p.drawRoundedRect(rect, radius, radius)

        p.end()

    def set_animation_state(self, animating):
        self._animating = animating

    def set_bubble_open(self, open_state):
        self._bubble_open = open_state

    def open_near(self, anchor_widget):
        """Kartın yanında aç"""
        if not anchor_widget:
            return
        
        try:
            pos = anchor_widget.mapToGlobal(anchor_widget.rect().bottomRight())
            self.move(pos + QPoint(12, 12))
            self.show()
            self.raise_()
            
            # ✅ SADECE ORİJİNAL KARTLAR İÇİN FOCUS
            if not self.is_copy:
                self.text.setFocus()
                
            print(f"✅ [NoteBubble.open_near] Bubble açıldı - is_copy: {self.is_copy}")
                
        except Exception as e:
            print(f"❌ [NoteBubble.open_near] Hata: {e}")

    def adjust_to_content(self):
        """Uyumluluk için"""
        pass
        
    def cleanup(self):
        """Temizlik"""
        try:
            print(f"🔵 [NoteBubble.cleanup] Temizleniyor - card_id: {self.card_id}, is_copy: {self.is_copy}")
            
            # Toolbar temizliği
            if hasattr(self, 'text') and self.text:
                if hasattr(self.text, 'toolbar'):
                    toolbar = self.text.toolbar
                    if toolbar:
                        if hasattr(toolbar, 'color_popup') and toolbar.color_popup:
                            toolbar.color_popup.hide()
                        toolbar.close_all(force=True)
            
            # Widget temizliği
            self.hide()
            self.setParent(None)
            self.deleteLater()
            
            print(f"✅ [NoteBubble.cleanup] Temizlendi")
            
        except Exception as e:
            print(f"❌ [NoteBubble.cleanup] Hata: {e}")