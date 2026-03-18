from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QApplication,
    QTabBar,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QShortcut, QKeySequence

from gandiva.widgets.chart_input import ChartInputPanel
from gandiva.widgets.left_panel import LeftPanel
from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView
from gandiva.themes import get_theme, DEFAULT_THEME, make_app_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gandiva — libaditya")
        self.resize(1200, 700)

        # ── chart registry ────────────────────────────────────────────────────
        # Each entry: {"chart": Chart, "key": birth_key, "state": birth_state}
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

        # ── left panel ────────────────────────────────────────────────────────
        self.input_panel = ChartInputPanel()
        self.input_panel.chart_created.connect(self.on_chart_created)
        self.input_panel.theme_changed.connect(self._on_theme_changed)
        self.input_panel.no_changes.connect(self._on_no_changes)
        self.input_panel.chart_style_changed.connect(self._on_chart_style_changed)

        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(
            lambda: self._adjust_fonts(+1)
        )
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(
            lambda: self._adjust_fonts(-1)
        )
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(
            lambda: self._adjust_fonts(0)
        )

        # ── center: chart scene + view ───────────────────────────────────────
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        self.chart_scene.set_chart_style("Western Wheel")

        # ── left panel: overlay/widget toggles ─────────────────────────────
        self.left_panel = LeftPanel()

        # ── splitter: left panel + chart view + input panel ────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.chart_view)
        self.splitter.addWidget(self.input_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.input_panel.splitter = self.splitter
        self.left_panel.splitter = self.splitter

        # ── left panel signal wiring ────────────────────────────────────────
        self.left_panel.overlay_toggled.connect(self._on_overlay_toggled)
        self.left_panel.spawn_widget.connect(self._on_spawn_widget)
        self.left_panel.calculate_requested.connect(self._on_calculate_requested)
        self.left_panel.theme_changed.connect(self._on_theme_changed)
        self.left_panel.chart_style_changed.connect(self._on_chart_style_changed)
        self.left_panel.display_options_changed.connect(
            self._on_display_options_changed
        )
        self.chart_scene.overlay_removed.connect(self.left_panel.on_overlay_removed)
        self.chart_scene.widget_removed.connect(self._on_widget_removed)

        # ── tab bars live outside the splitter so they're always visible ────
        splitter = self.splitter
        left_tab_bar = self.left_panel.tab_bar
        sidebar_tab_bar = self.input_panel.tab_bar
        content_row = QWidget()
        cr_layout = QHBoxLayout(content_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(0)
        cr_layout.addWidget(left_tab_bar)
        cr_layout.addWidget(splitter, stretch=1)
        cr_layout.addWidget(sidebar_tab_bar)

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
        self.input_panel.theme_combo.blockSignals(True)
        self.input_panel.theme_combo.setCurrentText(saved_theme)
        self.input_panel.theme_combo.blockSignals(False)
        self._apply_theme(saved_theme)

        # ── initial chart ─────────────────────────────────────────────────────
        self.input_panel.calculate()

        # ── set initial splitter sizes after layout is ready ─────────────────
        from gandiva.widgets.chart_input import EXPANDED_WIDTH
        from gandiva.widgets.left_panel import PANEL_WIDTH

        # Start with right panel collapsed
        self.input_panel.setVisible(False)
        self.input_panel.setFixedWidth(0)
        self.input_panel._expanded = False
        self.splitter.setSizes([PANEL_WIDTH, self.width() - PANEL_WIDTH - 1, 1])

    # ── chart display ─────────────────────────────────────────────────────────

    def _display_chart(self, chart):
        self.chart_scene.set_chart(chart)
        self.input_panel.update_info(chart)

    # ── called by ChartInputPanel when Calculate is pressed ───────────────────

    def on_chart_created(self, chart):
        new_key = self.input_panel.get_birth_key()
        birth_state = self.input_panel.get_birth_state()
        label = chart.context.name.strip() or f"Chart {len(self._charts) + 1}"

        options_state = self.left_panel.get_options_state()

        if self._current_idx >= 0 and self._charts[self._current_idx]["key"] == new_key:
            # Same birth info — recalculate (display options changed), update tab
            # Save current widget state first
            self._charts[self._current_idx]["widgets"] = (
                self.chart_scene.get_widget_states()
            )
            self._charts[self._current_idx].update(
                {"chart": chart, "state": birth_state, "options": options_state}
            )
            self.chart_tab_bar.setTabText(self._current_idx, label)
        else:
            # New birth info — open in a new tab
            # Save current chart's widgets before switching
            if self._current_idx >= 0:
                self._charts[self._current_idx]["widgets"] = (
                    self.chart_scene.get_widget_states()
                )

            # Create new chart entry with empty widget list
            self._charts.append(
                {
                    "chart": chart,
                    "key": new_key,
                    "state": birth_state,
                    "options": options_state,
                    "widgets": [],  # Start with no widgets for new chart
                }
            )
            self.chart_tab_bar.blockSignals(True)
            self.chart_tab_bar.addTab(label)
            self._current_idx = len(self._charts) - 1
            self.chart_tab_bar.setCurrentIndex(self._current_idx)
            self.chart_tab_bar.blockSignals(False)
            self._refresh_tab_bar()

        self._display_chart(chart)
        # Clear widgets and restore for this chart (new charts start empty)
        self.chart_scene.clear_all_widgets()
        if self._charts[self._current_idx].get("widgets"):
            self.chart_scene.restore_widget_states(
                self._charts[self._current_idx]["widgets"]
            )

    # ── tab bar events ────────────────────────────────────────────────────────

    def _on_chart_tab_changed(self, index):
        if 0 <= index < len(self._charts):
            # Save current chart's state before switching
            if self._current_idx >= 0 and self._current_idx < len(self._charts):
                self._charts[self._current_idx]["widgets"] = (
                    self.chart_scene.get_widget_states()
                )
                self._charts[self._current_idx]["options"] = (
                    self.left_panel.get_options_state()
                )

            # Switch to new chart
            self._current_idx = index
            entry = self._charts[index]
            self.input_panel.set_birth_state(entry["state"])

            # Restore calc/display options to left panel
            if entry.get("options"):
                self.left_panel.set_options_state(entry["options"])

            # Restore this chart's widgets
            self.chart_scene.clear_all_widgets()
            if entry.get("widgets"):
                self.chart_scene.restore_widget_states(entry["widgets"])

            self._display_chart(entry["chart"])

    def _on_chart_tab_close(self, index):
        if len(self._charts) <= 1:
            return

        # Clear widgets if closing current tab
        if index == self._current_idx:
            self.chart_scene.clear_all_widgets()

        self._charts.pop(index)
        self.chart_tab_bar.removeTab(index)
        self._current_idx = self.chart_tab_bar.currentIndex()
        self._refresh_tab_bar()
        if 0 <= self._current_idx < len(self._charts):
            entry = self._charts[self._current_idx]
            self.input_panel.set_birth_state(entry["state"])
            if entry.get("options"):
                self.left_panel.set_options_state(entry["options"])
            # Restore widgets for the now-active chart
            self.chart_scene.clear_all_widgets()
            if entry.get("widgets"):
                self.chart_scene.restore_widget_states(entry["widgets"])
            self._display_chart(entry["chart"])

    def _refresh_tab_bar(self):
        self.chart_tab_bar.setVisible(len(self._charts) > 1)

    # ── no changes notification ────────────────────────────────────────────

    def _adjust_fonts(self, delta: int):
        """Adjust font size in both side panels."""
        self.input_panel.adjust_font(delta)
        self.left_panel.adjust_font(delta)

    def _on_no_changes(self):
        self.statusBar().showMessage("No changes to calculate", 3000)

    # ── theme ─────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, name: str):
        self._apply_theme(name)

    def _apply_theme(self, name: str):
        QSettings("gandiva", "gandiva").setValue("theme", name)
        theme = get_theme(name)
        QApplication.instance().setStyleSheet(make_app_stylesheet(theme))
        self.chart_scene.set_theme(name)

    def _on_calculate_requested(self):
        """Called when Calculate button clicked in left panel."""
        # Copy values from left panel to right panel and calculate
        self.input_panel.name_edit.setText(self.left_panel.name_edit.text())
        self.input_panel.date_edit.setDate(self.left_panel.date_edit.date())
        self.input_panel.time_edit.setTime(self.left_panel.time_edit.time())
        self.input_panel.utcoffset_spin.setValue(self.left_panel.utcoffset_spin.value())
        self.input_panel.placename_edit.setText(self.left_panel.placename_edit.text())
        self.input_panel.lat_spin.setValue(self.left_panel.lat_spin.value())
        self.input_panel.long_spin.setValue(self.left_panel.long_spin.value())
        self.input_panel.zodiac_combo.setCurrentText(
            self.left_panel.zodiac_combo.currentText()
        )
        self.input_panel.ayanamsa_spin.setValue(self.left_panel.ayanamsa_spin.value())
        self.input_panel.hsys_combo.setCurrentText(
            self.left_panel.hsys_combo.currentText()
        )
        self.input_panel.chart_style_combo.setCurrentText(
            self.left_panel.chart_style_combo.currentText()
        )
        # Calc Options - Jaimini
        self.input_panel.rashi_temp_friend_check.setChecked(
            self.left_panel.rashi_temp_friend_check.isChecked()
        )
        self.input_panel.rashi_aspects_combo.setCurrentText(
            self.left_panel.rashi_aspects_combo.currentText()
        )
        # Calc Options - Human Design
        self.input_panel.hd_gate_one_spin.setValue(
            self.left_panel.hd_gate_one_spin.value()
        )
        # Calc Options - Cards of Truth
        self.input_panel.cot_savana_day_check.setChecked(
            self.left_panel.cot_savana_day_check.isChecked()
        )
        self.input_panel.cot_planet_order_combo.setCurrentText(
            self.left_panel.cot_planet_order_combo.currentText()
        )
        # Display Options
        self.input_panel.signize_check.setChecked(
            self.left_panel.signize_check.isChecked()
        )
        self.input_panel.toround_check.setChecked(
            self.left_panel.toround_check.isChecked()
        )
        self.input_panel.toround_places_spin.setValue(
            self.left_panel.toround_places_spin.value()
        )
        self.input_panel.print_nakshatras_check.setChecked(
            self.left_panel.print_nakshatras_check.isChecked()
        )
        self.input_panel.print_outer_planets_check.setChecked(
            self.left_panel.print_outer_planets_check.isChecked()
        )
        self.input_panel.hd_print_hexagrams_check.setChecked(
            self.left_panel.hd_print_hexagrams_check.isChecked()
        )
        self.input_panel.theme_combo.setCurrentText(
            self.left_panel.theme_combo.currentText()
        )
        self.input_panel.calculate()

    def _on_display_options_changed(self):
        """Called when display options (signize, toround, print_outer_planets, etc.) change.

        Recalculates the chart with the new display settings.
        """
        # Copy display option values from left panel to right panel
        self.input_panel.signize_check.setChecked(
            self.left_panel.signize_check.isChecked()
        )
        self.input_panel.toround_check.setChecked(
            self.left_panel.toround_check.isChecked()
        )
        self.input_panel.toround_places_spin.setValue(
            self.left_panel.toround_places_spin.value()
        )
        self.input_panel.print_nakshatras_check.setChecked(
            self.left_panel.print_nakshatras_check.isChecked()
        )
        self.input_panel.print_outer_planets_check.setChecked(
            self.left_panel.print_outer_planets_check.isChecked()
        )
        self.input_panel.hd_print_hexagrams_check.setChecked(
            self.left_panel.hd_print_hexagrams_check.isChecked()
        )
        # Recalculate with new display options
        self.input_panel.calculate()

    def _on_widget_removed(self, widget_id: str):
        """Called when a widget is closed/removed from the scene.

        Updates the current chart's widget state to reflect the removal.
        """
        # Save the updated widget state (the widget is already removed from scene)
        if self._current_idx >= 0 and self._current_idx < len(self._charts):
            self._charts[self._current_idx]["widgets"] = (
                self.chart_scene.get_widget_states()
            )

    def _on_chart_style_changed(self, style_name: str):
        """Called when chart style is changed in the left panel."""
        self.chart_scene.set_chart_style(style_name)
        self.left_panel.uncheck_all_overlays()

    def _on_overlay_toggled(self, overlay_id: str, checked: bool):
        """Called when an overlay is toggled on/off."""
        if checked:
            self.chart_scene.add_overlay(overlay_id)
        else:
            self.chart_scene.remove_overlay(overlay_id)

    def _on_spawn_widget(self, widget_type: str):
        """Called when user clicks the spawn button for a widget type.

        Creates a new widget of the specified type on the chart surface.
        Multiple widgets of the same type can be spawned.
        """
        # Map left panel widget type names to INFO_WIDGETS registry keys
        widget_id_map = {
            "Nakshatra Dashas": "Nakshatra Dashas",
            "Vargas": "Varga",
            "Rashi Dashas": "Rashi Dashas",  # Placeholder for future implementation
            "Panchanga": "Panchanga",
        }

        widget_id = widget_id_map.get(widget_type, "Panchanga")
        self.chart_scene.add_info_widget(widget_id)

        # Save the updated widget state to the current chart
        if self._current_idx >= 0 and self._current_idx < len(self._charts):
            self._charts[self._current_idx]["widgets"] = (
                self.chart_scene.get_widget_states()
            )
