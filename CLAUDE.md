# gandiva

PyQt6 desktop GUI for [libaditya](../libaditya). Thin presentation layer — all computation is in libaditya. Fun/learning project.

## Setup & Run

```bash
cd /home/josh/w/astro/soft/gandiva
uv venv && source .venv/bin/activate && uv add . --dev
python -m gandiva.app
```

libaditya is linked as editable local dependency (see `pyproject.toml` `[tool.uv.sources]`).

## Project structure

```
gandiva/
  app.py                    # QApplication entry point
  main_window.py            # MainWindow — layout, chart tab bar, signal wiring
  themes.py                 # Theme definitions, stylesheet generation
  glyphs.py / glyph_renderer.py  # Planet/sign glyphs + QPainter helpers
  widgets/
    left_panel.py           # Left sidebar: Chart Info, Calc Options, Display, Overlays, Widgets
    chart_area.py           # Nested QMainWindow with ChartView + data dock widgets
    data_panels.py          # 6 data widgets (Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga)
  scene/
    chart_scene.py          # QGraphicsScene — hosts renderer, overlays, info widgets
    chart_view.py           # QGraphicsView — forwards wheel events for scrolling
  renderers/                # BaseRenderer ABC, WesternWheelRenderer, SouthIndianRenderer
  overlays/                 # Aspect lines, rashi aspects
  info_widgets/             # Draggable/resizable floating widgets (dasha, mini varga, panchanga)
```

Dead code: `chart_input.py`, `planet_table.py`, `chart_wheel.py`.

## Layout

```
[Left TabBar] | [Left Panel] | [ChartArea] | [Right TabBar]
                                ├── Central: ChartView (QGraphicsScene)
                                └── Dock widgets: Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga
```

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
                 ayanamsa=98, hsys="C", signize=True, toround=(True, 3))
chart = Chart(context=ctx)

# NOTE: Location.placename is a METHOD, not a property — call loc.placename()

# Planets: chart.rashi().planets() → dict of Planet objects
#   .longitude(), .sign_name(), .nakshatra_name(), .dignity(), .retrograde(), etc.
# Zodiac: chart.tropical() / chart.sidereal(ayanamsa=27) / chart.aditya()
# Vargas: chart.varga(9)
# Cusps: chart.rashi().cusps()
# Panchanga: Panchanga(ctx) → .sunrise(), .tithi(), .nakshatra(), .vara(), etc.
# Vimshottari: calculate_vimshottari_dasha(planet, dlevels=1)
# JulianDay: .jd_number(), .month(), .year(), .day("usr"), .time("usr", False)
# Kala: from libaditya.calc.kala import cardinal_points, lunar_new_year
```

## Chart calculation flow

1. Calculate button → `LeftPanel._calculate()` builds `EphContext` + `Chart`
2. `LeftPanel` emits `chart_created(chart)` signal
3. `MainWindow.on_chart_created()` checks birth key, creates/updates tab, calls `_display_chart()`
4. `_display_chart()` → `chart_area.set_chart(chart)` (updates scene + all data panels)

### Chart tab identity

`get_birth_key()` determines tab identity — includes birth info + zodiac + ayanamsa + hsys + Jaimini options. Changing birth info or key calc options → new tab. Changing display-only options → updates existing tab. Options saved/restored per tab via `get_options_state()`/`set_options_state()` with `blockSignals` to prevent cascading.

## Design principles

- All astro computation stays in libaditya. gandiva only does presentation.
- Prefer interactive PyQt6 widgets over static SVGs.
- Keep it simple and fun.

## Style

- Monospace font: Source Code Pro Semibold, 10pt
