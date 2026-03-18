# Multi-View Charts, Vargas Dock, and Yogas Dock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add side-by-side chart views with varga sub-tabs, pop-out chart windows, a Vargas browsing dock, and a Yogas dock with category dropdown.

**Architecture:** `ChartArea`'s central widget becomes a sub-tab bar + `QSplitter` holding `ChartPanel` widgets (each wrapping a `ChartView` + `ChartScene`). Pop-outs are standalone `QWidget` windows containing a `ChartPanel`. `MainWindow` mediates all chart updates to panels and pop-outs. Two new data panels (Vargas, Yogas) register in `DATA_PANELS`.

**Tech Stack:** Python 3, PyQt6 (QSplitter, QTabBar, QGraphicsScene, QGraphicsView, QStackedWidget), libaditya

**Branch:** `multi-view` (create from current `master`)

**Spec:** `docs/superpowers/specs/2026-03-18-multi-view-vargas-yogas-design.md`

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| `gandiva/widgets/chart_panel.py` | Self-contained chart rendering unit: wraps ChartView + ChartScene, stores chart + varga_number, draws active highlight |
| `gandiva/widgets/vargas_dock.py` | Vargas dock widget for right panel: collapsible tree of vargas with mini renderings and action buttons |
| `gandiva/widgets/yogas_dock.py` | Yogas dock widget for right panel: QComboBox category selector + QStackedWidget pages |

### Modified Files
| File | Changes |
|------|---------|
| `gandiva/widgets/chart_area.py` | Replace single ChartView with sub-tab bar + QSplitter + ChartPanel(s). Add methods: `open_varga_tab()`, `open_side_by_side()`, `close_secondary_panel()`, `set_active_panel()`, `save_view_state()`, `restore_view_state()` |
| `gandiva/main_window.py` | Add pop-out button to chart tabs via `setTabButton()`. Add pop-out window management (create, update, destroy). Extend `_charts` entries with `varga_tabs`, `active_panel`, `side_by_side`, `splitter_state`, `popouts`. Wire Vargas dock signals. |
| `gandiva/widgets/data_panels.py` | Import and register VargasWidget and YogasWidget in `DATA_PANELS` dict |

---

## Chunk 1: ChartPanel Widget

### Task 1: Create the branch

**Files:** None (git only)

- [ ] **Step 1: Create and switch to new branch**

```bash
cd /home/josh/w/astro/soft/gandiva
git checkout -b multi-view
```

- [ ] **Step 2: Verify branch**

Run: `git branch --show-current`
Expected: `multi-view`

---

### Task 2: Create ChartPanel widget

**Files:**
- Create: `gandiva/widgets/chart_panel.py`

This is the core building block — a self-contained chart rendering unit. It wraps a `ChartView` + `ChartScene` pair and tracks which chart/varga it is displaying. It also has an optional header bar (for secondary panels in side-by-side mode) and an active-selection highlight.

- [ ] **Step 1: Create `chart_panel.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gandiva.scene.chart_scene import ChartScene
from gandiva.scene.chart_view import ChartView


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
        close_btn = QPushButton("\u2715")  # ✕
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.setStyleSheet("color: #e88; font-size: 12px;")
        close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_btn)
        self._header.setVisible(show_header)
        layout.addWidget(self._header)

        # Chart scene + view
        self.chart_scene = ChartScene()
        self.chart_view = ChartView(self.chart_scene)
        layout.addWidget(self.chart_view)

    @property
    def varga_number(self):
        return self._varga_number

    @property
    def chart(self):
        return self._chart

    @property
    def active(self):
        return self._active

    def set_active(self, active: bool):
        self._active = active
        border = "1px solid #5566aa" if active else "1px solid transparent"
        self.setStyleSheet(f"ChartPanel {{ border: {border}; }}")

    def set_chart(self, chart, varga_number=None):
        """Update the displayed chart. varga_number=None means rashi."""
        self._chart = chart
        self._varga_number = varga_number
        if chart is None:
            return
        if varga_number is not None:
            varga_chart = chart.varga(varga_number)
            self.chart_scene.set_chart(varga_chart)
        else:
            self.chart_scene.set_chart(chart.rashi())

        # Update header label
        if self._show_header and varga_number is not None:
            from libaditya.calc.varga import Varga
            name = Varga(chart.context, varga_number).varga_name()
            self._header_label.setText(name)
        elif self._show_header:
            self._header_label.setText("Rashi")

    def set_chart_style(self, style_name: str):
        self.chart_scene.set_chart_style(style_name)

    def set_theme(self, name: str):
        self.chart_scene.set_theme(name)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
```

- [ ] **Step 2: Verify it loads**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.widgets.chart_panel import ChartPanel; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add gandiva/widgets/chart_panel.py
git commit -m "feat: add ChartPanel widget — self-contained chart rendering unit"
```

---

## Chunk 2: ChartArea Rework

### Task 3: Rework ChartArea to use ChartPanel + QSplitter

**Files:**
- Modify: `gandiva/widgets/chart_area.py` (full rewrite of central widget setup)

The central widget changes from a bare `ChartView` to a `QWidget` containing a varga sub-tab bar (`QTabBar`) + a `QSplitter` holding `ChartPanel`(s). The dock system stays the same. All existing public methods (`set_chart`, `set_chart_style`, `set_theme`, `save_dock_state`, `restore_dock_state`, `dock_toggle_actions`, `adjust_font`) keep their signatures so `MainWindow` doesn't break.

- [ ] **Step 1: Rewrite `chart_area.py`**

Read the current file at `gandiva/widgets/chart_area.py` (83 lines). Replace the central widget setup in `__init__` and update `set_chart` and related methods. Keep dock creation unchanged.

The key changes:
1. Replace `self.chart_scene` / `self.chart_view` with `self._primary_panel` (a `ChartPanel`)
2. Add `self._secondary_panel` (initially None)
3. Add `self._varga_tab_bar` (QTabBar, hidden by default)
4. Add `self._splitter` (QSplitter containing the panels)
5. Track `self._active_panel_idx` (0 or 1)
6. Track `self._varga_tabs` list — always starts with `[None]` (rashi)

New `__init__` structure:

```python
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout, QSplitter, QTabBar,
)
from PyQt6.QtCore import Qt, pyqtSignal

from gandiva.widgets.chart_panel import ChartPanel
from gandiva.widgets.data_panels import DATA_PANELS


class ChartArea(QMainWindow):
    """Central chart area with splitter for side-by-side views."""

    varga_tab_changed = pyqtSignal()  # emitted when sub-tab state changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockNestingEnabled(True)
        self._chart = None

        # Central widget container
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Varga sub-tab bar (hidden until 2+ vargas)
        self._varga_tab_bar = QTabBar()
        self._varga_tab_bar.setTabsClosable(True)
        self._varga_tab_bar.setExpanding(False)
        self._varga_tab_bar.addTab("Rashi")
        # Hide close button on Rashi tab
        self._varga_tab_bar.setTabButton(
            0, QTabBar.ButtonPosition.RightSide, None
        )
        self._varga_tab_bar.setVisible(False)
        self._varga_tab_bar.currentChanged.connect(self._on_varga_tab_changed)
        self._varga_tab_bar.tabCloseRequested.connect(self._on_varga_tab_close)
        central_layout.addWidget(self._varga_tab_bar)

        # Varga tabs list: [None, 9, -3, ...] — None = rashi
        self._varga_tabs = [None]

        # Splitter with primary panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._primary_panel = ChartPanel(show_header=False)
        self._primary_panel.clicked.connect(lambda: self.set_active_panel(0))
        self._splitter.addWidget(self._primary_panel)
        central_layout.addWidget(self._splitter)

        self._secondary_panel = None
        self._active_panel_idx = 0

        self.setCentralWidget(central)

        # Data docks (unchanged from before)
        self._docks = {}
        self._data_panels = {}
        for name, cls in DATA_PANELS.items():
            widget = cls()
            dock = QDockWidget(name)
            dock.setWidget(widget)
            dock.setAllowedAreas(
                Qt.DockWidgetArea.RightDockWidgetArea
                | Qt.DockWidgetArea.BottomDockWidgetArea
            )
            dock.setVisible(False)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._docks[name] = (dock, widget)
            self._data_panels[name] = widget
```

- [ ] **Step 2: Add `set_chart` and forwarding methods**

These replace the old single-scene methods. `set_chart` updates all panels.

```python
    def set_chart(self, chart):
        """Update all chart panels and data panels with new chart."""
        self._chart = chart
        # Update primary panel — preserve its current varga
        self._primary_panel.set_chart(chart, self._primary_panel.varga_number)
        # Update secondary panel if it exists
        if self._secondary_panel is not None:
            self._secondary_panel.set_chart(
                chart, self._secondary_panel.varga_number
            )
        # Update data panels
        for widget in self._data_panels.values():
            widget.update_from_chart(chart)

    def set_chart_style(self, style_name: str):
        self._primary_panel.set_chart_style(style_name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_chart_style(style_name)

    def set_theme(self, name: str):
        self._primary_panel.set_theme(name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_theme(name)
```

- [ ] **Step 3: Add `active_panel` property and setter**

```python
    @property
    def active_panel(self) -> ChartPanel:
        if self._active_panel_idx == 1 and self._secondary_panel is not None:
            return self._secondary_panel
        return self._primary_panel

    def set_active_panel(self, idx: int):
        self._active_panel_idx = idx
        self._primary_panel.set_active(idx == 0)
        if self._secondary_panel is not None:
            self._secondary_panel.set_active(idx == 1)
        # Only show highlight when there are two panels
        if self._secondary_panel is None:
            self._primary_panel.set_active(False)
```

- [ ] **Step 4: Add varga sub-tab methods**

```python
    def _update_tab_bar_visibility(self):
        """Show tab bar when 2+ vargas or side-by-side active."""
        visible = (
            len(self._varga_tabs) > 1 or self._secondary_panel is not None
        )
        self._varga_tab_bar.setVisible(visible)

    def open_varga_tab(self, varga_number: int):
        """Add a varga sub-tab (or select existing) and switch active panel."""
        if varga_number in self._varga_tabs:
            idx = self._varga_tabs.index(varga_number)
            self._varga_tab_bar.setCurrentIndex(idx)
            return
        # Add new tab
        from libaditya.calc.varga import Varga
        if self._chart is not None:
            name = Varga(self._chart.context, varga_number).varga_name()
        else:
            name = f"D-{abs(varga_number)}"
        self._varga_tabs.append(varga_number)
        self._varga_tab_bar.addTab(name)
        new_idx = len(self._varga_tabs) - 1
        self._varga_tab_bar.setCurrentIndex(new_idx)
        self._update_tab_bar_visibility()

    def _on_varga_tab_changed(self, index):
        """Switch active panel's varga when sub-tab is clicked."""
        if index < 0 or index >= len(self._varga_tabs):
            return
        varga_number = self._varga_tabs[index]
        if self._chart is not None:
            self.active_panel.set_chart(self._chart, varga_number)

    def _on_varga_tab_close(self, index):
        """Close a varga sub-tab."""
        if index == 0:
            return  # Can't close Rashi
        varga_number = self._varga_tabs[index]
        self._varga_tabs.pop(index)
        self._varga_tab_bar.removeTab(index)
        # If active panel was showing this varga AND the varga no longer
        # exists in any remaining tab, revert to rashi
        if (
            self.active_panel.varga_number == varga_number
            and varga_number not in self._varga_tabs
        ):
            self.active_panel.set_chart(self._chart, None)
            self._varga_tab_bar.setCurrentIndex(0)
        self._update_tab_bar_visibility()
```

- [ ] **Step 5: Add side-by-side methods**

```python
    def open_side_by_side(self, varga_number: int):
        """Open or replace a secondary panel showing the given varga."""
        if self._secondary_panel is None:
            self._secondary_panel = ChartPanel(show_header=True)
            self._secondary_panel.clicked.connect(
                lambda: self.set_active_panel(1)
            )
            self._secondary_panel.close_requested.connect(
                self.close_secondary_panel
            )
            self._splitter.addWidget(self._secondary_panel)
            # Copy current chart style and theme from primary
            # (scene defaults should match)
        if self._chart is not None:
            self._secondary_panel.set_chart(self._chart, varga_number)
        # Ensure varga is in tab list
        if varga_number not in self._varga_tabs:
            from libaditya.calc.varga import Varga
            if self._chart is not None:
                name = Varga(self._chart.context, varga_number).varga_name()
            else:
                name = f"D-{abs(varga_number)}"
            self._varga_tabs.append(varga_number)
            self._varga_tab_bar.addTab(name)
        self._update_tab_bar_visibility()

    def close_secondary_panel(self):
        """Remove the secondary panel from the splitter."""
        if self._secondary_panel is None:
            return
        self._secondary_panel.setParent(None)
        self._secondary_panel.deleteLater()
        self._secondary_panel = None
        self._active_panel_idx = 0
        self._primary_panel.set_active(False)  # no highlight when single
        self._update_tab_bar_visibility()
```

- [ ] **Step 6: Add state save/restore methods**

```python
    def save_view_state(self) -> dict:
        """Save varga tabs, splitter, and panel state for chart tab switching."""
        state = {
            "varga_tabs": list(self._varga_tabs),
            "active_panel": self._active_panel_idx,
            "side_by_side": (
                self._secondary_panel.varga_number
                if self._secondary_panel is not None
                else None
            ),
            "splitter_state": (
                self._splitter.saveState()
                if self._secondary_panel is not None
                else None
            ),
            "primary_varga": self._primary_panel.varga_number,
        }
        return state

    def restore_view_state(self, state: dict):
        """Restore varga tabs, splitter, and panel state."""
        # Close secondary if open
        if self._secondary_panel is not None:
            self.close_secondary_panel()

        # Restore varga tabs
        self._varga_tab_bar.blockSignals(True)
        while self._varga_tab_bar.count() > 1:
            self._varga_tab_bar.removeTab(self._varga_tab_bar.count() - 1)
        self._varga_tabs = [None]  # reset to just Rashi

        for vn in state.get("varga_tabs", [None])[1:]:
            from libaditya.calc.varga import Varga
            if self._chart is not None:
                name = Varga(self._chart.context, vn).varga_name()
            else:
                name = f"D-{abs(vn)}"
            self._varga_tabs.append(vn)
            self._varga_tab_bar.addTab(name)

        # Restore primary panel varga (while signals still blocked)
        primary_varga = state.get("primary_varga")
        if self._chart is not None:
            self._primary_panel.set_chart(self._chart, primary_varga)

        # Select the right tab (while signals still blocked — no double render)
        if primary_varga in self._varga_tabs:
            idx = self._varga_tabs.index(primary_varga)
            self._varga_tab_bar.setCurrentIndex(idx)

        # Now unblock signals
        self._varga_tab_bar.blockSignals(False)

        # Restore side-by-side
        side_varga = state.get("side_by_side")
        if side_varga is not None:
            self.open_side_by_side(side_varga)
            splitter_state = state.get("splitter_state")
            if splitter_state is not None:
                self._splitter.restoreState(splitter_state)

        # Restore active panel last
        self.set_active_panel(state.get("active_panel", 0))
        self._update_tab_bar_visibility()
```

- [ ] **Step 7: Keep existing dock methods unchanged**

The following methods stay the same as before. Verify they still reference `self._docks` and `self._data_panels` correctly (they should, since dock creation is unchanged):

- `save_dock_state(self)` — returns `self.saveState()`
- `restore_dock_state(self, state)` — calls `self.restoreState(state)`
- `dock_toggle_actions(self)` — returns `{name: dock.toggleViewAction()}`
- `adjust_font(self, delta)` — calls `widget.adjust_font(delta)` on each data panel

- [ ] **Step 8: Add backward-compatible properties**

The existing `MainWindow` code references `self.chart_area.chart_scene` in many places: signal connections in `__init__` (overlay_removed, widget_removed), `_on_overlay_toggled`, `_on_spawn_widget`, `_on_widget_removed`, `_on_chart_tab_changed` (clear_all_widgets, get_widget_states, restore_widget_states), and `on_chart_created`. These properties delegate all those calls to the primary panel's scene, so no MainWindow changes are needed for overlays/widgets:

```python
    @property
    def chart_scene(self):
        """Backward compat — delegates to primary panel's scene."""
        return self._primary_panel.chart_scene

    @property
    def chart_view(self):
        """Backward compat — delegates to primary panel's view."""
        return self._primary_panel.chart_view
```

- [ ] **Step 9: Verify the app launches**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

The app should launch and display charts exactly as before (single panel, no sub-tabs visible). Calculate a chart and confirm it renders.

- [ ] **Step 10: Commit**

```bash
git add gandiva/widgets/chart_area.py
git commit -m "refactor: rework ChartArea to use ChartPanel + QSplitter + varga sub-tabs"
```

---

## Chunk 3: MainWindow — Pop-out Windows + Extended State

### Task 4: Add pop-out button to chart tabs

**Files:**
- Modify: `gandiva/main_window.py`

Add a ⬍ pop-out button to each chart tab using `QTabBar.setTabButton()`. When clicked, it creates a floating window with a `ChartPanel` showing the current varga of the active panel.

- [ ] **Step 1: Read `main_window.py`**

Read the full file to understand the current tab creation flow. The chart tab bar is created at line 29. Tabs are added in `on_chart_created()` around line 122. The `_refresh_tab_bar()` method at line 229 updates tab text.

- [ ] **Step 2: Add pop-out button helper**

Add a method to create and attach a pop-out button when a tab is added. Add this after the imports:

```python
from PyQt6.QtWidgets import QToolButton
from gandiva.widgets.chart_panel import ChartPanel
```

Add method to `MainWindow`:

```python
    def _add_tab_popout_button(self, tab_index: int):
        """Add a ⬍ pop-out button to a chart tab."""
        btn = QToolButton()
        btn.setText("\u2b0d")  # ⬍
        btn.setFixedSize(16, 16)
        btn.setAutoRaise(True)
        btn.setStyleSheet("font-size: 10px; color: #aaa;")
        # Capture the entry dict (stable reference), not the index
        # (which goes stale if tabs are reordered)
        entry = self._charts[tab_index]
        btn.clicked.connect(lambda: self._pop_out_chart_entry(entry))
        self.chart_tab_bar.setTabButton(
            tab_index, QTabBar.ButtonPosition.RightSide, btn
        )
```

- [ ] **Step 3: Call it when tabs are created**

In `on_chart_created()`, after `self.chart_tab_bar.addTab(...)`, call `self._add_tab_popout_button(new_index)`.

- [ ] **Step 4: Add pop-out window creation**

```python
    def _pop_out_chart_entry(self, entry: dict):
        """Create a floating window with a ChartPanel for the given chart entry."""
        chart = entry["chart"]
        if chart is None:
            return

        # Get current varga from active panel
        varga_number = self.chart_area.active_panel.varga_number

        panel = ChartPanel(show_header=False)
        panel.set_chart(chart, varga_number)

        window = QWidget()
        window.setWindowFlags(Qt.WindowType.Window)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panel)

        # Build title
        title = entry.get("key", "Chart")
        if varga_number is not None:
            from libaditya.calc.varga import Varga
            vname = Varga(chart.context, varga_number).varga_name()
            title = f"{title} \u2014 {vname}"
        window.setWindowTitle(title)
        window.resize(500, 500)
        window.show()

        # Track the pop-out
        entry.setdefault("popouts", []).append(
            {"window": window, "panel": panel, "varga": varga_number}
        )
        # Clean up on close
        window.destroyed.connect(
            lambda: self._remove_popout(entry, window)
        )

    def _remove_popout(self, entry, window):
        """Remove a pop-out from tracking when its window is destroyed."""
        entry["popouts"] = [
            p for p in entry.get("popouts", []) if p["window"] is not window
        ]

    def pop_out_varga(self, varga_number: int):
        """Pop out a specific varga for the current chart. Called from Vargas dock."""
        if self._current_idx < 0:
            return
        entry = self._charts[self._current_idx]
        chart = entry["chart"]
        if chart is None:
            return

        panel = ChartPanel(show_header=False)
        panel.set_chart(chart, varga_number)

        window = QWidget()
        window.setWindowFlags(Qt.WindowType.Window)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panel)

        from libaditya.calc.varga import Varga
        vname = Varga(chart.context, varga_number).varga_name()
        title = f"{entry.get('key', 'Chart')} \u2014 {vname}"
        window.setWindowTitle(title)
        window.resize(500, 500)
        window.show()

        entry.setdefault("popouts", []).append(
            {"window": window, "panel": panel, "varga": varga_number}
        )
        window.destroyed.connect(
            lambda: self._remove_popout(entry, window)
        )
```

- [ ] **Step 5: Commit**

```bash
git add gandiva/main_window.py
git commit -m "feat: add pop-out button to chart tabs and pop-out window management"
```

---

### Task 5: Update pop-outs on chart recalculation

**Files:**
- Modify: `gandiva/main_window.py`

- [ ] **Step 1: Add pop-out update to `on_chart_created()`**

In the existing `on_chart_created()` method, after the call to `self._display_chart(chart)`, add:

```python
        # Update all pop-outs for this chart
        entry = self._charts[self._current_idx]
        for popout in entry.get("popouts", []):
            popout["panel"].set_chart(chart, popout["varga"])
```

- [ ] **Step 2: Add pop-out cleanup to `_on_chart_tab_close()`**

In `_on_chart_tab_close()`, before removing the entry from `self._charts`, add:

```python
        # Close all pop-outs for this chart
        entry = self._charts[index]
        for popout in entry.get("popouts", []):
            popout["window"].close()
```

- [ ] **Step 3: Verify pop-outs update**

Run the app. Calculate a chart. Pop it out. Change a birth detail and recalculate. The pop-out window should update.

- [ ] **Step 4: Commit**

```bash
git add gandiva/main_window.py
git commit -m "feat: pop-out windows update on chart recalculation and close on tab removal"
```

---

### Task 6: Extend per-chart tab state with view state

**Files:**
- Modify: `gandiva/main_window.py`

- [ ] **Step 1: Initialize new fields in chart entry**

In `on_chart_created()`, where new chart entries are created (the dict with `chart`, `key`, `state`, `options`, `widgets`, `dock_state`), add:

```python
    "view_state": None,
    "popouts": [],
```

- [ ] **Step 2: Save view state on tab switch**

In `_on_chart_tab_changed()`, before switching to the new tab, save the current tab's view state:

```python
        # Save current view state
        if 0 <= self._current_idx < len(self._charts):
            self._charts[self._current_idx]["view_state"] = (
                self.chart_area.save_view_state()
            )
```

- [ ] **Step 3: Restore view state on tab switch**

In `_on_chart_tab_changed()`, after restoring the chart and dock state for the new tab, add:

```python
        # Restore view state (varga tabs, side-by-side, active panel)
        view_state = entry.get("view_state")
        if view_state is not None:
            self.chart_area.restore_view_state(view_state)
        else:
            # Default: single rashi view, reset any existing state
            self.chart_area.restore_view_state({
                "varga_tabs": [None],
                "active_panel": 0,
                "side_by_side": None,
                "splitter_state": None,
                "primary_varga": None,
            })
```

- [ ] **Step 4: Verify tab switching preserves varga state**

Run the app. Calculate two charts (different birth data). On chart A, open a varga side-by-side. Switch to chart B tab. Switch back to chart A — the side-by-side and varga tabs should be restored.

- [ ] **Step 5: Commit**

```bash
git add gandiva/main_window.py
git commit -m "feat: save/restore varga view state per chart tab"
```

---

## Chunk 4: Vargas Dock

### Task 7: Create VargasWidget

**Files:**
- Create: `gandiva/widgets/vargas_dock.py`

A collapsible tree widget (like `NakshatrasWidget`) listing all vargas. Each row expands to show a mini chart rendering + three action buttons.

- [ ] **Step 1: Read the NakshatrasWidget for reference**

Read `gandiva/widgets/data_panels.py` lines 509-605 to see the collapsible tree pattern.

- [ ] **Step 2: Create `vargas_dock.py` with the tree structure**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QSpinBox, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter

from libaditya.calc.varga import Varga


# All varga codes in display order
_VARGA_CODES = [
    1, -2, 2, -3, 3, -4, 4, 5, 7, 9,
    -10, -100, -12, -16, -20, -24, -240,
    -27, 30, -40, -45, -60,
]


class VargaActionWidget(QWidget):
    """Row of action buttons + optional mini chart for a varga."""

    pop_out = pyqtSignal(int)
    make_main = pyqtSignal(int)
    side_by_side = pyqtSignal(int)

    def __init__(self, varga_code: int, parent=None):
        super().__init__(parent)
        self._varga_code = varga_code
        self._chart = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Mini chart preview
        self._preview = QLabel()
        self._preview.setFixedSize(150, 150)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background: #1a1a2a; border: 1px solid #333;"
        )
        layout.addWidget(self._preview)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        pop_btn = QPushButton("\u2b0d")  # ⬍
        pop_btn.setToolTip("Pop out as floating window")
        pop_btn.setFixedSize(28, 24)
        pop_btn.clicked.connect(lambda: self.pop_out.emit(self._varga_code))
        btn_layout.addWidget(pop_btn)

        main_btn = QPushButton("\u25f1")  # ◱
        main_btn.setToolTip("Open as main chart view")
        main_btn.setFixedSize(28, 24)
        main_btn.clicked.connect(
            lambda: self.make_main.emit(self._varga_code)
        )
        btn_layout.addWidget(main_btn)

        sbs_btn = QPushButton("\u25eb")  # ◫
        sbs_btn.setToolTip("View side by side")
        sbs_btn.setFixedSize(28, 24)
        sbs_btn.clicked.connect(
            lambda: self.side_by_side.emit(self._varga_code)
        )
        btn_layout.addWidget(sbs_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def update_preview(self, chart):
        """Render a mini chart preview as a pixmap."""
        self._chart = chart
        if chart is None:
            self._preview.clear()
            return

        from gandiva.scene.chart_scene import ChartScene
        from PyQt6.QtCore import QRectF

        scene = ChartScene()
        if self._varga_code == 1:
            scene.set_chart(chart.rashi())
        else:
            scene.set_chart(chart.varga(self._varga_code))

        pixmap = QPixmap(150, 150)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, QRectF(0, 0, 150, 150))
        painter.end()
        self._preview.setPixmap(pixmap)


class VargasWidget(QWidget):
    """Vargas dock — collapsible tree of all divisional charts."""

    varga_pop_out = pyqtSignal(int)
    varga_make_main = pyqtSignal(int)
    varga_side_by_side = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._action_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setIndentation(14)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.itemClicked.connect(
            lambda item, _: item.setExpanded(not item.isExpanded())
            if item.childCount() > 0 else None
        )
        layout.addWidget(self._tree)

        self._build_tree()

        # Lazy-load previews on expand
        self._tree.itemExpanded.connect(self._on_item_expanded)

    def _build_tree(self):
        """Build the collapsible varga tree."""
        for code in _VARGA_CODES:
            name = Varga._static_varga_name(code) if hasattr(Varga, '_static_varga_name') else f"D-{abs(code)}"
            # We'll get proper names in update_from_chart
            item = QTreeWidgetItem([f"D-{abs(code)}"])
            self._tree.addTopLevelItem(item)
            item.setExpanded(False)

            # Action widget as child
            child = QTreeWidgetItem()
            item.addChild(child)
            action = VargaActionWidget(code)
            action.pop_out.connect(self.varga_pop_out.emit)
            action.make_main.connect(self.varga_make_main.emit)
            action.side_by_side.connect(self.varga_side_by_side.emit)
            self._tree.setItemWidget(child, 0, action)
            self._action_widgets[code] = (item, action)

        # Custom Parivritti entry
        custom_item = QTreeWidgetItem(["Custom Parivritti"])
        self._tree.addTopLevelItem(custom_item)

        child = QTreeWidgetItem()
        custom_item.addChild(child)
        custom_widget = QWidget()
        cl = QVBoxLayout(custom_widget)
        cl.setContentsMargins(4, 4, 4, 4)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Division:"))
        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(2, 360)
        self._custom_spin.setValue(11)
        input_row.addWidget(self._custom_spin)
        input_row.addStretch()
        cl.addLayout(input_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for symbol, tooltip, signal in [
            ("\u2b0d", "Pop out", self.varga_pop_out),
            ("\u25f1", "Open as main", self.varga_make_main),
            ("\u25eb", "Side by side", self.varga_side_by_side),
        ]:
            btn = QPushButton(symbol)
            btn.setToolTip(tooltip)
            btn.setFixedSize(28, 24)
            btn.clicked.connect(
                lambda checked, s=signal: s.emit(self._custom_spin.value())
            )
            btn_row.addWidget(btn)
        btn_row.addStretch()
        cl.addLayout(btn_row)

        self._tree.setItemWidget(child, 0, custom_widget)

    def update_from_chart(self, chart):
        """Update varga names and mini previews."""
        self._chart = chart
        if chart is None:
            return
        for code, (item, action) in self._action_widgets.items():
            try:
                name = Varga(chart.context, code).varga_name()
                item.setText(0, f"{name} (D-{abs(code)})")
            except Exception:
                item.setText(0, f"D-{abs(code)}")
            # Only update preview for expanded items
            if item.isExpanded():
                action.update_preview(chart)

    def _on_item_expanded(self, item):
        """Lazy-load mini preview when a varga row is expanded."""
        for code, (tree_item, action) in self._action_widgets.items():
            if tree_item is item and self._chart is not None:
                action.update_preview(self._chart)
                break

    def adjust_font(self, delta: int):
        pass  # No font adjustment needed for this widget
```

- [ ] **Step 3: Verify it imports**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.widgets.vargas_dock import VargasWidget; print('OK')"`
Expected: `OK`

Note: `Varga._static_varga_name` may not exist. The `_build_tree` method uses placeholder names (`D-{abs(code)}`), and `update_from_chart` fills in real names from libaditya. If `Varga` needs a chart context to get names, the initial tree just shows codes. This is fine — names populate on first chart calculation.

- [ ] **Step 4: Commit**

```bash
git add gandiva/widgets/vargas_dock.py
git commit -m "feat: add VargasWidget — collapsible tree dock for divisional charts"
```

---

## Chunk 5: Yogas Dock

### Task 8: Create YogasWidget

**Files:**
- Create: `gandiva/widgets/yogas_dock.py`

A data panel with a `QComboBox` for yoga categories and a `QStackedWidget` with one page per category.

- [ ] **Step 1: Read libaditya yoga API reference**

The yoga methods are on `chart.rashi()`:
- `nabhasa_yogas()` → `list[NabhasaYoga]` — fields: `name`, `translation`, `category`, `to_move`, `condition`
- `panchamahapurusha_yogas()` → `list[MahapurushaYoga]` — fields: `name`, `translation`, `planet`, `present`, `house`, `dignity`
- `solar_yogas()` → `list[SolarYoga]` — fields: `name`, `planets`, `present`
- `lunar_yogas()` → `list[LunarYoga]` — fields: `name`, `planets`, `present`
- `akriti_yogas()` → `list[AkritiYoga]` — fields: `name`, `translation`, `to_move`, `houses`

Print helpers in `libaditya/print_functions.py`: `rich_nabhasa_yogas`, `rich_mahapurusha_yogas`, `rich_solar_yogas`, `rich_lunar_yogas`, `rich_akriti_yogas`.

Read those print functions to understand formatting conventions before implementing.

- [ ] **Step 2: Create `yogas_dock.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt


# Category name → (method name on rashi, column headers, row builder)
_YOGA_CATEGORIES = [
    "Nabhasa Yogas",
    "Mahapurusha Yogas",
    "Solar Yogas",
    "Lunar Yogas",
    "Named Yogas",
]


class YogasWidget(QWidget):
    """Yogas dock — dropdown category selector + stacked display pages."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Category dropdown
        self._combo = QComboBox()
        self._combo.addItems(_YOGA_CATEGORIES)
        layout.addWidget(self._combo)

        # Stacked pages
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # One tree widget per category
        self._trees = {}
        for cat in _YOGA_CATEGORIES:
            tree = QTreeWidget()
            tree.setHeaderHidden(False)
            tree.setIndentation(0)
            tree.setRootIsDecorated(False)
            tree.setEditTriggers(
                QTreeWidget.EditTrigger.NoEditTriggers
            )
            self._trees[cat] = tree
            self._stack.addWidget(tree)

        self._combo.currentIndexChanged.connect(self._stack.setCurrentIndex)

        # Configure columns per category
        self._setup_columns()

    def _setup_columns(self):
        """Set up column headers for each category."""
        # Nabhasa
        t = self._trees["Nabhasa Yogas"]
        t.setColumnCount(4)
        t.setHeaderLabels(["Name", "Category", "Translation", "Moves"])
        t.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Mahapurusha
        t = self._trees["Mahapurusha Yogas"]
        t.setColumnCount(5)
        t.setHeaderLabels(["Name", "Planet", "Present", "House", "Dignity"])
        t.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Solar
        t = self._trees["Solar Yogas"]
        t.setColumnCount(3)
        t.setHeaderLabels(["Name", "Present", "Planets"])
        t.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Lunar
        t = self._trees["Lunar Yogas"]
        t.setColumnCount(3)
        t.setHeaderLabels(["Name", "Present", "Planets"])
        t.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        # Named (Akriti)
        t = self._trees["Named Yogas"]
        t.setColumnCount(4)
        t.setHeaderLabels(["Name", "Translation", "Houses", "Moves"])
        t.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

    def update_from_chart(self, chart):
        """Populate all yoga categories from chart data."""
        if chart is None:
            return
        rashi = chart.rashi()

        # Nabhasa
        tree = self._trees["Nabhasa Yogas"]
        tree.clear()
        for y in rashi.nabhasa_yogas():
            QTreeWidgetItem(tree, [
                y.name, y.category, y.translation, str(y.to_move),
            ])

        # Mahapurusha
        tree = self._trees["Mahapurusha Yogas"]
        tree.clear()
        for y in rashi.panchamahapurusha_yogas():
            QTreeWidgetItem(tree, [
                y.name, y.planet,
                "\u2713" if y.present else "\u2717",
                str(y.house), y.dignity,
            ])

        # Solar
        tree = self._trees["Solar Yogas"]
        tree.clear()
        for y in rashi.solar_yogas():
            planets_str = ", ".join(y.planets) if y.planets else "\u2014"
            QTreeWidgetItem(tree, [
                y.name,
                "\u2713" if y.present else "\u2717",
                planets_str,
            ])

        # Lunar
        tree = self._trees["Lunar Yogas"]
        tree.clear()
        for y in rashi.lunar_yogas():
            planets_str = ", ".join(y.planets) if y.planets else "\u2014"
            QTreeWidgetItem(tree, [
                y.name,
                "\u2713" if y.present else "\u2717",
                planets_str,
            ])

        # Named (Akriti)
        tree = self._trees["Named Yogas"]
        tree.clear()
        for y in rashi.akriti_yogas():
            houses_str = ", ".join(str(h) for h in y.houses)
            QTreeWidgetItem(tree, [
                y.name, y.translation, houses_str, str(y.to_move),
            ])

    def adjust_font(self, delta: int):
        pass  # Font adjustment can be added later
```

- [ ] **Step 3: Verify it imports**

Run: `cd /home/josh/w/astro/soft/gandiva && python -c "from gandiva.widgets.yogas_dock import YogasWidget; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add gandiva/widgets/yogas_dock.py
git commit -m "feat: add YogasWidget — category dropdown dock for yoga display"
```

---

## Chunk 6: Registration + Wiring

### Task 9: Register new panels in DATA_PANELS

**Files:**
- Modify: `gandiva/widgets/data_panels.py` (lines 1319-1328)

- [ ] **Step 1: Add imports and registry entries**

At the top of `data_panels.py`, after existing imports, add:

```python
from gandiva.widgets.vargas_dock import VargasWidget
from gandiva.widgets.yogas_dock import YogasWidget
```

In the `DATA_PANELS` dict (line 1319), add two entries:

```python
DATA_PANELS = {
    "Planets": PlanetsWidget,
    "Cusps": CuspsWidget,
    "Nakshatras": NakshatrasWidget,
    "Dashas": DashasWidget,
    "Kala": KalaWidget,
    "Panchanga": PanchangaWidget,
    "Vargas": VargasWidget,
    "Yogas": YogasWidget,
}
```

- [ ] **Step 2: Verify app launches with new tabs**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

The right tab bar should now show "Vargas" and "Yogas" tabs. Clicking them should show the dock widgets (initially empty until a chart is calculated).

- [ ] **Step 3: Commit**

```bash
git add gandiva/widgets/data_panels.py
git commit -m "feat: register Vargas and Yogas panels in DATA_PANELS"
```

---

### Task 10: Wire Vargas dock signals to ChartArea and MainWindow

**Files:**
- Modify: `gandiva/main_window.py`

The Vargas dock emits `varga_pop_out`, `varga_make_main`, and `varga_side_by_side` signals. These need to be connected to `MainWindow.pop_out_varga()`, `ChartArea.open_varga_tab()`, and `ChartArea.open_side_by_side()`.

- [ ] **Step 1: Connect Vargas dock signals**

In `MainWindow.__init__`, after the dock creation loop (or in the section where signals are connected), find the Vargas dock widget and connect its signals. The data panels are accessible via `self.chart_area._data_panels`:

```python
        # Wire Vargas dock signals
        vargas = self.chart_area._data_panels.get("Vargas")
        if vargas is not None:
            vargas.varga_pop_out.connect(self.pop_out_varga)
            vargas.varga_make_main.connect(self.chart_area.open_varga_tab)
            vargas.varga_side_by_side.connect(self.chart_area.open_side_by_side)
```

- [ ] **Step 2: Full integration test**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

Test the following flow:
1. Calculate a chart
2. Open the Vargas dock from the right tab bar
3. Expand "Navamsha (D-9)" — should show mini preview + 3 buttons
4. Click "◱ Make main" — should add a "Navamsha" sub-tab and the chart view switches to navamsha
5. Click "Rashi" sub-tab — should switch back to rashi
6. Click "◫ Side by side" on another varga — should split the view
7. Click the ✕ on the secondary panel — should return to single view
8. Click "⬍ Pop out" — should open a floating window
9. Switch chart tabs — view state should save/restore
10. Open Yogas dock — should show dropdown with 5 categories and data

- [ ] **Step 3: Commit**

```bash
git add gandiva/main_window.py
git commit -m "feat: wire Vargas dock signals to chart area and pop-out management"
```

---

## Chunk 7: Polish + Edge Cases

### Task 11: Handle edge cases and polish

**Files:**
- Modify: `gandiva/widgets/chart_area.py`
- Modify: `gandiva/main_window.py`

- [ ] **Step 1: Propagate chart style and theme to secondary panels and pop-outs**

In `ChartArea.open_side_by_side()`, after creating the secondary panel, copy the current chart style and theme from the primary panel's scene:

```python
            # Match primary panel's style/theme
            style = self._primary_panel.chart_scene._renderer
            if style is not None:
                style_name = None
                from gandiva.renderers import CHART_STYLES
                for name, cls in CHART_STYLES.items():
                    if isinstance(style, cls):
                        style_name = name
                        break
                if style_name:
                    self._secondary_panel.set_chart_style(style_name)
            theme = self._primary_panel.chart_scene._theme
            if theme:
                self._secondary_panel.set_theme(theme)
```

Similarly in `MainWindow._pop_out_chart()` and `pop_out_varga()`, after creating the panel, apply the current style and theme:

```python
        # Match current chart style and theme
        panel.set_chart_style(self.chart_area._primary_panel.chart_scene._renderer.__class__.__name__)  # or track style name
        # Better: store current style name in chart_area
```

Actually, a cleaner approach — add `_current_style` and `_current_theme` attributes to `ChartArea` and set them in `set_chart_style` / `set_theme`. Then new panels can just read these:

In `ChartArea.__init__`:
```python
        self._current_style = None
        self._current_theme = None
```

In `ChartArea.set_chart_style`:
```python
    def set_chart_style(self, style_name: str):
        self._current_style = style_name
        self._primary_panel.set_chart_style(style_name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_chart_style(style_name)
```

In `ChartArea.set_theme`:
```python
    def set_theme(self, name: str):
        self._current_theme = name
        self._primary_panel.set_theme(name)
        if self._secondary_panel is not None:
            self._secondary_panel.set_theme(name)
```

In `ChartArea.open_side_by_side`, after creating secondary panel:
```python
            if self._current_style:
                self._secondary_panel.set_chart_style(self._current_style)
            if self._current_theme:
                self._secondary_panel.set_theme(self._current_theme)
```

In `MainWindow._pop_out_chart` and `pop_out_varga`, after creating panel:
```python
        if self.chart_area._current_style:
            panel.set_chart_style(self.chart_area._current_style)
        if self.chart_area._current_theme:
            panel.set_theme(self.chart_area._current_theme)
```

- [ ] **Step 2: Handle theme changes updating all pop-outs**

In `MainWindow._apply_theme()`, after calling `self.chart_area.set_theme(name)`, iterate all pop-outs:

```python
        # Update pop-out themes
        for entry in self._charts:
            for popout in entry.get("popouts", []):
                popout["panel"].set_theme(name)
```

Similarly for chart style changes in `_on_chart_style_changed()`:

```python
        # Update pop-out chart styles
        entry = self._charts[self._current_idx]
        for popout in entry.get("popouts", []):
            popout["panel"].set_chart_style(style_name)
```

- [ ] **Step 3: Verify polish**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

Test:
- Change theme with pop-outs open — they should update
- Change chart style — secondary panel and pop-outs should match
- Open side-by-side — secondary panel should use current style/theme

- [ ] **Step 4: Commit**

```bash
git add gandiva/widgets/chart_area.py gandiva/main_window.py
git commit -m "fix: propagate chart style and theme to secondary panels and pop-outs"
```

---

### Task 12: Final verification

- [ ] **Step 1: Full test run**

Run: `cd /home/josh/w/astro/soft/gandiva && python -m gandiva.app`

Verify all features end-to-end:

1. **Single chart**: app launches, calculate a chart, renders normally
2. **Varga sub-tabs**: open Vargas dock → make main on D-9 → sub-tab bar appears with "Rashi" + "Navamsha" → clicking tabs switches the chart view → close sub-tab via × → bar hides
3. **Side by side**: click side-by-side on a varga → two panels appear with splitter → click each to select → sub-tabs switch the active panel → close secondary via ✕
4. **Pop-out**: ⬍ button on chart tab → floating window appears → recalculate → pop-out updates → close pop-out
5. **Varga pop-out**: from Vargas dock → ⬍ on a varga → floating window with that specific varga
6. **Tab switching**: calculate two charts → set up vargas/side-by-side on one → switch tabs → switch back → state restored
7. **Yogas dock**: open Yogas tab → dropdown shows 5 categories → switching categories shows different yoga data → data populates after chart calculation
8. **Theme/style propagation**: change theme → all panels and pop-outs update. Change chart style → same
9. **Custom Parivritti**: enter a number → click any of the 3 buttons → works correctly

- [ ] **Step 2: Commit any remaining fixes**

```bash
git add -u
git commit -m "fix: address issues found in final verification"
```
