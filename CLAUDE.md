# CLAUDE.md — lagui

## What is this?

A PyQt6 desktop GUI for [libaditya](../libaditya), an astrological calculation library. lagui is a thin presentation layer — all computation is done by libaditya. This is a fun/learning project, not production software.

## Setup

```bash
cd /home/josh/w/astro/soft/lagui
uv venv && source .venv/bin/activate
uv add . --dev
```

libaditya is linked as an editable local dependency (see `pyproject.toml` `[tool.uv.sources]`).

## Run

```bash
python -m lagui.app
```

## Project structure

```
lagui/
  app.py              # QApplication entry point
  main_window.py      # MainWindow — top-level layout, splitter, wiring
  widgets/
    chart_input.py     # Left panel: date/time/location form, zodiac/ayanamsa options, "Calculate" button
    planet_table.py    # QTableWidget showing planet positions from a chart
```

## How libaditya is used

All computation goes through libaditya. The GUI never does astro math itself.

```python
from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const

# Build an EphContext from user input, then:
chart = Chart(context=context)
rashi = chart.rashi()
planets = rashi.planets()  # dict-like, keyed by name ("Sun", "Moon", etc.) or number

# Per planet:
planet.longitude()          # formatted position string
planet.sign_name()          # "Aries", "Taurus", etc. (or Aditya names)
planet.nakshatra_name()     # "Kritika", etc.
planet.dignity()            # "EX", "MT", "OH", "GF", "F", "N", "E", "GE", "DB"
planet.longitude_speed()    # float, deg/day
planet.retrograde()         # bool
planet.ecliptic_longitude() # float, 0-360

# Zodiac modes:
chart.tropical()            # returns new Chart
chart.sidereal(ayanamsa=27) # returns new Chart
chart.aditya()              # returns new Chart

# Divisional charts:
chart.varga(9)              # Navamsha, same .planets() interface

# Other data:
rashi.panchanga()           # Tithi, Nakshatra, Yoga, Karana, Vara
rashi.panchanga().vimshottari_dasha()  # Dasha periods
rashi.cusps()               # House cusps
chart.cot()                 # Cards of Truth
chart.bodygraph()           # Human Design
```

## Design principles

- lagui is an **example app** showing how to use libaditya. Keep it separate.
- All astro computation stays in libaditya. lagui only does presentation.
- Prefer interactive PyQt6 widgets over rendering static SVGs.
- Keep it simple and fun. No over-engineering.

---

# Implementation Plan — Phase 1

This plan covers the first usable version: enter chart data, see planet positions, switch between zodiac systems and vargas.

## Step 1: Get it running (DONE — scaffolded)

The skeleton is in place:
- `app.py` → QApplication entry point
- `main_window.py` → horizontal QSplitter: input panel (left) + planet table (right)
- `widgets/chart_input.py` → form with name, datetime, UTC offset, lat/long/place, zodiac mode, ayanamsa, house system, "Calculate" button. Emits `chart_created` signal with a `Chart` object.
- `widgets/planet_table.py` → QTableWidget with columns: Planet, Longitude, Sign, Nakshatra, Dignity, Speed. Populated from `chart.rashi().planets()`.

**First thing to do:** `cd ../lagui && uv venv && source .venv/bin/activate && uv add . --dev && python -m lagui.app` — verify the window opens and shows planet data. Fix any import or API issues.

## Step 2: Polish the planet table

- Add retrograde indicator (show "R" or color the row)
- Add a "Retro" column or mark retrograde planets with a distinct color
- Color-code dignity: green for EX/MT/OH, neutral for F/GF/N, red for E/GE/DB
- Add tooltips on planet rows (e.g., full degree, lat, distance)
- Make the table font monospaced for alignment

## Step 3: Add Panchanga display

- Below the planet table (or as a tab), show Panchanga info:
  - Tithi, Nakshatra, Yoga, Karana, Vara
- Access: `chart.rashi().panchanga()` — use `str(panchanga)` initially, then break out individual fields
- Simple QGroupBox with QLabels

## Step 4: Varga selector

- Add a QComboBox in the input panel or above the planet table: "D1 Rashi", "D9 Navamsha", "D2 Hora", etc.
- When changed, call `chart.varga(n)` and update the planet table
- The key vargas to include:
  - D1 (Rashi), D2 (Hora), D3 (Drekkana), D4, D7, D9 (Navamsha), D10, D12, D16, D20, D24, D27, D30, D40, D45, D60
- Note: special vargas use negative codes (e.g., -3 for Drekkana with deities)

## Step 5: Cusps / house display

- Add a second table or section showing house cusps
- Access: `chart.rashi().cusps()` — iterate and show cusp positions
- Show which planets are in which house

## Step 6: Vimshottari Dasha display

- New widget: tree view or nested list showing dasha periods
- Access: `chart.rashi().panchanga().vimshottari_dasha()`
- Show Maha Dasha → Antar Dasha → Pratyantara levels
- Highlight the currently active period

## Step 7: Status bar and chart info

- Show in the status bar or a header: chart name, date/time, location, zodiac system
- Show the ayanamsa name and value when in sidereal mode

## Future phases (not for now, just awareness)

- **Chart diagram drawing**: North Indian diamond or South Indian grid, drawn with QPainter directly on a QWidget — this is the big interactive feature that makes a desktop app worthwhile
- **Cards of Truth**: visual card layout
- **Human Design bodygraph**: drawn with QPainter (not SVG)
- **Transit overlay**: second chart overlaid on natal
- **Side-by-side comparison**: two charts
- **Fixed star search**: searchable table of stars near planet positions

## Key libaditya API patterns to know

```python
# Creating a chart from GUI inputs:
jd = JulianDay((year, month, day, hour_decimal), utcoffset=offset)
loc = Location(lat=lat, long=lon, placename=name, utcoffset=offset)
ctx = EphContext(name=name, timeJD=jd, location=loc, sysflg=flag, circle=circle, ...)
chart = Chart(context=ctx)

# Planet iteration:
for name, planet in chart.rashi().planets().items():
    planet.longitude()        # str, formatted
    planet.sign_name()        # str
    planet.nakshatra_name()   # str
    planet.dignity()          # str code
    planet.longitude_speed()  # float
    planet.retrograde()       # bool
    planet.ecliptic_longitude()  # float, raw degrees

# Zodiac switching (returns NEW chart, doesn't mutate):
chart_trop = chart.tropical()
chart_sid = chart.sidereal(ayanamsa=27)
chart_aditya = chart.aditya()

# Varga access (same .planets() interface):
navamsha_planets = chart.varga(9).planets()

# EphContext sysflg values:
# const.ECL = tropical ecliptic
# const.SID = sidereal
# Circle.ADITYA = Aditya circle (tropical with 330° offset)
# Circle.ZODIAC = standard zodiac names
```
