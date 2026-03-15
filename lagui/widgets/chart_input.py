from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QDoubleSpinBox, QSpinBox, QDateTimeEdit, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, QDateTime

from libaditya import Chart, EphContext, Location, JulianDay, Circle
from libaditya import constants as const


class ChartInputPanel(QWidget):
    chart_created = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)

        # --- Name ---
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Chart name")
        form.addRow("Name:", self.name_edit)

        # --- Date/Time ---
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        form.addRow("Date/Time:", self.datetime_edit)

        # --- UTC Offset ---
        self.utcoffset_spin = QDoubleSpinBox()
        self.utcoffset_spin.setRange(-12.0, 14.0)
        self.utcoffset_spin.setDecimals(1)
        self.utcoffset_spin.setSingleStep(0.5)
        self.utcoffset_spin.setValue(0.0)
        form.addRow("UTC Offset:", self.utcoffset_spin)

        layout.addLayout(form)

        # --- Location ---
        loc_group = QGroupBox("Location")
        loc_form = QFormLayout(loc_group)

        self.placename_edit = QLineEdit("Yamakoti")
        loc_form.addRow("Place:", self.placename_edit)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setValue(23.1765)
        loc_form.addRow("Latitude:", self.lat_spin)

        self.long_spin = QDoubleSpinBox()
        self.long_spin.setRange(-180.0, 180.0)
        self.long_spin.setDecimals(4)
        self.long_spin.setValue(75.7885)
        loc_form.addRow("Longitude:", self.long_spin)

        layout.addWidget(loc_group)

        # --- Calculation Options ---
        calc_group = QGroupBox("Options")
        calc_form = QFormLayout(calc_group)

        self.zodiac_combo = QComboBox()
        self.zodiac_combo.addItems(["Aditya", "Tropical", "Sidereal"])
        calc_form.addRow("Zodiac:", self.zodiac_combo)

        self.ayanamsa_spin = QSpinBox()
        self.ayanamsa_spin.setRange(0, 100)
        self.ayanamsa_spin.setValue(98)
        calc_form.addRow("Ayanamsa:", self.ayanamsa_spin)

        self.hsys_combo = QComboBox()
        self.hsys_combo.addItems(["P — Placidus", "C — Campanus", "R — Regiomontanus", "W — Whole Sign"])
        self.hsys_combo.setCurrentIndex(1)
        calc_form.addRow("Houses:", self.hsys_combo)

        layout.addWidget(calc_group)

        # --- Calculate button ---
        self.calc_button = QPushButton("Calculate")
        self.calc_button.clicked.connect(self.calculate)
        layout.addWidget(self.calc_button)

        layout.addStretch()

    def calculate(self):
        dt = self.datetime_edit.dateTime().toPyDateTime()
        utcoffset = self.utcoffset_spin.value()

        hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        time_tuple = (dt.year, dt.month, dt.day, hour_decimal)
        jd = JulianDay(time_tuple, utcoffset=utcoffset)

        location = Location(
            lat=self.lat_spin.value(),
            long=self.long_spin.value(),
            placename=self.placename_edit.text(),
            utcoffset=utcoffset,
        )

        zodiac_text = self.zodiac_combo.currentText()
        if zodiac_text == "Tropical":
            sysflg = const.ECL
            circle = Circle.ZODIAC
            sign_names = "zodiac"
        elif zodiac_text == "Sidereal":
            sysflg = const.SID
            circle = Circle.ZODIAC
            sign_names = "zodiac"
        else:  # Aditya
            sysflg = const.ECL
            circle = Circle.ADITYA
            sign_names = "adityas"

        hsys_char = self.hsys_combo.currentText()[0]

        context = EphContext(
            name=self.name_edit.text(),
            timeJD=jd,
            location=location,
            sysflg=sysflg,
            ayanamsa=self.ayanamsa_spin.value(),
            hsys=hsys_char,
            circle=circle,
            sign_names=sign_names,
        )

        chart = Chart(context=context)
        self.chart_created.emit(chart)
