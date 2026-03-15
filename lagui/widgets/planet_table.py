from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt


class PlanetTableWidget(QTableWidget):
    COLUMNS = ["Planet", "Longitude", "Sign", "Nakshatra", "Dignity", "Speed"]

    def __init__(self):
        super().__init__()
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)

    def update_from_chart(self, chart):
        rashi = chart.rashi()
        planets = rashi.planets()

        rows = []
        for name, planet in planets.items():
            try:
                rows.append([
                    str(name),
                    str(planet.longitude()),
                    str(planet.sign_name()),
                    str(planet.nakshatra_name()),
                    str(planet.dignity()),
                    f"{planet.longitude_speed():.4f}",
                ])
            except Exception:
                continue

        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(r, c, item)
