# Renderer Migration — Phase 1: Scene Infrastructure + Western Wheel Migration

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `ChartWheelWidget` (plain QWidget) with a `QGraphicsScene`/`QGraphicsView` architecture, migrating the existing western wheel rendering so the app looks and behaves identically afterward.

**Architecture:** A `ChartScene` (QGraphicsScene) hosts a `ChartView` (QGraphicsView). Chart renderers are `QGraphicsObject` subclasses that paint via QPainter, same as before. The western wheel's existing `_draw_*` methods transfer nearly unchanged — only the geometry source and mouse event API change.

**Tech Stack:** Python 3, PyQt6 (QGraphicsScene, QGraphicsView, QGraphicsObject), libaditya

**Branch:** `renderer-migration` (create from current `master`)

**Spec:** `docs/superpowers/specs/2026-03-16-chart-scene-architecture-design.md`

---

## Chunk 1: Scene Infrastructure + Renderer Base

### Task 1: Create the branch

**Files:**
- None (git only)

- [ ] **Step 1: Create and switch to the new branch**

```bash
cd /home/josh/w/astro/soft/gandiva
git checkout -b renderer-migration
```

- [ ] **Step 2: Verify branch**

Run: `git branch --show-current`
Expected: `renderer-migration`

---

### Task 2: Create `ChartRenderer` base class

**Files:**
- Create: `gandiva/renderers/__init__.py`
- Create: `gandiva/renderers/base.py`

- [ ] **Step 1: Create the renderers package**

Create `gandiva/renderers/__init__.py`:
```python
"""Chart renderer registry."""

# Populated after renderer classes are defined to avoid circular imports.
# Import this dict to get {name: renderer_class} mappings.
CHART_STYLES: dict[str, type] = {}
```

- [ ] **Step 2: Create the base class**

Create `gandiva/renderers/base.py`:

```python
"""Abstract base class for chart renderers."""

import math

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtWidgets import QGraphicsObject


class ChartRenderer(QGraphicsObject):
    """Base class for all chart style renderers.

    Subclasses must implement:
        - paint(painter, option, widget)
        - update_from_chart(chart)
    """

    planet_selected = pyqtSignal(str)  # planet name, or "" for deselection

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rect = QRectF()
        self._theme = None
        self._chart = None

    def boundingRect(self) -> QRectF:
        return self._rect

    def resize(self, rect: QRectF) -> None:
        """Called by ChartScene when the view resizes."""
        self.prepareGeometryChange()
        self._rect = rect
        self.update()

    def set_theme(self, theme: dict) -> None:
        """Store theme dict and trigger repaint."""
        self._theme = theme
        self.update()

    def update_from_chart(self, chart) -> None:
        """Extract data from chart and trigger repaint. Subclasses must override."""
        self._chart = chart
        self.update()

    def paint(self, painter, option, widget=None) -> None:
        """Subclasses must implement."""
        raise NotImplementedError
```

- [ ] **Step 3: Verify import**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.renderers.base import ChartRenderer; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add gandiva/renderers/
git commit -m "add ChartRenderer base class (QGraphicsObject)"
```

---

### Task 3: Create `ChartScene`

**Files:**
- Create: `gandiva/scene/__init__.py`
- Create: `gandiva/scene/chart_scene.py`

- [ ] **Step 1: Create the scene package**

Create `gandiva/scene/__init__.py`:
```python
"""Scene infrastructure for the chart display area."""
```

- [ ] **Step 2: Create ChartScene**

Create `gandiva/scene/chart_scene.py`:

```python
"""QGraphicsScene subclass that manages chart renderer, overlays, and info widgets."""

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsScene

from gandiva.glyph_renderer import clear_cache
from gandiva.renderers import CHART_STYLES
from gandiva.themes import get_theme, DEFAULT_THEME


class ChartScene(QGraphicsScene):
    """Manages the layered scene: background, chart renderer, overlays, info widgets."""

    overlay_added = pyqtSignal(str)
    overlay_removed = pyqtSignal(str)
    widget_added = pyqtSignal(str)
    widget_removed = pyqtSignal(str)

    # Z-value constants
    Z_CHART = 10
    Z_OVERLAY_BASE = 50
    Z_WIDGET_BASE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = None
        self._chart = None
        self._theme = get_theme(DEFAULT_THEME)
        self._rect = QRectF()
        self._overlays: dict[str, object] = {}
        self._info_widgets: dict[str, object] = {}
        self.setBackgroundBrush(QColor(self._theme["bg"]))

    def set_theme(self, name: str) -> None:
        """Propagate theme to all scene items."""
        self._theme = get_theme(name)
        clear_cache()
        self.setBackgroundBrush(QColor(self._theme["bg"]))
        if self._renderer:
            self._renderer.set_theme(self._theme)
        for overlay in self._overlays.values():
            overlay.set_theme(self._theme)
        for widget in self._info_widgets.values():
            widget.set_theme(self._theme)

    def set_chart(self, chart) -> None:
        """Pass chart data to renderer and all scene items."""
        self._chart = chart
        if self._renderer:
            self._renderer.update_from_chart(chart)
        for overlay in self._overlays.values():
            overlay.update_from_chart(chart)
        for widget in self._info_widgets.values():
            widget.update_from_chart(chart)

    def set_chart_style(self, style_name: str) -> None:
        """Switch to a different chart renderer. Clears all overlays, keeps info widgets."""
        renderer_class = CHART_STYLES.get(style_name)
        if renderer_class is None:
            return

        # Remove old renderer
        if self._renderer:
            self.removeItem(self._renderer)
            self._renderer = None

        # Instantiate new renderer
        self._renderer = renderer_class()
        self._renderer.setZValue(self.Z_CHART)
        self.addItem(self._renderer)

        # Initialize with current state
        if self._rect.isValid():
            self._renderer.resize(self._rect)
        self._renderer.set_theme(self._theme)
        if self._chart:
            self._renderer.update_from_chart(self._chart)

        # Clear all overlays
        for overlay_id in list(self._overlays.keys()):
            self.remove_overlay(overlay_id)

    def resize_chart(self, rect: QRectF) -> None:
        """Called by ChartView on resize. Propagates to renderer and overlays."""
        self._rect = rect
        self.setSceneRect(rect)
        if self._renderer:
            self._renderer.resize(rect)
        for overlay in self._overlays.values():
            overlay.resize(rect)

    # ── overlay management ─────────────────────────────────────────────────

    def add_overlay(self, overlay_id: str) -> None:
        """Add an overlay by its registry ID."""
        # Placeholder for Phase 2 — overlays not yet implemented
        pass

    def remove_overlay(self, overlay_id: str) -> None:
        """Remove an overlay by its registry ID."""
        if overlay_id in self._overlays:
            self.removeItem(self._overlays.pop(overlay_id))
            self.overlay_removed.emit(overlay_id)

    # ── info widget management ──────────────────────────────────────────────

    def add_info_widget(self, widget_id: str) -> None:
        """Add an info widget by its registry ID."""
        # Placeholder for Phase 2 — info widgets not yet implemented
        pass

    def remove_info_widget(self, widget_id: str) -> None:
        """Remove an info widget by its registry ID."""
        if widget_id in self._info_widgets:
            self.removeItem(self._info_widgets.pop(widget_id))
            self.widget_removed.emit(widget_id)
```

- [ ] **Step 3: Verify import**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.scene.chart_scene import ChartScene; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add gandiva/scene/
git commit -m "add ChartScene with renderer/overlay/widget management"
```

---

### Task 4: Create `ChartView`

**Files:**
- Create: `gandiva/scene/chart_view.py`

- [ ] **Step 1: Create ChartView**

Create `gandiva/scene/chart_view.py`:

```python
"""QGraphicsView subclass that hosts the ChartScene."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsView, QFrame

from gandiva.scene.chart_scene import ChartScene


class ChartView(QGraphicsView):
    """View that hosts the chart scene. Handles resize propagation."""

    def __init__(self, scene: ChartScene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport().rect()
        rect = QRectF(0, 0, vp.width(), vp.height())
        self._scene.resize_chart(rect)
```

- [ ] **Step 2: Verify import**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.scene.chart_view import ChartView; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add gandiva/scene/chart_view.py
git commit -m "add ChartView (QGraphicsView wrapper)"
```

---

## Chunk 2: Migrate Western Wheel Renderer

### Task 5: Create `WesternWheelRenderer`

This is the largest task — migrating the painting code from `ChartWheelWidget` to a `QGraphicsObject`.

**Files:**
- Create: `gandiva/renderers/western_wheel.py`
- Modify: `gandiva/renderers/__init__.py`

**Source reference:** `gandiva/widgets/chart_wheel.py` — the entire file is the migration source.

- [ ] **Step 1a: Create file with imports, constants, and class skeleton**

Create `gandiva/renderers/western_wheel.py`. This is a mechanical migration of `ChartWheelWidget`. Copy all module-level constants and functions directly into this new file (do NOT import them from chart_wheel.py — that file is kept as reference only, not as a live dependency).

Here are the specific changes from the original:

**Class definition:**
```python
# old:
class ChartWheelWidget(QWidget):
# new:
class WesternWheelRenderer(ChartRenderer):
```

**Imports — replace QWidget imports with QGraphicsObject ones:**
```python
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
```

**Keep these module-level constants unchanged (copy from chart_wheel.py):**
- `CENTER_IMAGE`, `_fmt_lon()`, `ZODIAC_NAMES`, `ROMAN`, `SKIP_PLANETS`, `HIT_RADIUS`
- `FRAC_SIGN`, `FRAC_PLANET`, `FRAC_HOUSE`

**`__init__` changes:**
```python
# old:
def __init__(self):
    super().__init__()
    self.setMinimumSize(420, 420)
    self.setMouseTracking(True)
    self.chart            = None
    self.asc_deg          = 0.0
    self.wheel_ref_deg    = 15.0
    self.is_aditya        = True
    self.planet_positions = []
    self.selected_planet  = None
    self._center_pixmap   = QPixmap(CENTER_IMAGE)
    self.theme            = get_theme(DEFAULT_THEME)
    self.cusp_positions   = []
    # info_label stuff...

# new:
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
    # NOTE: self._chart and self._theme are set by the base class
    # NOTE: info_label is NOT migrated here — it will become an info widget later.
    #       For now, skip the info overlay (chart name/date/location text in top-left).
    #       The same info is shown in the right panel's Chart Info tab.
```

**`set_theme` changes:**
```python
# old:
def set_theme(self, name: str):
    self.theme = get_theme(name)
    clear_cache()
    self._apply_info_label_style()
    self.update()

# new: use base class set_theme(theme_dict) — no name lookup, no info label
# The base class already stores self._theme and calls self.update().
# Override only if extra work is needed:
def set_theme(self, theme: dict) -> None:
    super().set_theme(theme)
    # clear_cache() is called by ChartScene.set_theme(), not here
```

**`update_from_chart` changes:**
```python
# old:
def update_from_chart(self, chart):
    self.chart     = chart
    self.asc_deg   = chart.rashi().cusps()[1].ecliptic_longitude()
    self.is_aditya = chart.context.circle == Circle.ADITYA
    asc_sign_idx       = int(self.asc_deg / 30)
    self.wheel_ref_deg = asc_sign_idx * 30.0 + 15.0
    self.selected_planet = None
    self._update_info_overlay(chart)
    self.update()

# new:
def update_from_chart(self, chart) -> None:
    self.asc_deg   = chart.rashi().cusps()[1].ecliptic_longitude()
    self.is_aditya = chart.context.circle == Circle.ADITYA
    asc_sign_idx       = int(self.asc_deg / 30)
    self.wheel_ref_deg = asc_sign_idx * 30.0 + 15.0
    self.selected_planet = None
    super().update_from_chart(chart)  # stores self._chart, calls self.update()
    # NOTE: _update_info_overlay removed — will be a separate info widget
```

**`_geometry` changes:**
```python
# old:
def _geometry(self):
    side = min(self.width(), self.height())
    cx, cy = self.width() / 2, self.height() / 2
    r        = side / 2 - 18
    ...

# new:
def _geometry(self):
    rect = self.boundingRect()
    side = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    r        = side / 2 - 18
    r_sign   = r       - r * FRAC_SIGN
    r_planet = r_sign  - r * FRAC_PLANET
    r_house  = r_planet - r * FRAC_HOUSE
    return cx, cy, r, r_sign, r_planet, r_house
```

**`paintEvent` → `paint`:**
```python
# old:
def paintEvent(self, event):
    p = QPainter(self)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(self.rect(), self.theme["bg"])
    if self.chart is None:
        p.end()
        return
    cx, cy, r, r_sign, r_planet, r_house = self._geometry()
    self.cusp_positions = []
    self._draw_skeleton(p, cx, cy, r, r_sign, r_planet, r_house)
    self._draw_sign_names(p, cx, cy, r, r_sign)
    self._draw_planets(p, cx, cy, r_sign, r_planet)
    self._draw_house_ring(p, cx, cy, r_planet, r_house)
    self._draw_center_image(p, cx, cy, r_house)
    p.end()

# new:
def paint(self, painter, option, widget=None):
    if self._chart is None or not self._rect.isValid():
        return
    # Background is handled by the scene (setBackgroundBrush), not the renderer.
    # But we still draw the outer circle fill:
    p = painter
    cx, cy, r, r_sign, r_planet, r_house = self._geometry()
    self.cusp_positions = []
    self._draw_skeleton(p, cx, cy, r, r_sign, r_planet, r_house)
    self._draw_sign_names(p, cx, cy, r, r_sign)
    self._draw_planets(p, cx, cy, r_sign, r_planet)
    self._draw_house_ring(p, cx, cy, r_planet, r_house)
    self._draw_center_image(p, cx, cy, r_house)
    # Do NOT call p.end() — the scene manages the painter lifecycle
```

- [ ] **Step 1b: Copy all `_draw_*` methods**

Copy all five drawing methods unchanged from `chart_wheel.py`.
Replace any reference to `self.theme` with `self._theme` and `self.chart` with `self._chart`. These are the specific occurrences:

- `self.theme[...]` → `self._theme[...]` (in `_draw_skeleton`, `_draw_sign_names`, `_draw_planets`, `_draw_house_ring`, `_draw_center_image`)
- `self.chart.rashi()` → `self._chart.rashi()` (in `_draw_planets`, `_draw_house_ring`)
- `self.chart.context.print_outer_planets` → `self._chart.context.print_outer_planets` (in `_draw_planets`)

- [ ] **Step 1c: Copy helper methods and add mouse event handlers**

Copy these helper methods unchanged (just update `self.theme` → `self._theme`):
- `_ecl_to_angle(self, ecl_deg)`
- `_polar(self, cx, cy, r, ecl_deg)`
- `_tangent_rotation(self, ecl_deg)`
- `_draw_arc_text(self, p, cx, cy, r_arc, ecl_center, text, font)`
- `_angle_to_ecl(self, screen_angle_deg)`
- `_planet_at(self, pos)` — unchanged
- `_cusp_at(self, pos)` — unchanged

**NOTE:** `_spread` (line 480 of chart_wheel.py) is dead code — it is defined but never called. The force-directed collision resolution in `_draw_planets` replaced it. **Do NOT copy it** to the new file.

Then add the mouse event handlers (migrated API):

**Mouse event migration:**
```python
# old:
def mousePressEvent(self, event):
    hit = self._planet_at(event.position())
    self.selected_planet = hit[0] if hit else None
    self.update()

def mouseMoveEvent(self, event):
    planet_hit = self._planet_at(event.position())
    cusp_tip   = self._cusp_at(event.position())
    gpos       = event.globalPosition().toPoint()
    ...

# new:
def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
    hit = self._planet_at(event.pos())
    name = hit[0] if hit else None
    self.selected_planet = name
    self.planet_selected.emit(name or "")
    self.update()
    super().mousePressEvent(event)  # preserve scene-level event dispatch

def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
    planet_hit = self._planet_at(event.pos())
    cusp_tip   = self._cusp_at(event.pos())
    gpos       = event.screenPos()
    if planet_hit:
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # NOTE: no `self` arg — QGraphicsObject is not a QWidget
        QToolTip.showText(gpos, planet_hit[1])
    elif cusp_tip:
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        QToolTip.showText(gpos, cusp_tip)
    else:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        QToolTip.hideText()
    super().hoverMoveEvent(event)
```

Note: `event.position()` (QWidget) → `event.pos()` (QGraphicsSceneMouseEvent/HoverEvent). `event.globalPosition().toPoint()` → `event.screenPos()`.

**Do NOT migrate:** `_update_info_overlay`, `_apply_info_label_style`, `info_label` — these will become a separate info widget in Phase 2. The chart info is still visible in the right panel's Chart Info tab and Planets tab, so nothing is lost.

**Do NOT migrate:** `resizeEvent` — resize is handled by `ChartRenderer.resize()` called from `ChartScene`.

- [ ] **Step 2: Register the renderer**

Modify `gandiva/renderers/__init__.py` — append after the `CHART_STYLES` dict:

```python
from gandiva.renderers.western_wheel import WesternWheelRenderer

CHART_STYLES["Western Wheel"] = WesternWheelRenderer
```

- [ ] **Step 3: Verify import**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.renderers import CHART_STYLES; print(list(CHART_STYLES.keys()))"`
Expected: `['Western Wheel']`

- [ ] **Step 4: Commit**

```bash
git add gandiva/renderers/
git commit -m "migrate western wheel to WesternWheelRenderer (QGraphicsObject)"
```

---

## Chunk 3: Wire Into MainWindow

### Task 6: Replace `ChartWheelWidget` with `ChartView` in MainWindow

**Files:**
- Modify: `gandiva/main_window.py`

**Current state of `main_window.py`:** see `gandiva/main_window.py` (166 lines). The key sections to change are marked below.

- [ ] **Step 1: Update imports**

In `gandiva/main_window.py`, change the imports:

```python
# old:
from gandiva.widgets.chart_wheel import ChartWheelWidget

# new:
from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView
from gandiva.renderers import CHART_STYLES
```

- [ ] **Step 2: Replace widget creation in `__init__`**

Replace the chart wheel creation section (around line 48-49):

```python
# old:
        # ── center: chart wheel ───────────────────────────────────────────────
        self.chart_wheel = ChartWheelWidget()

# new:
        # ── center: chart scene + view ───────────────────────────────────────
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        # Set initial chart style (Western Wheel is the default/only one for now)
        self.chart_scene.set_chart_style("Western Wheel")
```

- [ ] **Step 3: Update splitter wiring**

Replace splitter references (around lines 51-57):

```python
# old:
        self.splitter.addWidget(self.chart_wheel)
        self.splitter.addWidget(self.input_panel)
        ...
        self.input_panel.splitter = self.splitter

# new:
        self.splitter.addWidget(self.chart_view)
        self.splitter.addWidget(self.input_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.input_panel.splitter = self.splitter
```

- [ ] **Step 4: Update `_display_chart`**

```python
# old:
    def _display_chart(self, chart):
        self.chart_wheel.update_from_chart(chart)
        self.input_panel.update_info(chart)

# new:
    def _display_chart(self, chart):
        self.chart_scene.set_chart(chart)
        self.input_panel.update_info(chart)
```

- [ ] **Step 5: Update `_apply_theme`**

```python
# old:
    def _apply_theme(self, name: str):
        QSettings("gandiva", "gandiva").setValue("theme", name)
        theme = get_theme(name)
        QApplication.instance().setStyleSheet(make_app_stylesheet(theme))
        self.chart_wheel.set_theme(name)

# new:
    def _apply_theme(self, name: str):
        QSettings("gandiva", "gandiva").setValue("theme", name)
        theme = get_theme(name)
        QApplication.instance().setStyleSheet(make_app_stylesheet(theme))
        self.chart_scene.set_theme(name)
```

- [ ] **Step 6: Smoke test**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

**Verify:**
- Window opens without errors
- Chart wheel renders with planets, signs, houses, cusps
- Hover tooltips work on planets and cusps
- Click to select a planet (gold highlight)
- Theme switching works (Light/Forest/Cosmic via Display tab)
- Resize window — chart scales correctly
- Collapse/expand the right panel — chart resizes to fill space
- Calculate button works — chart updates
- Multiple charts (change name/date, calculate) — tab bar appears, switching works
- The ONLY expected difference: the info overlay text in the top-left corner is gone (chart name, date, location). This info is still visible in the right panel's Chart Info tab.

- [ ] **Step 7: Commit**

```bash
git add gandiva/main_window.py
git commit -m "wire ChartView/ChartScene into MainWindow, replacing ChartWheelWidget"
```

---

### Task 7: Clean up — keep old file as reference

**Files:**
- None changed, just a note

- [ ] **Step 1: Do NOT delete `chart_wheel.py` yet**

Keep `gandiva/widgets/chart_wheel.py` as a reference. It's still importable but no longer used by `main_window.py`. It can be removed in a later phase once the migration is fully validated.

Verify it's no longer imported:

Run: `cd /home/josh/w/astro/soft/gandiva && grep -r "chart_wheel" gandiva/ --include="*.py" | grep -v "widgets/chart_wheel.py" | grep -v "renderers/" | grep -v "__pycache__"`

Expected: no output. If `main_window.py` still references it, go back and fix Step 1 of Task 6.

---

## Phase 1 Complete — Test Checkpoint

After completing all tasks above:

1. Run the app: `python -m gandiva.app`
2. Compare side-by-side with the `master` branch (switch branches or run from a separate checkout)
3. Everything should look and behave identically except the missing info overlay text in the top-left corner
4. If satisfied, the branch is ready for Phase 2

**What's in place after Phase 1:**
- `gandiva/scene/chart_scene.py` — ChartScene with renderer management, overlay/widget stubs
- `gandiva/scene/chart_view.py` — ChartView with resize propagation
- `gandiva/renderers/base.py` — ChartRenderer base class
- `gandiva/renderers/western_wheel.py` — migrated western wheel
- `gandiva/main_window.py` — updated to use ChartView/ChartScene

**What's NOT done yet (Phase 2+):**
- Chart style dropdown on Display tab
- Left panel (overlay/widget toggle)
- Overlay system
- Info widget system
- South Indian renderer
- Info overlay text (moved to info widget later)
