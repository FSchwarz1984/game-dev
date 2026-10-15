"""The sacred things of the home's barrier and its heart (round 4, G5R2-1 ②: the shrine's
surroundings should feel holy, a place apart, entered "by a special way").

  gate_stones   the main gate of the barrier: two old standing stones flanking the approach, a thick
                rope (注連縄) slung between them with paper streamers (紙垂) and straw tassels that move
                in the wind; moss on their shoulders
  chozubachi    the water basin before the shrine steps: a hollowed natural stone, a bamboo spout on a
                stand bringing the water, ladles on a bamboo rest
  ema_kake      a small roofed rack of votive plaques (絵馬)
  massha        a little side shrine on a stone, its own rope and a cup of sake
  iwakura       a great rock held sacred: a rope round its girth with streamers
  jizo          a roadside Jizo with a red bib and cap, a flower in a bamboo cup
  sekimori      a boundary stone (関守石): a round stone tied with a black cross of rope, set on a path
                ("go no further"); for the barrier's lesser gates
Origins on the ground, fronts toward +z (south, the camera)."""
from __future__ import annotations

import math

import numpy as np

from ..core import PX, fbm3, rng
from . import kit as K
from .common import export_prop

STONE = K.col('#8b877d')
STONE_OLD = K.col('#7d7a70')
ROPE = K.col('#b9a46a')
ROPE_DARK = K.col('#8c7a4a')
PAPER = K.col('#f0ece0')
WOOD = K.col('#85796b')
WOOD_DARK = K.col('#5a4e42')
BAMBOO = K.col('#9c9a5e')
WATER = K.col('#4f7c8a')
RED = K.col('#b8322a')


def _w(pc, pattern='bark', amount=0.3, seed=0, var=0.05):
    pc.pattern = K.PAT[pattern]
    pc.amount = amount
    pc.seed = seed
    pc.var = var
    return pc


def cyl(p0, p1, r, colour, n=6, **kw):
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    return K.cprism(n, r, r, float(np.linalg.norm(d)), colour, base=p0, bevel=0.0, R=K.frame_to(d), **kw)


def rope(points, r, seed, colour=ROPE):
    """A twisted straw rope along points: the body, and a darker spiral of the twist."""
    pc = K.rod(points, r, colour, n=6, cap=True, step=0.08, var=0.05, seed=seed)
    pc.pattern, pc.amount = K.PAT['thatch'], 0.25
    return pc


def shide(x, y, z, seed, scale=1.0, anchor=None):
    """紙垂: a zigzag paper streamer, four folds, hanging from (x, y, z); it swings."""
    R = rng(seed)
    P = []
    w = 0.07 * scale
    h = 0.075 * scale
    for k in range(4):
        dx = (w * 0.5) * (1 if k % 2 else -1) * 0.6
        yy = y - h * (k + 0.5)
        pc = K.cbox((w, h * 0.92, 0.008), PAPER, centre=(x + dx, yy, z), bevel=0.0, var=0.0, pattern='paper', amount=0.1)
        pc.swaying(anchor if anchor is not None else (x, y, z), 0.35 + 0.18 * k, mat='swaynl')
        P.append(pc)
    return P


def standing_stone(seed, H, W, D, lean=0.0):
    def f(Q):
        y = np.clip(Q[..., 1] / H, 0, 1)
        taper = 1.0 - 0.32 * y ** 1.5
        q = Q.copy()
        q[..., 0] = (Q[..., 0] - lean * Q[..., 1]) / (W * taper)
        q[..., 2] = Q[..., 2] / (D * taper)
        q[..., 1] = (Q[..., 1] - H * 0.48) / (H * 0.55)
        d = (np.sqrt(q[..., 0] ** 2 + q[..., 1] ** 2 + q[..., 2] ** 2) - 1.0) * min(W, D) * 0.6
        return d + K.weathered(Q, 0.045, 0.22, seed) + (fbm3(Q[..., 0] * 1.4, Q[..., 1] * 0.6, Q[..., 2] * 1.4, 2, seed + 1) - 0.5) * 0.1
    pc = K.sdf_piece(f, (-W * 1.3 - abs(lean) * H, -0.3, -D * 1.3), (W * 1.3 + abs(lean) * H, H * 1.08, D * 1.3), STONE_OLD, h=0.04,
                     tris=700, pattern='stone', amount=1.0, var=0.07, seed=seed)

    def mossy(Pp, N):
        m = np.ones((len(Pp), 3))
        top = (N[:, 1] > 0.35) & (fbm3(Pp[:, 0] * 2.5, Pp[:, 1] * 2.5, Pp[:, 2] * 2.5, 2, seed + 7) > 0.45)
        m[top] = np.array([0.62, 0.78, 0.5])
        foot = Pp[:, 1] < 0.35
        m[foot] *= 0.85
        return m
    pc.shade = mossy
    return pc


def gate_stones(out):
    R = rng(9801)
    P = []
    xl, xr = -1.65, 1.62
    Hl, Hr = 1.72, 1.45
    P.append(standing_stone(9802, Hl, 0.42, 0.36, lean=-0.05).moved(K.rot_y(0.2), (xl, 0.0, 0.0)))
    P.append(standing_stone(9803, Hr, 0.38, 0.34, lean=0.06).moved(K.rot_y(-0.3), (xr, 0.0, 0.02)))
    # the rope: wrapped round each stone near its top, slung between them with a deep sag
    ya, yb = Hl - 0.4, Hr - 0.35
    for (x, y, r) in ((xl, ya, 0.37), (xr, yb, 0.33)):
        ring = [[x + math.cos(a) * r, y + 0.02 * math.sin(2 * a), math.sin(a) * r * 0.9] for a in np.linspace(0, 2 * math.pi, 13)]
        P.append(rope(ring, 0.05, 9804))
    pts = []
    for t in np.linspace(0, 1, 13):
        x = xl + 0.3 + (xr - 0.27 - xl - 0.3) * t
        y = ya + (yb - ya) * t - 0.34 * math.sin(math.pi * t)
        pts.append([x, y, 0.12 + 0.06 * math.sin(math.pi * t)])
    P.append(rope(pts, 0.07, 9805))
    P.append(rope([[p[0], p[1] + 0.035, p[2] + 0.02] for p in pts], 0.03, 9806, ROPE_DARK))
    # streamers and straw tassels hanging from the rope
    for t in (0.2, 0.42, 0.62, 0.84):
        i = int(round(t * 12))
        x, y, z = pts[i]
        P += shide(x, y - 0.05, z + 0.06, 9810 + i, scale=1.2)
    for t in (0.31, 0.52, 0.73):
        i = int(round(t * 12))
        x, y, z = pts[i]
        for k in range(5):
            st = cyl((x + (k - 2) * 0.012, y - 0.04, z + 0.05), (x + (k - 2) * 0.016, y - 0.3 - 0.03 * (k % 2), z + 0.06), 0.008, ROPE, n=3)
            st.swaying((x, y, z), 0.5, mat='swaynl')
            P.append(st)
    # small offerings at the foot of the left stone: a pile of pebbles, a tiny sake cup
    for k in range(5):
        a = R.uniform(0, 2 * math.pi)
        P.append(K.lathe([(0.0, -0.025), (0.035, -0.015), (0.035, 0.012), (0.0, 0.025)], STONE * (0.9 + 0.2 * R.uniform()), n=6,
                         base=(xl + 0.32 + math.cos(a) * 0.08, 0.025 + 0.03 * (k > 2), 0.32 + math.sin(a) * 0.06)))
    P.append(K.lathe([(0.0, 0.0), (0.035, 0.0), (0.045, 0.035), (0.0, 0.035)], K.col('#e8e2d2'), n=7, base=(xl + 0.52, 0.0, 0.3)))
    prop = K.Prop('gate_stones', 9801).add(P)
    cat = {'footprint': [[xl, 0.0, 0.42], [xr, 0.0, 0.38]], 'tags': ['sacred', 'gate', 'landmark'],
           'notes': 'The main gate of the barrier: two old standing stones (1.7 and 1.45 m) 3.3 m apart, a thick rope slung between '
                    'them (lowest 0.95 m), four paper streamers and three straw tassels that swing; the path passes between.',
           'anchors': {'gate': [0.0, 0.0, 0.0], 'perch': [[xl, Hl + 0.05, 0.0], [xr, Hr + 0.05, 0.0]]}}
    return export_prop(out, 'gate_stones', 'props', prop, cat, porosity=0.5, far=False, budget=3600)


def chozubachi(out):
    R = rng(9821)
    P = []

    def basin(Q):
        b = K.sd_ellipsoid(Q - np.array([0, 0.3, 0]), (0.62, 0.36, 0.42))
        b = np.maximum(b, -Q[..., 1] - 0.05)
        bowl = K.sd_ellipsoid(Q - np.array([0, 0.62, 0.0]), (0.4, 0.24, 0.26))
        return K.smax(b, -bowl, 0.04) + K.weathered(Q, 0.03, 0.14, 9822)
    pc = K.sdf_piece(basin, (-0.75, -0.08, -0.5), (0.75, 0.7, 0.5), STONE_OLD, h=0.025, tris=700, pattern='stone', amount=1.0, var=0.07, seed=9822)
    P.append(pc)
    P.append(K.lathe([(0.0, 0.0), (0.36, 0.0), (0.36, 0.004), (0.0, 0.004)], WATER, n=12, base=(0, 0.56, 0), var=0.0, ao=False, dirt=False))
    # the spout: a bamboo pipe on a little stand behind, the water falling into the bowl
    P.append(_w(cyl((0.05, 0.95, -1.1), (0.0, 0.88, -0.22), 0.04, BAMBOO, n=6), 'plain', 0.0, 9823))
    for s in (-1, 1):
        P.append(_w(cyl((s * 0.07, -0.1, -0.7), (s * 0.02, 0.92, -0.7), 0.022, WOOD_DARK, n=4), 'bark', 0.3, 9824))
    P.append(K.cbox((PX, 0.3, PX), K.col('#d6e8ec'), centre=(0.0, 0.73, -0.2), bevel=0.0, var=0.0, ao=False, dirt=False))
    # ladles on a bamboo rest across the bowl
    P.append(_w(cyl((-0.42, 0.66, 0.12), (0.42, 0.66, 0.12), 0.012, BAMBOO * 1.05, n=4), 'plain', 0.0, 9825))
    for k, x in enumerate((-0.18, 0.05, 0.25)):
        P.append(_w(cyl((x, 0.67, 0.12), (x + 0.04, 0.7, -0.2), 0.008, BAMBOO * 1.1, n=3), 'plain', 0.0, 9826))
        P.append(K.lathe([(0.0, 0.0), (0.04, 0.0), (0.04, 0.05), (0.0, 0.05)], BAMBOO * 1.1, n=6, base=(x, 0.64, 0.17)))
    # stones and a lantern-less flat stone to stand on (前石)
    def flat(Q):
        return K.sd_box(Q - np.array([0, 0.06, 0]), (0.32, 0.06, 0.24), 0.05) + K.weathered(Q, 0.012, 0.08, 9827)
    P.append(K.sdf_piece(flat, (-0.4, -0.04, -0.3), (0.4, 0.16, 0.3), STONE, h=0.025, tris=120, pattern='stone', amount=0.6,
                         seed=9827).moved(None, (0.05, 0, 0.75)))
    prop = K.Prop('chozubachi', 9821).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.6]], 'tags': ['sacred', 'water', 'interact'],
           'notes': 'The water basin (手水鉢) before the shrine steps: a hollowed natural stone 1.2 m, a bamboo spout on a stand '
                    'behind (the water falls into the bowl), three ladles on a bamboo rest, a flat stone in front.',
           'anchors': {'interact': [0.05, 0.0, 0.95], 'water': [0.0, 0.56, 0.0], 'firefly': [[0.3, 0.7, 0.3], [-0.4, 0.5, 0.2]]}}
    return export_prop(out, 'chozubachi', 'props', prop, cat, porosity=0.5, far=False, budget=2400)


def ema_kake(out):
    R = rng(9841)
    P = []
    W_ = 1.3
    for x in (-W_ / 2, W_ / 2):
        P.append(_w(K.cbox((0.08, 1.45, 0.08), WOOD_DARK, centre=(x, 0.62, 0), bevel=0.01), 'bark', 0.3, 9842))
    for y in (0.75, 1.12):
        P.append(_w(K.beam((-W_ / 2 - 0.06, y, 0.05), (W_ / 2 + 0.06, y, 0.05), 0.04, 0.05, WOOD_DARK), 'planks', 0.2, 9843))
    # a little gable roof of boards
    for s in (-1, 1):
        P.append(_w(K.convex([(-W_ / 2 - 0.18, 1.42, 0.0), (W_ / 2 + 0.18, 1.42, 0.0), (-W_ / 2 - 0.18, 1.3, s * 0.32),
                              (W_ / 2 + 0.18, 1.3, s * 0.32), (-W_ / 2 - 0.18, 1.39, 0.0), (W_ / 2 + 0.18, 1.39, 0.0),
                              (-W_ / 2 - 0.18, 1.27, s * 0.32), (W_ / 2 + 0.18, 1.27, s * 0.32)], WOOD * 0.85), 'planks', 0.3, 9844))
    # the plaques: pentagons of pale wood, a few new, most weathered; each hangs from its cord
    for row, y in enumerate((0.72, 1.09)):
        n = 7 if row == 0 else 6
        for k in range(n):
            x = -W_ / 2 + 0.12 + (k + R.uniform(0.1, 0.9)) * (W_ - 0.24) / n
            c = K.col('#d8c49a') * (0.75 + 0.3 * R.uniform())
            w, h = 0.14, 0.1
            z = 0.075 + 0.006 * k
            pent = [(x - w / 2, y - 0.03 - h, z), (x + w / 2, y - 0.03 - h, z), (x + w / 2, y - 0.03 - h * 0.35, z), (x, y - 0.025, z),
                    (x - w / 2, y - 0.03 - h * 0.35, z)]
            pts = pent + [(p[0], p[1], p[2] + 0.01) for p in pent]
            pc = K.convex(pts, c, pattern='planks', amount=0.2, var=0.03)
            pc.swaying((x, y, z), 0.15)
            P.append(pc)
            if R.uniform() < 0.6:
                mk = K.cbox((0.05, 0.03, 0.004), RED if R.uniform() < 0.5 else K.col('#2a2a2a'), centre=(x, y - 0.03 - h * 0.6, z + 0.012),
                            bevel=0.0, var=0.0)
                mk.swaying((x, y, z), 0.15)
                P.append(mk)
    prop = K.Prop('ema_kake', 9841).add(P)
    return export_prop(out, 'ema_kake', 'props', prop, {'footprint': [[0.0, 0.0, 0.4]], 'tags': ['sacred', 'interact'],
                                                       'notes': 'A small roofed rack (1.3 m) with thirteen votive plaques (絵馬) on two rails.',
                                                       'anchors': {'interact': [0.0, 0.0, 0.6]}},
                       porosity=0.8, far=False, budget=1600)


def massha(out):
    R = rng(9861)
    P = []

    def base(Q):
        return K.sd_box(Q - np.array([0, 0.18, 0]), (0.36, 0.18, 0.3), 0.06) + K.weathered(Q, 0.02, 0.12, 9862)
    P.append(K.sdf_piece(base, (-0.45, -0.05, -0.38), (0.45, 0.4, 0.38), STONE_OLD, h=0.025, tris=200, pattern='stone', amount=1.0, seed=9862))
    P.append(_w(K.cbox((0.42, 0.34, 0.32), WOOD * 0.9, centre=(0, 0.55, -0.02), bevel=0.01), 'planks', 0.4, 9863))
    P.append(K.cbox((0.26, 0.24, 0.02), K.col('#2b2521'), centre=(0, 0.53, 0.145), bevel=0.0, var=0.0))
    for k in range(3):
        P.append(K.cbox((0.012, 0.24, 0.015), WOOD * 0.85, centre=(-0.08 + k * 0.08, 0.53, 0.155), bevel=0.0))
    for s in (-1, 1):
        P.append(_w(K.convex([(-0.32, 0.92, 0.0), (0.32, 0.92, 0.0), (-0.32, 0.72, s * 0.3), (0.32, 0.72, s * 0.3),
                              (-0.32, 0.88, 0.0), (0.32, 0.88, 0.0), (-0.32, 0.69, s * 0.3), (0.32, 0.69, s * 0.3)], K.col('#655b50')),
                    'tiles', 0.3, 9864))
    P.append(rope([[-0.2, 0.74, 0.17], [0.0, 0.7, 0.18], [0.2, 0.74, 0.17]], 0.018, 9865))
    for x in (-0.1, 0.1):
        P += shide(x, 0.71, 0.19, 9866 + int(x * 10), scale=0.6)
    P.append(K.lathe([(0.0, 0.0), (0.025, 0.0), (0.032, 0.035), (0.0, 0.035)], K.col('#e8e2d2'), n=6, base=(0.12, 0.36, 0.22)))
    P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.08), (0.02, 0.1), (0.0, 0.1)], K.col('#e8e2d2'), n=6, base=(-0.12, 0.36, 0.2)))
    prop = K.Prop('massha', 9861).add(P)
    return export_prop(out, 'massha', 'props', prop, {'footprint': [[0.0, 0.0, 0.42]], 'tags': ['sacred', 'interact'],
                                                     'notes': 'A little side shrine (末社, 0.95 m) on a stone, its rope and two streamers, '
                                                              'a sake cup and a flask.', 'anchors': {'interact': [0.0, 0.0, 0.7]}},
                       porosity=0.7, far=False, budget=1400)


def iwakura(out):
    R = rng(9881)
    P = []

    def rock(Q):
        q = Q - np.array([0, 0.75, 0])
        d = K.sd_ellipsoid(q, (1.35, 0.95, 1.0))
        d = d + K.weathered(Q, 0.09, 0.45, 9882) + (fbm3(Q[..., 0] * 0.9, Q[..., 1] * 0.9, Q[..., 2] * 0.9, 3, 9883) - 0.5) * 0.25
        return np.maximum(d, -Q[..., 1] - 0.25)
    pc = K.sdf_piece(rock, (-1.7, -0.3, -1.35), (1.7, 1.95, 1.35), STONE_OLD * 0.95, h=0.05, tris=1400, pattern='stone', amount=1.0,
                     var=0.08, seed=9882)

    def mossy(Pp, N):
        m = np.ones((len(Pp), 3))
        up = (N[:, 1] > 0.3) & (fbm3(Pp[:, 0] * 1.6, Pp[:, 1] * 1.6, Pp[:, 2] * 1.6, 2, 9884) > 0.42)
        m[up] = np.array([0.6, 0.76, 0.48])
        return m
    pc.shade = mossy
    P.append(pc)
    # the rope round its girth: follow the rock's outline at 0.9 m (sampled outward from the centre)
    from scipy.optimize import brentq
    ring = []
    for a in np.linspace(0, 2 * math.pi, 19):
        d = np.array([math.cos(a), 0.0, math.sin(a)])

        def f(r):
            return float(rock(np.array([[d[0] * r, 0.95, d[2] * r]]))[0])
        try:
            r = brentq(f, 0.2, 2.2)
        except ValueError:
            r = 1.2
        ring.append([d[0] * (r + 0.05), 0.95 + 0.04 * math.sin(3 * a), d[2] * (r + 0.05)])
    P.append(rope(ring, 0.055, 9885))
    for a in (0.95, 1.35, 1.75, 2.15):
        i = int(round(a / (2 * math.pi) * 18))
        x, y, z = ring[i]
        P += shide(x, y - 0.05, z + 0.05, 9886 + i, scale=1.1)
    prop = K.Prop('iwakura', 9881).add(P)
    return export_prop(out, 'iwakura', 'props', prop, {'footprint': [[0.0, 0.0, 1.25]], 'tags': ['sacred', 'landmark'],
                                                      'notes': 'A great rock held sacred (磐座), 2.7 x 1.9 m, mossy on top, a rope round its '
                                                               'girth with four streamers.',
                                                      'anchors': {'perch': [[0.0, 1.85, 0.0]]}},
                       porosity=0.5, far=False, budget=3000)


def jizo(out):
    R = rng(9901)
    P = []

    def body(Q):
        b = K.sd_capsule(Q, (0.0, 0.22, 0.0), (0.0, 0.42, 0.0), 0.13)
        h = K.sd_ellipsoid(Q - np.array([0, 0.58, 0.0]), (0.095, 0.1, 0.09))
        return K.smin(b, h, 0.03) + K.weathered(Q, 0.008, 0.05, 9902)
    P.append(K.sdf_piece(body, (-0.2, 0.05, -0.18), (0.2, 0.72, 0.18), STONE * 1.02, h=0.012, tris=420, pattern='stone', amount=0.6,
                         var=0.05, seed=9902))

    def base(Q):
        return K.sd_box(Q - np.array([0, 0.07, 0]), (0.2, 0.07, 0.17), 0.03) + K.weathered(Q, 0.01, 0.06, 9903)
    P.append(K.sdf_piece(base, (-0.25, -0.03, -0.22), (0.25, 0.16, 0.22), STONE_OLD, h=0.02, tris=90, pattern='stone', amount=0.8, seed=9903))
    # the red bib (よだれかけ) and the knitted red cap
    P.append(K.convex([(-0.12, 0.47, 0.11), (0.12, 0.47, 0.11), (0.0, 0.32, 0.15), (-0.12, 0.47, 0.13), (0.12, 0.47, 0.13),
                       (0.0, 0.32, 0.165)], RED, pattern='plain', amount=0.0))
    P.append(K.lathe([(0.0, 0.0), (0.1, 0.0), (0.09, 0.05), (0.05, 0.09), (0.0, 0.1)], RED * 0.95, n=8, base=(0, 0.62, 0.0)))
    # a flower in a bamboo cup, a pebble offering
    P.append(_w(cyl((0.17, 0.0, 0.18), (0.17, 0.14, 0.18), 0.025, BAMBOO, n=6), 'plain', 0.0, 9904))
    P.append(_w(cyl((0.17, 0.14, 0.18), (0.18, 0.27, 0.2), 0.006, K.col('#4a6a34'), n=3), 'plain', 0.0, 9905))
    P.append(K.lathe([(0.0, -0.02), (0.03, 0.0), (0.0, 0.02)], K.col('#e8c640'), n=6, base=(0.18, 0.28, 0.2)))
    prop = K.Prop('jizo', 9901).add(P)
    return export_prop(out, 'jizo', 'props', prop, {'footprint': [[0.0, 0.0, 0.25]], 'tags': ['sacred', 'interact'],
                                                   'notes': 'A roadside Jizo (0.7 m) with a red bib and cap on a little stone base, a flower '
                                                            'in a bamboo cup.', 'anchors': {'interact': [0.0, 0.0, 0.5]}},
                       porosity=0.6, far=False, budget=1200)


def sekimori(out):
    P = []

    def st(Q):
        return K.sd_ellipsoid(Q - np.array([0, 0.1, 0]), (0.14, 0.11, 0.13)) + K.weathered(Q, 0.006, 0.05, 9921)
    P.append(K.sdf_piece(st, (-0.18, -0.03, -0.17), (0.18, 0.24, 0.17), STONE, h=0.012, tris=200, pattern='stone', amount=0.3, seed=9921))
    black = K.col('#2a2420')
    for a in (0.0, math.pi / 2):
        ring = [[math.cos(t) * 0.0 + math.cos(a) * math.sin(t) * 0.15, 0.1 + math.cos(t) * 0.12, math.sin(a) * math.sin(t) * 0.14 * 1.0]
                for t in np.linspace(-math.pi / 2 - 0.2, math.pi / 2 + 0.2, 9)]
        P.append(K.rod(ring, 0.012, black, n=4, cap=True, step=0.03))
    P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.0, 0.035)], black, n=6, base=(0, 0.22, 0)))
    for s in (-1, 1):
        P.append(K.rod([[0.0, 0.25, 0.0], [s * 0.05, 0.26, 0.02], [s * 0.07, 0.24, 0.04]], 0.01, black, n=3, cap=True, step=0.03))
    prop = K.Prop('sekimori', 9920).add(P)
    return export_prop(out, 'sekimori', 'props', prop, {'footprint': [], 'tags': ['sacred', 'gate'],
                                                       'notes': 'A boundary stone (関守石): a round stone tied with a black cross of rope, set '
                                                                'on a path: go no further.'},
                       porosity=0.5, far=False, budget=600)


def build(out):
    return {'gate_stones': gate_stones(out), 'chozubachi': chozubachi(out), 'ema_kake': ema_kake(out), 'massha': massha(out),
            'iwakura': iwakura(out), 'jizo': jizo(out), 'sekimori': sekimori(out)}
