"""
HD Bodygraph — SVG-traced channel curves experiment

APPROACH: Instead of computing Bézier curves algorithmically, define each
channel as a hand-traced SVG path string. The workflow:

1. Run this script with --template to generate a blank SVG with centers and
   straight-line channels as a tracing guide
2. Open the template in Inkscape, draw curves over the straight lines
3. Copy each path's `d` attribute into CHANNEL_PATHS below
4. Run this script normally to render the bodygraph with curved channels

This gives you full artistic control over every curve. No more fighting
with control point math.
"""

import drawsvg as draw
import sys
import re

from libaditya.hd import constants as hdc

# ---------------------------------------------------------------------------
# Channel definitions: (gate_a, gate_b, center_a, center_b)
# ---------------------------------------------------------------------------
CHANNELS = [
    (64, 47, "head", "ajna"), (61, 24, "head", "ajna"), (63, 4, "head", "ajna"),
    (17, 62, "ajna", "throat"), (43, 23, "ajna", "throat"), (11, 56, "ajna", "throat"),
    (16, 48, "throat", "spleen"), (20, 57, "throat", "spleen"),
    (35, 36, "throat", "solar"), (12, 22, "throat", "solar"),
    (45, 21, "throat", "will"), (31, 7, "throat", "ji"), (8, 1, "throat", "ji"),
    (33, 13, "throat", "ji"),
    (25, 51, "ji", "will"), (15, 5, "ji", "sacral"), (2, 14, "ji", "sacral"),
    (46, 29, "ji", "sacral"),
    (37, 40, "solar", "will"), (44, 26, "spleen", "will"),
    (59, 6, "sacral", "solar"), (27, 50, "sacral", "spleen"),
    (42, 53, "sacral", "root"), (3, 60, "sacral", "root"), (9, 52, "sacral", "root"),
    (32, 54, "spleen", "root"), (28, 38, "spleen", "root"), (18, 58, "spleen", "root"),
    (49, 19, "solar", "root"), (55, 39, "solar", "root"), (30, 41, "solar", "root"),
    # integration channels (these share segments via gates 34, 10, 20, 57)
    (34, 57, "sacral", "spleen"), (34, 10, "sacral", "ji"),
    (34, 20, "sacral", "throat"), (57, 10, "spleen", "ji"),
    (10, 20, "ji", "throat"),
]

# ---------------------------------------------------------------------------
# CHANNEL_PATHS — hand-traced SVG path `d` strings
#
# Key: (gate_a, gate_b) — smaller gate first
# Value: SVG path d-attribute string
#
# To fill these in:
#   1. Run:  python svg_traced_bodygraph.py --template
#   2. Open experiments/bodygraph_template.svg in Inkscape
#   3. Draw a bezier path over each straight line guide
#   4. Select the path → XML editor → copy the `d` attribute
#   5. Paste it here as the value
#
# Paths go from gate_a's channel-start to gate_b's channel-start
# (i.e., full channel, not half-channels)
#
# Leave a channel as None to fall back to straight line
# ---------------------------------------------------------------------------
CHANNEL_PATHS = {
    # --- HEAD ↔ AJNA (spine — these are basically straight, slight curves ok) ---
    (4, 63):   None,  # straight spine
    (24, 61):  None,  # straight spine
    (47, 64):  None,  # straight spine

    # --- AJNA ↔ THROAT (spine) ---
    (17, 62):  None,
    (23, 43):  None,
    (11, 56):  None,

    # --- THROAT ↔ JI (spine) ---
    (7, 31):   None,
    (1, 8):    None,
    (13, 33):  None,

    # --- JI ↔ SACRAL (spine) ---
    (5, 15):   None,
    (2, 14):   None,
    (29, 46):  None,

    # --- SACRAL ↔ ROOT (spine) ---
    (42, 53):  None,
    (3, 60):   None,
    (9, 52):   None,

    # --- THROAT ↔ SPLEEN (left curves) ---
    # Example hand-traced path — replace with your Inkscape traces
    (16, 48):  "M 221,163 C 190,180 140,200 160,230",
    (20, 57):  "M 221,178 C 195,195 150,210 180,230",

    # --- THROAT ↔ SOLAR (right curves) ---
    (35, 36):  "M 268,140 C 300,160 340,200 350,240",
    (12, 22):  "M 268,150 C 310,200 360,280 330,245",

    # --- THROAT ↔ WILL ---
    (21, 45):  "M 275,190 C 285,200 290,215 295,228",

    # --- JI ↔ WILL ---
    (25, 51):  "M 285,257 C 290,260 295,268 297,270",

    # --- SPLEEN ↔ WILL ---
    (26, 44):  "M 140,350 C 170,340 200,330 220,323",

    # --- SOLAR ↔ WILL ---
    (37, 40):  "M 340,322 C 345,340 355,355 360,362",

    # --- SACRAL ↔ SOLAR ---
    (6, 59):   "M 268,372 C 280,371 295,371 307,371",

    # --- SACRAL ↔ SPLEEN ---
    (27, 50):  "M 222,370 C 210,370 200,370 195,370",

    # --- SPLEEN ↔ ROOT (left curves) ---
    (32, 54):  "M 127,365 C 140,375 160,395 180,410",
    (28, 38):  "M 117,378 C 130,395 150,415 172,425",
    (18, 58):  "M 108,390 C 120,405 140,425 163,438",

    # --- SOLAR ↔ ROOT (right curves) ---
    (19, 49):  "M 330,410 C 340,420 355,435 363,378",
    (39, 55):  "M 335,429 C 350,420 365,410 378,384",
    (30, 41):  "M 343,445 C 360,440 385,420 398,392",

    # --- INTEGRATION CHANNELS ---
    (34, 57):  "M 222,350 C 190,340 160,320 120,353",
    (10, 34):  "M 212,258 C 190,270 170,290 140,310",
    (20, 34):  "M 221,178 C 195,200 170,250 140,310",
    (10, 57):  "M 212,258 C 190,250 160,245 180,230",
    (10, 20):  "M 212,258 C 200,250 195,240 180,230",
}


def get_channel_key(ga, gb):
    """Normalize channel key so smaller gate is first."""
    return (min(ga, gb), max(ga, gb))


def draw_channel_curved(d, ga, gb, color, width=5):
    """Draw a single channel using SVG path if available, else straight line."""
    key = get_channel_key(ga, gb)
    path_d = CHANNEL_PATHS.get(key)

    if path_d:
        d.append(draw.Path(d=path_d, stroke=color, stroke_width=width,
                           fill="none", stroke_linecap="round"))
    else:
        # fallback: straight line from gate_a start to gate_b start
        # indices: 4=sx, 5=sy for gate start of channel
        ax, ay = hdc.gates[ga][4], hdc.gates[ga][5]
        bx, by = hdc.gates[gb][4], hdc.gates[gb][5]
        d.append(draw.Line(ax, ay, bx, by,
                           stroke=color, stroke_width=width,
                           stroke_linecap="round"))


def draw_centers(d, theme):
    """Draw the 9 centers (same as libaditya's draw_bodygraph)."""
    d.append(draw.Lines(210, 50, 250, 10, 290, 50, 210, 50,
                        stroke=theme["lines"], fill=theme.get("head", "#fff")))
    d.append(draw.Lines(210, 70, 250, 120, 290, 70, 210, 70,
                        stroke=theme["lines"], fill=theme.get("ajna", "#fff")))
    d.append(draw.Rectangle(220, 140, 60, 60, rx=5,
                            stroke=theme["lines"], fill=theme.get("throat", "#fff")))
    d.append(draw.Rectangle(220, 210, 60, 60, rx=5,
                            stroke=theme["lines"], fill=theme.get("ji", "#fff"),
                            transform="rotate(45,230,250)"))
    d.append(draw.Rectangle(220, 330, 60, 60, rx=5,
                            stroke=theme["lines"], fill=theme.get("sacral", "#fff")))
    d.append(draw.Rectangle(220, 420, 60, 60, rx=5,
                            stroke=theme["lines"], fill=theme.get("root", "#fff")))
    d.append(draw.Lines(100, 400, 100, 330, 170, 365, 100, 400,
                        stroke=theme["lines"], fill=theme.get("spleen", "#fff")))
    d.append(draw.Lines(400, 400, 400, 330, 330, 370, 400, 400,
                        stroke=theme["lines"], fill=theme.get("solar", "#fff")))
    d.append(draw.Lines(295, 300, 315, 255, 360, 290, 295, 300,
                        stroke=theme["lines"], fill=theme.get("will", "#fff")))


def generate_template():
    """
    Generate a tracing template SVG.

    Shows centers + straight-line channels with gate numbers labeled.
    Open in Inkscape and draw bezier curves on a layer above.
    """
    d = draw.Drawing(500, 500)
    d.append(draw.Rectangle(0, 0, 500, 500, fill="#1a1a2e"))

    theme = {"lines": "#666", "head": "#333", "ajna": "#333", "throat": "#333",
             "ji": "#333", "sacral": "#333", "root": "#333",
             "spleen": "#333", "solar": "#333", "will": "#333"}

    # Draw straight-line channels as thin guides
    for ga, gb, ca, cb in CHANNELS:
        ax, ay = hdc.gates[ga][4], hdc.gates[ga][5]
        bx, by = hdc.gates[gb][4], hdc.gates[gb][5]
        d.append(draw.Line(ax, ay, bx, by,
                           stroke="#444", stroke_width=3, stroke_linecap="round"))
        # Label gate numbers at endpoints
        d.append(draw.Text(str(ga), font_size=7, x=ax-4, y=ay-4, fill="#888"))
        d.append(draw.Text(str(gb), font_size=7, x=bx-4, y=by+8, fill="#888"))

    draw_centers(d, theme)

    outfile = "experiments/bodygraph_template.svg"
    d.save_svg(outfile)
    print(f"Template saved to {outfile}")
    print("Open in Inkscape, trace curves over the guides, then copy path `d` attributes")
    print("into CHANNEL_PATHS in this script.")


def generate_curved():
    """
    Generate bodygraph with curved channels (from CHANNEL_PATHS data).
    """
    d = draw.Drawing(500, 500)
    d.append(draw.Rectangle(0, 0, 500, 500, fill="#1a1a2e"))

    theme = {"lines": "#aaa",
             "head": "#fff3", "ajna": "#fff3", "throat": "#fff3",
             "ji": "#fff3", "sacral": "#fff3", "root": "#fff3",
             "spleen": "#fff3", "solar": "#fff3", "will": "#fff3"}

    # Draw all channels
    for ga, gb, ca, cb in CHANNELS:
        draw_channel_curved(d, ga, gb, color="#556", width=5)

    # Draw centers on top
    draw_centers(d, theme)

    # Draw gate numbers
    for i in range(1, 65):
        d.append(draw.Text(hdc.gates[i][0], font_size=10,
                           x=hdc.gates[i][2], y=hdc.gates[i][3], fill="#ccc"))

    outfile = "experiments/bodygraph_curved.svg"
    d.save_svg(outfile)
    print(f"Curved bodygraph saved to {outfile}")


if __name__ == "__main__":
    if "--template" in sys.argv:
        generate_template()
    else:
        generate_curved()
