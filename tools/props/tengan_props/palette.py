"""Colour ramps for every prop material (docs/knowledge/19-props.md section 3).

All ramps are built in CIELAB around a base colour (core.ramp): darks drift to blue-violet, lights to
warm ochre, chroma peaks in the middle and stays low overall: v0.1's low-saturation natural colours
(P-2). Bases were chosen next to the terrain's measured albedos (meadow ~ (82, 95, 70), dirt
(118, 103, 84), gravel (118, 113, 102), moss (70, 83, 57)) so props sit on the ground without
glowing: dressing stays near ground values; interactables get a wider value range.
"""
import numpy as np

from .core import ramp

# name: (base, n, dark, light, extra kwargs)
SPEC = {
    'wood_old':   ('#7b6e62', 8, 0.50, 0.32, {}),       # silvered weathered boards
    'wood_dark':  ('#4f4035', 8, 0.55, 0.34, {}),       # posts, sills, beams (smoke-darkened)
    'wood_new':   ('#b39470', 8, 0.48, 0.30, {}),       # fresh-cut wood: the new door bar, split ends
    'wood_end':   ('#9c7c58', 7, 0.50, 0.32, {}),       # end grain of firewood
    'bark':       ('#6a4c3c', 8, 0.52, 0.32, {}),       # cedar bark, bark shingles
    'thatch':     ('#8a7a56', 9, 0.56, 0.36, {}),       # aged thatch, grey-ochre
    'straw':      ('#b49c68', 8, 0.50, 0.30, {}),       # fresh straw: bundles, sandals
    'rope':       ('#bca674', 7, 0.50, 0.30, {}),       # straw rope, shimenawa
    'plaster':    ('#a6926f', 8, 0.48, 0.32, {}),       # earth wall (中塗り)
    'mud':        ('#7e6a50', 7, 0.50, 0.30, {}),       # exposed mud and straw where plaster fell
    'stone':      ('#87827a', 8, 0.52, 0.34, {}),       # granite: base stones, lanterns
    'stone_cool': ('#73766f', 8, 0.52, 0.34, {}),       # andesite: graves, dosojin slab
    'stone_warm': ('#8a8070', 8, 0.52, 0.34, {}),       # warm field stone
    'moss':       ('#5d6b3d', 7, 0.52, 0.34, {}),       # moss on stone and thatch (terrain moss family)
    'lichen':     ('#9c9c78', 5, 0.40, 0.25, {}),
    'paper':      ('#e2d8c2', 7, 0.36, 0.30, {'hue_light': 85.0}),
    'bamboo':     ('#a09660', 7, 0.50, 0.32, {}),       # old yellowed bamboo
    'bamboo_g':   ('#7a8c55', 7, 0.50, 0.32, {}),       # green bamboo (water spout)
    'iron':       ('#57585a', 6, 0.50, 0.38, {}),
    'rust':       ('#7c4e34', 6, 0.50, 0.32, {}),
    'indigo':     ('#3f4b6a', 7, 0.50, 0.32, {}),
    'ochre_cloth': ('#a8894e', 7, 0.50, 0.30, {}),
    'red':        ('#9a4434', 7, 0.50, 0.30, {}),        # weathered vermilion / red cord
    'lacquer':    ('#5c2e28', 6, 0.50, 0.30, {}),
    'white':      ('#e4e0d4', 6, 0.34, 0.40, {'hue_light': 90.0}),   # dango, shide paper, cups
    'water':      ('#4b6264', 6, 0.50, 0.40, {'hue_dark': 230.0}),
    'dark':       ('#2c2829', 5, 0.50, 0.30, {}),       # interiors, niches, gaps
    'earth':      ('#776650', 7, 0.50, 0.32, {}),       # soil, ash
    'leaf':       ('#5a6e40', 7, 0.52, 0.34, {}),       # sakaki, weeds, flowers' leaves
    'flower_y':   ('#cbb44e', 5, 0.40, 0.30, {}),
    'flower_w':   ('#dcd8c8', 5, 0.36, 0.30, {}),
    'flower_r':   ('#b04a3a', 5, 0.45, 0.30, {}),
    'orange':     ('#c0773c', 6, 0.50, 0.30, {}),       # persimmon, lantern glow tint
    'green_veg':  ('#6f8a46', 5, 0.50, 0.30, {}),       # cucumber horse
    'purple_veg': ('#5a4466', 5, 0.50, 0.30, {}),       # eggplant cow
}

NAMES = list(SPEC.keys())
ID = {n: i for i, n in enumerate(NAMES)}
RAMPS = []
for _n in NAMES:
    base, n, dk, lt, kw = SPEC[_n]
    RAMPS.append(ramp(base, n=n, dark=dk, light=lt, **kw))
SIZES = np.array([len(r) for r in RAMPS])


def color(pal_ids, idx):
    """Look up colours: pal_ids and idx are integer arrays of the same shape (idx clipped per ramp)."""
    pal_ids = np.asarray(pal_ids)
    idx = np.asarray(idx)
    out = np.zeros(pal_ids.shape + (3,))
    for p in np.unique(pal_ids):
        m = pal_ids == p
        r = RAMPS[int(p)]
        out[m] = r[np.clip(idx[m], 0, len(r) - 1)]
    return out


def sheet():
    """An image of every ramp (for the docs and for checking)."""
    w = max(SIZES) * 12 + 120
    img = np.zeros((len(NAMES) * 12, w, 3), np.uint8) + 30
    for i, r in enumerate(RAMPS):
        for k, c in enumerate(r):
            img[i * 12:(i + 1) * 12 - 2, 120 + k * 12:120 + k * 12 + 10] = c
    return img
