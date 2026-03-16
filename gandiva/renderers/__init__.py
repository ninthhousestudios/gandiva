"""Chart renderer registry."""

# Populated after renderer classes are defined to avoid circular imports.
# Import this dict to get {name: renderer_class} mappings.
CHART_STYLES: dict[str, type] = {}

from gandiva.renderers.western_wheel import WesternWheelRenderer  # noqa: E402

CHART_STYLES["Western Wheel"] = WesternWheelRenderer

from gandiva.renderers.south_indian import SouthIndianRenderer  # noqa: E402

CHART_STYLES["South Indian"] = SouthIndianRenderer
