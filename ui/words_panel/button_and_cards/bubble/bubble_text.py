# bubble_text.py - SADECE KÜÇÜK GÜNCELLEME
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import QEvent, QTimer, Qt, QRect, QPoint
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt6.QtWidgets import QScroller, QScrollerProperties

# ✅ GÜNCELLENDİ: Yeni toolbar klasöründen import et
from .toolbar.floating_toolbar import FloatingToolbar

class BubbleText(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # BASIC CONFIG
        self.setAcceptRichText(True)
        self.setFrameStyle(0)

        # DEFAULT TEXT COLOR - SİYAH
        default_text_color = QColor(0, 0, 0)
        self.setTextColor(default_text_color)
        
        self.document().setDefaultStyleSheet("""
            body { 
                color: #000000; 
                font-family: sans-serif; 
                font-size: 14px; 
            }
            p { 
                margin: 0; 
                padding: 0; 
                color: #000000; 
            }
        """)
        
        self.setHtml("<p></p>")

        # SELECTION HIGHLIGHT
        pal = self.palette()
        pal.setColor(pal.ColorRole.Highlight, QColor("#e9ecef"))
        pal.setColor(pal.ColorRole.HighlightedText, QColor("#000"))
        pal.setColor(pal.ColorRole.Text, QColor("#000000"))
        self.setPalette(pal)
        self.viewport().setPalette(pal)

        # SCROLLBARS
        self.setStyleSheet("""
            QTextEdit { 
                background: transparent; 
                border: none; 
                color: #000000;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px; height: 0px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: transparent;
                min-height: 0px; min-width: 0px;
            }
            QScrollBar::add-line, QScrollBar::sub-line,
            QScrollBar::add-page, QScrollBar::sub-page {
                background: transparent;
                width: 0px; height: 0px;
            }
        """)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # SMOOTH SCROLL
        QScroller.grabGesture(
            self.viewport(),
            QScroller.ScrollerGestureType.TouchGesture
        )
        scroller = QScroller.scroller(self.viewport())
        props = scroller.scrollerProperties()
        props.setScrollMetric(
            QScrollerProperties.ScrollMetric.DecelerationFactor, 0.12
        )
        props.setScrollMetric(
            QScrollerProperties.ScrollMetric.MaximumVelocity, 0.55
        )
        scroller.setScrollerProperties(props)

        # FLOATING TOOLBAR
        self.toolbar = FloatingToolbar(self)

        # INTERNAL STATE
        self.viewport().installEventFilter(self)
        self._selecting = False

    # ==================================================
    # ENTER / NEW BLOCK FORMAT RESET
    # ==================================================
    def _reset_new_block_format(self):
        """
        Enter sonrası:
        - foreground / background taşmasını engeller
        - yeni satır DEFAULT formatla başlar
        """

        cursor = self.textCursor()

        # CHAR FORMAT RESET - Siyah metin rengi
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(QColor(0, 0, 0))  # Siyah renk
        char_fmt.clearBackground()
        cursor.setCharFormat(char_fmt)

        # BLOCK FORMAT RESET
        block_fmt = cursor.blockFormat()
        block_fmt.clearBackground()
        cursor.setBlockFormat(block_fmt)

        # BLOCK CHAR FORMAT RESET (kritik)
        block_char_fmt = QTextCharFormat()
        block_char_fmt.setForeground(QColor(0, 0, 0))  # Siyah renk
        cursor.setBlockCharFormat(block_char_fmt)

        self.setTextCursor(cursor)

    # ==================================================
    # KEY PRESS
    # ==================================================
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()

            # selection yoksa normal enter
            if not cursor.hasSelection():
                super().keyPressEvent(event)

                # reseti tek noktadan, async yap
                QTimer.singleShot(0, self._reset_new_block_format)
                return

        super().keyPressEvent(event)
        
        # Her yazı işlemden sonra metin rengini kontrol et
        QTimer.singleShot(0, self._ensure_text_color)

    # ==================================================
    # METİN RENGİ KONTROLÜ
    # ==================================================
    def _ensure_text_color(self):
        """Metin renginin siyah olduğundan emin ol"""
        cursor = self.textCursor()
        char_format = cursor.charFormat()
        
        # Eğer metin rengi belirlenmemişse veya şeffaf/saydam ise
        if not char_format.foreground().isOpaque():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(0, 0, 0))  # Siyah
            cursor.mergeCharFormat(fmt)
            self.setTextCursor(cursor)

    # ==================================================
    # FOCUS / MOUSE
    # ==================================================
    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Odaklandığında varsayılan metin rengini siyah yap
        QTimer.singleShot(0, self._ensure_text_color)

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._selecting = True
        super().mousePressEvent(event)
        self.toolbar.close_all(force=True)

    # ==================================================
    # EVENT FILTER
    # ==================================================
    def eventFilter(self, obj, event):
        if obj == self.viewport():

            if event.type() in (
                QEvent.Type.MouseMove,
                QEvent.Type.KeyPress,
            ):
                return False

            if event.type() in (
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.KeyRelease,
            ):
                self._selecting = False
                QTimer.singleShot(0, self._show_toolbar_if_needed)

            elif event.type() in (
                QEvent.Type.Wheel,
                QEvent.Type.Scroll,
                QEvent.Type.Resize,
            ):
                QTimer.singleShot(0, self.toolbar.update_position)

        return super().eventFilter(obj, event)

    # ==================================================
    # SELECTION GEOMETRY (WINDOW COORDS) - OPTİMİZE EDİLMİŞ
    # ==================================================
    def _selection_geo_in_window(self):
        cur: QTextCursor = self.textCursor()
        if not cur.hasSelection():
            return None

        doc = cur.document()
        start = min(cur.selectionStart(), cur.selectionEnd())
        end = max(cur.selectionStart(), cur.selectionEnd())

        c1 = QTextCursor(doc)
        c1.setPosition(start)
        c2 = QTextCursor(doc)
        c2.setPosition(end)

        r1 = self.cursorRect(c1)
        r2 = self.cursorRect(c2)

        # Seçimin ÜST NOKTASINI bul
        top_rect = r1 if r1.top() <= r2.top() else r2
        
        # Toolbar için ideal pozisyon: seçimin ORTA ÜSTÜ
        cx = (r1.left() + r2.right()) // 2
        top_y = min(r1.top(), r2.top())
        
        win = self.window()
        vp = self.viewport()

        # Pencere koordinatlarına çevir
        anchor = vp.mapTo(win, QPoint(cx, top_y))
        
        # Avoid rect (seçim alanı)
        union = r1.united(r2).adjusted(-4, -4, 4, 4)
        avoid = QRect(vp.mapTo(win, union.topLeft()), union.size())

        return anchor, avoid

    # ==================================================
    # TOOLBAR CONTROL
    # ==================================================
    def _show_toolbar_if_needed(self):
        if self._selecting:
            return

        cursor: QTextCursor = self.textCursor()

        if not cursor.hasSelection():
            self.toolbar.close_all(force=True)
            return

        geo = self._selection_geo_in_window()
        if not geo:
            return

        anchor, avoid = geo
        
        # Toolbar'ı göster (yeni konumlandırma ile)
        self.toolbar.show_at(anchor, avoid_rect=avoid)

    def force_activate(self):
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, self._show_toolbar_if_needed)
        
    # ==================================================
    # HTML YÜKLEME İŞLEMİ
    # ==================================================
    def setHtml(self, html):
        """HTML içeriği yüklerken varsayılan CSS ekle"""
        if not html or html.strip() == "":
            html = "<p></p>"
            
        # Eğer CSS yoksa ekle
        if "style" not in html.lower():
            html = f"""
            <html>
            <head>
            <style>
                body {{ 
                    color: #000000; 
                    font-family: sans-serif; 
                    font-size: 14px; 
                }}
                p {{ 
                    margin: 0; 
                    padding: 0; 
                    color: #000000; 
                }}
            </style>
            </head>
            <body>
            {html}
            </body>
            </html>
            """
            
        super().setHtml(html)
        QTimer.singleShot(0, self._ensure_text_color)

    def cleanup(self):
        """Text editor'ü temizle"""
        try:
            if hasattr(self, 'toolbar'):
                toolbar = self.toolbar
                if toolbar:
                    toolbar.close_all(force=True)
                    if hasattr(toolbar, 'cleanup'):
                        toolbar.cleanup()
        except Exception:
            pass