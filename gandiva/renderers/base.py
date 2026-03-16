"""Abstract base class for chart renderers."""

import math

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtWidgets import QGraphicsObject


class ChartRenderer(QGraphicsObject):
    """Base class for all chart style renderers.

    Subclasses must implement:
        - paint(painter, option, widget)
        - update_from_chart(chart)
    """

    planet_selected = pyqtSignal(str)  # planet name, or "" for deselection

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rect = QRectF()
        self._theme = None
        self._chart = None

    def boundingRect(self) -> QRectF:
        return self._rect

    def resize(self, rect: QRectF) -> None:
        """Called by ChartScene when the view resizes."""
        self.prepareGeometryChange()
        self._rect = rect
        self.update()

    def set_theme(self, theme: dict) -> None:
        """Store theme dict and trigger repaint."""
        self._theme = theme
        self.update()

    def update_from_chart(self, chart) -> None:
        """Extract data from chart and trigger repaint. Subclasses must override."""
        self._chart = chart
        self.update()

    def paint(self, painter, option, widget=None) -> None:
        """Subclasses must implement."""
        raise NotImplementedError
