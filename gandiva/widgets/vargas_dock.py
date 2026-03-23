from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter

from gandiva.widgets.chart_panel import varga_display_name


# All varga codes in display order
_VARGA_CODES = [
    1, -2, 2, -3, 3, -4, 4, 5, 7, 9,
    -10, -100, -12, -16, -20, -24, -240,
    -27, 30, -40, -45, -60,
]


class VargaActionWidget(QWidget):
    """Row of action buttons + optional mini chart for a varga."""

    pop_out = pyqtSignal(int)
    make_main = pyqtSignal(int)
    side_by_side = pyqtSignal(int)

    def __init__(self, varga_code: int, parent=None):
        super().__init__(parent)
        self._varga_code = varga_code
        self._chart = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Mini chart preview
        self._preview = QLabel()
        self._preview.setFixedSize(300, 300)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background: #1a1a2a; border: 1px solid #333;"
        )
        layout.addWidget(self._preview)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        pop_btn = QPushButton("\u2b0d")  # ⬍
        pop_btn.setToolTip("Pop out as floating window")
        pop_btn.setFixedSize(28, 24)
        pop_btn.clicked.connect(lambda: self.pop_out.emit(self._varga_code))
        btn_layout.addWidget(pop_btn)

        main_btn = QPushButton("\u25f1")  # ◱
        main_btn.setToolTip("Open as main chart view")
        main_btn.setFixedSize(28, 24)
        main_btn.clicked.connect(
            lambda: self.make_main.emit(self._varga_code)
        )
        btn_layout.addWidget(main_btn)

        sbs_btn = QPushButton("\u25eb")  # ◫
        sbs_btn.setToolTip("View side by side")
        sbs_btn.setFixedSize(28, 24)
        sbs_btn.clicked.connect(
            lambda: self.side_by_side.emit(self._varga_code)
        )
        btn_layout.addWidget(sbs_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def update_preview(self, chart, style_name="Western Wheel"):
        """Render a mini chart preview as a pixmap."""
        self._chart = chart
        if chart is None:
            self._preview.clear()
            return

        from gandiva.scene.chart_scene import ChartScene
        from gandiva.widgets.chart_panel import _VargaAsChart
        from PyQt6.QtCore import QRectF

        scene = ChartScene()
        scene.set_chart_style(style_name)
        scene.resize_chart(QRectF(0, 0, 300, 300))
        if self._varga_code == 1:
            scene.set_chart(chart)
        else:
            varga = chart.varga(self._varga_code)
            scene.set_chart(_VargaAsChart(varga, chart.context))

        pixmap = QPixmap(300, 300)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, QRectF(0, 0, 300, 300))
        painter.end()
        self._preview.setPixmap(pixmap)


class VargasWidget(QWidget):
    """Vargas dock — collapsible tree of all divisional charts."""

    varga_pop_out = pyqtSignal(int)
    varga_make_main = pyqtSignal(int)
    varga_side_by_side = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._chart_style = "Western Wheel"
        self._font_size = 14
        self._action_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setIndentation(14)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded())
            if item.childCount() > 0 else None
        )
        layout.addWidget(self._tree)

        self._build_tree()

        # Lazy-load previews on expand
        self._tree.itemExpanded.connect(self._on_item_expanded)

    def _build_tree(self):
        """Build the collapsible varga tree."""
        for code in _VARGA_CODES:
            item = QTreeWidgetItem([f"D-{abs(code)}"])
            self._tree.addTopLevelItem(item)
            item.setExpanded(False)

            child = QTreeWidgetItem()
            item.addChild(child)
            action = VargaActionWidget(code)
            action.pop_out.connect(self.varga_pop_out.emit)
            action.make_main.connect(self.varga_make_main.emit)
            action.side_by_side.connect(self.varga_side_by_side.emit)
            self._tree.setItemWidget(child, 0, action)
            self._action_widgets[code] = (item, action)

        # Custom Parivritti entry
        custom_item = QTreeWidgetItem(["Custom Parivritti"])
        self._tree.addTopLevelItem(custom_item)

        child = QTreeWidgetItem()
        custom_item.addChild(child)
        custom_widget = QWidget()
        cl = QVBoxLayout(custom_widget)
        cl.setContentsMargins(4, 4, 4, 4)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Division:"))
        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(2, 360)
        self._custom_spin.setValue(11)
        input_row.addWidget(self._custom_spin)
        input_row.addStretch()
        cl.addLayout(input_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for symbol, tooltip, signal in [
            ("\u2b0d", "Pop out", self.varga_pop_out),
            ("\u25f1", "Open as main", self.varga_make_main),
            ("\u25eb", "Side by side", self.varga_side_by_side),
        ]:
            btn = QPushButton(symbol)
            btn.setToolTip(tooltip)
            btn.setFixedSize(28, 24)
            btn.clicked.connect(
                lambda checked, s=signal: s.emit(self._custom_spin.value())
            )
            btn_row.addWidget(btn)
        btn_row.addStretch()
        cl.addLayout(btn_row)

        self._tree.setItemWidget(child, 0, custom_widget)

    def set_chart_style(self, style_name: str):
        """Update chart style used for varga previews."""
        if style_name == self._chart_style:
            return
        self._chart_style = style_name
        # Re-render any currently expanded previews
        if self._chart is not None:
            for code, (item, action) in self._action_widgets.items():
                if item.isExpanded():
                    action.update_preview(self._chart, self._chart_style)

    def update_from_chart(self, chart):
        """Update varga names and mini previews."""
        self._chart = chart
        if chart is None:
            return
        for code, (item, action) in self._action_widgets.items():
            try:
                name = varga_display_name(chart.context, code)
                item.setText(0, f"{name} (D-{abs(code)})")
            except Exception:
                item.setText(0, f"D-{abs(code)}")
            if item.isExpanded():
                action.update_preview(chart, self._chart_style)

    def _on_item_expanded(self, item):
        """Lazy-load mini preview when a varga row is expanded."""
        for code, (tree_item, action) in self._action_widgets.items():
            if tree_item is item and self._chart is not None:
                action.update_preview(self._chart, self._chart_style)
                break

    def adjust_font(self, delta: int):
        if delta == 0:
            self._font_size = 14
        else:
            self._font_size = max(10, min(28, self._font_size + delta))
        style = f"QWidget {{ font-size: {self._font_size}px; }}"
        self.setStyleSheet(style)
