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
  goban         (round 5, 烂柯, G5R3-11 5.2 A) a stone go board by the iwakura, a game left half played,
                moss grown over the stones and into the grid, one bowl tipped
  ono           (烂柯) an axe by the great camphor's root whose handle has rotted away to a stump: the
                rusted head, moss on the stump
  kumotsu_old   (烂柯) offerings from different times on the shrine's offering stone: a holed copper
                coin gone green, a brown glass medicine bottle, a rusted drop-candy tin, a fresh cup
  shoryouma     (Obon) the spirit horse and cow (精霊馬): a cucumber horse and an eggplant cow on
                legs of hemp stalk, on a lotus leaf before the graves
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


def rope(points, r, seed, colour=ROPE, step=0.08):
    """A twisted straw rope along points: the body, and a darker spiral of the twist."""
    pc = K.rod(points, r, colour, n=6, cap=True, step=step, var=0.05, seed=seed)
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
    """The east gate's posts: two old standing stones with nothing tied on them (lead 14:00: at the
    gates a michikiri rope, not a shimenawa; the shimenawa only marks what cannot be taken)."""
    R = rng(9801)
    P = []
    xl, xr = -1.65, 1.62
    Hl, Hr = 1.72, 1.45
    P.append(standing_stone(9802, Hl, 0.42, 0.36, lean=-0.05).moved(K.rot_y(0.2), (xl, 0.0, 0.0)))
    P.append(standing_stone(9803, Hr, 0.38, 0.34, lean=0.06).moved(K.rot_y(-0.3), (xr, 0.0, 0.02)))
    # small offerings at the foot of the left stone: a pile of pebbles, a tiny sake cup
    for k in range(5):
        a = R.uniform(0, 2 * math.pi)
        P.append(K.lathe([(0.0, -0.025), (0.035, -0.015), (0.035, 0.012), (0.0, 0.025)], STONE * (0.9 + 0.2 * R.uniform()), n=6,
                         base=(xl + 0.32 + math.cos(a) * 0.08, 0.025 + 0.03 * (k > 2), 0.32 + math.sin(a) * 0.06)))
    P.append(K.lathe([(0.0, 0.0), (0.035, 0.0), (0.045, 0.035), (0.0, 0.035)], K.col('#e8e2d2'), n=7, base=(xl + 0.52, 0.0, 0.3)))
    prop = K.Prop('gate_stones', 9801).add(P)
    cat = {'footprint': [[xl, 0.0, 0.42], [xr, 0.0, 0.38]], 'tags': ['sacred', 'gate', 'landmark'],
           'notes': 'The east gate of the barrier: two old standing stones (1.7 and 1.45 m) 3.3 m apart, the path passes between; '
                    'the michikiri rope (michikiri_e) hangs over them between two old cedars.',
           'anchors': {'gate': [0.0, 0.0, 0.0], 'perch': [[xl, Hl + 0.05, 0.0], [xr, Hr + 0.05, 0.0]]}}
    return export_prop(out, 'gate_stones', 'props', prop, cat, porosity=0.5, far=False, budget=2000)


def waraji(seed, L=1.9, W=0.82):
    """大わらじ: a straw sandal bigger than a person, hung by its toe (y up = toe): a woven sole of
    straw cords with rows across, the toe loop, the side loops and the long tying cords."""
    R = rng(seed)
    T = 0.14
    straw = K.col('#b29e66')

    def sole(Q):
        q = Q - np.array([0.0, -L / 2, 0.0])
        # a little narrower at the heel (bottom) than at the ball, rounded ends
        w = W / 2 * (0.86 + 0.14 * np.clip((q[..., 1] + L / 2) / L, 0, 1))
        d = K.sd_box(np.stack([q[..., 0] * (W / 2) / np.maximum(w, 1e-3), q[..., 1], q[..., 2]], -1), (W / 2, L / 2, T / 2), r=0.11)
        return d + (fbm3(Q[..., 0] * 9, Q[..., 1] * 9, Q[..., 2] * 9, 2, seed) - 0.5) * 0.012
    pc = K.sdf_piece(sole, (-W / 2 - 0.03, -L - 0.03, -T / 2 - 0.03), (W / 2 + 0.03, 0.03, T / 2 + 0.03), straw * 0.86, h=0.03, tris=360,
                     pattern='plain', amount=0.0, var=0.05, seed=seed + 1)

    def weave(P_, N_):
        # rows of straw across the sole (every 7 cm, a darker groove between), four warp cords along
        rows = np.mod(P_[:, 1], 0.07) / 0.07
        m = np.where(rows < 0.22, 0.78, 1.0 + 0.06 * np.sin(rows * 6.0))
        warp = np.zeros(len(P_))
        for x in (-0.27, -0.09, 0.09, 0.27):
            warp = np.maximum(warp, np.clip(1.0 - np.abs(P_[:, 0] - x * W / 0.82) / 0.025, 0, 1))
        m = m * (1.0 - 0.12 * warp)
        return np.repeat(m[:, None], 3, axis=1)
    pc.shade = weave
    P = [pc]
    rope_c = K.col('#9c8752')
    # the weft as real ribs across the sole's face (the toon light draws each one lit on top, dark
    # underneath: woven straw reads at 30 px per metre; vertex shading could not)
    y = -0.1
    k = 0
    while y > -L + 0.08:
        t = (-y) / L
        hw = W / 2 * (0.86 + 0.14 * (1 - t)) - 0.04
        rib = K.rod([[-hw, y, T / 2 + 0.004], [0.0, y - 0.006, T / 2 + 0.02], [hw, y, T / 2 + 0.004]], 0.024,
                    straw * (0.92 if k % 2 else 1.04), n=4, cap=False, step=0.3, var=0.04, seed=seed + 30 + k)
        rib.pattern, rib.amount = K.PAT['thatch'], 0.2
        P.append(rib)
        y -= 0.1
        k += 1
    # the toe loop (前緒) at the top and the side loops (乳), the tying cords hanging loose
    P.append(rope([[0.0, -0.05, T / 2 + 0.02], [-0.07, -0.18, T / 2 + 0.07], [0.0, -0.3, T / 2 + 0.05], [0.07, -0.18, T / 2 + 0.07],
                   [0.0, -0.05, T / 2 + 0.02]], 0.03, seed + 2, rope_c))
    for sgn in (-1, 1):
        for y in (-0.5, -0.95):
            x0 = sgn * (W / 2 - 0.02)
            P.append(rope([[x0, y + 0.1, 0.0], [x0 + sgn * 0.16, y, 0.05], [x0, y - 0.1, 0.0]], 0.032, seed + 3, rope_c))
        # the long tying cords hang loose past the heel
        P.append(rope([[sgn * (W / 2 + 0.1), -0.5, 0.06], [sgn * (W / 2 + 0.2), -1.0, 0.12], [sgn * (W / 2 + 0.12), -1.6, 0.1],
                       [sgn * (W / 2 - 0.02), -2.15, 0.08]], 0.03, seed + 4, rope_c))
    return P


def _michikiri(name, seed, span, h_end, sag, r_rope, tassels, sandal, tree_r):
    """道切り: a thick straw rope tied round two trees on either side of the way, across it at h_end
    metres, sagging by `sag`; straw tassels hang along it; on the east gate a giant sandal in the
    middle (its own node 'Waraji': the dressing turns it slowly in the wind)."""
    R = rng(seed)
    P = []
    x0, x1 = -span / 2, span / 2
    for (x, rr) in ((x0, tree_r[0]), (x1, tree_r[1])):
        for k in range(2):
            y = h_end + 0.1 - k * 0.12
            ring = [[x + math.cos(a) * (rr + r_rope), y + 0.03 * math.sin(3 * a), math.sin(a) * (rr + r_rope) * 0.95]
                    for a in np.linspace(0, 2 * math.pi, 15)]
            P.append(rope(ring, r_rope * 0.8, seed + 2 + k, step=0.14))
    pts = []
    n = 25
    for i in range(n):
        t = i / (n - 1)
        x = x0 + tree_r[0] * 0.9 + (x1 - tree_r[1] * 0.9 - x0 - tree_r[0] * 0.9) * t
        y = h_end - sag * math.sin(math.pi * t) - 0.04 * math.sin(3 * math.pi * t)
        pts.append([x, y, 0.06 * math.sin(math.pi * t)])
    P.append(rope(pts, r_rope, seed + 5, step=0.16))
    P.append(rope([[q[0], q[1] + r_rope * 0.55, q[2] + r_rope * 0.35] for q in pts], r_rope * 0.42, seed + 6, ROPE_DARK, step=0.2))
    # straw tassels (房) hanging along the rope, swinging
    for t in tassels:
        i = int(round(t * (n - 1)))
        x, y, z = pts[i]
        L_ = R.uniform(0.35, 0.55)
        for k in range(6):
            st = cyl((x + (k - 2.5) * 0.014, y - r_rope * 0.6, z + 0.02), (x + (k - 2.5) * 0.02, y - r_rope - L_ - 0.04 * (k % 2), z + 0.03),
                     0.009, ROPE, n=3)
            st.swaying((x, y, z), 0.55, mat='swaynl')
            P.append(st)
        P.append(cyl((x, y - r_rope * 0.4, z), (x, y - r_rope - 0.08, z), 0.03, ROPE_DARK, n=5))
    extras = None
    mid = pts[n // 2]
    if sandal:
        # the hanging cord, and the sandal under it by its toe, sole to the camera
        hang = 0.32
        P.append(rope([[mid[0], mid[1] - r_rope * 0.5, mid[2]], [mid[0], mid[1] - hang, mid[2] + 0.02]], 0.028, seed + 7, ROPE_DARK))
        # the node stands at the ground under the rope (its origin's height is what the renderer leans
        # an upright object from); the sandal hangs in it at the rope's height, turning about the cord
        top = (0.0, float(mid[1] - hang), 0.0)
        wp = K.Prop('waraji', seed + 20).add([pc.moved(None, top) for pc in waraji(seed + 21)])
        extras = {'Waraji': (wp, (float(mid[0]), 0.0, float(mid[2] + 0.02)))}
    return P, extras, mid


def michikiri_e(out):
    P, extras, mid = _michikiri('michikiri_e', 9901, 8.4, 4.6, 0.5, 0.075, (0.14, 0.27, 0.37, 0.63, 0.73, 0.86), True, (0.6, 0.6))
    prop = K.Prop('michikiri_e', 9901).add(P)
    cat = {'footprint': [], 'tags': ['sacred', 'gate', 'landmark'],
           'notes': 'The east gate\'s michikiri (道切り): a thick straw rope 8.4 m long tied round two old cedars at x = -4.2 and '
                    '4.2 (4.6 m up; the trees stand on the same level ground as the rope\'s origin), across the way, sagging to 4.1 m; straw tassels along it; a giant straw sandal (大わらじ, '
                    '1.9 m) hangs from the middle by its toe: node "Waraji", turned slowly by the dressing (dressing.gd).',
           'anchors': {'waraji': [round(float(mid[0]), 3), round(float(mid[1] - 0.32), 3), round(float(mid[2]), 3)],
                       'perch': [[-2.2, 4.42, 0.05], [2.2, 4.42, 0.05]]}}
    return export_prop(out, 'michikiri_e', 'props', prop, cat, porosity=0.8, far=False, budget=5000, extras=extras)


def michikiri_n(out):
    P, extras, mid = _michikiri('michikiri_n', 9931, 4.6, 3.7, 0.32, 0.05, (0.25, 0.5, 0.75), False, (0.62, 0.62))
    prop = K.Prop('michikiri_n', 9931).add(P)
    cat = {'footprint': [], 'tags': ['sacred', 'gate'],
           'notes': 'A thinner michikiri rope for the north and south-west gates: 4.6 m between two trees at x = -2.3 and 2.3 '
                    '(3.7 m up), three straw tassels, no sandal.',
           'anchors': {'perch': [[0.0, 3.4, 0.03]]}}
    return export_prop(out, 'michikiri_n', 'props', prop, cat, porosity=0.8, far=False, budget=2500)


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


def hiraishi(out):
    """A flat stone by the graves (she lays her towel on it): 0.75 x 0.5 m, its top worn flat, moss
    round its foot."""
    def f(Q):
        d = K.sd_box(Q - np.array([0.0, 0.08, 0.0]), (0.37, 0.1, 0.25), r=0.06)
        return d + K.weathered(Q, 0.012, 0.08, 9961)
    pc = K.sdf_piece(f, (-0.42, -0.04, -0.3), (0.42, 0.22, 0.3), STONE_OLD, h=0.025, tris=160, pattern='stone', amount=0.55,
                     var=0.05, seed=9962)
    prop = K.Prop('hiraishi', 9961).add([pc])
    cat = {'footprint': [[0.0, 0.0, 0.3]], 'tags': ['interact', 'life'],
           'notes': 'A flat stone by the graves, 0.75 x 0.5 m, top at 0.18 m: where she lays her towel.',
           'anchors': {'interact': [0.0, 0.0, 0.5], 'top': [0.0, 0.18, 0.0]}}
    return export_prop(out, 'hiraishi', 'props', prop, cat, porosity=0.5, far=False, budget=400)


def shoikago(out):
    """A bamboo back basket (背負い籠) leaning back against something behind it (-z): woven split
    bamboo in a diagonal plait, a bamboo rim, two straw shoulder straps on its back; a folded indigo
    cloth in it."""
    R = rng(9971)
    H = 0.72
    prof = [(0.0, 0.0), (0.16, 0.0), (0.2, 0.06), (0.25, H * 0.55), (0.27, H), (0.24, H), (0.22, H * 0.55), (0.15, 0.04), (0.0, 0.04)]
    body = K.lathe(prof, K.col('#b59c64'), n=14, smooth=False)

    def plait(P_, N_):
        th = np.arctan2(P_[:, 0], P_[:, 2])
        u = th * 0.25
        a = np.floor((u + P_[:, 1]) / 0.045) + np.floor((u - P_[:, 1]) / 0.045)
        m = np.where(np.mod(a, 2) == 0, 1.0, 0.82)
        return np.repeat(m[:, None], 3, axis=1)
    body.shade = plait
    P = [body]
    P.append(K.lathe([(0.255, H - 0.025), (0.285, H - 0.01), (0.285, H + 0.02), (0.255, H + 0.03)], K.col('#9c8a58'), n=14,
                     cap_top=False, cap_bottom=False))
    for sx in (-0.11, 0.11):
        P.append(rope([[sx, H - 0.05, -0.25], [sx * 1.3, H * 0.6, -0.36], [sx * 1.2, 0.18, -0.3], [sx, 0.12, -0.2]], 0.018, 9972 + int(sx > 0)))
    P.append(K.cbox((0.3, 0.08, 0.22), K.col('#2f3d5c'), centre=(0.0, H - 0.02, 0.02), bevel=0.02, R=K.rot_x(0.2)))
    Rl = K.rot_x(-0.17)
    P = [pc.moved(Rl, (0.0, 0.0, 0.0)) for pc in P]
    prop = K.Prop('shoikago', 9971).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.3]], 'tags': ['life', 'interact'],
           'notes': 'A bamboo back basket 0.72 m tall leaning back 10 degrees (against the camphor\'s root, under the '
                    'shimenawa: it keeps its colour the next morning, being under the rope).'}
    return export_prop(out, 'shoikago', 'props', prop, cat, porosity=0.8, far=True, budget=1200)


def radio(out):
    """A wooden radio hung on a nail on an engawa post: varnished case with a rounded top, a cloth
    speaker grille behind three slats, a dial window with its needle, two knobs; the cord over the
    nail. Origin: the nail on the post's face (place it with 'hang' at the nail's height)."""
    P = []
    case = K.col('#7e5232')
    W_, H_, D_ = 0.36, 0.25, 0.14
    cy = -0.06 - H_ / 2
    P.append(K.cbox((W_, H_, D_), case, centre=(0.0, cy, D_ / 2 + 0.005), bevel=0.025, pattern='planks', amount=0.15))
    P.append(K.cbox((0.17, 0.15, 0.006), K.col('#cbb690'), centre=(-0.07, cy + 0.01, D_ + 0.008), bevel=0.0))
    for k in range(3):
        P.append(K.cbox((0.012, 0.15, 0.008), case * 0.8, centre=(-0.12 + k * 0.05, cy + 0.01, D_ + 0.012), bevel=0.0))
    P.append(K.cbox((0.11, 0.05, 0.006), K.col('#e9dfc2'), centre=(0.1, cy + 0.05, D_ + 0.008), bevel=0.0))
    P.append(K.cbox((0.004, 0.04, 0.004), K.col('#b03022'), centre=(0.09, cy + 0.05, D_ + 0.012), bevel=0.0))
    for x in (0.07, 0.13):
        P.append(K.cprism(8, 0.02, 0.018, 0.02, K.col('#2e2420'), base=(x, cy - 0.05, D_ + 0.005), bevel=0.0, R=K.rot_x(math.pi / 2)))
    P.append(rope([[-0.14, cy + H_ / 2, 0.05], [0.0, 0.0, 0.01], [0.14, cy + H_ / 2, 0.05]], 0.006, 9981, K.col('#3a3028')))
    P.append(K.cprism(5, 0.008, 0.008, 0.04, K.col('#55504a'), base=(0.0, 0.0, -0.01), bevel=0.0, R=K.rot_x(math.pi / 2)))
    prop = K.Prop('radio', 9981).add(P)
    cat = {'footprint': [], 'tags': ['life', 'interact', 'sound'],
           'notes': 'A wooden radio (case 0.36 x 0.25 x 0.14 m) hung on a nail: origin = the nail; the case hangs 0.06-0.31 m below '
                    'it, its back against the post (+z is its front).',
           'anchors': {'sound': [0.0, -0.18, 0.15], 'interact': [0.0, -1.2, 0.6]}}
    return export_prop(out, 'radio', 'props', prop, cat, porosity=0.4, far=True, budget=600, ground=False)


def goban(out):
    """A go board cut in stone (碁盤石) on a low rock, 0.46 m square: grid lines worn into it, a game
    half played (black and white stones on one corner and side), moss in the grid and over some
    stones; two bowls, one tipped over and its stones spilled in the moss."""
    R = rng(9971)
    P = []

    def base(Q):
        d = K.sd_box(Q - np.array([0.0, 0.1, 0.0]), (0.3, 0.13, 0.27), r=0.08)
        return d + K.weathered(Q, 0.03, 0.18, 9972)
    P.append(K.sdf_piece(base, (-0.42, -0.05, -0.38), (0.42, 0.26, 0.38), STONE_OLD * 0.92, h=0.03, tris=260, pattern='stone',
                         amount=0.8, var=0.06, seed=9972))
    top = 0.25
    board = K.cbox((0.46, 0.09, 0.46), STONE * 1.05, centre=(0.0, top + 0.045, 0.0), bevel=0.012, var=0.05, seed=9973,
                   pattern='stone', amount=0.35)

    def grid(Pp, N):
        m = np.ones((len(Pp), 3))
        on_top = N[:, 1] > 0.8
        gx = np.abs(((Pp[:, 0] + 0.2) / 0.066) - np.round((Pp[:, 0] + 0.2) / 0.066)) < 0.12
        gz = np.abs(((Pp[:, 2] + 0.2) / 0.066) - np.round((Pp[:, 2] + 0.2) / 0.066)) < 0.12
        m[on_top & (gx | gz)] = np.array([0.62, 0.62, 0.6])
        moss = on_top & (fbm3(Pp[:, 0] * 9, Pp[:, 1] * 9, Pp[:, 2] * 9, 2, 9974) > 0.55)
        m[moss] = np.array([0.6, 0.74, 0.46])
        return m
    board.shade = grid
    P.append(board)
    # the game: stones on the grid points of one corner and one side
    pts = [(i, j) for i in range(7) for j in range(7)]
    R.shuffle(pts)
    black, white = K.col('#2a2a2c'), K.col('#e4e2da')
    moss = K.col('#6e8a4a')
    for k, (i, j) in enumerate(pts[:19]):
        if i > 4 and j > 4:
            continue
        x, z = -0.2 + i * 0.066, -0.2 + j * 0.066
        c = black if k % 2 else white
        if R.uniform() < 0.35:
            c = moss * R.uniform(0.9, 1.1)
        P.append(K.lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.008), (0.0, 0.014)], c, n=6, base=(x, top + 0.09, z), var=0.0, dirt=False))
    # the bowls: one upright, one tipped over with its stones spilled
    P.append(K.lathe([(0.0, 0.0), (0.07, 0.0), (0.085, 0.05), (0.07, 0.09), (0.0, 0.09)], K.col('#5a4232'), n=10, base=(0.42, 0.0, 0.18),
                     pattern='planks', amount=0.2, var=0.05, seed=9975))
    P.append(K.lathe([(0.0, 0.0), (0.07, 0.0), (0.085, 0.05), (0.07, 0.09), (0.0, 0.09)], K.col('#4e3a2c'), n=10,
                     R=K.rot_z(1.4), base=(-0.44, 0.07, 0.22), pattern='planks', amount=0.2, var=0.05, seed=9976))
    for k in range(7):
        c = white if k % 3 else black
        P.append(K.lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.008), (0.0, 0.014)], c * (0.85 if R.uniform() < 0.5 else 1.0), n=6,
                         base=(-0.55 - R.uniform(0, 0.2), 0.0, 0.25 + R.normal(0, 0.08)), var=0.0, dirt=False))
    prop = K.Prop('goban', 9971).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.36]], 'tags': ['sacred', 'interact', 'ranka'],
           'notes': '烂柯: a stone go board on a low rock by the iwakura, a game left half played, moss in the grid and over some '
                    'stones, a bowl tipped over. 0.46 m square, top at 0.34 m.',
           'anchors': {'interact': [0.0, 0.0, 0.55], 'perch': [[0.0, 0.36, 0.0]]}}
    return export_prop(out, 'goban', 'props', prop, cat, porosity=0.5, far=False, budget=1800)


def ono(out):
    """An axe left by the great camphor's root long ago: the handle rotted away to a stump in the iron,
    the head rusted dark, lying in the moss against the root."""
    R = rng(9981)
    P = []
    iron = K.col('#5a4234')
    head = K.cbox((0.2, 0.025, 0.08), iron, centre=(0.0, 0.03, 0.0), bevel=0.006, R=K.rot_y(0.5) @ K.rot_z(0.25), var=0.12, seed=9982,
                  pattern='stone', amount=0.4)
    P.append(head)
    blade = K.cbox((0.06, 0.02, 0.14), iron * 0.9, centre=(0.1, 0.032, 0.05), bevel=0.004, R=K.rot_y(0.5) @ K.rot_z(0.25), var=0.1, seed=9983)
    P.append(blade)
    stump = cyl((-0.06, 0.03, -0.02), (-0.2, 0.06, -0.12), 0.022, K.col('#4e4232'), n=5)
    P.append(_w(stump, 'bark', 0.8, 9984))
    P.append(K.lathe([(0.0, 0.0), (0.08, 0.0), (0.0, 0.03)], K.col('#6a8648'), n=7, base=(-0.12, 0.0, -0.06), var=0.08, dirt=False))
    prop = K.Prop('ono', 9981).add(P)
    cat = {'footprint': [], 'tags': ['sacred', 'interact', 'ranka'],
           'notes': '烂柯: an axe whose handle has rotted away to a stump, the head rusted, in the moss by the camphor\'s root.',
           'anchors': {'interact': [0.0, 0.0, 0.35]}}
    return export_prop(out, 'ono', 'props', prop, cat, porosity=0.5, far=False, budget=400)


def kumotsu_old(out):
    """Offerings from different times on a flat stone before the shrine: a holed copper coin gone
    green (穴銭), a brown glass medicine bottle, a rusted drop-candy tin, and a fresh cup of water
    with a sprig of sakaki (hers, this morning). No dates anywhere."""
    R = rng(9991)
    P = []

    def slab(Q):
        d = K.sd_box(Q - np.array([0.0, 0.06, 0.0]), (0.3, 0.07, 0.18), r=0.04)
        return d + K.weathered(Q, 0.01, 0.08, 9992)
    P.append(K.sdf_piece(slab, (-0.36, -0.03, -0.24), (0.36, 0.16, 0.24), STONE_OLD, h=0.02, tris=180, pattern='stone', amount=0.6,
                         var=0.05, seed=9992))
    y = 0.13
    P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.006), (0.0, 0.006)], K.col('#4a7a62'), n=8, base=(-0.2, y, 0.04), var=0.05, dirt=False))
    P.append(K.lathe([(0.0, 0.0), (0.028, 0.0), (0.03, 0.06), (0.012, 0.085), (0.012, 0.11), (0.0, 0.11)], K.col('#6a4026'), n=8,
                     base=(-0.06, y, -0.05), var=0.02, dirt=False))
    P.append(K.cbox((0.07, 0.11, 0.045), K.col('#8a3a2a'), centre=(0.08, y + 0.055, -0.04), bevel=0.008, var=0.15, seed=9993,
                    pattern='stone', amount=0.3))
    P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.035, 0.05), (0.0, 0.05)], K.col('#e6e2d6'), n=8, base=(0.2, y, 0.05), var=0.0, dirt=False))
    P.append(K.cbox((0.012, 0.12, 0.012), K.col('#3a5a3a'), centre=(0.2, y + 0.1, 0.05), bevel=0.0, var=0.0))
    for k in range(3):
        P.append(K.cbox((0.035, 0.012, 0.02), K.col('#2f4a34'), centre=(0.2 + (k - 1) * 0.02, y + 0.14 + k * 0.012, 0.05),
                        bevel=0.0, R=K.rot_z((k - 1) * 0.6), var=0.0))
    prop = K.Prop('kumotsu_old', 9991).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.3]], 'tags': ['sacred', 'interact', 'ranka'],
           'notes': '烂柯: offerings from different times on a flat stone before the shrine: a holed copper coin gone green, a brown glass '
                    'medicine bottle, a rusted candy tin, and a fresh cup with a sakaki sprig.',
           'anchors': {'interact': [0.0, 0.0, 0.45]}}
    return export_prop(out, 'kumotsu_old', 'props', prop, cat, porosity=0.5, far=False, budget=900)


def shoryouma(out):
    """精霊馬 for Obon: a cucumber horse (the dead come home fast) and an eggplant cow (and go back
    slowly), on legs of hemp stalk, standing on a lotus leaf before the graves."""
    R = rng(9995)
    P = []
    leaf = K.lathe([(0.0, 0.0), (0.2, 0.004), (0.24, 0.02), (0.0, 0.012)], K.col('#4a7044'), n=12, base=(0.0, 0.0, 0.0), var=0.05,
                   seed=9996)
    P.append(leaf)
    ogara = K.col('#d8cfb2')
    for (x, colour, L_, r) in ((-0.08, K.col('#3e6a32'), 0.2, 0.024), (0.1, K.col('#3e2a48'), 0.13, 0.035)):
        body = K.cprism(7, r, r * 0.85, L_, colour, base=(x - L_ / 2, 0.075, 0.0), bevel=0.0, R=K.frame_to(np.array([1.0, 0.0, 0.0])))
        P.append(body)
        for dx in (-L_ * 0.35, L_ * 0.35):
            for dz in (-r * 0.6, r * 0.6):
                P.append(K.cbox((0.006, 0.07, 0.006), ogara, centre=(x + dx, 0.04, dz), bevel=0.0, var=0.0))
    prop = K.Prop('shoryouma', 9995).add(P)
    cat = {'footprint': [], 'tags': ['sacred', 'season'],
           'notes': '精霊馬 (Obon): a cucumber horse and an eggplant cow on hemp-stalk legs, on a lotus leaf.', 'anchors': {}}
    return export_prop(out, 'shoryouma', 'props', prop, cat, porosity=0.6, far=False, budget=400)


def build(out):
    return {'gate_stones': gate_stones(out), 'michikiri_e': michikiri_e(out), 'michikiri_n': michikiri_n(out),
            'chozubachi': chozubachi(out), 'ema_kake': ema_kake(out), 'massha': massha(out),
            'iwakura': iwakura(out), 'jizo': jizo(out), 'sekimori': sekimori(out), 'hiraishi': hiraishi(out),
            'shoikago': shoikago(out), 'radio': radio(out), 'goban': goban(out), 'ono': ono(out), 'kumotsu_old': kumotsu_old(out),
            'shoryouma': shoryouma(out)}
