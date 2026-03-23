"""Mini varga info widget — displays a divisional chart with varga selector."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QGraphicsScene, QGraphicsView,
)
from PyQt6.QtGui import QColor

from gandiva.info_widgets.base import InfoWidget
from gandiva.renderers import CHART_STYLES


MINI_SIZE = 380

# Varga codes and display names (populated lazily from chart context)
_VARGA_CODES = [
    1, -2, 2, -3, 3, -4, 4, 5, 7, 9,
    -10, -100, -12, -16, -20, -24, -240,
    -27, 30, -40, -45, -60,
]


class MiniVargaWidget(InfoWidget):
    """Displays a divisional chart using the current chart style, with varga selector."""

    def __init__(self, widget_id: str = "Mini Varga", title: str = "Varga",
                 varga: int = 9, **kwargs):
        self._varga_code = varga
        self._chart = None
        self._chart_style_name = "Western Wheel"
        self._renderer = None
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Varga selector
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Varga:"))
        self._varga_combo = QComboBox()
        self._varga_combo.setFixedHeight(22)
        for code in _VARGA_CODES:
            self._varga_combo.addItem(f"D-{abs(code)}", code)
        # Set initial selection
        for i in range(self._varga_combo.count()):
            if self._varga_combo.itemData(i) == self._varga_code:
                self._varga_combo.setCurrentIndex(i)
                break
        self._varga_combo.currentIndexChanged.connect(self._on_varga_changed)
        selector_row.addWidget(self._varga_combo)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        # Chart preview
        self._mini_scene = QGraphicsScene()
        self._mini_view = QGraphicsView(self._mini_scene)
        self._mini_view.setFixedSize(MINI_SIZE, MINI_SIZE)
        self._mini_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self._mini_view.setStyleSheet("background: transparent;")

        self._scene_rect = QRectF(0, 0, MINI_SIZE, MINI_SIZE)
        self._mini_scene.setSceneRect(self._scene_rect)

        self._install_renderer(self._chart_style_name)
        layout.addWidget(self._mini_view)
        return content

    def _install_renderer(self, style_name: str):
        """Create and install the appropriate renderer for the given style."""
        if self._renderer:
            self._mini_scene.removeItem(self._renderer)
            self._renderer = None

        renderer_class = CHART_STYLES.get(style_name)
        if renderer_class is None:
            return

        self._renderer = renderer_class()
        self._mini_scene.addItem(self._renderer)
        self._renderer.resize(self._scene_rect)
        if self._theme:
            self._renderer.set_theme(self._theme)

    def set_chart_style(self, style_name: str):
        """Switch the renderer to match the main chart style."""
        if style_name == self._chart_style_name and self._renderer is not None:
            return
        self._chart_style_name = style_name
        self._install_renderer(style_name)
        self._refresh()

    def _on_varga_changed(self, index):
        code = self._varga_combo.itemData(index)
        if code is not None:
            self._varga_code = code
            self._refresh()

    def _refresh(self):
        """Re-render the current varga with the current chart and style."""
        if self._chart is None or self._renderer is None:
            return
        try:
            if self._varga_code == 1:
                self._renderer.update_from_chart(self._chart)
            else:
                varga = self._chart.varga(self._varga_code)
                from gandiva.widgets.chart_panel import _VargaAsChart
                self._renderer.update_from_chart(
                    _VargaAsChart(varga, self._chart.context)
                )
        except Exception:
            pass

    def update_from_chart(self, chart) -> None:
        self._chart = chart
        # Update varga names in combo
        if chart is not None:
            from gandiva.widgets.chart_panel import varga_display_name
            for i in range(self._varga_combo.count()):
                code = self._varga_combo.itemData(i)
                try:
                    name = varga_display_name(chart.context, code)
                    self._varga_combo.setItemText(i, f"{name} (D-{abs(code)})")
                except Exception:
                    pass
        self._refresh()

    def set_theme(self, theme: dict) -> None:
        super().set_theme(theme)
        if theme:
            if self._renderer:
                self._renderer.set_theme(theme)
            self._mini_scene.setBackgroundBrush(QColor(theme["bg"]))
