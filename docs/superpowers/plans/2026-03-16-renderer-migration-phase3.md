# Renderer Migration — Phase 3: South Indian Renderer, Overlays, MiniVargaWidget

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second chart style (South Indian grid), two overlay implementations (aspect lines for western wheel, rashi aspects for south indian grid), and the MiniVargaWidget that reuses renderers at small scale for divisional charts.

**Architecture:** South Indian renderer draws a 4×4 grid with fixed sign positions and planet glyphs laid out within cells. Overlays draw semi-transparent lines/arrows over the chart using QPainter. MiniVargaWidget embeds a QGraphicsScene+QGraphicsView inside the InfoWidget proxy, hosting a renderer instance at small scale.

**Tech Stack:** Python 3, PyQt6 (QPainter, QGraphicsScene/View, QGraphicsProxyWidget), libaditya

**Branch:** `renderer-migration` (continues from Phase 2)

**Spec:** `docs/superpowers/specs/2026-03-16-chart-scene-architecture-design.md`

**Phase 2 plan:** `docs/superpowers/plans/2026-03-16-renderer-migration-phase2.md`

---

## What already exists (Phase 2 output)

```
gandiva/
  scene/
    chart_scene.py       # ChartScene — real overlay/widget management, auto-placement
    chart_view.py        # ChartView
  renderers/
    __init__.py          # CHART_STYLES = {"Western Wheel": WesternWheelRenderer}
    base.py              # ChartRenderer(QGraphicsObject) ABC
    western_wheel.py     # WesternWheelRenderer — full wheel with collision physics
  overlays/
    __init__.py          # OVERLAYS = {} (empty registry)
    base.py              # ChartOverlay(QGraphicsObject) ABC
  info_widgets/
    __init__.py          # INFO_WIDGETS = {"Panchanga": ..., "Dasha Periods": ...}
    base.py              # InfoWidget(QGraphicsProxyWidget) base — draggable, chrome, hover close
    panchanga.py         # PanchangaWidget
    dasha.py             # DashaWidget
  widgets/
    chart_input.py       # ChartInputPanel — chart style dropdown on Display tab
    left_panel.py        # LeftPanel — overlay/widget checkboxes, collapsible
  main_window.py         # 3-way splitter, full signal wiring
  themes.py              # 3 themes (Cosmic, Forest, Light), 18 color keys each
```

Key APIs already in place:
- `ChartScene.add_overlay(id)` / `remove_overlay(id)` — registry lookup, z-value, state init, signal emit
- `ChartScene.add_info_widget(id)` / `remove_info_widget(id)` — same + auto-placement + close signal
- `CHART_STYLES` dropdown wired to `ChartScene.set_chart_style(name)` which clears overlays on switch
- `LeftPanel` two-way sync with scene for overlay/widget checkboxes

---

## File Structure (new/modified files)

```
gandiva/
  renderers/
    south_indian.py      # NEW: SouthIndianRenderer(ChartRenderer)
    __init__.py          # MODIFY: add "South Indian" to CHART_STYLES
  overlays/
    aspect_lines.py      # NEW: AspectLinesOverlay(ChartOverlay) — western wheel
    rashi_aspects.py     # NEW: RashiAspectsOverlay(ChartOverlay) — south indian
    __init__.py          # MODIFY: register both overlays
  info_widgets/
    mini_varga.py        # NEW: MiniVargaWidget(InfoWidget) — embedded renderer
    __init__.py          # MODIFY: add Mini Navamsha, Mini Hora entries
  themes.py              # MODIFY: add 2 aspect color keys to each theme
```

---

## Chunk 1: South Indian Renderer

### Task 1: Implement SouthIndianRenderer

**Files:**
- Create: `gandiva/renderers/south_indian.py`
- Modify: `gandiva/renderers/__init__.py`

The South Indian chart is a 4×4 grid where signs have **fixed positions** (Aries is always top-right). The ascendant sign is marked with a diagonal line. Planets are drawn inside their sign's cell.

**Grid layout (row, col → sign number 1-12):**
```
┌────────┬────────┬────────┬────────┐
│ 3 Gem  │ 2 Tau  │ 1 Ari  │12 Pis  │  row 0
├────────┼────────┴────────┼────────┤
│ 4 Can  │                 │11 Aqu  │  row 1
├────────┤    (center)     ├────────┤
│ 5 Leo  │                 │10 Cap  │  row 2
├────────┼────────┬────────┼────────┤
│ 6 Vir  │ 7 Lib  │ 8 Sco  │ 9 Sag  │  row 3
└────────┴────────┴────────┴────────┘
  col 0    col 1    col 2    col 3
```

**libaditya API reference:**
```python
rashi   = chart.rashi()
signs   = rashi.signs()        # Signs object, iterable over Sign objects
cusps   = rashi.cusps()        # cusps[1].ecliptic_longitude() → float

# Per Sign:
sign.sign()                    # int, 1-12
sign.name()                    # str, e.g. "Aries"
sign.planets()                 # [Planet] — all planets in this sign
sign.grahas()                  # [Planet] — sun-ketu only (Vedic planets)

# Per Planet (from rashi.planets().items()):
# name comes from dict key, e.g. "Sun", "Moon"
planet.ecliptic_longitude()    # float, 0-360
planet.retrograde()            # bool
planet.dignity()               # str code or ""
planet.is_outer_planet()       # bool
planet.longitude_speed()       # float, deg/day

# Aditya sign names:
from libaditya import constants as const
const.adityas                  # list of 12 Aditya names, 0-indexed: [0]="dhātā"=sign 1
```

**IMPORTANT — planet name access:** When iterating `rashi.planets().items()`, the dict key IS the planet name string (e.g., `"Sun"`, `"Moon"`). Do NOT use `planet.name()` (method — appends "R" for retrograde) or `planet.name` (not a simple attribute). Always get the name from the iteration key, same as `WesternWheelRenderer` does.

**IMPORTANT — `const.adityas` indexing:** The list is 0-indexed: `adityas[0]` = "dhātā" = sign 1 (Aries equivalent). For sign number N (1-12), use `const.adityas[(sign_num - 1) % 12]`.

- [ ] **Step 1: Create `gandiva/renderers/south_indian.py`**

```python
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
                sign_num = int(ecl / 30) + 1
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
```

- [ ] **Step 2: Register in `gandiva/renderers/__init__.py`**

Add after the WesternWheelRenderer import:

```python
from gandiva.renderers.south_indian import SouthIndianRenderer  # noqa: E402

CHART_STYLES["South Indian"] = SouthIndianRenderer
```

- [ ] **Step 3: Verify import**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.renderers import CHART_STYLES; print(list(CHART_STYLES.keys()))"
```
Expected: `['Western Wheel', 'South Indian']`

- [ ] **Step 4: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Chart Style dropdown now shows "Western Wheel" and "South Indian"
- Selecting "South Indian" shows a 4×4 grid with signs in fixed positions
- Planets appear in their correct sign cells
- Ascendant sign has a diagonal mark in its cell
- Center area shows chart name, date, location
- Hovering over planet glyphs shows tooltip
- Clicking a planet highlights it
- Switching back to "Western Wheel" works
- Theme changes apply to the south indian grid
- Recalculating updates the grid correctly
- Aditya mode shows Aditya sign names, zodiac mode shows abbreviations

- [ ] **Step 5: Commit**

```bash
git add gandiva/renderers/south_indian.py gandiva/renderers/__init__.py
git commit -m "add South Indian grid chart renderer"
```

---

## Chunk 2: Aspect Overlays

### Task 2: Add aspect theme colors + AspectLinesOverlay (Western Wheel)

**Files:**
- Modify: `gandiva/themes.py` (add 2 color keys to each theme)
- Create: `gandiva/overlays/aspect_lines.py`
- Modify: `gandiva/overlays/__init__.py`

The AspectLinesOverlay draws lines between planets that form standard western aspects (conjunction, sextile, square, trine, opposition). Lines are drawn through the center of the wheel, connecting planet positions at the inner edge of the planet band.

**Aspect types and orbs (standard western):**
```
Conjunction:  0°, orb 8° — drawn as a small dot/highlight, not a line
Sextile:     60°, orb 6° — harmonious, dashed line
Square:      90°, orb 8° — tense, solid line
Trine:      120°, orb 8° — harmonious, solid line
Opposition: 180°, orb 8° — tense, solid thick line
```

**No libaditya API needed** — aspects are computed geometrically from ecliptic longitudes. This overlay does pure geometry using planet positions already extracted by the renderer.

**How to get planet ecliptic longitudes:**
```python
rashi = chart.rashi()
for name, planet in rashi.planets().items():
    ecl = planet.ecliptic_longitude()  # float, 0-360
```

**Drawing geometry:** Lines connect pairs of planet ecliptic positions at a radius inside the house ring. The WesternWheelRenderer uses these geometry constants:
```python
FRAC_SIGN   = 0.12   # sign band
FRAC_PLANET = 0.445  # planet band
FRAC_HOUSE  = 0.10   # house + cusp band
# r_house = r - r*FRAC_SIGN - r*FRAC_PLANET - r*FRAC_HOUSE
# Lines should connect at r_house (inner edge of house ring)
```

The overlay needs to replicate the wheel's coordinate transform to draw at the right positions. It stores the ascendant degree and uses the same `_ecl_to_angle` conversion:
```python
def _ecl_to_angle(self, ecl_deg):
    asc_sign_idx = int(self._asc_deg / 30)
    wheel_ref = asc_sign_idx * 30.0 + 15.0
    return math.radians(180.0 + (ecl_deg - wheel_ref))
```

- [ ] **Step 1: Add aspect colors to themes**

In `gandiva/themes.py`, add two keys to each theme dict, after the `"house_label"` line:

**Cosmic:**
```python
    "aspect_hard":     _c(255, 80, 80),     # red for squares/oppositions
    "aspect_soft":     _c(80, 200, 255),     # cyan-blue for trines/sextiles
```

**Forest:**
```python
    "aspect_hard":     _c(200, 80, 50),      # rust red
    "aspect_soft":     _c(100, 160, 100),     # muted green
```

**Light:**
```python
    "aspect_hard":     _c(200, 50, 50),      # red
    "aspect_soft":     _c(50, 120, 200),      # blue
```

- [ ] **Step 2: Create `gandiva/overlays/aspect_lines.py`**

```python
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
```

- [ ] **Step 3: Register in `gandiva/overlays/__init__.py`**

```python
"""Overlay registry."""

OVERLAYS: dict[str, type] = {}

from gandiva.overlays.aspect_lines import AspectLinesOverlay  # noqa: E402

OVERLAYS["Aspect Lines"] = AspectLinesOverlay
```

- [ ] **Step 4: Verify import**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.overlays import OVERLAYS; print(list(OVERLAYS.keys()))"
```
Expected: `['Aspect Lines']`

- [ ] **Step 5: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel Overlays tab shows "Aspect Lines" checkbox
- With Western Wheel active, checking it draws colored lines between planets that aspect each other
- Hard aspects (squares, oppositions) use red/rust color
- Soft aspects (trines, sextiles) use blue/green color, sextiles are dashed
- Lines connect at the inner edge of the house ring
- Lines are semi-transparent
- Switching chart style clears overlays (checkbox unchecks)
- Recalculating updates aspect lines
- Theme changes update aspect line colors
- Lines don't appear when no aspects exist (unlikely but verify no crash)

- [ ] **Step 6: Commit**

```bash
git add gandiva/themes.py gandiva/overlays/aspect_lines.py gandiva/overlays/__init__.py
git commit -m "add aspect line colors to themes and AspectLinesOverlay for western wheel"
```

---

### Task 3: Implement RashiAspectsOverlay (South Indian)

**Files:**
- Create: `gandiva/overlays/rashi_aspects.py`
- Modify: `gandiva/overlays/__init__.py`

Draws arrows between cells on the South Indian grid showing active rashi (Jaimini) aspects. An arrow from cell A to cell B means sign A has grahas that aspect sign B.

**libaditya API reference:**
```python
signs = chart.rashi().signs()    # Signs object

# For each pair of occupied signs, check aspect:
signs.rashi_aspect_between(sign1, sign2)
# Returns:
#   0 — no aspect
#   1 — sign1 → sign2
#   2 — sign2 → sign1
#   3 — mutual (both directions)

# signs is iterable: for sign in signs: ...
# sign.sign() → int 1-12
# sign.grahas() → [Planet] (empty if no vedic planets in sign)
```

**Drawing approach:**
- For each pair of signs where `rashi_aspect_between != 0`, draw an arrow line between their cell centers
- One-way aspects: single arrowhead
- Mutual aspects (return value 3): arrowheads on both ends
- Use `aspect_hard` color (these are rashi aspects, no soft/hard distinction — just use one color with good visibility)
- Lines are semi-transparent, slightly offset from center to avoid overlapping

**Grid geometry:** Must match `SouthIndianRenderer._grid_geometry()`:
```python
rect = self.boundingRect()
side = min(rect.width(), rect.height()) - 20
cx, cy = rect.center().x(), rect.center().y()
x0 = cx - side / 2
y0 = cy - side / 2
cell_w = side / 4
cell_h = side / 4
```

Cell center for sign N at `_SIGN_TO_CELL[N]` = `(row, col)`:
```python
center_x = x0 + (col + 0.5) * cell_w
center_y = y0 + (row + 0.5) * cell_h
```

- [ ] **Step 1: Create `gandiva/overlays/rashi_aspects.py`**

```python
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
```

- [ ] **Step 2: Register in `gandiva/overlays/__init__.py`**

Add after the AspectLinesOverlay registration:

```python
from gandiva.overlays.rashi_aspects import RashiAspectsOverlay  # noqa: E402

OVERLAYS["Rashi Aspects"] = RashiAspectsOverlay
```

- [ ] **Step 3: Verify import**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.overlays import OVERLAYS; print(list(OVERLAYS.keys()))"
```
Expected: `['Aspect Lines', 'Rashi Aspects']`

- [ ] **Step 4: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel Overlays tab shows "Aspect Lines" and "Rashi Aspects" checkboxes
- Switch to South Indian chart style
- Check "Rashi Aspects" — arrows appear between sign cells
- One-way aspects show a single arrowhead
- Mutual aspects show arrowheads on both ends
- Arrows are semi-transparent
- Change the Jaimini "Aspects" dropdown (Calc Options tab) to "element" or "conventional", recalculate — arrows update to reflect the new aspect mode
- Switch to Western Wheel — overlay is cleared (checkbox unchecks)
- The overlay doesn't crash when used with the "wrong" chart style (it just draws in grid coordinates that don't align with the wheel — this is by design per spec)

- [ ] **Step 5: Commit**

```bash
git add gandiva/overlays/rashi_aspects.py gandiva/overlays/__init__.py
git commit -m "add RashiAspectsOverlay for South Indian grid"
```

---

## Chunk 3: MiniVargaWidget

### Task 4: Implement MiniVargaWidget

**Files:**
- Create: `gandiva/info_widgets/mini_varga.py`
- Modify: `gandiva/info_widgets/__init__.py`

The MiniVargaWidget displays a small divisional chart (e.g., Navamsha D9, Hora D2) using an embedded renderer at small scale. It creates its own QGraphicsScene+QGraphicsView inside the InfoWidget proxy, hosts a renderer instance, and feeds it varga data.

**libaditya varga API:**
```python
varga_chart = chart.varga(9)     # Navamsha
varga_chart.planets()            # same interface as chart.rashi().planets()
varga_chart.cusps()              # same interface as chart.rashi().cusps()
varga_chart.varga_name()         # "Navamsha", "Hora", etc.

# Positive vargas: 1-60+ (parivritti method)
# Negative vargas: special deity-based methods
#   -2=Hora, -3=Drekkana, -4=Chaturthamsha, etc.

# IMPORTANT: chart.varga() returns a Varga object, not a Chart.
# Varga has .planets() and .cusps() but NOT .rashi() — it IS the rashi equivalent.
# So the renderer's update_from_chart() which calls chart.rashi() will NOT work
# directly with a Varga object.
```

**Key challenge:** `WesternWheelRenderer.update_from_chart(chart)` calls `chart.rashi().cusps()` and `chart.rashi().planets()`. But `chart.varga(9)` returns a `Varga` object which has `.cusps()` and `.planets()` directly (no `.rashi()` method). The MiniVargaWidget must wrap the varga data so the renderer can consume it.

**Solution:** Create a thin adapter that wraps a Varga to look like what the renderer expects:
```python
class _VargaAdapter:
    """Makes a Varga quack like a Chart for renderer consumption."""
    def __init__(self, varga, original_chart):
        self._varga = varga
        self.context = original_chart.context
    def rashi(self):
        return self._varga
```

This works because `Varga` already has `.planets()`, `.cusps()`, `.signs()` — the same methods as `Rashi`. The renderers call `chart.rashi().planets()` and `chart.rashi().cusps()`, so wrapping the varga in `.rashi()` makes it transparent.

**Renderer choice:** The mini widget uses the South Indian renderer by default (it's more space-efficient at small sizes). The western wheel's collision physics are expensive and the radial layout doesn't read well at small sizes.

**Widget size:** Fixed 240×240px — large enough to see the grid, small enough to not dominate the scene.

- [ ] **Step 1: Create `gandiva/info_widgets/mini_varga.py`**

```python
"""Mini varga info widget — displays a small divisional chart."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QColor

from gandiva.info_widgets.base import InfoWidget
from gandiva.renderers.south_indian import SouthIndianRenderer


MINI_SIZE = 240


class _VargaAdapter:
    """Makes a Varga quack like a Chart for renderer consumption.

    Note: .context is the original chart's context (not the varga's internal
    context). This is intentional — the renderer reads context.circle and
    context.print_outer_planets from it, which should reflect the user's
    top-level settings.
    """

    def __init__(self, varga, original_chart):
        self._varga = varga
        self.context = original_chart.context

    def rashi(self):
        return self._varga


class MiniVargaWidget(InfoWidget):
    """Displays a small divisional chart using an embedded renderer."""

    def __init__(self, widget_id: str = "Mini Varga", title: str = "Mini Varga",
                 varga: int = 9, **kwargs):
        self._varga_code = varga
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        content.setFixedSize(MINI_SIZE, MINI_SIZE)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Embedded scene + view + renderer
        self._mini_scene = QGraphicsScene()
        self._mini_view = QGraphicsView(self._mini_scene)
        self._mini_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self._mini_view.setStyleSheet("background: transparent;")

        self._mini_renderer = SouthIndianRenderer()
        self._mini_scene.addItem(self._mini_renderer)

        rect = QRectF(0, 0, MINI_SIZE, MINI_SIZE)
        self._mini_scene.setSceneRect(rect)
        self._mini_renderer.resize(rect)

        layout.addWidget(self._mini_view)
        return content

    def update_from_chart(self, chart) -> None:
        try:
            varga = chart.varga(self._varga_code)
            adapted = _VargaAdapter(varga, chart)
            self._mini_renderer.update_from_chart(adapted)
        except Exception:
            pass

    def set_theme(self, theme: dict) -> None:
        super().set_theme(theme)
        if theme:
            self._mini_renderer.set_theme(theme)
            self._mini_scene.setBackgroundBrush(QColor(theme["bg"]))
```

- [ ] **Step 2: Register in `gandiva/info_widgets/__init__.py`**

Add after the DashaWidget registration:

```python
from gandiva.info_widgets.mini_varga import MiniVargaWidget  # noqa: E402

INFO_WIDGETS["Mini Navamsha"] = (MiniVargaWidget, {"varga": 9})
INFO_WIDGETS["Mini Hora"] = (MiniVargaWidget, {"varga": -2})
```

- [ ] **Step 3: Verify import**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.info_widgets import INFO_WIDGETS; print(list(INFO_WIDGETS.keys()))"
```
Expected: `['Panchanga', 'Dasha Periods', 'Mini Navamsha', 'Mini Hora']`

- [ ] **Step 4: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel Widgets tab shows 4 checkboxes: Panchanga, Dasha Periods, Mini Navamsha, Mini Hora
- Checking "Mini Navamsha" adds a draggable widget showing D9 in South Indian grid format
- Planets appear in their navamsha sign cells
- Checking "Mini Hora" adds another widget showing D2
- Both mini vargas can be active simultaneously, auto-placed without overlap
- All mini varga widgets are draggable
- Recalculating updates the mini varga content
- Theme changes apply to mini varga widgets
- Mini vargas survive chart style switch (they always use South Indian renderer internally)
- Close button (hover X) removes widget and unchecks checkbox
- Multiple info widgets (Panchanga + Dasha + Mini Navamsha + Mini Hora) can all be active and tiled

- [ ] **Step 5: Commit**

```bash
git add gandiva/info_widgets/mini_varga.py gandiva/info_widgets/__init__.py
git commit -m "add MiniVargaWidget for divisional charts (Navamsha, Hora)"
```

---

## Phase 3 Complete — Test Checkpoint

After completing all 4 tasks:

1. Run the app: `python -m gandiva.app`
2. Full workflow verification:
   - Calculate a chart
   - **South Indian renderer:** Switch to "South Indian" via Display tab → verify grid, planet placement, ascendant mark, center info
   - **Aspect Lines overlay:** Switch back to "Western Wheel" → check "Aspect Lines" in left panel → verify colored lines between aspecting planets
   - **Rashi Aspects overlay:** Switch to "South Indian" → overlays clear → check "Rashi Aspects" → verify arrows between sign cells
   - **Change aspect mode:** Go to Calc Options → change Jaimini Aspects to "element" → recalculate → verify arrows update
   - **MiniVargaWidget:** Check "Mini Navamsha" and "Mini Hora" → verify small South Indian grids appear with correct divisional data
   - **Theme switching:** Change theme → verify all renderers, overlays, and info widgets update
   - **Multiple chart tabs:** Create second chart → all widgets update with new chart data → switch tabs → widgets switch data
   - **Drag and close:** Drag info widgets around → close via X → checkboxes uncheck
   - **Chart style switch:** While overlays and widgets are active, switch chart style → overlays clear, widgets persist

3. Verify no regressions:
   - Western Wheel still renders correctly
   - Panchanga and Dasha widgets still work
   - Right panel (chart input) still works
   - Left panel collapse/expand animation works

**What's in place after Phase 3:**
- Two chart styles: Western Wheel + South Indian grid
- Two overlay implementations: Aspect Lines (western) + Rashi Aspects (south indian)
- Four info widgets: Panchanga, Dasha Periods, Mini Navamsha, Mini Hora
- Aspect theme colors (aspect_hard, aspect_soft) in all 3 themes
- VargaAdapter pattern for feeding divisional data to renderers

**Future phases (not for now):**
- North Indian diamond renderer
- More vargas as info widgets (D3 Drekkana, D10 Dashamsha, etc.)
- Graha drishti (planetary aspect) overlay for South Indian grid
- Transit overlay (second chart data overlaid on natal)
