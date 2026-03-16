"""Base class for draggable info widgets in the chart scene."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGraphicsProxyWidget, QGraphicsItem, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton,
)


class InfoWidget(QGraphicsProxyWidget):
    """Draggable info panel embedded in the chart scene.

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

        # Build container with chrome
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

        # Enable dragging and selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        # Default size
        container.setFixedWidth(220)

    @property
    def widget_id(self) -> str:
        return self._widget_id

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

        close_btn = QPushButton("×")
        close_btn.setObjectName("info_widget_close")
        close_btn.setFixedSize(18, 18)
        close_btn.setFlat(True)
        close_btn.clicked.connect(lambda: self.closed.emit(self._widget_id))
        close_btn.setVisible(False)
        self._close_btn = close_btn
        layout.addWidget(close_btn)

        return bar

    def build_content(self) -> QWidget:
        """Subclasses must implement. Returns the content widget."""
        raise NotImplementedError

    def update_from_chart(self, chart) -> None:
        """Subclasses must override to update content from chart data."""
        pass

    def set_theme(self, theme: dict) -> None:
        """Apply theme colors to the widget chrome and content."""
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

    # -- hover show/hide close button ------------------------------------------

    def hoverEnterEvent(self, event):
        self._close_btn.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._close_btn.setVisible(False)
        super().hoverLeaveEvent(event)

    # -- click to raise --------------------------------------------------------

    def mousePressEvent(self, event):
        # Raise to top of widget stack
        siblings = [item for item in self.scene().items()
                    if isinstance(item, InfoWidget)]
        if siblings:
            max_z = max(s.zValue() for s in siblings)
            self.setZValue(max_z + 1)
        super().mousePressEvent(event)
