"""Mini varga info widget — displays a small divisional chart."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QColor

from gandiva.info_widgets.base import InfoWidget
from gandiva.renderers.south_indian import SouthIndianRenderer


MINI_SIZE = 240


class _VargaAdapter:
    """Makes a Varga quack like a Chart for renderer consumption.

    Note: .context is the original chart's context (not the varga's internal
    context). This is intentional — the renderer reads context.circle and
    context.print_outer_planets from it, which should reflect the user's
    top-level settings.
    """

    def __init__(self, varga, original_chart):
        self._varga = varga
        self.context = original_chart.context

    def rashi(self):
        return self._varga


class MiniVargaWidget(InfoWidget):
    """Displays a small divisional chart using an embedded renderer."""

    def __init__(self, widget_id: str = "Mini Varga", title: str = "Mini Varga",
                 varga: int = 9, **kwargs):
        self._varga_code = varga
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        content.setFixedSize(MINI_SIZE, MINI_SIZE)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Embedded scene + view + renderer
        self._mini_scene = QGraphicsScene()
        self._mini_view = QGraphicsView(self._mini_scene)
        self._mini_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mini_view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self._mini_view.setStyleSheet("background: transparent;")

        self._mini_renderer = SouthIndianRenderer()
        self._mini_scene.addItem(self._mini_renderer)

        rect = QRectF(0, 0, MINI_SIZE, MINI_SIZE)
        self._mini_scene.setSceneRect(rect)
        self._mini_renderer.resize(rect)

        layout.addWidget(self._mini_view)
        return content

    def update_from_chart(self, chart) -> None:
        try:
            varga = chart.varga(self._varga_code)
            adapted = _VargaAdapter(varga, chart)
            self._mini_renderer.update_from_chart(adapted)
        except Exception:
            pass

    def set_theme(self, theme: dict) -> None:
        super().set_theme(theme)
        if theme:
            self._mini_renderer.set_theme(theme)
            self._mini_scene.setBackgroundBrush(QColor(theme["bg"]))
