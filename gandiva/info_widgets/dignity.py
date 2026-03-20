"""Dignity info widget — displays dignity, baladi, jagradadi, and sign lord for each planet."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QHBoxLayout, QLabel,
)
from PyQt6.QtGui import QFont

from gandiva.info_widgets.base import InfoWidget

# Planet display order and unicode symbols
_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

_PLANET_SYMBOLS = {
    "Sun": "\u2609", "Moon": "\u263D", "Mars": "\u2642",
    "Mercury": "\u263F", "Jupiter": "\u2643", "Venus": "\u2640",
    "Saturn": "\u2644", "Rahu": "\u260A", "Ketu": "\u260B",
    "Uranus": "\u2645", "Neptune": "\u2646", "Pluto": "\u2647",
    "Lg": "Lg",
}

_COLUMNS = ["", "Dign", "Baladi", "Jagradadi", "Lord"]


class DignityWidget(InfoWidget):
    """Displays a dignity table: planet glyph, dignity, baladi, jagradadi, sign lord."""

    def __init__(self, widget_id: str = "Dignity", title: str = "Dignity",
                 varga: int = 1, **kwargs):
        self._varga_code = varga
        self._chart = None
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Varga selector
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Varga:"))
        self._varga_combo = QComboBox()
        self._varga_combo.setFixedHeight(22)
        from gandiva.info_widgets.mini_varga import _VARGA_CODES
        for code in _VARGA_CODES:
            self._varga_combo.addItem(f"D-{abs(code)}", code)
        for i in range(self._varga_combo.count()):
            if self._varga_combo.itemData(i) == self._varga_code:
                self._varga_combo.setCurrentIndex(i)
                break
        self._varga_combo.currentIndexChanged.connect(self._on_varga_changed)
        selector_row.addWidget(self._varga_combo)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        # Table: 9 rows (7 planets + Lagna + blank separator potential), 5 columns
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setShowGrid(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(1, len(_COLUMNS)):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)
        return content

    def _on_varga_changed(self, index):
        code = self._varga_combo.itemData(index)
        if code is not None:
            self._varga_code = code
            self._refresh()

    def _refresh(self):
        if self._chart is None:
            return
        try:
            if self._varga_code == 1:
                rashi = self._chart.rashi()
            else:
                rashi = self._chart.varga(self._varga_code)

            planets_dict = dict(rashi.planets().items())
            signs = rashi.signs()

            # Build rows: 7 karakas + Lagna
            rows = []
            for pname in _PLANETS:
                planet = planets_dict.get(pname)
                if planet is None:
                    continue
                sym = _PLANET_SYMBOLS.get(pname, pname[:2])
                dig = planet.dignity() or ""
                try:
                    baladi = planet.baladi_avastha()
                except Exception:
                    baladi = ""
                try:
                    jagradadi = planet.jagradadi_avastha()
                except Exception:
                    jagradadi = ""
                try:
                    sign_num = planet.sign()
                    lord_name = signs[sign_num].lord()
                    lord_sym = _PLANET_SYMBOLS.get(lord_name, lord_name[:2])
                except Exception:
                    lord_sym = ""
                rows.append((sym, dig, baladi, jagradadi, lord_sym))

            # Lagna row
            try:
                cusp1 = rashi.cusps()[1]
                sign_num = cusp1.sign()
                lord_name = signs[sign_num].lord()
                lord_sym = _PLANET_SYMBOLS.get(lord_name, lord_name[:2])
                rows.append(("Lg", "", "", "", lord_sym))
            except Exception:
                pass

            # Populate table
            self._table.setRowCount(len(rows))
            sym_font = QFont("Sans", 14)
            for r, (sym, dig, baladi, jagradadi, lord_sym) in enumerate(rows):
                # Planet symbol
                item = QTableWidgetItem(sym)
                item.setFont(sym_font)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 0, item)
                # Dignity
                item = QTableWidgetItem(dig)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 1, item)
                # Baladi
                item = QTableWidgetItem(baladi)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 2, item)
                # Jagradadi
                item = QTableWidgetItem(jagradadi)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 3, item)
                # Lord
                item = QTableWidgetItem(lord_sym)
                item.setFont(sym_font)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, 4, item)

        except Exception:
            pass

    def update_from_chart(self, chart) -> None:
        self._chart = chart
        # Update varga names in combo
        if chart is not None:
            from gandiva.widgets.chart_panel import varga_display_name
            for i in range(self._varga_combo.count()):
                code = self._varga_combo.itemData(i)
                try:
                    name = varga_display_name(chart.context, code)
                    self._varga_combo.setItemText(i, f"{name} (D-{abs(code)})")
                except Exception:
                    pass
        self._refresh()
