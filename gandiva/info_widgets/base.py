"""Base class for draggable, resizable info widgets in the chart scene."""

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPointF, QEvent, QRectF
from PyQt6.QtGui import QFont, QPen, QColor
from PyQt6.QtWidgets import (
    QGraphicsProxyWidget,
    QGraphicsItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

_GRIP_SIZE = 14


class _DragEventFilter(QObject):
    """Event filter that enables dragging the proxy widget by its title bar."""

    def __init__(self, proxy, parent=None):
        super().__init__(parent)
        self._proxy = proxy
        self._dragging = False
        self._drag_start_pos = None
        self._drag_mouse_start = None

    def eventFilter(self, a0, a1):
        event = a1
        obj = a0

        if self._proxy is None:
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                widget = obj
                while widget:
                    if isinstance(widget, QPushButton):
                        return False
                    widget = widget.parent()

                self._dragging = True
                self._drag_start_pos = self._proxy.pos()
                self._drag_mouse_start = QPointF(event.globalPosition())

                if self._proxy.scene():
                    siblings = [
                        item
                        for item in self._proxy.scene().items()
                        if isinstance(item, InfoWidget)
                    ]
                    if siblings:
                        max_z = max(s.zValue() for s in siblings)
                        self._proxy.setZValue(max_z + 1)

                event.accept()
                return True

        elif event.type() == QEvent.Type.MouseMove:
            if self._dragging and self._drag_start_pos is not None:
                delta = QPointF(event.globalPosition()) - self._drag_mouse_start
                new_pos = self._drag_start_pos + delta
                self._proxy.setPos(new_pos)
                event.accept()
                return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton and self._dragging:
                self._dragging = False
                self._drag_start_pos = None
                self._drag_mouse_start = None
                event.accept()
                return True

        return False


class InfoWidget(QGraphicsProxyWidget):
    """Draggable, resizable info panel embedded in the chart scene.

    Subclasses must implement:
        - build_content() -> QWidget
        - update_from_chart(chart)
    """

    closed = pyqtSignal(str)  # emits widget_id when X clicked

    def __init__(self, widget_id: str, title: str, parent=None):
        super().__init__(parent)
        self._widget_id = widget_id
        self._title = title
        self._theme = None
        self._minimized = False

        # Resize state
        self._resizing = False
        self._resize_start_mouse = None
        self._resize_start_size = None

        # Build container
        container = QWidget()
        container.setObjectName("info_widget_container")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        self._title_bar = self._build_title_bar(title)
        layout.addWidget(self._title_bar)

        # Content from subclass
        self._content = self.build_content()
        layout.addWidget(self._content)

        self.setWidget(container)

        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        container.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Title bar drag
        self._drag_filter = _DragEventFilter(self)
        self._title_bar.installEventFilter(self._drag_filter)
        for child in self._title_bar.findChildren(QWidget):
            if isinstance(child, QLabel):
                child.installEventFilter(self._drag_filter)

        # Default size
        container.setMinimumSize(150, 80)
        container.resize(220, container.sizeHint().height())

    @property
    def widget_id(self) -> str:
        return self._widget_id

    def _grip_rect(self) -> QRectF:
        """Grip region in scene-local (item) coordinates."""
        r = self.boundingRect()
        return QRectF(r.right() - _GRIP_SIZE, r.bottom() - _GRIP_SIZE,
                       _GRIP_SIZE, _GRIP_SIZE)

    # -- painting -----------------------------------------------------------

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self._minimized:
            return
        # Draw grip lines on top of the rendered widget
        pen = QPen(QColor(128, 128, 128, 160))
        pen.setWidth(1)
        painter.setPen(pen)
        r = self.boundingRect()
        bx, by = r.right(), r.bottom()
        for offset in (4, 8, 12):
            painter.drawLine(QPointF(bx, by - offset), QPointF(bx - offset, by))

    # -- title bar ----------------------------------------------------------

    def _build_title_bar(self, title: str) -> QWidget:
        bar = QWidget()
        bar.setObjectName("info_widget_title_bar")
        bar.setFixedHeight(24)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("info_widget_title")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addStretch()

        min_btn = QPushButton("−")
        min_btn.setObjectName("info_widget_minimize")
        min_btn.setFixedSize(18, 18)
        min_btn.setFlat(True)
        min_btn.clicked.connect(self._toggle_minimize)
        min_btn.setVisible(False)
        self._minimize_btn = min_btn
        layout.addWidget(min_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("info_widget_close")
        close_btn.setFixedSize(18, 18)
        close_btn.setFlat(True)
        close_btn.clicked.connect(lambda: self.closed.emit(self._widget_id))
        close_btn.setVisible(False)
        self._close_btn = close_btn
        layout.addWidget(close_btn)

        return bar

    # -- subclass interface -------------------------------------------------

    def build_content(self) -> QWidget:
        """Subclasses must implement. Returns the content widget."""
        raise NotImplementedError

    def update_from_chart(self, chart) -> None:
        """Subclasses must override to update content from chart data."""
        pass

    # -- theming ------------------------------------------------------------

    def set_theme(self, theme: dict) -> None:
        self._theme = theme
        container = self.widget()
        if container and theme:
            bg = theme["ui_bg"]
            text = theme["ui_text"]
            border = theme["ui_border"]
            accent = theme["ui_accent"]
            container.setStyleSheet(f"""
                #info_widget_container {{
                    background-color: rgba({bg.red()},{bg.green()},{bg.blue()},230);
                    border: 1px solid rgb({border.red()},{border.green()},{border.blue()});
                    border-radius: 6px;
                }}
                #info_widget_title_bar {{
                    background-color: rgba({accent.red()},{accent.green()},{accent.blue()},60);
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }}
                #info_widget_title {{
                    color: rgb({text.red()},{text.green()},{text.blue()});
                    background: transparent;
                }}
                #info_widget_close {{
                    color: rgb({text.red()},{text.green()},{text.blue()});
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                }}
                #info_widget_close:hover {{
                    color: rgb({accent.red()},{accent.green()},{accent.blue()});
                }}
                QLabel {{
                    color: rgb({text.red()},{text.green()},{text.blue()});
                    background: transparent;
                }}
            """)

    # -- minimize -----------------------------------------------------------

    def _toggle_minimize(self):
        self._minimized = not self._minimized
        self._content.setVisible(not self._minimized)

        container = self.widget()
        if container:
            if self._minimized:
                self._pre_minimize_size = container.size()
                container.setFixedHeight(24)
            else:
                container.setMinimumHeight(80)
                container.setMaximumHeight(16777215)
                if hasattr(self, "_pre_minimize_size"):
                    container.resize(self._pre_minimize_size)
                else:
                    container.adjustSize()

        self._minimize_btn.setText("+" if self._minimized else "−")

    # -- hover show/hide buttons --------------------------------------------

    def hoverEnterEvent(self, event):
        self._minimize_btn.setVisible(True)
        self._close_btn.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._minimize_btn.setVisible(False)
        self._close_btn.setVisible(False)
        super().hoverLeaveEvent(event)

    # -- mouse: raise, resize, cursor --------------------------------------

    def hoverMoveEvent(self, event):
        if not self._minimized and self._grip_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        # Raise to top
        if self.scene():
            siblings = [
                item for item in self.scene().items() if isinstance(item, InfoWidget)
            ]
            if siblings:
                max_z = max(s.zValue() for s in siblings)
                self.setZValue(max_z + 1)

        # Start resize if clicking the grip
        if (not self._minimized
                and event.button() == Qt.MouseButton.LeftButton
                and self._grip_rect().contains(event.pos())):
            self._resizing = True
            self._resize_start_mouse = event.scenePos()
            self._resize_start_size = self.widget().size()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_start_mouse is not None:
            delta = event.scenePos() - self._resize_start_mouse
            container = self.widget()
            new_w = max(container.minimumWidth(),
                        int(self._resize_start_size.width() + delta.x()))
            new_h = max(container.minimumHeight(),
                        int(self._resize_start_size.height() + delta.y()))
            container.resize(new_w, new_h)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_start_mouse = None
            self._resize_start_size = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

