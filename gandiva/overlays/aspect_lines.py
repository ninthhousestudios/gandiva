"""Aspect lines overlay for the Western Wheel renderer.

Draws lines between planets that form standard western aspects
(sextile, square, trine, opposition). Lines pass through the center
of the wheel at the inner edge of the house ring.
"""

import math

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor

from gandiva.overlays.base import ChartOverlay


SKIP_PLANETS = {"Earth"}

# (name, angle, orb, is_hard, dash_pattern or None)
_ASPECTS = [
    ("sextile",     60,  6, False, [6, 4]),
    ("square",      90,  8, True,  None),
    ("trine",      120,  8, False, None),
    ("opposition", 180,  8, True,  None),
]

# Match WesternWheelRenderer geometry constants
FRAC_SIGN   = 0.12
FRAC_PLANET = 0.445
FRAC_HOUSE  = 0.10


class AspectLinesOverlay(ChartOverlay):
    """Draws aspect lines between planets on the Western Wheel."""

    compatible_styles = {"Western Wheel"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._asc_deg = 0.0
        self._planet_ecls = []    # [(name, ecl_deg)]
        self._aspects_found = []  # [(name1, name2, aspect_name, is_hard, dash)]

    def update_from_chart(self, chart) -> None:
        self._asc_deg = chart.rashi().cusps()[1].ecliptic_longitude()
        skip_outer = not chart.context.print_outer_planets

        self._planet_ecls = []
        for name, planet in chart.rashi().planets().items():
            if name in SKIP_PLANETS:
                continue
            if skip_outer and planet.is_outer_planet():
                continue
            try:
                self._planet_ecls.append((name, planet.ecliptic_longitude()))
            except Exception:
                continue

        self._find_aspects()
        super().update_from_chart(chart)

    def _find_aspects(self):
        """Compute all aspects between planet pairs."""
        self._aspects_found = []
        ecls = self._planet_ecls
        for i in range(len(ecls)):
            for j in range(i + 1, len(ecls)):
                n1, e1 = ecls[i]
                n2, e2 = ecls[j]
                sep = abs(e1 - e2)
                if sep > 180:
                    sep = 360 - sep
                for asp_name, asp_angle, orb, is_hard, dash in _ASPECTS:
                    if abs(sep - asp_angle) <= orb:
                        self._aspects_found.append((n1, n2, e1, e2, is_hard, dash))
                        break  # only strongest aspect per pair

    def _ecl_to_angle(self, ecl_deg):
        asc_sign_idx = int(self._asc_deg / 30)
        wheel_ref = asc_sign_idx * 30.0 + 15.0
        return math.radians(180.0 + (ecl_deg - wheel_ref))

    def paint(self, painter, option, widget=None):
        if not self._aspects_found or not self._rect.isValid() or not self._theme:
            return

        rect = self._rect
        side = min(rect.width(), rect.height())
        cx, cy = rect.center().x(), rect.center().y()
        r = side / 2 - 18
        # Draw lines at inner edge of house ring
        r_line = r - r * FRAC_SIGN - r * FRAC_PLANET - r * FRAC_HOUSE

        hard_color = QColor(self._theme["aspect_hard"])
        hard_color.setAlpha(160)
        soft_color = QColor(self._theme["aspect_soft"])
        soft_color.setAlpha(160)

        for n1, n2, e1, e2, is_hard, dash in self._aspects_found:
            a1 = self._ecl_to_angle(e1)
            a2 = self._ecl_to_angle(e2)
            x1 = cx + r_line * math.cos(a1)
            y1 = cy - r_line * math.sin(a1)
            x2 = cx + r_line * math.cos(a2)
            y2 = cy - r_line * math.sin(a2)

            color = hard_color if is_hard else soft_color
            pen = QPen(color, 1.5 if is_hard else 1.0)
            if dash:
                pen.setDashPattern(dash)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
