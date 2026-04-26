"""
HD Bodygraph — Bent polygon strips experiment (Option 3)

Takes hdkit's straight polygon channel strips (MIT license) and warps them
along Bézier spines to create curved channels.

Algorithm:
1. Parse each hdkit polygon strip → 4 corners → spine (midline) + width
2. For channels that need curves, define a quadratic pull point
3. Convert to cubic Bézier spine
4. Sample the spine at N points, offset each ±half_width perpendicular to tangent
5. Output as filled polygon approximating the curved strip

hdkit source: https://github.com/jdempcy/hdkit (MIT license)
SVG data from: bodygraph-blank.svg (851.41 × 1309.4 viewbox)
"""

import drawsvg as draw
import math
import re
import sys

# ---------------------------------------------------------------------------
# hdkit SVG path data (MIT license, from bodygraph-blank.svg)
# ---------------------------------------------------------------------------
HDKIT_GATE_PATHS = {
    1:  "M429.37,572.57l.38,31.77-17.4.16L412,572.77",
    2:  "M411.75,838.49l-.52-67.76,17.4-.16.52,67.49",
    3:  "M412,1113.75l-.37-38.78,17.4-.16.38,39.33",
    4:  "M466.89,183.91l.37,30.02-17.4.16-.37-30.18",
    5:  "M391.93,837.64,393,929.22l-17.4.16-1.07-91.31",
    6:  "M592,990.7l109.78,-25.1.16,17.4L594,1007.68",
    7:  "M391.81,586.87l.83,60.56-17.4.16-.87-60.53",
    8:  "M411.94,572.77l-.35-29,17.4-.16.35,29",
    9:  "M449.5,1113.75l-.36-39.19,17.4-.16.37,39.72",
    10: "M342.37,683.81l.15,15.4L224,700.67l-.14,-15.39,118.48,-1.47",
    11: "M449.65,350.52l-.86-78.18,17.4-.16.86,78.35",
    12: "M627.89,707.14,478.12,463.22l15.13-8.59L642.37,697.5",
    13: "M466.78,586.87l.83,60.56-17.4.16-.84-60.53",
    14: "M429.15,838.06l.93,90.47-17.4.16-.93-90.2",
    15: "M374.53,838.07l-1.07-113.93,17.4-.17,1.07,113.67",
    16: "M176.37,686.82,345.85,430.73,361.18,439,191.8,694.87",
    17: "M374.7,350.15l-.88-83.36,17.4-.16.88,83.53",
    18: "M184,1159.72,36.93,1049.36l8.58-15.13,148.71,111.6",
    19: "M618.84,1109.91,494,1206.14,485.49,1191l123-94.88",
    20: "M207.63,700.23,347,485.46l15.32,8.23L228,700.69",
    21: "M552.66,630.14,608,751.29l-12.23,16-58.06,-130.5",
    22: "M642.37,697.5l137.53,224-15.13,8.59-136.88,-223",
    23: "M429.3,373.22l.48,27.3-17.39.16-.49-27.46",
    24: "M429.37,183.54l.38,30.8-17.39.16-.38-31",
    25: "M523.68,744l-35.94,-39.16L501.26,694l35.92,39.12",
    26: "M324.86,877.2,536,819.5l7.58,15.66L329.22,893.75",
    27: "M241.79,989.74l105.77,26.54.16,17.4L239.43,1006.5",
    28: "M202.37,1135.64,66.92,1032.37l8.53-15.16L212.72,1121.9",
    29: "M466.89,838.48l1.08,90-17.4.16L449.49,838",
    30: "M648.29,1146.45l152.08,-113.71,8.58,15.13L658.83,1160.14",
    31: "M374.41,587.09l-.41-43.04,17.4-.17.59,43",
    32: "M222,1110.4,97.24,1014.87l8.54-15.16,126.61,97",
    33: "M449.37,587.09l-.59-43,17.4-.17.59,43",
    34: "M139.46,819.72l213,148.33-6.21,14-213-148.32,6.21,-14.05",
    35: "M656.89,690.37,480.23,418.14l15-8.82L671.37,680.74",
    36: "M671.37,680.74l139.5,221.93-15,8.82-139,-221.12",
    37: "M703.37,882,750,945.61l-17,3.8-42.4,-57.87",
    38: "M212.72,1121.9l142,108.27-8.54,15.16L202.37,1135.64",
    39: "M639.63,1135.14,494.37,1246l-8.53-15.15L629,1121.64",
    40: "M690.61,891.54,647.73,833l17,-3.8L703.37,882",
    41: "M658.83,1160.14l-164,122.58-8.58-15.13,162,-121.12",
    42: "M374.52,1113.38l-.35-38,17.4-.16.35,38.16",
    43: "M411.9,373.22l-.24-32.28,17.4-.16.24,32.44",
    44: "M329.22,893.75l-223.06,61-7.58-15.66,226.28,-61.85",
    45: "M537.66,636.79,478.37,503.44l14.89-4.37,59.4,131.07",
    46: "M449.49,838.06l-1.06-110.7,17.4-.16,1.06,111.28",
    47: "M391.91,183.35l.38,31.39-17.4.17-.38-31.56",
    48: "M191.8,694.87,49.37,910.05,34,901.82l142.3,-215",
    49: "M608.5,1096.14l128.41,-99,8.53,15.16L618.84,1110",
    50: "M239.43,1006.5,147,983.31l-.16-17.4,94.91,23.83",
    51: "M537.18,733.07l42.22,46L565.87,790l-42.19,-46",
    52: "M466.91,1114.14l.35,38-17.4.16-.36,-38.49",
    53: "M391.92,1113.38l.37,39.52-17.4.16-.37-39.68",
    54: "M232.37,1096.67,355.56,1191l-8.51,15.13-125,-95.76",
    55: "M629,1121.64l140.21,-107,8.53,15.15L639.63,1135.14",
    56: "M467.05,350.14l.56,51.08-17.4.16-.56,-50.87",
    57: "M147.44,824.86,79.76,929.14l-15.32,-8.22L133.78,814Z",
    58: "M194.22,1145.83l160.44,120.41-8.58,15.13L184,1159.72",
    59: "M594,1007.68l-101.47,23.19-.16-17.39L592,990.7",
    60: "M429.37,1114.14l.36,38.37-17.4.16-.36,-38.9",
    61: "M412,183.54l-.35-30.15,17.4-.16.31,30.31",
    62: "M392.1,350.34l.54,51-17.4.16-.54,-51.36",
    63: "M449.49,183.73,449.14,153l17.4-.16.35,31.09",
    64: "M374.51,183.35l-.34-29.55,17.4-.16.34,29.71",
}

HDKIT_SPECIAL_PATHS = {
    'GateSpan':      "M227.96,700.74l-80.52,124.12-13.66,-10.79L214.3,689.95Z",
    'GateConnect34': "M138.86,839.14l-5.08,-25.09,13.66,10.79Z",
    'GateConnect10': "M228,700.74l-20.33,-.51,31.7,-15.68Z",
}

HDKIT_CENTER_PATHS = {
    'Head':         "M340.59,156.62a5.48,5.48,0,0,1-4.68,-8.32L414,17.86a5.49,5.49,0,0,1,7.54,-1.9,5.64,5.64,0,0,1,1.86,1.84l81.12,131.34a5.5,5.5,0,0,1-4.68,8.39Z",
    'Ajna':         "M420.37,355.14a5.44,5.44,0,0,1-4.73,-2.69L335.92,218.14a5.49,5.49,0,0,1,1.89,-7.53,5.57,5.57,0,0,1,2.84,-.78l159.5,.82a5.51,5.51,0,0,1,4.7,8.32L425.12,352.49A5.48,5.48,0,0,1,420.37,355.14Z",
    'Throat':       "M349.37,558.45a6,6,0,0,1-6,-6l.68,-148a6,6,0,0,1,6,-6L491.4,399a6,6,0,0,1,6,6l-.67,148a6,6,0,0,1-6,6Z",
    'G':            "M420,795.51a6.4,6.4,0,0,1-4.58,-1.9l-95.86,-96.68a6.48,6.48,0,0,1,0,-9.13l96.69,-95.92a6.46,6.46,0,0,1,9.12,0l95.9,96.72a6.48,6.48,0,0,1,0,9.12l-96.69,95.93A6.48,6.48,0,0,1,420,795.51Z",
    'Sacral':       "M348.86,1078.19a5.5,5.5,0,0,1-5.48,-5.52L344,930.26a5.5,5.5,0,0,1,5.5,-5.48l142.43,.56a5.5,5.5,0,0,1,5.48,5.52l-.57,142.41a5.54,5.54,0,0,1-5.5,5.48Z",
    'Root':         "M348.86,1295.7a5.43,5.43,0,0,1-3.88,-1.62,5.49,5.49,0,0,1-1.6,-3.9l.57,-135.56a5.5,5.5,0,0,1,5.5,-5.48l142.43,.57a5.5,5.5,0,0,1,5.48,5.52l-.57,135.56a5.54,5.54,0,0,1-5.5,5.48Z",
    'SolarPlexus':  "M831.56,1063.92a5.48,5.48,0,0,1-2.68,-.71L685,982.36a5.5,5.5,0,0,1-2.11,-7.49h0a5.48,5.48,0,0,1,2,-2l145.71,-86.2a5.18,5.18,0,0,1,2.79,-.78,5.51,5.51,0,0,1,5.51,5.51v.06l-1.78,167A5.53,5.53,0,0,1,831.56,1063.92Z",
    'Spleen':       "M15.53,1063.92a5.53,5.53,0,0,1-5.5,-5.45l-1.78,-167a5.31,5.31,0,0,1,1.57,-3.91,5.52,5.52,0,0,1,3.94,-1.66,5.39,5.39,0,0,1,2.79,.78l145.71,86.2a5.49,5.49,0,0,1,1.94,7.52h0a5.48,5.48,0,0,1-2,2l-144,80.85A5.61,5.61,0,0,1,15.53,1063.92Z",
    'Ego':          "M527.17,838.36a6.76,6.76,0,0,1-4.73,-11.54l78.29,-78.14a6.66,6.66,0,0,1,4.76,-2,6.75,6.75,0,0,1,5.5,2.83l56.48,79A6.76,6.76,0,0,1,662,839.19Z",
}

# Which channel each gate belongs to: gate → partner gate
CHANNEL_PAIRS = {
    64: 47, 47: 64,  61: 24, 24: 61,  63: 4, 4: 63,       # head-ajna
    17: 62, 62: 17,  43: 23, 23: 43,  11: 56, 56: 11,      # ajna-throat
    16: 48, 48: 16,  20: 57, 57: 20,                         # throat-spleen
    35: 36, 36: 35,  12: 22, 22: 12,                         # throat-solar
    45: 21, 21: 45,                                           # throat-will/ego
    31: 7, 7: 31,  8: 1, 1: 8,  33: 13, 13: 33,            # throat-ji/G
    25: 51, 51: 25,                                           # ji-will
    15: 5, 5: 15,  2: 14, 14: 2,  46: 29, 29: 46,          # ji-sacral
    37: 40, 40: 37,                                           # solar-will
    44: 26, 26: 44,                                           # spleen-will
    59: 6, 6: 59,                                             # sacral-solar
    27: 50, 50: 27,                                           # sacral-spleen
    42: 53, 53: 42,  3: 60, 60: 3,  9: 52, 52: 9,          # sacral-root
    32: 54, 54: 32,  28: 38, 38: 28,  18: 58, 58: 18,      # spleen-root
    49: 19, 19: 49,  55: 39, 39: 55,  30: 41, 41: 30,      # solar-root
    # integration channels
    34: 57,  10: 34,  # these have multiple partners, handled specially
}

# Full channel list: (gate_a, gate_b) — rendering order
CHANNELS = [
    (57, 20), (10, 20),  # integration pieces first (under)
    (57, 34), (10, 34),
    (34, 20),
    (44, 26), (12, 22), (35, 36), (21, 45), (51, 25),
    (40, 37), (59, 6), (27, 50),
    (48, 16), (58, 18), (38, 28), (54, 32),
    (41, 30), (39, 55), (49, 19),
    (64, 47), (61, 24), (63, 4),
    (17, 62), (43, 23), (11, 56),
    (31, 7), (1, 8), (33, 13),
    (15, 5), (2, 14), (46, 29),
    (42, 53), (3, 60), (9, 52),
]

# ---------------------------------------------------------------------------
# Curve parameters per center pair
# direction: which side to pull the curve toward
#   "left"  = pull toward lower x (viewer's left)
#   "right" = pull toward higher x (viewer's right)
#   "straight" = no curve
# strength: how far to pull (fraction of spine length)
# ---------------------------------------------------------------------------
CURVE_PARAMS = {
    # spine channels — straight
    ("head", "ajna"):     {"direction": "straight", "strength": 0},
    ("ajna", "throat"):   {"direction": "straight", "strength": 0},
    ("throat", "G"):      {"direction": "straight", "strength": 0},
    ("G", "sacral"):      {"direction": "straight", "strength": 0},
    ("sacral", "root"):   {"direction": "straight", "strength": 0},
    # left-side curves
    ("throat", "spleen"): {"direction": "left",  "strength": 0.25},
    ("spleen", "root"):   {"direction": "left",  "strength": 0.15},
    ("sacral", "spleen"): {"direction": "left",  "strength": 0.10},
    # right-side curves
    ("throat", "solar"):  {"direction": "right", "strength": 0.25},
    ("solar", "root"):    {"direction": "right", "strength": 0.15},
    ("sacral", "solar"):  {"direction": "right", "strength": 0.08},
    # small connectors
    ("throat", "ego"):    {"direction": "right", "strength": 0.12},
    ("G", "ego"):         {"direction": "right", "strength": 0.10},
    ("spleen", "ego"):    {"direction": "straight", "strength": 0},
    ("solar", "ego"):     {"direction": "straight", "strength": 0},
    # integration channels — gentle left curves
    ("sacral", "throat"): {"direction": "left",  "strength": 0.20},
    ("sacral", "G"):      {"direction": "left",  "strength": 0.15},
    ("spleen", "G"):      {"direction": "left",  "strength": 0.18},
    ("spleen", "throat"): {"direction": "left",  "strength": 0.25},
}

# Map each gate to its center
GATE_TO_CENTER = {
    # Head
    64: "head", 61: "head", 63: "head",
    # Ajna
    47: "ajna", 24: "ajna", 4: "ajna", 17: "ajna", 43: "ajna", 11: "ajna",
    # Throat
    62: "throat", 23: "throat", 56: "throat", 16: "throat", 20: "throat",
    35: "throat", 12: "throat", 45: "throat", 31: "throat", 8: "throat", 33: "throat",
    # G / Ji
    7: "G", 1: "G", 13: "G", 25: "G", 15: "G", 2: "G", 46: "G", 10: "G",
    # Ego / Will
    21: "ego", 51: "ego", 26: "ego", 40: "ego",
    # Sacral
    5: "sacral", 14: "sacral", 29: "sacral", 34: "sacral", 27: "sacral",
    59: "sacral", 42: "sacral", 3: "sacral", 9: "sacral",
    # Spleen
    48: "spleen", 57: "spleen", 44: "spleen", 50: "spleen",
    32: "spleen", 28: "spleen", 18: "spleen",
    # Solar Plexus
    36: "solar", 22: "solar", 37: "solar", 6: "solar",
    49: "solar", 55: "solar", 30: "solar",
    # Root
    53: "root", 60: "root", 52: "root", 54: "root", 38: "root",
    58: "root", 19: "root", 39: "root", 41: "root",
}


# ---------------------------------------------------------------------------
# SVG path parsing
# ---------------------------------------------------------------------------
def parse_svg_path(d):
    """Parse SVG path d-string into list of absolute (x, y) coordinates."""
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?[0-9]*\.?[0-9]+', d)
    points = []
    cx, cy = 0, 0
    i = 0
    cmd = 'M'
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in ('Z', 'z'):
                continue
        if cmd == 'M':
            cx, cy = float(tokens[i]), float(tokens[i+1])
            points.append((cx, cy))
            i += 2
            cmd = 'L'  # implicit
        elif cmd == 'm':
            cx += float(tokens[i]); cy += float(tokens[i+1])
            points.append((cx, cy))
            i += 2
            cmd = 'l'
        elif cmd == 'L':
            cx, cy = float(tokens[i]), float(tokens[i+1])
            points.append((cx, cy))
            i += 2
        elif cmd == 'l':
            cx += float(tokens[i]); cy += float(tokens[i+1])
            points.append((cx, cy))
            i += 2
        else:
            i += 1  # skip unknown
    return points


def strip_from_polygon(pts):
    """
    Given 4 polygon corners, extract:
    - spine_start, spine_end (midpoints of the two short edges)
    - width (average of the two short edge lengths)

    Assumes corners go: P0 → P1 (long edge) → P2 → P3 (long edge back).
    Short edges are P0-P3 and P1-P2.
    """
    if len(pts) == 5:
        pts = pts[:4]  # drop closing duplicate
    assert len(pts) == 4, f"Expected 4 points, got {len(pts)}"
    p0, p1, p2, p3 = pts

    w03 = math.dist(p0, p3)
    w12 = math.dist(p1, p2)

    spine_start = ((p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2)
    spine_end   = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    width = (w03 + w12) / 2

    return spine_start, spine_end, width


# ---------------------------------------------------------------------------
# Bézier math
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def cubic_bezier(p0, p1, p2, p3, t):
    """Evaluate cubic Bézier at parameter t."""
    u = 1 - t
    return (
        u**3 * p0[0] + 3*u**2*t * p1[0] + 3*u*t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3*u**2*t * p1[1] + 3*u*t**2 * p2[1] + t**3 * p3[1],
    )


def cubic_bezier_tangent(p0, p1, p2, p3, t):
    """Tangent vector of cubic Bézier at parameter t."""
    u = 1 - t
    return (
        3*u**2 * (p1[0]-p0[0]) + 6*u*t * (p2[0]-p1[0]) + 3*t**2 * (p3[0]-p2[0]),
        3*u**2 * (p1[1]-p0[1]) + 6*u*t * (p2[1]-p1[1]) + 3*t**2 * (p3[1]-p2[1]),
    )


def perpendicular(tangent):
    """Unit vector perpendicular to tangent (rotated 90° CCW)."""
    tx, ty = tangent
    length = math.sqrt(tx*tx + ty*ty)
    if length < 1e-9:
        return (0, 0)
    return (-ty / length, tx / length)


def make_spine_curve(spine_start, spine_end, center_a, center_b):
    """
    Create cubic Bézier control points for a channel spine.

    Uses quadratic-to-cubic conversion:
    1. Compute a single pull point Q offset perpendicular to the chord midpoint
    2. Convert to cubic: CP1 = P0 + 2/3*(Q-P0), CP2 = P2 + 2/3*(Q-P2)
    This guarantees symmetric, circular-looking arcs.
    """
    pair_key = (center_a, center_b)
    params = CURVE_PARAMS.get(pair_key)
    if not params:
        # try reversed
        pair_key = (center_b, center_a)
        params = CURVE_PARAMS.get(pair_key)
    if not params or params["direction"] == "straight":
        # straight line: CPs at 1/3 and 2/3 along chord
        cp1 = lerp(spine_start, spine_end, 1/3)
        cp2 = lerp(spine_start, spine_end, 2/3)
        return spine_start, cp1, cp2, spine_end

    direction = params["direction"]
    strength = params["strength"]

    # chord midpoint and vector
    mid = lerp(spine_start, spine_end, 0.5)
    chord_vec = (spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])
    chord_len = math.sqrt(chord_vec[0]**2 + chord_vec[1]**2)

    if chord_len < 1e-9:
        return spine_start, mid, mid, spine_end

    # perpendicular to chord
    perp = perpendicular(chord_vec)

    # displacement
    disp = chord_len * strength
    if direction == "right":
        disp = -disp  # flip direction

    # quadratic pull point Q
    Q = (mid[0] + perp[0] * disp, mid[1] + perp[1] * disp)

    # convert quadratic to cubic
    cp1 = (spine_start[0] + 2/3 * (Q[0] - spine_start[0]),
            spine_start[1] + 2/3 * (Q[1] - spine_start[1]))
    cp2 = (spine_end[0] + 2/3 * (Q[0] - spine_end[0]),
            spine_end[1] + 2/3 * (Q[1] - spine_end[1]))

    return spine_start, cp1, cp2, spine_end


def bend_strip(spine_start, spine_end, width, center_a, center_b, n_samples=40):
    """
    Warp a straight strip along a Bézier spine.

    Returns two lists of points: left_edge and right_edge (forming the
    outline of the curved strip).
    """
    p0, cp1, cp2, p3 = make_spine_curve(spine_start, spine_end, center_a, center_b)
    half_w = width / 2

    left_edge = []
    right_edge = []

    for i in range(n_samples + 1):
        t = i / n_samples
        pt = cubic_bezier(p0, cp1, cp2, p3, t)
        tan = cubic_bezier_tangent(p0, cp1, cp2, p3, t)
        perp = perpendicular(tan)

        left_edge.append((pt[0] + perp[0] * half_w,
                          pt[1] + perp[1] * half_w))
        right_edge.append((pt[0] - perp[0] * half_w,
                           pt[1] - perp[1] * half_w))

    return left_edge, right_edge


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
VW, VH = 851.41, 1309.4


def draw_curved_channel(d, gate_a, gate_b, color="#fff", opacity=0.8):
    """Parse the hdkit polygon for gate_a, bend it along the spine, draw it."""
    path_str = HDKIT_GATE_PATHS.get(gate_a)
    if not path_str:
        return

    pts = parse_svg_path(path_str)
    if len(pts) < 4:
        return

    spine_start, spine_end, width = strip_from_polygon(pts)
    center_a = GATE_TO_CENTER.get(gate_a, "")
    center_b = GATE_TO_CENTER.get(gate_b, "")

    left_edge, right_edge = bend_strip(
        spine_start, spine_end, width, center_a, center_b
    )

    # Build filled polygon from left_edge forward + right_edge reversed
    all_pts = left_edge + list(reversed(right_edge))
    flat = []
    for p in all_pts:
        flat.extend(p)

    d.append(draw.Lines(*flat, close=True,
                        fill=color, fill_opacity=opacity,
                        stroke="none"))


def draw_channel_pair(d, gate_a, gate_b, color="#ffffff"):
    """Draw both halves of a channel (one polygon strip per gate)."""
    draw_curved_channel(d, gate_a, gate_b, color=color, opacity=0.7)
    draw_curved_channel(d, gate_b, gate_a, color=color, opacity=0.7)


def draw_bodygraph(outfile="experiments/bent_bodygraph.svg"):
    d = draw.Drawing(VW, VH, viewBox=f"0 0 {VW} {VH}")

    # background
    d.append(draw.Rectangle(0, 0, VW, VH, fill="#0f0f1a"))

    # draw channels
    for ga, gb in CHANNELS:
        draw_channel_pair(d, ga, gb, color="#445566")

    # draw integration special connectors (straight, these are triangular fills)
    for name, path_d in HDKIT_SPECIAL_PATHS.items():
        d.append(draw.Path(d=path_d, fill="#445566", fill_opacity=0.7, stroke="none"))

    # draw centers using hdkit's proper shapes
    for name, path_d in HDKIT_CENTER_PATHS.items():
        d.append(draw.Path(d=path_d, fill="#1a1a2e", stroke="#667788",
                           stroke_width=2))

    # draw gate numbers
    from libaditya.hd import constants as hdc
    for i in range(1, 65):
        d.append(draw.Text(hdc.gates[i][0], font_size=14,
                           x=hdc.gates[i][2] * VW/500,
                           y=hdc.gates[i][3] * VH/500,
                           fill="#aabbcc", font_family="monospace"))

    d.save_svg(outfile)
    print(f"Saved to {outfile}")


def draw_comparison(outfile="experiments/bent_comparison.svg"):
    """Side-by-side: straight (hdkit original) vs bent."""
    total_w = VW * 2 + 40
    d = draw.Drawing(total_w, VH + 40, viewBox=f"0 0 {total_w} {VH + 40}")
    d.append(draw.Rectangle(0, 0, total_w, VH + 40, fill="#0f0f1a"))

    # Labels
    d.append(draw.Text("STRAIGHT (hdkit original)", font_size=20,
                        x=VW/2 - 120, y=25, fill="#aabbcc"))
    d.append(draw.Text("BENT (curved spines)", font_size=20,
                        x=VW + 40 + VW/2 - 100, y=25, fill="#aabbcc"))

    # --- Left: straight channels using raw hdkit paths ---
    g_left = draw.Group(transform=f"translate(0, 30)")

    for ga, gb in CHANNELS:
        for gate in (ga, gb):
            path_str = HDKIT_GATE_PATHS.get(gate)
            if path_str:
                g_left.append(draw.Path(d=path_str, fill="#445566",
                                        fill_opacity=0.7, stroke="none"))
    for name, path_d in HDKIT_SPECIAL_PATHS.items():
        g_left.append(draw.Path(d=path_d, fill="#445566", fill_opacity=0.7))
    for name, path_d in HDKIT_CENTER_PATHS.items():
        g_left.append(draw.Path(d=path_d, fill="#1a1a2e", stroke="#667788",
                                stroke_width=2))
    d.append(g_left)

    # --- Right: bent channels ---
    g_right = draw.Group(transform=f"translate({VW + 40}, 30)")

    for ga, gb in CHANNELS:
        # bent version
        for gate, partner in ((ga, gb), (gb, ga)):
            path_str = HDKIT_GATE_PATHS.get(gate)
            if not path_str:
                continue
            pts = parse_svg_path(path_str)
            if len(pts) < 4:
                continue
            spine_start, spine_end, width = strip_from_polygon(pts)
            center_a = GATE_TO_CENTER.get(gate, "")
            center_b = GATE_TO_CENTER.get(partner, "")
            left_edge, right_edge = bend_strip(spine_start, spine_end, width,
                                                center_a, center_b)
            all_pts = left_edge + list(reversed(right_edge))
            flat = []
            for p in all_pts:
                flat.extend(p)
            g_right.append(draw.Lines(*flat, close=True,
                                       fill="#445566", fill_opacity=0.7,
                                       stroke="none"))

    for name, path_d in HDKIT_SPECIAL_PATHS.items():
        g_right.append(draw.Path(d=path_d, fill="#445566", fill_opacity=0.7))
    for name, path_d in HDKIT_CENTER_PATHS.items():
        g_right.append(draw.Path(d=path_d, fill="#1a1a2e", stroke="#667788",
                                 stroke_width=2))
    d.append(g_right)

    d.save_svg(outfile)
    print(f"Comparison saved to {outfile}")


if __name__ == "__main__":
    if "--compare" in sys.argv:
        draw_comparison()
    else:
        draw_bodygraph()
