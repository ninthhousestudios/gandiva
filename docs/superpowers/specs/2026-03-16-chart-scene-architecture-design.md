# Chart Scene Architecture — Design Spec

**Date:** 2026-03-16
**Status:** Approved

## Overview

Migrate gandiva's chart display from a single `QWidget` (`ChartWheelWidget`) to a `QGraphicsScene`/`QGraphicsView` architecture. This enables:

1. **Multiple chart styles** — western wheel, south indian grid, north indian diamond, etc.
2. **Overlay system** — semi-transparent layers drawn over the chart (aspect lines, rashi aspects, etc.)
3. **Info widget system** — small draggable panels around the chart (mini vargas, panchanga, dasha periods)
4. **A left panel** — collapsible tab panel for toggling overlays and widgets on/off

All four are independent subsystems unified by the scene graph.

## Current State

### Files involved

- `gandiva/main_window.py` — MainWindow with horizontal QSplitter: `[ChartWheelWidget | ChartInputPanel]`
- `gandiva/widgets/chart_wheel.py` — `ChartWheelWidget(QWidget)`, ~800 lines, all painting in `paintEvent` via QPainter
- `gandiva/widgets/chart_input.py` — `ChartInputPanel(QWidget)`, collapsible right-side tab panel with 7 tabs
- `gandiva/themes.py` — theme dicts (Light, Forest, Cosmic)
- `gandiva/glyphs.py` — SVG path data for planet/sign glyphs
- `gandiva/glyph_renderer.py` — SVG glyph rendering with caching

### Current ChartWheelWidget architecture

`ChartWheelWidget` is a plain `QWidget` that paints concentric rings in `paintEvent`:
- Outer ring: zodiac sign names/glyphs
- Mid-outer ring: planet glyphs with force-directed collision resolution
- Inner ring: house numbers + cusps
- Center: Prometheus logo image
- Info overlay: top-left text showing chart name, date/time, location

Key methods:
- `update_from_chart(chart)` — extracts planet/cusp data, triggers repaint
- `_draw_skeleton(p, cx, cy, R)` — 12 radial lines, concentric circles
- `_draw_sign_names(p, cx, cy, R)` — arc text or Aditya glyphs in outer ring
- `_draw_planets(p, cx, cy, R)` — force-directed planet placement with collision resolution
- `_draw_house_ring(p, cx, cy, R)` — house numbers + cusp markers
- `_draw_center_image(p, cx, cy, R)` — circular-clipped center image

Mouse interaction: click to select planets (highlighted in gold), hover for tooltips showing full planet data.

Geometry constants:
```python
FRAC_SIGN = 0.12     # sign band width as fraction of radius
FRAC_PLANET = 0.445  # planet band width
FRAC_HOUSE = 0.10    # house/cusp band width
```

### How libaditya is used

All computation goes through libaditya. gandiva only does presentation.

```python
from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const

chart = Chart(context=context)
rashi = chart.rashi()
planets = rashi.planets()  # dict-like, keyed by name or number

# Per planet:
planet.longitude()          # formatted position string
planet.sign_name()          # "Aries", "Taurus", etc.
planet.nakshatra_name()     # "Kritika", etc.
planet.dignity()            # "EX", "MT", "OH", "GF", "F", "N", "E", "GE", "DB"
planet.longitude_speed()    # float, deg/day
planet.retrograde()         # bool
planet.ecliptic_longitude() # float, 0-360
planet.in_sign_longitude()  # formatted DD:MM:SS in sign
planet.latitude()           # float
planet.distance()           # float
planet.rise(), .set()       # rise/set times

# Zodiac modes (return new Chart, don't mutate):
chart.tropical()
chart.sidereal(ayanamsa=27)
chart.aditya()

# Divisional charts:
chart.varga(9)              # Navamsha — same .planets() interface

# Other data:
rashi.panchanga()           # Tithi, Nakshatra, Yoga, Karana, Vara
rashi.panchanga().vimshottari_dasha()  # Dasha periods
rashi.cusps()               # House cusps
```

---

## Architecture

### Scene Layer Stack

The central area becomes a `QGraphicsView` hosting a `QGraphicsScene`. Items are layered by z-value:

| Layer | Z-value | Contents |
|-------|---------|----------|
| Background | 0 | Theme-colored rect |
| Chart | 10 | One active `ChartRenderer` |
| Overlays | 50+ | Zero or more `ChartOverlay` items |
| Info Widgets | 100+ | Zero or more `InfoWidget` proxy items |

Info widgets can be dragged to any z-level (including under the chart). Click-to-raise brings a widget to the top of the widget stack.

### Scene Coordinate System

The scene uses a **1:1 pixel mapping** — no `fitInView`, no logical coordinate system. When the view resizes:

1. `ChartView.resizeEvent` gets the new viewport size
2. Calls `scene.resize_chart(QRectF(0, 0, viewport_width, viewport_height))`
3. `ChartScene.resize_chart()` does:
   - Sets the scene rect to match: `self.setSceneRect(rect)`
   - Calls `renderer.resize(rect)` on the active chart renderer
   - Calls `overlay.resize(rect)` on every active overlay (they share the chart's rect)
   - Does NOT reposition info widgets (they have user-set positions)

This mirrors how the current `ChartWheelWidget` works — `_geometry()` derives `cx, cy, r` from `self.width()` and `self.height()`. In the migrated renderer, `_geometry()` derives from `self.boundingRect()` instead:

```python
# Current (QWidget):
def _geometry(self):
    side = min(self.width(), self.height())
    cx, cy = self.width() / 2, self.height() / 2
    r = side / 2 - 18
    ...

# Migrated (QGraphicsItem):
def _geometry(self):
    rect = self.boundingRect()
    side = min(rect.width(), rect.height())
    cx, cy = rect.center().x(), rect.center().y()
    r = side / 2 - 18
    ...
```

### Theme Propagation

`ChartScene` holds the current theme name and propagates it to all items:

```python
class ChartScene(QGraphicsScene):
    def set_theme(self, name: str) -> None:
        self._theme_name = name
        self._theme = get_theme(name)
        clear_cache()  # SVG glyph color cache
        if self._renderer:
            self._renderer.set_theme(self._theme)
        for overlay in self._overlays.values():
            overlay.set_theme(self._theme)
        for widget in self._info_widgets.values():
            widget.set_theme(self._theme)
```

Each item base class has a `set_theme(theme_dict)` method that stores the theme and calls `self.update()`.

`MainWindow._apply_theme()` calls `scene.set_theme(name)` instead of `chart_wheel.set_theme(name)`.

### MainWindow Layout Change

The current layout extracts `ChartInputPanel.tab_bar` and places it outside the splitter so it remains visible when the panel collapses to 0 width. The new layout does the same for both panels:

**Current layout tree:**
```
root (QVBoxLayout)
├── chart_tab_bar (QTabBar)
└── content_row (QHBoxLayout)
    ├── splitter (QSplitter)
    │   ├── chart_wheel (ChartWheelWidget)
    │   └── input_panel (ChartInputPanel)
    └── right_tab_bar (input_panel.tab_bar)
```

**New layout tree:**
```
root (QVBoxLayout)
├── chart_tab_bar (QTabBar)
└── content_row (QHBoxLayout)
    ├── left_tab_bar (left_panel.tab_bar)
    ├── splitter (QSplitter)
    │   ├── left_panel (LeftPanel)
    │   ├── chart_view (ChartView)
    │   └── input_panel (ChartInputPanel)
    └── right_tab_bar (input_panel.tab_bar)
```

`MainWindow` is responsible for extracting both tab bars and placing them outside the splitter, same pattern already used for the right panel. `LeftPanel` exposes `self.tab_bar` the same way `ChartInputPanel` does.

---

## Component 1: Core Scene (`gandiva/scene/`)

### `ChartScene(QGraphicsScene)` — `gandiva/scene/chart_scene.py`

Responsibilities:
- Owns the layer stack (background, chart renderer, overlays, widgets)
- Holds reference to the current `Chart` object
- Propagates chart data to all items when chart changes
- Manages chart style switching: swaps renderer, clears all overlays, keeps info widgets
- Manages adding/removing overlays and widgets
- Emits signals when overlays/widgets are added or removed (for left panel sync)

Key interface:
```python
class ChartScene(QGraphicsScene):
    overlay_added = pyqtSignal(str)       # overlay_id
    overlay_removed = pyqtSignal(str)     # overlay_id
    widget_added = pyqtSignal(str)        # widget_id
    widget_removed = pyqtSignal(str)      # widget_id

    def set_chart(self, chart: Chart) -> None: ...
    def set_chart_style(self, style_name: str) -> None: ...
    def add_overlay(self, overlay_id: str) -> None: ...
    def remove_overlay(self, overlay_id: str) -> None: ...
    def add_info_widget(self, widget_id: str) -> None: ...
    def remove_info_widget(self, widget_id: str) -> None: ...
    def resize_chart(self, rect: QRectF) -> None: ...
```

### `ChartView(QGraphicsView)` — `gandiva/scene/chart_view.py`

Responsibilities:
- Hosts the `ChartScene`
- On resize: tells scene to resize the chart renderer (via `resize_chart`)
- Replaces `ChartWheelWidget` in MainWindow's splitter

```python
class ChartView(QGraphicsView):
    def __init__(self, scene: ChartScene): ...
    def resizeEvent(self, event): ...  # calls scene.resize_chart()
```

### File structure
```
gandiva/
  scene/
    __init__.py
    chart_scene.py       # ChartScene
    chart_view.py        # ChartView
```

---

## Component 2: Chart Renderers (`gandiva/renderers/`)

### `ChartRenderer(QGraphicsObject)` — `gandiva/renderers/base.py`

Abstract base class for all chart styles. Inherits `QGraphicsObject` (not plain `QGraphicsItem`) so it can emit signals — e.g., `planet_selected` for communicating selection state to the info panel.

```python
class ChartRenderer(QGraphicsObject):
    planet_selected = pyqtSignal(str)   # planet name, or "" for deselection

    def update_from_chart(self, chart: Chart) -> None: ...  # extract data, call update()
    def resize(self, rect: QRectF) -> None: ...             # store self._rect, call prepareGeometryChange() + update()
    def boundingRect(self) -> QRectF: ...                    # return self._rect
    def set_theme(self, theme: dict) -> None: ...            # store theme, call update()
    def paint(self, painter, option, widget) -> None: ...    # subclasses implement
```

Holds common state extracted from Chart:
- Planet data (positions, signs, nakshatras, dignities, speeds, retrograde flags)
- Cusp data
- Theme dict (set via `set_theme()`)
- Glyph renderer reference

### `WesternWheelRenderer(ChartRenderer)` — `gandiva/renderers/western_wheel.py`

Direct migration of `ChartWheelWidget`. Key changes from migration:

| Current (`QWidget`) | New (`QGraphicsItem`) |
|---|---|
| `paintEvent(event)` | `paint(painter, option, widget)` |
| `self.width()`, `self.height()` | `self.boundingRect()` |
| `QWidget.mousePressEvent` | `QGraphicsItem.mousePressEvent` |
| `QWidget.mouseMoveEvent` + `setMouseTracking` | `QGraphicsItem.hoverMoveEvent` + `setAcceptHoverEvents(True)` |
| `QToolTip.showText()` in mouse move | `QToolTip.showText()` in `hoverMoveEvent` |
| `self.update()` to trigger repaint | `self.update()` (same, works on QGraphicsItem too) |

The `_draw_*` methods transfer with minimal changes. Their actual signatures:

- `_draw_skeleton(self, p, cx, cy, r, r_sign, r_planet, r_house)` — 7 params
- `_draw_sign_names(self, p, cx, cy, r, r_sign)` — 5 params
- `_draw_planets(self, p, cx, cy, r_sign, r_planet)` — 5 params
- `_draw_house_ring(self, p, cx, cy, r_planet, r_house)` — 5 params
- `_draw_center_image(self, p, cx, cy, r_house)` — 4 params

All params are derived from `_geometry()`. The only change is that `_geometry()` reads from `self.boundingRect()` instead of `self.width()`/`self.height()` (see "Scene Coordinate System" section above).

### `SouthIndianRenderer(ChartRenderer)` — `gandiva/renderers/south_indian.py`

Built after western wheel migration. Square grid layout with 12 cells in the south indian arrangement. Same `update_from_chart` interface, completely different paint logic.

### Registry — `gandiva/renderers/__init__.py`

```python
CHART_STYLES = {
    "Western Wheel": WesternWheelRenderer,
    "South Indian": SouthIndianRenderer,
}
```

Display tab dropdown populates from `CHART_STYLES.keys()`. On selection change, `ChartInputPanel` emits:

```python
chart_style_changed = pyqtSignal(str)  # style name from CHART_STYLES
```

`MainWindow` connects this to `scene.set_chart_style(name)`.

### Chart style switching lifecycle

`ChartScene.set_chart_style(name)` does:
1. Remove old renderer from scene (and delete it)
2. Instantiate new renderer from `CHART_STYLES[name]`
3. Call `renderer.resize(current_rect)` with the current scene rect
4. Call `renderer.set_theme(self._theme)` with the current theme
5. If a chart is loaded, call `renderer.update_from_chart(self._chart)`
6. Add new renderer to scene at z=10
7. Remove all overlays from scene, emit `overlay_removed` for each
8. Info widgets are untouched
9. Mouse interaction state (selected planet) resets

### File structure
```
gandiva/
  renderers/
    __init__.py          # CHART_STYLES registry
    base.py              # ChartRenderer ABC
    western_wheel.py     # WesternWheelRenderer (migrated from chart_wheel.py)
    south_indian.py      # SouthIndianRenderer (new, built after migration)
```

---

## Component 3: Overlays (`gandiva/overlays/`)

### `ChartOverlay(QGraphicsObject)` — `gandiva/overlays/base.py`

Abstract base class for semi-transparent layers drawn over the chart. Uses `QGraphicsObject` for consistency with `ChartRenderer` (signal capability if needed).

```python
class ChartOverlay(QGraphicsObject):
    compatible_styles: set[str] = set()   # e.g., {"Western Wheel"}

    def update_from_chart(self, chart: Chart) -> None: ...
    def resize(self, rect: QRectF) -> None: ...  # matches chart renderer's rect
    def boundingRect(self) -> QRectF: ...
    def set_theme(self, theme: dict) -> None: ...
    def paint(self, painter, option, widget) -> None: ...
```

Not interactive by default — mouse events pass through to chart beneath. Individual overlays can opt in to interactivity if needed. Incompatible overlays (wrong chart style) still render — they just won't produce meaningful output. The user is free to enable whatever they want.

### Example overlays (built later)

- `AspectLinesOverlay` — draws aspect lines through center of western wheel. `compatible_styles = {"Western Wheel"}`
- `RashiAspectsOverlay` — draws rashi aspect arrows on south indian grid. `compatible_styles = {"South Indian"}`

### Registry — `gandiva/overlays/__init__.py`

```python
OVERLAYS = {
    "Aspect Lines": AspectLinesOverlay,
    "Rashi Aspects": RashiAspectsOverlay,
}
```

### Behavior

- Multiple overlays can stack (z=50, 51, 52, etc.)
- On chart style switch: all overlays removed from scene, checkboxes unchecked
- Left panel can show compatibility info but does not prevent incompatible selections

### File structure
```
gandiva/
  overlays/
    __init__.py          # OVERLAYS registry
    base.py              # ChartOverlay ABC
    aspect_lines.py      # AspectLinesOverlay (later)
    rashi_aspects.py     # RashiAspectsOverlay (later)
```

---

## Component 4: Info Widgets (`gandiva/info_widgets/`)

### `InfoWidget` — `gandiva/info_widgets/base.py`

Base class for draggable info panels. Uses `QGraphicsProxyWidget` to embed a regular QWidget in the scene.

**Chrome architecture**: `InfoWidget` builds a container QWidget that includes the title bar, close button, and content area. The container is set on the proxy via `self.setWidget(container)`. The chrome is part of the embedded QWidget, not painted on the proxy.

```python
class InfoWidget(QGraphicsProxyWidget):
    closed = pyqtSignal(str)  # emits widget_id when X clicked

    def __init__(self, widget_id: str, title: str):
        super().__init__()
        self._widget_id = widget_id
        # Build the container with chrome
        container = QWidget()
        layout = QVBoxLayout(container)
        # Title bar with label + close button (X visible on hover)
        title_bar = self._build_title_bar(title)
        layout.addWidget(title_bar)
        # Content from subclass
        layout.addWidget(self.build_content())
        self.setWidget(container)
        # Enable dragging and selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def update_from_chart(self, chart: Chart) -> None: ...  # subclasses override
    def build_content(self) -> QWidget: ...                  # subclasses implement
    def set_theme(self, theme: dict) -> None: ...            # update container stylesheet
```

### Auto-placement

When a widget is first added, `ChartScene` places it in available space:
- Candidate positions in order: top-left, top-right, bottom-left, bottom-right, then midpoints of edges
- "Available space" = outside the chart renderer's outermost drawn circle/rect (not the boundingRect, which fills the view)
- Pick the first position where the widget's bounding rect doesn't overlap existing info widgets
- If all candidates overlap, stack at bottom-right with a small offset
- User drags wherever they want after that

### Z-ordering

- Default z=100+ (above chart and overlays)
- Clicking a widget raises it to top of widget stack
- User can drag widgets to overlap the chart — they appear underneath if z < chart's z-value
- Possible future: "send to back" context menu action

### Concrete widgets

**`MiniVargaWidget`** — `gandiva/info_widgets/mini_varga.py`
- Renders a small chart for a specific divisional chart
- Reuses a `ChartRenderer` at small scale
- Constructor takes `varga: int` parameter (9 for navamsha, 2 for hora, etc.)

**`PanchangaWidget`** — `gandiva/info_widgets/panchanga.py`
- Compact display of tithi, nakshatra, yoga, karana, vara
- Data from `chart.rashi().panchanga()`

**`DashaWidget`** — `gandiva/info_widgets/dasha.py`
- Current dasha periods in a compact tree
- Data from `chart.rashi().panchanga().vimshottari_dasha()`

### Registry — `gandiva/info_widgets/__init__.py`

```python
INFO_WIDGETS = {
    "Mini Navamsha": (MiniVargaWidget, {"varga": 9}),
    "Mini Hora": (MiniVargaWidget, {"varga": 2}),
    "Panchanga": (PanchangaWidget, {}),
    "Dasha Periods": (DashaWidget, {}),
}
```

Tuple of `(class, kwargs)` so one widget class can appear multiple times with different config.

### File structure
```
gandiva/
  info_widgets/
    __init__.py          # INFO_WIDGETS registry
    base.py              # InfoWidget base
    mini_varga.py        # MiniVargaWidget
    panchanga.py         # PanchangaWidget
    dasha.py             # DashaWidget
```

---

## Component 5: Left Panel (`gandiva/widgets/left_panel.py`)

### `LeftPanel(QWidget)`

Mirrors `ChartInputPanel`'s collapsible tab behavior, positioned on the left side of the splitter.

- Same animation style: 220ms, InOutCubic easing
- Same collapse/expand on tab click
- Tab bar on the left edge, visible when collapsed
- Two tabs:

**Overlays tab:**
- List of checkboxes, one per entry in `OVERLAYS` registry
- Check → `ChartScene.add_overlay(id)`, uncheck → `ChartScene.remove_overlay(id)`
- On chart style switch: all checkboxes uncheck (scene clears overlays)
- Can show compatibility annotations (e.g., grayed text) but does not block selection

**Widgets tab:**
- List of checkboxes, one per entry in `INFO_WIDGETS` registry
- Check → `ChartScene.add_info_widget(id)`, uncheck → `ChartScene.remove_info_widget(id)`
- When widget closed via X button on the widget itself, checkbox unchecks (synced via `ChartScene.widget_removed` signal)
- Persists across chart style switches

### Two-way sync

Scene emits signals (`overlay_added`, `overlay_removed`, `widget_added`, `widget_removed`). Left panel connects to these and updates checkbox state. This keeps the panel and the scene in sync regardless of whether the action originated from the panel or from the widget/scene directly.

---

## Changes to Existing Files

### `gandiva/main_window.py`

- Import `ChartView`, `ChartScene`, `LeftPanel` instead of `ChartWheelWidget`
- Splitter becomes 3-way: `[LeftPanel | ChartView | ChartInputPanel]`
- `_display_chart()` calls `scene.set_chart(chart)` instead of `wheel.update_from_chart(chart)`
- Wire up chart style dropdown signal to `scene.set_chart_style()`

### `gandiva/widgets/chart_input.py`

- Add "Chart Style" dropdown to the Display tab, populated from `CHART_STYLES.keys()`
- Emit signal when chart style changes (MainWindow connects this to the scene)

### `gandiva/widgets/chart_wheel.py`

- Becomes the source for `WesternWheelRenderer` migration, then can be removed or kept as reference

### `gandiva/widgets/planet_table.py`

- Unchanged. Still populated by `MainWindow._display_chart()` → `input_panel.update_info(chart)`. Not affected by the scene migration.

### `gandiva/themes.py`

- No structural changes, but renderers/overlays/widgets all reference theme colors. Theme propagation now goes through `ChartScene.set_theme()` (see "Theme Propagation" section).

---

## Implementation Order

1. **Scene infrastructure** — `ChartScene`, `ChartView`, `ChartRenderer` base class
2. **Migrate western wheel** — `WesternWheelRenderer` from `ChartWheelWidget`
3. **Wire into MainWindow** — replace `ChartWheelWidget` with `ChartView`, verify identical output
4. **Chart style dropdown** — add to Display tab, wire to scene
5. **Left panel skeleton** — collapsible tabs, overlay/widget checklists (empty registries)
6. **Overlay base + wiring** — `ChartOverlay` base, scene add/remove, left panel sync
7. **Info widget base + wiring** — `InfoWidget` base with chrome/dragging, scene placement, left panel sync
8. **First info widgets** — `PanchangaWidget`, `DashaWidget` (pure data display, no renderer dependency)
9. **MiniVargaWidget** — reuses renderer at small scale
10. **South Indian renderer** — second chart style
11. **First overlays** — `AspectLinesOverlay` for western, `RashiAspectsOverlay` for south indian

Steps 1-3 are the critical migration. After step 3, the app should look and behave identically to today. Steps 4-7 build the framework. Steps 8-11 populate it with content.

---

## Final File Structure

```
gandiva/
  app.py
  main_window.py              # Updated: 3-way splitter
  themes.py
  glyphs.py
  glyph_renderer.py
  scene/
    __init__.py
    chart_scene.py             # ChartScene(QGraphicsScene)
    chart_view.py              # ChartView(QGraphicsView)
  renderers/
    __init__.py                # CHART_STYLES registry
    base.py                    # ChartRenderer(QGraphicsObject) ABC
    western_wheel.py           # WesternWheelRenderer — migrated from chart_wheel.py
    south_indian.py            # SouthIndianRenderer
  overlays/
    __init__.py                # OVERLAYS registry
    base.py                    # ChartOverlay(QGraphicsObject) ABC
    aspect_lines.py            # AspectLinesOverlay
    rashi_aspects.py           # RashiAspectsOverlay
  info_widgets/
    __init__.py                # INFO_WIDGETS registry
    base.py                    # InfoWidget(QGraphicsProxyWidget) base
    mini_varga.py              # MiniVargaWidget
    panchanga.py               # PanchangaWidget
    dasha.py                   # DashaWidget
  widgets/
    chart_input.py             # Updated: chart style dropdown on Display tab
    left_panel.py              # New: overlay/widget toggle panel
    planet_table.py            # Unchanged
    chart_wheel.py             # Deprecated after migration (keep as reference or remove)
```
