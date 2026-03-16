"""Overlay registry."""

OVERLAYS: dict[str, type] = {}

from gandiva.overlays.aspect_lines import AspectLinesOverlay  # noqa: E402

OVERLAYS["Aspect Lines"] = AspectLinesOverlay
