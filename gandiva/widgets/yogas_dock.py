from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
)
from PyQt6.QtCore import QSize


_YOGA_CATEGORIES = [
    "Nabhasa Yogas",
    "Mahapurusha Yogas",
    "Solar Yogas",
    "Lunar Yogas",
    "Named Yogas",
]

_NABHASA_CATEGORY_ORDER = ["Ashraya", "Dala", "Sankhya", "Akriti"]

DEFAULT_FONT_SIZE = 14


class YogasWidget(QWidget):
    """Yogas dock — dropdown category selector + stacked display pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = DEFAULT_FONT_SIZE

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
            tree.setIndentation(14)
            tree.setRootIsDecorated(True)
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

    def sizeHint(self):
        return QSize(420, 300)

    def update_from_chart(self, chart):
        if chart is None:
            return
        rashi = chart.rashi()

        # Nabhasa Yogas — grouped by category, then alphabetical
        tree = self._trees["Nabhasa Yogas"]
        tree.clear()
        yogas = rashi.nabhasa_yogas()
        groups = {}
        for y in yogas:
            category = getattr(y, 'category', 'Akriti')
            groups.setdefault(category, []).append(y)
        for cat in _NABHASA_CATEGORY_ORDER:
            cat_yogas = groups.get(cat, [])
            if not cat_yogas:
                continue
            cat_item = QTreeWidgetItem(tree, [cat, "", "", ""])
            f = cat_item.font(0)
            f.setBold(True)
            cat_item.setFont(0, f)
            for y in sorted(cat_yogas, key=lambda y: y.to_move):
                QTreeWidgetItem(cat_item, [
                    y.name, cat, y.translation, str(y.to_move),
                ])
            cat_item.setExpanded(True)

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

        # Named Yogas — reserved for yogas not shown in other categories
        tree = self._trees["Named Yogas"]
        tree.clear()

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = DEFAULT_FONT_SIZE
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        style = f"QWidget {{ font-size: {self._font_size}px; }}"
        self.setStyleSheet(style)
