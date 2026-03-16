"""QGraphicsView subclass that hosts the ChartScene."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsView, QFrame

from gandiva.scene.chart_scene import ChartScene


class ChartView(QGraphicsView):
    """View that hosts the chart scene. Handles resize propagation."""

    def __init__(self, scene: ChartScene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport().rect()
        rect = QRectF(0, 0, vp.width(), vp.height())
        self._scene.resize_chart(rect)
