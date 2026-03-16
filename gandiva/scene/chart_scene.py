"""QGraphicsScene subclass that manages chart renderer, overlays, and info widgets."""

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsScene

from gandiva.glyph_renderer import clear_cache
from gandiva.renderers import CHART_STYLES
from gandiva.themes import get_theme, DEFAULT_THEME


class ChartScene(QGraphicsScene):
    """Manages the layered scene: background, chart renderer, overlays, info widgets."""

    overlay_added = pyqtSignal(str)
    overlay_removed = pyqtSignal(str)
    widget_added = pyqtSignal(str)
    widget_removed = pyqtSignal(str)

    # Z-value constants
    Z_CHART = 10
    Z_OVERLAY_BASE = 50
    Z_WIDGET_BASE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = None
        self._chart = None
        self._theme = get_theme(DEFAULT_THEME)
        self._rect = QRectF()
        self._overlays: dict[str, object] = {}
        self._info_widgets: dict[str, object] = {}
        self.setBackgroundBrush(QColor(self._theme["bg"]))

    def set_theme(self, name: str) -> None:
        """Propagate theme to all scene items."""
        self._theme = get_theme(name)
        clear_cache()
        self.setBackgroundBrush(QColor(self._theme["bg"]))
        if self._renderer:
            self._renderer.set_theme(self._theme)
        for overlay in self._overlays.values():
            overlay.set_theme(self._theme)
        for widget in self._info_widgets.values():
            widget.set_theme(self._theme)

    def set_chart(self, chart) -> None:
        """Pass chart data to renderer and all scene items."""
        self._chart = chart
        if self._renderer:
            self._renderer.update_from_chart(chart)
        for overlay in self._overlays.values():
            overlay.update_from_chart(chart)
        for widget in self._info_widgets.values():
            widget.update_from_chart(chart)

    def set_chart_style(self, style_name: str) -> None:
        """Switch to a different chart renderer. Clears all overlays, keeps info widgets."""
        renderer_class = CHART_STYLES.get(style_name)
        if renderer_class is None:
            return

        # Remove old renderer
        if self._renderer:
            self.removeItem(self._renderer)
            self._renderer = None

        # Instantiate new renderer
        self._renderer = renderer_class()
        self._renderer.setZValue(self.Z_CHART)
        self.addItem(self._renderer)

        # Initialize with current state
        if self._rect.isValid():
            self._renderer.resize(self._rect)
        self._renderer.set_theme(self._theme)
        if self._chart:
            self._renderer.update_from_chart(self._chart)

        # Clear all overlays
        for overlay_id in list(self._overlays.keys()):
            self.remove_overlay(overlay_id)

    def resize_chart(self, rect: QRectF) -> None:
        """Called by ChartView on resize. Propagates to renderer and overlays."""
        self._rect = rect
        self.setSceneRect(rect)
        if self._renderer:
            self._renderer.resize(rect)
        for overlay in self._overlays.values():
            overlay.resize(rect)

    # ── overlay management ─────────────────────────────────────────────────

    def add_overlay(self, overlay_id: str) -> None:
        """Add an overlay by its registry ID."""
        # Placeholder for Phase 2
        pass

    def remove_overlay(self, overlay_id: str) -> None:
        """Remove an overlay by its registry ID."""
        if overlay_id in self._overlays:
            self.removeItem(self._overlays.pop(overlay_id))
            self.overlay_removed.emit(overlay_id)

    # ── info widget management ──────────────────────────────────────────────

    def add_info_widget(self, widget_id: str) -> None:
        """Add an info widget by its registry ID."""
        # Placeholder for Phase 2
        pass

    def remove_info_widget(self, widget_id: str) -> None:
        """Remove an info widget by its registry ID."""
        if widget_id in self._info_widgets:
            self.removeItem(self._info_widgets.pop(widget_id))
            self.widget_removed.emit(widget_id)
