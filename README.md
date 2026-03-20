# Gāṇḍiva

A PyQt6 desktop application for Jyotish (Vedic astrology), built on [libaditya](https://gitlab.com/ninthhouse/libaditya).

Gandiva is a presentation layer — all astronomical and astrological computation is handled by libaditya. Gandiva provides an interactive, dockable-panel interface for exploring charts, vargas, dashas, and more.

NOTE: Gandiva is 100% vibe-coded software. I can sort of tell; it's pretty slow and
heavy. In any case, I wrote ```libaditya``` by hand (though it now has calculation
additions from Claude) but the idea of making a GUI for it was very overwhelming and not
very interesting.

This is of course where Claude comes in. I made this in about three days of working
time. I'm not going to say it is a great piece of software and that it is production
ready - I'm not saying that, and I'm not suggesting you switch from your regular
software.

But, this provides an interesting opportunity. For me, I have a hard time designing
something completely. I need to see it, use it, to really know how I want it to be. But
when building something is intensive and difficult, then it is difficult to see it...but
with Claude, I was able to just do this quickly and see what it is like.

I see this as an opportunity to experiment, especially with the UX/UI design.
Since it is relatively easier to add, subtract, change things, then you just can and see
what it's like. At some point, it could be that I want to make a proper piece of
software. This will help a lot because then I will have a much clearer idea of what I
want and how to accomplish it.

Lastly, you can modify Gandiva yourself if you want to. An agent, Claude, Codex, etc.
should be able to download and install Gandiva, so then you can try modifying it in a
way that you think is interesting.

I'd be curious to hear what you like and dislike about the setup of this software. What
would you want? How would you design your software?

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

## Installation

```bash
git clone <repo-url>
cd gandiva

# Create a virtual environment and install dependencies
uv venv && source .venv/bin/activate
uv add . --dev
```

libaditya is expected to be in a sibling directory (`../libaditya`). See `pyproject.toml` for the source link.

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
