# CLAUDE.md — gandiva

## TODO

- [ ] Fix outer planets toggle in side-by-side vargas
- [ ] Fix right-side info display in side-by-side view (Planets/Cusps should reflect focused varga, not just rashi)
- [ ] Implement South Indian chart renderer
- [ ] Implement North Indian chart renderer

## What is this?

A PyQt6 desktop GUI for [libaditya](../libaditya), an astrological calculation library. gandiva is a thin presentation layer — all computation is done by libaditya. This is a fun/learning project, not production software.

## Setup

```bash
cd /home/josh/w/astro/soft/gandiva
uv venv && source .venv/bin/activate
uv add . --dev
```

libaditya is linked as an editable local dependency (see `pyproject.toml` `[tool.uv.sources]`).

## Run

```bash
python -m gandiva.app
```

## Project structure

```
gandiva/
  app.py                    # QApplication entry point
  main_window.py            # MainWindow — top-level layout, chart tab bar, signal wiring
  themes.py                 # Theme definitions, app stylesheet generation
  glyphs.py                 # Planet/sign glyph characters
  glyph_renderer.py         # QPainter glyph rendering helpers

  widgets/
    left_panel.py           # Left sidebar: Chart Info, Calc Options, Display, Overlays, Widgets tabs
                            #   Also holds _calculate() method and birth key/state management
    chart_area.py           # ChartArea — nested QMainWindow with ChartView + data dock widgets
    data_panels.py          # 6 standalone data display widgets (Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga)
    chart_input.py          # (dead code — replaced by data_panels.py + left_panel.py calc)
    planet_table.py         # (dead code)
    chart_wheel.py          # (dead code)

  scene/
    chart_scene.py          # QGraphicsScene — hosts chart renderer, overlays, info widgets
    chart_view.py           # QGraphicsView — forwards wheel events to proxy widgets for scrolling

  renderers/
    __init__.py             # CHART_STYLES registry
    base.py                 # BaseRenderer ABC
    western_wheel.py        # Western wheel chart renderer
    south_indian.py         # South Indian grid chart renderer

  overlays/
    __init__.py             # OVERLAYS registry
    base.py                 # BaseOverlay ABC
    aspect_lines.py         # Aspect line overlay
    rashi_aspects.py        # Rashi (sign-based) aspect overlay

  info_widgets/
    __init__.py             # INFO_WIDGETS registry
    base.py                 # InfoWidget — draggable/resizable QGraphicsProxyWidget base class
    nakshatra_dasha.py      # Floating Vimshottari dasha widget (scene-based)
    mini_varga.py           # Mini divisional chart widget
    panchanga.py            # Panchanga info widget
    dasha.py                # Dasha info widget
```

## Current architecture

### Layout

```
[Left TabBar] | [Left Panel] | [ChartArea (nested QMainWindow)] | [Right TabBar]
                                ├── Central: ChartView (QGraphicsScene)
                                └── Dock widgets: Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga
```

- **Left panel** (`LeftPanel`): collapsible sidebar with animated width (`QPropertyAnimation`). Tabs: Chart Info (birth data form + Calculate), Calc Options (zodiac, ayanamsa, hsys, Jaimini, HD, CoT), Display (chart style, signize, round, themes), Overlays (checkboxes), Widgets (spawn buttons). Also holds `_calculate()` method and `chart_created` signal.
- **Center** (`ChartArea`): nested `QMainWindow` (with `setWindowFlags(Qt.WindowType.Widget)`). Central widget is `ChartView` (QGraphicsView + ChartScene). Data panels are `QDockWidget`s that can float, dock, or be closed. All docks start hidden.
- **Right tab bar**: `QTabBar` with `RoundedEast` shape. Each tab toggles the corresponding dock widget (one at a time). Lives outside ChartArea in the main layout.
- **Data panels** (`data_panels.py`): 6 standalone widgets (PlanetsWidget, CuspsWidget, NakshatrasWidget, DashasWidget, KalaWidget, PanchangaWidget). Each has `update_from_chart(chart)` and `adjust_font(delta)`. Registered in `DATA_PANELS` dict.
- Left tab bar lives outside the left panel so it's always visible even when the panel is collapsed.

### Chart tab system

- `QTabBar` at top of window for multiple charts (hidden until 2+ charts).
- Each chart entry stores: `chart`, `key` (birth key), `state` (birth form values), `options` (calc/display options), `widgets` (info widget states), `dock_state` (QByteArray from `ChartArea.saveState()`).
- `get_birth_key()` determines tab identity — includes birth info + zodiac + ayanamsa + hsys + Jaimini options.
- Changing birth info → new tab. Changing calc options that are in the key → new tab. Changing display-only options → updates existing tab.
- Options are saved/restored per chart tab via `get_options_state()`/`set_options_state()` with `blockSignals` to prevent cascading.
- Dock layout is saved/restored per chart tab via `ChartArea.save_dock_state()`/`restore_dock_state()`.

### Chart calculation flow

1. Left panel Calculate button → `LeftPanel._calculate()` builds `EphContext` + `Chart`
2. `LeftPanel` emits `chart_created(chart)` signal
3. `MainWindow.on_chart_created()` checks birth key, creates/updates tab, calls `_display_chart()`
4. `_display_chart()` → `chart_area.set_chart(chart)` (updates scene + all data panels)

### Info widgets (floating, scene-based)

- `InfoWidget` (base): `QGraphicsProxyWidget` with title bar drag (via event filter), resize grip (painted in `paint()` after `super().paint()`), minimize, close, hover show/hide buttons, z-order raise on click.
- Spawned from left panel Widgets tab. Multiple instances of same type allowed.
- Widget states saved/restored per chart tab.
- `ChartView.wheelEvent` forwards scroll events to proxy widgets so embedded tables are scrollable.

### Overlays

- Rendered as QGraphicsItems added to the scene on top of the chart renderer.
- Toggled from left panel Overlays tab.

### Renderers

- `BaseRenderer` ABC. Implementations: `WesternWheelRenderer`, `SouthIndianRenderer`.
- Selected via Display tab "Chart Style" combo.
- Each renderer draws into the QGraphicsScene.

## Key libaditya API patterns

```python
from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const
from libaditya.calc import Panchanga
from libaditya.calc.vimshottari import calculate_vimshottari_dasha, calculate_specific_period

# Chart creation:
jd = JulianDay((year, month, day, hour_decimal), utcoffset=offset)
loc = Location(lat=lat, long=lon, placename=name, utcoffset=offset)
ctx = EphContext(name=name, timeJD=jd, location=loc, sysflg=sysflg, circle=circle,
                 ayanamsa=98, hsys="C",
                 rashi_temporary_friendships=True, rashi_aspects="quadrant",
                 hd_gate_one=223.25, cot_savana_day=True, cot_planet_order="vedic",
                 signize=True, toround=(True, 3), print_nakshatras=True,
                 print_outer_planets=True, hd_print_hexagrams=False)
chart = Chart(context=ctx)

# NOTE: Location.placename is a METHOD, not a property — call loc.placename()

# Planets:
for name, planet in chart.rashi().planets().items():
    planet.longitude()           # str, formatted
    planet.sign_name()           # str
    planet.in_sign_longitude()   # str, DD:MM:SS within sign
    planet.amsha_longitude()     # float
    planet.nakshatra_name()      # str
    planet.dignity()             # str: "EX", "MT", "OH", "GF", "F", "N", "E", "GE", "DB"
    planet.longitude_speed()     # float, deg/day
    planet.retrograde()          # bool
    planet.ecliptic_longitude()  # float, 0-360
    planet.latitude()            # float
    planet.distance()            # float, AU
    planet.rise()                # JulianDay
    planet.set()                 # JulianDay
    planet.constellation()       # str

# Zodiac switching (returns NEW chart):
chart.tropical()  / chart.sidereal(ayanamsa=27)  / chart.aditya()

# Vargas: chart.varga(9)  — same .planets() interface

# Cusps: chart.rashi().cusps() — list, each has .number(), .sign_name(), .nakshatra_name(), etc.

# Panchanga:
p = Panchanga(ctx)
p.sunrise() / p.sunset() / p.moonrise() / p.moonset()  # JulianDay objects
p.vara() / p.nakshatra() / p.tithi() / p.karana() / p.yoga_name()  # strings
p.next_vara() / p.next_nakshatra() / p.next_tithi() / p.next_karana() / p.next_yoga()  # have .timeJD

# Vimshottari Dasha:
# calculate_vimshottari_dasha(planet, dlevels=1, yrlen=365.2422) → [..., first_dasha_idx, beginning_age]
# calculate_specific_period(planet, lord_path=[idx, ...], yrlen) → (JulianDay, dur_days)
# Lord indices: 0=Ke, 1=Ve, 2=Su, 3=Mo, 4=Ma, 5=Ra, 6=Ju, 7=Sa, 8=Me

# JulianDay:
jd.jd_number()    # float
jd.month()        # int
jd.year()         # int
jd.day("usr")     # int (local), day("utc") for UTC
jd.time("usr", False)  # time string
jd.timezone()     # str
jd.shift("f", "day", 1)  # forward 1 day

# Kala:
from libaditya.calc.kala import cardinal_points, lunar_new_year
cardinal_points(year)  # list of 4 JulianDay-like objects
lunar_new_year(jd)     # has .moon() method

# EphContext sysflg values:
# const.ECL = tropical ecliptic
# const.SID = sidereal
# Circle.ADITYA = Aditya circle (tropical with 330 offset)
# Circle.ZODIAC = standard zodiac names
# const.dasha_years = {"saura": 365.24, "nakshatra": 359.02, ...}
```

## Design principles

- gandiva is an **example app** showing how to use libaditya. Keep it separate.
- All astro computation stays in libaditya. gandiva only does presentation.
- Prefer interactive PyQt6 widgets over rendering static SVGs.
- Keep it simple and fun. No over-engineering.

## Known issues / WIP

- **South Indian renderer**: needs visual polish — rounded corners, center fix, bigger planets, sign name direction, zodiac mode verification.
- **Panchanga tab**: Cal/Sunrise and Savana/Sunrise modes marked WIP (not yet verified correct).
- **Info widgets**: should eventually be spawnable multiple times with per-instance options (e.g. varga selector). Widget tab UI needs redesign.

## Future work

- Individual planet detail docks (useful for Shadbala/Avasthas)
- Varga selector per dock (e.g. view Planets in varga 9)
- Multiple ChartViews as docks in ChartArea (two charts side by side)
- HD/CoT tabs on the left panel
- Dead code cleanup: delete `chart_input.py`, `planet_table.py`, `chart_wheel.py`

## Recent implementations

### PlanetsWidget (3×4 grid with pop-out)

The Planets tab now displays all 12 planets in a rigid 3×4 grid using `QGridLayout`:
- **Row 0**: Sun, Moon, Mars, Mercury (Vedic order)
- **Row 1**: Jupiter, Venus, Saturn, Rahu
- **Row 2**: Ketu, Uranus, Neptune, Pluto

**Pop-out feature**: Each panel has a ⬍ button that creates a cloned floating `QDockWidget` for detailed reading. The original tree stays locked in the grid; the floating window shows only an X button (no re-dock button). When closed, the clone is destroyed without affecting the grid layout. Implementation uses `topLevelChanged` signal to switch between float/close buttons based on docked vs floating state.

## Style preferences

- Font for monospace displays (Kala, Panchanga tabs): Source Code Pro Semibold, 10pt
- Theming system exists (`themes.py`) but is basic — future: full theme system including fonts
- Future: keybind system
