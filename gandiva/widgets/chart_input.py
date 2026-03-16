from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QDoubleSpinBox, QSpinBox, QDateEdit, QTimeEdit, QGroupBox,
    QFileDialog, QLabel, QStackedWidget, QTabBar, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QMessageBox,
)
from PyQt6.QtCore import (
    pyqtSignal, QDateTime, QDate, QTime, Qt,
    QPropertyAnimation, QEasingCurve, pyqtProperty, QSettings,
)
from PyQt6.QtGui import QColor

from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const
from libaditya.read import read_chtk, read_chtk_location

from gandiva.themes import theme_names, DEFAULT_THEME


EXPANDED_WIDTH    = 200
DEFAULT_FONT_SIZE = 16
ANIM_DURATION_MS  = 220


# Tab index → stack page index. Index 3 is a collapse-action tab (no page).
_TAB_TO_PAGE   = {0: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5}
_COLLAPSE_TAB  = 3

_VEDIC_ORDER = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu", "Uranus", "Neptune", "Pluto", "Chiron",
]

# The 12 planets shown in the Planets tab (9 grahas + 3 modern outer)
_CHART_PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu", "Uranus", "Neptune", "Pluto",
]

# Tab index → target width when expanding.
# "half" means compute half the splitter width at click time.
_TAB_WIDTHS = {
    0: EXPANDED_WIDTH,   # Chart Info — simple form
    1: EXPANDED_WIDTH,   # Calc Options — simple form
    2: EXPANDED_WIDTH,   # Display — simple form
    4: "half",           # Planets — needs room for 3×4 grid
    5: 320,              # Cusps — 4 short columns
    6: 300,              # Nakshatras — two short columns
}

_NAKSHATRA_ORDER = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]


def _fmt_lon(obj) -> str:
    """Format a planet or cusp longitude per context settings.
    Signize on → DD:MM:SS within sign; off → full ecliptic longitude float."""
    if obj.context.signize:
        return obj.in_sign_longitude()
    return str(obj.amsha_longitude())


def _make_style(pt: int) -> str:
    h = pt + 8   # compact input-widget height sized to comfortably hold pt-px text
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
        QLabel       {{ font-size: {pt}px; }}
    """


class ChartInputPanel(QWidget):
    chart_created       = pyqtSignal(object)
    theme_changed       = pyqtSignal(str)
    no_changes          = pyqtSignal()          # emitted when Calculate pressed with no changes
    chart_style_changed = pyqtSignal(str)

    # ── animatable width property ─────────────────────────────────────────────

    def _get_panel_width(self):
        return self.width()

    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, 'splitter') and self.splitter:
            total = self.splitter.width()
            self.splitter.setSizes([total - w, w])

    panel_width = pyqtProperty(int, _get_panel_width, _set_panel_width)

    # ── init ──────────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.setFixedWidth(EXPANDED_WIDTH)
        self._font_size   = DEFAULT_FONT_SIZE
        self._expanded    = True
        self._current_tab = 0
        self._anim        = None
        self._last_calc_state = None   # tracks previous calculate snapshot

        self.setStyleSheet(_make_style(self._font_size))

        # ── tab bar — lives outside this widget, placed by MainWindow ───────────
        # Index 3 is a disabled spacer tab; _TAB_TO_PAGE maps the rest to pages.
        self.tab_bar = QTabBar()
        self.tab_bar.setShape(QTabBar.Shape.RoundedEast)
        self.tab_bar.addTab("Chart Info")   # 0
        self.tab_bar.addTab("Calc Options") # 1
        self.tab_bar.addTab("Display")      # 2
        self.tab_bar.addTab("               ")  # 3 — collapse action
        self.tab_bar.addTab("Planets")      # 4
        self.tab_bar.addTab("Cusps")        # 5
        self.tab_bar.addTab("Nakshatras")   # 6
        self.tab_bar.setTabToolTip(0, "Chart Info")
        self.tab_bar.setTabToolTip(1, "Calc Options")
        self.tab_bar.setTabToolTip(2, "Display")
        self.tab_bar.setTabToolTip(4, "Planets")
        self.tab_bar.setTabToolTip(5, "Cusps")
        self.tab_bar.setTabToolTip(6, "Nakshatras")
        self.tab_bar.tabBarClicked.connect(self._on_tab_clicked)

        # ── content stack (collapsible, fills this widget) ────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # ── page 0: chart info ────────────────────────────────────────────────
        info_page   = QWidget()
        info_layout = QVBoxLayout(info_page)
        info_layout.setContentsMargins(6, 4, 6, 4)
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
        loc_form  = QFormLayout(loc_group)
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
        self.calc_button.clicked.connect(self.calculate)
        info_layout.addWidget(self.calc_button)

        self.stack.addWidget(info_page)

        # ── page 1: calc options ──────────────────────────────────────────────
        calc_page   = QWidget()
        calc_layout = QVBoxLayout(calc_page)
        calc_layout.setContentsMargins(6, 4, 6, 4)
        calc_layout.setSpacing(6)

        # Basic
        basic_group = QGroupBox("Basic")
        basic_form  = QFormLayout(basic_group)
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
        self.hsys_combo.addItems([
            "P — Placidus", "C — Campanus",
            "R — Regiomontanus", "W — Whole Sign",
        ])
        self.hsys_combo.setCurrentIndex(1)
        basic_form.addRow("Houses:", self.hsys_combo)

        calc_layout.addWidget(basic_group)

        # Jaimini
        jaimini_group = QGroupBox("Jaimini")
        jaimini_form  = QFormLayout(jaimini_group)
        jaimini_form.setVerticalSpacing(3)
        jaimini_form.setHorizontalSpacing(6)

        self.rashi_temp_friend_check = QCheckBox()
        self.rashi_temp_friend_check.setChecked(True)
        jaimini_form.addRow("Temp. Friendships:", self.rashi_temp_friend_check)

        self.rashi_aspects_combo = QComboBox()
        self.rashi_aspects_combo.addItems(["quadrant", "element", "conventional"])
        jaimini_form.addRow("Aspects:", self.rashi_aspects_combo)

        calc_layout.addWidget(jaimini_group)

        # Human Design
        hd_calc_group = QGroupBox("Human Design")
        hd_calc_form  = QFormLayout(hd_calc_group)
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
        cot_form  = QFormLayout(cot_group)
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

        calc_calc_btn = QPushButton("Calculate")
        calc_calc_btn.clicked.connect(self.calculate)
        calc_layout.addWidget(calc_calc_btn)

        self.stack.addWidget(calc_page)

        # ── page 2: display options ───────────────────────────────────────────
        disp_page   = QWidget()
        disp_layout = QVBoxLayout(disp_page)
        disp_layout.setContentsMargins(6, 4, 6, 4)
        disp_layout.setSpacing(6)

        # Chart Style
        style_group = QGroupBox("Chart Style")
        style_form  = QFormLayout(style_group)
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
        disp_form  = QFormLayout(disp_group)
        disp_form.setVerticalSpacing(3)
        disp_form.setHorizontalSpacing(6)

        self.signize_check = QCheckBox()
        self.signize_check.setChecked(True)
        self.signize_check.stateChanged.connect(self.calculate)
        disp_form.addRow("Signize:", self.signize_check)

        self.toround_check = QCheckBox()
        self.toround_check.setChecked(True)
        self.toround_check.stateChanged.connect(self.calculate)
        disp_form.addRow("Round:", self.toround_check)

        self.toround_places_spin = QSpinBox()
        self.toround_places_spin.setRange(0, 9)
        self.toround_places_spin.setValue(3)
        self.toround_places_spin.valueChanged.connect(self.calculate)
        disp_form.addRow("Decimal Places:", self.toround_places_spin)

        disp_layout.addWidget(disp_group)

        # Print
        print_group = QGroupBox("Print")
        print_form  = QFormLayout(print_group)
        print_form.setVerticalSpacing(3)
        print_form.setHorizontalSpacing(6)

        self.print_nakshatras_check = QCheckBox()
        self.print_nakshatras_check.setChecked(True)
        self.print_nakshatras_check.stateChanged.connect(self.calculate)
        print_form.addRow("Nakshatras:", self.print_nakshatras_check)

        self.print_outer_planets_check = QCheckBox()
        self.print_outer_planets_check.setChecked(True)
        self.print_outer_planets_check.stateChanged.connect(self.calculate)
        print_form.addRow("Outer Planets:", self.print_outer_planets_check)

        disp_layout.addWidget(print_group)

        # Human Design
        hd_disp_group = QGroupBox("Human Design")
        hd_disp_form  = QFormLayout(hd_disp_group)
        hd_disp_form.setVerticalSpacing(3)
        hd_disp_form.setHorizontalSpacing(6)

        self.hd_print_hexagrams_check = QCheckBox()
        self.hd_print_hexagrams_check.setChecked(False)
        self.hd_print_hexagrams_check.stateChanged.connect(self.calculate)
        hd_disp_form.addRow("Print Hexagrams:", self.hd_print_hexagrams_check)

        disp_layout.addWidget(hd_disp_group)

        # Theme
        theme_group = QGroupBox("Theme")
        theme_form  = QFormLayout(theme_group)
        theme_form.setVerticalSpacing(3)
        theme_form.setHorizontalSpacing(6)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(DEFAULT_THEME)
        self.theme_combo.currentTextChanged.connect(self.theme_changed)
        theme_form.addRow("Theme:", self.theme_combo)

        disp_layout.addWidget(theme_group)
        disp_layout.addStretch()

        disp_calc_btn = QPushButton("Calculate")
        disp_calc_btn.clicked.connect(self.calculate)
        disp_layout.addWidget(disp_calc_btn)

        self.stack.addWidget(disp_page)

        # ── page 3: Planets — 3×4 grid ────────────────────────────────────────
        planet_page = QWidget()
        pp_layout   = QVBoxLayout(planet_page)
        pp_layout.setContentsMargins(4, 4, 4, 4)
        pp_layout.setSpacing(0)

        scroll      = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        grid_widget = QWidget()
        grid        = QGridLayout(grid_widget)
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        self.planet_cells: dict[str, tuple] = {}   # name → (groupbox, tree)
        for idx, name in enumerate(_CHART_PLANETS):
            row, col = divmod(idx, 4)
            gb       = QGroupBox(name)
            gb_lay   = QVBoxLayout(gb)
            gb_lay.setContentsMargins(2, 2, 2, 2)
            gb_lay.setSpacing(0)

            tree = QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setColumnCount(2)
            tree.setIndentation(10)
            tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
            tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            tree.setExpandsOnDoubleClick(False)
            tree.itemClicked.connect(
                lambda item, _: item.setExpanded(not item.isExpanded()))

            gb_lay.addWidget(tree)
            grid.addWidget(gb, row, col)
            self.planet_cells[name] = (gb, tree)

        for r in range(3):
            grid.setRowStretch(r, 1)
        for c in range(4):
            grid.setColumnStretch(c, 1)

        scroll.setWidget(grid_widget)
        pp_layout.addWidget(scroll)
        self.stack.addWidget(planet_page)

        # ── page 4: Cusps ─────────────────────────────────────────────────────
        cusp_page   = QWidget()
        cp_layout   = QVBoxLayout(cusp_page)
        cp_layout.setContentsMargins(4, 4, 4, 4)
        self.cusp_table = QTableWidget()
        self.cusp_table.setColumnCount(4)
        self.cusp_table.setHorizontalHeaderLabels(["Cusp", "Longitude", "Sign", "Nakshatra"])
        self.cusp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.cusp_table.horizontalHeader().setStretchLastSection(True)
        self.cusp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cusp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cusp_table.verticalHeader().setVisible(False)
        cp_layout.addWidget(self.cusp_table)
        self.stack.addWidget(cusp_page)

        # ── page 5: Nakshatras ────────────────────────────────────────────────
        nak_page   = QWidget()
        np_layout  = QVBoxLayout(nak_page)
        np_layout.setContentsMargins(4, 4, 4, 4)
        self.nakshatra_tree = QTreeWidget()
        self.nakshatra_tree.setHeaderHidden(True)
        self.nakshatra_tree.setColumnCount(2)
        self.nakshatra_tree.setIndentation(14)
        self.nakshatra_tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.nakshatra_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.nakshatra_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.nakshatra_tree.setExpandsOnDoubleClick(False)
        self.nakshatra_tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded()))
        np_layout.addWidget(self.nakshatra_tree)
        self.stack.addWidget(nak_page)

        # ── initial state ─────────────────────────────────────────────────────
        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    # ── tab collapse / expand with animation ──────────────────────────────────

    def _on_tab_clicked(self, idx):
        if idx == _COLLAPSE_TAB:
            # Always collapse; restore selection to the previously active tab.
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
            # Expand to half the splitter width (or half the window if no parent)
            self._current_tab = idx
            self._expanded    = True
            self.tab_bar.setCurrentIndex(idx)
            page     = _TAB_TO_PAGE[idx]
            parent   = self.parentWidget()
            spec     = _TAB_WIDTHS.get(idx, EXPANDED_WIDTH)
            if spec == "half":
                target_w = max(350, parent.width() // 2) if parent else EXPANDED_WIDTH
            else:
                target_w = spec
            if not self.isVisible():
                self.setFixedWidth(1)
                self.setVisible(True)
            # Show the stack immediately — not in on_finished — so that stopping
            # an animation mid-flight never leaves the stack permanently hidden.
            self.stack.setCurrentIndex(page)
            self.stack.show()
            self._animate_to(target_w)

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
        # Clear the reference when done so the next click doesn't call .stop()
        # on a finished animation (avoids stale C++ wrapper crash).
        self._anim.finished.connect(lambda: setattr(self, "_anim", None))
        self._anim.start()

    # ── font size adjustment ──────────────────────────────────────────────────

    # ── birth-info snapshot (for chart tab tracking) ──────────────────────────

    def get_birth_key(self):
        """Hashable key for chart-affecting options. Changes → new tab."""
        return (
            self.date_edit.date().toString(Qt.DateFormat.ISODate),
            self.time_edit.time().toString("HH:mm:ss"),
            self.utcoffset_spin.value(),
            self.lat_spin.value(),
            self.long_spin.value(),
            self.zodiac_combo.currentText(),
            self.ayanamsa_spin.value(),
            self.hsys_combo.currentText(),
        )

    def get_birth_state(self):
        """Snapshot of all chart-determining form values."""
        return {
            "name":      self.name_edit.text(),
            "date":      self.date_edit.date(),
            "time":      self.time_edit.time(),
            "utcoffset": self.utcoffset_spin.value(),
            "placename": self.placename_edit.text(),
            "lat":       self.lat_spin.value(),
            "lon":       self.long_spin.value(),
            "zodiac":    self.zodiac_combo.currentText(),
            "ayanamsa":  self.ayanamsa_spin.value(),
            "hsys":      self.hsys_combo.currentText(),
        }

    def set_birth_state(self, state):
        """Restore form values without triggering a new-tab cycle."""
        self.name_edit.setText(state["name"])
        self.date_edit.setDate(state["date"])
        self.time_edit.setTime(state["time"])
        self.utcoffset_spin.setValue(state["utcoffset"])
        self.placename_edit.setText(state["placename"])
        self.lat_spin.setValue(state["lat"])
        self.long_spin.setValue(state["lon"])
        self.zodiac_combo.setCurrentText(state.get("zodiac", "Aditya"))
        self.ayanamsa_spin.setValue(state.get("ayanamsa", 98))
        self.hsys_combo.setCurrentText(state.get("hsys", "C — Campanus"))

    def adjust_font(self, delta: int):
        """Increase/decrease font size by delta px. delta=0 resets to default."""
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))

    # ── chart calculation ─────────────────────────────────────────────────────

    # ── info tab population ───────────────────────────────────────────────────

    def update_info(self, chart):
        self._update_planet_tree(chart)
        self._update_cusp_table(chart)
        self._update_nakshatra_tree(chart)

    def _update_planet_tree(self, chart):
        planets = dict(chart.rashi().planets().items())

        def bold_item(parent, texts):
            item = QTreeWidgetItem(parent, texts)
            f = item.font(0); f.setBold(True); item.setFont(0, f)
            return item

        for name, (gb, tree) in self.planet_cells.items():
            tree.clear()
            planet = planets.get(name)
            if planet is None:
                gb.setTitle(name)
                continue
            try:
                retro = " (R)" if planet.retrograde() else ""
                gb.setTitle(f"{name}{retro}")

                # ── Basic ──────────────────────────────────────────────────
                basic = bold_item(tree, ["Basic", ""])
                QTreeWidgetItem(basic, ["Longitude",  _fmt_lon(planet)])
                QTreeWidgetItem(basic, ["Sign",       planet.sign_name()])
                dig = planet.dignity()
                if dig:
                    QTreeWidgetItem(basic, ["Dignity", dig])
                QTreeWidgetItem(basic, ["Nakshatra", planet.nakshatra_name()])
                try:
                    c = planet.constellation()
                    if c and c != "n/a":
                        QTreeWidgetItem(basic, ["Constellation", c])
                except Exception:
                    pass
                QTreeWidgetItem(basic, ["Speed", f"{planet.longitude_speed():.4f}°/day"])
                try:
                    QTreeWidgetItem(basic, ["Latitude",  f"{planet.latitude():.4f}°"])
                except Exception:
                    pass
                try:
                    QTreeWidgetItem(basic, ["Distance", f"{planet.distance():.4f} AU"])
                except Exception:
                    pass
                try:
                    QTreeWidgetItem(basic, ["Rise", planet.rise().usrtimedate()])
                except Exception:
                    pass
                try:
                    QTreeWidgetItem(basic, ["Set", planet.set().usrtimedate()])
                except Exception:
                    pass

                # ── Shadbala (placeholder) ─────────────────────────────────
                bold_item(tree, ["Shadbala", ""])

                # ── Avasthas (placeholder) ─────────────────────────────────
                bold_item(tree, ["Avasthas", ""])

                # Basic open, Shadbala/Avasthas collapsed
                for i in range(tree.topLevelItemCount()):
                    item = tree.topLevelItem(i)
                    item.setExpanded(item.text(0) == "Basic")

            except Exception:
                continue

    def _update_nakshatra_tree(self, chart):
        tree = self.nakshatra_tree
        tree.clear()
        rashi   = chart.rashi()
        planets = dict(rashi.planets().items())

        def nak_key(nak_name):
            base = nak_name.split("(")[0].strip()
            try:
                return _NAKSHATRA_ORDER.index(base)
            except ValueError:
                return len(_NAKSHATRA_ORDER)

        def vedic_key(item):
            try:
                return _VEDIC_ORDER.index(item[0])
            except ValueError:
                return len(_VEDIC_ORDER)

        _SKIP = {"Earth"}

        # Group planets by nakshatra
        groups: dict[str, list] = {}   # nak_name → [(label, lon_str), ...]
        for pname, planet in planets.items():
            if pname in _SKIP:
                continue
            try:
                nak = planet.nakshatra_name()
                retro = " (R)" if planet.retrograde() else ""
                dig   = planet.dignity()
                dig_s = f" [{dig}]" if dig else ""
                groups.setdefault(nak, []).append(
                    (f"{pname}{retro}{dig_s}", _fmt_lon(planet), "planet", pname))
            except Exception:
                continue

        # Group cusps by nakshatra
        try:
            for cusp in rashi.cusps():
                try:
                    nak = cusp.nakshatra_name()
                    groups.setdefault(nak, []).append(
                        (f"Cusp {cusp.number()}", _fmt_lon(cusp), "cusp", cusp.number()))
                except Exception:
                    continue
        except Exception:
            pass

        for nak_name in sorted(groups.keys(), key=nak_key):
            top = QTreeWidgetItem(tree, [nak_name, ""])
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            # Planets first (Vedic order), then cusps (by number)
            occupants = groups[nak_name]
            planets_here = [(l, v, t, k) for l, v, t, k in occupants if t == "planet"]
            cusps_here   = [(l, v, t, k) for l, v, t, k in occupants if t == "cusp"]
            for label, lon, _, key in sorted(planets_here, key=lambda x: vedic_key((x[3],))):
                QTreeWidgetItem(top, [label, str(lon)])
            for label, lon, _, _ in sorted(cusps_here, key=lambda x: x[3]):
                QTreeWidgetItem(top, [label, str(lon)])
            top.setExpanded(True)

    def _update_cusp_table(self, chart):
        cusps = chart.rashi().cusps()
        rows  = []
        for cusp in cusps:
            try:
                rows.append([
                    str(cusp.number()),
                    _fmt_lon(cusp),
                    str(cusp.sign_name()),
                    str(cusp.nakshatra_name()),
                ])
            except Exception:
                continue
        t = self.cusp_table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                t.setItem(r, c, item)

    def calculate(self):
        try:
            self._calculate()
        except Exception as e:
            QMessageBox.critical(self, "Calculation error", str(e))

    def _calculate(self):
        d         = self.date_edit.date()
        t         = self.time_edit.time()
        utcoffset = self.utcoffset_spin.value()

        local_hour = t.hour() + t.minute() / 60.0 + t.second() / 3600.0
        utc_hour   = local_hour - utcoffset
        jd = JulianDay((d.year(), d.month(), d.day(), utc_hour), utcoffset=utcoffset)

        location = Location(
            lat=self.lat_spin.value(),
            long=self.long_spin.value(),
            placename=self.placename_edit.text(),
            utcoffset=utcoffset,
        )

        zodiac_text = self.zodiac_combo.currentText()
        if zodiac_text == "Tropical":
            sysflg, circle, sign_names = const.ECL, Circle.ZODIAC, "zodiac"
        elif zodiac_text == "Sidereal":
            sysflg, circle, sign_names = const.SID, Circle.ZODIAC, "zodiac"
        else:
            sysflg, circle, sign_names = const.ECL, Circle.ADITYA, "adityas"

        context = EphContext(
            name=self.name_edit.text(),
            timeJD=jd,
            location=location,
            sysflg=sysflg,
            ayanamsa=self.ayanamsa_spin.value(),
            hsys=self.hsys_combo.currentText()[0],
            circle=circle,
            sign_names=sign_names,
            # Jaimini
            rashi_temporary_friendships=self.rashi_temp_friend_check.isChecked(),
            rashi_aspects=self.rashi_aspects_combo.currentText(),
            # Human Design (calc)
            hd_gate_one=self.hd_gate_one_spin.value(),
            # Cards of Truth
            cot_savana_day=self.cot_savana_day_check.isChecked(),
            cot_planet_order=self.cot_planet_order_combo.currentText(),
            # Display
            signize=self.signize_check.isChecked(),
            toround=(self.toround_check.isChecked(), self.toround_places_spin.value()),
            print_nakshatras=self.print_nakshatras_check.isChecked(),
            print_outer_planets=self.print_outer_planets_check.isChecked(),
            hd_print_hexagrams=self.hd_print_hexagrams_check.isChecked(),
        )

        chart = Chart(context=context)
        self.chart_created.emit(chart)

    def _load_default_location(self):
        s = QSettings("gandiva", "gandiva")
        self.placename_edit.setText(s.value("default/placename", "Fishers, IN"))
        self.lat_spin.setValue(float(s.value("default/lat",       39.9567)))
        self.long_spin.setValue(float(s.value("default/lon",      -86.0134)))
        self.utcoffset_spin.setValue(float(s.value("default/utcoffset", -5.0)))

    def _save_default_location(self):
        s = QSettings("gandiva", "gandiva")
        s.setValue("default/placename", self.placename_edit.text())
        s.setValue("default/lat",       self.lat_spin.value())
        s.setValue("default/lon",       self.long_spin.value())
        s.setValue("default/utcoffset", self.utcoffset_spin.value())

    def _set_now(self):
        now = QDateTime.currentDateTime()
        self.date_edit.setDate(now.date())
        self.time_edit.setTime(now.time())

    def load_chtk(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open chart file", "", "Kala chart files (*.chtk);;All files (*)"
        )
        if not path:
            return

        name, placename, month, day, year, timedec, lat, long, utcoffset = read_chtk(path)

        local_hour = timedec + utcoffset
        h   = int(local_hour)
        rem = (local_hour - h) * 60
        m   = int(rem)
        s   = int((rem - m) * 60)

        self.name_edit.setText(name)
        self.placename_edit.setText(placename)
        self.lat_spin.setValue(lat)
        self.long_spin.setValue(long)
        self.utcoffset_spin.setValue(utcoffset)
        self.date_edit.setDate(QDate(year, month, day))
        self.time_edit.setTime(QTime(h, m, s))
        self.calculate()

    def load_location(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open location from chart", "", "Kala chart files (*.chtk);;All files (*)"
        )
        if not path:
            return

        placename, lat, lon, utcoffset = read_chtk_location(path)
        self.placename_edit.setText(placename)
        self.lat_spin.setValue(lat)
        self.long_spin.setValue(lon)
        self.utcoffset_spin.setValue(utcoffset)
