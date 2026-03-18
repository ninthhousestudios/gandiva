# Multi-View Charts, Vargas Dock, and Yogas Dock

**Date**: 2026-03-18
**Status**: Approved

## Overview

Three related features that add nested navigation and multi-view capabilities to gandiva:

1. **Multi-view chart area** — side-by-side chart panels, pop-out windows, varga sub-tabs
2. **Vargas dock** — right panel dock for browsing and opening divisional charts
3. **Yogas dock** — right panel dock with dropdown category selector

## Feature 1: Multi-View Chart Area

### ChartPanel (new widget)

A self-contained chart rendering unit. Wraps a `ChartView` + `ChartScene` pair.

- **Properties**: `chart` (Chart object), `varga_number` (int or None for rashi), `active` (bool)
- **Optional header bar**: shown on secondary panels in side-by-side mode. Displays varga name + close button (✕).
- **Active indicator**: subtle border highlight when this panel is the active/selected one. Click to select. When only one panel exists, it is implicitly active (no highlight needed, sub-tab clicks apply to it).
- **`set_chart(chart, varga_number)`**: method to update the panel. Computes the varga chart via `chart.varga(varga_number)` if varga_number is not None, otherwise uses `chart.rashi()`. Passes the result to its renderer. The panel stores its current `varga_number` as an attribute so `ChartArea` can iterate panels and call `panel.set_chart(new_chart, panel.varga_number)` on each when the chart is recalculated.

### ChartArea Rework

Current: `ChartArea` (nested `QMainWindow`) has a single `ChartView` as central widget.

Proposed: Central widget becomes a vertical layout containing:

```
┌─ Varga sub-tab bar (QTabBar, hidden when ≤1 varga) ──┐
├─ QSplitter (horizontal) ──────────────────────────────┤
│  ┌─ ChartPanel ─┐  ┌─ ChartPanel ─────────────────┐  │
│  │  (primary)   │  │  header (varga name + ✕)      │  │
│  │              │  │  (secondary)                  │  │
│  └──────────────┘  └──────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

- **QSplitter**: starts with one ChartPanel. Side-by-side adds a second. Close button on secondary panel removes it from the splitter.
- **Varga sub-tab bar**: `QTabBar` above the splitter with `setTabsClosable(True)`. Always includes a "Rashi" tab (not closable — hide close button on index 0 via `setTabButton(0, RightSide, None)`). Additional tabs for each opened varga, each with a close button. **Visibility rule**: hidden when only "Rashi" exists in the tab list (i.e. no vargas have been opened via "make main" and no side-by-side is active). Shown when there are 2+ tabs in the list OR side-by-side is active. Opening side-by-side automatically adds the varga to the tab list if not already present.
- **Active panel**: click a panel to select it. Sub-tab clicks apply to the active panel. Both panels can show different vargas. Users can swap positions by clicking the other panel and selecting the desired sub-tab — both panels may temporarily show the same varga during this process. When the secondary panel is closed, `active_panel` resets to 0 (primary).
- **Data docks**: remain on the `QMainWindow`, unchanged.

### Pop-out Windows

Two sources for pop-outs, same underlying mechanism — a `QWidget` window (with `Qt.WindowType.Window` flag) containing a single `ChartPanel`:

**Chart tab pop-out** (⬍ button on main chart tab bar):
- The ⬍ button is added to each tab using `QTabBar.setTabButton()` with a small `QPushButton`/`QToolButton` widget placed on the `RightSide` of the tab.
- Creates a `QWidget` window with a `ChartPanel` inside
- Window title: chart name (e.g. "Person A")
- Renders whatever varga the active sub-tab was showing at pop-out time
- No data docks, no sub-tabs — rendering only
- Closing destroys the window

**Varga pop-out** (button in Vargas dock):
- Same mechanism, window title shows chart name + varga name (e.g. "Person A — Navamsha D-9")
- Always renders that specific varga

**Live updates**: `MainWindow` maintains a list of pop-out windows per chart tab (stored in the `_charts` entry). When `MainWindow.on_chart_created()` fires, it iterates the pop-out list for the current chart and calls `set_chart()` on each pop-out's `ChartPanel`. Pop-outs do not connect to `chart_created` directly — `MainWindow` mediates.

**Pop-out lifetime**: pop-out windows are destroyed when:
- The user closes the pop-out window (✕)
- The chart tab they belong to is removed (switching to a different chart with the same birth key replaces the chart — pop-outs update. Removing the tab entirely closes its pop-outs.)

### Varga Sub-tabs Lifecycle

- **Default**: no sub-tab bar (single rashi view, only "Rashi" in tab list)
- **"Make main" from Vargas dock**: adds the varga to the tab list if not already present. If already present, just selects the existing tab. The bar appears when 2+ tabs exist. Active panel switches to that varga.
- **"Side by side" from Vargas dock**: if no secondary panel exists, adds one showing the selected varga. If a secondary panel already exists, replaces its varga. Also adds the varga to the tab list (making the bar visible if needed). Both rashi and the varga are in the tab list.
- **"Side by side" with same varga already showing in primary**: allowed — both panels show the same varga. This enables position-swap workflows.
- **Multiple sub-tabs**: unlimited. Clicking a tab switches the active panel to that varga.
- **Closing a sub-tab** (×): removes the tab from the list. If the active panel was showing that varga, it reverts to rashi. If only "Rashi" remains in the tab list and no side-by-side is active, the bar hides.
- **Closing the secondary panel** (✕ on header): removes the panel from splitter. The varga's tab remains in the tab list (user can re-open via "side by side" or switch to it via tab). If only "Rashi" remains after cleanup, bar hides.

### Per-Chart Tab State

Extend the existing `_charts` list entries with:
- `varga_tabs` — list of varga numbers in the sub-tab bar (always starts with None for rashi)
- `active_panel` — int: 0 (primary) or 1 (secondary). Reset to 0 when secondary is closed.
- `side_by_side` — int or None: varga number the secondary panel is showing, or None if no secondary panel
- `splitter_state` — `QByteArray` from `QSplitter.saveState()` (preserves panel sizes)
- `popouts` — list of pop-out `QWidget` references

Existing `dock_state`, `widgets`, `options` fields unchanged.

**Save/restore on chart tab switch**: when switching chart tabs, `ChartArea` exposes `save_view_state()` → dict and `restore_view_state(state)` → reconstructs sub-tab bar, splitter panels, and active panel from the saved state. This is called alongside the existing `save_dock_state()`/`restore_dock_state()` in `MainWindow`. Pop-outs persist across tab switches (they belong to the chart, not the view state). Pop-outs retain whatever chart data they last received — they are not re-rendered on tab switch, only on `chart_created`. Since each pop-out stores its own chart + varga_number, they always display valid data regardless of which tab is active.

## Feature 2: Vargas Dock (Right Panel)

New data panel registered in `DATA_PANELS`, appears as a tab on the right tab bar.

### Layout

Collapsible tree widget (same pattern as `NakshatrasWidget`):
- Each varga is a top-level row, **collapsed by default**
- Varga list sourced from `Varga().varga_name()` in libaditya. Vargas use integer codes: positive for parivritti, negative for standard. Includes the main 16 plus alternate methods (e.g. Parivritti Hora = 2, Parashara Hora = -2).
- Click a row to expand

### Expanded Row Contents

- Mini chart rendering: a small (approx 150×150px) static `QPixmap` rendered by creating a temporary `ChartScene`, calling the current renderer at small scale, and grabbing the result via `QGraphicsScene.render()` into a `QPainter` on the pixmap. Displayed in a `QLabel`. Re-rendered when chart changes or renderer style changes.
- Three action buttons in a horizontal layout, with tooltips:
  - **⬍ Pop out** — opens a floating pop-out window with this varga
  - **◱ Make main** — adds a varga sub-tab, switches active panel to this varga
  - **◫ Side by side** — adds/replaces secondary panel showing this varga

### Custom Parivritti Entry

Last entry in the tree: "Custom Parivritti" with:
- `QSpinBox` input for an arbitrary division number
- Same three action buttons (operate on the entered number as a parivritti varga code)

### Signals

The Vargas dock emits signals that `MainWindow` connects to `ChartArea` methods:
- `varga_pop_out(int)` → `MainWindow.pop_out_varga(varga_number)`
- `varga_make_main(int)` → `ChartArea.open_varga_tab(varga_number)`
- `varga_side_by_side(int)` → `ChartArea.open_side_by_side(varga_number)`

## Feature 3: Yogas Dock (Right Panel)

New data panel registered in `DATA_PANELS`, appears as a tab on the right tab bar.

### Layout

- **Top**: `QComboBox` dropdown with yoga categories
- **Below**: `QStackedWidget` with one page per category
- Dropdown `currentIndexChanged` switches the stacked widget page
- `update_from_chart(chart)` populates all categories

### Yoga Categories and libaditya API

Each category maps to a method on the rashi (or varga) object:

| Category | Method | Returns |
|---|---|---|
| Nabhasa Yogas | `chart.rashi().nabhasa_yogas()` | `list[NabhasaYoga]` — fields: `name`, `translation`, `category`, `to_move`, `condition` |
| Mahapurusha Yogas | `chart.rashi().panchamahapurusha_yogas()` | `list[MahapurushaYoga]` — fields: `name`, `translation`, `planet`, `present` (bool), `house`, `dignity` |
| Solar Yogas | `chart.rashi().solar_yogas()` | `list[SolarYoga]` — fields: `name`, `planets` (list), `present` (bool) |
| Lunar Yogas | `chart.rashi().lunar_yogas()` | `list[LunarYoga]` — fields: `name`, `planets` (list), `present` (bool) |
| Named Yogas | `chart.rashi().akriti_yogas()` | `list[AkritiYoga]` — fields: `name`, `translation`, `to_move`, `houses` |

All yoga types are dataclasses defined in `libaditya/calc/rashi.py`. Display formatting per category to be determined during implementation — each category has different fields so each page in the stacked widget will have its own layout. Print helpers exist in `libaditya/print_functions.py` (`rich_nabhasa_yogas`, `rich_mahapurusha_yogas`, `rich_solar_yogas`, `rich_lunar_yogas`, `rich_akriti_yogas`) for reference on how to format each type.

### Future Categories

Adding a new category: add an entry to the dropdown, add a page to the stacked widget, wire up the corresponding libaditya method. Bandhana Yogas (`chart.rashi().bandhana_yogas()`) is an existing candidate.

## Key Implementation Details

### Files to Create
- `gandiva/widgets/chart_panel.py` — ChartPanel widget
- `gandiva/widgets/vargas_dock.py` — VargasWidget for right panel
- `gandiva/widgets/yogas_dock.py` — YogasWidget for right panel

### Files to Modify
- `gandiva/widgets/chart_area.py` — rework central widget to sub-tab bar + splitter + ChartPanels
- `gandiva/main_window.py` — pop-out button on chart tabs (via `QTabBar.setTabButton()`), extended per-chart state, pop-out window management, signal wiring for vargas dock
- `gandiva/widgets/data_panels.py` — register VargasWidget and YogasWidget in DATA_PANELS

### Signal Flow

```
chart_created(chart)
  └─→ MainWindow.on_chart_created()
        ├─→ ChartArea.set_chart(chart) — updates all ChartPanels in splitter
        ├─→ iterates popouts list, calls set_chart() on each pop-out's ChartPanel
        └─→ Data docks update_from_chart(chart) (unchanged)

Vargas dock varga_make_main(varga_number)
  └─→ ChartArea.open_varga_tab(varga_number)
        ├─→ adds to sub-tab bar if not present, selects tab
        └─→ active panel switches to that varga

Vargas dock varga_side_by_side(varga_number)
  └─→ ChartArea.open_side_by_side(varga_number)
        ├─→ creates or replaces secondary ChartPanel in splitter
        ├─→ adds varga to tab list if not present
        └─→ shows sub-tab bar

Vargas dock varga_pop_out(varga_number)
  └─→ MainWindow.pop_out_varga(varga_number)
        └─→ creates QWidget window with ChartPanel, adds to popouts list

Varga sub-tab clicked
  └─→ ChartArea — switches active panel's varga via set_chart()

ChartPanel clicked
  └─→ ChartArea — sets active_panel index, updates highlight

Chart tab switch
  └─→ MainWindow
        ├─→ ChartArea.save_view_state() on old tab
        └─→ ChartArea.restore_view_state() on new tab
```

### Dependencies
- libaditya `Varga().varga_name()` for varga list and codes
- libaditya `chart.varga(n)` for varga chart computation (positive n = parivritti, negative n = standard)
- libaditya yoga dataclasses and methods on rashi object (see Yogas section above)
