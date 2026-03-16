from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QApplication, QTabBar,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QShortcut, QKeySequence

from gandiva.widgets.chart_input import ChartInputPanel
from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView
from gandiva.themes import get_theme, DEFAULT_THEME, make_app_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gandiva — libaditya")
        self.resize(1200, 700)

        # ── chart registry ────────────────────────────────────────────────────
        # Each entry: {"chart": Chart, "key": birth_key, "state": birth_state}
        self._charts: list[dict] = []
        self._current_idx: int   = -1

        # ── chart tab bar (hidden until 2+ charts) ────────────────────────────
        self.chart_tab_bar = QTabBar()
        self.chart_tab_bar.setTabsClosable(True)
        self.chart_tab_bar.setMovable(True)
        self.chart_tab_bar.setExpanding(False)
        self.chart_tab_bar.setVisible(False)
        self.chart_tab_bar.currentChanged.connect(self._on_chart_tab_changed)
        self.chart_tab_bar.tabCloseRequested.connect(self._on_chart_tab_close)

        # ── left panel ────────────────────────────────────────────────────────
        self.input_panel = ChartInputPanel()
        self.input_panel.chart_created.connect(self.on_chart_created)
        self.input_panel.theme_changed.connect(self._on_theme_changed)
        self.input_panel.no_changes.connect(self._on_no_changes)

        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(
            lambda: self.input_panel.adjust_font(+1)
        )
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(
            lambda: self.input_panel.adjust_font(-1)
        )
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(
            lambda: self.input_panel.adjust_font(0)
        )

        # ── center: chart scene + view ───────────────────────────────────────
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        self.chart_scene.set_chart_style("Western Wheel")

        # ── splitter: chart wheel + collapsible content panel ────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.chart_view)
        self.splitter.addWidget(self.input_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.input_panel.splitter = self.splitter

        # ── sidebar tab bar lives outside the splitter so it's always visible ─
        # When the content panel collapses to 0, the chart fills the splitter
        # and only this thin strip remains on the right edge.
        splitter = self.splitter
        sidebar_tab_bar = self.input_panel.tab_bar
        content_row = QWidget()
        cr_layout   = QHBoxLayout(content_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(0)
        cr_layout.addWidget(splitter, stretch=1)
        cr_layout.addWidget(sidebar_tab_bar)

        # ── root layout: chart tabs on top, content row below ─────────────────
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.chart_tab_bar)
        root_layout.addWidget(content_row, stretch=1)
        self.setCentralWidget(root)

        # ── theme ─────────────────────────────────────────────────────────────
        saved_theme = QSettings("gandiva", "gandiva").value("theme", DEFAULT_THEME)
        self.input_panel.theme_combo.blockSignals(True)
        self.input_panel.theme_combo.setCurrentText(saved_theme)
        self.input_panel.theme_combo.blockSignals(False)
        self._apply_theme(saved_theme)

        # ── initial chart ─────────────────────────────────────────────────────
        self.input_panel.calculate()

        # ── set initial splitter sizes after layout is ready ─────────────────
        from gandiva.widgets.chart_input import EXPANDED_WIDTH
        self.splitter.setSizes([self.width() - EXPANDED_WIDTH, EXPANDED_WIDTH])

    # ── chart display ─────────────────────────────────────────────────────────

    def _display_chart(self, chart):
        self.chart_scene.set_chart(chart)
        self.input_panel.update_info(chart)

    # ── called by ChartInputPanel when Calculate is pressed ───────────────────

    def on_chart_created(self, chart):
        new_key     = self.input_panel.get_birth_key()
        birth_state = self.input_panel.get_birth_state()
        label       = chart.context.name.strip() or f"Chart {len(self._charts) + 1}"

        if (self._current_idx >= 0
                and self._charts[self._current_idx]["key"] == new_key):
            # Same birth info — recalculate (display options changed), update tab
            self._charts[self._current_idx].update(
                {"chart": chart, "state": birth_state}
            )
            self.chart_tab_bar.setTabText(self._current_idx, label)
        else:
            # New birth info — open in a new tab
            self._charts.append({"chart": chart, "key": new_key,
                                  "state": birth_state})
            self.chart_tab_bar.blockSignals(True)
            self.chart_tab_bar.addTab(label)
            self._current_idx = len(self._charts) - 1
            self.chart_tab_bar.setCurrentIndex(self._current_idx)
            self.chart_tab_bar.blockSignals(False)
            self._refresh_tab_bar()

        self._display_chart(chart)

    # ── tab bar events ────────────────────────────────────────────────────────

    def _on_chart_tab_changed(self, index):
        if 0 <= index < len(self._charts):
            self._current_idx = index
            entry = self._charts[index]
            self.input_panel.set_birth_state(entry["state"])
            self._display_chart(entry["chart"])

    def _on_chart_tab_close(self, index):
        if len(self._charts) <= 1:
            return
        self._charts.pop(index)
        self.chart_tab_bar.removeTab(index)
        self._current_idx = self.chart_tab_bar.currentIndex()
        self._refresh_tab_bar()
        if 0 <= self._current_idx < len(self._charts):
            entry = self._charts[self._current_idx]
            self.input_panel.set_birth_state(entry["state"])
            self._display_chart(entry["chart"])

    def _refresh_tab_bar(self):
        self.chart_tab_bar.setVisible(len(self._charts) > 1)

    # ── no changes notification ────────────────────────────────────────────

    def _on_no_changes(self):
        self.statusBar().showMessage("No changes to calculate", 3000)

    # ── theme ─────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, name: str):
        self._apply_theme(name)

    def _apply_theme(self, name: str):
        QSettings("gandiva", "gandiva").setValue("theme", name)
        theme = get_theme(name)
        QApplication.instance().setStyleSheet(make_app_stylesheet(theme))
        self.chart_scene.set_theme(name)
