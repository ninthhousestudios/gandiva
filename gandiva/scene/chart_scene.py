"""QGraphicsScene subclass that manages chart renderer, overlays, and info widgets."""

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsScene

from gandiva.glyph_renderer import clear_cache
from gandiva.info_widgets import INFO_WIDGETS
from gandiva.info_widgets.base import InfoWidget
from gandiva.overlays import OVERLAYS
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
        self._info_widgets: list = []  # List to support multiple instances
        self._widget_counter = 0  # Unique ID counter for widgets
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
        for widget in self._info_widgets:
            widget.set_theme(self._theme)

    def set_chart(self, chart) -> None:
        """Pass chart data to renderer and all scene items."""
        self._chart = chart
        if self._renderer:
            self._renderer.update_from_chart(chart)
        for overlay in self._overlays.values():
            overlay.update_from_chart(chart)
        for widget in self._info_widgets:
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
        if overlay_id in self._overlays:
            return  # already active
        overlay_class = OVERLAYS.get(overlay_id)
        if overlay_class is None:
            return

        overlay = overlay_class()
        z = self.Z_OVERLAY_BASE + len(self._overlays)
        overlay.setZValue(z)
        self.addItem(overlay)
        self._overlays[overlay_id] = overlay

        # Initialize with current state
        if self._rect.isValid():
            overlay.resize(self._rect)
        if self._theme:
            overlay.set_theme(self._theme)
        if self._chart:
            overlay.update_from_chart(self._chart)

        self.overlay_added.emit(overlay_id)

    def remove_overlay(self, overlay_id: str) -> None:
        """Remove an overlay by its registry ID."""
        if overlay_id in self._overlays:
            self.removeItem(self._overlays.pop(overlay_id))
            self.overlay_removed.emit(overlay_id)

    # ── info widget management ──────────────────────────────────────────────

    def _place_info_widget(self, widget: InfoWidget) -> None:
        """Place a new info widget in available space around the chart."""
        scene_rect = self._rect
        if not scene_rect.isValid():
            return

        # Widget size (use sizeHint from the embedded widget)
        w = widget.widget().width() if widget.widget() else 220
        h = widget.widget().sizeHint().height() if widget.widget() else 200

        margin = 10

        # Candidate positions: corners then edge midpoints
        candidates = [
            (margin, margin),  # top-left
            (scene_rect.width() - w - margin, margin),  # top-right
            (margin, scene_rect.height() - h - margin),  # bottom-left
            (
                scene_rect.width() - w - margin,
                scene_rect.height() - h - margin,
            ),  # bottom-right
            (scene_rect.width() / 2 - w / 2, margin),  # top-center
            (
                scene_rect.width() / 2 - w / 2,
                scene_rect.height() - h - margin,
            ),  # bottom-center
            (margin, scene_rect.height() / 2 - h / 2),  # mid-left
            (
                scene_rect.width() - w - margin,
                scene_rect.height() / 2 - h / 2,
            ),  # mid-right
        ]

        existing_rects = []
        for other in self._info_widgets:
            if other is not widget:
                existing_rects.append(other.sceneBoundingRect())

        for x, y in candidates:
            candidate_rect = QRectF(x, y, w, h)
            overlaps = any(candidate_rect.intersects(r) for r in existing_rects)
            if not overlaps:
                widget.setPos(x, y)
                return

        # Fallback: stack at bottom-right with offset
        offset = len(self._info_widgets) * 20
        widget.setPos(
            scene_rect.width() - w - margin - offset,
            scene_rect.height() - h - margin - offset,
        )

    def add_info_widget(self, widget_id: str) -> None:
        """Add an info widget by its registry ID. Multiple instances allowed."""
        entry = INFO_WIDGETS.get(widget_id)
        if entry is None:
            return

        widget_class, kwargs = entry

        # Generate unique instance ID
        self._widget_counter += 1
        instance_id = f"{widget_id}#{self._widget_counter}"

        # Create widget with unique ID
        widget = widget_class(widget_id=instance_id, title=widget_id, **kwargs)
        z = self.Z_WIDGET_BASE + len(self._info_widgets)
        widget.setZValue(z)
        widget.setAcceptHoverEvents(True)
        self.addItem(widget)
        self._info_widgets.append(widget)

        # Connect close signal - pass instance_id to remove the specific widget
        widget.closed.connect(lambda wid=instance_id: self._remove_widget_instance(wid))

        # Initialize with current state
        if self._theme:
            widget.set_theme(self._theme)
        if self._chart:
            widget.update_from_chart(self._chart)

        # Auto-place
        self._place_info_widget(widget)

        self.widget_added.emit(widget_id)

    def _remove_widget_instance(self, instance_id: str) -> None:
        """Remove a specific widget instance by its unique ID."""
        for widget in self._info_widgets[
            :
        ]:  # Copy list to safely modify during iteration
            if widget.widget_id == instance_id:
                self.removeItem(widget)
                self._info_widgets.remove(widget)
                # Extract base widget_id for the signal (everything before #)
                base_id = instance_id.split("#")[0]
                self.widget_removed.emit(base_id)
                break

    def remove_info_widget(self, widget_id: str) -> None:
        """Remove all info widgets of a given registry ID."""
        to_remove = [
            w for w in self._info_widgets if w.widget_id.startswith(f"{widget_id}#")
        ]
        for widget in to_remove:
            self.removeItem(widget)
            self._info_widgets.remove(widget)
        if to_remove:
            self.widget_removed.emit(widget_id)

    def get_widget_states(self) -> list[dict]:
        """Serialize all current widget states for saving per-chart.

        Returns list of widget states with: widget_id, pos, minimized, options
        """
        states = []
        for widget in self._info_widgets:
            state = {
                "widget_id": widget.widget_id,
                "base_id": widget.widget_id.split("#")[0],
                "pos": {"x": widget.pos().x(), "y": widget.pos().y()},
                "minimized": getattr(widget, "_minimized", False),
            }
            # Capture widget-specific options if available
            if hasattr(widget, "_levels"):
                state["levels"] = widget._levels
            if hasattr(widget, "_highlight_current"):
                state["highlight_current"] = widget._highlight_current
            states.append(state)
        return states

    def restore_widget_states(self, states: list[dict]) -> None:
        """Restore widgets from saved states."""
        # Clear current widgets first
        self.clear_all_widgets()

        # Restore each widget
        for state in states:
            widget_id = state.get("base_id")
            if widget_id is None:
                continue

            entry = INFO_WIDGETS.get(widget_id)
            if entry is None:
                continue

            widget_class, kwargs = entry

            # Generate new unique instance ID
            self._widget_counter += 1
            instance_id = f"{widget_id}#{self._widget_counter}"

            # Create widget
            widget = widget_class(widget_id=instance_id, title=widget_id, **kwargs)
            z = self.Z_WIDGET_BASE + len(self._info_widgets)
            widget.setZValue(z)
            widget.setAcceptHoverEvents(True)
            self.addItem(widget)
            self._info_widgets.append(widget)

            # Restore position
            pos = state.get("pos", {})
            widget.setPos(pos.get("x", 10), pos.get("y", 10))

            # Restore minimized state
            if state.get("minimized") and hasattr(widget, "_toggle_minimize"):
                widget._minimized = False  # Start not minimized
                widget._toggle_minimize()  # Toggle to minimized

            # Restore widget-specific options
            if hasattr(widget, "_levels") and "levels" in state:
                widget._levels = state["levels"]
                # Update button states if the widget has level buttons
                if hasattr(widget, "_level_buttons"):
                    for i, btn in widget._level_buttons.items():
                        btn.setChecked(i == state["levels"])

            if hasattr(widget, "_highlight_current") and "highlight_current" in state:
                widget._highlight_current = state["highlight_current"]

            # Connect close signal
            widget.closed.connect(
                lambda wid=instance_id: self._remove_widget_instance(wid)
            )

            # Initialize with current state
            if self._theme:
                widget.set_theme(self._theme)
            if self._chart:
                widget.update_from_chart(self._chart)

            self.widget_added.emit(widget_id)

    def clear_all_widgets(self) -> None:
        """Remove all info widgets from the scene."""
        for widget in self._info_widgets[:]:
            self.removeItem(widget)
        self._info_widgets.clear()
