# Gāṇḍiva

A PyQt6 desktop application for Jyotish (Vedic astrology), built on [libaditya](https://gitlab.com/ninthhouse/libaditya).

Gandiva is a presentation layer — all astronomical and astrological computation is handled by libaditya. Gandiva provides an interactive, dockable-panel interface for exploring charts, vargas, dashas, and more.

NOTE: binaries for Windows and MacOS availabe here:
[Gandiva binaries](https://github.com/ninthhousestudios/gandiva/releases/tag/v1.0.0)


## Features

- **Multiple chart styles** — Western wheel and South Indian grid renderers
- **Divisional charts (vargas)** — side-by-side varga display with the main chart
- **Dockable data panels** — Planets, Cusps, Nakshatras, Dashas, Kala, and Panchanga, each floatable and rearrangeable
- **Planet detail pop-outs** — 3x4 planet grid with floating detail windows
- **Jaimini indicators** — automatic detection of jaimini yogas across vargas
- **Overlays** — aspect lines and rashi aspect overlays on the chart
- **Floating info widgets** — draggable, resizable widgets for dashas, panchanga, and mini vargas on the chart scene
- **Multi-chart tabs** — open multiple charts simultaneously, each preserving its own layout and options
- **Shadbala and Avasthas** — planetary strength and state calculations
- **Themes** — switchable color themes

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended package manager)
- [libaditya](../libaditya) — the astrological calculation library (linked as a local dependency)

## Installation for Linux (for MacOS and Windows, download binaries from github; link
above)

```bash
git clone https://gitlab.com/ninthhouse/gandiva
git clone https://gitlab.com/ninthhouse/libaditya
cd gandiva

uv sync
uv run gandiva/app.py
```

libaditya is expected to be in a sibling directory (`../libaditya`).

## Usage

```bash
uv run python -m gandiva.app
```

1. Enter birth data (date, time, location) in the left panel
2. Click **Calculate** to generate a chart
3. Use the right tab bar to open data panels (Planets, Cusps, Dashas, etc.)
4. Switch chart styles and display options in the left panel's Display tab
5. Toggle overlays and spawn floating widgets from their respective tabs

## Building Standalone Binaries

Gandiva uses [Nuitka](https://nuitka.net/) for standalone builds. See `docs/nuitka-build.md` for platform-specific instructions.

```bash
uv run build.py
```

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE) for details.

Copyright (C) 2026 Ninth House Studios, LLC
