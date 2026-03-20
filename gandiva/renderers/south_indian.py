"""South Indian grid chart renderer — fixed-sign 4×4 grid layout.

Sign positions are fixed: top-left is always Pisces (sign 12), proceeding
clockwise: 12, 1, 2, 3 across the top row, then down the right column,
across the bottom row right-to-left, and up the left column.
"""

import math

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetricsF,
    QPixmap, QPainterPath,
)
from PyQt6.QtWidgets import QToolTip, QGraphicsSceneHoverEvent

from libaditya.objects.context import Circle
from libaditya import constants as const

from gandiva.glyphs import PLANET_GLYPHS, SIGN_GLYPHS
from gandiva.glyph_renderer import draw_glyph
from gandiva.renderers.base import ChartRenderer
from gandiva.assets import CENTER_IMAGE


def _fmt_lon(obj) -> str:
    """Format a planet or cusp longitude — works for both rashi and vargas."""
    return obj.longitude()

# Fixed grid positions — clockwise from top-left (Pisces).
# (row, col) → sign number (1-indexed)
_CELL_SIGNS = [
    (0, 0, 12), (0, 1,  1), (0, 2,  2), (0, 3,  3),
    (1, 3,  4),                           (1, 0, 11),
    (2, 3,  5),                           (2, 0, 10),
    (3, 3,  6), (3, 2,  7), (3, 1,  8), (3, 0,  9),
]

# sign_number → (row, col)
_SIGN_TO_CELL = {sign: (r, c) for r, c, sign in _CELL_SIGNS}

SKIP_PLANETS = {"Earth"}

_ROMAN = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
    7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII",
}

HIT_RADIUS = 18


class SouthIndianRenderer(ChartRenderer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptHoverEvents(True)
        self.asc_sign = 1
        self.is_aditya = True
        self.selected_planet = None
        self._planet_positions = []   # [(name, x, y, info_str)]
        self._sign_data = {}          # sign_num → [(name, retro, dignity, info_str)]
        self._cusp_in_sign = {}       # sign_num → cusp_number (1-12)
        self._center_pixmap = QPixmap(CENTER_IMAGE)

    def update_from_chart(self, chart) -> None:
        self.is_aditya = chart.context.circle == Circle.ADITYA
        self.asc_sign = int(chart.rashi().cusps()[1].ecliptic_longitude() / 30) + 1
        self.selected_planet = None
        self._extract_sign_data(chart)
        self._extract_cusp_data(chart)
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
                if self.is_aditya:
                    sign_num = sign_num % 12 + 1
                retro = planet.retrograde()
                dig = planet.dignity()
                info = "\n".join(filter(None, [
                    f"{pname}" + ("  (R)" if retro else ""),
                    f"Longitude:  {_fmt_lon(planet)}",
                    f"Sign:       {planet.sign_name()}",
                    f"Dignity:    {dig}" if dig else "",
                    f"Speed:      {planet.longitude_speed():.4f}°/day",
                ]))
                self._sign_data.setdefault(sign_num, []).append(
                    (pname, retro, dig, info)
                )
            except Exception:
                continue

    def _extract_cusp_data(self, chart):
        """Map each cusp to the sign it falls in, with tooltip info."""
        self._cusp_in_sign = {}
        self._cusp_positions = []  # [(label, x, y, tip)] filled during paint
        rashi = chart.rashi()
        for i in range(1, 13):
            try:
                cusp = rashi.cusps()[i]
                ecl = cusp.ecliptic_longitude()
                sign_num = int(ecl / 30) % 12 + 1
                if self.is_aditya:
                    sign_num = sign_num % 12 + 1
                tip = "\n".join(filter(None, [
                    f"Cusp {_ROMAN[i]}  (House {i})",
                    f"Longitude:  {_fmt_lon(cusp)}",
                    f"Sign:       {cusp.sign_name()}",
                    f"Nakshatra:  {cusp.nakshatra_name()}",
                ]))
                self._cusp_in_sign[sign_num] = (i, tip)
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
        self._draw_cusp_numerals(p, x0, y0, cw, ch)
        self._draw_planets_in_cells(p, x0, y0, cw, ch)
        self._draw_center_image(p, x0, y0, cw, ch)

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
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(t["bg"]))
        p.drawRect(QRectF(x0 + cw + 1, y0 + ch + 1, cw * 2 - 2, ch * 2 - 2))

    def _draw_sign_labels(self, p, x0, y0, cw, ch):
        """Draw sign labels in each cell — glyphs for tropical/sidereal, text for aditya."""
        t = self._theme

        if self.is_aditya:
            # Aditya mode: small text labels
            label_font = QFont("Sans", max(5, int(min(cw, ch) * 0.11)))
            p.setFont(label_font)
            p.setPen(QPen(t["sign_label"]))

            for row, col, sign_num in _CELL_SIGNS:
                rect = self._cell_rect(row, col, x0, y0, cw, ch)
                label = const.adityas[(sign_num - 1) % 12].upper()
                text_rect = QRectF(rect.x() + 3, rect.y() + 2,
                                   rect.width() - 6, label_font.pointSize() * 1.8)
                halign = Qt.AlignmentFlag.AlignLeft if col <= 1 else Qt.AlignmentFlag.AlignRight
                p.drawText(text_rect,
                           int(halign | Qt.AlignmentFlag.AlignTop),
                           label)
        else:
            # Tropical/sidereal: sign glyphs
            glyph_size = min(cw, ch) * 0.50
            margin = glyph_size * 0.45
            for row, col, sign_num in _CELL_SIGNS:
                rect = self._cell_rect(row, col, x0, y0, cw, ch)
                glyph_data = SIGN_GLYPHS[(sign_num - 1) % 12]
                # Left side (cols 0-1): upper-left corner
                # Right side (cols 2-3): upper-right corner
                if col <= 1:
                    gx = rect.x() + margin
                else:
                    gx = rect.right() - margin
                gy = rect.y() + margin
                draw_glyph(p, glyph_data, gx, gy, size=glyph_size,
                           color=t["sign_label"])

    def _draw_cusp_numerals(self, p, x0, y0, cw, ch):
        """Draw roman numeral for each cusp, with positions for hover tooltips."""
        t = self._theme
        font = QFont("Sans", max(5, int(min(cw, ch) * 0.09)))
        fm = QFontMetricsF(font)
        p.setFont(font)
        self._cusp_positions = []

        for sign_num, (cusp_num, tip) in self._cusp_in_sign.items():
            cell = _SIGN_TO_CELL.get(sign_num)
            if cell is None:
                continue
            row, col = cell
            rect = self._cell_rect(row, col, x0, y0, cw, ch)
            numeral = _ROMAN[cusp_num]
            weight = 1.6 if cusp_num in (1, 4, 7, 10) else 1.0
            p.setPen(QPen(t["line_angular"], weight))

            # Place opposite to sign label: left side cells → right, right side → left
            text_h = font.pointSize() * 1.8
            if col <= 1:
                halign = Qt.AlignmentFlag.AlignRight
                text_rect = QRectF(rect.x() + 4, rect.y() + 2,
                                   rect.width() - 8, text_h)
                # Hit position: right side of cell
                tx = rect.right() - 4 - fm.horizontalAdvance(numeral) / 2
            else:
                halign = Qt.AlignmentFlag.AlignLeft
                text_rect = QRectF(rect.x() + 4, rect.y() + 2,
                                   rect.width() - 8, text_h)
                # Hit position: left side of cell
                tx = rect.x() + 4 + fm.horizontalAdvance(numeral) / 2
            ty = rect.y() + 2 + text_h / 2

            p.drawText(text_rect,
                       int(halign | Qt.AlignmentFlag.AlignTop),
                       numeral)
            self._cusp_positions.append((numeral, tx, ty, tip))

    def _draw_planets_in_cells(self, p, x0, y0, cw, ch):
        """Draw planet glyphs inside each sign's cell."""
        t = self._theme
        glyph_size = min(cw, ch) * 0.34

        for sign_num, planets in self._sign_data.items():
            cell = _SIGN_TO_CELL.get(sign_num)
            if cell is None:
                continue
            row, col = cell
            rect = self._cell_rect(row, col, x0, y0, cw, ch)

            # Leave top strip for sign label
            label_h = min(cw, ch) * 0.22
            avail_rect = QRectF(rect.x() + 2, rect.y() + label_h,
                                rect.width() - 4, rect.height() - label_h - 2)

            cols_per_row = max(1, int(avail_rect.width() / (glyph_size * 0.95)))

            for idx, (pname, retro, dig, info) in enumerate(planets):
                pr = idx // cols_per_row
                pc = idx % cols_per_row
                px = avail_rect.x() + (pc + 0.5) * (avail_rect.width() / cols_per_row)
                py = avail_rect.y() + (pr + 0.5) * glyph_size * 1.15

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
                               int(Qt.AlignmentFlag.AlignCenter), pname[:2])

                self._planet_positions.append((pname, px, py, info))

    def _draw_center_image(self, p, x0, y0, cw, ch):
        """Draw circular center image in the 2×2 center area."""
        center_rect = QRectF(x0 + cw, y0 + ch, cw * 2, ch * 2)

        # Border for center area
        p.setPen(QPen(self._theme["line"], 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(center_rect)

        if self._center_pixmap.isNull():
            return

        # Circular clip inside the center area
        cx = center_rect.center().x()
        cy = center_rect.center().y()
        r = min(cw, ch) * 0.9

        d = int(r * 2)
        scaled = self._center_pixmap.scaled(
            d, d,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        clip = QPainterPath()
        clip.addEllipse(QPointF(cx, cy), r, r)
        p.save()
        p.setClipPath(clip)
        p.drawPixmap(
            int(cx - r), int(cy - r),
            scaled.copy(
                (scaled.width() - d) // 2,
                (scaled.height() - d) // 2,
                d, d,
            ),
        )
        p.restore()
        p.setPen(QPen(self._theme["line"], 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

    # ── mouse interaction ─────────────────────────────────────────────────────

    def _planet_at(self, pos):
        for name, px, py, info in self._planet_positions:
            dx, dy = pos.x() - px, pos.y() - py
            if math.sqrt(dx*dx + dy*dy) < HIT_RADIUS:
                return name, info
        return None

    def _cusp_at(self, pos):
        for label, px, py, tip in self._cusp_positions:
            dx, dy = pos.x() - px, pos.y() - py
            if math.sqrt(dx*dx + dy*dy) < HIT_RADIUS:
                return tip
        return None

    def mousePressEvent(self, event):
        hit = self._planet_at(event.pos())
        name = hit[0] if hit else None
        self.selected_planet = name
        self.planet_selected.emit(name or "")
        self.update()
        super().mousePressEvent(event)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        planet_hit = self._planet_at(event.pos())
        cusp_tip = self._cusp_at(event.pos())
        if planet_hit:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(planet_hit[1])
            QToolTip.showText(event.screenPos(), planet_hit[1])
        elif cusp_tip:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(cusp_tip)
            QToolTip.showText(event.screenPos(), cusp_tip)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("")
            QToolTip.hideText()
        super().hoverMoveEvent(event)
