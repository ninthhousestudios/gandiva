"""Rashi aspects overlay for the South Indian grid renderer.

Draws arrows between sign cells that have active rashi (Jaimini) aspects.
"""

import math

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPolygonF

from gandiva.overlays.base import ChartOverlay


# Must match south_indian.py grid layout
_SIGN_TO_CELL = {
    3: (0, 0),  2: (0, 1),  1: (0, 2), 12: (0, 3),
    4: (1, 0),                          11: (1, 3),
    5: (2, 0),                          10: (2, 3),
    6: (3, 0),  7: (3, 1),  8: (3, 2),  9: (3, 3),
}


class RashiAspectsOverlay(ChartOverlay):
    """Draws rashi aspect arrows on the South Indian grid."""

    compatible_styles = {"South Indian"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._aspect_pairs = []  # [(sign1_num, sign2_num, direction)]
        # direction: 1 = sign1→sign2, 2 = sign2→sign1, 3 = mutual

    def update_from_chart(self, chart) -> None:
        self._aspect_pairs = []
        try:
            signs = chart.rashi().signs()
            sign_list = list(signs)
            for i in range(len(sign_list)):
                for j in range(i + 1, len(sign_list)):
                    s1 = sign_list[i]
                    s2 = sign_list[j]
                    result = signs.rashi_aspect_between(s1, s2)
                    if result != 0:
                        self._aspect_pairs.append((s1.sign(), s2.sign(), result))
        except Exception:
            pass
        super().update_from_chart(chart)

    def _grid_geometry(self):
        rect = self._rect
        side = min(rect.width(), rect.height()) - 20
        cx, cy = rect.center().x(), rect.center().y()
        x0 = cx - side / 2
        y0 = cy - side / 2
        cw = side / 4
        ch = side / 4
        return x0, y0, cw, ch

    def _cell_center(self, sign_num, x0, y0, cw, ch):
        cell = _SIGN_TO_CELL.get(sign_num)
        if cell is None:
            return None
        row, col = cell
        return QPointF(x0 + (col + 0.5) * cw, y0 + (row + 0.5) * ch)

    def paint(self, painter, option, widget=None):
        if not self._aspect_pairs or not self._rect.isValid() or not self._theme:
            return

        x0, y0, cw, ch = self._grid_geometry()

        color = QColor(self._theme["aspect_hard"])
        color.setAlpha(140)
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        arrow_size = min(cw, ch) * 0.08

        for s1_num, s2_num, direction in self._aspect_pairs:
            p1 = self._cell_center(s1_num, x0, y0, cw, ch)
            p2 = self._cell_center(s2_num, x0, y0, cw, ch)
            if p1 is None or p2 is None:
                continue

            # Shorten line slightly so arrows don't overlap cell center
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            length = math.sqrt(dx*dx + dy*dy)
            if length < 1:
                continue
            ux, uy = dx / length, dy / length
            shrink = min(cw, ch) * 0.2
            lp1 = QPointF(p1.x() + ux * shrink, p1.y() + uy * shrink)
            lp2 = QPointF(p2.x() - ux * shrink, p2.y() - uy * shrink)

            painter.setPen(pen)
            painter.drawLine(lp1, lp2)

            # Arrowheads
            if direction in (1, 3):
                # Arrow pointing at p2 (sign1 → sign2)
                self._draw_arrowhead(painter, lp2, -ux, -uy, arrow_size, color)
            if direction in (2, 3):
                # Arrow pointing at p1 (sign2 → sign1)
                self._draw_arrowhead(painter, lp1, ux, uy, arrow_size, color)

    def _draw_arrowhead(self, painter, tip, back_ux, back_uy, size, color):
        """Draw a filled triangle arrowhead at `tip` pointing opposite to (back_ux, back_uy)."""
        # Perpendicular
        perp_x, perp_y = -back_uy, back_ux
        base1 = QPointF(tip.x() + back_ux * size + perp_x * size * 0.4,
                         tip.y() + back_uy * size + perp_y * size * 0.4)
        base2 = QPointF(tip.x() + back_ux * size - perp_x * size * 0.4,
                         tip.y() + back_uy * size - perp_y * size * 0.4)
        triangle = QPolygonF([tip, base1, base2])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(triangle)
