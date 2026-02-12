from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QApplication, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QPoint, QPropertyAnimation, QEasingCurve,
    QRect, QTimer
)
from PyQt6.QtGui import (
    QTextCharFormat, QFont, QTextCursor, QCursor
)

from .toolbar_ui import FloatingToolbarUI
from .helpers_and_colorpop import ColorPopup


class FloatingToolbar(QWidget):
    """
    Selection üstünde beliren floating toolbar.
    ColorPopup + format uygulama + fade animasyon içerir.
    """

    def __init__(self, editor):
        super().__init__(None)
        self.editor = editor

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------
        self._visible = False
        self._avoid_rect: QRect | None = None
        self._selection_cursor: QTextCursor | None = None

        # -------------------------------------------------
        # WINDOW SETUP
        # -------------------------------------------------
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        # -------------------------------------------------
        # UI
        # -------------------------------------------------
        self.ui = FloatingToolbarUI(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        # -------------------------------------------------
        # COLOR POPUP
        # -------------------------------------------------
        self.color_popup = ColorPopup(self)

        # -------------------------------------------------
        # BUTTON HOOKS
        # -------------------------------------------------
        self.ui.btn_b.clicked.connect(self.bold)
        self.ui.btn_i.clicked.connect(self.italic)
        self.ui.btn_u.clicked.connect(self.underline)
        self.ui.btn_s.clicked.connect(self.strike)
        self.ui.btn_color.clicked.connect(self.toggle_color_popup)

        # -------------------------------------------------
        # FADE ANIMATION
        # -------------------------------------------------
        self._opacity = QGraphicsOpacityEffect(self.ui.container)
        self._opacity.setOpacity(0.0)
        self.ui.container.setGraphicsEffect(self._opacity)

        self.fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self.fade.setDuration(140)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade.finished.connect(self._on_fade_finished)

        # -------------------------------------------------
        # CURSOR FIX
        # -------------------------------------------------
        for btn in (
            self.ui.btn_b,
            self.ui.btn_i,
            self.ui.btn_u,
            self.ui.btn_s,
            self.ui.btn_color,
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.hide()

    # =================================================
    # WINDOW / PARENT HELPERS
    # =================================================
    def _target_window(self) -> QWidget:
        w = self.editor.window() if self.editor is not None else None
        return w if w is not None else QApplication.activeWindow() or self.editor

    def _ensure_on_correct_window(self):
        win = self._target_window()
        if win is None:
            return

        # SADECE parent değişmişse güncelle
        if self.parent() is not win:
            was_visible = self.isVisible()
            
            # ÖNCE gizle, sonra parent değiştir
            if was_visible:
                self.hide()
                
            self.setParent(win)
            self.color_popup.setParent(win)
            
            # Sonra tekrar göster
            if was_visible:
                self.show()
                self.raise_()

    # =================================================
    # VISIBILITY
    # =================================================
    def _on_fade_finished(self):
        if not self._visible:
            self.hide()

    def is_color_popup_open(self) -> bool:
        return self.color_popup.isVisible()

    # =================================================
    # SELECTION SNAPSHOT
    # =================================================
    def capture_selection_cursor(self):
        cur = self.editor.textCursor()
        self._selection_cursor = QTextCursor(cur) if cur.hasSelection() else None

    # =================================================
    # OPEN / CLOSE
    # =================================================
    def close_all(self, *, force=True):
        """Tüm popup'ları kapat"""
        if self.color_popup.isVisible():
            self.color_popup.hide()
        
        self.hide_soft(force=force)

    def hide_soft(self, *, force=False):
        if self.is_color_popup_open() and not force:
            return
        if not self._visible:
            return

        self._visible = False
        self.fade.stop()
        self.fade.setStartValue(self._opacity.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()

    # =================================================
    # COLOR POPUP - GÜNCELLENMİŞ
    # =================================================
    def toggle_color_popup(self):
        self._ensure_on_correct_window()
        
        if self.color_popup.isVisible():
            self.color_popup.hide()
            return

        self.capture_selection_cursor()
        self.sync()
        
        # 1. MOUSE CURSOR pozisyonunu al
        cursor_pos = QCursor.pos()
        
        # 2. Popup boyutunu al
        self.color_popup.adjustSize()
        popup_width = self.color_popup.width()
        popup_height = self.color_popup.height()
        
        # 3. Ekran sınırları
        screen = QApplication.primaryScreen().availableGeometry()
        
        # 4. Konumu hesapla
        target_x = cursor_pos.x() - popup_width // 2
        target_y = cursor_pos.y() + 20
        
        # Sol sınır
        if target_x < screen.left() + 10:
            target_x = screen.left() + 10
        
        # Sağ sınır
        if target_x + popup_width > screen.right() - 10:
            target_x = screen.right() - popup_width - 10
        
        # Alt sınır
        if target_y + popup_height > screen.bottom() - 10:
            target_y = cursor_pos.y() - popup_height - 20
        
        # Üst sınır
        if target_y < screen.top() + 10:
            target_y = screen.top() + 10
        
        # 5. CRITICAL: Popup'ı TAMAMEN BAĞIMSIZ pencere yap
        self.color_popup.setParent(None)
        self.color_popup.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.X11BypassWindowManagerHint  # Linux için
        )
        
        # 6. Özellikleri ayarla
        self.color_popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.color_popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 7. Move ve show
        self.color_popup.move(int(target_x), int(target_y))
        self.color_popup.show()
        
        # 8. Z-order'ı garanti altına al
        self.color_popup.raise_()
        self.color_popup.activateWindow()
        
        # 9. Toolbar'ı da güncelle
        self.raise_()
        
    def _place_popup_below_toolbar(self):
        """Popup'ı MOUSE CURSOR pozisyonuna göre aç"""
        self._ensure_on_correct_window()
        
        # 1. Mouse cursor'ün pozisyonunu al
        cursor_pos = QCursor.pos()
        
        # 2. Popup boyutunu al
        self.color_popup.adjustSize()
        popup_width = self.color_popup.width()
        popup_height = self.color_popup.height()
        
        # 3. Popup'ı cursor'ün altına yerleştir
        target_x = cursor_pos.x() - popup_width // 2
        target_y = cursor_pos.y() + 20  # Cursor'ün 20px altı
        
        # 4. EKRAN SINIRLARI KONTROLÜ
        screen = QApplication.primaryScreen().availableGeometry()
        
        # SOL sınır
        if target_x < screen.left() + 10:
            target_x = screen.left() + 10
        
        # SAĞ sınır
        if target_x + popup_width > screen.right() - 10:
            target_x = screen.right() - popup_width - 10
        
        # ALT sınır
        if target_y + popup_height > screen.bottom() - 10:
            # Altta yer yoksa, cursor'ün ÜSTÜNE yerleştir
            target_y = cursor_pos.y() - popup_height - 20
        
        # ÜST sınır
        if target_y < screen.top() + 10:
            target_y = screen.top() + 10
        
        # 5. Move et
        self.color_popup.move(int(target_x), int(target_y))

    # =================================================
    # SHOW AT SELECTION
    # =================================================
    def show_at(self, anchor_in_window: QPoint, *, avoid_rect: QRect | None = None):
        self._ensure_on_correct_window()

        self.capture_selection_cursor()
        self._avoid_rect = avoid_rect

        self.adjustSize()

        win = self._target_window()
        gap = 10
        
        # Toolbar boyutları
        toolbar_width = self.width()
        toolbar_height = self.height()
        
        # Toolbar'ı seçimin ORTASINA hizala
        x = int(anchor_in_window.x() - toolbar_width / 2)
        
        # ÖNCE SEÇİMİN ALTINDA GÖSTER
        y = int(anchor_in_window.y() + 25)
        
        # Eğer altta yer yoksa, üstünde göster
        if y + toolbar_height > win.height() - 8:
            y = int(anchor_in_window.y() - toolbar_height - 10)
        
        # Ekran sınırları içinde kal
        x = max(8, min(x, win.width() - toolbar_width - 8))
        y = max(8, min(y, win.height() - toolbar_height - 8))
        
        # Avoid rect ile çakışmayı kontrol et
        if avoid_rect:
            toolbar_rect = QRect(x, y, toolbar_width, toolbar_height)
            if toolbar_rect.intersects(avoid_rect):
                # Çakışıyorsa, avoid_rect'ın altına yerleştir
                y = avoid_rect.bottom() + 15
        
        # ✅ HER ZAMAN GÖRÜNÜR OLSUN
        self.move(x, y)
        self.raise_()
        
        # ✅ TAM OPACITY İLE GÖSTER
        self._opacity.setOpacity(1.0)
        
        if not self._visible:
            self._visible = True
            self.fade.stop()
            self.show()
            self.raise_()
        
        # ColorPopup da görünür mü kontrol et
        if self.color_popup.isVisible():
            self._place_popup_below_toolbar()

    # =================================================
    # POSITION UPDATE (SCROLL / RESIZE)
    # =================================================
    def update_position(self):
        if not self._visible:
            return

        self._ensure_on_correct_window()

        cur = self.editor.textCursor()
        if not cur.hasSelection():
            self.close_all(force=True)
            return

        geo_fn = getattr(self.editor, "_selection_geo_in_window", None)
        if callable(geo_fn):
            geo = geo_fn()
            if geo:
                anchor, avoid = geo
                self.show_at(anchor, avoid_rect=avoid)
                
                # ColorPopup açıksa, onun da konumunu güncelle
                if self.color_popup.isVisible():
                    self._place_popup_below_toolbar()
                return

        # ColorPopup açıksa, onun da konumunu güncelle
        if self.color_popup.isVisible():
            self._place_popup_below_toolbar()
        
        self.raise_()

    # =================================================
    # SYNC UI
    # =================================================
    def sync(self):
        cf = self.editor.currentCharFormat()

        self.ui.btn_b.setProperty("active", cf.fontWeight() >= QFont.Weight.Bold)
        self.ui.btn_i.setProperty("active", cf.fontItalic())
        self.ui.btn_u.setProperty("active", cf.fontUnderline())
        self.ui.btn_s.setProperty("active", cf.fontStrikeOut())

        for b in (self.ui.btn_b, self.ui.btn_i, self.ui.btn_u, self.ui.btn_s):
            b.style().unpolish(b)
            b.style().polish(b)
            
            # Butonun metin rengini her zaman siyah yap
            b.setStyleSheet("""
                QPushButton {
                    color: #000000;
                    font-weight: normal;
                }
                QPushButton[active="true"] {
                    color: #000000;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #000000;
                }
            """)

        self.color_popup.sync_selected_borders()

    # =================================================
    # FORMAT ACTIONS
    # =================================================
    def bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(
            QFont.Weight.Normal
            if self.editor.currentCharFormat().fontWeight() >= QFont.Weight.Bold
            else QFont.Weight.Bold
        )
        self.apply_format(fmt)

    def italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.currentCharFormat().fontItalic())
        self.apply_format(fmt)

    def underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.currentCharFormat().fontUnderline())
        self.apply_format(fmt)

    def strike(self):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self.editor.currentCharFormat().fontStrikeOut())
        self.apply_format(fmt)

    # =================================================
    # APPLY FORMAT (CORE LOGIC)
    # =================================================
    def apply_format(self, fmt: QTextCharFormat):
        self._merge(fmt)

    def _merge(self, fmt: QTextCharFormat):
        """
        ✔ Undo block
        ✔ Selection snapshot
        ✔ Typing format reset (renk taşması yok)
        """
        if not self._selection_cursor or not self._selection_cursor.hasSelection():
            self.capture_selection_cursor()

        base = self._selection_cursor
        if not base or not base.hasSelection():
            return

        start = base.selectionStart()
        end = base.selectionEnd()

        cur = QTextCursor(base.document())
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        cur.beginEditBlock()
        cur.mergeCharFormat(fmt)
        cur.endEditBlock()

        self.editor.setTextCursor(cur)
        self._selection_cursor = QTextCursor(cur)

        fg_changed = fmt.foreground().style() != Qt.BrushStyle.NoBrush
        bg_changed = fmt.background().style() != Qt.BrushStyle.NoBrush

        if fg_changed or bg_changed:
            after = QTextCursor(cur)
            after.setPosition(end)
            after.clearSelection()
            self.editor.setTextCursor(after)

            reset = QTextCharFormat()
            reset.clearForeground()
            reset.clearBackground()
            self.editor.mergeCurrentCharFormat(reset)

            self.editor.setTextCursor(cur)

        self.editor.setFocus(Qt.FocusReason.OtherFocusReason)
        self.sync()
        QTimer.singleShot(0, self.update_position)
    
    # =================================================
    # CLEANUP
    # =================================================
    def cleanup(self):
        """Toolbar'ı ve popup'ları temizle"""
        try:
            # 1. ColorPopup'ı temizle
            if hasattr(self, 'color_popup') and self.color_popup:
                self.color_popup.hide()
                if hasattr(self.color_popup, 'cleanup'):
                    self.color_popup.cleanup()
                
            # 2. Tüm animasyonları durdur
            if hasattr(self, 'fade'):
                self.fade.stop()
            
            # 3. Graphics effect'i kaldır
            if hasattr(self, '_opacity'):
                self._opacity.setOpacity(0.0)
            
            # 4. Kendini gizle ve kapat
            self.hide()
            
            # 5. Parent'ı temizle
            self.setParent(None)
            
        except Exception:
            pass