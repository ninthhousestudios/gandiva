"""ChartArea — nested QMainWindow hosting chart view and data dock widgets."""

from PyQt6.QtWidgets import QMainWindow, QDockWidget
from PyQt6.QtCore import Qt

from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView
from gandiva.widgets.data_panels import DATA_PANELS


class ChartArea(QMainWindow):
    """Nested QMainWindow used as a widget inside the outer MainWindow.

    Central widget: ChartView (primary chart)
    Dock widgets: data panels (Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Critical: make this behave as an embedded widget, not a top-level window
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockNestingEnabled(True)

        # ── chart scene + view (central widget) ──────────────────────────────
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        self.setCentralWidget(self.chart_view)

        # ── data dock widgets ────────────────────────────────────────────────
        self._docks: dict[str, tuple[QDockWidget, object]] = {}
        self._data_panels: dict[str, object] = {}

        for name, widget_cls in DATA_PANELS.items():
            widget = widget_cls()
            dock = QDockWidget(name, self)
            dock.setWidget(widget)
            dock.setObjectName(f"dock_{name}")  # required for saveState/restoreState
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            dock.hide()  # start with all docks closed

            self._docks[name] = (dock, widget)
            self._data_panels[name] = widget

    # ── chart management ──────────────────────────────────────────────────────

    def set_chart(self, chart):
        """Set chart on scene and update all data panels."""
        self.chart_scene.set_chart(chart)
        for widget in self._data_panels.values():
            widget.update_from_chart(chart)

    def set_chart_style(self, style_name: str):
        """Change chart renderer style."""
        self.chart_scene.set_chart_style(style_name)

    def set_theme(self, name: str):
        """Propagate theme to scene."""
        self.chart_scene.set_theme(name)

    # ── dock state (per chart tab) ────────────────────────────────────────────

    def save_dock_state(self):
        """Save dock widget layout as QByteArray."""
        return self.saveState()

    def restore_dock_state(self, state):
        """Restore dock widget layout from QByteArray."""
        if state:
            self.restoreState(state)

    # ── dock visibility ───────────────────────────────────────────────────────

    def dock_toggle_actions(self):
        """Return list of QActions for toggling dock visibility (for View menu)."""
        return [dock.toggleViewAction() for dock, _ in self._docks.values()]

    # ── font size ─────────────────────────────────────────────────────────────

    def adjust_font(self, delta: int):
        """Propagate font size change to all data panels."""
        for widget in self._data_panels.values():
            widget.adjust_font(delta)
