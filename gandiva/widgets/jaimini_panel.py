"""Jaimini tab panel — displays Jaimini astrology data for the current chart."""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
    QTreeWidgetItem, QSizePolicy, QPushButton, QComboBox,
)
from PyQt6.QtGui import QFont, QPainter, QPen, QColor

from gandiva.glyphs import PLANET_GLYPHS
from gandiva.themes import get_theme, DEFAULT_THEME

_KARAKA_ABBREVS = ["AK", "AmK", "BK", "MK", "PuK", "GK", "DK"]

_PLANET_SYMBOLS = {
    "Sun": "\u2609", "Moon": "\u263D", "Mars": "\u2642",
    "Mercury": "\u263F", "Jupiter": "\u2643", "Venus": "\u2640",
    "Saturn": "\u2644",
}

# South Indian grid: (row, col, sign_number)
_CELL_SIGNS = [
    (0, 0, 12), (0, 1,  1), (0, 2,  2), (0, 3,  3),
    (1, 3,  4),                           (1, 0, 11),
    (2, 3,  5),                           (2, 0, 10),
    (3, 3,  6), (3, 2,  7), (3, 1,  8), (3, 0,  9),
]

_SIGN_TO_CELL = {sign: (r, c) for r, c, sign in _CELL_SIGNS}


def _pada_abbrev(sign_name: str) -> str:
    """First 3 chars of sign name, capitalised."""
    if not sign_name:
        return ""
    return sign_name.strip()[:3].capitalize()


class _PadaGridWidget(QWidget):
    """Custom-painted South Indian grid showing arudha padas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pada_data = {}   # sign_num -> pada sign name
        self._sign_names = {}  # sign_num -> sign name
        self._lagna_sign = 0
        self._upapada_sign = 0
        self._theme = None
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, sign_names, pada_data, lagna_sign, upapada_sign):
        self._sign_names = sign_names
        self._pada_data = pada_data
        self._lagna_sign = lagna_sign
        self._upapada_sign = upapada_sign
        self.update()

    def set_theme(self, theme):
        self._theme = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._theme or {}
        color_line = QColor(t.get("line", "#888888"))
        color_sign = QColor(t.get("sign_label", "#cc3333"))
        color_text = QColor(t.get("glyph", "#dddddd"))
        color_cusp = QColor(t.get("cusp_label", "#6688ff"))
        color_bg = QColor(t.get("bg", "#111111"))

        w = self.width()
        h = self.height()
        side = min(w, h)
        x0 = (w - side) / 2
        y0 = 0
        cw = side / 4
        ch = side / 4

        # Background
        p.fillRect(QRectF(x0, y0, side, side), color_bg)

        # Draw grid lines
        pen = QPen(color_line, 1.5)
        p.setPen(pen)
        # Outer border
        p.drawRect(QRectF(x0, y0, side, side))
        # Inner grid lines
        for i in range(1, 4):
            p.drawLine(QRectF(x0 + i * cw, y0, 0, side).topLeft().toPoint(),
                       QRectF(x0 + i * cw, y0 + side, 0, 0).topLeft().toPoint())
            p.drawLine(QRectF(x0, y0 + i * ch, 0, 0).topLeft().toPoint(),
                       QRectF(x0 + side, y0 + i * ch, 0, 0).topLeft().toPoint())
        # Center box border (2x2 inner area)
        p.drawRect(QRectF(x0 + cw, y0 + ch, cw * 2, ch * 2))

        sign_font = QFont("Sans", max(7, int(cw * 0.12)))
        pada_font = QFont("Sans", max(9, int(cw * 0.18)))
        pada_font.setBold(True)
        lagna_font = QFont("Sans", max(8, int(cw * 0.14)))

        for row, col, sign_num in _CELL_SIGNS:
            rect = QRectF(x0 + col * cw, y0 + row * ch, cw, ch)

            # Pada abbreviation — centered, bold, glyph color
            pada_name = self._pada_data.get(sign_num, "")
            abbrev = _pada_abbrev(pada_name)
            p.setFont(pada_font)
            p.setPen(color_text)
            p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), abbrev)

            # Upapada marker
            if sign_num == self._upapada_sign:
                p.setFont(pada_font)
                p.setPen(color_cusp)
                up_rect = QRectF(rect.x(), rect.y() + rect.height() * 0.55,
                                 rect.width(), rect.height() * 0.4)
                p.drawText(up_rect, int(Qt.AlignmentFlag.AlignCenter), "UP")

        # Lagna marker in center
        if self._lagna_sign:
            p.setFont(lagna_font)
            p.setPen(color_text)
            center_rect = QRectF(x0 + cw, y0 + ch, cw * 2, ch * 2)
            p.drawText(center_rect, int(Qt.AlignmentFlag.AlignCenter),
                       str(self._lagna_sign))

        p.end()


class JaiminiPanel(QWidget):
    """Right-side dock panel showing Jaimini calculations for the current chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)

        self._build_karakas_section()
        self._build_padas_section()
        self._build_rashi_argala_section()
        self._build_general_argala_section()
        self._build_strength_section()
        self._build_bandhana_section()

        self._layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Section helpers ─────────────────────────────────────────────────

    def _add_section(self, title, expanded=True):
        """Create a collapsible section: clickable header + content widget."""
        btn = QPushButton(f"▼ {title}" if expanded else f"▶ {title}")
        btn.setFlat(True)
        btn.setStyleSheet("text-align: left; font-weight: bold; padding: 4px 2px;")
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        content.setVisible(expanded)

        def toggle():
            vis = not content.isVisible()
            content.setVisible(vis)
            btn.setText(f"▼ {title}" if vis else f"▶ {title}")

        btn.clicked.connect(toggle)
        self._layout.addWidget(btn)
        self._layout.addWidget(content)
        return lay

    # ── Section builders ────────────────────────────────────────────────

    def _build_karakas_section(self):
        lay = self._add_section("Chara Karakas", expanded=True)

        self._karaka_table = QTableWidget(7, 4)
        self._karaka_table.setHorizontalHeaderLabels(["", "", "Longitude", "Sign"])
        self._karaka_table.verticalHeader().setVisible(False)
        self._karaka_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._karaka_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._karaka_table.setShowGrid(False)
        h = self._karaka_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._karaka_table.setMaximumHeight(220)
        lay.addWidget(self._karaka_table)

        self._karakamsha_label = QLabel("Karakamsha: —")
        self._svamsha_label = QLabel("Svamsha: —")
        lay.addWidget(self._karakamsha_label)
        lay.addWidget(self._svamsha_label)

    def _build_padas_section(self):
        lay = self._add_section("Padas", expanded=True)

        self._pada_grid = _PadaGridWidget()
        lay.addWidget(self._pada_grid)

        self._upapada_label = QLabel("Upapada: —")
        lay.addWidget(self._upapada_label)

    def _build_rashi_argala_section(self):
        lay = self._add_section("Rashi Argala", expanded=False)

        self._argala_tree = QTreeWidget()
        self._argala_tree.setHeaderHidden(True)
        self._argala_tree.setRootIsDecorated(True)
        self._argala_tree.setMaximumHeight(200)
        lay.addWidget(self._argala_tree)

    def _build_general_argala_section(self):
        lay = self._add_section("General Argala", expanded=False)

        # Varga selector
        varga_row = QHBoxLayout()
        varga_row.addWidget(QLabel("Varga:"))
        self._gen_argala_varga = QComboBox()
        self._gen_argala_varga.setFixedHeight(22)
        from gandiva.info_widgets.mini_varga import _VARGA_CODES
        for code in _VARGA_CODES:
            self._gen_argala_varga.addItem(f"D-{abs(code)}", code)
        varga_row.addWidget(self._gen_argala_varga)
        varga_row.addStretch()
        lay.addLayout(varga_row)

        # Sign selector
        sign_row = QHBoxLayout()
        sign_row.addWidget(QLabel("Sign:"))
        self._gen_argala_sign = QComboBox()
        self._gen_argala_sign.setFixedHeight(22)
        for i in range(1, 13):
            self._gen_argala_sign.addItem(str(i), i)
        sign_row.addWidget(self._gen_argala_sign)
        sign_row.addStretch()
        lay.addLayout(sign_row)

        # Calculate button
        calc_btn = QPushButton("Calculate")
        calc_btn.clicked.connect(self._on_general_argala_calc)
        lay.addWidget(calc_btn)

        # Results tree
        self._gen_argala_tree = QTreeWidget()
        self._gen_argala_tree.setHeaderHidden(True)
        self._gen_argala_tree.setRootIsDecorated(True)
        self._gen_argala_tree.setMaximumHeight(200)
        lay.addWidget(self._gen_argala_tree)

    def _build_strength_section(self):
        lay = self._add_section("Jaimini Strength", expanded=False)

        self._strength_table = QTableWidget(12, 4)
        self._strength_table.setHorizontalHeaderLabels(["", "Prathama", "Dvitiya", ""])
        self._strength_table.verticalHeader().setVisible(False)
        self._strength_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._strength_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._strength_table.setShowGrid(False)
        h = self._strength_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._strength_table.setMaximumHeight(400)
        lay.addWidget(self._strength_table)

    def _build_bandhana_section(self):
        lay = self._add_section("Bandhana Yogas", expanded=False)

        self._bandhana_tree = QTreeWidget()
        self._bandhana_tree.setHeaderHidden(True)
        self._bandhana_tree.setRootIsDecorated(True)
        self._bandhana_tree.setMaximumHeight(200)
        lay.addWidget(self._bandhana_tree)

    # ── Update from chart ───────────────────────────────────────────────

    def update_from_chart(self, chart):
        self._chart = chart
        if chart is None:
            return
        # Sync theme for painted widgets
        from PyQt6.QtCore import QSettings
        theme_name = QSettings("gandiva", "gandiva").value("theme", DEFAULT_THEME)
        self._pada_grid.set_theme(get_theme(theme_name))
        try:
            rashi = chart.rashi()
            jaimini = chart.jaimini()
            self._update_karakas(jaimini, rashi)
            self._update_padas(rashi)
            self._update_rashi_argala(rashi)
            self._update_general_argala_signs(rashi)
            self._update_strength(rashi)
            self._update_bandhana(rashi)
        except Exception:
            pass

    def _update_karakas(self, jaimini, rashi):
        try:
            karakas = jaimini.karakas()
            for i, planet in enumerate(karakas):
                abbrev = _KARAKA_ABBREVS[i] if i < len(_KARAKA_ABBREVS) else ""
                sym = _PLANET_SYMBOLS.get(planet.planet_name, "")

                item = QTableWidgetItem(abbrev)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                f = item.font()
                f.setBold(True)
                item.setFont(f)
                self._karaka_table.setItem(i, 0, item)

                item = QTableWidgetItem(f"{sym} {planet.planet_name}")
                self._karaka_table.setItem(i, 1, item)

                item = QTableWidgetItem(planet.in_sign_longitude())
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._karaka_table.setItem(i, 2, item)

                item = QTableWidgetItem(planet.sign_name())
                self._karaka_table.setItem(i, 3, item)

            self._karakamsha_label.setText(f"Karakamsha: {jaimini.karakamsha().sign_name()}")
            self._svamsha_label.setText(f"Svamsha: {jaimini.svamsha().sign_name()}")
        except Exception:
            self._karakamsha_label.setText("Karakamsha: —")
            self._svamsha_label.setText("Svamsha: —")

    def _update_padas(self, rashi):
        try:
            padas = rashi.padas()
            signs = rashi.signs()
            upapada = rashi.upapada()

            sign_names = {}
            pada_data = {}
            for sign_num in range(1, 13):
                sign = signs[sign_num]
                sign_names[sign_num] = sign.sign_name()
                pada = padas.get(sign)
                if pada:
                    pada_data[sign_num] = pada.sign_name()

            lagna_sign = signs.lagna().sign()
            upapada_sign = upapada.sign() if upapada else 0

            self._pada_grid.set_data(sign_names, pada_data, lagna_sign, upapada_sign)
            self._upapada_label.setText(f"Upapada: {upapada.sign_name()}")
        except Exception:
            pass

    def _update_rashi_argala(self, rashi):
        self._argala_tree.clear()
        try:
            signs = rashi.signs()
            lagna = signs.lagna()
            seventh = signs[lagna.astrological_signs_forward(7)]

            a1, m1, o1 = rashi.argala(lagna)
            a7, m7, o7 = rashi.argala(seventh)

            def bold_node(label):
                node = QTreeWidgetItem(self._argala_tree, [label])
                f = node.font(0)
                f.setBold(True)
                node.setFont(0, f)
                return node

            def add_planets(node, planets):
                if planets:
                    for p in planets:
                        sym = _PLANET_SYMBOLS.get(p.planet_name, "")
                        QTreeWidgetItem(node, [f"{sym} {p.planet_name}"])
                else:
                    QTreeWidgetItem(node, ["(none)"])

            add_planets(bold_node("Argala from 1st"), a1)
            add_planets(bold_node("Argala from 7th"), a7)
            add_planets(bold_node("Malefic Argala"), m1 + m7)
            add_planets(bold_node("Obstructions to Argala"), o1 + o7)

            self._argala_tree.expandAll()
        except Exception:
            pass

    def _update_general_argala_signs(self, rashi):
        """Update sign combo with current sign names."""
        signs = rashi.signs()
        self._gen_argala_sign.blockSignals(True)
        current = self._gen_argala_sign.currentData()
        self._gen_argala_sign.clear()
        for i in range(1, 13):
            self._gen_argala_sign.addItem(f"{i}. {signs[i].sign_name()}", i)
        # Restore selection
        if current:
            for j in range(self._gen_argala_sign.count()):
                if self._gen_argala_sign.itemData(j) == current:
                    self._gen_argala_sign.setCurrentIndex(j)
                    break
        self._gen_argala_sign.blockSignals(False)
        # Update varga names if possible
        try:
            from gandiva.widgets.chart_panel import varga_display_name
            for i in range(self._gen_argala_varga.count()):
                code = self._gen_argala_varga.itemData(i)
                try:
                    name = varga_display_name(self._chart.context, code)
                    self._gen_argala_varga.setItemText(i, f"{name} (D-{abs(code)})")
                except Exception:
                    pass
        except Exception:
            pass

    def _on_general_argala_calc(self):
        """Calculate argala for user-selected varga and sign."""
        if self._chart is None:
            return
        self._gen_argala_tree.clear()
        try:
            varga_code = self._gen_argala_varga.currentData()
            sign_num = self._gen_argala_sign.currentData()
            if varga_code is None or sign_num is None:
                return

            if varga_code == 1:
                varga = self._chart.rashi()
            else:
                varga = self._chart.varga(varga_code)

            sign = varga.signs()[sign_num]
            argala, malefic, obstructed = varga.argala(sign)

            def bold_node(label):
                node = QTreeWidgetItem(self._gen_argala_tree, [label])
                f = node.font(0)
                f.setBold(True)
                node.setFont(0, f)
                return node

            def add_planets(node, planets):
                if planets:
                    for p in planets:
                        sym = _PLANET_SYMBOLS.get(p.planet_name, "")
                        QTreeWidgetItem(node, [f"{sym} {p.planet_name}"])
                else:
                    QTreeWidgetItem(node, ["(none)"])

            add_planets(bold_node("Argala"), argala)
            add_planets(bold_node("Malefic Argala"), malefic)
            add_planets(bold_node("Obstructions to Argala"), obstructed)

            self._gen_argala_tree.expandAll()
        except Exception:
            pass

    def _update_strength(self, rashi):
        try:
            ranked = rashi.jaimini_first_strength()
            second = rashi.jaimini_second_strength()
            signs = rashi.signs()

            glyph_font = QFont("Sans", 14)

            for i in range(12):
                # Column 0: row number
                item = QTableWidgetItem(str(i + 1))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._strength_table.setItem(i, 0, item)

                # Column 1: Prathama — first strength sign glyph
                if i < len(ranked):
                    item = QTableWidgetItem(ranked[i].glyph())
                    item.setFont(glyph_font)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self._strength_table.setItem(i, 1, item)

                # Column 2: Dvitiya — sign glyph (signs 1-12 in order)
                sign = signs[i + 1]
                item = QTableWidgetItem(sign.glyph())
                item.setFont(glyph_font)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._strength_table.setItem(i, 2, item)

                # Column 3: supporter abbreviations
                supporters = second.get(sign, [])
                lord = sign.lord()
                abbrevs = []
                seen = set()
                for p in supporters:
                    if p.planet_name == lord and "Ld" not in seen:
                        abbrevs.append("Ld")
                        seen.add("Ld")
                    else:
                        short = p.planet_name[:2]
                        if short not in seen:
                            abbrevs.append(short)
                            seen.add(short)
                item = QTableWidgetItem(" ".join(abbrevs))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._strength_table.setItem(i, 3, item)
        except Exception:
            pass

    def _update_bandhana(self, rashi):
        self._bandhana_tree.clear()
        try:
            yogas = rashi.bandhana_yogas()
            if not yogas:
                QTreeWidgetItem(self._bandhana_tree, ["(none)"])
                return
            for pair in yogas:
                planets_a, planets_b = pair
                names_a = ", ".join(p.planet_name for p in planets_a)
                names_b = ", ".join(p.planet_name for p in planets_b)
                QTreeWidgetItem(self._bandhana_tree, [f"{names_a}  ↔  {names_b}"])
        except Exception:
            QTreeWidgetItem(self._bandhana_tree, ["(none)"])

    def adjust_font(self, delta: int):
        pass
