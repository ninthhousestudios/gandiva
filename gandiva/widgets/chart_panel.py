from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView


class ChartPanel(QWidget):
    """Self-contained chart rendering unit.

    Wraps a ChartView + ChartScene. Knows its chart and varga_number.
    Can display an optional header bar (for secondary panels).
    Emits `clicked` when the user clicks anywhere on the panel.
    """

    clicked = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, show_header: bool = False, parent=None):
        super().__init__(parent)
        self._chart = None
        self._varga_number = None  # None = rashi
        self._active = False
        self._show_header = show_header

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # Optional header bar
        self._header = QFrame()
        self._header.setFrameShape(QFrame.Shape.NoFrame)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        self._header_label = QLabel("Rashi")
        self._header_label.setStyleSheet("font-size: 11px; color: #aaa;")
        header_layout.addWidget(self._header_label)
        header_layout.addStretch()
        close_btn = QPushButton("\u2715")  # ✕
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.setStyleSheet("color: #e88; font-size: 12px;")
        close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_btn)
        self._header.setVisible(show_header)
        layout.addWidget(self._header)

        # Chart scene + view
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        layout.addWidget(self.chart_view)

    @property
    def varga_number(self):
        return self._varga_number

    @property
    def chart(self):
        return self._chart

    @property
    def active(self):
        return self._active

    def set_active(self, active: bool):
        self._active = active
        border = "1px solid #5566aa" if active else "1px solid transparent"
        self.setStyleSheet(f"ChartPanel {{ border: {border}; }}")

    def set_chart(self, chart, varga_number=None):
        """Update the displayed chart. varga_number=None means rashi."""
        self._chart = chart
        self._varga_number = varga_number
        if chart is None:
            return
        if varga_number is not None:
            varga_chart = chart.varga(varga_number)
            self.chart_scene.set_chart(varga_chart)
        else:
            # Pass Chart object directly — renderer calls .rashi() internally
            self.chart_scene.set_chart(chart)

        # Update header label
        if self._show_header and varga_number is not None:
            from libaditya.calc.varga import Varga
            name = Varga(chart.context, varga_number).varga_name()
            self._header_label.setText(name)
        elif self._show_header:
            self._header_label.setText("Rashi")

    def set_chart_style(self, style_name: str):
        self.chart_scene.set_chart_style(style_name)

    def set_theme(self, name: str):
        self.chart_scene.set_theme(name)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
