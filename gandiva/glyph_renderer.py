"""
Render SVG-path astrological glyphs via QPainter.

Usage:
    from gandiva.glyph_renderer import draw_glyph
    from gandiva.glyphs import PLANET_GLYPHS

    draw_glyph(painter, PLANET_GLYPHS["Sun"], cx, cy, size=20, color=QColor(...))
"""

from PyQt6.QtCore import QRectF, QByteArray, Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtSvg import QSvgRenderer


_SVG_COMMANDS = set("MmZzLlHhVvCcSsQqTtAa")


def _make_svg(glyph: dict, color: str = "#000000", stroke_width: float = 1.5) -> bytes:
    """Wrap glyph path data in a minimal SVG document.

    The path fragments in glyphs.py are relative-coordinate sequences extracted
    from AstroChart.  Many start with bare coordinate pairs (no command letter),
    which SVG's M-followed-by-coords would interpret as absolute L commands —
    sending the pen to near-origin and producing stray diagonal lines.
    Prepend 'l' when the fragment starts with a coordinate instead of a letter
    so Qt renders them as relative lineto sequences from the anchor point.
    """
    shift_x, shift_y = glyph["shift"]
    paths_svg = ""
    for path_d, dx, dy in glyph["paths"]:
        ox = 50 + shift_x + dx
        oy = 50 + shift_y + dy
        # If path_d starts with a coordinate (digit, minus, or dot) rather than
        # an SVG command letter, make it a relative lineto sequence.
        fragment = path_d.strip()
        if fragment and fragment[0] not in _SVG_COMMANDS:
            fragment = "l " + fragment
        full_d = f"M {ox},{oy} {fragment}"
        paths_svg += (
            f'<path d="{full_d}" '
            f'stroke="{color}" stroke-width="{stroke_width}" fill="none"/>\n'
        )

    svg = (
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 10 80 80" '
        'width="80" height="80">'
        f'{paths_svg}'
        '</svg>'
    )
    return svg.encode("utf-8")


# cache rendered SVGs keyed by (id(glyph), color_hex, stroke_width)
_cache: dict[tuple, QSvgRenderer] = {}


def _get_renderer(glyph: dict, color: QColor, stroke_width: float = 1.5) -> QSvgRenderer:
    key = (id(glyph), color.name(), stroke_width)
    if key not in _cache:
        svg_bytes = _make_svg(glyph, color.name(), stroke_width)
        renderer = QSvgRenderer(QByteArray(svg_bytes))
        _cache[key] = renderer
    return _cache[key]


def draw_glyph(
    painter: QPainter,
    glyph: dict,
    cx: float,
    cy: float,
    size: float = 20.0,
    color: QColor = QColor(0, 0, 0),
    stroke_width: float = 1.5,
):
    """Draw an astrological glyph centered at (cx, cy) with the given size."""
    renderer = _get_renderer(glyph, color, stroke_width)
    half = size / 2
    rect = QRectF(cx - half, cy - half, size, size)
    renderer.render(painter, rect)


def clear_cache():
    """Clear the renderer cache (call after color/theme changes)."""
    _cache.clear()
