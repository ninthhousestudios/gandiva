"""South Indian grid chart renderer — fixed-sign 4×4 grid layout."""

import math

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetricsF,
)
from PyQt6.QtWidgets import QToolTip, QGraphicsSceneHoverEvent

from libaditya.objects.context import Circle
from libaditya import constants as const

from gandiva.glyphs import PLANET_GLYPHS
from gandiva.glyph_renderer import draw_glyph
from gandiva.renderers.base import ChartRenderer


# Fixed grid positions: (row, col) → sign number (1-indexed)
_CELL_SIGNS = [
    (0, 0,  3), (0, 1,  2), (0, 2,  1), (0, 3, 12),
    (1, 0,  4),                           (1, 3, 11),
    (2, 0,  5),                           (2, 3, 10),
    (3, 0,  6), (3, 1,  7), (3, 2,  8), (3, 3,  9),
]

# sign_number → (row, col)
_SIGN_TO_CELL = {sign: (r, c) for r, c, sign in _CELL_SIGNS}

SKIP_PLANETS = {"Earth"}

HIT_RADIUS = 16


class SouthIndianRenderer(ChartRenderer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptHoverEvents(True)
        self.asc_sign = 1
        self.is_aditya = True
        self.selected_planet = None
        self._planet_positions = []   # [(name, x, y, info_str)]
        self._sign_data = {}          # sign_num → [(name, retro, dignity, info_str)]

    def update_from_chart(self, chart) -> None:
        self.is_aditya = chart.context.circle == Circle.ADITYA
        self.asc_sign = int(chart.rashi().cusps()[1].ecliptic_longitude() / 30) + 1
        self.selected_planet = None
        self._extract_sign_data(chart)
        super().update_from_chart(chart)

    def _extract_sign_data(self, chart):
        """Group planets by sign for grid placement."""
        self._sign_data = {}
        rashi = chart.rashi()
        skip_outer = not chart.context.print_outer_planets

        for pname, planet in rashi.planets().items():
            if pname in SKIP_PLANETS:
                continue
            if skip_outer and planet.is_outer_planet():
                continue
            try:
                ecl = planet.ecliptic_longitude()
                sign_num = int(ecl / 30) % 12 + 1
                retro = planet.retrograde()
                dig = planet.dignity()
                info = "\n".join(filter(None, [
                    f"{pname}" + ("  (R)" if retro else ""),
                    f"Sign:       {planet.sign_name()}",
                    f"Dignity:    {dig}" if dig else "",
                    f"Speed:      {planet.longitude_speed():.4f}°/day",
                ]))
                self._sign_data.setdefault(sign_num, []).append(
                    (pname, retro, dig, info)
                )
            except Exception:
                continue

    # ── geometry ──────────────────────────────────────────────────────────────

    def _grid_geometry(self):
        """Return (x0, y0, cell_w, cell_h) for the 4×4 grid."""
        rect = self.boundingRect()
        side = min(rect.width(), rect.height()) - 20
        cx, cy = rect.center().x(), rect.center().y()
        x0 = cx - side / 2
        y0 = cy - side / 2
        cell_w = side / 4
        cell_h = side / 4
        return x0, y0, cell_w, cell_h

    def _cell_rect(self, row, col, x0, y0, cell_w, cell_h):
        return QRectF(x0 + col * cell_w, y0 + row * cell_h, cell_w, cell_h)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter, option, widget=None):
        if self._chart is None or not self._rect.isValid():
            return
        p = painter
        x0, y0, cw, ch = self._grid_geometry()
        self._planet_positions = []

        self._draw_grid(p, x0, y0, cw, ch)
        self._draw_sign_labels(p, x0, y0, cw, ch)
        self._draw_ascendant_mark(p, x0, y0, cw, ch)
        self._draw_planets_in_cells(p, x0, y0, cw, ch)
        self._draw_center(p, x0, y0, cw, ch)

    def _draw_grid(self, p, x0, y0, cw, ch):
        """Draw the outer border and grid lines."""
        t = self._theme
        side = cw * 4

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(t["bg"]))
        p.drawRect(QRectF(x0, y0, side, side))

        # Grid lines
        p.setPen(QPen(t["line"], 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Outer border
        p.drawRect(QRectF(x0, y0, side, side))

        # Vertical lines (full height)
        for c in range(1, 4):
            x = x0 + c * cw
            p.drawLine(QPointF(x, y0), QPointF(x, y0 + side))

        # Horizontal lines (full width)
        for r in range(1, 4):
            y = y0 + r * ch
            p.drawLine(QPointF(x0, y), QPointF(x0 + side, y))

        # Center area: erase inner grid lines to create 2×2 open center
        # Redraw center box borders (top, bottom inner borders)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(t["bg"]))
        p.drawRect(QRectF(x0 + cw + 1, y0 + ch + 1, cw * 2 - 2, ch * 2 - 2))

    def _draw_sign_labels(self, p, x0, y0, cw, ch):
        """Draw sign abbreviations in each cell."""
        t = self._theme
        label_font = QFont("Sans", max(5, int(min(cw, ch) * 0.14)))
        p.setFont(label_font)
        p.setPen(QPen(t["sign_label"]))

        for row, col, sign_num in _CELL_SIGNS:
            rect = self._cell_rect(row, col, x0, y0, cw, ch)
            if self.is_aditya:
                label = const.adityas[(sign_num - 1) % 12].upper()
            else:
                label = _ZODIAC_ABBREV[sign_num - 1]
            # Draw sign label at top-left of cell
            text_rect = QRectF(rect.x() + 3, rect.y() + 2,
                               rect.width() - 6, label_font.pointSize() * 1.8)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)

    def _draw_ascendant_mark(self, p, x0, y0, cw, ch):
        """Draw a diagonal line in the ascendant sign's cell."""
        cell = _SIGN_TO_CELL.get(self.asc_sign)
        if cell is None:
            return
        row, col = cell
        rect = self._cell_rect(row, col, x0, y0, cw, ch)
        p.setPen(QPen(self._theme["line_angular"], 1.5))
        # Diagonal from top-left to ~20% in
        d = min(cw, ch) * 0.25
        p.drawLine(QPointF(rect.x(), rect.y()), QPointF(rect.x() + d, rect.y() + d))

    def _draw_planets_in_cells(self, p, x0, y0, cw, ch):
        """Draw planet glyphs inside each sign's cell."""
        t = self._theme
        glyph_size = min(cw, ch) * 0.28

        for sign_num, planets in self._sign_data.items():
            cell = _SIGN_TO_CELL.get(sign_num)
            if cell is None:
                continue
            row, col = cell
            rect = self._cell_rect(row, col, x0, y0, cw, ch)

            # Layout planets in a grid within the cell
            # Leave top strip for sign label
            label_h = min(cw, ch) * 0.22
            avail_rect = QRectF(rect.x() + 4, rect.y() + label_h,
                                rect.width() - 8, rect.height() - label_h - 4)

            cols_per_row = max(1, int(avail_rect.width() / (glyph_size * 1.1)))

            for idx, (pname, retro, dig, info) in enumerate(planets):
                pr = idx // cols_per_row
                pc = idx % cols_per_row
                px = avail_rect.x() + (pc + 0.5) * (avail_rect.width() / cols_per_row)
                py = avail_rect.y() + (pr + 0.5) * glyph_size * 1.2

                if py + glyph_size / 2 > avail_rect.bottom():
                    break  # cell overflow — skip remaining

                color = t["glyph_selected"] if pname == self.selected_planet \
                    else t["glyph_retro"] if retro \
                    else t["glyph"]

                glyph_data = PLANET_GLYPHS.get(pname)
                if glyph_data:
                    draw_glyph(p, glyph_data, px, py, size=glyph_size, color=color)
                else:
                    p.setPen(QPen(color, 1))
                    p.setFont(QFont("Sans", max(5, int(glyph_size * 0.5))))
                    p.drawText(QRectF(px - glyph_size/2, py - glyph_size/2,
                                      glyph_size, glyph_size),
                               Qt.AlignmentFlag.AlignCenter, pname[:2])

                self._planet_positions.append((pname, px, py, info))

    def _draw_center(self, p, x0, y0, cw, ch):
        """Draw chart info in the center 2×2 area."""
        t = self._theme
        center_rect = QRectF(x0 + cw, y0 + ch, cw * 2, ch * 2)

        # Border for center area
        p.setPen(QPen(t["line"], 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(center_rect)

        # Chart name and info
        if self._chart:
            ctx = self._chart.context
            name = ctx.name.strip() or "Chart"
            font = QFont("Sans", max(6, int(min(cw, ch) * 0.18)))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QPen(t["glyph"]))

            lines = [name]
            try:
                lines.append(ctx.timeJD.usrtimedate())
            except Exception:
                pass
            try:
                lines.append(ctx.location.placename)
            except Exception:
                pass

            line_h = QFontMetricsF(font).height() * 1.3
            total_h = line_h * len(lines)
            start_y = center_rect.center().y() - total_h / 2

            for i, line in enumerate(lines):
                text_rect = QRectF(center_rect.x() + 8, start_y + i * line_h,
                                   center_rect.width() - 16, line_h)
                p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, line)

    # ── mouse interaction ─────────────────────────────────────────────────────

    def _planet_at(self, pos):
        for name, px, py, info in self._planet_positions:
            dx, dy = pos.x() - px, pos.y() - py
            if math.sqrt(dx*dx + dy*dy) < HIT_RADIUS:
                return name, info
        return None

    def mousePressEvent(self, event):
        hit = self._planet_at(event.pos())
        name = hit[0] if hit else None
        self.selected_planet = name
        self.planet_selected.emit(name or "")
        self.update()
        super().mousePressEvent(event)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        hit = self._planet_at(event.pos())
        if hit:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(hit[1])
            QToolTip.showText(event.screenPos(), hit[1])
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("")
            QToolTip.hideText()
        super().hoverMoveEvent(event)


# Sign abbreviations for non-Aditya mode (3-letter uppercase)
_ZODIAC_ABBREV = [
    "ARI", "TAU", "GEM", "CAN", "LEO", "VIR",
    "LIB", "SCO", "SAG", "CAP", "AQU", "PIS",
]
