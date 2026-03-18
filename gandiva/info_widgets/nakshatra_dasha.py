"""Nakshatra Dasha info widget — displays Vimshottari dasha periods."""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMenu,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QBrush

from gandiva.info_widgets.base import InfoWidget


# Lord indices: 0=Ke, 1=Ve, 2=Su, 3=Mo, 4=Ma, 5=Ra, 6=Ju, 7=Sa, 8=Me
_LORD_ABBREV = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]

_SOLAR_YEAR = 365.2422  # for age display (always solar, independent of dasha yrlen)


def _today_jd():
    """Current moment as Julian Day number."""
    j2000 = datetime(2000, 1, 1, 12, 0, 0)
    return 2451545.0 + (datetime.utcnow() - j2000).total_seconds() / 86400.0


def _jd_to_datetime(jd):
    """Convert Julian Day to datetime."""
    j2000 = datetime(2000, 1, 1, 12, 0, 0)
    return j2000 + timedelta(days=float(jd) - 2451545.0)


class NakshatraDashaWidget(InfoWidget):
    """Displays Vimshottari Dasha periods."""

    def __init__(
        self,
        widget_id: str = "Nakshatra Dashas",
        title: str = "Nakshatra Dashas",
        **kwargs,
    ):
        self._year_length = "saura"
        self._base_planet = "Moon"
        self._levels = 1
        self._last_chart = None
        self._dasha_table = None
        self._scroll_area = None
        self._level_buttons = {}
        self._options_btn = None

        super().__init__(widget_id=widget_id, title=title)

        # Larger default size for this widget
        container = self.widget()
        if container:
            container.setMinimumWidth(280)
            container.resize(300, 400)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(4)

        # Control bar with 1-5 buttons and cog
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(2)

        for i in range(1, 6):
            btn = QPushButton(str(i))
            btn.setFixedSize(24, 24)
            btn.setCheckable(True)
            btn.setChecked(i == self._levels)
            btn.clicked.connect(lambda checked, level=i: self._on_level_clicked(level))
            self._level_buttons[i] = btn
            control_layout.addWidget(btn)

        control_layout.addStretch()

        self._options_btn = QPushButton("⚙")
        self._options_btn.setFixedSize(24, 24)
        self._options_btn.setToolTip("Options")
        self._options_btn.clicked.connect(self._show_options_menu)
        control_layout.addWidget(self._options_btn)

        layout.addWidget(control_bar)

        # Scrollable table area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._dasha_table = self._create_dasha_table()
        self._scroll_area.setWidget(self._dasha_table)
        layout.addWidget(self._scroll_area)

        return content

    def _create_dasha_table(self):
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Dasha", "Start", "Age"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setStretchLastSection(False)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        table.setColumnWidth(0, 90)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 60)
        table.verticalHeader().setDefaultSectionSize(18)

        return table

    def _on_level_clicked(self, level):
        self._levels = level
        for i, btn in self._level_buttons.items():
            btn.setChecked(i == level)
        if self._last_chart:
            self.update_from_chart(self._last_chart)

    def _show_options_menu(self):
        menu = QMenu(self._options_btn)

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
            action.setChecked(self._year_length == key)
            action.triggered.connect(lambda checked, k=key: self._set_year_length(k))
        menu.addMenu(year_menu)
        menu.addSeparator()

        planet_menu = QMenu("Base Planet", menu)
        for key, label in [("Moon", "Moon"), ("Sun", "Sun"), ("Lagna", "Lagna (Ascendant)")]:
            action = planet_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._base_planet == key)
            action.triggered.connect(lambda checked, k=key: self._set_base_planet(k))
        menu.addMenu(planet_menu)

        menu.exec(self._options_btn.mapToGlobal(QPoint(0, self._options_btn.height())))

    def _set_year_length(self, length):
        self._year_length = length
        if self._last_chart:
            self.update_from_chart(self._last_chart)

    def _set_base_planet(self, planet):
        self._base_planet = planet
        if self._last_chart:
            self.update_from_chart(self._last_chart)

    def update_from_chart(self, chart) -> None:
        self._last_chart = chart

        if not hasattr(self, "_dasha_table") or self._dasha_table is None:
            return

        self._dasha_table.setRowCount(0)

        try:
            from libaditya.calc.vimshottari import (
                calculate_vimshottari_dasha,
                calculate_specific_period,
            )
            from libaditya import constants as const

            # Resolve base planet
            planets = dict(chart.rashi().planets().items())
            base = None
            if self._base_planet == "Moon":
                base = planets.get("Moon")
            elif self._base_planet == "Sun":
                base = planets.get("Sun")
            elif self._base_planet == "Lagna":
                cusps = chart.rashi().cusps()
                if cusps:
                    base = cusps[0]

            if base is None:
                self._set_empty()
                return

            yrlen = const.dasha_years.get(self._year_length, 365.2422)

            # Get first_dasha index (cheap at dlevels=1)
            result = calculate_vimshottari_dasha(base, dlevels=1, yrlen=yrlen)
            if not result or len(result) < 2:
                self._set_empty()
                return
            _beginning_age = result.pop()
            first_dasha = result.pop()

            birth_jd = chart.context.timeJD.jd_number()
            now_jd = _today_jd()

            # Build rows and get the last highlighted row for scrolling
            last_current_row = self._populate(base, first_dasha, birth_jd, now_jd, yrlen)

            # Scroll the QScrollArea so the deepest current row is visible
            if last_current_row >= 0 and self._scroll_area:
                row_height = self._dasha_table.verticalHeader().defaultSectionSize()
                header_height = self._dasha_table.horizontalHeader().height()
                row_y = header_height + last_current_row * row_height
                viewport_h = self._scroll_area.viewport().height()
                # Center the row in the viewport
                scroll_to = max(0, row_y - viewport_h // 2)
                self._scroll_area.verticalScrollBar().setValue(scroll_to)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._set_empty()

    def _populate(self, base, first_dasha, birth_jd, now_jd, yrlen):
        """Populate the table. Returns the row index of the deepest current period."""
        from libaditya.calc.vimshottari import calculate_specific_period

        last_current_row = -1

        def recurse(lord_path, depth):
            nonlocal last_current_row
            start_lord = lord_path[-1] if lord_path else first_dasha
            for i in range(9):
                lord_idx = (start_lord + i) % 9
                path = lord_path + [lord_idx]
                start_jd_obj, dur_days = calculate_specific_period(base, path, yrlen)
                start_jd = start_jd_obj.jd_number()
                end_jd = start_jd + dur_days

                label = "-".join(_LORD_ABBREV[l] for l in path)

                # Age from birth in solar years
                age = (start_jd - birth_jd) / _SOLAR_YEAR

                is_current = start_jd <= now_jd < end_jd

                row = self._add_row(label, start_jd, age, is_current)
                if is_current:
                    last_current_row = row

                if depth < self._levels:
                    recurse(path, depth + 1)

        recurse([], 1)
        return last_current_row

    def _add_row(self, label, start_jd, age, is_current):
        """Add a row and return its index."""
        row = self._dasha_table.rowCount()
        self._dasha_table.insertRow(row)

        item = QTableWidgetItem(label)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._dasha_table.setItem(row, 0, item)

        date_str = _jd_to_datetime(start_jd).strftime("%m/%d/%Y %H:%M")
        item = QTableWidgetItem(date_str)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._dasha_table.setItem(row, 1, item)

        age_years = int(age)
        age_months = int((age - age_years) * 12)
        item = QTableWidgetItem(f"{age_years}y {age_months}m")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._dasha_table.setItem(row, 2, item)

        if is_current:
            brush = QBrush(QColor(100, 200, 100, 100))
            for col in range(3):
                self._dasha_table.item(row, col).setBackground(brush)

        return row

    def _set_empty(self):
        self._dasha_table.setRowCount(1)
        for col, text in enumerate(["No dasha data", "available", ""]):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._dasha_table.setItem(0, col, item)
