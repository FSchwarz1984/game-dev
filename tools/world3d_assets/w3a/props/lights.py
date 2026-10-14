"""Lights: stone lanterns (石灯籠) by the shrine steps and a hanging paper lantern (提灯) for the
graves' hooks and the eaves. Each has an unlit scene, a lit one (the fire box / the paper glows at
dusk and night: emission_at_night) and the faded twin; anchors.light is where the renderer hangs
its point light, anchors.hang where a paper lantern hangs from."""
from __future__ import annotations

import math

import numpy as np

from ..core import rng
from . import kit as K
from .common import export_prop

STONE = K.col('#7d7a72')
STONE_OLD = K.col('#77776a')
DARK = K.col('#3b3733')
GLOW = np.array([1.0, 0.86, 0.6])


def _ngon(P, n, apothem, rot=0.0):
    """Distance to the sides of a regular n-gon prism (infinite in y), negative inside."""
    x, z = P[..., 0], P[..., 2]
    rho = np.hypot(x, z)
    phi = np.arctan2(z, x) - rot
    s = 2 * math.pi / n
    ph = np.mod(phi + s / 2, s) - s / 2
    return rho * np.cos(ph) - apothem


def _slab(P, y0, y1):
    return np.maximum(y0 - P[..., 1], P[..., 1] - y1)


def _part(d_side, P, y0, y1, r=0.012):
    """A prism between heights y0 and y1, its edges rounded by r."""
    a = d_side + r
    b = _slab(P, y0 + r, y1 - r)
    return np.minimum(np.maximum(a, b), 0) + np.hypot(np.maximum(a, 0), np.maximum(b, 0)) - r


def lantern_sdf(P, tall=1.0, lean=0.0, old=False, seed=0):
    """Kasuga-style stone lantern (simplified), 1.45 m (tall=1). Hexagonal parts turn a face to the
    camera (+z); the fire box has a square window front and back and round ones on the slanted
    faces."""
    Q = P.copy()
    if lean:
        Q[..., 0] = Q[..., 0] - lean * np.maximum(Q[..., 1], 0)
    y = Q[..., 1]
    s = tall
    rot = math.pi / 2
    rr = np.hypot(Q[..., 0], Q[..., 2])
    d = _part(_ngon(Q, 6, 0.27, rot), Q, 0.0, 0.13 * s, 0.02)                            # base
    d = np.minimum(d, _part(_ngon(Q, 6, 0.18, rot), Q, 0.12 * s, 0.2 * s, 0.015))       # socket
    pole = _part(rr - 0.085, Q, 0.19 * s, 0.76 * s, 0.01)                                 # pole
    band = _part(rr - 0.1, Q, 0.46 * s, 0.5 * s, 0.01)
    d = np.minimum(d, np.minimum(pole, band))
    t = np.clip((y - 0.75 * s) / (0.11 * s), 0, 1)                                       # platform, flaring
    d = np.minimum(d, _part(_ngon(Q, 6, 0.13 + 0.12 * t, rot), Q, 0.75 * s, 0.86 * s, 0.012))
    yc = 0.99 * s
    box = _part(_ngon(Q, 6, 0.15, rot), Q, 0.86 * s, 1.12 * s, 0.01)                   # fire box
    hole = np.maximum(np.abs(Q[..., 0]) - 0.06, np.abs(Q[..., 1] - yc) - 0.075)          # front / back
    for a in (math.radians(30), math.radians(150)):                                        # round side windows
        n = np.array([math.cos(a), 0.0, math.sin(a)])
        along = Q @ n
        off = Q - along[..., None] * n - np.array([0, yc, 0])
        hole = np.minimum(hole, np.linalg.norm(off, axis=-1) - 0.045)
    box = np.maximum(box, -hole)
    box = np.maximum(box, -_part(_ngon(Q, 6, 0.11, rot), Q, 0.88 * s, 1.1 * s, 0.005))  # hollow inside
    d = np.minimum(d, box)
    tr = np.clip((y - 1.12 * s) / (0.2 * s), 0, 1)                                       # roof, concave
    ap = 0.36 - 0.29 * tr ** 0.55
    roof = _part(_ngon(Q, 6, ap, rot), Q, 1.115 * s, 1.33 * s, 0.012)
    for i in range(6):                                                                    # curled corners
        a = 2 * math.pi * i / 6
        c = np.array([math.cos(a) * 0.4, 1.16 * s, math.sin(a) * 0.4])
        roof = K.smin(roof, np.linalg.norm(Q - c, axis=-1) - 0.034, 0.03)
    d = np.minimum(d, roof)
    d = np.minimum(d, _part(rr - 0.06, Q, 1.32 * s, 1.36 * s, 0.01))                   # lotus
    fin = np.linalg.norm((Q - np.array([0, 1.415 * s, 0])) * np.array([1, 0.85, 1]), axis=-1) - 0.06
    tip = np.linalg.norm(Q - np.array([0, 1.47 * s, 0]), axis=-1) - 0.022
    d = np.minimum(d, K.smin(fin, tip, 0.03))
    d = d + K.weathered(P, 0.006 if not old else 0.011, 0.07, seed)
    return d


def stone_lantern(out, name='stone_lantern', old=False, seed=7801):
    """Built from chamfered stone pieces (crisp planes read better in pixels than a noisy surface).
    Q proportion: the fire box is enlarged so its window reads (3 x 5 px)."""
    R = rng(seed)
    colour = STONE_OLD if old else STONE
    k = 0.86 if old else 1.0                     # the old one is squatter
    pieces = []

    def st(pc, amount=0.25):
        pc.pattern = K.PAT['stone']
        pc.amount = amount
        pc.var = 0.05
        pc.seed = int(R.integers(0, 1 << 20))
        pc.colour = colour * (1 + R.normal(0, 0.03))
        return pc
    y = 0.0
    pieces.append(st(K.cprism(6, 0.31, 0.29, 0.12, colour, base=(0, y, 0), bevel=0.02), 0.5))
    y += 0.12
    pieces.append(st(K.cprism(6, 0.2, 0.17, 0.08, colour, base=(0, y, 0), bevel=0.015)))
    y += 0.08
    ph = 0.56 * k
    pieces.append(st(K.cprism(12, 0.088, 0.08, ph, colour, base=(0, y, 0), bevel=0.01)))
    pieces.append(st(K.cprism(12, 0.102, 0.102, 0.04, colour, base=(0, y + ph * 0.48, 0), bevel=0.01)))
    y += ph
    pieces.append(st(K.cprism(6, 0.15, 0.29, 0.1, colour, base=(0, y, 0), bevel=0.015), 0.6))
    y += 0.1
    fb0 = y
    rf = 0.2
    pieces.append(st(K.cprism(6, rf + 0.02, rf + 0.02, 0.025, colour, base=(0, y, 0), bevel=0.008)))
    hbox = 0.27
    for i in range(6):                                            # corner posts
        a = 2 * math.pi * i / 6
        c = np.array([math.cos(a) * rf, y + hbox / 2, math.sin(a) * rf])
        pieces.append(st(K.cbox((0.05, hbox, 0.05), colour, centre=c, bevel=0.008, R=K.rot_y(-a))))
    for a in (math.radians(30), math.radians(150), math.radians(210), math.radians(330)):   # side panels
        c = np.array([math.cos(a) * rf * 0.87, y + hbox / 2, math.sin(a) * rf * 0.87])
        pieces.append(st(K.cbox((0.035, hbox * 0.92, rf * 0.95), colour, centre=c, bevel=0.006, R=K.rot_y(-a))))
    y += hbox
    pieces.append(st(K.cprism(6, rf + 0.02, rf + 0.02, 0.025, colour, base=(0, y, 0), bevel=0.008)))
    y += 0.02
    roof = [(0.42, 0.37, 0.05), (0.37, 0.21, 0.09), (0.21, 0.09, 0.07)]
    for r0, r1, hh in roof:
        pieces.append(st(K.cprism(6, r0, r1, hh, colour, base=(0, y, 0), bevel=0.012), 0.55 if old else 0.3))
        y += hh
    for i in range(6):                                            # curled corners (warabi-te)
        a = 2 * math.pi * i / 6
        c = np.array([math.cos(a) * 0.425, fb0 + hbox + 0.085, math.sin(a) * 0.425])
        pieces.append(st(K.cbox((0.075, 0.07, 0.07), colour, centre=c, bevel=0.015, R=K.rot_y(-a))))
    fin = K.lathe([(0.065, 0.0), (0.08, 0.025), (0.055, 0.045), (0.07, 0.075), (0.065, 0.1), (0.035, 0.13), (0.0, 0.155)],
                  colour, n=10, base=(0, y, 0))
    pieces.append(st(fin, 0.3))
    top = y + 0.155
    lit_y = fb0 + hbox / 2

    def core(lit):
        return K.cprism(6, rf * 0.92, rf * 0.92, hbox * 0.86, GLOW if lit else DARK, base=(0, fb0 + hbox * 0.07, 0), bevel=0.0,
                        mat='lit' if lit else 'solid', ao=not lit, dirt=False, var=0.0, seed=seed + 5)
    lean = 0.04 if old else 0.0

    def leaned(pc):
        if not lean:
            return pc
        P = pc.p.copy()
        P[:, 0] += lean * P[:, 1]
        q = K.Piece(P, pc.n, pc.idx, pc.colour, pc.pattern, pc.amount, pc.mat, pc.var, pc.seed, pc.ao, pc.dirt,
                    pc.emissive, pc.shade)
        return q
    unlit = K.Prop(name, seed).add([leaned(p) for p in pieces], leaned(core(False)))
    litp = K.Prop(name + '_lit', seed).add([leaned(p) for p in pieces], leaned(core(True)))
    cat = {'footprint': [[0.0, 0.0, 0.32]], 'tags': ['light', 'stone'],
           'notes': ('Old weathered stone lantern, squat, leaning a little, mossy.' if old else
                     'Kasuga-style stone lantern (simplified), %.2f m; a pair flanks the shrine steps.' % top)
           + ' Variants: lit (the fire box glows at dusk and night), far (faded).'}
    return export_prop(out, name, 'lights', unlit, cat, porosity=0.6, markers={'light': [lean * lit_y, lit_y, 0.0]},
                       variants={'lit': litp}, budget=2000)


def paper_lantern(out, name='lantern_paper', seed=7811):
    """A white hanging chochin: paper oval on bamboo ribs, black lacquered rims, a cord loop."""
    prof = [(0.09, 0.0), (0.135, 0.04), (0.16, 0.11), (0.165, 0.2), (0.155, 0.29), (0.13, 0.35), (0.09, 0.39)]

    def body(lit):
        def shade(P, N):
            # the ribs: faint darker rings every 3 cm
            r = (np.floor(P[:, 1] / 0.03) % 2 == 0)
            m = np.ones((len(P), 3))
            m[r] *= 0.94
            return m
        return K.lathe(prof, GLOW * 0.98 if lit else K.col('#e6ddc8'), n=14, base=(0, 0.04, 0), pattern='paper',
                       amount=0.3, mat='lit' if lit else 'paper', var=0.02, seed=seed, ao=not lit, dirt=False,
                       shade=shade, smooth=True)
    rim = K.col('#2a221e')
    rims = [K.lathe([(0.088, 0.0), (0.1, 0.004), (0.1, 0.04), (0.086, 0.044)], rim, n=12, base=(0, 0.0, 0),
                    var=0.0, seed=seed + 1, dirt=False),
            K.lathe([(0.086, 0.0), (0.098, 0.004), (0.098, 0.036), (0.084, 0.04)], rim, n=12, base=(0, 0.42, 0),
                    var=0.0, seed=seed + 2, dirt=False)]
    cord = K.rod([[0, 0.46, 0], [0.025, 0.53, 0], [0, 0.58, 0], [-0.025, 0.53, 0], [0, 0.46, 0]], 0.008, rim, n=4,
                 cap=False, step=0.02, dirt=False, var=0.0)
    unlit = K.Prop(name, seed).add(body(False), rims, cord)
    litp = K.Prop(name + '_lit', seed).add(body(True), rims, cord)
    cat = {'footprint': [], 'tags': ['light', 'pickup', 'hang'],
           'notes': 'White chochin, 0.58 m with its loop; origin at the bottom rim, anchors.hang at the loop top. '
                    'Ten of these hang on the graves\' hooks (graves anchors.hook_*).'}
    return export_prop(out, name, 'lights', unlit, cat, porosity=0.3, ground=False,
                       markers={'light': [0.0, 0.22, 0.0], 'hang': [0.0, 0.58, 0.0]}, variants={'lit': litp}, budget=800)


def build(out):
    st = {}
    st['stone_lantern'] = stone_lantern(out)
    st['stone_lantern_old'] = stone_lantern(out, 'stone_lantern_old', old=True, seed=7805)
    st['lantern_paper'] = paper_lantern(out)
    return st
