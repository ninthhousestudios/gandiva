"""Left panel with overlay and widget toggle checkboxes."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabBar, QStackedWidget, QCheckBox, QLabel,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal,
)

from gandiva.overlays import OVERLAYS
from gandiva.info_widgets import INFO_WIDGETS


PANEL_WIDTH = 180
ANIM_DURATION_MS = 220

_TAB_OVERLAYS = 0
_TAB_WIDGETS = 1
_TAB_COLLAPSE = 2


class LeftPanel(QWidget):
    """Collapsible left panel for toggling overlays and info widgets."""

    overlay_toggled = pyqtSignal(str, bool)
    widget_toggled = pyqtSignal(str, bool)

    def _get_panel_width(self):
        return self.width()

    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, 'splitter') and self.splitter:
            total = self.splitter.width()
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                remaining = total - w - sizes[2]
                self.splitter.setSizes([w, remaining, sizes[2]])

    panel_width = pyqtProperty(int, _get_panel_width, _set_panel_width)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.splitter = None
        self.setFixedWidth(PANEL_WIDTH)
        self._expanded = True
        self._current_tab = 0
        self._anim = None

        self.tab_bar = QTabBar()
        self.tab_bar.setShape(QTabBar.Shape.RoundedWest)
        self.tab_bar.addTab("Overlays")
        self.tab_bar.addTab("Widgets")
        self.tab_bar.addTab("          ")
        self.tab_bar.setTabToolTip(0, "Overlays")
        self.tab_bar.setTabToolTip(1, "Info Widgets")
        self.tab_bar.tabBarClicked.connect(self._on_tab_clicked)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # Overlays page
        overlay_page = QWidget()
        ol_layout = QVBoxLayout(overlay_page)
        ol_layout.setContentsMargins(6, 6, 6, 6)
        ol_layout.setSpacing(4)

        self._overlay_checks: dict[str, QCheckBox] = {}
        for overlay_id in OVERLAYS:
            cb = QCheckBox(overlay_id)
            cb.stateChanged.connect(
                lambda state, oid=overlay_id: self.overlay_toggled.emit(
                    oid, state == Qt.CheckState.Checked.value
                )
            )
            ol_layout.addWidget(cb)
            self._overlay_checks[overlay_id] = cb

        if not OVERLAYS:
            ol_layout.addWidget(QLabel("No overlays available yet"))

        ol_layout.addStretch()
        self.stack.addWidget(overlay_page)

        # Widgets page
        widget_page = QWidget()
        wl_layout = QVBoxLayout(widget_page)
        wl_layout.setContentsMargins(6, 6, 6, 6)
        wl_layout.setSpacing(4)

        self._widget_checks: dict[str, QCheckBox] = {}
        for widget_id in INFO_WIDGETS:
            cb = QCheckBox(widget_id)
            cb.stateChanged.connect(
                lambda state, wid=widget_id: self.widget_toggled.emit(
                    wid, state == Qt.CheckState.Checked.value
                )
            )
            wl_layout.addWidget(cb)
            self._widget_checks[widget_id] = cb

        if not INFO_WIDGETS:
            wl_layout.addWidget(QLabel("No widgets available yet"))

        wl_layout.addStretch()
        self.stack.addWidget(widget_page)

        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    def on_overlay_removed(self, overlay_id: str):
        cb = self._overlay_checks.get(overlay_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def on_widget_removed(self, widget_id: str):
        cb = self._widget_checks.get(widget_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def uncheck_all_overlays(self):
        for cb in self._overlay_checks.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def _on_tab_clicked(self, idx):
        if idx == _TAB_COLLAPSE:
            self.tab_bar.setCurrentIndex(self._current_tab)
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
            return

        if idx == self._current_tab and self._expanded:
            self.setFixedWidth(self.width())
            self.stack.hide()
            self._expanded = False
            self._animate_to(0, on_finished=lambda: self.setVisible(False))
        else:
            self._current_tab = idx
            self._expanded = True
            self.tab_bar.setCurrentIndex(idx)
            if not self.isVisible():
                self.setFixedWidth(1)
                self.setVisible(True)
            self.stack.setCurrentIndex(idx)
            self.stack.show()
            self._animate_to(PANEL_WIDTH)

    def _animate_to(self, target_w: int, on_finished=None):
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        self._anim = QPropertyAnimation(self, b"panel_width")
        self._anim.setDuration(ANIM_DURATION_MS)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target_w)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if on_finished:
            self._anim.finished.connect(on_finished)
        self._anim.finished.connect(lambda: setattr(self, "_anim", None))
        self._anim.start()
