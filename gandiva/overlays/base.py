"""Abstract base class for chart overlays."""

from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import QGraphicsObject


class ChartOverlay(QGraphicsObject):
    """Semi-transparent layer drawn over the chart.

    Subclasses must implement:
        - paint(painter, option, widget)
        - update_from_chart(chart)
    """

    compatible_styles: set[str] = set()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rect = QRectF()
        self._theme = None
        self._chart = None

    def boundingRect(self) -> QRectF:
        return self._rect

    def resize(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._rect = rect
        self.update()

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        self.update()

    def update_from_chart(self, chart) -> None:
        self._chart = chart
        self.update()

    def paint(self, painter, option, widget=None) -> None:
        raise NotImplementedError
