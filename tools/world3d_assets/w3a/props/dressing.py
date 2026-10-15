"""Dressing of the home and the paths: woodpile (薪), stump with an axe, fallen branch, fences,
the bamboo water spout (筧) over a stone basin, baskets, straw bundles, signposts (no text).
Every scene has its faded (遠化) twin. Origins on the ground; fronts toward +z."""
from __future__ import annotations

import math

import numpy as np

from ..core import fbm3, rng
from . import kit as K
from .common import export_prop

WOOD = K.col('#7a6650')
WOOD_GREY = K.col('#857a6c')
LOG_END = K.col('#b9a079')
BARK = K.col('#5b4d40')
BAMBOO = K.col('#9c9a5e')
BAMBOO_OLD = K.col('#a89a66')
STONE = K.col('#8a867c')
STRAW = K.col('#c4ab6c')
WICKER = K.col('#a17a45')
WATER = K.col('#5d7f8c')
IRON = K.col('#4c4f52')


def cyl(p0, p1, r, colour, n=6, bevel=0.0, **kw):
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    return K.cprism(n, r, r, float(np.linalg.norm(d)), colour, base=p0, bevel=bevel, R=K.frame_to(d), **kw)


def _w(pc, pattern='bark', amount=0.3, seed=0):
    pc.pattern = K.PAT[pattern]
    pc.amount = amount
    pc.seed = seed
    return pc


def split_log(p0, p1, r, R, end=LOG_END, bark=BARK):
    """A split piece of firewood: a half or quarter round (bark on the round side, light wood on the
    cut faces), lying from p0 to p1."""
    k = int(R.integers(0, 3))
    angs = {0: np.linspace(0, math.pi, 5), 1: np.linspace(0, math.pi / 2, 4), 2: np.linspace(0, 2 * math.pi, 7)[:-1]}[k]
    pts2 = [(math.cos(a) * r, math.sin(a) * r) for a in angs]
    if k in (0, 1):
        pts2.append((0.0, 0.0))
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    Rm = K.frame_to(d)
    rot = R.uniform(0, 2 * math.pi)
    pts = []
    for (u, v) in pts2:
        a = math.cos(rot) * u - math.sin(rot) * v
        b = math.sin(rot) * u + math.cos(rot) * v
        for t in (0.0, 1.0):
            pts.append(p0 + Rm @ np.array([a, t * np.linalg.norm(d), b]))
    pc = K.convex(pts, end * (1 + R.normal(0, 0.05)), pattern='bark', amount=0.3, var=0.04, seed=int(R.integers(0, 1 << 20)))

    # bark on the faces that are not cut: those whose normal is not along the log and not a split face
    def shade(P, N, Rm=Rm, rot=rot):
        loc = N @ Rm
        along = np.abs(loc[:, 1]) > 0.8
        m = np.ones((len(P), 3))
        m[~along] = bark / end
        return m
    pc.shade = shade
    return pc


def woodpile(out):
    R = rng(8301)
    P = []
    L = 1.7
    # two pairs of stakes hold the ends; the stack between them on two sleepers
    for x in (-L / 2 - 0.05, L / 2 + 0.05):
        for z in (-0.22, 0.22):
            P.append(_w(cyl((x, -0.1, z), (x + R.normal(0, 0.02), 1.15, z), 0.035, WOOD_GREY, n=5), 'bark', 0.3, 8302))
    for z in (-0.18, 0.18):
        P.append(_w(K.beam((-L / 2, 0.05, z), (L / 2, 0.05, z), 0.08, 0.08, WOOD_GREY * 0.9), 'bark', 0.3, 8303))
    for row in range(6):
        y = 0.14 + row * 0.14
        n = 11 - (1 if row % 2 else 0)
        for k in range(n):
            x = -L / 2 + 0.08 + k * (L - 0.16) / 10 + (0.075 if row % 2 else 0) + R.normal(0, 0.008)
            r = 0.075 + R.normal(0, 0.008)
            ln = 0.42 + R.normal(0, 0.03)
            P.append(split_log((x, y, -ln / 2), (x, y + R.normal(0, 0.01), ln / 2), r, R))
    # a small board roof on top
    P.append(_w(K.cbox((L + 0.35, 0.04, 0.7), WOOD_GREY * 0.85, centre=(0, 1.2, 0.02), bevel=0.01, R=K.rot_x(0.12)),
                'planks', 0.4, 8304))
    prop = K.Prop('woodpile', 8301).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.95]], 'tags': ['interact', 'wood'],
           'notes': 'Stacked split firewood (薪) between stakes under a board, 1.7 m long; split ends face front and back.',
           'anchors': {'interact': [0.0, 0.0, 0.75], 'take': [0.0, 0.9, 0.25]}}
    return export_prop(out, 'woodpile', 'props', prop, cat, porosity=0.8, budget=2000)


def stump_axe(out):
    R = rng(8311)
    P = []

    def f(Q):
        r = 0.32 + 0.12 * np.exp(-np.maximum(Q[..., 1], 0) / 0.12)
        ang = np.arctan2(Q[..., 2], Q[..., 0])
        r = r + 0.05 * np.maximum(np.cos(5 * ang + 0.4), 0) * np.exp(-np.maximum(Q[..., 1], 0) / 0.1)
        side = np.hypot(Q[..., 0], Q[..., 2]) - r
        top = Q[..., 1] - (0.42 + 0.03 * Q[..., 0])
        return np.maximum(side, top) + K.weathered(Q, 0.01, 0.08, 8312)
    stump = K.sdf_piece(f, (-0.55, -0.1, -0.55), (0.55, 0.5, 0.55), BARK, h=0.025, tris=420, pattern='bark', amount=0.3,
                        var=0.06, seed=8312)

    def shade(Pp, N):
        m = np.ones((len(Pp), 3))
        top = N[:, 1] > 0.75
        rr = np.hypot(Pp[:, 0], Pp[:, 2])
        ring = (np.floor(rr / 0.05) % 2 == 0)
        m[top] = (LOG_END / BARK) * np.where(ring[top], 0.92, 1.0)[:, None]
        return m
    stump.shade = shade
    P.append(stump)
    # the axe: head bitten into the top, handle up at an angle
    head_c = np.array([0.04, 0.44, 0.02])
    P.append(_w(K.convex([head_c + v for v in ([-0.02, -0.03, -0.09], [0.02, -0.03, -0.09], [-0.02, 0.07, -0.07], [0.02, 0.07, -0.07],
                                              [-0.006, -0.05, 0.08], [0.006, -0.05, 0.08], [-0.006, 0.09, 0.08], [0.006, 0.09, 0.08])],
                         IRON), 'plain', 0.0, 8313))
    P.append(_w(cyl(head_c + np.array([0, 0.02, -0.06]), head_c + np.array([-0.3, 0.42, -0.36]), 0.02, K.col('#8a7250'), n=5),
                'bark', 0.2, 8314))
    # a few chips around
    for k in range(6):
        a = R.uniform(0, 2 * math.pi)
        rr = R.uniform(0.5, 0.8)
        P.append(K.cbox((0.06, 0.012, 0.03), LOG_END, centre=(math.cos(a) * rr, 0.006, math.sin(a) * rr), bevel=0.0,
                        R=K.rot_y(R.uniform(0, 3))))
    prop = K.Prop('stump_axe', 8311).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.42]], 'tags': ['interact'],
           'notes': 'A cut stump with an axe bitten into it, chips around (by the tree she may cut).',
           'anchors': {'interact': [0.0, 0.0, 0.8], 'axe': [-0.13, 0.65, -0.16]}}
    return export_prop(out, 'stump_axe', 'props', prop, cat, porosity=0.8, budget=1200)


def fallen_branch(out):
    R = rng(8321)
    P = []
    main = [np.array([-1.3, 0.1, 0.2]), np.array([-0.4, 0.12, 0.0]), np.array([0.5, 0.1, -0.15]), np.array([1.4, 0.07, -0.05])]
    P.append(_w(K.rod(main, 0.08, BARK, n=6, cap=True, step=0.25, radii=[0.09, 0.075, 0.055, 0.03]), 'bark', 0.4, 8322))
    for k in range(6):
        t = R.uniform(0.15, 0.9)
        i = int(t * 3)
        p0 = main[i] + (main[min(i + 1, 3)] - main[i]) * (t * 3 - i)
        d = np.array([R.normal(0.4, 0.3), R.uniform(0.05, 0.35), R.choice([-1, 1]) * R.uniform(0.3, 0.6)])
        p1 = p0 + d * R.uniform(0.4, 0.8)
        P.append(_w(K.rod([p0, (p0 + p1) / 2 + np.array([0, 0.05, 0]), p1], 0.02, BARK * 1.1, n=4, cap=True, step=0.2,
                          radii=[0.03, 0.02, 0.01]), 'bark', 0.3, 8323 + k))
    for k in range(10):                                       # a few brown leaves still on it
        p = main[1] + np.array([R.uniform(-0.8, 1.6), R.uniform(0.05, 0.3), R.uniform(-0.5, 0.5)])
        P.append(K.cbox((0.07, 0.01, 0.04), K.col('#8a6a40') * (1 + R.normal(0, 0.1)), centre=p, bevel=0.0,
                        R=K.rot_y(R.uniform(0, 3)) @ K.rot_x(R.uniform(-0.6, 0.6))))
    prop = K.Prop('fallen_branch', 8321).add(P)
    cat = {'footprint': [], 'tags': ['pickup', 'wood'],
           'notes': 'A fallen branch, 2.8 m, a few dead leaves on it.', 'anchors': {'take': [0.0, 0.1, 0.0]}}
    return export_prop(out, 'fallen_branch', 'props', prop, cat, porosity=0.8, budget=1200)


def fence(out, name, kind, seed):
    R = rng(seed)
    P = []
    L = 2.0
    if kind == 'bamboo':                                      # 四つ目垣: posts, three rails, upright canes
        for x in (-L / 2, L / 2):
            P.append(_w(cyl((x, -0.15, 0), (x, 1.05, 0), 0.04, WOOD_GREY, n=6), 'bark', 0.3, seed + 1))
        for y in (0.3, 0.62, 0.92):
            P.append(_w(cyl((-L / 2 - 0.08, y, 0.05), (L / 2 + 0.08, y + R.normal(0, 0.01), 0.05), 0.016, BAMBOO_OLD, n=4),
                        'plain', 0.0, seed + 2))
        for k in range(1, 10):
            x = -L / 2 + k * L / 10
            P.append(_w(cyl((x, -0.05, -0.02), (x, 0.98 + R.normal(0, 0.03), -0.02), 0.014, BAMBOO * (1 + R.normal(0, 0.05)), n=4),
                        'plain', 0.0, seed + 3))
        for k in range(1, 10):                                # black cord ties where they cross
            x = -L / 2 + k * L / 10
            for y in (0.3, 0.62, 0.92):
                P.append(K.cbox((0.035, 0.03, 0.04), K.col('#2c2622'), centre=(x, y, 0.02), bevel=0.0, var=0.0, ao=False))
    else:                                                     # old post and rail fence, one rail sagging
        for x in (-L / 2, L / 2):
            P.append(_w(K.cbox((0.11, 1.0, 0.11), WOOD_GREY, centre=(x, 0.4, 0), bevel=0.015, jitter=0.01, seed=seed),
                        'bark', 0.4, seed + 1))
        P.append(_w(K.beam((-L / 2 - 0.1, 0.78, 0.07), (L / 2 + 0.1, 0.8, 0.07), 0.05, 0.09, WOOD_GREY * 0.95), 'planks', 0.4, seed + 2))
        P.append(_w(K.beam((-L / 2 - 0.1, 0.42, 0.07), (L / 2 + 0.05, 0.2, 0.07), 0.05, 0.09, WOOD_GREY * 0.9), 'planks', 0.4, seed + 3))
    prop = K.Prop(name, seed).add(P)
    cat = {'footprint': [[-1.0, 0.0, 0.12], [0.0, 0.0, 0.12], [1.0, 0.0, 0.12]], 'tags': ['fence'],
           'notes': ('Bamboo lattice fence (四つ目垣), ' if kind == 'bamboo' else 'Old post-and-rail fence, ') + '2 m segment along x; '
                    'segments join end to end.'}
    return export_prop(out, name, 'props', prop, cat, porosity=0.8, budget=1600)


def kakehi(out):
    """筧: split bamboo pipes on forked stakes, falling into a stone basin with a ladle."""
    R = rng(8341)
    P = []
    # the basin (手水鉢): a rough block with a carved bowl, water in it
    def basin(Q):
        b = K.sd_box(Q - np.array([0, 0.28, 0]), (0.36, 0.28, 0.3), 0.06)
        bowl = K.sd_ellipsoid(Q - np.array([0, 0.56, 0]), (0.26, 0.16, 0.2))
        return K.smax(b, -bowl, 0.03) + K.weathered(Q, 0.015, 0.1, 8342)
    P.append(K.sdf_piece(basin, (-0.42, -0.05, -0.36), (0.42, 0.6, 0.36), STONE, h=0.02, tris=380, pattern='stone',
                         amount=0.8, var=0.06, seed=8342))
    P.append(K.lathe([(0.0, 0.0), (0.22, 0.0), (0.22, 0.004), (0.0, 0.004)], WATER, n=12, base=(0, 0.49, 0), var=0.0,
                     ao=False, dirt=False))
    # pipes from the back (the spring) to over the basin: two lengths on forked stakes
    pts = [np.array([0.0, 0.92, -2.4]), np.array([0.0, 0.85, -1.2]), np.array([0.0, 0.8, -0.12])]
    for a, b in ((pts[0], pts[1]), (pts[1], pts[2])):
        P.append(_w(cyl(a, b, 0.045, BAMBOO, n=6), 'plain', 0.0, 8343))
    for z in (-1.9, -0.75):
        y = 0.8 + 0.07 * (-z / 1.2)
        for s in (-1, 1):
            P.append(_w(cyl((s * 0.08, -0.1, z), (s * 0.03, y - 0.02, z), 0.022, WOOD_GREY, n=4), 'bark', 0.3, 8344))
    # the falling water: a thin bright string into the bowl
    P.append(K.cbox((0.025, 0.28, 0.025), K.col('#c8dde0'), centre=(0.0, 0.64, -0.08), bevel=0.0, var=0.0, ao=False, dirt=False))
    # the ladle on the basin's rim
    P.append(_w(cyl((0.2, 0.6, 0.12), (0.5, 0.64, 0.3), 0.012, BAMBOO_OLD, n=4), 'plain', 0.0, 8345))
    P.append(K.lathe([(0.0, 0.0), (0.05, 0.0), (0.05, 0.06), (0.0, 0.06)], BAMBOO_OLD, n=6, base=(0.17, 0.58, 0.1)))
    prop = K.Prop('kakehi', 8341).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.45]], 'tags': ['interact', 'water'],
           'notes': 'Bamboo water spout (筧) carrying the spring into a stone basin; the pipe starts 2.4 m behind (-z) at the spring.',
           'anchors': {'interact': [0.0, 0.0, 0.75], 'spout': [0.0, 0.8, -0.12], 'water': [0.0, 0.5, 0.0]}}
    return export_prop(out, 'kakehi', 'props', prop, cat, porosity=0.6, budget=1600)


def basket(out, name, kind, seed):
    R = rng(seed)
    P = []
    if kind == 'tall':                                        # 背負い籠: a tall carrying basket
        prof = [(0.0, 0.0), (0.16, 0.0), (0.2, 0.15), (0.25, 0.55), (0.27, 0.62), (0.25, 0.63), (0.23, 0.56), (0.0, 0.56)]
        h = 0.62
    else:                                                     # 笊: a wide flat basket with greens
        prof = [(0.0, 0.0), (0.2, 0.0), (0.3, 0.06), (0.33, 0.1), (0.31, 0.105), (0.27, 0.07), (0.0, 0.07)]
        h = 0.1

    def shade(Pp, N):
        a = np.arctan2(Pp[:, 2], Pp[:, 0])
        weave = ((np.floor(a / 0.25) + np.floor(Pp[:, 1] / 0.04)) % 2 == 0)
        m = np.ones((len(Pp), 3))
        m[weave] *= 0.86
        return m
    P.append(K.lathe(prof, WICKER, n=12, pattern='thatch', amount=0.2, var=0.05, seed=seed, shade=shade))
    if kind == 'tall':
        for x in (-0.1, 0.1):
            P.append(K.rod([[x, 0.5, -0.24], [x * 1.1, 0.3, -0.33], [x, 0.12, -0.2]], 0.014, K.col('#5a4636'), n=3, cap=True, step=0.06))
    else:
        for k in range(5):
            a = R.uniform(0, 2 * math.pi)
            rr = R.uniform(0, 0.18)
            P.append(K.lathe([(0.0, 0.0), (0.05, 0.01), (0.055, 0.04), (0.0, 0.06)], K.col('#6f8a46') * (1 + R.normal(0, 0.08)),
                             n=6, base=(math.cos(a) * rr, 0.07, math.sin(a) * rr)))
    prop = K.Prop(name, seed).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.3]], 'tags': ['pickup' if kind != 'tall' else 'interact'],
           'notes': 'Carrying basket (背負い籠), 0.62 m.' if kind == 'tall' else 'Flat basket (笊) with a few greens.'}
    return export_prop(out, name, 'props', prop, cat, porosity=0.8, budget=900)


def straw(out, name, kind, seed):
    R = rng(seed)
    P = []
    if kind == 'sheaf':                                       # 藁束: standing sheaves tied at the waist
        for k in range(3):
            x = -0.3 + k * 0.3 + R.normal(0, 0.03)
            z = R.normal(0, 0.05)
            prof = [(0.0, 0.0), (0.17, 0.0), (0.12, 0.14), (0.085, 0.36), (0.1, 0.46), (0.17, 0.66), (0.21, 0.8), (0.17, 0.9),
                    (0.08, 0.96), (0.0, 0.97)]
            pc = K.lathe(prof, K.col('#d2b878') * (1 + R.normal(0, 0.05)), n=9, pattern='bark', amount=0.3, var=0.05,
                         seed=seed + k)
            Rt = K.rot_z(R.normal(0, 0.12)) @ K.rot_x(R.normal(0, 0.08))
            P.append(pc.moved(Rt, (x, 0, z)))
            P.append(K.lathe([(0.088, 0.0), (0.095, 0.01), (0.095, 0.04), (0.088, 0.05)], K.col('#8a6a3a'), n=8,
                             cap_top=False, cap_bottom=False).moved(Rt, (x, 0.38, z)))
    else:                                                     # bundles lying in a small heap
        for k in range(5):
            a = R.uniform(-0.4, 0.4)
            c = np.array([R.uniform(-0.35, 0.35), 0.09 + (0.12 if k > 2 else 0.0), R.uniform(-0.2, 0.2)])
            pc = K.lathe([(0.0, -0.4), (0.09, -0.38), (0.07, 0.0), (0.09, 0.38), (0.0, 0.4)], STRAW * (1 + R.normal(0, 0.06)), n=7,
                         pattern='bark', amount=0.3, var=0.05, seed=seed + k)
            P.append(pc.moved(K.rot_y(a) @ K.rot_z(math.pi / 2), c))
    prop = K.Prop(name, seed).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.4]], 'tags': ['pickup'],
           'notes': 'Three standing straw sheaves (藁束).' if kind == 'sheaf' else 'Straw bundles lying in a heap.'}
    return export_prop(out, name, 'props', prop, cat, porosity=0.9, budget=900)


def signpost(out, name, kind, seed):
    R = rng(seed)
    P = []
    if kind == 'wood':                                        # a post with two blank arms pointing
        P.append(_w(K.cbox((0.12, 1.75, 0.12), WOOD_GREY, centre=(0, 0.75, 0), bevel=0.015, jitter=0.006, seed=seed), 'bark', 0.4, seed))
        P.append(_w(K.convex([(0.06, 1.42, -0.03), (0.62, 1.42, -0.03), (0.72, 1.5, -0.03), (0.62, 1.58, -0.03), (0.06, 1.58, -0.03),
                              (0.06, 1.42, 0.0), (0.62, 1.42, 0.0), (0.72, 1.5, 0.0), (0.62, 1.58, 0.0), (0.06, 1.58, 0.0)],
                             WOOD * 1.1), 'planks', 0.3, seed + 1).moved(K.rot_y(0.3), (0, 0, 0.04)))
        P.append(_w(K.convex([(-0.06, 1.2, 0.0), (-0.6, 1.2, 0.0), (-0.7, 1.28, 0.0), (-0.6, 1.36, 0.0), (-0.06, 1.36, 0.0),
                              (-0.06, 1.2, 0.03), (-0.6, 1.2, 0.03), (-0.7, 1.28, 0.03), (-0.6, 1.36, 0.03), (-0.06, 1.36, 0.03)],
                             WOOD * 1.05), 'planks', 0.3, seed + 2).moved(K.rot_y(-0.5), (0, 0, 0.05)))
        P.append(_w(K.convex([(-0.09, 1.62, -0.09), (0.09, 1.62, -0.09), (0.09, 1.62, 0.09), (-0.09, 1.62, 0.09), (0, 1.72, 0)],
                             WOOD_GREY * 0.9), 'planks', 0.3, seed + 3))
    else:                                                     # a stone waymark (道しるべ), blank, leaning
        def f(Q):
            return K.sd_box(Q - np.array([0, 0.45, 0]), (0.1, 0.5, 0.1), 0.025) + K.weathered(Q, 0.01, 0.07, seed)
        pc = K.sdf_piece(f, (-0.15, -0.1, -0.15), (0.15, 0.98, 0.15), STONE, h=0.02, tris=200, pattern='stone', amount=0.7,
                         var=0.06, seed=seed)
        P.append(pc.moved(K.rot_z(0.06) @ K.rot_x(-0.05), (0, 0, 0)))
        P.append(K.convex([(-0.1, 0.92, -0.1), (0.1, 0.92, -0.1), (0.1, 0.92, 0.1), (-0.1, 0.92, 0.1), (0.0, 1.0, 0.0)], STONE,
                          pattern='stone', amount=0.6).moved(K.rot_z(0.06) @ K.rot_x(-0.05), (0, 0, 0)))
    prop = K.Prop(name, seed).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.18]], 'tags': ['interact', 'sign'],
           'notes': ('Wooden signpost with two blank arms (no text).' if kind == 'wood' else 'Stone waymark (道しるべ), blank, leaning.')}
    return export_prop(out, name, 'props', prop, cat, porosity=0.7, budget=900)


def itabashi(out):
    """A plank bridge (板橋) over the stream where the way north crosses it: two log stringers 2.8 m
    long, grey planks across (one missing, one split), mossy log ends, a stake at each corner.
    Long axis along z; origin at the middle of the deck's underside at bank level (place with 'hang'
    so it sits on the banks over the stream bed)."""
    R = rng(8381)
    P = []
    L_, W_ = 3.6, 1.25
    for x in (-0.5, 0.5):
        pc = cyl((x, 0.0, -L_ / 2), (x + R.normal(0, 0.02), 0.01, L_ / 2), 0.13, BARK, n=7)
        pc.pattern, pc.amount, pc.seed = K.PAT['bark'], 0.6, int(R.integers(0, 1 << 20))
        P.append(pc)
        for z in (-L_ / 2, L_ / 2):
            P.append(K.cprism(7, 0.125, 0.125, 0.012, K.col('#a08a68'), base=(x, 0.0, z), bevel=0.0,
                              R=K.frame_to((0, 0, 1 if z > 0 else -1))))
    z = -L_ / 2 + 0.16
    k = 0
    while z < L_ / 2 - 0.1:
        w = R.uniform(0.2, 0.27)
        if k != 6:
            sh = R.uniform(0.82, 1.05)
            pc = K.cbox((W_ + R.uniform(-0.06, 0.06), 0.05, w - 0.025), WOOD_GREY * sh, centre=(R.normal(0, 0.03), 0.15, z + w / 2),
                        bevel=0.008, R=K.rot_y(R.normal(0, 0.03)), jitter=0.004, seed=int(R.integers(0, 1 << 20)))
            pc.pattern, pc.amount = K.PAT['planks'], 0.3
            P.append(pc)
        z += w
        k += 1
    for x in (-0.66, 0.66):
        for zz in (-L_ / 2 + 0.1, L_ / 2 - 0.1):
            P.append(cyl((x, -0.5, zz), (x + R.normal(0, 0.02), 0.32, zz), 0.045, WOOD, n=5))
    prop = K.Prop('itabashi', 8381).add(P)
    cat = {'footprint': [], 'tags': ['life', 'bridge'],
           'notes': 'A plank bridge 3.6 x 1.25 m over a small stream (long axis z); place with hang ~0.7 so the deck '
                    '(0.17 m over the origin) sits on the banks.',
           'anchors': {'perch': [[-0.66, 0.34, -1.3], [0.66, 0.34, 1.3]]}}
    return export_prop(out, 'itabashi', 'props', prop, cat, porosity=0.9, far=False, budget=1600)


def build(out):
    # round 4: the bamboo fence, baskets and straw are rebuilt in yard.py under new names, the signs
    # here are renamed (the assembly placed the round-3 names at fixed spots of the old layout)
    st = {}
    st['woodpile'] = woodpile(out)
    st['stump_axe'] = stump_axe(out)
    st['fallen_branch'] = fallen_branch(out)
    st['fence_rail'] = fence(out, 'fence_rail', 'rail', 8335)
    st['kakehi'] = kakehi(out)
    st['signpost_a'] = signpost(out, 'signpost_a', 'wood', 8371)
    st['waymark_a'] = signpost(out, 'waymark_a', 'stone', 8375)
    st['itabashi'] = itabashi(out)
    return st
