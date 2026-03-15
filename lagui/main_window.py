from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
)
from PyQt6.QtCore import Qt

from lagui.widgets.chart_input import ChartInputPanel
from lagui.widgets.planet_table import PlanetTableWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("lagui — libaditya")
        self.resize(1200, 700)

        self.chart = None

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.input_panel = ChartInputPanel()
        self.input_panel.chart_created.connect(self.on_chart_created)
        splitter.addWidget(self.input_panel)

        self.planet_table = PlanetTableWidget()
        splitter.addWidget(self.planet_table)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        # load a default chart on startup
        self.input_panel.calculate()

    def on_chart_created(self, chart):
        self.chart = chart
        self.planet_table.update_from_chart(chart)
