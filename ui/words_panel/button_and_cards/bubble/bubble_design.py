# bubble_design.py
# DRAG TASARIMI TAMAMEN KALDIRILDI – SADE VE TEMİZ TASARIM (TAM DOSYA)

from PyQt6.QtGui import QColor, QPainter, QPen, QPainterPath
from PyQt6.QtCore import Qt, QRectF


class BubbleDesign:
    BG_COLOR = QColor(255, 255, 255)
    BORDER_COLOR = QColor("#555")
    HEADER_BG = QColor(225, 225, 225)

    BORDER_WIDTH = 3
    RADIUS = 12
    HEADER_HEIGHT = 28
    TEXT_PADDING = 12

    @staticmethod
    def apply(widget):
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        widget.setAutoFillBackground(False)
        widget.setStyleSheet("background: transparent; border: none;")

    @staticmethod
    def paint(widget, p: QPainter):
        w, h = widget.width(), widget.height()
        bw = BubbleDesign.BORDER_WIDTH
        r = BubbleDesign.RADIUS
        hh = BubbleDesign.HEADER_HEIGHT

        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bubble_path = QPainterPath()
        bubble_path.addRoundedRect(
            QRectF(bw / 2, bw / 2, w - bw, h - bw),
            r, r
        )

        # BACKGROUND
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BubbleDesign.BG_COLOR)
        p.drawPath(bubble_path)

        # HEADER
        p.save()
        p.setClipPath(bubble_path)
        p.setBrush(BubbleDesign.HEADER_BG)
        p.drawRect(QRectF(bw, bw, w - bw * 2, hh))
        p.restore()

        # HEADER DIVIDER
        pen = QPen(BubbleDesign.BORDER_COLOR)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(bw, bw + hh, w - bw, bw + hh)

        # BORDER
        pen = QPen(BubbleDesign.BORDER_COLOR)
        pen.setWidth(bw)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bubble_path)
