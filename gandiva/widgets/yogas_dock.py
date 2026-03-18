from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt


_YOGA_CATEGORIES = [
    "Nabhasa Yogas",
    "Mahapurusha Yogas",
    "Solar Yogas",
    "Lunar Yogas",
    "Named Yogas",
]


class YogasWidget(QWidget):
    """Yogas dock — dropdown category selector + stacked display pages."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._combo = QComboBox()
        self._combo.addItems(_YOGA_CATEGORIES)
        layout.addWidget(self._combo)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._trees = {}
        for cat in _YOGA_CATEGORIES:
            tree = QTreeWidget()
            tree.setHeaderHidden(False)
            tree.setIndentation(0)
            tree.setRootIsDecorated(False)
            tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
            self._trees[cat] = tree
            self._stack.addWidget(tree)

        self._combo.currentIndexChanged.connect(self._stack.setCurrentIndex)
        self._setup_columns()

    def _setup_columns(self):
        t = self._trees["Nabhasa Yogas"]
        t.setColumnCount(4)
        t.setHeaderLabels(["Name", "Category", "Translation", "Moves"])
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        t = self._trees["Mahapurusha Yogas"]
        t.setColumnCount(5)
        t.setHeaderLabels(["Name", "Planet", "Present", "House", "Dignity"])
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        t = self._trees["Solar Yogas"]
        t.setColumnCount(3)
        t.setHeaderLabels(["Name", "Present", "Planets"])
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        t = self._trees["Lunar Yogas"]
        t.setColumnCount(3)
        t.setHeaderLabels(["Name", "Present", "Planets"])
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        t = self._trees["Named Yogas"]
        t.setColumnCount(4)
        t.setHeaderLabels(["Name", "Translation", "Houses", "Moves"])
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

    def update_from_chart(self, chart):
        if chart is None:
            return
        rashi = chart.rashi()

        tree = self._trees["Nabhasa Yogas"]
        tree.clear()
        for y in rashi.nabhasa_yogas():
            # nabhasa_yogas() returns mixed NabhasaYoga + AkritiYoga
            category = getattr(y, 'category', 'Akriti')
            QTreeWidgetItem(tree, [
                y.name, category, y.translation, str(y.to_move),
            ])

        tree = self._trees["Mahapurusha Yogas"]
        tree.clear()
        for y in rashi.panchamahapurusha_yogas():
            QTreeWidgetItem(tree, [
                y.name, y.planet,
                "\u2713" if y.present else "\u2717",
                str(y.house), y.dignity,
            ])

        tree = self._trees["Solar Yogas"]
        tree.clear()
        for y in rashi.solar_yogas():
            planets_str = ", ".join(y.planets) if y.planets else "\u2014"
            QTreeWidgetItem(tree, [
                y.name, "\u2713" if y.present else "\u2717", planets_str,
            ])

        tree = self._trees["Lunar Yogas"]
        tree.clear()
        for y in rashi.lunar_yogas():
            planets_str = ", ".join(y.planets) if y.planets else "\u2014"
            QTreeWidgetItem(tree, [
                y.name, "\u2713" if y.present else "\u2717", planets_str,
            ])

        tree = self._trees["Named Yogas"]
        tree.clear()
        for y in rashi.akriti_yogas():
            houses_str = ", ".join(str(h) for h in y.houses)
            QTreeWidgetItem(tree, [
                y.name, y.translation, houses_str, str(y.to_move),
            ])

    def adjust_font(self, delta: int):
        pass
