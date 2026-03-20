"""Western wheel chart renderer — QGraphicsObject subclass of ChartRenderer."""

import math
from collections import defaultdict

from PyQt6.QtWidgets import QToolTip, QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPixmap,
    QFontMetricsF,
)

from libaditya.objects.context import Circle
from libaditya import constants as const

from gandiva.glyphs import PLANET_GLYPHS, SIGN_GLYPHS
from gandiva.glyph_renderer import draw_glyph, clear_cache
from gandiva.themes import get_theme, DEFAULT_THEME
from gandiva.renderers.base import ChartRenderer

CENTER_IMAGE = "/home/josh/nhs/images/logo/prometheus-footer.png"


def _fmt_lon(obj) -> str:
    """Format a planet or cusp longitude — works for both rashi and vargas."""
    return obj.longitude()


ZODIAC_NAMES = [
    "ARIES", "TAURUS", "GEMINI", "CANCER",
    "LEO", "VIRGO", "LIBRA", "SCORPIO",
    "SAGITTARIUS", "CAPRICORN", "AQUARIUS", "PISCES",
]

ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]

SKIP_PLANETS = {"Earth"}

HIT_RADIUS = 18

# Band widths as fractions of r_outer (outer → inner)
FRAC_SIGN   = 0.12   # sign name band
FRAC_PLANET = 0.445  # planet glyph band — expanded to fill space from shrinking inner region
FRAC_HOUSE  = 0.10   # combined house + cusp band
# remaining ~0.335 × r = center (image)


class WesternWheelRenderer(ChartRenderer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptHoverEvents(True)
        self.asc_deg          = 0.0
        self.wheel_ref_deg    = 15.0
        self.is_aditya        = True
        self.planet_positions = []
        self.selected_planet  = None
        self._center_pixmap   = QPixmap(CENTER_IMAGE)
        self.cusp_positions   = []
        self._active_tip      = ""   # track current tooltip to avoid resetting on every hover move

    def set_theme(self, theme: dict) -> None:
        super().set_theme(theme)
        # clear_cache() is called by ChartScene.set_theme(), not here

    def update_from_chart(self, chart) -> None:
        self.asc_deg   = chart.rashi().cusps()[1].ecliptic_longitude()
        self.is_aditya = chart.context.circle == Circle.ADITYA
        asc_sign_idx       = int(self.asc_deg / 30)
        self.wheel_ref_deg = asc_sign_idx * 30.0 + 15.0
        self.selected_planet = None
        super().update_from_chart(chart)  # stores self._chart, calls self.update()

    # ── geometry ──────────────────────────────────────────────────────────────

    def _geometry(self):
        rect = self.boundingRect()
        side = min(rect.width(), rect.height())
        cx, cy = rect.center().x(), rect.center().y()
        r        = side / 2 - 18
        r_sign   = r       - r * FRAC_SIGN
        r_planet = r_sign  - r * FRAC_PLANET
        r_house  = r_planet - r * FRAC_HOUSE
        return cx, cy, r, r_sign, r_planet, r_house

    def _ecl_to_angle(self, ecl_deg):
        """Ecliptic longitude → math angle (radians, CCW from +x).
        House-1 sign midpoint is placed at 9 o'clock (π)."""
        return math.radians(180.0 + (ecl_deg - self.wheel_ref_deg))

    def _polar(self, cx, cy, r, ecl_deg):
        a = self._ecl_to_angle(ecl_deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def _tangent_rotation(self, ecl_deg):
        """Qt rotation (degrees, CW) so text reads tangentially along the ring,
        flipped for the bottom half to stay right-side-up."""
        a_deg = math.degrees(self._ecl_to_angle(ecl_deg)) % 360
        rot = 90.0 - a_deg
        if 180 < a_deg < 360:
            rot += 180.0
        return rot

    def _angle_to_ecl(self, screen_angle_deg):
        """Inverse of _ecl_to_angle: screen angle (math deg) → ecliptic deg."""
        return (screen_angle_deg - 180.0 + self.wheel_ref_deg) % 360

    def _planet_at(self, pos):
        for name, px, py, info in self.planet_positions:
            dx, dy = pos.x() - px, pos.y() - py
            if math.sqrt(dx*dx + dy*dy) < HIT_RADIUS:
                return name, info
        return None

    def _cusp_at(self, pos):
        for label, px, py, tip in self.cusp_positions:
            dx, dy = pos.x() - px, pos.y() - py
            if math.sqrt(dx*dx + dy*dy) < HIT_RADIUS:
                return tip
        return None

    # ── paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter, option, widget=None):
        if self._chart is None or not self._rect.isValid():
            return
        p = painter
        cx, cy, r, r_sign, r_planet, r_house = self._geometry()
        self.cusp_positions = []
        self._draw_skeleton(p, cx, cy, r, r_sign, r_planet, r_house)
        self._draw_sign_names(p, cx, cy, r, r_sign)
        self._draw_planets(p, cx, cy, r_sign, r_planet)
        self._draw_house_ring(p, cx, cy, r_planet, r_house)
        self._draw_center_image(p, cx, cy, r_house)
        # Do NOT call p.end() — the scene manages the painter lifecycle

    # ── skeleton ──────────────────────────────────────────────────────────────

    def _draw_skeleton(self, p, cx, cy, r, r_sign, r_planet, r_house):
        t = self._theme
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(t["bg"]))
        p.drawEllipse(QPointF(cx, cy), r, r)

        p.setPen(QPen(t["line_light"], 0.7))
        for i in range(12):
            x, y = self._polar(cx, cy, r, i * 30.0)
            p.drawLine(QPointF(cx, cy), QPointF(x, y))

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(t["line"], 1.2))
        for ri in (r, r_sign, r_planet, r_house):
            p.drawEllipse(QPointF(cx, cy), ri, ri)

    # ── sign names (arc text) ─────────────────────────────────────────────────

    def _draw_sign_names(self, p, cx, cy, r, r_sign):
        band_w = r - r_sign
        r_mid  = (r + r_sign) / 2

        if self.is_aditya:
            font_pt = max(5, int(band_w * 0.52))
            font    = QFont("Sans", font_pt)
            raw     = [n.upper() for n in const.adityas]
            labels  = [raw[(i + 1) % 12] for i in range(12)]
            p.setPen(QPen(self._theme["sign_label"]))
            for i, label in enumerate(labels):
                mid_ecl = i * 30.0 + 15.0
                self._draw_arc_text(p, cx, cy, r_mid, mid_ecl, label, font)
        else:
            glyph_size = band_w * 2.89
            for i, glyph_data in enumerate(SIGN_GLYPHS):
                mid_ecl  = i * 30.0 + 15.0
                sx, sy   = self._polar(cx, cy, r_mid, mid_ecl)
                draw_glyph(p, glyph_data, sx, sy, size=glyph_size,
                           color=self._theme["sign_label"])

    def _draw_arc_text(self, p, cx, cy, r_arc, ecl_center, text, font):
        """Draw text curved along the arc at radius r_arc, centered at ecl_center.

        Top half (a_center in 0–180°): characters go CW (decreasing math angle).
        Bottom half (a_center in 180–360°): characters go CCW (increasing math angle)
        to match the 180° rotation flip applied by _tangent_rotation — without this
        reversal the text would read right-to-left at the bottom.
        """
        fm = QFontMetricsF(font)
        char_widths = [fm.horizontalAdvance(ch) for ch in text]
        total_w = sum(char_widths)
        ch_h    = fm.height()

        half_span_rad = total_w / (2.0 * r_arc)
        a_center      = self._ecl_to_angle(ecl_center)
        a_center_deg  = math.degrees(a_center) % 360
        # Bottom half uses opposite traversal direction to compensate for the
        # 180° character flip that keeps text right-side-up.
        bottom = 180 < a_center_deg < 360
        sign   = -1 if bottom else +1   # +1 = CW, -1 = CCW

        p.setFont(font)
        x_pos = 0.0
        for ch, ch_w in zip(text, char_widths):
            a_char = a_center + sign * (half_span_rad - (x_pos + ch_w / 2.0) / r_arc)

            sx = cx + r_arc * math.cos(a_char)
            sy = cy - r_arc * math.sin(a_char)

            # Use the label-level `bottom` flag (not the per-character angle) to
            # decide the rotation flip.  Per-character flipping breaks labels that
            # straddle the 180° boundary (e.g. DHĀTĀ near 9 o'clock) or the
            # 0°/360° wrap (e.g. TVAṢṬĀ near 3 o'clock): some chars would land on
            # the wrong side of the boundary and get a different flip, making them
            # appear rotated opposite to the rest of the label.
            a_deg = math.degrees(a_char) % 360
            rot   = 90.0 - a_deg
            if bottom:
                rot += 180.0

            p.save()
            p.translate(sx, sy)
            p.rotate(rot)
            p.drawText(QRectF(-ch_w / 2, -ch_h / 2, ch_w, ch_h),
                       Qt.AlignmentFlag.AlignCenter, ch)
            p.restore()

            x_pos += ch_w

    # ── planets ───────────────────────────────────────────────────────────────

    def _draw_planets(self, p, cx, cy, r_sign, r_planet):
        rashi      = self._chart.rashi()
        planets    = rashi.planets()
        band_w     = r_sign - r_planet
        r_mid      = (r_sign + r_planet) / 2

        skip_outer = not self._chart.context.print_outer_planets

        raw = []
        for name, planet in planets.items():
            if name in SKIP_PLANETS:
                continue
            if skip_outer and planet.is_outer_planet():
                continue
            try:
                ecl   = planet.ecliptic_longitude()
                retro = planet.retrograde()
                dig   = planet.dignity()
                try:
                    rise_str = f"Rise:       {planet.rise().usrtimedate()}"
                except Exception:
                    rise_str = ""
                try:
                    set_str = f"Set:        {planet.set().usrtimedate()}"
                except Exception:
                    set_str = ""
                info  = "\n".join(filter(None, [
                    f"{name}" + ("  (R)" if retro else ""),
                    f"Longitude:  {_fmt_lon(planet)}",
                    f"Sign:       {planet.sign_name()}",
                    f"Nakshatra:  {planet.nakshatra_name()}",
                    f"Dignity:    {dig}" if dig else "",
                    f"Speed:      {planet.longitude_speed():.4f}°/day",
                    rise_str,
                    set_str,
                ]))
                raw.append((name, ecl, retro, info))
            except Exception:
                continue

        if not raw:
            self.planet_positions = []
            return

        glyph_size = band_w * 0.55
        half       = glyph_size / 2
        min_dist   = glyph_size * 0.95

        # ── initial placement: true ecliptic longitude at r_mid ────────────────
        # Each entry: [x, y, name, retro, info, sign_idx, ecl_true]
        # Tiny deterministic per-planet offset prevents exact co-location so the
        # collision loop always has a well-defined push direction.
        items = []
        for idx, (name, ecl, retro, info) in enumerate(raw):
            x, y = self._polar(cx, cy, r_mid, ecl)
            x += (idx % 3 - 1) * 0.5
            y += (idx // 3 % 3 - 1) * 0.5
            sign_idx = int(ecl / 30)
            items.append([x, y, name, retro, info, sign_idx, ecl])

        # ── force-directed collision resolution in screen pixel space ──────────
        # Push overlapping glyphs apart; clamp radially (stay in band) and
        # angularly (stay in the planet's own sign sector).
        r_min = r_planet + half + 4
        r_max = r_sign   - half - 4

        for iteration in range(200):
            moved = False
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    dx = items[j][0] - items[i][0]
                    dy = items[j][1] - items[i][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < min_dist:
                        if dist < 0.01:
                            # Exactly co-located: push along index-derived axis
                            angle = (i - j) * math.pi / max(len(items), 1)
                            nx, ny = math.cos(angle), math.sin(angle)
                        else:
                            nx, ny = dx / dist, dy / dist
                        push = (min_dist - dist) / 2 + 0.3
                        items[i][0] -= nx * push
                        items[i][1] -= ny * push
                        items[j][0] += nx * push
                        items[j][1] += ny * push
                        moved = True

            # Clamp each item: radially within band, angularly within its sign
            for item in items:
                dx_c = item[0] - cx
                dy_c = item[1] - cy
                r = math.sqrt(dx_c * dx_c + dy_c * dy_c)
                if r < 1:
                    continue

                # Weak radial spring — keeps glyphs roughly centred in the band
                # without fighting the collision forces that spread them radially.
                target_r = r + (r_mid - r) * 0.02
                clamped_r = max(r_min, min(r_max, target_r))

                # Angular: soft spring toward true ecliptic position so isolated
                # planets snap back precisely, plus a ±15° hard outer limit so
                # no planet can drift more than half a sign from its true pos.
                screen_angle = math.degrees(math.atan2(-(item[1] - cy), item[0] - cx)) % 360
                ecl_deg  = self._angle_to_ecl(screen_angle)
                ecl_true = item[6]
                drift = ecl_deg - ecl_true
                if drift >  180: drift -= 360
                if drift < -180: drift += 360
                ecl_spring  = ecl_deg - drift * 0.008
                sign_idx_i  = item[5]
                sign_lo     = sign_idx_i * 30.0
                sign_hi     = sign_lo + 30.0
                margin_deg  = half / (2 * math.pi * ((r_min + r_max) / 2)) * 360
                ecl_clamped = max(sign_lo + margin_deg, min(sign_hi - margin_deg, ecl_spring))

                # Convert back to screen position
                a = self._ecl_to_angle(ecl_clamped)
                item[0] = cx + clamped_r * math.cos(a)
                item[1] = cy - clamped_r * math.sin(a)

            if not moved:
                break

        # ── draw glyphs ───────────────────────────────────────────────────────
        self.planet_positions = []
        for x, y, name, retro, info, _sign, _ecl in items:
            color  = self._theme["glyph_selected"] if name == self.selected_planet \
                     else self._theme["glyph_retro"] if retro \
                     else self._theme["glyph"]
            glyph_data = PLANET_GLYPHS.get(name)
            if glyph_data:
                draw_glyph(p, glyph_data, x, y, size=glyph_size, color=color)
            else:
                p.setPen(QPen(color, 1))
                p.setFont(QFont("Sans", max(6, int(glyph_size * 0.6))))
                p.drawText(QRectF(x - half, y - half, glyph_size, glyph_size),
                           Qt.AlignmentFlag.AlignCenter, name[:2])
            self.planet_positions.append((name, x, y, info))

    # ── combined house + cusp ring ─────────────────────────────────────────────

    def _draw_house_ring(self, p, cx, cy, r_planet, r_house):
        cusps   = self._chart.rashi().cusps()
        band_w  = r_planet - r_house

        # Cusp numerals in outer third, house numbers in inner third — no radial overlap
        r_cusp_row  = r_house + band_w * 0.72
        r_house_row = r_house + band_w * 0.28

        # House numbers: centered in each whole-sign sector, inner row
        font_pt_h = max(4, int(band_w * 0.39))
        font_h    = QFont("Sans", font_pt_h)
        box_h     = font_pt_h * 1.6
        asc_sign  = int(self.asc_deg / 30)

        p.setFont(font_h)
        p.setPen(QPen(self._theme["house_label"]))
        for house in range(1, 13):
            sign_idx = (asc_sign + house - 1) % 12
            mid_ecl  = sign_idx * 30.0 + 15.0
            lx, ly   = self._polar(cx, cy, r_house_row, mid_ecl)
            p.drawText(QRectF(lx - box_h/2, ly - box_h/2, box_h, box_h),
                       Qt.AlignmentFlag.AlignCenter, str(house))

        # Cusp numerals: half size of house, at actual cusp ecliptic degree, outer row
        font_pt_c = max(3, int(font_pt_h * 0.75))
        font_c    = QFont("Sans", font_pt_c)
        box_c     = font_pt_c * 1.4

        p.setFont(font_c)
        for i in range(1, 13):
            cusp   = cusps[i]
            ecl    = cusp.ecliptic_longitude()
            lx, ly = self._polar(cx, cy, r_cusp_row, ecl)
            weight = 1.6 if i in (1, 4, 7, 10) else 1.0
            p.setPen(QPen(self._theme["cusp_label"], weight))
            p.drawText(QRectF(lx - box_c/2, ly - box_c/2, box_c, box_c),
                       Qt.AlignmentFlag.AlignCenter, ROMAN[i - 1])
            try:
                tip = "\n".join([
                    f"Cusp {ROMAN[i-1]}  (House {i})",
                    f"Longitude:  {_fmt_lon(cusp)}",
                    f"Sign:       {cusp.sign_name()}",
                    f"Nakshatra:  {cusp.nakshatra_name()}",
                ])
            except Exception:
                tip = f"Cusp {ROMAN[i-1]}"
            self.cusp_positions.append((ROMAN[i - 1], lx, ly, tip))

    # ── center image ──────────────────────────────────────────────────────────

    def _draw_center_image(self, p, cx, cy, r_house):
        if self._center_pixmap.isNull():
            return
        d = int(r_house * 2)
        scaled = self._center_pixmap.scaled(
            d, d,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        clip = QPainterPath()
        clip.addEllipse(QPointF(cx, cy), r_house, r_house)
        p.save()
        p.setClipPath(clip)
        p.drawPixmap(
            int(cx - r_house), int(cy - r_house),
            scaled.copy(
                (scaled.width()  - d) // 2,
                (scaled.height() - d) // 2,
                d, d,
            ),
        )
        p.restore()
        p.setPen(QPen(self._theme["line"], 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_house, r_house)

    # ── mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        hit = self._planet_at(event.pos())
        name = hit[0] if hit else None
        self.selected_planet = name
        self.planet_selected.emit(name or "")
        self.update()
        super().mousePressEvent(event)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        planet_hit = self._planet_at(event.pos())
        cusp_tip   = self._cusp_at(event.pos())
        if planet_hit:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(planet_hit[1])
            if planet_hit[1] != self._active_tip:
                self._active_tip = planet_hit[1]
                # Force immediate show via QToolTip.showText, then setToolTip keeps it alive
                QToolTip.showText(event.screenPos(), planet_hit[1])
        elif cusp_tip:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(cusp_tip)
            if cusp_tip != self._active_tip:
                self._active_tip = cusp_tip
                QToolTip.showText(event.screenPos(), cusp_tip)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("")
            if self._active_tip:
                self._active_tip = ""
                QToolTip.hideText()
        super().hoverMoveEvent(event)
