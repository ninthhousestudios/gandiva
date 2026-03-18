"""QGraphicsView subclass that hosts the ChartScene."""

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QWheelEvent
from PyQt6.QtWidgets import QGraphicsView, QGraphicsProxyWidget, QFrame, QApplication

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

    def wheelEvent(self, event):
        """Forward wheel events to scrollable widgets inside proxy items."""
        scene_pos = self.mapToScene(event.position().toPoint())
        item = self._scene.itemAt(scene_pos, self.transform())

        # Walk up to find a QGraphicsProxyWidget
        proxy = None
        while item is not None:
            if isinstance(item, QGraphicsProxyWidget):
                proxy = item
                break
            item = item.parentItem()

        if proxy is None:
            event.ignore()
            return

        # Map scene position into the proxy's embedded widget coordinates
        proxy_pos = proxy.mapFromScene(scene_pos)
        embedded = proxy.widget()
        if embedded is None:
            event.ignore()
            return

        # Find the deepest child widget at this position
        local_pos = QPointF(proxy_pos.x(), proxy_pos.y())
        target = embedded.childAt(int(local_pos.x()), int(local_pos.y()))
        if target is None:
            target = embedded

        # Walk up to find a scrollable widget (one with a vertical scroll bar)
        widget = target
        while widget is not None:
            sb = getattr(widget, 'verticalScrollBar', None)
            if sb is not None and callable(sb):
                scrollbar = sb()
                if scrollbar is not None and scrollbar.maximum() > 0:
                    # Build a new wheel event with position local to the target
                    widget_pos = widget.mapFrom(embedded, local_pos.toPoint())
                    new_event = QWheelEvent(
                        QPointF(widget_pos),
                        event.globalPosition(),
                        event.pixelDelta(),
                        event.angleDelta(),
                        event.buttons(),
                        event.modifiers(),
                        event.phase(),
                        event.inverted(),
                    )
                    QApplication.sendEvent(widget, new_event)
                    event.accept()
                    return
            widget = widget.parent()

        event.ignore()
