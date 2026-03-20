"""Rashi aspects overlay for the South Indian grid renderer.

Draws arrows between sign cells that have active rashi (Jaimini) aspects.
"""

import math

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPolygonF

from libaditya import constants as const

from gandiva.overlays.base import ChartOverlay


# Must match south_indian.py grid layout
_SIGN_TO_CELL = {
    12: (0, 0),  1: (0, 1),  2: (0, 2),  3: (0, 3),
    11: (1, 0),                           4: (1, 3),
    10: (2, 0),                           5: (2, 3),
     9: (3, 0),  8: (3, 1),  7: (3, 2),  6: (3, 3),
}


class RashiAspectsOverlay(ChartOverlay):
    """Draws rashi aspect arrows on the South Indian grid."""

    compatible_styles = {"South Indian"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._aspect_pairs = []  # [(sign1_num, sign2_num, direction)]
        # direction: 1 = sign1→sign2, 2 = sign2→sign1, 3 = mutual
        self._aspect_mode = None  # override; None = use chart's mode
        self._occupied_signs = []  # sign numbers that have grahas

    def update_from_chart(self, chart) -> None:
        self._occupied_signs = []
        try:
            signs = chart.rashi().signs()
            for sign in signs:
                if sign.grahas():
                    self._occupied_signs.append(sign.sign())
        except Exception:
            pass
        self._recompute_aspects(chart)
        super().update_from_chart(chart)

    def set_aspect_mode(self, mode: str) -> None:
        self._aspect_mode = mode
        self._recompute_aspects(self._chart)
        self.update()

    def _recompute_aspects(self, chart) -> None:
        self._aspect_pairs = []
        if not chart or not self._occupied_signs:
            return
        try:
            mode = self._aspect_mode or chart.rashi().signs().context.rashi_aspects
            aspect_table = const.rashi_aspects[mode]

            seen = {}
            for sign_num in self._occupied_signs:
                for target_num in aspect_table[sign_num]:
                    seen[(sign_num, target_num)] = True

            # Collapse into directional pairs: 1=s1→s2, 2=s2→s1, 3=mutual
            pairs = {}
            for (src, tgt) in seen:
                key = (min(src, tgt), max(src, tgt))
                if key not in pairs:
                    pairs[key] = 0
                if src == key[0]:
                    pairs[key] |= 1
                else:
                    pairs[key] |= 2

            self._aspect_pairs = [(s1, s2, d) for (s1, s2), d in pairs.items()]
        except Exception:
            pass

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
