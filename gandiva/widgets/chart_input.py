from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QDateEdit,
    QTimeEdit,
    QGroupBox,
    QFileDialog,
    QLabel,
    QStackedWidget,
    QTabBar,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QGridLayout,
    QMessageBox,
    QPlainTextEdit,
)
from PyQt6.QtCore import (
    pyqtSignal,
    QDateTime,
    QDate,
    QTime,
    Qt,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QSettings,
)
from PyQt6.QtGui import QColor, QBrush

from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const
from libaditya.read import read_chtk, read_chtk_location

from gandiva.themes import theme_names, DEFAULT_THEME


EXPANDED_WIDTH = 200
DEFAULT_FONT_SIZE = 16
ANIM_DURATION_MS = 220


# Tab index → stack page index for content tabs.
# Index 3 is a spacer/collapse tab (no page).
_TAB_TO_PAGE = {0: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5}
_COLLAPSE_TAB = 3

_VEDIC_ORDER = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
]

# The 12 planets shown in the Planets tab (9 grahas + 3 modern outer)
_CHART_PLANETS = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
    "Uranus",
    "Neptune",
    "Pluto",
]

# Tab index → target width when expanding.
# "half" means compute half the splitter width at click time.
_TAB_WIDTHS = {
    0: "half",  # Planets — needs room for 3×4 grid
    1: 320,  # Cusps — 4 short columns
    2: 300,  # Nakshatras — two short columns
    4: 400,  # Dashas
    5: 420,  # Kala
    6: "half",  # Panchanga — wide table
}

_NAKSHATRA_ORDER = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]


def _fmt_lon(obj) -> str:
    """Format a planet or cusp longitude per context settings.
    Signize on → DD:MM:SS within sign; off → full ecliptic longitude float."""
    if obj.context.signize:
        return obj.in_sign_longitude()
    return str(obj.amsha_longitude())


def _make_style(pt: int) -> str:
    h = pt + 8  # compact input-widget height sized to comfortably hold pt-px text
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
    chart_created = pyqtSignal(object)
    theme_changed = pyqtSignal(str)
    no_changes = pyqtSignal()  # emitted when Calculate pressed with no changes
    chart_style_changed = pyqtSignal(str)

    # ── animatable width property ─────────────────────────────────────────────

    def _get_panel_width(self):
        return self.width()

    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, "splitter") and self.splitter:
            total = self.splitter.width()
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                self.splitter.setSizes([sizes[0], total - sizes[0] - w, w])
            else:
                self.splitter.setSizes([total - w, w])

    panel_width = pyqtProperty(int, _get_panel_width, _set_panel_width)

    # ── init ──────────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.setFixedWidth(EXPANDED_WIDTH)
        self._font_size = DEFAULT_FONT_SIZE
        self._expanded = True
        self._current_tab = 0
        self._anim = None
        self._last_calc_state = None  # tracks previous calculate snapshot

        self.setStyleSheet(_make_style(self._font_size))

        # ── tab bar — lives outside this widget, placed by MainWindow ───────────
        self.tab_bar = QTabBar()
        self.tab_bar.setShape(QTabBar.Shape.RoundedEast)
        self.tab_bar.addTab("Planets")  # 0
        self.tab_bar.addTab("Cusps")  # 1
        self.tab_bar.addTab("Nakshatras")  # 2
        self.tab_bar.addTab("               ")  # 3 — spacer / collapse action
        self.tab_bar.addTab("Dashas")  # 4
        self.tab_bar.addTab("Kala")  # 5
        self.tab_bar.addTab("Panchanga")  # 6
        self.tab_bar.setTabToolTip(0, "Planets")
        self.tab_bar.setTabToolTip(1, "Cusps")
        self.tab_bar.setTabToolTip(2, "Nakshatras")
        self.tab_bar.setTabToolTip(4, "Dashas")
        self.tab_bar.setTabToolTip(5, "Kala — time info")
        self.tab_bar.setTabToolTip(6, "Monthly Panchanga")
        self.tab_bar.tabBarClicked.connect(self._on_tab_clicked)

        # ── content stack (collapsible, fills this widget) ────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # Keep the input widgets (they're synced from left panel and used for calculation)
        # but don't add them as pages - they're just internal state

        # Chart info widgets (hidden, used for calculation)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Chart name")
        now = QDateTime.currentDateTime()
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(now.date())
        self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(now.time())
        self.utcoffset_spin = QDoubleSpinBox()
        self.utcoffset_spin.setRange(-12.0, 14.0)
        self.utcoffset_spin.setDecimals(1)
        self.utcoffset_spin.setSingleStep(0.5)
        self.utcoffset_spin.setValue(0.0)
        self.placename_edit = QLineEdit()
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(4)
        self.long_spin = QDoubleSpinBox()
        self.long_spin.setRange(-180.0, 180.0)
        self.long_spin.setDecimals(4)
        self._load_default_location()

        # Calc options widgets (hidden, used for calculation)
        self.zodiac_combo = QComboBox()
        self.zodiac_combo.addItems(["Aditya", "Tropical", "Sidereal"])
        self.ayanamsa_spin = QSpinBox()
        self.ayanamsa_spin.setRange(0, 100)
        self.ayanamsa_spin.setValue(98)
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
        self.rashi_temp_friend_check = QCheckBox()
        self.rashi_temp_friend_check.setChecked(True)
        self.rashi_aspects_combo = QComboBox()
        self.rashi_aspects_combo.addItems(["quadrant", "element", "conventional"])
        self.hd_gate_one_spin = QDoubleSpinBox()
        self.hd_gate_one_spin.setRange(0.0, 360.0)
        self.hd_gate_one_spin.setDecimals(4)
        self.hd_gate_one_spin.setSingleStep(0.25)
        self.hd_gate_one_spin.setValue(223.25)
        self.cot_savana_day_check = QCheckBox()
        self.cot_savana_day_check.setChecked(True)
        self.cot_planet_order_combo = QComboBox()
        self.cot_planet_order_combo.addItems(["vedic", "solar_system"])

        # Display options widgets (hidden, used for calculation)
        self.chart_style_combo = QComboBox()
        from gandiva.renderers import CHART_STYLES

        self.chart_style_combo.addItems(list(CHART_STYLES.keys()))
        self.chart_style_combo.currentTextChanged.connect(self.chart_style_changed)
        self.signize_check = QCheckBox()
        self.signize_check.setChecked(True)
        self.signize_check.stateChanged.connect(self.calculate)
        self.toround_check = QCheckBox()
        self.toround_check.setChecked(True)
        self.toround_check.stateChanged.connect(self.calculate)
        self.toround_places_spin = QSpinBox()
        self.toround_places_spin.setRange(0, 9)
        self.toround_places_spin.setValue(3)
        self.toround_places_spin.valueChanged.connect(self.calculate)
        self.print_nakshatras_check = QCheckBox()
        self.print_nakshatras_check.setChecked(True)
        self.print_nakshatras_check.stateChanged.connect(self.calculate)
        self.print_outer_planets_check = QCheckBox()
        self.print_outer_planets_check.setChecked(True)
        self.print_outer_planets_check.stateChanged.connect(self.calculate)
        self.hd_print_hexagrams_check = QCheckBox()
        self.hd_print_hexagrams_check.setChecked(False)
        self.hd_print_hexagrams_check.stateChanged.connect(self.calculate)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(DEFAULT_THEME)
        self.theme_combo.currentTextChanged.connect(self.theme_changed)

        # ── page 0: Planets — 3×4 grid ────────────────────────────────────────
        planet_page = QWidget()
        pp_layout = QVBoxLayout(planet_page)
        pp_layout.setContentsMargins(4, 4, 4, 4)
        pp_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        self.planet_cells: dict[str, tuple] = {}  # name → (groupbox, tree)
        for idx, name in enumerate(_CHART_PLANETS):
            row, col = divmod(idx, 4)
            gb = QGroupBox(name)
            gb_lay = QVBoxLayout(gb)
            gb_lay.setContentsMargins(2, 2, 2, 2)
            gb_lay.setSpacing(0)

            tree = QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setColumnCount(2)
            tree.setIndentation(10)
            tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
            tree.header().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents
            )
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            tree.setExpandsOnDoubleClick(False)
            tree.itemClicked.connect(
                lambda item, _: item.setExpanded(not item.isExpanded())
            )

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

        # ── page 1: Cusps ─────────────────────────────────────────────────────
        cusp_page = QWidget()
        cp_layout = QVBoxLayout(cusp_page)
        cp_layout.setContentsMargins(4, 4, 4, 4)
        self.cusp_table = QTableWidget()
        self.cusp_table.setColumnCount(4)
        self.cusp_table.setHorizontalHeaderLabels(
            ["Cusp", "Longitude", "Sign", "Nakshatra"]
        )
        self.cusp_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.cusp_table.horizontalHeader().setStretchLastSection(True)
        self.cusp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cusp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cusp_table.verticalHeader().setVisible(False)
        cp_layout.addWidget(self.cusp_table)
        self.stack.addWidget(cusp_page)

        # ── page 2: Nakshatras ────────────────────────────────────────────────
        nak_page = QWidget()
        np_layout = QVBoxLayout(nak_page)
        np_layout.setContentsMargins(4, 4, 4, 4)
        self.nakshatra_tree = QTreeWidget()
        self.nakshatra_tree.setHeaderHidden(True)
        self.nakshatra_tree.setColumnCount(2)
        self.nakshatra_tree.setIndentation(14)
        self.nakshatra_tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.nakshatra_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.nakshatra_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.nakshatra_tree.setExpandsOnDoubleClick(False)
        self.nakshatra_tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded())
        )
        np_layout.addWidget(self.nakshatra_tree)
        self.stack.addWidget(nak_page)

        # ── page 3: Dashas ──────────────────────────────────────────────────
        dasha_page = QWidget()
        dp_layout = QVBoxLayout(dasha_page)
        dp_layout.setContentsMargins(4, 4, 4, 4)
        dp_layout.setSpacing(4)

        # Nakshatra Dasha section (top half)
        nak_dasha_group = QGroupBox("Nakshatra Dasha (Vimshottari)")
        nd_layout = QVBoxLayout(nak_dasha_group)
        nd_layout.setContentsMargins(4, 4, 4, 4)
        nd_layout.setSpacing(4)

        # Control bar: level buttons + options
        nd_control = QWidget()
        nd_ctrl_layout = QHBoxLayout(nd_control)
        nd_ctrl_layout.setContentsMargins(0, 0, 0, 0)
        nd_ctrl_layout.setSpacing(2)

        self._nd_levels = 1
        self._nd_year_length = "saura"
        self._nd_base_planet = "Moon"
        self._nd_level_buttons = {}

        for i in range(1, 6):
            btn = QPushButton(str(i))
            btn.setFixedSize(24, 24)
            btn.setCheckable(True)
            btn.setChecked(i == self._nd_levels)
            btn.clicked.connect(
                lambda checked, level=i: self._nd_on_level_clicked(level)
            )
            self._nd_level_buttons[i] = btn
            nd_ctrl_layout.addWidget(btn)

        nd_ctrl_layout.addStretch()

        self._nd_current_btn = QPushButton("⌖")
        self._nd_current_btn.setFixedSize(24, 24)
        self._nd_current_btn.setToolTip("Go to current dasha")
        self._nd_current_btn.clicked.connect(self._nd_goto_current)
        nd_ctrl_layout.addWidget(self._nd_current_btn)

        self._nd_options_btn = QPushButton("⚙")
        self._nd_options_btn.setFixedSize(24, 24)
        self._nd_options_btn.setToolTip("Options")
        self._nd_options_btn.clicked.connect(self._nd_show_options_menu)
        nd_ctrl_layout.addWidget(self._nd_options_btn)

        nd_layout.addWidget(nd_control)

        # Dasha table
        self._nd_table = QTableWidget()
        self._nd_table.setColumnCount(3)
        self._nd_table.setHorizontalHeaderLabels(["Dasha", "Start", "Age"])
        header = self._nd_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._nd_table.verticalHeader().setVisible(False)
        self._nd_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._nd_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._nd_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._nd_table.verticalHeader().setDefaultSectionSize(20)
        nd_layout.addWidget(self._nd_table)

        dp_layout.addWidget(nak_dasha_group, stretch=1)

        # Placeholder for Rashi Dasha (bottom half, future)
        rashi_dasha_group = QGroupBox("Rashi Dasha")
        rd_layout = QVBoxLayout(rashi_dasha_group)
        rd_layout.setContentsMargins(4, 4, 4, 4)
        placeholder = QLabel("Coming soon")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rd_layout.addWidget(placeholder)
        dp_layout.addWidget(rashi_dasha_group, stretch=1)

        self.stack.addWidget(dasha_page)

        # ── page 4: Kala — time info ────────────────────────────────────────
        kala_page = QWidget()
        kp_layout = QVBoxLayout(kala_page)
        kp_layout.setContentsMargins(4, 4, 4, 4)

        self._kala_text = QPlainTextEdit()
        self._kala_text.setReadOnly(True)
        self._kala_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        from PyQt6.QtGui import QFont as _QFont, QFontDatabase
        # Preferred: Source Code Pro Semibold (user's terminal font)
        kala_font = QFontDatabase.font("Source Code Pro", "Semibold", 10)
        if not kala_font.family().lower().startswith("source"):
            kala_font = _QFont("monospace")
            kala_font.setStyleHint(_QFont.StyleHint.Monospace)
            kala_font.setPointSize(10)
        self._kala_text.setFont(kala_font)
        kp_layout.addWidget(self._kala_text)

        self.stack.addWidget(kala_page)

        # ── page 5: Panchanga — monthly table ────────────────────────────────
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup, QDialog

        panch_page = QWidget()
        panch_layout = QVBoxLayout(panch_page)
        panch_layout.setContentsMargins(4, 4, 4, 4)
        panch_layout.setSpacing(4)

        # Row 1: Month/year navigation
        nav_row = QWidget()
        nav_layout = QHBoxLayout(nav_row)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        self._panch_yr_back = QPushButton("«")
        self._panch_yr_back.setFixedSize(24, 24)
        self._panch_yr_back.setToolTip("Previous year")
        self._panch_mo_back = QPushButton("‹")
        self._panch_mo_back.setFixedSize(24, 24)
        self._panch_mo_back.setToolTip("Previous month")

        self._panch_month_spin = QSpinBox()
        self._panch_month_spin.setRange(1, 12)
        self._panch_month_spin.setFixedWidth(50)
        sep_label = QLabel("/")
        self._panch_year_spin = QSpinBox()
        self._panch_year_spin.setRange(-5000, 9999)
        self._panch_year_spin.setFixedWidth(60)

        self._panch_mo_fwd = QPushButton("›")
        self._panch_mo_fwd.setFixedSize(24, 24)
        self._panch_mo_fwd.setToolTip("Next month")
        self._panch_yr_fwd = QPushButton("»")
        self._panch_yr_fwd.setFixedSize(24, 24)
        self._panch_yr_fwd.setToolTip("Next year")

        self._panch_yr_back.clicked.connect(lambda: self._panch_shift(-12))
        self._panch_mo_back.clicked.connect(lambda: self._panch_shift(-1))
        self._panch_mo_fwd.clicked.connect(lambda: self._panch_shift(1))
        self._panch_yr_fwd.clicked.connect(lambda: self._panch_shift(12))
        self._panch_month_spin.valueChanged.connect(self._panch_recalc)
        self._panch_year_spin.valueChanged.connect(self._panch_recalc)

        nav_layout.addWidget(self._panch_yr_back)
        nav_layout.addWidget(self._panch_mo_back)
        nav_layout.addWidget(self._panch_month_spin)
        nav_layout.addWidget(sep_label)
        nav_layout.addWidget(self._panch_year_spin)
        nav_layout.addWidget(self._panch_mo_fwd)
        nav_layout.addWidget(self._panch_yr_fwd)

        nav_layout.addStretch()

        # Location button
        self._panch_loc_btn = QPushButton("Location")
        self._panch_loc_btn.setToolTip("Location settings")
        self._panch_loc_btn.clicked.connect(self._panch_show_location)
        nav_layout.addWidget(self._panch_loc_btn)

        panch_layout.addWidget(nav_row)

        # Row 2: Calc options
        panch_opts = QWidget()
        po_layout = QHBoxLayout(panch_opts)
        po_layout.setContentsMargins(0, 0, 0, 0)
        po_layout.setSpacing(8)

        self._panch_local_radio = QRadioButton("Local")
        self._panch_utc_radio = QRadioButton("UTC")
        self._panch_local_radio.setChecked(True)
        tz_group = QButtonGroup(self)
        tz_group.addButton(self._panch_local_radio)
        tz_group.addButton(self._panch_utc_radio)
        po_layout.addWidget(self._panch_local_radio)
        po_layout.addWidget(self._panch_utc_radio)

        po_layout.addWidget(QLabel(" |"))

        self._panch_mode_midnight = QRadioButton("Cal/Midnight")
        self._panch_mode_sunrise_cal = QRadioButton("Cal/Sunrise (WIP)")
        self._panch_mode_savana = QRadioButton("Savana/Sunrise (WIP)")
        self._panch_mode_midnight.setToolTip("Calendar day, panchanga at midnight")
        self._panch_mode_sunrise_cal.setToolTip("Calendar day, panchanga at sunrise")
        self._panch_mode_savana.setToolTip("Savana day (sunrise to sunrise)")
        self._panch_mode_midnight.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self._panch_mode_midnight)
        mode_group.addButton(self._panch_mode_sunrise_cal)
        mode_group.addButton(self._panch_mode_savana)
        po_layout.addWidget(self._panch_mode_midnight)
        po_layout.addWidget(self._panch_mode_sunrise_cal)
        po_layout.addWidget(self._panch_mode_savana)
        po_layout.addStretch()

        tz_group.buttonClicked.connect(self._panch_recalc)
        mode_group.buttonClicked.connect(self._panch_recalc)

        panch_layout.addWidget(panch_opts)

        # Panchanga location state (independent of chart)
        s = QSettings("gandiva", "gandiva")
        self._panch_location = {
            "placename": s.value("default/placename", "Fishers, IN"),
            "lat": float(s.value("default/lat", 39.9567)),
            "lon": float(s.value("default/lon", -86.0134)),
            "utcoffset": float(s.value("default/utcoffset", -5.0)),
        }

        # Text display
        self._panch_text = QPlainTextEdit()
        self._panch_text.setReadOnly(True)
        self._panch_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._panch_text.setFont(kala_font)
        panch_layout.addWidget(self._panch_text)

        self.stack.addWidget(panch_page)

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
            self._expanded = True
            self.tab_bar.setCurrentIndex(idx)
            page = _TAB_TO_PAGE[idx]
            parent = self.parentWidget()
            spec = _TAB_WIDTHS.get(idx, EXPANDED_WIDTH)
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
            # Jaimini
            self.rashi_temp_friend_check.isChecked(),
            self.rashi_aspects_combo.currentText(),
        )

    def get_birth_state(self):
        """Snapshot of all chart-determining form values."""
        return {
            "name": self.name_edit.text(),
            "date": self.date_edit.date(),
            "time": self.time_edit.time(),
            "utcoffset": self.utcoffset_spin.value(),
            "placename": self.placename_edit.text(),
            "lat": self.lat_spin.value(),
            "lon": self.long_spin.value(),
            "zodiac": self.zodiac_combo.currentText(),
            "ayanamsa": self.ayanamsa_spin.value(),
            "hsys": self.hsys_combo.currentText(),
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
        self._last_chart = chart
        self._update_planet_tree(chart)
        self._update_cusp_table(chart)
        self._update_nakshatra_tree(chart)
        self._update_nakshatra_dasha(chart)
        self._update_kala(chart)
        self._update_panchanga(chart)

    def _update_planet_tree(self, chart):
        planets = dict(chart.rashi().planets().items())

        def bold_item(parent, texts):
            item = QTreeWidgetItem(parent, texts)
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
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
                QTreeWidgetItem(basic, ["Longitude", _fmt_lon(planet)])
                QTreeWidgetItem(basic, ["Sign", planet.sign_name()])
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
                QTreeWidgetItem(
                    basic, ["Speed", f"{planet.longitude_speed():.4f}°/day"]
                )
                try:
                    QTreeWidgetItem(basic, ["Latitude", f"{planet.latitude():.4f}°"])
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
        rashi = chart.rashi()
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
        groups: dict[str, list] = {}  # nak_name → [(label, lon_str), ...]
        for pname, planet in planets.items():
            if pname in _SKIP:
                continue
            try:
                nak = planet.nakshatra_name()
                retro = " (R)" if planet.retrograde() else ""
                dig = planet.dignity()
                dig_s = f" [{dig}]" if dig else ""
                groups.setdefault(nak, []).append(
                    (f"{pname}{retro}{dig_s}", _fmt_lon(planet), "planet", pname)
                )
            except Exception:
                continue

        # Group cusps by nakshatra
        try:
            for cusp in rashi.cusps():
                try:
                    nak = cusp.nakshatra_name()
                    groups.setdefault(nak, []).append(
                        (f"Cusp {cusp.number()}", _fmt_lon(cusp), "cusp", cusp.number())
                    )
                except Exception:
                    continue
        except Exception:
            pass

        for nak_name in sorted(groups.keys(), key=nak_key):
            top = QTreeWidgetItem(tree, [nak_name, ""])
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            # Planets first (Vedic order), then cusps (by number)
            occupants = groups[nak_name]
            planets_here = [(l, v, t, k) for l, v, t, k in occupants if t == "planet"]
            cusps_here = [(l, v, t, k) for l, v, t, k in occupants if t == "cusp"]
            for label, lon, _, key in sorted(
                planets_here, key=lambda x: vedic_key((x[3],))
            ):
                QTreeWidgetItem(top, [label, str(lon)])
            for label, lon, _, _ in sorted(cusps_here, key=lambda x: x[3]):
                QTreeWidgetItem(top, [label, str(lon)])
            top.setExpanded(True)

    def _update_cusp_table(self, chart):
        cusps = chart.rashi().cusps()
        rows = []
        for cusp in cusps:
            try:
                rows.append(
                    [
                        str(cusp.number()),
                        _fmt_lon(cusp),
                        str(cusp.sign_name()),
                        str(cusp.nakshatra_name()),
                    ]
                )
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
        d = self.date_edit.date()
        t = self.time_edit.time()
        utcoffset = self.utcoffset_spin.value()

        local_hour = t.hour() + t.minute() / 60.0 + t.second() / 3600.0
        utc_hour = local_hour - utcoffset
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
        self.lat_spin.setValue(float(s.value("default/lat", 39.9567)))
        self.long_spin.setValue(float(s.value("default/lon", -86.0134)))
        self.utcoffset_spin.setValue(float(s.value("default/utcoffset", -5.0)))

    def _save_default_location(self):
        s = QSettings("gandiva", "gandiva")
        s.setValue("default/placename", self.placename_edit.text())
        s.setValue("default/lat", self.lat_spin.value())
        s.setValue("default/lon", self.long_spin.value())
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
        self.calculate()

    def load_location(self):
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

    # ── Nakshatra Dasha (tab page) ────────────────────────────────────────────

    def _nd_on_level_clicked(self, level):
        self._nd_levels = level
        for i, btn in self._nd_level_buttons.items():
            btn.setChecked(i == level)
        if hasattr(self, "_last_chart") and self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _nd_show_options_menu(self):
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self._nd_options_btn)

        year_menu = QMenu("Year Length", menu)
        year_lengths = [
            ("saura", "Saura (365.24 days)"),
            ("nakshatra", "Nakshatra (359.02 days)"),
            ("savana", "Savana (360 days)"),
            ("sidereal", "Sidereal (365.26 days)"),
            ("chandra", "Chandra (364.29 days)"),
            ("lunar", "Lunar (354.37 days)"),
        ]
        for key, label in year_lengths:
            action = year_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._nd_year_length == key)
            action.triggered.connect(
                lambda checked, k=key: self._nd_set_year_length(k)
            )
        menu.addMenu(year_menu)
        menu.addSeparator()

        planet_menu = QMenu("Base Planet", menu)
        for key, label in [
            ("Moon", "Moon"),
            ("Sun", "Sun"),
            ("Lagna", "Lagna (Ascendant)"),
        ]:
            action = planet_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._nd_base_planet == key)
            action.triggered.connect(
                lambda checked, k=key: self._nd_set_base_planet(k)
            )
        menu.addMenu(planet_menu)

        menu.exec(
            self._nd_options_btn.mapToGlobal(QPoint(0, self._nd_options_btn.height()))
        )

    def _nd_set_year_length(self, length):
        self._nd_year_length = length
        if hasattr(self, "_last_chart") and self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _nd_set_base_planet(self, planet):
        self._nd_base_planet = planet
        if hasattr(self, "_last_chart") and self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _update_nakshatra_dasha(self, chart):
        from datetime import datetime, timedelta
        from libaditya.calc.vimshottari import (
            calculate_vimshottari_dasha,
            calculate_specific_period,
        )

        _LORD_ABBREV = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
        _SOLAR_YEAR = 365.2422

        self._nd_table.setRowCount(0)

        try:
            # Resolve base planet
            planets = dict(chart.rashi().planets().items())
            base = None
            if self._nd_base_planet == "Moon":
                base = planets.get("Moon")
            elif self._nd_base_planet == "Sun":
                base = planets.get("Sun")
            elif self._nd_base_planet == "Lagna":
                cusps = chart.rashi().cusps()
                if cusps:
                    base = cusps[0]

            if base is None:
                return

            yrlen = const.dasha_years.get(self._nd_year_length, 365.2422)

            # Get first_dasha index
            result = calculate_vimshottari_dasha(base, dlevels=1, yrlen=yrlen)
            if not result or len(result) < 2:
                return
            _beginning_age = result.pop()
            first_dasha = result.pop()

            birth_jd = chart.context.timeJD.jd_number()

            # Current JD
            j2000 = datetime(2000, 1, 1, 12, 0, 0)
            now_jd = 2451545.0 + (datetime.utcnow() - j2000).total_seconds() / 86400.0

            last_current_row = -1

            def recurse(lord_path, depth):
                nonlocal last_current_row
                start_lord = lord_path[-1] if lord_path else first_dasha
                for i in range(9):
                    lord_idx = (start_lord + i) % 9
                    path = lord_path + [lord_idx]
                    start_jd_obj, dur_days = calculate_specific_period(
                        base, path, yrlen
                    )
                    start_jd = start_jd_obj.jd_number()
                    end_jd = start_jd + dur_days

                    label = "-".join(_LORD_ABBREV[l] for l in path)
                    age = (start_jd - birth_jd) / _SOLAR_YEAR
                    is_current = start_jd <= now_jd < end_jd

                    row = self._nd_table.rowCount()
                    self._nd_table.insertRow(row)

                    item = QTableWidgetItem(label)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self._nd_table.setItem(row, 0, item)

                    start_dt = j2000 + timedelta(days=start_jd - 2451545.0)
                    date_str = start_dt.strftime("%m/%d/%Y %H:%M")
                    item = QTableWidgetItem(date_str)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self._nd_table.setItem(row, 1, item)

                    age_years = int(age)
                    age_months = int((age - age_years) * 12)
                    item = QTableWidgetItem(f"{age_years}y {age_months}m")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self._nd_table.setItem(row, 2, item)

                    if is_current:
                        brush = QBrush(QColor(100, 200, 100, 100))
                        for col in range(3):
                            self._nd_table.item(row, col).setBackground(brush)
                        last_current_row = row

                    if depth < self._nd_levels:
                        recurse(path, depth + 1)

            recurse([], 1)

            # Store and scroll to current period
            self._nd_last_current_row = last_current_row
            if last_current_row >= 0:
                self._nd_table.scrollToItem(
                    self._nd_table.item(last_current_row, 0),
                    QTableWidget.ScrollHint.PositionAtCenter,
                )

        except Exception:
            import traceback
            traceback.print_exc()

    def _nd_goto_current(self):
        """Scroll to the deepest currently active dasha period."""
        row = getattr(self, "_nd_last_current_row", -1)
        if row >= 0 and row < self._nd_table.rowCount():
            self._nd_table.scrollToItem(
                self._nd_table.item(row, 0),
                QTableWidget.ScrollHint.PositionAtCenter,
            )

    # ── Kala (tab page) ───────────────────────────────────────────────────────

    def _update_kala(self, chart):
        """Capture output of print_kala-equivalent functions and display."""
        import io
        import sys

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf

        try:
            from libaditya.calc.kala import cardinal_points, lunar_new_year
            from libaditya.calc import Panchanga

            context = chart.context

            # Cardinal points
            year = context.timeJD.year()
            points = cardinal_points(year)
            print(f"Cardinal points for {year}\n")
            print(f"Ascending equinox:\n{points[0]}")
            print(f"Northern solstice:\n{points[1]}")
            print(f"Descending equinox:\n{points[2]}")
            print(f"Southern solstice:\n{points[3]}")

            # Lunar new year
            print("\nLunar new year:\n")
            print(lunar_new_year(context.timeJD).moon())

            # Panchanga
            p = Panchanga(context)
            print(p)
            p.print_next_new_moon()
            p.print_next_full_moon()

        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout

        self._kala_text.setPlainText(buf.getvalue())

    # ── Panchanga (tab page) ─────────────────────────────────────────────────

    def _panch_shift(self, delta_months):
        """Shift month/year by delta_months and recalculate."""
        m = self._panch_month_spin.value()
        y = self._panch_year_spin.value()
        total = (y * 12 + (m - 1)) + delta_months
        new_y, new_m = divmod(total, 12)
        new_m += 1
        # Block signals so we only recalculate once
        self._panch_month_spin.blockSignals(True)
        self._panch_year_spin.blockSignals(True)
        self._panch_month_spin.setValue(new_m)
        self._panch_year_spin.setValue(new_y)
        self._panch_month_spin.blockSignals(False)
        self._panch_year_spin.blockSignals(False)
        self._panch_recalc()

    def _panch_recalc(self):
        """Recalculate panchanga from current widget state."""
        self._run_panchanga(
            self._panch_month_spin.value(),
            self._panch_year_spin.value(),
        )

    def _panch_show_location(self):
        """Show location settings dialog."""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Panchanga Location")
        lay = QVBoxLayout(dlg)

        form = QFormLayout()
        form.setVerticalSpacing(3)
        form.setHorizontalSpacing(6)

        pname = self._panch_location["placename"]
        place_edit = QLineEdit(str(pname() if callable(pname) else pname))
        form.addRow("Place:", place_edit)

        lat_spin = QDoubleSpinBox()
        lat_spin.setRange(-90.0, 90.0)
        lat_spin.setDecimals(4)
        lat_spin.setValue(self._panch_location["lat"])
        form.addRow("Latitude:", lat_spin)

        lon_spin = QDoubleSpinBox()
        lon_spin.setRange(-180.0, 180.0)
        lon_spin.setDecimals(4)
        lon_spin.setValue(self._panch_location["lon"])
        form.addRow("Longitude:", lon_spin)

        utc_spin = QDoubleSpinBox()
        utc_spin.setRange(-12.0, 14.0)
        utc_spin.setDecimals(1)
        utc_spin.setSingleStep(0.5)
        utc_spin.setValue(self._panch_location["utcoffset"])
        form.addRow("UTC Offset:", utc_spin)

        lay.addLayout(form)

        # Load from .chtk
        def load_chtk():
            path, _ = QFileDialog.getOpenFileName(
                dlg, "Open location from chart", "",
                "Kala chart files (*.chtk);;All files (*)",
            )
            if path:
                placename, lat, lon, utcoffset = read_chtk_location(path)
                place_edit.setText(placename)
                lat_spin.setValue(lat)
                lon_spin.setValue(lon)
                utc_spin.setValue(utcoffset)

        chtk_btn = QPushButton("Load from .chtk…")
        chtk_btn.clicked.connect(load_chtk)
        lay.addWidget(chtk_btn)

        # Use chart location
        def use_chart_loc():
            if hasattr(self, "_last_chart") and self._last_chart:
                loc = self._last_chart.context.location
                pn = loc.placename() if callable(loc.placename) else loc.placename
                place_edit.setText(str(pn))
                lat_spin.setValue(loc.lat)
                lon_spin.setValue(loc.long)
                utc_spin.setValue(loc.utcoffset)

        chart_btn = QPushButton("Use chart location")
        chart_btn.clicked.connect(use_chart_loc)
        lay.addWidget(chart_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._panch_location = {
                "placename": place_edit.text(),
                "lat": lat_spin.value(),
                "lon": lon_spin.value(),
                "utcoffset": utc_spin.value(),
            }
            self._panch_recalc()

    def _update_panchanga(self, chart):
        """Called on chart update — sync month/year from chart, then calculate."""
        ctx = chart.context
        loc = ctx.location
        self._panch_location = {
            "placename": loc.placename() if callable(loc.placename) else loc.placename,
            "lat": loc.lat,
            "lon": loc.long,
            "utcoffset": loc.utcoffset,
        }
        # Set month/year without triggering double recalc
        self._panch_month_spin.blockSignals(True)
        self._panch_year_spin.blockSignals(True)
        self._panch_month_spin.setValue(ctx.timeJD.month())
        self._panch_year_spin.setValue(ctx.timeJD.year())
        self._panch_month_spin.blockSignals(False)
        self._panch_year_spin.blockSignals(False)
        self._panch_recalc()

    def _run_panchanga(self, month, year):
        """Build monthly panchanga table for given month/year and current location."""
        from dataclasses import replace as dc_replace
        from prettytable import PrettyTable
        from libaditya.calc import Panchanga
        from libaditya.objects import JulianDay, EphContext, Location

        try:
            loc = self._panch_location
            utcoffset = loc["utcoffset"]
            location = Location(
                lat=loc["lat"], long=loc["lon"],
                placename=loc["placename"], utcoffset=utcoffset,
            )

            use_utc = self._panch_utc_radio.isChecked()
            savana = self._panch_mode_savana.isChecked() or self._panch_mode_sunrise_cal.isChecked()
            calendar = self._panch_mode_sunrise_cal.isChecked()

            if use_utc:
                start_jd = JulianDay((year, month, 1, 0), 0, "UTC")
                tz = "utc"
            else:
                start_jd = JulianDay((year, month, 1, -utcoffset), utcoffset, "UTC")
                tz = "usr"

            ctx = EphContext(timeJD=start_jd, location=location)
            panch = Panchanga(ctx)

            table = PrettyTable()
            table.field_names = [
                "Day", "Sunrise", "Sunset", "Moonrise", "Moonset",
                "V", "N.V.", "N", "N.N.", "T", "N.T.", "K.", "N.K.", "Y", "N.Y.",
            ]

            current_month = month
            while panch.timeJD.month() == current_month:
                sunrise = panch.sunrise()
                sunset = panch.sunset()
                moonrise = panch.moonrise()
                moonset = panch.moonset()

                if savana:
                    working_panch = Panchanga(dc_replace(panch.context, timeJD=sunrise))
                    if calendar:
                        day = panch.timeJD.day(tz)
                        lower_bound = panch.timeJD.jd_number()
                        upper_bound = lower_bound + 1
                    else:
                        day = sunrise.day(tz)
                        lower_bound = sunrise.jd_number()
                        next_day_panch = Panchanga(
                            dc_replace(panch.context, timeJD=panch.timeJD.shift("f", "day", 1))
                        )
                        upper_bound = next_day_panch.sunrise().jd_number()
                else:
                    working_panch = panch
                    day = panch.timeJD.day(tz)
                    lower_bound = panch.timeJD.jd_number()
                    upper_bound = lower_bound + 1

                row = [
                    day,
                    sunrise.time(tz, False),
                    sunset.time(tz, False),
                ]

                ptimes = [
                    moonrise, moonset,
                    working_panch.vara(), working_panch.next_vara().timeJD,
                    working_panch.nakshatra(), working_panch.next_nakshatra().timeJD,
                    working_panch.tithi(), working_panch.next_tithi().timeJD,
                    working_panch.karana(), working_panch.next_karana().timeJD,
                    working_panch.yoga_name(), working_panch.next_yoga().timeJD,
                ]

                for t in ptimes:
                    if not isinstance(t, JulianDay):
                        row.append(t)
                    elif lower_bound < t.jd_number() < upper_bound:
                        row.append(t.time(tz, False))
                    else:
                        row.append("N/A")

                table.add_row(row)
                table.add_divider()

                panch = Panchanga(
                    dc_replace(panch.context, timeJD=panch.timeJD.shift("f", "day", 1))
                )

            # Header
            if savana and not calendar:
                time_note = "All times relative to sunrise"
            else:
                time_note = "All times relative to midnight"
            if use_utc:
                tz_note = "All times UTC"
            else:
                tz_note = f"All times: {start_jd.timezone()}"

            header = (
                f"Panchanga for {month}/{year}\n"
                f"{loc['placename']} ({loc['lat']:.4f} lat, {loc['lon']:.4f} long)\n"
                f"{time_note}\n"
                f"{tz_note}\n\n"
            )
            self._panch_text.setPlainText(
                header + table.get_formatted_string(out_format="text")
            )

        except Exception:
            import traceback
            self._panch_text.setPlainText(traceback.format_exc())
