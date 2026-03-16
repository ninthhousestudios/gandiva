"""Overlay registry."""

OVERLAYS: dict[str, type] = {}

from gandiva.overlays.aspect_lines import AspectLinesOverlay  # noqa: E402

OVERLAYS["Aspect Lines"] = AspectLinesOverlay

from gandiva.overlays.rashi_aspects import RashiAspectsOverlay  # noqa: E402

OVERLAYS["Rashi Aspects"] = RashiAspectsOverlay
