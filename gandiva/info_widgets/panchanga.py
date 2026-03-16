"""Panchanga info widget — displays tithi, nakshatra, yoga, karana, vara."""

from PyQt6.QtWidgets import QWidget, QFormLayout, QLabel

from gandiva.info_widgets.base import InfoWidget


class PanchangaWidget(InfoWidget):
    """Compact panchanga display."""

    def __init__(self, widget_id: str = "Panchanga", title: str = "Panchanga", **kwargs):
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QFormLayout(content)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setVerticalSpacing(3)
        layout.setHorizontalSpacing(8)

        self._tithi_label = QLabel("—")
        self._nakshatra_label = QLabel("—")
        self._yoga_label = QLabel("—")
        self._karana_label = QLabel("—")
        self._vara_label = QLabel("—")

        layout.addRow("Tithi:", self._tithi_label)
        layout.addRow("Nakshatra:", self._nakshatra_label)
        layout.addRow("Yoga:", self._yoga_label)
        layout.addRow("Karana:", self._karana_label)
        layout.addRow("Vara:", self._vara_label)

        return content

    def update_from_chart(self, chart) -> None:
        try:
            p = chart.rashi().panchanga()
            self._tithi_label.setText(f"{p.init_tithi()} ({p.tithi_type()})")
            self._nakshatra_label.setText(str(p.nakshatra()))
            self._yoga_label.setText(str(p.yoga_name()))
            self._karana_label.setText(str(p.karana()))
            self._vara_label.setText(str(p.vara()))
        except Exception:
            self._tithi_label.setText("—")
            self._nakshatra_label.setText("—")
            self._yoga_label.setText("—")
            self._karana_label.setText("—")
            self._vara_label.setText("—")
