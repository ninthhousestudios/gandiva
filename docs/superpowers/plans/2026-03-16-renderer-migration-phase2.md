# Renderer Migration — Phase 2: Chart Style Switching, Left Panel, Overlays, Info Widgets

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the framework for chart style switching, overlay toggling, and info widgets — then populate it with the first two info widgets (Panchanga and Dasha).

**Architecture:** A left panel mirrors the right panel's collapsible tab behavior. ChartScene gains real overlay/widget management. InfoWidget uses QGraphicsProxyWidget to embed regular QWidgets in the scene with draggable chrome (title bar + close button).

**Tech Stack:** Python 3, PyQt6 (QGraphicsProxyWidget, QPropertyAnimation), libaditya

**Branch:** `renderer-migration` (continues from Phase 1)

**Spec:** `docs/superpowers/specs/2026-03-16-chart-scene-architecture-design.md`

**Phase 1 plan:** `docs/superpowers/plans/2026-03-16-renderer-migration-phase1.md`

---

## What already exists (Phase 1 output)

```
gandiva/
  scene/
    chart_scene.py       # ChartScene — has overlay/widget stubs (add_overlay, add_info_widget are pass)
    chart_view.py        # ChartView
  renderers/
    __init__.py          # CHART_STYLES = {"Western Wheel": WesternWheelRenderer}
    base.py              # ChartRenderer(QGraphicsObject) ABC
    western_wheel.py     # WesternWheelRenderer
  main_window.py         # Uses ChartScene/ChartView, 2-way splitter (chart_view + input_panel)
  widgets/
    chart_input.py       # ChartInputPanel — 7 tabs, no chart style dropdown yet
```

Key signals already defined on ChartScene: `overlay_added(str)`, `overlay_removed(str)`, `widget_added(str)`, `widget_removed(str)`.

`set_chart_style()` already removes old renderer, instantiates new one, clears overlays.

---

## Chunk 1: Chart Style Dropdown + Overlay/Widget Registries

### Task 1: Add chart style dropdown to Display tab

**Files:**
- Modify: `gandiva/widgets/chart_input.py` (lines 320-400, Display tab section)

The Display tab (page 2 in the stack) needs a "Chart Style" dropdown at the top, populated from the renderer registry.

- [ ] **Step 1: Add the signal and dropdown**

In `ChartInputPanel` class definition (around line 96), add a new signal:

```python
chart_style_changed = pyqtSignal(str)  # style name from CHART_STYLES
```

In the Display tab section (page 2, around line 320), add the chart style dropdown as the FIRST group in `disp_layout`, before the existing "Display" group:

```python
        # ── page 2: display options ───────────────────────────────────────────
        disp_page   = QWidget()
        disp_layout = QVBoxLayout(disp_page)
        disp_layout.setContentsMargins(6, 4, 6, 4)
        disp_layout.setSpacing(6)

        # Chart Style
        style_group = QGroupBox("Chart Style")
        style_form  = QFormLayout(style_group)
        style_form.setVerticalSpacing(3)
        style_form.setHorizontalSpacing(6)

        from gandiva.renderers import CHART_STYLES
        self.chart_style_combo = QComboBox()
        self.chart_style_combo.addItems(list(CHART_STYLES.keys()))
        self.chart_style_combo.currentTextChanged.connect(self.chart_style_changed)
        style_form.addRow("Style:", self.chart_style_combo)

        disp_layout.addWidget(style_group)

        # Display (existing group follows...)
```

- [ ] **Step 2: Wire in MainWindow**

In `gandiva/main_window.py`, add a connection after the existing signal connections (around line 37):

```python
self.input_panel.chart_style_changed.connect(self._on_chart_style_changed)
```

Add the handler method:

```python
def _on_chart_style_changed(self, style_name: str):
    self.chart_scene.set_chart_style(style_name)
```

- [ ] **Step 3: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Display tab shows "Chart Style" dropdown at the top with "Western Wheel" selected
- Changing to "Western Wheel" (it's the only option for now) doesn't break anything
- All other Display tab options still work

- [ ] **Step 4: Commit**

```bash
git add gandiva/widgets/chart_input.py gandiva/main_window.py
git commit -m "add chart style dropdown to Display tab"
```

---

### Task 2: Create overlay and info widget registries + base classes

**Files:**
- Create: `gandiva/overlays/__init__.py`
- Create: `gandiva/overlays/base.py`
- Create: `gandiva/info_widgets/__init__.py`
- Create: `gandiva/info_widgets/base.py`

- [ ] **Step 1: Create overlay base**

Create `gandiva/overlays/__init__.py`:
```python
"""Overlay registry."""

OVERLAYS: dict[str, type] = {}
```

Create `gandiva/overlays/base.py`:
```python
"""Abstract base class for chart overlays."""

from PyQt6.QtCore import QRectF, pyqtSignal
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
```

- [ ] **Step 2: Create info widget base**

Create `gandiva/info_widgets/__init__.py`:
```python
"""Info widget registry.

Each entry is (widget_class, kwargs_dict) so one class can appear
multiple times with different configuration.
"""

INFO_WIDGETS: dict[str, tuple] = {}
```

Create `gandiva/info_widgets/base.py`:

```python
"""Base class for draggable info widgets in the chart scene."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
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

    # ── hover show/hide close button ───────────────────────────────────────

    def hoverEnterEvent(self, event):
        self._close_btn.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._close_btn.setVisible(False)
        super().hoverLeaveEvent(event)

    # ── click to raise ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        # Raise to top of widget stack
        siblings = [item for item in self.scene().items()
                    if isinstance(item, InfoWidget)]
        if siblings:
            max_z = max(s.zValue() for s in siblings)
            self.setZValue(max_z + 1)
        super().mousePressEvent(event)
```

- [ ] **Step 3: Verify imports**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.overlays.base import ChartOverlay; print('OK')"
python -c "from gandiva.info_widgets.base import InfoWidget; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add gandiva/overlays/ gandiva/info_widgets/
git commit -m "add ChartOverlay and InfoWidget base classes with registries"
```

---

## Chunk 2: Scene Overlay + Widget Management (Real Implementation)

### Task 3: Implement real overlay and widget management in ChartScene

**Files:**
- Modify: `gandiva/scene/chart_scene.py`

Replace the stub implementations of `add_overlay` and `add_info_widget` with real ones.

- [ ] **Step 1: Add imports**

At the top of `chart_scene.py`, add:

```python
from gandiva.overlays import OVERLAYS
from gandiva.info_widgets import INFO_WIDGETS
from gandiva.info_widgets.base import InfoWidget
```

- [ ] **Step 2: Implement `add_overlay`**

Replace the `add_overlay` stub:

```python
    def add_overlay(self, overlay_id: str) -> None:
        """Add an overlay by its registry ID."""
        if overlay_id in self._overlays:
            return  # already active
        overlay_class = OVERLAYS.get(overlay_id)
        if overlay_class is None:
            return

        overlay = overlay_class()
        z = self.Z_OVERLAY_BASE + len(self._overlays)
        overlay.setZValue(z)
        self.addItem(overlay)
        self._overlays[overlay_id] = overlay

        # Initialize with current state
        if self._rect.isValid():
            overlay.resize(self._rect)
        if self._theme:
            overlay.set_theme(self._theme)
        if self._chart:
            overlay.update_from_chart(self._chart)

        self.overlay_added.emit(overlay_id)
```

- [ ] **Step 3: Implement `add_info_widget`**

Replace the `add_info_widget` stub:

```python
    def add_info_widget(self, widget_id: str) -> None:
        """Add an info widget by its registry ID."""
        if widget_id in self._info_widgets:
            return  # already active
        entry = INFO_WIDGETS.get(widget_id)
        if entry is None:
            return

        widget_class, kwargs = entry
        widget = widget_class(widget_id=widget_id, title=widget_id, **kwargs)
        z = self.Z_WIDGET_BASE + len(self._info_widgets)
        widget.setZValue(z)
        widget.setAcceptHoverEvents(True)
        self.addItem(widget)
        self._info_widgets[widget_id] = widget

        # Connect close signal
        widget.closed.connect(self.remove_info_widget)

        # Initialize with current state
        if self._theme:
            widget.set_theme(self._theme)
        if self._chart:
            widget.update_from_chart(self._chart)

        # Auto-place
        self._place_info_widget(widget)

        self.widget_added.emit(widget_id)
```

- [ ] **Step 4: Add auto-placement method**

Add this method to ChartScene:

```python
    def _place_info_widget(self, widget: InfoWidget) -> None:
        """Place a new info widget in available space around the chart."""
        scene_rect = self._rect
        if not scene_rect.isValid():
            return

        # Widget size (use sizeHint from the embedded widget)
        w = widget.widget().width() if widget.widget() else 220
        h = widget.widget().sizeHint().height() if widget.widget() else 200

        margin = 10

        # Candidate positions: corners then edge midpoints
        candidates = [
            (margin, margin),                                                    # top-left
            (scene_rect.width() - w - margin, margin),                           # top-right
            (margin, scene_rect.height() - h - margin),                          # bottom-left
            (scene_rect.width() - w - margin, scene_rect.height() - h - margin), # bottom-right
            (scene_rect.width() / 2 - w / 2, margin),                           # top-center
            (scene_rect.width() / 2 - w / 2, scene_rect.height() - h - margin), # bottom-center
            (margin, scene_rect.height() / 2 - h / 2),                          # mid-left
            (scene_rect.width() - w - margin, scene_rect.height() / 2 - h / 2), # mid-right
        ]

        from PyQt6.QtCore import QRectF

        existing_rects = []
        for other in self._info_widgets.values():
            if other is not widget:
                existing_rects.append(other.sceneBoundingRect())

        for x, y in candidates:
            candidate_rect = QRectF(x, y, w, h)
            overlaps = any(candidate_rect.intersects(r) for r in existing_rects)
            if not overlaps:
                widget.setPos(x, y)
                return

        # Fallback: stack at bottom-right with offset
        offset = len(self._info_widgets) * 20
        widget.setPos(
            scene_rect.width() - w - margin - offset,
            scene_rect.height() - h - margin - offset,
        )
```

- [ ] **Step 5: Verify import**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.scene.chart_scene import ChartScene; s = ChartScene(); print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add gandiva/scene/chart_scene.py
git commit -m "implement real overlay and info widget management in ChartScene"
```

---

## Chunk 3: Left Panel

### Task 4: Create LeftPanel with overlay/widget toggle tabs

**Files:**
- Create: `gandiva/widgets/left_panel.py`
- Modify: `gandiva/main_window.py`

The left panel mirrors ChartInputPanel's collapsible tab behavior: a vertical tab bar on the left edge, same animation style. Two tabs: Overlays and Widgets. Each tab shows a list of checkboxes.

- [ ] **Step 1: Create LeftPanel**

Create `gandiva/widgets/left_panel.py`:

```python
"""Left panel with overlay and widget toggle checkboxes."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabBar, QStackedWidget, QCheckBox, QScrollArea,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal,
)

from gandiva.overlays import OVERLAYS
from gandiva.info_widgets import INFO_WIDGETS


PANEL_WIDTH = 180
ANIM_DURATION_MS = 220

# Tab indices
_TAB_OVERLAYS = 0
_TAB_WIDGETS = 1
_TAB_COLLAPSE = 2


class LeftPanel(QWidget):
    """Collapsible left panel for toggling overlays and info widgets."""

    overlay_toggled = pyqtSignal(str, bool)   # (overlay_id, checked)
    widget_toggled = pyqtSignal(str, bool)    # (widget_id, checked)

    # ── animatable width property ──────────────────────────────────────────

    def _get_panel_width(self):
        return self.width()

    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, 'splitter') and self.splitter:
            total = self.splitter.width()
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                # left_panel, chart_view, input_panel
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

        # Tab bar — placed by MainWindow outside the splitter
        self.tab_bar = QTabBar()
        self.tab_bar.setShape(QTabBar.Shape.RoundedWest)
        self.tab_bar.addTab("Overlays")     # 0
        self.tab_bar.addTab("Widgets")      # 1
        self.tab_bar.addTab("          ")   # 2 — collapse action
        self.tab_bar.setTabToolTip(0, "Overlays")
        self.tab_bar.setTabToolTip(1, "Info Widgets")
        self.tab_bar.tabBarClicked.connect(self._on_tab_clicked)

        # Content stack
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # ── Overlays page ──────────────────────────────────────────────────
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
            from PyQt6.QtWidgets import QLabel
            ol_layout.addWidget(QLabel("No overlays available yet"))

        ol_layout.addStretch()
        self.stack.addWidget(overlay_page)

        # ── Widgets page ───────────────────────────────────────────────────
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
            from PyQt6.QtWidgets import QLabel
            wl_layout.addWidget(QLabel("No widgets available yet"))

        wl_layout.addStretch()
        self.stack.addWidget(widget_page)

        # Initial state
        self.tab_bar.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    # ── two-way sync: scene → checkboxes ───────────────────────────────────

    def on_overlay_removed(self, overlay_id: str):
        """Called when scene removes an overlay (e.g., chart style switch)."""
        cb = self._overlay_checks.get(overlay_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def on_widget_removed(self, widget_id: str):
        """Called when scene removes a widget (e.g., user clicked X)."""
        cb = self._widget_checks.get(widget_id)
        if cb:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    def uncheck_all_overlays(self):
        """Uncheck all overlay checkboxes (called on chart style switch)."""
        for cb in self._overlay_checks.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

    # ── tab collapse / expand with animation ───────────────────────────────

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
```

- [ ] **Step 2: Wire LeftPanel into MainWindow**

Modify `gandiva/main_window.py`:

**Add import** (near the top):
```python
from gandiva.widgets.left_panel import LeftPanel
```

**Add left panel creation** in `__init__`, right after the chart scene/view creation (after line 52):

```python
        # ── left panel: overlay/widget toggles ─────────────────────────────
        self.left_panel = LeftPanel()
```

**Update splitter** to be 3-way — replace the existing splitter section (lines 55-60):

```python
        # ── splitter: left panel + chart view + input panel ────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.chart_view)
        self.splitter.addWidget(self.input_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.input_panel.splitter = self.splitter
        self.left_panel.splitter = self.splitter
```

**IMPORTANT: Update `ChartInputPanel._set_panel_width`** — the right panel's animation method assumes a 2-way splitter. Now that the splitter has 3 widgets, it must be updated. In `gandiva/widgets/chart_input.py`, find the `_set_panel_width` method (around line 105) and replace it:

```python
    # old (2-way splitter):
    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, 'splitter') and self.splitter:
            total = self.splitter.width()
            self.splitter.setSizes([total - w, w])

    # new (3-way splitter):
    def _set_panel_width(self, w: int):
        self.setFixedWidth(w)
        if hasattr(self, 'splitter') and self.splitter:
            total = self.splitter.width()
            sizes = self.splitter.sizes()
            if len(sizes) >= 3:
                self.splitter.setSizes([sizes[0], total - sizes[0] - w, w])
            else:
                self.splitter.setSizes([total - w, w])
```

**Update content_row layout** — add the left tab bar before the splitter. Replace the content_row section (lines 65-72):

```python
        splitter = self.splitter
        left_tab_bar    = self.left_panel.tab_bar
        sidebar_tab_bar = self.input_panel.tab_bar
        content_row = QWidget()
        cr_layout   = QHBoxLayout(content_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(0)
        cr_layout.addWidget(left_tab_bar)
        cr_layout.addWidget(splitter, stretch=1)
        cr_layout.addWidget(sidebar_tab_bar)
```

**Wire signals** — add after the existing signal connections (after line 37):

```python
        # ── left panel ↔ scene wiring ──────────────────────────────────────
        self.left_panel.overlay_toggled.connect(self._on_overlay_toggled)
        self.left_panel.widget_toggled.connect(self._on_widget_toggled)
        self.chart_scene.overlay_removed.connect(self.left_panel.on_overlay_removed)
        self.chart_scene.widget_removed.connect(self.left_panel.on_widget_removed)
```

**Add handler methods:**

```python
    def _on_overlay_toggled(self, overlay_id: str, checked: bool):
        if checked:
            self.chart_scene.add_overlay(overlay_id)
        else:
            self.chart_scene.remove_overlay(overlay_id)

    def _on_widget_toggled(self, widget_id: str, checked: bool):
        if checked:
            self.chart_scene.add_info_widget(widget_id)
        else:
            self.chart_scene.remove_info_widget(widget_id)
```

**Update `_on_chart_style_changed`** to also clear overlay checkboxes:

```python
    def _on_chart_style_changed(self, style_name: str):
        self.chart_scene.set_chart_style(style_name)
        self.left_panel.uncheck_all_overlays()
```

**Update initial splitter sizes** — replace the last lines of `__init__` (around line 95):

```python
        from gandiva.widgets.chart_input import EXPANDED_WIDTH
        from gandiva.widgets.left_panel import PANEL_WIDTH
        self.splitter.setSizes([PANEL_WIDTH, self.width() - EXPANDED_WIDTH - PANEL_WIDTH, EXPANDED_WIDTH])
```

- [ ] **Step 3: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel appears with "Overlays" and "Widgets" tabs
- Left tab bar is on the left edge, visible even when collapsed
- Clicking tabs opens/collapses the left panel with animation
- The collapse spacer tab works (panel collapses, tab bar stays)
- Overlays tab shows "No overlays available yet"
- Widgets tab shows "No widgets available yet"
- Chart and right panel still work normally

- [ ] **Step 4: Commit**

```bash
git add gandiva/widgets/left_panel.py gandiva/main_window.py
git commit -m "add LeftPanel with overlay/widget toggle tabs, wire into MainWindow"
```

---

## Chunk 4: First Info Widgets

### Task 5: Create PanchangaWidget

**Files:**
- Create: `gandiva/info_widgets/panchanga.py`
- Modify: `gandiva/info_widgets/__init__.py`

Displays panchanga data (tithi, nakshatra, yoga, karana, vara) in a compact label grid.

**libaditya API reference:**
```python
panchanga = chart.rashi().panchanga()
panchanga.tithi()           # int (absolute tithi number)
panchanga.tithi_type()      # str, e.g. "jāya"
panchanga.nakshatra()       # str, e.g. "dhaniṣṭhā"
panchanga.yoga()            # str, e.g. "22 sādhya"
panchanga.yoga_name()       # str, e.g. "sādhya"
panchanga.karana()          # str, e.g. "garija"
panchanga.vara()            # str, e.g. "somavāra"
panchanga.init_tithi()      # int (relative tithi, 1-15)
```

- [ ] **Step 1: Create PanchangaWidget**

Create `gandiva/info_widgets/panchanga.py`:

```python
"""Panchanga info widget — displays tithi, nakshatra, yoga, karana, vara."""

from PyQt6.QtWidgets import QWidget, QFormLayout, QLabel
from PyQt6.QtGui import QFont

from gandiva.info_widgets.base import InfoWidget


class PanchangaWidget(InfoWidget):
    """Compact panchanga display."""

    def __init__(self, widget_id: str = "Panchanga", title: str = "Panchanga", **kwargs):
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QFormLayout(content)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setVerticalSpacing(3)
        layout.setHorizontalSpacing(8)

        self._tithi_label = QLabel("—")
        self._nakshatra_label = QLabel("—")
        self._yoga_label = QLabel("—")
        self._karana_label = QLabel("—")
        self._vara_label = QLabel("—")

        layout.addRow("Tithi:", self._tithi_label)
        layout.addRow("Nakshatra:", self._nakshatra_label)
        layout.addRow("Yoga:", self._yoga_label)
        layout.addRow("Karana:", self._karana_label)
        layout.addRow("Vara:", self._vara_label)

        return content

    def update_from_chart(self, chart) -> None:
        try:
            p = chart.rashi().panchanga()
            self._tithi_label.setText(f"{p.init_tithi()} ({p.tithi_type()})")
            self._nakshatra_label.setText(str(p.nakshatra()))
            self._yoga_label.setText(str(p.yoga_name()))
            self._karana_label.setText(str(p.karana()))
            self._vara_label.setText(str(p.vara()))
        except Exception:
            self._tithi_label.setText("—")
            self._nakshatra_label.setText("—")
            self._yoga_label.setText("—")
            self._karana_label.setText("—")
            self._vara_label.setText("—")
```

- [ ] **Step 2: Register**

Modify `gandiva/info_widgets/__init__.py`:

```python
"""Info widget registry."""

INFO_WIDGETS: dict[str, tuple] = {}

from gandiva.info_widgets.panchanga import PanchangaWidget  # noqa: E402

INFO_WIDGETS["Panchanga"] = (PanchangaWidget, {})
```

- [ ] **Step 3: Verify**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.info_widgets import INFO_WIDGETS; print(list(INFO_WIDGETS.keys()))"
```
Expected: `['Panchanga']`

- [ ] **Step 4: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel Widgets tab shows "Panchanga" checkbox
- Checking it adds a draggable widget to the scene showing panchanga data
- Unchecking removes it
- Clicking X on hover removes it and unchecks the checkbox
- Widget is draggable
- Recalculating updates the data
- Theme changes apply to the widget

- [ ] **Step 5: Commit**

```bash
git add gandiva/info_widgets/
git commit -m "add PanchangaWidget info widget"
```

---

### Task 6: Create DashaWidget

**Files:**
- Create: `gandiva/info_widgets/dasha.py`
- Modify: `gandiva/info_widgets/__init__.py`

Displays current Vimshottari dasha periods (maha/antar/pratyantara) as a compact list.

**libaditya API reference:**
```python
from libaditya import current_vimshottari_dasha
from libaditya import constants as const

moon = dict(chart.rashi().planets().items())["Moon"]

# const.vimshottari_dashas is a list of (name, years) tuples:
# [('Ketu', 7), ('Venus', 20), ('Sun', 6), ('Moon', 10), ('Mars', 7),
#  ('Rahu', 18), ('Jupiter', 16), ('Saturn', 19), ('Mercury', 17)]

# current_vimshottari_dasha(planet, nowtimeJD, dlevels, yrlen)
# Returns [maha_idx, antar_idx, pratyantar_idx, end_jd]
# Indices map into const.vimshottari_dashas list
# nowtimeJD = the chart's time (shows dasha active at chart moment)
result = current_vimshottari_dasha(moon, nowtimeJD=chart.context.timeJD, dlevels=3)
# e.g. [4, 3, 1, 2461148.56...] → Mars/Moon/Venus
lords = [const.vimshottari_dashas[i][0] for i in result[:3]]
```

**IMPORTANT:** `vimshottari_dashas` is in `libaditya.constants`, NOT importable from `libaditya` directly. Always use `from libaditya import constants as const` and then `const.vimshottari_dashas`.

- [ ] **Step 1: Create DashaWidget**

Create `gandiva/info_widgets/dasha.py`:

```python
"""Dasha info widget — displays current Vimshottari dasha periods."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont

from gandiva.info_widgets.base import InfoWidget


class DashaWidget(InfoWidget):
    """Compact current dasha period display."""

    def __init__(self, widget_id: str = "Dasha Periods", title: str = "Dasha Periods", **kwargs):
        super().__init__(widget_id=widget_id, title=title)

    def build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(2)

        self._maha_label = QLabel("Maha: —")
        self._antar_label = QLabel("Antar: —")
        self._pratyantar_label = QLabel("Pratyantar: —")

        font = QFont()
        font.setPointSize(9)
        for label in (self._maha_label, self._antar_label, self._pratyantar_label):
            label.setFont(font)
            layout.addWidget(label)

        layout.addStretch()
        return content

    def update_from_chart(self, chart) -> None:
        try:
            from libaditya import current_vimshottari_dasha
            from libaditya import constants as const

            planets = dict(chart.rashi().planets().items())
            moon = planets.get("Moon")
            if moon is None:
                self._set_empty()
                return

            result = current_vimshottari_dasha(
                moon, nowtimeJD=chart.context.timeJD, dlevels=3
            )
            if len(result) < 4:
                self._set_empty()
                return

            lords = [const.vimshottari_dashas[i][0] for i in result[:3]]

            self._maha_label.setText(f"Maha: {lords[0]}")
            self._antar_label.setText(f"Antar: {lords[1]}")
            self._pratyantar_label.setText(f"Pratyantar: {lords[2]}")
        except Exception:
            self._set_empty()

    def _set_empty(self):
        self._maha_label.setText("Maha: —")
        self._antar_label.setText("Antar: —")
        self._pratyantar_label.setText("Pratyantar: —")
```

- [ ] **Step 2: Register**

In `gandiva/info_widgets/__init__.py`, add after the PanchangaWidget registration:

```python
from gandiva.info_widgets.dasha import DashaWidget  # noqa: E402

INFO_WIDGETS["Dasha Periods"] = (DashaWidget, {})
```

- [ ] **Step 3: Verify**

```bash
cd /home/josh/w/astro/soft/gandiva
python -c "from gandiva.info_widgets import INFO_WIDGETS; print(list(INFO_WIDGETS.keys()))"
```
Expected: `['Panchanga', 'Dasha Periods']`

- [ ] **Step 4: Smoke test**

Run: `python -m gandiva.app`

Verify:
- Left panel Widgets tab shows "Panchanga" and "Dasha Periods" checkboxes
- Checking "Dasha Periods" adds a widget showing current dasha lords (Maha/Antar/Pratyantar)
- Both widgets can be active simultaneously and auto-place without overlap
- Widgets survive chart style switch (unaffected by style change)
- Clicking X removes widget and unchecks checkbox
- Both widgets are independently draggable

- [ ] **Step 5: Commit**

```bash
git add gandiva/info_widgets/
git commit -m "add DashaWidget info widget"
```

---

## Phase 2 Complete — Test Checkpoint

After completing all tasks above:

1. Run the app: `python -m gandiva.app`
2. Verify the full workflow:
   - Calculate a chart
   - Open left panel → Widgets tab → check both Panchanga and Dasha Periods
   - Both appear as draggable widgets in the scene
   - Drag them around, close via X, reopen via checkbox
   - Switch theme — widgets update styling
   - Switch chart style dropdown (only Western Wheel available, but verify it doesn't crash and overlays would be cleared)
   - Recalculate — widget content updates
   - Multiple chart tabs — widgets persist across tab switches and update content
3. Verify left panel collapse/expand animation works smoothly
4. Verify right panel still works normally

**What's in place after Phase 2:**
- Chart style dropdown on Display tab
- Left panel with Overlays and Widgets tabs (collapsible, animated)
- ChartOverlay base class + empty registry
- InfoWidget base class with chrome, dragging, hover close, click-to-raise
- Real overlay/widget management in ChartScene (add/remove, auto-placement)
- Two-way sync: left panel checkboxes ↔ scene state
- PanchangaWidget — tithi, nakshatra, yoga, karana, vara
- DashaWidget — current Vimshottari maha/antar/pratyantar dasha lords

**What's NOT done yet (Phase 3+):**
- MiniVargaWidget (reuses renderer at small scale)
- South Indian renderer
- Overlay implementations (aspect lines, rashi aspects)
- Chart style keybinding
