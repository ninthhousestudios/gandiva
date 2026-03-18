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

    def _populate_yoga_tree(self, tree, rashi, method_name, row_builder):
        """Safely populate a yoga tree, handling missing methods."""
        tree.clear()
        method = getattr(rashi, method_name, None)
        if method is None:
            QTreeWidgetItem(tree, ["Not yet available in libaditya"])
            return
        try:
            for y in method():
                row_builder(tree, y)
        except Exception:
            QTreeWidgetItem(tree, ["Error loading yogas"])

    def update_from_chart(self, chart):
        if chart is None:
            return
        rashi = chart.rashi()

        self._populate_yoga_tree(
            self._trees["Nabhasa Yogas"], rashi, "nabhasa_yogas",
            lambda t, y: QTreeWidgetItem(t, [
                y.name, getattr(y, 'category', ''),
                getattr(y, 'translation', ''), str(y.to_move),
            ])
        )

        self._populate_yoga_tree(
            self._trees["Mahapurusha Yogas"], rashi, "panchamahapurusha_yogas",
            lambda t, y: QTreeWidgetItem(t, [
                y.name, y.planet,
                "\u2713" if y.present else "\u2717",
                str(y.house), y.dignity,
            ])
        )

        self._populate_yoga_tree(
            self._trees["Solar Yogas"], rashi, "solar_yogas",
            lambda t, y: QTreeWidgetItem(t, [
                y.name, "\u2713" if y.present else "\u2717",
                ", ".join(y.planets) if y.planets else "\u2014",
            ])
        )

        self._populate_yoga_tree(
            self._trees["Lunar Yogas"], rashi, "lunar_yogas",
            lambda t, y: QTreeWidgetItem(t, [
                y.name, "\u2713" if y.present else "\u2717",
                ", ".join(y.planets) if y.planets else "\u2014",
            ])
        )

        self._populate_yoga_tree(
            self._trees["Named Yogas"], rashi, "akriti_yogas",
            lambda t, y: QTreeWidgetItem(t, [
                y.name if hasattr(y, 'name') else str(y[0]),
                getattr(y, 'translation', ''),
                ", ".join(str(h) for h in y.houses) if hasattr(y, 'houses') else '',
                str(y.to_move) if hasattr(y, 'to_move') else str(y[1]),
            ])
        )

    def adjust_font(self, delta: int):
        pass
