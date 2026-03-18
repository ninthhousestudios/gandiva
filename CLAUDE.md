# CLAUDE.md — gandiva

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
  main_window.py            # MainWindow — top-level layout, splitter, chart tab bar, signal wiring
  themes.py                 # Theme definitions, app stylesheet generation
  glyphs.py                 # Planet/sign glyph characters
  glyph_renderer.py         # QPainter glyph rendering helpers

  widgets/
    left_panel.py           # Left sidebar: Chart Info, Calc Options, Display, Overlays, Widgets tabs
    chart_input.py          # Right sidebar: Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga tabs
                            #   Also holds hidden calculation widgets and calculate() method
    planet_table.py         # (legacy) QTableWidget for planet positions
    chart_wheel.py          # (legacy) chart wheel widget

  scene/
    chart_scene.py          # QGraphicsScene — hosts chart renderer, overlays, info widgets
    chart_view.py           # QGraphicsView with zoom/pan

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

### Layout: three-panel splitter

```
[Left TabBar] | [Left Panel] | [Chart View (QGraphicsScene)] | [Right Panel] | [Right TabBar]
```

- **Left panel** (`LeftPanel`): collapsible sidebar with animated width. Tabs: Chart Info (birth data form + Calculate), Calc Options (zodiac, ayanamsa, hsys, Jaimini, HD, CoT), Display (chart style, signize, round, themes), Overlays (checkboxes), Widgets (spawn buttons).
- **Center**: `ChartScene` (QGraphicsScene) + `ChartView` (QGraphicsView). Hosts the chart renderer, overlays, and floating info widgets.
- **Right panel** (`ChartInputPanel`): collapsible sidebar with animated width. Tabs: Planets (3x4 grid of QTreeWidgets), Cusps (table), Nakshatras (tree grouped by nakshatra), Dashas (Vimshottari + placeholder Rashi), Kala (cardinal points, lunar new year, panchanga, moon phases), Panchanga (monthly table with independent month/year/location).
- Tab bars live outside the splitter so they're always visible even when panels are collapsed.
- Both panels use custom `QPropertyAnimation` on width for smooth collapse/expand.

### Chart tab system

- `QTabBar` at top of window for multiple charts.
- Each chart entry stores: `chart`, `key` (birth key), `state` (birth form values), `options` (calc/display options), `widgets` (info widget states).
- `get_birth_key()` determines tab identity — includes birth info + zodiac + ayanamsa + hsys + Jaimini options.
- Changing birth info → new tab. Changing calc options that are in the key → new tab. Changing display-only options → updates existing tab.
- Options are saved/restored per chart tab via `get_options_state()`/`set_options_state()` with `blockSignals` to prevent cascading.

### Chart calculation flow

1. Left panel Calculate button → `calculate_requested` signal
2. `MainWindow._on_calculate_requested()` copies all values from left panel to right panel's hidden widgets
3. `ChartInputPanel._calculate()` builds `EphContext` + `Chart`, emits `chart_created`
4. `MainWindow.on_chart_created()` checks birth key, creates/updates tab, calls `_display_chart()`
5. `_display_chart()` → `chart_scene.set_chart(chart)` + `input_panel.update_info(chart)`

### Info widgets (floating, scene-based)

- `InfoWidget` (base): `QGraphicsProxyWidget` with title bar drag (via event filter), resize grip (painted in `paint()` after `super().paint()`), minimize, close, hover show/hide buttons, z-order raise on click.
- Spawned from left panel Widgets tab. Multiple instances of same type allowed.
- Widget states saved/restored per chart tab.

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

## Upcoming: QDockWidget architecture migration

The current right panel uses a `QStackedWidget` + custom `QTabBar` + animation. This should be migrated to `QDockWidget` so that:
- Each data panel (Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga) can be popped out into its own floating window
- Panels can be docked back, tabified, or arranged side-by-side
- Individual planet detail views can also be popped out (useful for Shadbala/Avasthas)
- The left panel should also be considered for this migration

This is the next major architectural task. See the planning conversation for details.

## Style preferences

- Font for monospace displays (Kala, Panchanga tabs): Source Code Pro Semibold, 10pt
- Theming system exists (`themes.py`) but is basic — future: full theme system including fonts
- Future: keybind system
