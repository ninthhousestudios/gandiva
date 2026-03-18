"""Left panel with chart config tabs, overlay and widget toggle checkboxes."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabBar,
    QStackedWidget,
    QCheckBox,
    QLabel,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QDateEdit,
    QTimeEdit,
    QGroupBox,
    QPushButton,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    pyqtSignal,
    QDateTime,
    QDate,
    QTime,
    QSettings,
)
from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    pyqtSignal,
    QDateTime,
    QDate,
    QTime,
    QSettings,
)
from PyQt6.QtGui import QFont

from libaditya.read import read_chtk, read_chtk_location
from gandiva.overlays import OVERLAYS
from gandiva.info_widgets import INFO_WIDGETS


PANEL_WIDTH = 220
ANIM_DURATION_MS = 220
DEFAULT_FONT_SIZE = 16

# Tab indices
_TAB_CHART_INFO = 0
_TAB_CALC_OPTIONS = 1
_TAB_DISPLAY = 2
_TAB_SPACER = 3
_TAB_OVERLAYS = 4
_TAB_WIDGETS = 5
_TAB_COLLAPSE = 6

# Tab index → stack page index
_TAB_TO_PAGE = {
    _TAB_CHART_INFO: 0,
    _TAB_CALC_OPTIONS: 1,
    _TAB_DISPLAY: 2,
    _TAB_OVERLAYS: 3,
    _TAB_WIDGETS: 4,
}


class LeftPanel(QWidget):
    """Collapsible left panel for chart config, overlays and info widgets."""

    overlay_toggled = pyqtSignal(str, bool)
    widget_toggled = pyqtSignal(str, bool)
    spawn_widget = pyqtSignal(str)  # Emitted when user wants to spawn a widget (type)
    chart_config_changed = pyqtSignal()  # Emitted when any chart config value changes
    calculate_requested = pyqtSignal()  # Emitted when Calculate button clicked
    theme_changed = pyqtSignal(str)  # Emitted when theme is changed
    chart_style_changed = pyqtSignal(str)  # Emitted when chart style changes
    display_options_changed = pyqtSignal()  # Emitted when display options (signize, toround, print_outer_planets, etc.) change

    def _get_panel_width(self):
        return self.width()

    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, "splitter") and self.splitter:
            total = self.splitter.width()
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                self.splitter.setSizes([w, total - w - sizes[2], sizes[2]])

    panel_width = pyqtProperty(int, _get_panel_width, _set_panel_width)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.splitter = None
        self.setFixedWidth(PANEL_WIDTH)
        self._expanded = True
        self._current_tab = 0
        self._anim = None
        self._font_size = DEFAULT_FONT_SIZE

        self.setStyleSheet(self._make_style(self._font_size))

        self.tab_bar = QTabBar()
        self.tab_bar.setShape(QTabBar.Shape.RoundedWest)
        # Chart config tabs
        self.tab_bar.addTab("Chart Info")
        self.tab_bar.addTab("Calc Options")
        self.tab_bar.addTab("Display")
        self.tab_bar.addTab("     ")  # Spacer separator - same size as collapse
        # Overlay/widget tabs
        self.tab_bar.addTab("Overlays")
        self.tab_bar.addTab("Widgets")
        self.tab_bar.addTab("     ")  # Collapse - same size

        self.tab_bar.setTabToolTip(_TAB_CHART_INFO, "Chart Info")
        self.tab_bar.setTabToolTip(_TAB_CALC_OPTIONS, "Calc Options")
        self.tab_bar.setTabToolTip(_TAB_DISPLAY, "Display")
        self.tab_bar.setTabToolTip(_TAB_OVERLAYS, "Overlays")
        self.tab_bar.setTabToolTip(_TAB_WIDGETS, "Info Widgets")

        self.tab_bar.tabBarClicked.connect(self._on_tab_clicked)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # ── page 0: Chart Info ─────────────────────────────────────────────────
        info_page = QWidget()
        info_layout = QVBoxLayout(info_page)
        info_layout.setContentsMargins(6, 6, 6, 6)
        info_layout.setSpacing(4)

        form = QFormLayout()
        form.setVerticalSpacing(3)
        form.setHorizontalSpacing(6)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Chart name")
        form.addRow("Name:", self.name_edit)

        now = QDateTime.currentDateTime()

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(now.date())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Date:", self.date_edit)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(now.time())
        form.addRow("Time:", self.time_edit)

        self.utcoffset_spin = QDoubleSpinBox()
        self.utcoffset_spin.setRange(-12.0, 14.0)
        self.utcoffset_spin.setDecimals(1)
        self.utcoffset_spin.setSingleStep(0.5)
        self.utcoffset_spin.setValue(0.0)
        form.addRow("UTC Offset:", self.utcoffset_spin)

        self.now_button = QPushButton("Now")
        self.now_button.clicked.connect(self._set_now)
        form.addRow("", self.now_button)

        info_layout.addLayout(form)

        loc_group = QGroupBox("Location")
        loc_form = QFormLayout(loc_group)
        loc_form.setVerticalSpacing(3)
        loc_form.setHorizontalSpacing(6)

        self.placename_edit = QLineEdit()
        loc_form.addRow("Place:", self.placename_edit)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(4)
        loc_form.addRow("Latitude:", self.lat_spin)

        self.long_spin = QDoubleSpinBox()
        self.long_spin.setRange(-180.0, 180.0)
        self.long_spin.setDecimals(4)
        loc_form.addRow("Longitude:", self.long_spin)

        info_layout.addWidget(loc_group)

        # load saved default location (first run: Fishers, IN)
        self._load_default_location()

        self.save_default_button = QPushButton("Save as default location")
        self.save_default_button.clicked.connect(self._save_default_location)
        info_layout.addWidget(self.save_default_button)

        self.open_chtk_button = QPushButton("Open .chtk…")
        self.open_chtk_button.clicked.connect(self.load_chtk)
        info_layout.addWidget(self.open_chtk_button)

        self.open_location_button = QPushButton("Open location…")
        self.open_location_button.clicked.connect(self.load_location)
        info_layout.addWidget(self.open_location_button)

        info_layout.addStretch()

        self.calc_button = QPushButton("Calculate")
        self.calc_button.clicked.connect(self._on_calculate)
        info_layout.addWidget(self.calc_button)

        self.stack.addWidget(info_page)

        # ── page 1: Calc Options ───────────────────────────────────────────────
        calc_page = QWidget()
        calc_layout = QVBoxLayout(calc_page)
        calc_layout.setContentsMargins(6, 6, 6, 6)
        calc_layout.setSpacing(6)

        basic_group = QGroupBox("Basic")
        basic_form = QFormLayout(basic_group)
        basic_form.setVerticalSpacing(3)
        basic_form.setHorizontalSpacing(6)

        self.zodiac_combo = QComboBox()
        self.zodiac_combo.addItems(["Aditya", "Tropical", "Sidereal"])
        basic_form.addRow("Zodiac:", self.zodiac_combo)

        self.ayanamsa_spin = QSpinBox()
        self.ayanamsa_spin.setRange(0, 100)
        self.ayanamsa_spin.setValue(98)
        basic_form.addRow("Ayanamsa:", self.ayanamsa_spin)

        self.hsys_combo = QComboBox()
        self.hsys_combo.addItems(
            [
                "P — Placidus",
                "C — Campanus",
                "R — Regiomontanus",
                "W — Whole Sign",
            ]
        )
        self.hsys_combo.setCurrentIndex(1)
        basic_form.addRow("Houses:", self.hsys_combo)

        calc_layout.addWidget(basic_group)

        # Jaimini
        jaimini_group = QGroupBox("Jaimini")
        jaimini_lay = QVBoxLayout(jaimini_group)
        jaimini_lay.setContentsMargins(6, 6, 6, 6)
        jaimini_lay.setSpacing(3)

        tf_row = QHBoxLayout()
        tf_row.setSpacing(4)
        tf_row.addWidget(QLabel("Temp. Friendships:"))
        self.rashi_temp_friend_check = QCheckBox()
        self.rashi_temp_friend_check.setChecked(True)
        tf_row.addWidget(self.rashi_temp_friend_check)
        tf_row.addStretch()
        jaimini_lay.addLayout(tf_row)

        asp_row = QHBoxLayout()
        asp_row.setSpacing(4)
        asp_row.addWidget(QLabel("Aspects:"))
        self.rashi_aspects_combo = QComboBox()
        self.rashi_aspects_combo.addItems(["quadrant", "element", "conventional"])
        asp_row.addWidget(self.rashi_aspects_combo)
        asp_row.addStretch()
        jaimini_lay.addLayout(asp_row)

        calc_layout.addWidget(jaimini_group)

        # Human Design
        hd_calc_group = QGroupBox("Human Design")
        hd_calc_form = QFormLayout(hd_calc_group)
        hd_calc_form.setVerticalSpacing(3)
        hd_calc_form.setHorizontalSpacing(6)

        self.hd_gate_one_spin = QDoubleSpinBox()
        self.hd_gate_one_spin.setRange(0.0, 360.0)
        self.hd_gate_one_spin.setDecimals(4)
        self.hd_gate_one_spin.setSingleStep(0.25)
        self.hd_gate_one_spin.setValue(223.25)
        hd_calc_form.addRow("Gate One:", self.hd_gate_one_spin)

        calc_layout.addWidget(hd_calc_group)

        # Cards of Truth
        cot_group = QGroupBox("Cards of Truth")
        cot_form = QFormLayout(cot_group)
        cot_form.setVerticalSpacing(3)
        cot_form.setHorizontalSpacing(6)

        self.cot_savana_day_check = QCheckBox()
        self.cot_savana_day_check.setChecked(True)
        cot_form.addRow("Savana Day:", self.cot_savana_day_check)

        self.cot_planet_order_combo = QComboBox()
        self.cot_planet_order_combo.addItems(["vedic", "solar_system"])
        cot_form.addRow("Planet Order:", self.cot_planet_order_combo)

        calc_layout.addWidget(cot_group)
        calc_layout.addStretch()

        calc_calc_button = QPushButton("Calculate")
        calc_calc_button.clicked.connect(self._on_calculate)
        calc_layout.addWidget(calc_calc_button)

        self.stack.addWidget(calc_page)

        # ── page 2: Display ─────────────────────────────────────────────────────
        disp_page = QWidget()
        disp_layout = QVBoxLayout(disp_page)
        disp_layout.setContentsMargins(6, 6, 6, 6)
        disp_layout.setSpacing(6)

        style_group = QGroupBox("Chart Style")
        style_form = QFormLayout(style_group)
        style_form.setVerticalSpacing(3)
        style_form.setHorizontalSpacing(6)

        from gandiva.renderers import CHART_STYLES

        self.chart_style_combo = QComboBox()
        self.chart_style_combo.addItems(list(CHART_STYLES.keys()))
        self.chart_style_combo.currentTextChanged.connect(self.chart_style_changed)
        style_form.addRow("Style:", self.chart_style_combo)

        disp_layout.addWidget(style_group)

        # Display
        disp_group = QGroupBox("Display")
        disp_form = QFormLayout(disp_group)
        disp_form.setVerticalSpacing(3)
        disp_form.setHorizontalSpacing(6)

        self.signize_check = QCheckBox()
        self.signize_check.setChecked(True)
        self.signize_check.stateChanged.connect(self._on_display_option_changed)
        disp_form.addRow("Signize:", self.signize_check)

        self.toround_check = QCheckBox()
        self.toround_check.setChecked(True)
        self.toround_check.stateChanged.connect(self._on_display_option_changed)
        disp_form.addRow("Round:", self.toround_check)

        self.toround_places_spin = QSpinBox()
        self.toround_places_spin.setRange(0, 9)
        self.toround_places_spin.setValue(3)
        self.toround_places_spin.valueChanged.connect(self._on_display_option_changed)
        disp_form.addRow("Decimal Places:", self.toround_places_spin)

        disp_layout.addWidget(disp_group)

        # Print
        print_group = QGroupBox("Print")
        print_form = QFormLayout(print_group)
        print_form.setVerticalSpacing(3)
        print_form.setHorizontalSpacing(6)

        self.print_nakshatras_check = QCheckBox()
        self.print_nakshatras_check.setChecked(True)
        self.print_nakshatras_check.stateChanged.connect(
            self._on_display_option_changed
        )
        print_form.addRow("Nakshatras:", self.print_nakshatras_check)

        self.print_outer_planets_check = QCheckBox()
        self.print_outer_planets_check.setChecked(True)
        self.print_outer_planets_check.stateChanged.connect(
            self._on_display_option_changed
        )
        print_form.addRow("Outer Planets:", self.print_outer_planets_check)

        disp_layout.addWidget(print_group)

        # Human Design
        hd_disp_group = QGroupBox("Human Design")
        hd_disp_form = QFormLayout(hd_disp_group)
        hd_disp_form.setVerticalSpacing(3)
        hd_disp_form.setHorizontalSpacing(6)

        self.hd_print_hexagrams_check = QCheckBox()
        self.hd_print_hexagrams_check.setChecked(False)
        self.hd_print_hexagrams_check.stateChanged.connect(
            self._on_display_option_changed
        )
        hd_disp_form.addRow("Print Hexagrams:", self.hd_print_hexagrams_check)

        disp_layout.addWidget(hd_disp_group)

        # Theme
        from gandiva.themes import theme_names, DEFAULT_THEME

        theme_group = QGroupBox("Theme")
        theme_form = QFormLayout(theme_group)
        theme_form.setVerticalSpacing(3)
        theme_form.setHorizontalSpacing(6)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(DEFAULT_THEME)
        self.theme_combo.currentTextChanged.connect(self.theme_changed)
        theme_form.addRow("Theme:", self.theme_combo)

        disp_layout.addWidget(theme_group)
        disp_layout.addStretch()

        self.stack.addWidget(disp_page)

        # Overlays page
        overlay_page = QWidget()
        ol_layout = QVBoxLayout(overlay_page)
        ol_layout.setContentsMargins(6, 6, 6, 6)
        ol_layout.setSpacing(4)

        self._overlay_checks: dict[str, QCheckBox] = {}
        for overlay_id in OVERLAYS:
            cb = QCheckBox(overlay_id)
            cb.stateChanged.connect(
                lambda state, oid=overlay_id: self.overlay_toggled.emit(
                    oid, state == Qt.CheckState.Checked.value
                )
            )
            ol_layout.addWidget(cb)
            self._overlay_checks[overlay_id] = cb

        if not OVERLAYS:
            ol_layout.addWidget(QLabel("No overlays available yet"))

        ol_layout.addStretch()
        self.stack.addWidget(overlay_page)

        # Widgets page
        widget_page = QWidget()
        wl_layout = QVBoxLayout(widget_page)
        wl_layout.setContentsMargins(6, 6, 6, 6)
        wl_layout.setSpacing(8)

        # Define the widget types we can spawn
        self._widget_types = [
            "Nakshatra Dashas",
            "Vargas",
            "Rashi Dashas",
            "Panchanga",
        ]

        for widget_type in self._widget_types:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            label = QLabel(widget_type)
            row_layout.addWidget(label)
            row_layout.addStretch()

            spawn_btn = QPushButton("→")
            spawn_btn.setFixedWidth(30)
            spawn_btn.setToolTip(f"Spawn {widget_type} widget")
            spawn_btn.clicked.connect(
                lambda checked=False, wt=widget_type: self.spawn_widget.emit(wt)
            )
            row_layout.addWidget(spawn_btn)

            wl_layout.addWidget(row)

        wl_layout.addStretch()
        self.stack.addWidget(widget_page)

        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    def _make_style(self, pt: int) -> str:
        """Generate stylesheet for given font size."""
        h = pt + 8
        return f"""
            QWidget {{ font-size: {pt}px; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit {{
                font-size: {pt}px;
                padding: 1px 3px;
                min-height: {h}px;
                max-height: {h}px;
            }}
            QGroupBox {{
                font-size: {pt}px;
                margin-top: 10px;
                padding-top: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 2px;
            }}
            QPushButton {{ font-size: {pt}px; padding: 3px 6px; }}
            QLabel {{ font-size: {pt}px; }}
            QTabBar::tab {{ font-size: {pt}px; }}
        """

    def adjust_font(self, delta: int):
        """Increase/decrease font size by delta px. delta=0 resets to default."""
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(self._make_style(self._font_size))

    def _set_now(self):
        """Set date/time to current moment."""
        now = QDateTime.currentDateTime()
        self.date_edit.setDate(now.date())
        self.time_edit.setTime(now.time())

    def _on_display_option_changed(self):
        """Called when any display option (signize, toround, print_outer_planets, etc.) changes."""
        self.display_options_changed.emit()

    def _on_calculate(self):
        """Emit signal that calculate was requested."""
        self.calculate_requested.emit()

    def _load_default_location(self):
        """Load saved default location from settings."""
        s = QSettings("gandiva", "gandiva")
        self.placename_edit.setText(s.value("default/placename", "Fishers, IN"))
        self.lat_spin.setValue(float(s.value("default/lat", 39.9567)))
        self.long_spin.setValue(float(s.value("default/lon", -86.0134)))
        self.utcoffset_spin.setValue(float(s.value("default/utcoffset", -5.0)))

    def _save_default_location(self):
        """Save current location as default."""
        s = QSettings("gandiva", "gandiva")
        s.setValue("default/placename", self.placename_edit.text())
        s.setValue("default/lat", self.lat_spin.value())
        s.setValue("default/lon", self.long_spin.value())
        s.setValue("default/utcoffset", self.utcoffset_spin.value())

    def load_chtk(self):
        """Load chart data from a .chtk file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open chart file", "", "Kala chart files (*.chtk);;All files (*)"
        )
        if not path:
            return

        name, placename, month, day, year, timedec, lat, long, utcoffset = read_chtk(
            path
        )

        local_hour = timedec + utcoffset
        h = int(local_hour)
        rem = (local_hour - h) * 60
        m = int(rem)
        s = int((rem - m) * 60)

        self.name_edit.setText(name)
        self.placename_edit.setText(placename)
        self.lat_spin.setValue(lat)
        self.long_spin.setValue(long)
        self.utcoffset_spin.setValue(utcoffset)
        self.date_edit.setDate(QDate(year, month, day))
        self.time_edit.setTime(QTime(h, m, s))
        self.calculate_requested.emit()

    def load_location(self):
        """Load only location data from a .chtk file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open location from chart",
            "",
            "Kala chart files (*.chtk);;All files (*)",
        )
        if not path:
            return

        placename, lat, lon, utcoffset = read_chtk_location(path)
        self.placename_edit.setText(placename)
        self.lat_spin.setValue(lat)
        self.long_spin.setValue(lon)
        self.utcoffset_spin.setValue(utcoffset)

    def on_overlay_removed(self, overlay_id: str):
        cb = self._overlay_checks.get(overlay_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def on_widget_removed(self, widget_id: str):
        cb = self._widget_checks.get(widget_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def uncheck_all_overlays(self):
        for cb in self._overlay_checks.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def _on_tab_clicked(self, idx):
        # Both empty tabs (spacer and collapse) always collapse, never open
        if idx == _TAB_SPACER or idx == _TAB_COLLAPSE:
            self.tab_bar.setCurrentIndex(self._current_tab)
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
            return

        if idx not in _TAB_TO_PAGE:
            return

        if idx == self._current_tab and self._expanded:
            # Collapse — lock current width so animation has a valid start value
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
        else:
            # Expand to target width
            self._current_tab = idx
            self._expanded = True
            self.tab_bar.setCurrentIndex(idx)
            page = _TAB_TO_PAGE[idx]
            if not self.isVisible():
                self.setFixedWidth(1)
                self.setVisible(True)
            self.stack.setCurrentIndex(page)
            self.stack.show()
            self._animate_to(PANEL_WIDTH)

    # ── options state (saved/restored per chart tab) ─────────────────────────

    def get_options_state(self):
        """Snapshot of all calc + display options (not birth info)."""
        return {
            # Chart Info
            "zodiac": self.zodiac_combo.currentText(),
            "ayanamsa": self.ayanamsa_spin.value(),
            "hsys": self.hsys_combo.currentText(),
            # Jaimini
            "rashi_temp_friend": self.rashi_temp_friend_check.isChecked(),
            "rashi_aspects": self.rashi_aspects_combo.currentText(),
            # Human Design
            "hd_gate_one": self.hd_gate_one_spin.value(),
            # Cards of Truth
            "cot_savana_day": self.cot_savana_day_check.isChecked(),
            "cot_planet_order": self.cot_planet_order_combo.currentText(),
            # Display
            "chart_style": self.chart_style_combo.currentText(),
            "signize": self.signize_check.isChecked(),
            "toround": self.toround_check.isChecked(),
            "toround_places": self.toround_places_spin.value(),
            "print_nakshatras": self.print_nakshatras_check.isChecked(),
            "print_outer_planets": self.print_outer_planets_check.isChecked(),
            "hd_print_hexagrams": self.hd_print_hexagrams_check.isChecked(),
        }

    def set_options_state(self, state):
        """Restore calc + display options without triggering signals."""
        # Block signals to avoid cascading recalculations
        widgets = [
            self.zodiac_combo, self.ayanamsa_spin, self.hsys_combo,
            self.rashi_temp_friend_check, self.rashi_aspects_combo,
            self.hd_gate_one_spin,
            self.cot_savana_day_check, self.cot_planet_order_combo,
            self.chart_style_combo,
            self.signize_check, self.toround_check, self.toround_places_spin,
            self.print_nakshatras_check, self.print_outer_planets_check,
            self.hd_print_hexagrams_check,
        ]
        for w in widgets:
            w.blockSignals(True)

        self.zodiac_combo.setCurrentText(state.get("zodiac", "Aditya"))
        self.ayanamsa_spin.setValue(state.get("ayanamsa", 98))
        self.hsys_combo.setCurrentText(state.get("hsys", "C — Campanus"))
        self.rashi_temp_friend_check.setChecked(state.get("rashi_temp_friend", True))
        self.rashi_aspects_combo.setCurrentText(state.get("rashi_aspects", "quadrant"))
        self.hd_gate_one_spin.setValue(state.get("hd_gate_one", 223.25))
        self.cot_savana_day_check.setChecked(state.get("cot_savana_day", True))
        self.cot_planet_order_combo.setCurrentText(state.get("cot_planet_order", "vedic"))
        self.chart_style_combo.setCurrentText(state.get("chart_style", "Western Wheel"))
        self.signize_check.setChecked(state.get("signize", True))
        self.toround_check.setChecked(state.get("toround", True))
        self.toround_places_spin.setValue(state.get("toround_places", 3))
        self.print_nakshatras_check.setChecked(state.get("print_nakshatras", True))
        self.print_outer_planets_check.setChecked(state.get("print_outer_planets", True))
        self.hd_print_hexagrams_check.setChecked(state.get("hd_print_hexagrams", False))

        for w in widgets:
            w.blockSignals(False)

    def _animate_to(self, target_w: int, on_finished=None):
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        self._anim = QPropertyAnimation(self, b"panel_width")
        self._anim.setDuration(ANIM_DURATION_MS)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target_w)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if on_finished:
            self._anim.finished.connect(on_finished)
        self._anim.finished.connect(lambda: setattr(self, "_anim", None))
        self._anim.start()
