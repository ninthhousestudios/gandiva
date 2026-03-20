"""Jaimini Indicators tab — displays Gets spec results for the current chart."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QPushButton, QComboBox, QLabel,
)
from PyQt6.QtGui import QFont

from libaditya.calc.jaimini_get import Gets
from libaditya import constants as const


_PLANET_SYMBOLS = {
    "Sun": "\u2609", "Moon": "\u263D", "Mars": "\u2642",
    "Mercury": "\u263F", "Jupiter": "\u2643", "Venus": "\u2640",
    "Saturn": "\u2644", "Rahu": "\u260A", "Ketu": "\u260B",
}


def _discover_specs():
    """Find all specs on Gets — any class attribute that is a dict with 'factor' and 'vargas' keys."""
    specs = []
    for name in dir(Gets):
        if name.startswith("_"):
            continue
        val = getattr(Gets, name)
        if isinstance(val, dict) and "factor" in val and "vargas" in val:
            display = name.replace("_", " ").title()
            specs.append((display, name))
    return specs

_SPECS = _discover_specs()


def _varga_display_name(code):
    """Get a display name for a varga code integer."""
    from libaditya.calc.varga import Varga
    from libaditya.objects.context import EphContext
    try:
        name = Varga(EphContext(), code).varga_name()
        return name.title() if name else f"D-{abs(code)}"
    except Exception:
        return f"D-{abs(code)}"


def _multi_vargas_for_spec(spec):
    """Return {varga_key: [code, ...]} for vargas in this spec that have multiple options."""
    from libaditya.calc.jaimini_get import JaiminiGet
    result = {}
    for v in spec["vargas"]:
        codes = list(const.multi_vargas.get(v, []))
        # Include default override code if it's not already in the list
        default_code = JaiminiGet.DEFAULT_VARGA_OVERRIDES.get(v)
        if default_code is not None and int(default_code) not in codes:
            codes.append(int(default_code))
        if codes:
            result[v] = codes
    return result


def _fmt_planet(info_str):
    """Format a jaimini_info() string: 'name,nature,lord,dignity' -> display string."""
    parts = info_str.split(",")
    if len(parts) < 4:
        return info_str
    name, nature, lord, dignity = parts[0], parts[1], parts[2], parts[3]
    sym = _PLANET_SYMBOLS.get(name, "")
    pieces = [f"{sym} {name}"]
    if nature:
        pieces.append(nature)
    if dignity and dignity != "None":
        pieces.append(dignity)
    return "  ".join(pieces)


def _varga_label(varga_key):
    """Display name for a varga key string (as used in Gets specs)."""
    code = int(varga_key)
    return _varga_display_name(code)


class JaiminiIndicatorsPanel(QWidget):
    """Right-side dock panel showing Jaimini Gets indicator results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None
        self._aspect_mode = None  # None = use chart's mode

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)

        self._sections = {}  # attr_name -> {tree, combos, content}
        for display_name, attr_name in _SPECS:
            self._add_section(display_name, attr_name)

        self._layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _add_section(self, title, attr_name, expanded=False):
        """Create a collapsible section, with varga variant combos if needed."""
        spec = getattr(Gets, attr_name)
        multi = _multi_vargas_for_spec(spec)

        btn = QPushButton(f"▼ {title}" if expanded else f"▶ {title}")
        btn.setFlat(True)
        btn.setStyleSheet("text-align: left; font-weight: bold; padding: 4px 2px;")

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(4, 4, 4, 4)
        content_lay.setSpacing(4)
        content.setVisible(expanded)

        # Varga variant combos (only for specs that have multi-varga options)
        combos = {}
        if multi:
            for varga_key, codes in multi.items():
                row = QHBoxLayout()
                row.setSpacing(4)
                default_name = _varga_display_name(int(varga_key))
                row.addWidget(QLabel(f"D-{varga_key}:"))
                combo = QComboBox()
                combo.setFixedHeight(22)
                for code in codes:
                    combo.addItem(_varga_display_name(code), str(code))
                # Select the default override if one exists
                default_code = Gets.KARAKA_ORDER  # just need to check DEFAULT_VARGA_OVERRIDES
                from libaditya.calc.jaimini_get import JaiminiGet
                default_override = JaiminiGet.DEFAULT_VARGA_OVERRIDES.get(varga_key, varga_key)
                for i in range(combo.count()):
                    if combo.itemData(i) == default_override:
                        combo.setCurrentIndex(i)
                        break
                row.addWidget(combo)
                row.addStretch()
                content_lay.addLayout(row)
                combos[varga_key] = combo

            calc_btn = QPushButton("Calculate")
            calc_btn.clicked.connect(lambda _, a=attr_name: self._on_recalculate(a))
            content_lay.addWidget(calc_btn)

        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(True)
        content_lay.addWidget(tree)

        def toggle():
            vis = not content.isVisible()
            content.setVisible(vis)
            btn.setText(f"▼ {title}" if vis else f"▶ {title}")

        btn.clicked.connect(toggle)
        self._layout.addWidget(btn)
        self._layout.addWidget(content)

        self._sections[attr_name] = {"tree": tree, "combos": combos}

    def _get_varga_overrides(self, attr_name):
        """Build varga_overrides dict from the combo selections for a spec."""
        section = self._sections[attr_name]
        combos = section["combos"]
        if not combos:
            return None
        overrides = {}
        for varga_key, combo in combos.items():
            overrides[varga_key] = combo.currentData()
        return overrides

    def _on_recalculate(self, attr_name):
        """Re-run a single spec with the selected varga overrides."""
        if self._chart is None:
            return
        try:
            rashi = self._chart.rashi()
            spec = getattr(Gets, attr_name)
            overrides = self._get_varga_overrides(attr_name)
            self._populate_spec(self._sections[attr_name]["tree"], rashi, spec, overrides)
        except Exception:
            pass

    def set_aspect_mode(self, mode: str):
        """Update all specs when rashi aspect mode changes."""
        self._aspect_mode = mode
        self._refresh_all()

    def update_from_chart(self, chart):
        self._chart = chart
        if chart is None:
            return
        self._refresh_all()

    def _refresh_all(self):
        if self._chart is None:
            return
        try:
            rashi = self._chart.rashi()
            for _, attr_name in _SPECS:
                spec = getattr(Gets, attr_name)
                overrides = self._get_varga_overrides(attr_name)
                self._populate_spec(self._sections[attr_name]["tree"], rashi, spec, overrides)
        except Exception:
            pass

    def _populate_spec(self, tree, rashi, spec, varga_overrides=None):
        tree.clear()
        try:
            result = rashi.jaimini_get(spec, varga_overrides=varga_overrides)
        except Exception as e:
            QTreeWidgetItem(tree, [f"(error: {e})"])
            return

        aspect_type = result.get("aspect_type", "")

        for factor_str in spec["factor"]:
            factor_data = result.get(factor_str, {})
            factor_node = QTreeWidgetItem(tree, [f"{factor_str}  ({aspect_type})"])
            f = factor_node.font(0)
            f.setBold(True)
            factor_node.setFont(0, f)

            for varga_key, influences in factor_data.items():
                varga_name = _varga_display_name(int(varga_key))
                varga_node = QTreeWidgetItem(factor_node, [varga_name])

                # Conjunction
                conj = influences.get("conjunction", [])
                if conj:
                    conj_node = QTreeWidgetItem(varga_node, ["Conjunction"])
                    for info_str in conj:
                        QTreeWidgetItem(conj_node, [_fmt_planet(info_str)])
                else:
                    QTreeWidgetItem(varga_node, ["Conjunction: (none)"])

                # Aspecting
                asp_lists = influences.get("aspecting", [])
                all_asp = [p for sign_planets in asp_lists for p in sign_planets]
                if all_asp:
                    asp_node = QTreeWidgetItem(varga_node, ["Aspecting"])
                    for info_str in all_asp:
                        QTreeWidgetItem(asp_node, [_fmt_planet(info_str)])
                else:
                    QTreeWidgetItem(varga_node, ["Aspecting: (none)"])

        tree.expandAll()

    def adjust_font(self, delta: int):
        pass
