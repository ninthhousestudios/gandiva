"""Chart renderer registry."""

# Populated after renderer classes are defined to avoid circular imports.
# Import this dict to get {name: renderer_class} mappings.
CHART_STYLES: dict[str, type] = {}
