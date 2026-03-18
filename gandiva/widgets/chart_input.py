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
    QMessageBox,
)
from PyQt6.QtCore import (
    pyqtSignal,
    QDateTime,
    QDate,
    QTime,
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QSettings,
)

from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const
from libaditya.read import read_chtk, read_chtk_location

from gandiva.themes import theme_names, DEFAULT_THEME
from gandiva.widgets.data_panels import (
    PlanetsWidget,
    CuspsWidget,
    NakshatrasWidget,
    DashasWidget,
    KalaWidget,
    PanchangaWidget,
    _make_style,
)


EXPANDED_WIDTH = 200
DEFAULT_FONT_SIZE = 16
ANIM_DURATION_MS = 220


# Tab index → stack page index for content tabs.
# Index 3 is a spacer/collapse tab (no page).
_TAB_TO_PAGE = {0: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5}
_COLLAPSE_TAB = 3

# Tab index → target width when expanding.
_TAB_WIDTHS = {
    0: "half",  # Planets — needs room for 3×4 grid
    1: 320,  # Cusps — 4 short columns
    2: 300,  # Nakshatras — two short columns
    4: 400,  # Dashas
    5: 420,  # Kala
    6: "half",  # Panchanga — wide table
}


class ChartInputPanel(QWidget):
    chart_created = pyqtSignal(object)
    theme_changed = pyqtSignal(str)
    no_changes = pyqtSignal()
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
        self._last_calc_state = None

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

        # Hidden input widgets (synced from left panel, used for calculation)
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

        # Calc options widgets (hidden)
        self.zodiac_combo = QComboBox()
        self.zodiac_combo.addItems(["Aditya", "Tropical", "Sidereal"])
        self.ayanamsa_spin = QSpinBox()
        self.ayanamsa_spin.setRange(0, 100)
        self.ayanamsa_spin.setValue(98)
        self.hsys_combo = QComboBox()
        self.hsys_combo.addItems([
            "P — Placidus", "C — Campanus", "R — Regiomontanus", "W — Whole Sign",
        ])
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

        # Display options widgets (hidden)
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

        # ── data panel widgets (extracted) ─────────────────────────────────────
        self._planets_widget = PlanetsWidget()
        self.planet_cells = self._planets_widget.planet_cells  # backward compat
        self.stack.addWidget(self._planets_widget)

        self._cusps_widget = CuspsWidget()
        self.cusp_table = self._cusps_widget.cusp_table  # backward compat
        self.stack.addWidget(self._cusps_widget)

        self._nakshatras_widget = NakshatrasWidget()
        self.nakshatra_tree = self._nakshatras_widget.nakshatra_tree  # backward compat
        self.stack.addWidget(self._nakshatras_widget)

        self._dashas_widget = DashasWidget()
        self.stack.addWidget(self._dashas_widget)

        self._kala_widget = KalaWidget()
        self.stack.addWidget(self._kala_widget)

        self._panchanga_widget = PanchangaWidget()
        self.stack.addWidget(self._panchanga_widget)

        # ── initial state ─────────────────────────────────────────────────────
        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    # ── tab collapse / expand with animation ──────────────────────────────────

    def _on_tab_clicked(self, idx):
        if idx == _COLLAPSE_TAB:
            self.tab_bar.setCurrentIndex(self._current_tab)
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
            return
        if idx not in _TAB_TO_PAGE:
            return
        if idx == self._current_tab and self._expanded:
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
        else:
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
        self._anim.finished.connect(lambda: setattr(self, "_anim", None))
        self._anim.start()

    # ── birth-info snapshot (for chart tab tracking) ──────────────────────────

    def get_birth_key(self):
        return (
            self.date_edit.date().toString(Qt.DateFormat.ISODate),
            self.time_edit.time().toString("HH:mm:ss"),
            self.utcoffset_spin.value(),
            self.lat_spin.value(),
            self.long_spin.value(),
            self.zodiac_combo.currentText(),
            self.ayanamsa_spin.value(),
            self.hsys_combo.currentText(),
            self.rashi_temp_friend_check.isChecked(),
            self.rashi_aspects_combo.currentText(),
        )

    def get_birth_state(self):
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
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))
        # Propagate to extracted widgets
        self._planets_widget.adjust_font(delta)
        self._cusps_widget.adjust_font(delta)
        self._nakshatras_widget.adjust_font(delta)
        self._dashas_widget.adjust_font(delta)
        self._kala_widget.adjust_font(delta)
        self._panchanga_widget.adjust_font(delta)

    # ── chart calculation ─────────────────────────────────────────────────────

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
            rashi_temporary_friendships=self.rashi_temp_friend_check.isChecked(),
            rashi_aspects=self.rashi_aspects_combo.currentText(),
            hd_gate_one=self.hd_gate_one_spin.value(),
            cot_savana_day=self.cot_savana_day_check.isChecked(),
            cot_planet_order=self.cot_planet_order_combo.currentText(),
            signize=self.signize_check.isChecked(),
            toround=(self.toround_check.isChecked(), self.toround_places_spin.value()),
            print_nakshatras=self.print_nakshatras_check.isChecked(),
            print_outer_planets=self.print_outer_planets_check.isChecked(),
            hd_print_hexagrams=self.hd_print_hexagrams_check.isChecked(),
        )

        chart = Chart(context=context)
        self.chart_created.emit(chart)

    # ── info tab population ───────────────────────────────────────────────────

    def update_info(self, chart):
        self._last_chart = chart
        self._planets_widget.update_from_chart(chart)
        self._cusps_widget.update_from_chart(chart)
        self._nakshatras_widget.update_from_chart(chart)
        self._dashas_widget.update_from_chart(chart)
        self._kala_widget.update_from_chart(chart)
        self._panchanga_widget.update_from_chart(chart)

    # ── file I/O ──────────────────────────────────────────────────────────────

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
