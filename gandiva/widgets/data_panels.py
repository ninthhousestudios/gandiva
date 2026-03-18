"""Standalone data display widgets extracted from ChartInputPanel.

Each widget has:
- update_from_chart(chart) — populate from chart data
- adjust_font(delta) — font size control (delta=0 resets)
"""

from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QDockWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QGroupBox,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QGridLayout,
    QPlainTextEdit,
    QFileDialog,
    QRadioButton,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QMenu,
)
from PyQt6.QtCore import Qt, QPoint, QSettings, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont, QFontDatabase

from libaditya import constants as const
from libaditya.read import read_chtk_location


# ── Shared constants ──────────────────────────────────────────────────────────

DEFAULT_FONT_SIZE = 16

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

_SKIP = {"Earth"}

_LORD_ABBREV = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]


# ── Shared helpers ────────────────────────────────────────────────────────────


def _fmt_lon(obj) -> str:
    """Format a planet or cusp longitude per context settings."""
    if obj.context.signize:
        return obj.in_sign_longitude()
    return str(obj.amsha_longitude())


def _make_style(pt: int) -> str:
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
        QLabel       {{ font-size: {pt}px; }}
    """


def _monospace_font():
    """Preferred: Source Code Pro Semibold; fallback: monospace."""
    font = QFontDatabase.font("Source Code Pro", "Semibold", 10)
    if not font.family().lower().startswith("source"):
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
    return font


# ── PlanetsWidget ─────────────────────────────────────────────────────────────


class PlanetPanel(QWidget):
    """Individual planet panel with title bar and tree. Tree stays put."""

    pop_out_requested = pyqtSignal(str)  # planet_name

    def __init__(self, planet_name: str, parent=None):
        super().__init__(parent)
        self.planet_name = planet_name
        self._font_size = DEFAULT_FONT_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Header with title and pop-out button
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)

        self.title_label = QLabel(planet_name)
        self.title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        pop_out_btn = QPushButton("⬍")
        pop_out_btn.setFixedSize(20, 20)
        pop_out_btn.setToolTip("Pop out to floating window")
        pop_out_btn.clicked.connect(self._on_pop_out)
        header_layout.addWidget(pop_out_btn)

        layout.addWidget(header)

        # Tree widget for planet data (STAYS in this panel always)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setIndentation(10)
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded())
        )
        layout.addWidget(self.tree, stretch=1)

    def _on_pop_out(self):
        self.pop_out_requested.emit(self.planet_name)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


class FloatingPlanetDock(QDockWidget):
    """Floating dock for a popped-out planet panel."""

    docked = pyqtSignal(str)  # planet_name

    def __init__(self, planet_name: str, parent=None):
        super().__init__(planet_name, parent)
        self.planet_name = planet_name
        # Start with floatable + closable, will change to just closable when floating
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        # Connect to know when it becomes top-level (floating)
        self.topLevelChanged.connect(self._on_top_level_changed)

    def _on_top_level_changed(self, is_top_level: bool):
        """When dock becomes floating, show only X button. When docked, show both."""
        if is_top_level:
            # Now floating - show only close button (X)
            self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        else:
            # Now docked - show both float and close
            self.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QDockWidget.DockWidgetFeature.DockWidgetClosable
            )

    def closeEvent(self, event):
        # Hide first to prevent re-docking behavior
        self.hide()
        # Remove from parent main window before accepting close
        parent = self.parent()
        if isinstance(parent, QMainWindow):
            parent.removeDockWidget(self)
        self.docked.emit(self.planet_name)
        event.accept()


class PlanetsWidget(QWidget):
    """Widget with 3x4 grid of planet panels, each poppable to floating docks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE
        self._last_chart = None

        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        self.panels: dict[str, PlanetPanel] = {}
        self._floating_docks: dict[str, FloatingPlanetDock] = {}
        self._popped_out: set[str] = set()

        for idx, name in enumerate(_CHART_PLANETS):
            row, col = divmod(idx, 4)
            panel = PlanetPanel(name)
            panel.pop_out_requested.connect(self._on_pop_out)
            layout.addWidget(panel, row, col)
            self.panels[name] = panel

    def _on_pop_out(self, planet_name: str):
        if planet_name in self._popped_out:
            return

        self._popped_out.add(planet_name)
        panel = self.panels[planet_name]

        # Create floating dock with a cloned tree
        dock = FloatingPlanetDock(planet_name, self.window())
        dock.docked.connect(self._on_docked)
        dock.setFloating(True)
        dock.resize(350, 400)

        # Clone the tree content into the dock
        dock_tree = self._clone_tree(panel.tree)
        dock.setWidget(dock_tree)

        panel_pos = panel.mapToGlobal(QPoint(50, 50))
        dock.move(panel_pos)

        parent_mainwindow = self.window()
        if isinstance(parent_mainwindow, QMainWindow):
            parent_mainwindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.show()
        dock.raise_()

        self._floating_docks[planet_name] = dock

    def _clone_tree(self, source_tree: QTreeWidget) -> QTreeWidget:
        """Create a new tree with the same content as the source."""
        new_tree = QTreeWidget()
        new_tree.setHeaderHidden(True)
        new_tree.setColumnCount(2)
        new_tree.setIndentation(10)
        new_tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        new_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        new_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        new_tree.setExpandsOnDoubleClick(False)
        new_tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded())
        )

        # Clone all items
        for i in range(source_tree.topLevelItemCount()):
            source_item = source_tree.topLevelItem(i)
            cloned_item = self._clone_tree_item(source_item)
            new_tree.addTopLevelItem(cloned_item)
            cloned_item.setExpanded(source_item.isExpanded())

        return new_tree

    def _clone_tree_item(self, source_item: QTreeWidgetItem) -> QTreeWidgetItem:
        """Recursively clone a tree item and its children."""
        texts = [source_item.text(c) for c in range(source_item.columnCount())]
        cloned = QTreeWidgetItem(texts)

        # Copy font (bold status)
        f = source_item.font(0)
        cloned.setFont(0, f)

        # Clone children recursively
        for i in range(source_item.childCount()):
            child_clone = self._clone_tree_item(source_item.child(i))
            cloned.addChild(child_clone)

        return cloned

    def _on_docked(self, planet_name: str):
        if planet_name in self._floating_docks:
            dock = self._floating_docks.pop(planet_name)
            dock.deleteLater()

        self._popped_out.discard(planet_name)

    def update_from_chart(self, chart):
        self._last_chart = chart
        planets = dict(chart.rashi().planets().items())

        def bold_item(parent, texts):
            item = QTreeWidgetItem(parent, texts)
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)
            return item

        for name, panel in self.panels.items():
            planet = planets.get(name)
            if planet is None:
                panel.set_title(name)
                continue

            try:
                retro = " (R)" if planet.retrograde() else ""
                panel.set_title(f"{name}{retro}")

                tree = panel.tree
                tree.clear()
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
                    basic, ["Speed", f"{planet.longitude_speed():.4f}\u00b0/day"]
                )
                try:
                    QTreeWidgetItem(
                        basic, ["Latitude", f"{planet.latitude():.4f}\u00b0"]
                    )
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

                bold_item(tree, ["Shadbala", ""])
                bold_item(tree, ["Avasthas", ""])

                for i in range(tree.topLevelItemCount()):
                    item = tree.topLevelItem(i)
                    item.setExpanded(item.text(0) == "Basic")

            except Exception:
                continue

        # Update floating docks if any
        for planet_name, dock in self._floating_docks.items():
            planet = planets.get(planet_name)
            if planet:
                retro = " (R)" if planet.retrograde() else ""
                dock.setWindowTitle(f"{planet_name}{retro}")

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))
        for panel in self.panels.values():
            panel.adjust_font(delta)


# ── CuspsWidget ───────────────────────────────────────────────────────────────


class CuspsWidget(QWidget):
    """Table of house cusps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

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
        layout.addWidget(self.cusp_table)

    def update_from_chart(self, chart):
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

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


# ── NakshatrasWidget ──────────────────────────────────────────────────────────


class NakshatrasWidget(QWidget):
    """Tree grouped by nakshatra showing planets and cusps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

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
        layout.addWidget(self.nakshatra_tree)

    def update_from_chart(self, chart):
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

        groups: dict[str, list] = {}
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

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


# ── DashasWidget ──────────────────────────────────────────────────────────────


class DashasWidget(QWidget):
    """Vimshottari dasha table with level buttons and options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE
        self._last_chart = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Nakshatra Dasha section
        nak_dasha_group = QGroupBox("Nakshatra Dasha (Vimshottari)")
        nd_layout = QVBoxLayout(nak_dasha_group)
        nd_layout.setContentsMargins(4, 4, 4, 4)
        nd_layout.setSpacing(4)

        # Control bar
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

        self._nd_current_btn = QPushButton("\u2316")
        self._nd_current_btn.setFixedSize(24, 24)
        self._nd_current_btn.setToolTip("Go to current dasha")
        self._nd_current_btn.clicked.connect(self._nd_goto_current)
        nd_ctrl_layout.addWidget(self._nd_current_btn)

        self._nd_options_btn = QPushButton("\u2699")
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

        layout.addWidget(nak_dasha_group, stretch=1)

        # Placeholder for Rashi Dasha
        rashi_dasha_group = QGroupBox("Rashi Dasha")
        rd_layout = QVBoxLayout(rashi_dasha_group)
        rd_layout.setContentsMargins(4, 4, 4, 4)
        placeholder = QLabel("Coming soon")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rd_layout.addWidget(placeholder)
        layout.addWidget(rashi_dasha_group, stretch=1)

        self._nd_last_current_row = -1

    def update_from_chart(self, chart):
        self._last_chart = chart
        self._update_nakshatra_dasha(chart)

    def _nd_on_level_clicked(self, level):
        self._nd_levels = level
        for i, btn in self._nd_level_buttons.items():
            btn.setChecked(i == level)
        if self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _nd_show_options_menu(self):
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
            action.triggered.connect(lambda checked, k=key: self._nd_set_year_length(k))
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
            action.triggered.connect(lambda checked, k=key: self._nd_set_base_planet(k))
        menu.addMenu(planet_menu)

        menu.exec(
            self._nd_options_btn.mapToGlobal(QPoint(0, self._nd_options_btn.height()))
        )

    def _nd_set_year_length(self, length):
        self._nd_year_length = length
        if self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _nd_set_base_planet(self, planet):
        self._nd_base_planet = planet
        if self._last_chart:
            self._update_nakshatra_dasha(self._last_chart)

    def _update_nakshatra_dasha(self, chart):
        from datetime import datetime, timedelta
        from libaditya.calc.vimshottari import (
            calculate_vimshottari_dasha,
            calculate_specific_period,
        )

        _SOLAR_YEAR = 365.2422

        self._nd_table.setRowCount(0)

        try:
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

            result = calculate_vimshottari_dasha(base, dlevels=1, yrlen=yrlen)
            if not result or len(result) < 2:
                return
            _beginning_age = result.pop()
            first_dasha = result.pop()

            birth_jd = chart.context.timeJD.jd_number()

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
        row = getattr(self, "_nd_last_current_row", -1)
        if row >= 0 and row < self._nd_table.rowCount():
            self._nd_table.scrollToItem(
                self._nd_table.item(row, 0),
                QTableWidget.ScrollHint.PositionAtCenter,
            )

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


# ── KalaWidget ────────────────────────────────────────────────────────────────


class KalaWidget(QWidget):
    """Kala time info display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._kala_text = QPlainTextEdit()
        self._kala_text.setReadOnly(True)
        self._kala_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._kala_text.setFont(_monospace_font())
        layout.addWidget(self._kala_text)

    def update_from_chart(self, chart):
        import io
        import sys

        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf

        try:
            from libaditya.calc.kala import cardinal_points, lunar_new_year
            from libaditya.calc import Panchanga

            context = chart.context

            year = context.timeJD.year()
            points = cardinal_points(year)
            print(f"Cardinal points for {year}\n")
            print(f"Ascending equinox:\n{points[0]}")
            print(f"Northern solstice:\n{points[1]}")
            print(f"Descending equinox:\n{points[2]}")
            print(f"Southern solstice:\n{points[3]}")

            print("\nLunar new year:\n")
            print(lunar_new_year(context.timeJD).moon())

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

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


# ── PanchangaWidget ───────────────────────────────────────────────────────────


class PanchangaWidget(QWidget):
    """Monthly panchanga table with independent location."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE
        self._last_chart = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Row 1: Month/year navigation
        nav_row = QWidget()
        nav_layout = QHBoxLayout(nav_row)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)

        self._panch_yr_back = QPushButton("\u00ab")
        self._panch_yr_back.setFixedSize(24, 24)
        self._panch_yr_back.setToolTip("Previous year")
        self._panch_mo_back = QPushButton("\u2039")
        self._panch_mo_back.setFixedSize(24, 24)
        self._panch_mo_back.setToolTip("Previous month")

        self._panch_month_spin = QSpinBox()
        self._panch_month_spin.setRange(1, 12)
        self._panch_month_spin.setFixedWidth(50)
        sep_label = QLabel("/")
        self._panch_year_spin = QSpinBox()
        self._panch_year_spin.setRange(-5000, 9999)
        self._panch_year_spin.setFixedWidth(60)

        self._panch_mo_fwd = QPushButton("\u203a")
        self._panch_mo_fwd.setFixedSize(24, 24)
        self._panch_mo_fwd.setToolTip("Next month")
        self._panch_yr_fwd = QPushButton("\u00bb")
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

        self._panch_loc_btn = QPushButton("Location")
        self._panch_loc_btn.setToolTip("Location settings")
        self._panch_loc_btn.clicked.connect(self._panch_show_location)
        nav_layout.addWidget(self._panch_loc_btn)

        layout.addWidget(nav_row)

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

        layout.addWidget(panch_opts)

        # Location state
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
        self._panch_text.setFont(_monospace_font())
        layout.addWidget(self._panch_text)

    def update_from_chart(self, chart):
        self._last_chart = chart
        ctx = chart.context
        loc = ctx.location
        self._panch_location = {
            "placename": loc.placename() if callable(loc.placename) else loc.placename,
            "lat": loc.lat,
            "lon": loc.long,
            "utcoffset": loc.utcoffset,
        }
        self._panch_month_spin.blockSignals(True)
        self._panch_year_spin.blockSignals(True)
        self._panch_month_spin.setValue(ctx.timeJD.month())
        self._panch_year_spin.setValue(ctx.timeJD.year())
        self._panch_month_spin.blockSignals(False)
        self._panch_year_spin.blockSignals(False)
        self._panch_recalc()

    def _panch_shift(self, delta_months):
        m = self._panch_month_spin.value()
        y = self._panch_year_spin.value()
        total = (y * 12 + (m - 1)) + delta_months
        new_y, new_m = divmod(total, 12)
        new_m += 1
        self._panch_month_spin.blockSignals(True)
        self._panch_year_spin.blockSignals(True)
        self._panch_month_spin.setValue(new_m)
        self._panch_year_spin.setValue(new_y)
        self._panch_month_spin.blockSignals(False)
        self._panch_year_spin.blockSignals(False)
        self._panch_recalc()

    def _panch_recalc(self, *_args):
        self._run_panchanga(
            self._panch_month_spin.value(),
            self._panch_year_spin.value(),
        )

    def _panch_show_location(self):
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

        def load_chtk():
            path, _ = QFileDialog.getOpenFileName(
                dlg,
                "Open location from chart",
                "",
                "Kala chart files (*.chtk);;All files (*)",
            )
            if path:
                placename, lat, lon, utcoffset = read_chtk_location(path)
                place_edit.setText(placename)
                lat_spin.setValue(lat)
                lon_spin.setValue(lon)
                utc_spin.setValue(utcoffset)

        chtk_btn = QPushButton("Load from .chtk\u2026")
        chtk_btn.clicked.connect(load_chtk)
        lay.addWidget(chtk_btn)

        def use_chart_loc():
            if self._last_chart:
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

    def _run_panchanga(self, month, year):
        from dataclasses import replace as dc_replace
        from prettytable import PrettyTable
        from libaditya.calc import Panchanga
        from libaditya.objects import JulianDay, EphContext, Location

        try:
            loc = self._panch_location
            utcoffset = loc["utcoffset"]
            location = Location(
                lat=loc["lat"],
                long=loc["lon"],
                placename=loc["placename"],
                utcoffset=utcoffset,
            )

            use_utc = self._panch_utc_radio.isChecked()
            savana = (
                self._panch_mode_savana.isChecked()
                or self._panch_mode_sunrise_cal.isChecked()
            )
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
                "Day",
                "Sunrise",
                "Sunset",
                "Moonrise",
                "Moonset",
                "V",
                "N.V.",
                "N",
                "N.N.",
                "T",
                "N.T.",
                "K.",
                "N.K.",
                "Y",
                "N.Y.",
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
                            dc_replace(
                                panch.context, timeJD=panch.timeJD.shift("f", "day", 1)
                            )
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
                    moonrise,
                    moonset,
                    working_panch.vara(),
                    working_panch.next_vara().timeJD,
                    working_panch.nakshatra(),
                    working_panch.next_nakshatra().timeJD,
                    working_panch.tithi(),
                    working_panch.next_tithi().timeJD,
                    working_panch.karana(),
                    working_panch.next_karana().timeJD,
                    working_panch.yoga_name(),
                    working_panch.next_yoga().timeJD,
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

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        self.setStyleSheet(_make_style(self._font_size))


# ── Registry ──────────────────────────────────────────────────────────────────

from gandiva.widgets.vargas_dock import VargasWidget
from gandiva.widgets.yogas_dock import YogasWidget

DATA_PANELS = {
    "Planets": PlanetsWidget,
    "Cusps": CuspsWidget,
    "Nakshatras": NakshatrasWidget,
    "Dashas": DashasWidget,
    "Kala": KalaWidget,
    "Panchanga": PanchangaWidget,
    "Vargas": VargasWidget,
    "Yogas": YogasWidget,
}
