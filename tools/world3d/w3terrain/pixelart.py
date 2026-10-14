"""Hand-drawn pixel-art pieces for the terrain shader, written as text so they can be read and
edited like sprites:

  palette.png  8 tones x 16 rows (sRGB). Rows are ground materials; tone 0 dark .. 7 light,
               built in CIELAB: chroma peaks in the middle, darks lean cool, lights lean warm.
               Row 11 holds accent colours (flowers, roots, lichen, fallen leaves).
  glyphs.png   16 x 16 glyphs of 8 x 8 px. R = tone offset (+4 encoded, i.e. 4 = no change),
               G = accent colour index + 1 (0 = use the material ramp), B = 0, A = 255 where drawn.
               The shader stamps them on the screen-texel lattice, so they stand upright facing
               the camera like sprites painted on the ground.

Glyph characters: '.' empty; tone offsets '1'..'4' = -1..-4 (darker), 'm' 0, 'a' +1, 'b' +2,
'c' +3; accents 'W' white, 'Y' yellow, 'B' blue-violet, 'P' pink, 'R' root, 'L' pale lichen,
'O' orange lichen, 'E' red-brown leaf, 'K' dark twig, 'G' fresh green, 'S' straw.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color

ROWS = {
    # name: (L*, C*, hue deg) of the middle tone (index 3.5); albedos, the light adds its own warmth
    "grass": (34.0, 19.0, 128.0),
    "grass_dry": (40.0, 19.0, 104.0),
    "dirt": (41.0, 12.0, 68.0),
    "gravel": (46.0, 6.0, 72.0),
    "rock": (42.0, 5.0, 220.0),
    "moss": (31.0, 24.0, 124.0),
    "litter": (31.0, 12.0, 66.0),
    "needles": (31.0, 14.0, 56.0),
    "bamboo_litter": (45.0, 12.0, 86.0),
    "bank": (36.0, 15.0, 58.0),
    "paddy": (30.0, 11.0, 96.0),
}
ROW_INDEX = {k: i for i, k in enumerate(ROWS)}
ACCENT_ROW = 11
ACCENTS = {
    "W": (88.0, 6.0, 95.0), "Y": (80.0, 62.0, 92.0), "B": (52.0, 42.0, 290.0), "P": (66.0, 32.0, 350.0),
    "R": (30.0, 18.0, 55.0), "L": (66.0, 10.0, 120.0), "O": (50.0, 24.0, 62.0), "E": (34.0, 22.0, 44.0),
    "K": (20.0, 8.0, 60.0), "G": (52.0, 34.0, 122.0), "S": (64.0, 22.0, 88.0),
}
ACCENT_ORDER = "WYBPRLOEKGS"


def lch_to_srgb(L, C, h):
    lab = np.array([[[L, C * np.cos(np.radians(h)), C * np.sin(np.radians(h))]]])
    rgb = color.lab2rgb(lab)[0, 0]
    return np.clip(rgb, 0, 1)


def ramp(L, C, h, n=8):
    out = []
    for i in range(n):
        t = (i - 3.5) / 3.5                       # -1 dark .. +1 light
        Li = L + t * (13.0 if t > 0 else 15.0)
        Ci = C * (1.0 - 0.38 * abs(t) ** 1.4)
        hi = h + (-14.0 * -t if t < 0 else 10.0 * -t) * (1 if h > 90 else -0.6)
        # darks lean toward cyan-blue, lights toward yellow (hue wheel: 90 yellow, 200 cyan)
        if t < 0:
            hi = h + (200.0 - h) * 0.12 * -t if h < 200 else h
        else:
            hi = h + (90.0 - h) * 0.10 * t
        out.append(lch_to_srgb(Li, Ci, hi))
    return np.array(out)


def palette():
    P = np.zeros((16, 8, 3))
    for name, (L, C, h) in ROWS.items():
        P[ROW_INDEX[name]] = ramp(L, C, h)
    for i, ch in enumerate(ACCENT_ORDER):
        P[ACCENT_ROW, i % 8] = lch_to_srgb(*ACCENTS[ch]) if i < 8 else P[ACCENT_ROW, i % 8]
    # accents beyond 8 go to row 12
    for i, ch in enumerate(ACCENT_ORDER[8:]):
        P[ACCENT_ROW + 1, i] = lch_to_srgb(*ACCENTS[ch])
    return (np.clip(P, 0, 1) * 255).round().astype(np.uint8)


# ------------------------------------------------------------------------------------------------
# glyphs, 8x8 max, bottom-left anchored (the shader places them on the lattice)
G = {}
# grass tufts (blades catch the light at the tips; a dark root pixel below)
G["tuft_a"] = """
...c....
..bc.c..
..b.bb..
.ama.a..
.1m1ma..
..2211..
"""
G["tuft_b"] = """
.c...c..
.bc.cb..
..bbc...
.ambma..
.1mamm1.
..2222..
"""
G["tuft_c"] = """
..c.....
.cb..c..
.b.a.b..
.amam1..
..2121..
"""
G["tuft_d"] = """
....c...
.c..b.c.
.b.cb.b.
.ambambm
.1mam1m1
..22222.
"""
G["blade"] = """
.b..
.a..
1m..
"""
G["hollow"] = """
.......
..1....
.212...
..1....
"""
G["clover"] = """
.aba...
abmba..
.a1a...
"""
# flowers (accent colours), tiny and sparse
G["daisy"] = """
W.
.m
"""
G["yellow"] = """
Y.
.a
"""
G["tsuyukusa"] = """
B.
Bm
"""
G["nadeshiko"] = """
.P
P.
.a
"""
# stones and pebbles (light top-left, dark bottom-right)
G["pebble"] = """
bm.
m2.
"""
G["stone"] = """
.ba..
bam1.
.m21.
"""
G["stone_big"] = """
..bba..
.bbam1.
.amm21.
..2221.
"""
G["crack"] = """
2.......
.22.....
...2....
....22..
"""
G["rut"] = """
22222.
.1111.
"""
G["root"] = """
.......
RR.....
..RRR..
.....RR
"""
G["twig"] = """
K......
.KK....
...K...
....KK.
"""
# rock: cracks, strata, lichen
G["rock_crack"] = """
.3......
..3.....
..32....
....3...
.....3..
"""
G["strata"] = """
222222..
.aaaa...
"""
G["lichen"] = """
.L.
LLL
.L.
"""
G["lichen_o"] = """
O.
OO
"""
G["rock_chip"] = """
.cb.
cbm2
.m22
"""
# moss cushions and sparkles
G["moss_bump"] = """
..bb..
.bbaa.
.aamm.
.1111.
"""
G["moss_small"] = """
.b.
bam
.1.
"""
G["spore"] = """
c.
"""
# leaf litter (broadleaf), needles, bamboo leaves
G["leaf_a"] = """
.E.
EaE
.E.
"""
G["leaf_b"] = """
ba.
.aa
..1
"""
G["leaf_c"] = """
.bb
bm.
"""
G["leaf_red"] = """
EE.
.E.
"""
G["needles"] = """
O...
.O..
..O.
"""
G["needles_b"] = """
...O
..O.
.O..
"""
G["bamboo_leaf"] = """
SSS..
..SSS
"""
# bank earth: roots and crumbs
G["bank_crumb"] = """
.b.
b1.
"""
G["bank_line"] = """
2222..
.aa...
"""

# which glyphs each ground material uses, with their weights; the shader reads this layout:
# material m uses glyph indices [GSTART[m], GSTART[m] + GCOUNT[m])
SETS = {
    "grass": [("tuft_a", 4), ("tuft_b", 3), ("tuft_c", 4), ("tuft_d", 2), ("blade", 3), ("hollow", 3), ("clover", 1)],
    "flowers": [("daisy", 2), ("yellow", 3), ("tsuyukusa", 2), ("nadeshiko", 1)],
    "dirt": [("pebble", 5), ("stone", 2), ("crack", 1), ("rut", 1), ("root", 1)],
    "gravel": [("pebble", 4), ("stone", 3), ("stone_big", 1)],
    "rock": [("rock_crack", 2), ("strata", 3), ("lichen", 2), ("lichen_o", 1), ("rock_chip", 2)],
    "moss": [("moss_bump", 3), ("moss_small", 4), ("spore", 2)],
    "litter": [("leaf_b", 4), ("leaf_c", 4), ("leaf_a", 2), ("leaf_red", 1)],
    "needles": [("needles", 3), ("needles_b", 3)],
    "bamboo_litter": [("bamboo_leaf", 4), ("twig", 1)],
    "bank": [("bank_crumb", 3), ("bank_line", 2), ("root", 2), ("pebble", 1)],
}

CODE = {".": None, "1": -1, "2": -2, "3": -3, "4": -4, "m": 0, "a": 1, "b": 2, "c": 3}


def parse(txt):
    rows = [r for r in txt.strip("\n").split("\n")]
    return rows


def glyph_atlas():
    """Returns the atlas image and the table (set name -> (start index, count)), slots in order."""
    img = np.zeros((128, 128, 4), np.uint8)
    table = {}
    slot = 0
    for sname, items in SETS.items():
        start = slot
        for gname, weight in items:
            for _ in range(weight):
                rows = parse(G[gname])
                gy0 = (slot // 16) * 8
                gx0 = (slot % 16) * 8
                h = len(rows)
                for ry, row in enumerate(rows):
                    for rx, ch in enumerate(row):
                        if rx >= 8:
                            continue
                        y = gy0 + (8 - h) + ry          # bottom-aligned in the 8x8 slot
                        x = gx0 + rx
                        if ch in CODE and CODE[ch] is not None:
                            img[y, x] = (CODE[ch] + 4, 0, 0, 255)
                        elif ch in ACCENT_ORDER:
                            img[y, x] = (4, ACCENT_ORDER.index(ch) + 1, 0, 255)
                slot += 1
        table[sname] = (start, slot - start)
    return img, table


def write(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    pal = palette()
    Image.fromarray(pal, "RGB").save(out_dir / "palette.png")
    atlas, table = glyph_atlas()
    Image.fromarray(atlas, "RGBA").save(out_dir / "glyphs.png")
    for f in ("palette.png", "glyphs.png"):
        imp = out_dir / (f + ".import")
        if not imp.exists():
            imp.write_text('[remap]\n\nimporter="image"\ntype="Image"\n')
    return table
