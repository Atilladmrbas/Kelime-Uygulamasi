from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame, QGridLayout,
    QPushButton, QVBoxLayout, QLabel, QApplication
)
from PyQt6.QtCore import Qt, QObject, QEvent, QPoint, QRect
from PyQt6.QtGui import QTextCharFormat, QTextCursor, QColor

if TYPE_CHECKING:
    from .floating_toolbar import FloatingToolbar


# ======================================================
# HELPERS
# ======================================================
def _hex(c: QColor | None) -> str | None:
    if not c or not c.isValid():
        return None
    return c.name().lower()


def _format_fg_hex(cf: QTextCharFormat) -> str | None:
    try:
        return _hex(cf.foreground().color())
    except Exception:
        return None


def _format_bg_hex(cf: QTextCharFormat) -> str | None:
    try:
        col = cf.background().color()
        if not col or not col.isValid() or col.alpha() == 0:
            return None
        return _hex(col)
    except Exception:
        return None


# ======================================================
# 🎨 COLOR POPUP - GÜNCELLENMİŞ VERSİYON
# ======================================================
class ColorPopup(QFrame):
    TEXT_COLORS = [
        "#37352f", "#9b9a97", "#c94a4a", "#e8590c", "#f08c00",
        "#2f9e44", "#228be6", "#7048e8", "#e64980", "#fa5252"
    ]
    BG_COLORS = [
        "#ffffff", "#f1f3f5", "#fff4e6", "#ffe8cc", "#fff3bf",
        "#d3f9d8", "#d0ebff", "#e5dbff", "#ffe3e3", "#ffd6e7"
    ]

    def __init__(self, toolbar: "FloatingToolbar"):
        super().__init__(None)
        self.toolbar = toolbar

        self._preview_cursor: QTextCursor | None = None
        self._preview_fmt: QTextCharFormat | None = None
        self._preview_active = False

        self._text_btns = {}
        self._bg_btns = {}
        self._all_btns = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # STYLESHEET'i düzenle
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 12px;
                border: 1px solid #ddd;
            }
            QLabel { 
                font-size: 11px; 
                color: #666; 
                padding: 0px;
                margin: 0px;
            }
            QPushButton {
                border: 1px solid #e6e6e6;
                border-radius: 7px;
                min-width: 28px;
                min-height: 28px;
                max-width: 28px;
                max-height: 28px;
                background: white;
            }
            QPushButton:hover { 
                border: 1px solid #4dabf7; 
            }
            QPushButton[selected="true"] { 
                border: 2px solid #111; 
            }
        """)

        # Ana layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame(self)
        panel.setObjectName("panel")
        outer.addWidget(panel)

        root = QVBoxLayout(panel)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # Text color bölümü
        root.addWidget(QLabel("Text color"))
        root.addLayout(self._build_grid(self.TEXT_COLORS, "text"))

        # Background color bölümü
        root.addWidget(QLabel("Background color"))
        root.addLayout(self._build_grid(self.BG_COLORS, "bg"))

        # ✅ EVENT FILTER İÇİN DEĞİŞKEN
        self._close_filter = None
        
        self.hide()

    # -------------------------------------------------
    def _build_grid(self, colors, kind):
        """Renk grid'ini oluştur"""
        grid = QGridLayout()
        grid.setSpacing(6)
        
        for i, c in enumerate(colors):
            row = i // 5
            col = i % 5
            
            btn = QPushButton("A" if kind == "text" else "")
            btn.setProperty("kind", kind)
            btn.setProperty("color", c)
            
            if kind == "text":
                btn.setStyleSheet(f"color:{c}")
                self._text_btns[c] = btn
            else:
                btn.setStyleSheet(f"background:{c}")
                self._bg_btns[c] = btn

            # ✅ DÜZELTİLMİŞ BAĞLANTI
            btn.pressed.connect(self._create_preview_handler(btn))
            btn.released.connect(self._create_commit_handler(btn))

            self._all_btns.append(btn)
            grid.addWidget(btn, row, col)

        return grid

    # -------------------------------------------------
    def _create_preview_handler(self, btn):
        """Preview handler oluştur"""
        def handler():
            self._preview(btn)
        return handler
    
    def _create_commit_handler(self, btn):
        """Commit handler oluştur"""
        def handler():
            self._commit(btn)
        return handler

    # -------------------------------------------------
    def showEvent(self, event):
        """Popup gösterilirken event filter kur"""
        super().showEvent(event)
        self.adjustSize()
        
        # ✅ EVENT FILTER KUR
        self._install_event_filter()
        
    # -------------------------------------------------
    def hideEvent(self, event):
        """Popup kapanırken temizlik yap"""
        if self._preview_active:
            self._revert_preview()
        
        # ✅ EVENT FILTER'I KALDIR
        self._remove_event_filter()
        
        super().hideEvent(event)
        
    def closeEvent(self, event):
        """Popup kapanırken temizlik"""
        self._remove_event_filter()
        super().closeEvent(event)

    # -------------------------------------------------
    def _install_event_filter(self):
        """Global event filter kur - DIŞARI TIKLAYINCA KAPANMA"""
        # Eski filter'ı temizle
        self._remove_event_filter()
        
        # Yeni filter ekle
        self._close_filter = ColorPopupCloseFilter(self)
        QApplication.instance().installEventFilter(self._close_filter)
    
    def _remove_event_filter(self):
        """Event filter'ı kaldır"""
        if self._close_filter:
            try:
                QApplication.instance().removeEventFilter(self._close_filter)
            except:
                pass
            self._close_filter = None

    # -------------------------------------------------
    def sync_selected_borders(self):
        cf = self.toolbar.editor.currentCharFormat()
        fg = _format_fg_hex(cf)
        bg = _format_bg_hex(cf)

        for b in self._all_btns:
            b.setProperty("selected", False)
            b.style().unpolish(b)
            b.style().polish(b)

        if fg and fg in self._text_btns:
            b = self._text_btns[fg]
            b.setProperty("selected", True)
            b.style().unpolish(b)
            b.style().polish(b)

        if bg and bg in self._bg_btns:
            b = self._bg_btns[bg]
            b.setProperty("selected", True)
            b.style().unpolish(b)
            b.style().polish(b)

    # -------------------------------------------------
    def _preview(self, btn: QPushButton):
        """Renk önizlemesi"""
        self.toolbar.capture_selection_cursor()
        base = self.toolbar._selection_cursor

        if not base or not base.hasSelection():
            return

        self._preview_cursor = QTextCursor(base)
        self._preview_fmt = QTextCharFormat(base.charFormat())
        self._preview_active = True

        fmt = QTextCharFormat()
        if btn.property("kind") == "text":
            fmt.setForeground(QColor(btn.property("color")))
        else:
            fmt.setBackground(QColor(btn.property("color")))

        self._preview_cursor.mergeCharFormat(fmt)
        self.toolbar.editor.setTextCursor(self._preview_cursor)
        self.sync_selected_borders()

    # -------------------------------------------------
    def _commit(self, btn: QPushButton):
        """Renk uygula"""
        self._preview_active = False
        self._preview_cursor = None
        self._preview_fmt = None

        fmt = QTextCharFormat()
        if btn.property("kind") == "text":
            fmt.setForeground(QColor(btn.property("color")))
        else:
            fmt.setBackground(QColor(btn.property("color")))

        self.toolbar.apply_format(fmt)
        self.toolbar.sync()

    # -------------------------------------------------
    def _revert_preview(self):
        """Önizlemeyi geri al"""
        if not self._preview_fmt:
            return

        cur = QTextCursor(self.toolbar._selection_cursor)
        cur.mergeCharFormat(self._preview_fmt)
        self.toolbar.editor.setTextCursor(cur)

        self._preview_active = False
        self._preview_cursor = None
        self._preview_fmt = None

        self.toolbar.sync()
        
    # -------------------------------------------------
    def cleanup(self):
        """Popup'ı temizle"""
        try:
            print("🧹 Cleaning up color popup...")
            
            # 1. Event filter'ı kaldır
            self._remove_event_filter()
            
            # 2. Preview'ı temizle
            if self._preview_active:
                self._revert_preview()
            
            # 3. Kendini gizle
            self.hide()
            
            # 4. Parent'ı temizle
            self.setParent(None)
            
            print("✅ Color popup cleaned up")
            
        except Exception as e:
            print(f"❌ Color popup cleanup error: {e}")

# ======================================================
# COLOR POPUP CLOSE FILTER
# ======================================================
class ColorPopupCloseFilter(QObject):
    """ColorPopup'ın dışına tıklayınca kapanması için"""
    
    def __init__(self, color_popup):
        super().__init__()
        self.color_popup = color_popup
    
    def eventFilter(self, obj, event):
        if not self.color_popup.isVisible():
            return False
        
        if event.type() == QEvent.Type.MouseButtonPress:
            pos = event.globalPosition().toPoint()
            
            # 1. Popup'ın içine mi tıklandı?
            if self._contains(self.color_popup, pos):
                return False
            
            # 2. Toolbar'ın içine mi tıklandı?
            toolbar = self.color_popup.toolbar
            if toolbar and self._contains(toolbar, pos):
                return False
            
            # 3. Editor'ün içine mi tıklandı?
            if toolbar and toolbar.editor:
                editor = toolbar.editor
                # Editor'ün viewport'una bak
                if self._contains(editor.viewport(), pos):
                    return False
                # Editor'ün kendisine bak
                if self._contains(editor, pos):
                    return False
            
            # 4. Dışarı tıklandı - popup'ı kapat
            self.color_popup.hide()
            return True
        
        return False
    
    @staticmethod
    def _contains(widget: QWidget, pos: QPoint) -> bool:
        if not widget or not widget.isVisible():
            return False
        try:
            tl = widget.mapToGlobal(QPoint(0, 0))
            return QRect(tl, widget.size()).contains(pos)
        except:
            return False