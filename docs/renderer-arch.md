# Gandiva Renderer Architecture

## Overview

Gandiva has a cleanly layered renderer architecture: renderers are `QGraphicsObject` subclasses that know nothing about the scene or application layer. Data flows in via libaditya `Chart` objects (not dicts), themes are injected as plain dicts, and a registry allows runtime style switching.

**Total renderer code:** ~1,450 LOC (base + two renderers + glyph system + scene + view).

| File | LOC | Role |
|------|-----|------|
| `renderers/__init__.py` | 13 | Style registry |
| `renderers/base.py` | 44 | Abstract base class |
| `renderers/south_indian.py` | 401 | South Indian grid |
| `renderers/western_wheel.py` | 489 | Western wheel |
| `scene/chart_scene.py` | 339 | Scene orchestrator (renderer + overlays + widgets) |
| `scene/chart_view.py` | 82 | QGraphicsView host |
| `glyph_renderer.py` | 87 | SVG glyph rasterizer with cache |
| `glyphs.py` | 230 | Raw SVG path data (AstroChart, MIT) |
| `themes.py` | 335 | 3 themes + Qt stylesheet generator |

## Class Hierarchy

```
QGraphicsObject
└── ChartRenderer              (base.py — owns rect, theme dict, chart ref)
    ├── WesternWheelRenderer   (western_wheel.py)
    └── SouthIndianRenderer    (south_indian.py)

QGraphicsScene
└── ChartScene                 (scene orchestrator)

QGraphicsView
└── ChartView                  (thin host, wheel-event workaround for proxy widgets)
```

Renderers are first-class scene items — the scene does not paint, the renderer item does via Qt `paint()` events.

## Renderer Registry

```python
CHART_STYLES = {
    "Western Wheel": WesternWheelRenderer,
    "South Indian":  SouthIndianRenderer,
}
```

Manual registration. New renderers must be imported and inserted here. Functional but brittle — forgetting to add a new renderer means it silently never appears in the UI.

## Base Class Contract (`ChartRenderer`, 44 LOC)

| Method | Behavior |
|--------|----------|
| `resize(rect)` | Stores rect, calls `prepareGeometryChange()` |
| `set_theme(theme)` | Stores dict, calls `update()` |
| `update_from_chart(chart)` | Stores chart, calls `update()`. Subclasses override to extract data first. |
| `paint(painter, option, widget)` | `raise NotImplementedError` (should be `@abstractmethod`) |
| `boundingRect()` | Returns stored `_rect` |

**Signal:** `planet_selected = pyqtSignal(str)` — emits planet name on click, `""` on deselection. Only outbound signal from renderers.

## Data Flow

```
libaditya Chart
      │
      ▼
ChartScene.set_chart(chart)
      │
      ├── renderer.update_from_chart(chart)
      ├── overlay.update_from_chart(chart)  (for each overlay)
      └── widget.set_chart(chart)           (for each info widget)
```

Renderers consume libaditya objects directly — no bridge dict, no string-keyed lookups.

### libaditya API Surface Used

| Access | Used By |
|--------|---------|
| `chart.context.circle` (Circle.ADITYA check) | Both |
| `chart.context.print_outer_planets` | Both |
| `chart.rashi()` → rashi object | Both |
| `rashi.planets()` → `dict[str, Planet]` | Both |
| `rashi.cusps()` → `dict[int, Cusp]` | Both |
| `planet.ecliptic_longitude()` | Both |
| `planet.retrograde()` | Both |
| `planet.dignity()` | Both |
| `planet.sign_name()` | Both |
| `planet.is_outer_planet()` | Both |
| `planet.amsha()`, `planet.deity()` | Both |
| `planet.longitude()` (formatted) | Both |
| `planet.nakshatra_name()` | Western only |
| `planet.rise()`, `planet.set()` | Western only |
| `cusp.ecliptic_longitude()` | Both |
| `cusp.sign_name()`, `cusp.longitude()` | Both |

## WesternWheelRenderer (489 LOC)

**Geometry:** Four concentric annular bands (sign ring 12%, planet band 44.5%, house ring 10%, center image ~33.5% of radius). All geometry computed from `_geometry()` → `(cx, cy, r, r_sign, r_planet, r_house)`.

**Paint pipeline:**
1. `_draw_skeleton` — background circle, 12 spoke lines, ring circles
2. `_draw_sign_names` — arc text (Aditya) or sign glyphs (tropical/sidereal)
3. `_draw_planets` — reads planets from chart, runs force-directed collision resolver, draws glyphs + indicator lines
4. `_draw_house_ring` — whole-sign house numbers + cusp roman numerals at true ecliptic degrees
5. `_draw_center_image` — clipped circular pixmap

**Force-directed collision resolver** (~70 LOC, lines 288-360):
- Up to 200 iterations, O(n^2) pair scan per iteration
- Push apart overlapping glyphs, radial spring toward midline, angular spring toward true position
- Hard clamp to stay within own sign sector
- Runs on every `paint()` call (not cached between repaints)
- Reads planet data directly from libaditya objects during paint (no pre-extraction)

**Ecliptic-to-screen:** Ascendant sign midpoint at 9 o'clock (pi radians). `_ecl_to_angle(ecl_deg)` = `radians(180 + (ecl_deg - wheel_ref_deg))`.

## SouthIndianRenderer (401 LOC)

**Layout:** Fixed 4x4 grid, 12 outer cells (Pisces top-left, always), 2x2 center hole (erased by overdrawing with background color).

**Data extraction phase** (unlike Western, which reads during paint):
- `_extract_sign_data(chart)` — groups planets by sign into `self._sign_data`
- `_extract_cusp_data(chart)` — maps sign → (cusp_num, tooltip)

**Paint pipeline:**
1. `_draw_grid` — background, border, grid lines, center erase
2. `_draw_sign_labels` — Aditya text labels or sign glyphs, alignment flips by column
3. `_draw_cusp_numerals` — roman numerals, angular cusps drawn heavier (pen 1.6 vs 1.0)
4. `_draw_planets_in_cells` — simple row/column grid within each cell, wraps to next row, truncates at cell bottom (silent overflow)
5. `_draw_center_image` — same clipped circle pattern as Western

**Planet layout:** No collision detection. Simple grid within available cell height. Planets beyond available space are silently dropped.

## Interaction Model

Both renderers follow the same pattern:

| Action | Behavior |
|--------|----------|
| Hover | Linear scan of hit lists, `HIT_RADIUS = 18` px, tooltip on hit |
| Left click | Select planet (emits `planet_selected`), click empty to deselect |
| No drag, double-click, or right-click handling | |

**Hover optimization gap:** WesternWheelRenderer has tooltip dedup (`_active_tip` guard). SouthIndianRenderer calls `QToolTip.showText` on every `hoverMoveEvent` — may cause flicker.

Hit detection uses positions from the previous paint call (one-frame lag on resize — negligible in practice).

## Theme System (`themes.py`, 335 LOC)

Three themes: `LIGHT`, `FOREST`, `COSMIC` (default). Each is a `dict[str, QColor]` with ~20 keys:

**Chart keys:** `bg`, `bg_inner`, `bg_ring`, `fire`, `earth`, `air`, `water`, `line`, `line_light`, `line_angular`, `ring_border`, `glyph`, `glyph_retro`, `glyph_selected`, `sign_label`, `cusp_label`, `house_label`, `aspect_hard`, `aspect_soft`

**UI chrome keys:** `ui_bg`, `ui_text`, `ui_border`, `ui_accent`, `ui_button_bg`, `ui_input_bg`

Renderers currently use only: `bg`, `line`, `line_light`, `line_angular`, `glyph`, `glyph_retro`, `glyph_selected`, `sign_label`, `cusp_label`, `house_label`.

Unused theme keys available for future renderers: `bg_inner`, `bg_ring`, `fire`, `earth`, `air`, `water`, `ring_border`, `aspect_hard`, `aspect_soft`.

`make_app_stylesheet(theme)` generates a full Qt stylesheet for all standard widget classes.

## Glyph System

**`glyphs.py`** (230 LOC): Dict-based glyph definitions with SVG path data (AstroChart, MIT). 14 planet + 12 sign glyphs, each with `shift` and `paths` fields.

**`glyph_renderer.py`** (87 LOC): Wraps path fragments into minimal SVG (100x100 viewBox), creates `QSvgRenderer`, caches by `(glyph_id, color_hex, stroke_width)`. `clear_cache()` called on theme change.

## ChartScene Orchestrator (339 LOC)

Manages three Z-layers:

| Layer | Z | Contents |
|-------|---|----------|
| Chart | 10 | Single renderer instance |
| Overlays | 50+ | Aspect lines, transit markers, etc. |
| Info widgets | 100+ | Docked panels (planet info, dasha, etc.) |

**Key methods:**
- `set_chart(chart)` — fans out to renderer + overlays + widgets
- `set_theme(name)` — fans out + clears glyph cache
- `set_chart_style(name)` — swaps renderer, clears overlays, keeps widgets
- `add_info_widget(widget_cls)` — greedy placement (8 candidate positions), stacking fallback
- `get_widget_states()` / `restore_widget_states()` — persistence via attribute introspection

## Dependency Graph

```
renderers/
├── base.py            ← (no gandiva imports)
├── south_indian.py    ← glyphs, glyph_renderer, base, assets, libaditya
├── western_wheel.py   ← glyphs, glyph_renderer, base, assets, libaditya
└── __init__.py        ← south_indian, western_wheel

scene/
├── chart_scene.py     ← renderers, themes, glyph_renderer
└── chart_view.py      ← (no gandiva imports beyond chart_scene)
```

Renderers import nothing from `scene/`, `widgets/`, `overlays/`, or `themes`. The theme arrives as a plain dict. This is clean unidirectional dependency — renderers are downstream-agnostic.

## Known Issues and Architectural Debt

1. **`_fmt_lon` duplicated** in both renderers (trivial extraction to base or utility)
2. **Asymmetric data access** — WesternWheel reads libaditya objects during `paint()`, SouthIndian pre-extracts in `update_from_chart()`. The SouthIndian pattern is cleaner.
3. **Force-directed solver re-runs on every paint** — theme changes and selection changes trigger unnecessary re-solves. Could cache solved positions keyed by chart + geometry.
4. **Silent planet overflow** in SouthIndian — planets beyond cell height are dropped with no visual indicator.
5. **No `@abstractmethod`** on `paint()` or `update_from_chart()` in base class — subclass omissions caught at runtime only.
6. **`HIT_RADIUS = 18`** duplicated as magic constant in both renderers instead of defined in base.
7. **Center-hole hack** in SouthIndian — overdrawing with solid background color would break with gradients or images.
8. **Widget state persistence** in ChartScene introspects concrete attribute names (`_levels`, `_highlight_current`) — should use a protocol interface instead.
9. **No-op override** — `WesternWheelRenderer.set_theme()` just calls `super()`, should be removed.

## Comparison with Varuna360 Renderers

| Aspect | Varuna360 | Gandiva |
|--------|-----------|---------|
| Total LOC | 6,780 | ~930 (renderers only) |
| Base class | None | `ChartRenderer(QGraphicsObject)` |
| Data contract | `planets_data` dict (string keys) | libaditya `Chart` objects |
| Code duplication | ~500 LOC across 3 files | ~30 LOC (`_fmt_lon` + `HIT_RADIUS`) |
| Icon system | Raster .webp files, glob loading, per-background presets | SVG path data, `QSvgRenderer` cache |
| Collision avoidance | WheelView only (separate algorithm) | WesternWheel only (force-directed solver) |
| Theme injection | Global imports from `ui.qt_theme` | Dict parameter, no global state |
| Renderer registry | None | `CHART_STYLES` dict |
| Background images | SouthIndian: complex preset system | None (solid fill) |
| Interaction | Zoom, pan, double-click, hover preview | Hover tooltip, click select |
| Transit support | WheelView calls `planets_calculator` at runtime | None (clean separation) |
| Settings files | 3 JSON files, per-view accessors | Theme dict only |
