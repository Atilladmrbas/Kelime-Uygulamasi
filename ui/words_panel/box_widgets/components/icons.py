# ui/words_panel/box_widgets/components/icons.py
from PyQt6.QtGui import QColor, QPainter, QPixmap, QIcon, QPainterPath, QPen
from PyQt6.QtCore import Qt, QPointF

def make_trash_icon(size: int = 26) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(55, 55, 55), max(2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    w = float(size)
    h = float(size)

    cap_y = h * 0.24
    p.drawLine(QPointF(w * 0.18, cap_y), QPointF(w * 0.82, cap_y))
    p.drawLine(QPointF(w * 0.40, h * 0.13), QPointF(w * 0.60, h * 0.13))

    path = QPainterPath()
    path.moveTo(w * 0.22, cap_y)
    path.lineTo(w * 0.78, cap_y)
    path.lineTo(w * 0.68, h * 0.88)
    path.lineTo(w * 0.32, h * 0.88)
    path.closeSubpath()

    p.drawPath(path)
    p.end()
    return QIcon(pm)


def make_arrow_icon(size: int = 26) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(60, 60, 60), max(2, size * 0.09))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)

    w = float(size)
    h = float(size)

    p.drawLine(QPointF(w * 0.25, h * 0.50), QPointF(w * 0.68, h * 0.50))
    p.drawLine(QPointF(w * 0.55, h * 0.30), QPointF(w * 0.75, h * 0.50))
    p.drawLine(QPointF(w * 0.55, h * 0.70), QPointF(w * 0.75, h * 0.50))

    p.end()
    return QIcon(pm)