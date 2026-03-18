from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QTabBar,
    QToolButton,
    QLabel,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QShortcut, QKeySequence

from gandiva.widgets.left_panel import LeftPanel
from gandiva.widgets.chart_area import ChartArea
from gandiva.widgets.chart_panel import ChartPanel, varga_display_name
from gandiva.widgets.data_panels import DATA_PANELS
from gandiva.themes import get_theme, DEFAULT_THEME, make_app_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gandiva — libaditya")
        self.resize(1200, 700)

        # ── chart registry ────────────────────────────────────────────────────
        self._charts: list[dict] = []
        self._current_idx: int = -1

        # ── chart tab bar (hidden until 2+ charts) ────────────────────────────
        self.chart_tab_bar = QTabBar()
        self.chart_tab_bar.setTabsClosable(True)
        self.chart_tab_bar.setMovable(True)
        self.chart_tab_bar.setExpanding(False)
        self.chart_tab_bar.setVisible(False)
        self.chart_tab_bar.currentChanged.connect(self._on_chart_tab_changed)
        self.chart_tab_bar.tabCloseRequested.connect(self._on_chart_tab_close)

        # ── left panel ───────────────────────────────────────────────────────
        self.left_panel = LeftPanel()

        # ── chart area (nested QMainWindow with docks) ───────────────────────
        self.chart_area = ChartArea()

        # ── right tab bar (dock toggles, mirrors left panel tab bar) ────────
        self.right_tab_bar = QTabBar()
        self.right_tab_bar.setShape(QTabBar.Shape.RoundedEast)
        self._dock_names = list(DATA_PANELS.keys())
        for i, name in enumerate(self._dock_names):
            self.right_tab_bar.addTab(name)
            self.right_tab_bar.setTabToolTip(i, name)
        self.right_tab_bar.setCurrentIndex(-1)  # nothing selected initially
        self.right_tab_bar.tabBarClicked.connect(self._on_right_tab_clicked)

        # Sync tab bar when docks are closed via their own close button
        for name in self._dock_names:
            dock, _ = self.chart_area._docks[name]
            dock.visibilityChanged.connect(
                lambda visible, n=name: self._on_dock_visibility_changed(n, visible)
            )

        # Wire Vargas dock signals
        vargas = self.chart_area._data_panels.get("Vargas")
        if vargas is not None:
            vargas.varga_pop_out.connect(self.pop_out_varga)
            vargas.varga_make_main.connect(self.chart_area.open_varga_tab)
            vargas.varga_side_by_side.connect(self.chart_area.open_side_by_side)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(
            lambda: self._adjust_fonts(+1)
        )
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(
            lambda: self._adjust_fonts(-1)
        )
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(
            lambda: self._adjust_fonts(0)
        )

        # ── left panel signal wiring ────────────────────────────────────────
        self.left_panel.chart_created.connect(self.on_chart_created)
        self.left_panel.overlay_toggled.connect(self._on_overlay_toggled)
        self.left_panel.spawn_widget.connect(self._on_spawn_widget)
        self.left_panel.theme_changed.connect(self._on_theme_changed)
        self.left_panel.chart_style_changed.connect(self._on_chart_style_changed)
        self.left_panel.display_options_changed.connect(
            self._on_display_options_changed
        )
        self.chart_area.chart_scene.overlay_removed.connect(
            self.left_panel.on_overlay_removed
        )
        self.chart_area.chart_scene.widget_removed.connect(self._on_widget_removed)

        # ── layout: [left_tab_bar | left_panel | chart_area | right_tab_bar] ──
        content_row = QWidget()
        cr_layout = QHBoxLayout(content_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(0)
        cr_layout.addWidget(self.left_panel.tab_bar)
        cr_layout.addWidget(self.left_panel)
        cr_layout.addWidget(self.chart_area, stretch=1)
        cr_layout.addWidget(self.right_tab_bar)

        # ── root layout: chart tabs on top, content row below ─────────────────
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.chart_tab_bar)
        root_layout.addWidget(content_row, stretch=1)
        self.setCentralWidget(root)

        # ── theme ─────────────────────────────────────────────────────────────
        saved_theme = QSettings("gandiva", "gandiva").value("theme", DEFAULT_THEME)
        self.left_panel.theme_combo.blockSignals(True)
        self.left_panel.theme_combo.setCurrentText(saved_theme)
        self.left_panel.theme_combo.blockSignals(False)
        self._apply_theme(saved_theme)

        # ── initial chart style + calculate ───────────────────────────────────
        self.chart_area.set_chart_style("Western Wheel")
        self.left_panel.calculate()

    # ── chart display ─────────────────────────────────────────────────────────

    def _display_chart(self, chart):
        self.chart_area.set_chart(chart)

    # ── called when chart is calculated ───────────────────────────────────────

    def on_chart_created(self, chart):
        new_key = self.left_panel.get_birth_key()
        birth_state = self.left_panel.get_birth_state()
        label = chart.context.name.strip() or f"Chart {len(self._charts) + 1}"
        options_state = self.left_panel.get_options_state()

        is_same_key = (
            self._current_idx >= 0
            and self._charts[self._current_idx]["key"] == new_key
        )

        if is_same_key:
            # Same birth info — recalculate (display options changed), update tab
            self._charts[self._current_idx]["widgets"] = (
                self.chart_area.chart_scene.get_widget_states()
            )
            view_state = self.chart_area.save_view_state()
            self._charts[self._current_idx].update(
                {
                    "chart": chart,
                    "state": birth_state,
                    "options": options_state,
                    "dock_state": self.chart_area.save_dock_state(),
                    "view_state": view_state,
                }
            )
            self.chart_tab_bar.setTabText(self._current_idx, label)
        else:
            # New birth info — open in a new tab
            if self._current_idx >= 0:
                self._charts[self._current_idx]["widgets"] = (
                    self.chart_area.chart_scene.get_widget_states()
                )
                self._charts[self._current_idx]["dock_state"] = (
                    self.chart_area.save_dock_state()
                )
                self._charts[self._current_idx]["view_state"] = (
                    self.chart_area.save_view_state()
                )

            self._charts.append(
                {
                    "chart": chart,
                    "key": new_key,
                    "state": birth_state,
                    "options": options_state,
                    "widgets": [],
                    "dock_state": self.chart_area.save_dock_state(),
                    "view_state": None,
                    "popouts": [],
                }
            )
            self.chart_tab_bar.blockSignals(True)
            new_index = self.chart_tab_bar.addTab(label)
            self._add_tab_popout_button(new_index)
            self._current_idx = len(self._charts) - 1
            self.chart_tab_bar.setCurrentIndex(self._current_idx)
            self.chart_tab_bar.blockSignals(False)
            self._refresh_tab_bar()

        self._display_chart(chart)
        entry = self._charts[self._current_idx]
        for popout in entry.get("popouts", []):
            popout["panel"].set_chart(chart, popout["varga"])

        if is_same_key:
            # Same chart recalculated — preserve view state, just refresh widgets
            self.chart_area.chart_scene.clear_all_widgets()
            if entry.get("widgets"):
                self.chart_area.chart_scene.restore_widget_states(entry["widgets"])
            # Restore varga view (tabs, side-by-side) after _display_chart reset
            self.chart_area.restore_view_state(entry["view_state"])
        else:
            # New chart — clean slate
            self.chart_area.chart_scene.clear_all_widgets()
            for oid in list(self.chart_area.chart_scene._overlays.keys()):
                self.chart_area.chart_scene.remove_overlay(oid)
            self.left_panel.uncheck_all_overlays()
            self.chart_area.restore_view_state({
                "varga_tabs": [None],
                "active_panel": 0,
                "side_by_side": None,
                "splitter_state": None,
                "primary_varga": None,
            })

    # ── tab bar events ────────────────────────────────────────────────────────

    def _on_chart_tab_changed(self, index):
        if 0 <= index < len(self._charts):
            if 0 <= self._current_idx < len(self._charts):
                self._charts[self._current_idx]["widgets"] = (
                    self.chart_area.chart_scene.get_widget_states()
                )
                self._charts[self._current_idx]["options"] = (
                    self.left_panel.get_options_state()
                )
                self._charts[self._current_idx]["dock_state"] = (
                    self.chart_area.save_dock_state()
                )
                self._charts[self._current_idx]["view_state"] = (
                    self.chart_area.save_view_state()
                )

            self._current_idx = index
            entry = self._charts[index]
            self.left_panel.set_birth_state(entry["state"])

            if entry.get("options"):
                self.left_panel.set_options_state(entry["options"])

            # Restore dock layout
            self.chart_area.restore_dock_state(entry.get("dock_state"))

            self.chart_area.chart_scene.clear_all_widgets()
            if entry.get("widgets"):
                self.chart_area.chart_scene.restore_widget_states(entry["widgets"])

            self._display_chart(entry["chart"])

            view_state = entry.get("view_state")
            if view_state is not None:
                self.chart_area.restore_view_state(view_state)
            else:
                self.chart_area.restore_view_state({
                    "varga_tabs": [None],
                    "active_panel": 0,
                    "side_by_side": None,
                    "splitter_state": None,
                    "primary_varga": None,
                })

    def _on_chart_tab_close(self, index):
        if len(self._charts) <= 1:
            return

        if index == self._current_idx:
            self.chart_area.chart_scene.clear_all_widgets()

        entry = self._charts[index]
        for popout in entry.get("popouts", []):
            popout["window"].close()
        self._charts.pop(index)
        self.chart_tab_bar.removeTab(index)
        self._current_idx = self.chart_tab_bar.currentIndex()
        self._refresh_tab_bar()
        if 0 <= self._current_idx < len(self._charts):
            entry = self._charts[self._current_idx]
            self.left_panel.set_birth_state(entry["state"])
            if entry.get("options"):
                self.left_panel.set_options_state(entry["options"])
            self.chart_area.restore_dock_state(entry.get("dock_state"))
            self.chart_area.chart_scene.clear_all_widgets()
            if entry.get("widgets"):
                self.chart_area.chart_scene.restore_widget_states(entry["widgets"])
            self._display_chart(entry["chart"])

    def _refresh_tab_bar(self):
        self.chart_tab_bar.setVisible(len(self._charts) > 1)

    def _add_tab_popout_button(self, tab_index: int):
        btn = QToolButton()
        btn.setText("\u2b0d")  # ⬍
        btn.setFixedSize(16, 16)
        btn.setAutoRaise(True)
        btn.setStyleSheet("font-size: 10px; color: #aaa;")
        entry = self._charts[tab_index]
        btn.clicked.connect(lambda: self._pop_out_chart_entry(entry))
        self.chart_tab_bar.setTabButton(
            tab_index, QTabBar.ButtonPosition.RightSide, btn
        )

    def _pop_out_chart_entry(self, entry: dict):
        chart = entry["chart"]
        if chart is None:
            return
        varga_number = self.chart_area.active_panel.varga_number

        chart_label = chart.context.name.strip() or entry.get("key", "Chart")
        if varga_number is not None:
            title = f"{chart_label} \u2014 {varga_display_name(chart.context, varga_number)}"
        else:
            title = chart_label

        window = self._make_popout_window(chart, varga_number, title)

        entry.setdefault("popouts", []).append(
            {"window": window, "panel": window._chart_panel, "varga": varga_number}
        )
        window.destroyed.connect(lambda: self._remove_popout(entry, window))

    def _make_popout_window(self, chart, varga_number, title: str):
        """Create a pop-out window with a header label and chart panel."""
        panel = ChartPanel(show_header=False)
        panel.set_chart(chart, varga_number)
        if self.chart_area._current_style:
            panel.set_chart_style(self.chart_area._current_style)
        if self.chart_area._current_theme:
            panel.set_theme(self.chart_area._current_theme)

        window = QWidget()
        window.setWindowFlags(Qt.WindowType.Window)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size: 13px; color: #ccc; padding: 4px; background: #1a1a2a;"
        )
        layout.addWidget(header)
        layout.addWidget(panel, stretch=1)

        window.setWindowTitle(title)
        window.resize(500, 500)
        window.show()

        # Stash panel ref on the window for popout tracking
        window._chart_panel = panel
        return window

    def _remove_popout(self, entry, window):
        entry["popouts"] = [
            p for p in entry.get("popouts", []) if p["window"] is not window
        ]

    def pop_out_varga(self, varga_number: int):
        if self._current_idx < 0:
            return
        entry = self._charts[self._current_idx]
        chart = entry["chart"]
        if chart is None:
            return

        chart_label = chart.context.name.strip() or entry.get("key", "Chart")
        title = f"{chart_label} \u2014 {varga_display_name(chart.context, varga_number)}"

        window = self._make_popout_window(chart, varga_number, title)

        entry.setdefault("popouts", []).append(
            {"window": window, "panel": window._chart_panel, "varga": varga_number}
        )
        window.destroyed.connect(lambda: self._remove_popout(entry, window))

    # ── font size ──────────────────────────────────────────────────────────────

    def _adjust_fonts(self, delta: int):
        self.left_panel.adjust_font(delta)
        self.chart_area.adjust_font(delta)

    # ── right tab bar (dock toggles) ────────────────────────────────────────

    def _on_right_tab_clicked(self, index):
        """Toggle the corresponding dock widget on click (one at a time)."""
        if 0 <= index < len(self._dock_names):
            name = self._dock_names[index]
            dock, _ = self.chart_area._docks[name]
            if dock.isVisible():
                dock.hide()
                self.right_tab_bar.setCurrentIndex(-1)
            else:
                # Hide all other docks first
                for other_name in self._dock_names:
                    other_dock, _ = self.chart_area._docks[other_name]
                    if other_dock.isVisible():
                        other_dock.hide()
                dock.show()
                dock.raise_()

    def _on_dock_visibility_changed(self, name: str, visible: bool):
        """Deselect right tab bar when no docks are visible."""
        # If no dock is visible, clear the tab selection
        if not visible:
            any_visible = any(
                d.isVisible() for d, _ in self.chart_area._docks.values()
            )
            if not any_visible:
                self.right_tab_bar.setCurrentIndex(-1)

    # ── theme ──────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, name: str):
        self._apply_theme(name)

    def _apply_theme(self, name: str):
        QSettings("gandiva", "gandiva").setValue("theme", name)
        theme = get_theme(name)
        QApplication.instance().setStyleSheet(make_app_stylesheet(theme))
        self.chart_area.set_theme(name)
        # Update pop-out themes
        for entry in self._charts:
            for popout in entry.get("popouts", []):
                popout["panel"].set_theme(name)

    # ── display options changed → recalculate ─────────────────────────────────

    def _on_display_options_changed(self):
        self.left_panel.calculate()

    # ── widget/overlay management ──────────────────────────────────────────────

    def _on_widget_removed(self, widget_id: str):
        if self._current_idx >= 0 and self._current_idx < len(self._charts):
            self._charts[self._current_idx]["widgets"] = (
                self.chart_area.chart_scene.get_widget_states()
            )

    def _on_chart_style_changed(self, style_name: str):
        self.chart_area.set_chart_style(style_name)
        self.left_panel.uncheck_all_overlays()
        # Update pop-out chart styles
        entry = self._charts[self._current_idx]
        for popout in entry.get("popouts", []):
            popout["panel"].set_chart_style(style_name)

    def _on_overlay_toggled(self, overlay_id: str, checked: bool):
        scene = self.chart_area.active_chart_scene
        if checked:
            scene.add_overlay(overlay_id)
        else:
            scene.remove_overlay(overlay_id)

    def _on_spawn_widget(self, widget_type: str):
        widget_id_map = {
            "Nakshatra Dashas": "Nakshatra Dashas",
            "Vargas": "Varga",
            "Rashi Dashas": "Rashi Dashas",
            "Panchanga": "Panchanga",
        }

        widget_id = widget_id_map.get(widget_type, "Panchanga")
        self.chart_area.active_chart_scene.add_info_widget(widget_id)

        if self._current_idx >= 0 and self._current_idx < len(self._charts):
            self._charts[self._current_idx]["widgets"] = (
                self.chart_area.chart_scene.get_widget_states()
            )
