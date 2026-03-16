"""Dasha info widget — displays current Vimshottari dasha periods."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont

from gandiva.info_widgets.base import InfoWidget


class DashaWidget(InfoWidget):
    """Compact current dasha period display."""

    def __init__(self, widget_id: str = "Dasha Periods", title: str = "Dasha Periods", **kwargs):
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(2)

        self._maha_label = QLabel("Maha: —")
        self._antar_label = QLabel("Antar: —")
        self._pratyantar_label = QLabel("Pratyantar: —")

        font = QFont()
        font.setPointSize(9)
        for label in (self._maha_label, self._antar_label, self._pratyantar_label):
            label.setFont(font)
            layout.addWidget(label)

        layout.addStretch()
        return content

    def update_from_chart(self, chart) -> None:
        try:
            from libaditya import current_vimshottari_dasha
            from libaditya import constants as const

            planets = dict(chart.rashi().planets().items())
            moon = planets.get("Moon")
            if moon is None:
                self._set_empty()
                return

            result = current_vimshottari_dasha(
                moon, nowtimeJD=chart.context.timeJD, dlevels=3
            )
            if len(result) < 4:
                self._set_empty()
                return

            lords = [const.vimshottari_dashas[i][0] for i in result[:3]]

            self._maha_label.setText(f"Maha: {lords[0]}")
            self._antar_label.setText(f"Antar: {lords[1]}")
            self._pratyantar_label.setText(f"Pratyantar: {lords[2]}")
        except Exception:
            self._set_empty()

    def _set_empty(self):
        self._maha_label.setText("Maha: —")
        self._antar_label.setText("Antar: —")
        self._pratyantar_label.setText("Pratyantar: —")
