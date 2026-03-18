"""ChartArea — nested QMainWindow hosting ChartPanel(s) in a splitter + data docks."""

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout, QSplitter, QTabBar,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gandiva.widgets.chart_panel import ChartPanel, varga_display_name
from gandiva.widgets.data_panels import DATA_PANELS


class ChartArea(QMainWindow):
    """Central chart area with splitter for side-by-side views.

    Layout (central widget):
        VBoxLayout
          ├── _varga_tab_bar  (hidden until 2+ vargas or side-by-side active)
          └── _splitter
                ├── _primary_panel   (ChartPanel, always present)
                └── _secondary_panel (ChartPanel, created on demand)

    Dock widgets: data panels (Planets, Cusps, Nakshatras, Dashas, Kala, Panchanga)
    """

    varga_tab_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Make this behave as an embedded widget, not a top-level window
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockNestingEnabled(True)

        self._chart = None
        self._current_style = None
        self._current_theme = None

        # ── Central widget container ──────────────────────────────────────────
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Varga sub-tab bar (hidden until 2+ vargas or side-by-side active)
        self._varga_tab_bar = QTabBar()
        self._varga_tab_bar.setTabsClosable(True)
        self._varga_tab_bar.setExpanding(False)
        self._varga_tab_bar.setStyleSheet("""
            QTabBar::tab {
                font-size: 16px;
                padding: 8px 18px;
                color: #ccc;
            }
            QTabBar::tab:selected {
                color: #ccc;
            }
        """)
        self._varga_tab_bar.addTab("Rashi")
        self._varga_tab_bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self._varga_tab_bar.setVisible(False)
        self._varga_tab_bar.currentChanged.connect(self._on_varga_tab_changed)
        self._varga_tab_bar.tabCloseRequested.connect(self._on_varga_tab_close)
        central_layout.addWidget(self._varga_tab_bar)

        # None = rashi; int = varga number
        self._varga_tabs: list[int | None] = [None]

        # Splitter with primary panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._primary_panel = ChartPanel(show_header=False)
        self._primary_panel.clicked.connect(lambda: self.set_active_panel(0))
        self._splitter.addWidget(self._primary_panel)
        central_layout.addWidget(self._splitter)

        self._secondary_panel: ChartPanel | None = None
        self._active_panel_idx: int = 0

        self.setCentralWidget(central)

        # ── Data dock widgets ─────────────────────────────────────────────────
        self._docks: dict[str, tuple[QDockWidget, object]] = {}
        self._data_panels: dict[str, object] = {}

        for name, cls in DATA_PANELS.items():
            widget = cls()
            dock = QDockWidget(name, self)
            dock.setWidget(widget)
            dock.setObjectName(f"dock_{name}")  # required for saveState/restoreState
            dock.setAllowedAreas(
                Qt.DockWidgetArea.RightDockWidgetArea
                | Qt.DockWidgetArea.BottomDockWidgetArea
            )
            dock.setVisible(False)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._docks[name] = (dock, widget)
            self._data_panels[name] = widget

    # ── Backward-compat properties ────────────────────────────────────────────
    # MainWindow accesses chart_area.chart_scene in many places (signal connections,
    # overlay/widget operations).  Delegate to the primary panel.

    @property
    def chart_scene(self):
        return self._primary_panel.chart_scene

    @property
    def active_chart_scene(self):
        """Return the chart scene of the currently active (focused) panel."""
        return self.active_panel.chart_scene

    @property
    def chart_view(self):
        return self._primary_panel.chart_view

    # ── Chart update ──────────────────────────────────────────────────────────

    def set_chart(self, chart):
        """Set chart on panels and update all data panels."""
        self._chart = chart
        self._primary_panel.set_chart(chart, self._primary_panel.varga_number)
        if self._secondary_panel is not None:
            self._secondary_panel.set_chart(chart, self._secondary_panel.varga_number)
        for widget in self._data_panels.values():
            widget.update_from_chart(chart)

    def set_chart_style(self, style_name: str):
        """Change chart renderer style on all panels."""
        self._current_style = style_name
        self._primary_panel.set_chart_style(style_name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_chart_style(style_name)

    def set_theme(self, name: str):
        """Propagate theme to all panels."""
        self._current_theme = name
        self._primary_panel.set_theme(name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_theme(name)

    # ── Active panel ──────────────────────────────────────────────────────────

    @property
    def active_panel(self) -> ChartPanel:
        if self._active_panel_idx == 1 and self._secondary_panel is not None:
            return self._secondary_panel
        return self._primary_panel

    def set_active_panel(self, idx: int):
        self._active_panel_idx = idx
        self._primary_panel.set_active(idx == 0)
        if self._secondary_panel is not None:
            self._secondary_panel.set_active(idx == 1)
        if self._secondary_panel is None:
            self._primary_panel.set_active(False)

    # ── Varga sub-tab bar ─────────────────────────────────────────────────────

    def _update_tab_bar_visibility(self):
        visible = len(self._varga_tabs) > 1 or self._secondary_panel is not None
        self._varga_tab_bar.setVisible(visible)

    def open_varga_tab(self, varga_number: int):
        """Open (or switch to) a varga tab in the primary panel."""
        if varga_number in self._varga_tabs:
            idx = self._varga_tabs.index(varga_number)
            self._varga_tab_bar.setCurrentIndex(idx)
            return
        if self._chart is not None:
            name = varga_display_name(self._chart.context, varga_number)
        else:
            name = f"D-{abs(varga_number)}"
        self._varga_tabs.append(varga_number)
        self._varga_tab_bar.addTab(name)
        new_idx = len(self._varga_tabs) - 1
        self._varga_tab_bar.setCurrentIndex(new_idx)
        self._update_tab_bar_visibility()

    def _on_varga_tab_changed(self, index: int):
        if index < 0 or index >= len(self._varga_tabs):
            return
        varga_number = self._varga_tabs[index]
        if self._chart is not None:
            self.active_panel.set_chart(self._chart, varga_number)

    def _on_varga_tab_close(self, index: int):
        if index == 0:
            return  # Can't close Rashi
        varga_number = self._varga_tabs[index]
        self._varga_tabs.pop(index)
        self._varga_tab_bar.removeTab(index)
        if (
            self.active_panel.varga_number == varga_number
            and varga_number not in self._varga_tabs
        ):
            self.active_panel.set_chart(self._chart, None)
            self._varga_tab_bar.setCurrentIndex(0)
        self._update_tab_bar_visibility()

    # ── Side-by-side ──────────────────────────────────────────────────────────

    def open_side_by_side(self, varga_number: int):
        """Open (or update) a secondary panel with the given varga."""
        if self._secondary_panel is None:
            self._secondary_panel = ChartPanel(show_header=True)
            self._secondary_panel.clicked.connect(lambda: self.set_active_panel(1))
            self._secondary_panel.close_requested.connect(self.close_secondary_panel)
            self._splitter.addWidget(self._secondary_panel)
            if self._current_style:
                self._secondary_panel.set_chart_style(self._current_style)
            if self._current_theme:
                self._secondary_panel.set_theme(self._current_theme)
            # Show header on primary panel too
            self._primary_panel.set_header_visible(True)
        if self._chart is not None:
            self._secondary_panel.set_chart(self._chart, varga_number)
        # Equal split
        total = self._splitter.width()
        self._splitter.setSizes([total // 2, total // 2])
        if varga_number not in self._varga_tabs:
            if self._chart is not None:
                name = varga_display_name(self._chart.context, varga_number)
            else:
                name = f"D-{abs(varga_number)}"
            self._varga_tabs.append(varga_number)
            self._varga_tab_bar.addTab(name)
        self._update_tab_bar_visibility()

    def close_secondary_panel(self):
        """Remove and destroy the secondary panel."""
        if self._secondary_panel is None:
            return
        self._secondary_panel.setParent(None)
        self._secondary_panel.deleteLater()
        self._secondary_panel = None
        self._active_panel_idx = 0
        self._primary_panel.set_active(False)
        self._primary_panel.set_header_visible(False)
        self._update_tab_bar_visibility()

    # ── State save / restore ──────────────────────────────────────────────────

    def save_view_state(self) -> dict:
        """Return serialisable view state (varga tabs, splitter, active panel)."""
        return {
            "varga_tabs": list(self._varga_tabs),
            "active_panel": self._active_panel_idx,
            "side_by_side": (
                self._secondary_panel.varga_number
                if self._secondary_panel is not None
                else None
            ),
            "splitter_state": (
                self._splitter.saveState()
                if self._secondary_panel is not None
                else None
            ),
            "primary_varga": self._primary_panel.varga_number,
        }

    def restore_view_state(self, state: dict):
        """Restore view state from a dict previously returned by save_view_state."""
        if self._secondary_panel is not None:
            self.close_secondary_panel()

        self._varga_tab_bar.blockSignals(True)
        while self._varga_tab_bar.count() > 1:
            self._varga_tab_bar.removeTab(self._varga_tab_bar.count() - 1)
        self._varga_tabs = [None]

        for vn in state.get("varga_tabs", [None])[1:]:
            if self._chart is not None:
                name = varga_display_name(self._chart.context, vn)
            else:
                name = f"D-{abs(vn)}"
            self._varga_tabs.append(vn)
            self._varga_tab_bar.addTab(name)

        primary_varga = state.get("primary_varga")
        if self._chart is not None:
            self._primary_panel.set_chart(self._chart, primary_varga)

        if primary_varga in self._varga_tabs:
            idx = self._varga_tabs.index(primary_varga)
            self._varga_tab_bar.setCurrentIndex(idx)

        self._varga_tab_bar.blockSignals(False)

        side_varga = state.get("side_by_side")
        if side_varga is not None:
            self.open_side_by_side(side_varga)
            splitter_state = state.get("splitter_state")
            if splitter_state is not None:
                self._splitter.restoreState(splitter_state)

        self.set_active_panel(state.get("active_panel", 0))
        self._update_tab_bar_visibility()

    # ── Dock state (per chart tab) ────────────────────────────────────────────

    def save_dock_state(self):
        """Save dock widget layout as QByteArray."""
        return self.saveState()

    def restore_dock_state(self, state):
        """Restore dock widget layout from QByteArray."""
        if state is not None:
            self.restoreState(state)

    def dock_toggle_actions(self) -> dict:
        """Return {name: QAction} for toggling each dock's visibility."""
        return {name: dock.toggleViewAction() for name, (dock, _) in self._docks.items()}

    # ── Font size ─────────────────────────────────────────────────────────────

    def adjust_font(self, delta: int):
        """Propagate font size change to all data panels."""
        for widget in self._data_panels.values():
            widget.adjust_font(delta)
