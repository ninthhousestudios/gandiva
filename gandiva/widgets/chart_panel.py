from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView


def varga_display_name(context, varga_number):
    """Return a display name for a varga, including the division number for custom parivrittis."""
    from libaditya.calc.varga import Varga
    name = Varga(context, varga_number).varga_name()
    if name == "parivritti":
        return f"Parivritti {abs(varga_number)}"
    return name


class _VargaPlanetProxy:
    """Proxy a Planet so ecliptic_longitude() returns the varga (amsha) longitude."""

    _is_varga_proxy = True

    def __init__(self, planet):
        self._planet = planet

    def ecliptic_longitude(self):
        return self._planet.amsha_longitude()

    def __getattr__(self, name):
        return getattr(self._planet, name)


class _VargaCuspProxy:
    """Proxy a Cusp so ecliptic_longitude() returns the varga (amsha) longitude."""

    _is_varga_proxy = True

    def __init__(self, cusp):
        self._cusp = cusp

    def ecliptic_longitude(self):
        return self._cusp.amsha_longitude()

    def __getattr__(self, name):
        return getattr(self._cusp, name)


class _VargaPlanetsProxy:
    """Proxy the Planets collection, wrapping each planet with _VargaPlanetProxy."""

    def __init__(self, planets):
        self._planets = planets
        self._proxied = {name: _VargaPlanetProxy(p) for name, p in planets.items()}

    def items(self):
        return self._proxied.items()

    def __getitem__(self, key):
        return self._proxied[key]

    def __iter__(self):
        return iter(self._proxied)

    def __len__(self):
        return len(self._proxied)

    def __getattr__(self, name):
        return getattr(self._planets, name)


class _VargaCuspsProxy:
    """Proxy the Cusps collection, wrapping each cusp with _VargaCuspProxy.

    Preserves 1-indexed access: cusps[1] returns the first cusp (matching
    the libaditya Cusps convention).
    """

    def __init__(self, cusps):
        self._cusps = cusps
        self._proxied = [_VargaCuspProxy(c) for c in cusps]

    def __getitem__(self, n):
        return self._proxied[n - 1]

    def __iter__(self):
        return iter(self._proxied)

    def __len__(self):
        return len(self._proxied)

    def __getattr__(self, name):
        return getattr(self._cusps, name)


class _VargaAsRashi:
    """Wraps a Varga so it looks like a Rashi to renderers.

    Renderers call chart.rashi() then .planets()/.cusps() on the result,
    positioning items via .ecliptic_longitude(). For vargas, we proxy those
    to return amsha_longitude() so planets appear at their varga positions.
    """

    def __init__(self, varga):
        self._varga = varga
        self._proxied_planets = _VargaPlanetsProxy(varga.planets())
        self._proxied_cusps = _VargaCuspsProxy(varga.cusps())

    def planets(self):
        return self._proxied_planets

    def cusps(self):
        return self._proxied_cusps

    def __getattr__(self, name):
        return getattr(self._varga, name)


class _VargaAsChart:
    """Thin wrapper so a Varga can be passed to renderers that call .rashi()."""

    def __init__(self, varga, context):
        self._varga = varga
        self._rashi_proxy = _VargaAsRashi(varga)
        self.context = context

    def rashi(self):
        return self._rashi_proxy

    def __getattr__(self, name):
        return getattr(self._varga, name)


class ChartPanel(QWidget):
    """Self-contained chart rendering unit.

    Wraps a ChartView + ChartScene. Knows its chart and varga_number.
    Can display an optional header bar (for secondary panels).
    Emits `clicked` when the user clicks anywhere on the panel.
    """

    clicked = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, show_header: bool = False, parent=None):
        super().__init__(parent)
        self._chart = None
        self._varga_number = None  # None = rashi
        self._active = False
        self._show_header = show_header

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # Optional header bar
        self._header = QFrame()
        self._header.setFrameShape(QFrame.Shape.NoFrame)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        self._header_label = QLabel("Rashi")
        self._header_label.setStyleSheet("font-size: 11px; color: #aaa;")
        header_layout.addWidget(self._header_label)
        header_layout.addStretch()
        self._close_btn = QPushButton("\u2715")  # ✕
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setFlat(True)
        self._close_btn.setStyleSheet("color: #e88; font-size: 12px;")
        self._close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self._close_btn)
        self._close_btn.setVisible(show_header)
        self._header.setVisible(show_header)
        layout.addWidget(self._header)

        # Active indicator star (top-left corner)
        self._star = QLabel("\u2605")  # ★
        self._star.setStyleSheet("font-size: 18px; color: #ffcc00; background: transparent;")
        self._star.setFixedSize(24, 24)
        self._star.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._star.setVisible(False)

        # Chart scene + view
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        layout.addWidget(self.chart_view)

        # Float the star over the chart view
        self._star.setParent(self.chart_view)
        self._star.move(4, 4)
        self._star.raise_()

    @property
    def varga_number(self):
        return self._varga_number

    @property
    def chart(self):
        return self._chart

    @property
    def active(self):
        return self._active

    def set_header_visible(self, visible: bool):
        """Show or hide the header label (without close button)."""
        self._header.setVisible(visible)
        self._show_header = visible

    def set_active(self, active: bool):
        self._active = active
        self._star.setVisible(active)

    def set_chart(self, chart, varga_number=None):
        """Update the displayed chart. varga_number=None means rashi."""
        self._chart = chart
        self._varga_number = varga_number
        if chart is None:
            return
        if varga_number is not None:
            varga = chart.varga(varga_number)
            # Wrap varga so renderer can call .rashi() on it
            self.chart_scene.set_chart(_VargaAsChart(varga, chart.context))
        else:
            # Pass Chart object directly — renderer calls .rashi() internally
            self.chart_scene.set_chart(chart)

        # Update header label (always, even if not yet visible)
        if varga_number is not None:
            self._header_label.setText(varga_display_name(chart.context, varga_number))
        else:
            self._header_label.setText("Rashi")

    def set_chart_style(self, style_name: str):
        self.chart_scene.set_chart_style(style_name)

    def set_theme(self, name: str):
        self.chart_scene.set_theme(name)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
