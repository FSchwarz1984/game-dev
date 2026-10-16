"""The yard and the garden of the home (round 4): the life of the house around it.

  monohoshi       laundry pole on two forked posts: an indigo kasuri yukata through its sleeves, two
                  tenugui folded over the pole, a small red cloth. Round 5 (G5R3-5: "一张非常单薄的贴图"):
                  every cloth is a draped surface, over the pole at the top, soft folds deepening
                  toward the hem, the hem a little uneven, a hem band of double thickness; it swings
                  with the wind in bands (mesh-mode foliage)
  kakehi_yard     split-bamboo pipes on forked stakes from the hill into a stone trough; beside it a
                  tub of spring water with cucumbers, tomatoes and a watermelon cooling in it
  mizugame        a big glazed water jar with a board lid and a ladle
  endai           a low bench (縁台) with a tray, cups and a fan
  nougu           tools leaning on the fence: a hoe, a winnowing basket (箕), a sickle on a nail
  fence_yotsume_a/b/c  bamboo lattice fence (四つ目垣), 2 m: morning glories / gourds / a few vines
  shiorido        the yard's brushwood gate (枝折戸), half open
  hatake          the vegetable garden: four ridges (cucumbers on a bamboo frame, eggplants, ground
                  cherries and green onions, young greens), stones along its edge
  kakashi         a scarecrow in an old kimono and a sedge hat
  neko            a calico cat asleep, curled up (on the engawa)
  kago_tall, zaru, wara_sheaves, wara_heap   baskets and straw (the round-3 ones under new names:
                  the assembly's fixed positions for the old names no longer apply)
  mushiro         a straw mat (筵) on the ground; round 5 (Obon): umeboshi drying on three round bamboo
                  sieves (土用干し) and a few red shiso leaves (the red peppers and azuki were autumn)
  wara_kuzu       loose straw bits scattered on the ground (before the engawa, by the straw heap)
  makiwari        the chopping block (薪割り台): a stump, a split log on it, wood chips all round
  houki           a bamboo broom (竹箒) leaning on a wall
  teoke           a small wooden bucket with a bamboo hoop
  niwatori_a/b    hens (地鶏): one standing and looking, one pecking at the ground; round 5: their other
                  poses (Up / Peck / Step / Look) as hidden nodes, moved by W3Life (dressing_life.gd)
  karasu          a jungle crow (ハシブトガラス) in six poses (stand; Peck, Caw, Hop, FlyA, FlyB hidden)
Origins on the ground; fronts toward +z (south, the camera)."""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import flora as FL
from .. import foliage as FO
from ..core import PX, fbm3, normalize, rng
from . import dressing as DR
from . import kit as K
from .common import export_prop

WOOD = K.col('#7a6650')
WOOD_GREY = K.col('#857a6c')
BAMBOO = K.col('#9c9a5e')
BAMBOO_OLD = K.col('#a89a66')
STONE = K.col('#8a867c')
WATER = K.col('#5a8290')
INDIGO = K.col('#2c3a5e')
WHITE_CLOTH = K.col('#e8e6dc')
EARTH = K.col('#5e4c3a')
EARTH_DARK = K.col('#4a3c2e')
STRAW = K.col('#b49a62')
IRON = K.col('#4c4f52')


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


def cloth(x0, x1, y_top, y_bot, z, colour, anchor, flex_top=0.25, flex_bot=0.8, strips=2, pattern='plain', stripes=None):
    """A hanging cloth in the x-y plane, cut into horizontal strips that swing more toward the hem."""
    P = []
    for k in range(strips):
        ya = y_top - (y_top - y_bot) * k / strips
        yb = y_top - (y_top - y_bot) * (k + 1) / strips
        f = flex_top + (flex_bot - flex_top) * (k + 0.5) / strips
        pc = K.cbox((x1 - x0, ya - yb + 0.004, 0.012), colour, centre=((x0 + x1) / 2, (ya + yb) / 2, z), bevel=0.0, var=0.02)
        pc.pattern, pc.amount = K.PAT[pattern], 0.1
        pc.swaying(anchor, f)
        P.append(pc)
        for (sy, sc) in (stripes or []):
            if yb <= sy <= ya:
                st = K.cbox((x1 - x0, 0.04, 0.004), sc, centre=((x0 + x1) / 2, sy, z + 0.008), bevel=0.0, var=0.0)
                st.swaying(anchor, f)
                P.append(st)
    return P


def drape(x0, x1, y_top, length, z, colour, anchor, R, flex=(0.15, 0.85), bands=3, folds=3, depth=0.035, sag=0.03,
          over=True, hem=None, specks=None, stripes=None, thick=0.006, seed=0):
    """A cloth hanging from a pole as a surface, not a board: it comes over the pole at the top (the
    pole's radius), falls in soft vertical folds that deepen toward the hem (pinned at the pole, free
    below), the hem uneven where the folds take up the cloth; front and back faces `thick` apart.
    Cut into `bands` from the top, each swinging with the wind a little more (whole-pixel sway).
    hem: (height, colour) a band of the hem; specks: (density, colour) small marks (kasuri);
    stripes: [(y, colour, h)] bands across."""
    P = []
    W = x1 - x0
    # (the folds run down the cloth: fine across, coarse along; 1.5 px across, 3 px down)
    nx = max(int(W / 0.045), 4)
    ny_total = max(int(length / 0.09), 3)
    lam = [W / max(folds, 1) * f for f in (1.0, 0.55, 0.32)]
    ph = [R.uniform(0, 2 * math.pi) for _ in lam]
    amp = [depth, depth * 0.45, depth * 0.2]
    xs = np.linspace(x0, x1, nx + 1)

    def hem_y(x):
        u = (x - x0) / W
        return -length + sag * math.sin(math.pi * u) * 0.0 + depth * 0.6 * math.cos(2 * math.pi * (x - x0) / lam[0] + ph[0])

    def surf(x, t):
        # t 0 at the pole .. 1 at the hem
        y = y_top + (hem_y(x) * t)
        k = t ** 0.75
        zz = sum(a * k * math.sin(2 * math.pi * (x - x0) / l + p_) for a, l, p_ in zip(amp, lam, ph))
        # the cloth bellies out a little toward the hem (the wind side)
        zz += 0.012 * t * t
        return np.array([x, y, z + zz])

    def colour_at(x, t, y):
        c = np.array(colour, np.float64)
        if hem is not None and y < y_top + hem_y(x) + hem[0]:
            c = np.array(hem[1], np.float64)
        for (sy, sc, sh) in (stripes or []):
            if abs(y - sy) < sh / 2:
                c = np.array(sc, np.float64)
        if specks is not None:
            hsh = math.sin(x * 917.3 + y * 413.7 + seed) * 43758.5453
            if hsh - math.floor(hsh) < specks[0]:
                c = np.array(specks[1], np.float64)
        return c
    for b in range(bands):
        t0, t1 = b / bands, (b + 1) / bands
        ny = max(int(ny_total / bands), 2)
        ts = np.linspace(t0, t1, ny + 1)
        V = np.array([[surf(x, t) for x in xs] for t in ts])            # (ny+1, nx+1, 3)
        # normals by finite differences
        dx = np.gradient(V, axis=1)
        dy = np.gradient(V, axis=0)
        N = np.cross(dy, dx)
        N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-9)
        N[N[..., 2] < 0] *= -1.0
        pts, nrm, cols, idx = [], [], [], []
        for side in (1, -1):
            base = len(pts)
            for j in range(ny + 1):
                for i in range(nx + 1):
                    pts.append(V[j, i] - np.array([0, 0, thick * (side < 0)]))
                    nrm.append(N[j, i] * side)
                    cols.append(colour_at(xs[i], ts[j], V[j, i][1]))
            for j in range(ny):
                for i in range(nx):
                    a_ = base + j * (nx + 1) + i
                    b_, c_, d_ = a_ + 1, a_ + nx + 1, a_ + nx + 2
                    if side > 0:
                        idx += [(a_, c_, b_), (b_, c_, d_)]
                    else:
                        idx += [(a_, b_, c_), (b_, d_, c_)]
        pc = K.Piece(np.array(pts), np.array(nrm), np.array(idx), np.array(colour, np.float64), pattern='plain', amount=0.0,
                     var=0.0, seed=seed + b)
        cols = np.array(cols)
        base_c = np.array(colour, np.float64)
        pc.shade = (lambda cc, bc: (lambda P_, N_: cc / np.maximum(bc, 1e-4)))(cols, base_c)
        pc.swaying(anchor, flex[0] + (flex[1] - flex[0]) * (b + 0.5) / bands)
        P.append(pc)
    if over:
        # over the pole: a half tube of the cloth's colour
        rr = 0.03
        pts, nrm, idx = [], [], []
        n_a = 4
        for i, x in enumerate(xs):
            for k in range(n_a + 1):
                a = math.pi * k / n_a
                d = np.array([0.0, math.sin(a), math.cos(a)])
                pts.append(np.array([x, y_top, z - rr]) + d * rr)
                nrm.append(d)
        for i in range(nx):
            for k in range(n_a):
                a_ = i * (n_a + 1) + k
                idx += [(a_, a_ + 1, a_ + n_a + 1), (a_ + 1, a_ + n_a + 2, a_ + n_a + 1)]
        pc = K.Piece(np.array(pts), np.array(nrm), np.array(idx), np.array(colour, np.float64) * 0.95, pattern='plain', amount=0.0, var=0.0)
        pc.swaying(anchor, flex[0])
        P.append(pc)
    return P


def forked_post(x, z, h, R, colour=WOOD_GREY):
    """A post cut from a forked branch: the trunk and two short tines holding a pole at h."""
    P = [_w(cyl((x, -0.25, z), (x + R.normal(0, 0.015), h - 0.08, z), 0.045, colour, n=6), 'bark', 0.4, int(R.integers(0, 1 << 20)))]
    for s in (-1, 1):
        P.append(_w(cyl((x, h - 0.1, z), (x + s * 0.09, h + 0.1, z + R.normal(0, 0.02)), 0.022, colour, n=4), 'bark', 0.3, 1))
    return P


# ------------------------------------------------------------------------------------------- laundry
def monohoshi(out):
    R = rng(9501)
    P = []
    span = 3.6
    hp = 1.92
    for x in (-span / 2, span / 2):
        P += forked_post(x, 0.0, hp, R)
    P.append(_w(cyl((-span / 2 - 0.25, hp, 0.0), (span / 2 + 0.25, hp + 0.02, 0.0), 0.022, BAMBOO_OLD, n=6), 'plain', 0.0, 9502))
    z = 0.03
    # the yukata through its sleeves: the sleeves along the pole, the body hanging below them
    kx = -0.75
    kas = (0.05, K.col('#c8ccd0'))
    P += drape(kx - 0.7, kx + 0.7, hp, 0.4, z, INDIGO, (kx, hp, z), R, flex=(0.12, 0.3), bands=1, folds=5, depth=0.02,
               specks=kas, seed=9503)
    P += drape(kx - 0.33, kx + 0.33, hp - 0.38, 0.95, z + 0.012, INDIGO * 1.04, (kx, hp, z), R, flex=(0.3, 0.9), bands=3, folds=3,
               depth=0.04, over=False, specks=kas, hem=(0.05, INDIGO * 0.8), seed=9504)
    # the obi over it, folded
    P += drape(kx - 0.32, kx + 0.32, hp - 0.4, 0.07, z + 0.03, K.col('#a83a2e'), (kx, hp, z), R, flex=(0.35, 0.35), bands=1, folds=2,
               depth=0.008, over=False, seed=9505)
    # two tenugui folded over the pole, a blue band at the hem
    for k, x in enumerate((0.45, 0.85)):
        P += drape(x - 0.16, x + 0.16, hp, 0.46 + 0.04 * k, z, WHITE_CLOTH * (1.0 - 0.03 * k), (x, hp, z), R, flex=(0.25, 0.9), bands=2,
                   folds=2, depth=0.022, hem=(0.06, K.col('#3a5a8a')), seed=9506 + k)
    # a small red cloth
    P += drape(1.25, 1.52, hp, 0.38, z, K.col('#b04034'), (1.38, hp, z), R, flex=(0.3, 1.0), bands=2, folds=2, depth=0.02, seed=9508)
    prop = K.Prop('monohoshi', 9501).add(P)
    cat = {'footprint': [[-span / 2, 0.0, 0.12], [span / 2, 0.0, 0.12]], 'tags': ['life'],
           'notes': 'Laundry pole on two forked posts (3.6 m), an indigo kasuri yukata through its sleeves with its obi, two tenugui, '
                    'a red cloth; each cloth drapes over the pole and falls in folds deepening toward the hem, and swings with the wind '
                    'in bands (foliage material, mesh mode).',
           'anchors': {'perch': [[-span / 2, hp + 0.12, 0.0], [span / 2, hp + 0.12, 0.0], [0.1, hp + 0.03, 0.0]]}}
    return export_prop(out, 'monohoshi', 'props', prop, cat, porosity=0.8, far=False, budget=4800)


# ------------------------------------------------------------------------------------------- water
def kakehi_yard(out):
    R = rng(9511)
    P = []

    def trough(Q):
        b = K.sd_box(Q - np.array([0, 0.22, 0]), (0.42, 0.22, 0.27), 0.05)
        bowl = K.sd_box(Q - np.array([0, 0.42, 0]), (0.34, 0.16, 0.19), 0.06)
        return K.smax(b, -bowl, 0.02) + K.weathered(Q, 0.015, 0.1, 9512)
    P.append(K.sdf_piece(trough, (-0.5, -0.05, -0.33), (0.5, 0.48, 0.33), STONE, h=0.02, tris=360, pattern='stone', amount=0.9,
                         var=0.06, seed=9512))
    P.append(K.cbox((0.66, 0.006, 0.36), WATER, centre=(0, 0.39, 0), bevel=0.0, var=0.0, ao=False, dirt=False))
    # the split bamboo from the hill (west, -x), on forked stakes, sloping down to the spout
    pts = [np.array([-3.4, 1.0, 0.05]), np.array([-1.8, 0.92, 0.04]), np.array([-0.2, 0.82, 0.0])]
    for a, b in zip(pts[:-1], pts[1:]):
        P.append(_w(cyl(a, b, 0.045, BAMBOO, n=6), 'plain', 0.0, 9513))
        P.append(_w(cyl(a + np.array([0, 0.035, 0]), b + np.array([0, 0.035, 0]), 0.03, WATER * 1.15, n=4), 'plain', 0.0, 9514))
    for x in (-2.6, -1.0):
        for s in (-1, 1):
            P.append(_w(cyl((x + s * 0.06, -0.15, 0.04), (x + s * 0.02, 0.86 + (-x) * 0.04, 0.04), 0.02, WOOD_GREY, n=4), 'bark', 0.3, 9515))
    # the falling water (a bright string) and its splash
    P.append(K.cbox((PX, 0.4, PX), K.col('#d6e8ec'), centre=(-0.16, 0.6, 0.0), bevel=0.0, var=0.0, ao=False, dirt=False))
    # the tub beside it, full of spring water: cucumbers, tomatoes, a watermelon
    tx = 0.78
    P.append(K.lathe([(0.0, 0.0), (0.3, 0.0), (0.33, 0.32), (0.31, 0.33), (0.28, 0.06), (0.0, 0.06)], K.col('#8a7458'), n=12,
                     base=(tx, 0, 0.08), pattern='planks', amount=0.3, var=0.05, seed=9516))
    for y in (0.07, 0.25):
        P.append(K.lathe([(0.3 + y * 0.09, y), (0.315 + y * 0.09, y + 0.005), (0.315 + y * 0.09, y + 0.035), (0.3 + y * 0.09, y + 0.04)],
                         K.col('#4a4038'), n=12, base=(tx, 0, 0.08), var=0.0, cap_top=False, cap_bottom=False))
    P.append(K.lathe([(0.0, 0.0), (0.29, 0.0), (0.29, 0.005), (0.0, 0.005)], WATER, n=12, base=(tx, 0.28, 0.08), var=0.0, ao=False))
    melon = K.lathe([(0.0, -0.13), (0.09, -0.11), (0.13, 0.0), (0.09, 0.11), (0.0, 0.13)], K.col('#3a6a34'), n=10,
                    base=(tx - 0.05, 0.31, 0.05), pattern='plain', amount=0.0)

    def stripes(Pp, N):
        a = np.arctan2(Pp[:, 2] - 0.05, Pp[:, 0] - (tx - 0.05))
        m = np.ones((len(Pp), 3))
        m[(np.floor(a / 0.45) % 2) == 0] = np.array([0.55, 0.62, 0.5])
        return m
    melon.shade = stripes
    P.append(melon)
    for k in range(3):
        a = 0.8 + k * 1.3
        P.append(K.cbox((0.2, 0.04, 0.045), K.col('#3e6a30'), centre=(tx + math.cos(a) * 0.17, 0.3, 0.08 + math.sin(a) * 0.15), bevel=0.01,
                        R=K.rot_y(a + 1.2)))
    for k in range(2):
        a = 2.5 + k * 1.6
        P.append(K.lathe([(0.0, -0.035), (0.04, -0.02), (0.04, 0.02), (0.0, 0.035)], K.col('#c0382a'), n=7,
                         base=(tx + math.cos(a) * 0.19, 0.3, 0.08 + math.sin(a) * 0.14)))
    # a ladle on the trough's rim
    P.append(_w(cyl((0.2, 0.47, 0.18), (0.55, 0.52, 0.35), 0.012, BAMBOO_OLD, n=4), 'plain', 0.0, 9517))
    P.append(K.lathe([(0.0, 0.0), (0.05, 0.0), (0.05, 0.06), (0.0, 0.06)], BAMBOO_OLD, n=6, base=(0.17, 0.45, 0.16)))
    prop = K.Prop('kakehi_yard', 9511).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.48], [tx, 0.08, 0.36]], 'tags': ['interact', 'water', 'life'],
           'notes': 'Split-bamboo pipes from the hill (3.4 m toward -x) into a stone trough; a tub of spring water beside it with a '
                    'watermelon, cucumbers and tomatoes cooling. Rotate so the pipe points uphill.',
           'anchors': {'interact': [0.0, 0.0, 0.7], 'spout': [-0.16, 0.8, 0.0], 'water': [0.0, 0.4, 0.0], 'firefly': [[0.0, 0.5, 0.2]]}}
    return export_prop(out, 'kakehi_yard', 'props', prop, cat, porosity=0.6, far=False, budget=2600)


def mizugame(out):
    P = [K.lathe([(0.0, 0.0), (0.22, 0.0), (0.33, 0.2), (0.36, 0.42), (0.3, 0.62), (0.24, 0.68), (0.26, 0.72), (0.0, 0.72)],
                 K.col('#3c302a'), n=12, pattern='plain', amount=0.0, var=0.04, seed=9521)]

    def glaze(Pp, N):
        m = np.ones((len(Pp), 3))
        m[Pp[:, 1] > 0.6] = np.array([1.6, 1.4, 1.1])        # the ash glaze runs lighter at the shoulder
        m[Pp[:, 1] < 0.12] = np.array([1.35, 1.2, 1.05])     # the unglazed foot
        return m
    P[0].shade = glaze
    for k in range(3):
        P.append(_w(K.cbox((0.56, 0.025, 0.17), WOOD * 1.05, centre=(0, 0.735, -0.17 + k * 0.17), bevel=0.006), 'planks', 0.3, 9522 + k))
    P.append(_w(K.cbox((0.07, 0.04, 0.4), WOOD * 0.8, centre=(0, 0.765, 0), bevel=0.005), 'planks', 0.2, 9525))
    P.append(_w(cyl((-0.1, 0.77, 0.12), (0.32, 0.86, 0.3), 0.011, BAMBOO_OLD, n=4), 'plain', 0.0, 9526))
    P.append(K.lathe([(0.0, 0.0), (0.045, 0.0), (0.045, 0.05), (0.0, 0.05)], BAMBOO_OLD, n=6, base=(-0.13, 0.75, 0.1)))
    prop = K.Prop('mizugame', 9521).add(P)
    return export_prop(out, 'mizugame', 'props', prop, {'footprint': [[0.0, 0.0, 0.38]], 'tags': ['interact', 'water'],
                                                       'notes': 'A big glazed water jar (水甕) with a board lid and a ladle.',
                                                       'anchors': {'interact': [0.0, 0.0, 0.6]}}, porosity=0.3, far=False, budget=900)


def endai(out):
    R = rng(9531)
    P = []
    L, D, H = 1.6, 0.48, 0.42
    for k in range(4):
        P.append(_w(K.cbox((L, 0.03, D / 4 - 0.008), WOOD * (1.0 + R.normal(0, 0.04)), centre=(0, H, -D / 2 + D / 8 + k * D / 4), bevel=0.005),
                    'planks', 0.4, 9532 + k))
    for x in (-L / 2 + 0.1, L / 2 - 0.1):
        P.append(_w(K.cbox((0.07, H - 0.03, D - 0.06), WOOD * 0.85, centre=(x, (H - 0.03) / 2, 0), bevel=0.01), 'planks', 0.3, 9536))
    P.append(_w(K.cbox((L - 0.25, 0.06, 0.04), WOOD * 0.8, centre=(0, 0.12, 0), bevel=0.0), 'planks', 0.2, 9537))
    # a tray with two cups, a fan
    P.append(_w(K.cbox((0.32, 0.02, 0.22), K.col('#5a3a26'), centre=(-0.35, H + 0.025, 0.02), bevel=0.005), 'planks', 0.2, 9538))
    for dx in (-0.42, -0.3):
        P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.034, 0.05), (0.0, 0.05)], K.col('#e0d8c4'), n=6, base=(dx, H + 0.035, 0.02)))
    P.append(K.lathe([(0.0, 0.0), (0.11, 0.0), (0.11, 0.008), (0.0, 0.008)], K.col('#e8e2d0'), n=10, base=(0.35, H + 0.016, 0.0)))
    P.append(K.cbox((0.11, 0.01, 0.025), K.col('#3a6a9a'), centre=(0.35, H + 0.024, 0.0), bevel=0.0))
    prop = K.Prop('endai', 9531).add(P)
    return export_prop(out, 'endai', 'props', prop, {'footprint': [[-0.4, 0.0, 0.3], [0.4, 0.0, 0.3]], 'tags': ['interact', 'life'],
                                                    'notes': 'A low bench (縁台) with a tray, two cups and a round fan.',
                                                    'anchors': {'sit': [0.0, H, 0.0], 'perch': [[0.7, H + 0.02, 0.0]]}},
                       porosity=0.8, far=False, budget=900)


def nougu(out):
    R = rng(9541)
    P = []
    # a hoe leaning back on the fence (the fence is behind, at z -0.1)
    P.append(_w(cyl((-0.3, 0.02, 0.18), (-0.18, 1.3, -0.08), 0.02, K.col('#8a7250'), n=5), 'bark', 0.2, 9542))
    P.append(K.convex([(-0.38, 0.0, 0.2), (-0.22, 0.0, 0.2), (-0.38, 0.0, 0.26), (-0.22, 0.0, 0.26),
                       (-0.36, 0.22, 0.17), (-0.24, 0.22, 0.17), (-0.36, 0.22, 0.2), (-0.24, 0.22, 0.2)], IRON))
    # a winnowing basket (箕) on its edge
    def mi(Q):
        q = Q - np.array([0.25, 0.32, 0.05])
        shell = np.abs(np.hypot(q[..., 0] / 0.32, (q[..., 1]) / 0.3) - 1.0) * 0.1 - 0.012
        return np.maximum(shell, np.maximum(q[..., 2] - 0.05, -q[..., 2] - 0.05))
    pc = K.sdf_piece(mi, (-0.1, -0.02, -0.06), (0.6, 0.66, 0.16), K.col('#a8884e'), h=0.02, tris=280, pattern='thatch', amount=0.3, seed=9543)
    P.append(pc.moved(K.rot_x(-0.25), (0, 0, 0)))
    # a sickle hanging on the fence rail
    P.append(_w(cyl((0.7, 0.62, -0.06), (0.72, 0.85, -0.06), 0.014, K.col('#8a7250'), n=4), 'bark', 0.2, 9544))
    P.append(K.cbox((0.16, 0.02, 0.01), IRON * 1.2, centre=(0.66, 0.86, -0.055), bevel=0.0, R=K.rot_z(0.4)))
    prop = K.Prop('nougu', 9541).add(P)
    return export_prop(out, 'nougu', 'props', prop, {'footprint': [[0.0, 0.1, 0.35]], 'tags': ['life'],
                                                    'notes': 'Farm tools leaning on a fence: a hoe, a winnowing basket, a sickle on the rail '
                                                             '(place against a fence, the fence 0.1 m behind).'},
                       porosity=0.8, far=False, budget=900)


# ------------------------------------------------------------------------------------------- fences, gate
def fence_yotsume(out, name, seed, vines='asagao'):
    R = rng(seed)
    P = []
    L = 2.0
    for x in (-L / 2, L / 2):
        P.append(_w(cyl((x, -0.15, 0), (x, 1.12, 0), 0.042, WOOD_GREY, n=6), 'bark', 0.35, seed + 1))
        P.append(K.lathe([(0.0, 0.0), (0.042, 0.0), (0.0, 0.03)], WOOD_GREY * 0.9, n=6, base=(x, 1.12, 0)))
    for y in (0.3, 0.62, 0.92):
        P.append(_w(cyl((-L / 2 - 0.08, y, 0.05), (L / 2 + 0.08, y + R.normal(0, 0.01), 0.05), 0.016, BAMBOO_OLD, n=4), 'plain', 0.0, seed + 2))
    for k in range(1, 10):
        x = -L / 2 + k * L / 10
        P.append(_w(cyl((x, -0.05, -0.02), (x, 0.98 + R.normal(0, 0.03), -0.02), 0.014, BAMBOO * (1 + R.normal(0, 0.05)), n=4), 'plain', 0.0,
                    seed + 3))
        for y in (0.3, 0.62, 0.92):
            P.append(K.cbox((0.035, 0.03, 0.04), K.col('#2c2622'), centre=(x, y, 0.02), bevel=0.0, var=0.0, ao=False))
    prop = K.Prop(name, seed).add(P)
    a = out.asset(name, 'props')
    cards_ = None
    if vines:
        specs = {'vine': [(FL.vine_leaves, dict(W=int(12 + 2 * (i % 3)), H=int(12 + 3 * (i % 2)), seed=seed + 40 + i,
                                                flowers=(2 + i % 2) if vines == 'asagao' else 0,
                                                fruit=(1 if (vines == 'gourd' and i % 2 == 0) else 0))) for i in range(5)]}
        atlas, rects, sets = FO.build_tiles(specs, width=128)
        tex = a.texture('vines', atlas)
        mat = a.material('vines', 'toon_foliage_noline.gdshader', params=FO.foliage_params(wind_px=1.0, cutaway=False),
                         textures={'leaf_tex': tex})
        cards = []
        n = {'asagao': 9, 'gourd': 8, 'few': 3}[vines]
        for k in range(n):
            t = sets['vine'][int(R.integers(0, 5))]
            x = R.uniform(-L / 2 + 0.15, L / 2 - 0.15)
            y = R.uniform(0.25, 1.05) if vines != 'few' else R.uniform(0.2, 0.6)
            cards.append(CD.Card(np.array([x, y, 0.09]), normalize(np.array([0.0, 0.5, 1.0])), t[1], t[2], t[0], 0.9,
                                 np.clip(np.array([1.0, 1.0, 1.0]) * (0.92 + 0.1 * R.uniform()), 0, 1), 0.4, 'plant', 1.0))
        md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
        cards_ = [(mat, md)]
    cat = {'footprint': [[-0.67, 0.0, 0.14], [0.0, 0.0, 0.14], [0.67, 0.0, 0.14]], 'tags': ['fence'],
           'notes': f'Bamboo lattice fence (四つ目垣), 2 m along x, with {vines or "no"} vines; segments join end to end.',
           'anchors': {'perch': [[-L / 2, 1.16, 0.0], [L / 2, 1.16, 0.0]]}}
    return export_prop(out, name, 'props', prop, cat, porosity=0.8, far=False, budget=2200, cards=cards_, asset=a)


def shiorido(out):
    R = rng(9551)
    P = []
    W_ = 1.0
    for x in (-W_ / 2 - 0.06, W_ / 2 + 0.06):
        P.append(_w(cyl((x, -0.2, 0), (x, 1.25, 0), 0.05, WOOD_GREY, n=6), 'bark', 0.35, 9552))
    # the gate leaf: a frame of bent bamboo with a lattice of split bamboo, swung 35 degrees open
    leaf = []
    leaf.append(_w(cyl((0, 0.1, 0), (0, 1.05, 0), 0.016, BAMBOO_OLD, n=4), 'plain', 0.0, 9553))
    leaf.append(_w(cyl((W_ - 0.04, 0.1, 0), (W_ - 0.04, 0.95, 0), 0.016, BAMBOO_OLD, n=4), 'plain', 0.0, 9553))
    arc = [np.array([0.0, 1.05, 0.0]), np.array([W_ * 0.3, 1.16, 0.0]), np.array([W_ * 0.7, 1.12, 0.0]), np.array([W_ - 0.04, 0.95, 0.0])]
    leaf.append(K.rod(arc, 0.016, BAMBOO_OLD, n=4, step=0.1))
    for k in range(-4, 5):
        a = np.array([max(0.0, k * 0.11), 0.12 + max(0.0, -k * 0.11), 0.0])
        b = a + np.array([0.75, 0.75, 0.0])
        b = np.minimum(b, [W_ - 0.05, 1.05, 0.0])
        if np.linalg.norm(b - a) > 0.1:
            leaf.append(cyl(a, b, 0.008, BAMBOO * 0.95, n=3))
    for k in range(-4, 5):
        a = np.array([W_ - 0.05 - max(0.0, k * 0.11), 0.12 + max(0.0, -k * 0.11), 0.01])
        b = a + np.array([-0.75, 0.75, 0.0])
        b = np.array([max(b[0], 0.0), min(b[1], 1.05), 0.01])
        if np.linalg.norm(b - a) > 0.1:
            leaf.append(cyl(a, b, 0.008, BAMBOO * 0.9, n=3))
    Rl = K.rot_y(-0.6)
    P += [p.moved(Rl, (-W_ / 2, 0, 0)) for p in leaf]
    prop = K.Prop('shiorido', 9551).add(P)
    cat = {'footprint': [[-W_ / 2 - 0.06, 0.0, 0.1], [W_ / 2 + 0.06, 0.0, 0.1]], 'tags': ['gate', 'sacred'],
           'notes': "The yard's brushwood gate (枝折戸), 1 m wide, the leaf swung open; between two posts (x +-0.56).",
           'anchors': {'perch': [[-W_ / 2 - 0.06, 1.28, 0.0], [W_ / 2 + 0.06, 1.28, 0.0]]}}
    return export_prop(out, 'shiorido', 'props', prop, cat, porosity=0.8, far=False, budget=1500)


# ------------------------------------------------------------------------------------------- the garden
def hatake(out):
    R = rng(9561)
    P = []
    W_, D = 6.2, 3.6
    rows = 4
    for k in range(rows):
        z = -D / 2 + (k + 0.5) * D / rows

        def ridge(Q, z=z, s=9562 + k):
            q = Q - np.array([0.0, 0.0, z])
            ax = np.clip(q[..., 0], -W_ / 2 + 0.3, W_ / 2 - 0.3)
            d = np.sqrt((q[..., 0] - ax) ** 2 + (q[..., 1] / 0.45) ** 2 + (q[..., 2] / 1.0) ** 2) - 0.3
            return d + (fbm3(Q[..., 0] * 4, Q[..., 1] * 4, Q[..., 2] * 4, 2, s) - 0.5) * 0.04
        pc = K.sdf_piece(ridge, (-W_ / 2 - 0.1, -0.15, z - 0.42), (W_ / 2 + 0.1, 0.2, z + 0.42), EARTH, h=0.05, tris=300,
                         pattern='plain', amount=0.0, var=0.08, seed=9562 + k)
        P.append(pc)
    # a few stones along the garden's front edge, a path of straw between
    for k in range(9):
        x = -W_ / 2 + 0.3 + k * (W_ - 0.6) / 8 + R.normal(0, 0.06)

        def st(Q, s=9570 + k):
            return K.sd_ellipsoid(Q, (0.14, 0.08, 0.11)) + K.weathered(Q, 0.01, 0.05, s)
        P.append(K.sdf_piece(st, (-0.18, -0.1, -0.15), (0.18, 0.1, 0.15), STONE * (0.85 + 0.2 * R.uniform()), h=0.03, tris=30,
                             pattern='stone', amount=0.6, seed=9570 + k).moved(K.rot_y(R.uniform(0, 3)), (x, 0.0, D / 2 + 0.15)))
    # the cucumber frame on the back ridge: bamboo A-frames and a ridge pole
    zc = -D / 2 + 0.45
    for x in np.linspace(-W_ / 2 + 0.5, W_ / 2 - 0.5, 5):
        for s in (-1, 1):
            P.append(_w(cyl((x, -0.1, zc + s * 0.32), (x, 1.5, zc), 0.014, BAMBOO_OLD, n=4), 'plain', 0.0, 9580))
    P.append(_w(cyl((-W_ / 2 + 0.4, 1.45, zc), (W_ / 2 - 0.4, 1.45, zc), 0.014, BAMBOO_OLD, n=4), 'plain', 0.0, 9581))
    P.append(_w(cyl((-W_ / 2 + 0.4, 0.75, zc + 0.16), (W_ / 2 - 0.4, 0.75, zc + 0.16), 0.01, BAMBOO_OLD, n=3), 'plain', 0.0, 9582))
    prop = K.Prop('hatake', 9561).add(P)
    a = out.asset('hatake', 'props')
    specs = {'cuke': [(FL.cucumber_vine, dict(W=int(14 + 2 * (i % 2)), H=int(16 + 2 * (i % 3)), seed=9590 + i)) for i in range(4)],
             'nasu': [(FL.eggplant, dict(W=14, H=int(14 + i), seed=9600 + i)) for i in range(3)],
             'hozuki': [(FL.hozuki, dict(W=12, H=int(14 + i), seed=9610 + i)) for i in range(2)],
             'negi': [(FL.negi, dict(W=10, H=12, seed=9620 + i)) for i in range(2)],
             'greens': [(FL.tuft, dict(W=8, H=6, seed=9630 + i, family='grass_yellow', tall=0.8, spread=0.8)) for i in range(3)]}
    atlas, rects, sets = FO.build_tiles(specs, width=128)
    tex = a.texture('plants', atlas)
    mat = a.material('plants', 'toon_foliage_noline.gdshader', params=FO.foliage_params(wind_px=1.0, cutaway=False), textures={'leaf_tex': tex})
    cards = []
    up = normalize(np.array([0.0, 1.0, 0.45]))
    for k in range(rows):
        z = -D / 2 + (k + 0.5) * D / rows
        kind = ['cuke', 'nasu', 'hozuki', 'greens'][k]
        n = {'cuke': 7, 'nasu': 6, 'hozuki': 7, 'greens': 12}[kind]
        for j in range(n):
            x = -W_ / 2 + 0.45 + (j + R.uniform(0.2, 0.8)) * (W_ - 0.9) / n
            if kind == 'hozuki' and j % 3 == 2:
                t = sets['negi'][int(R.integers(0, 2))]
            else:
                t = sets[kind][int(R.integers(0, len(sets[kind])))]
            y = 0.18 + t[2] / 30.0 * 0.5 + (0.5 if kind == 'cuke' else 0.0)
            cards.append(CD.Card(np.array([x, y, z + R.normal(0, 0.05)]), up, t[1], t[2], t[0], 0.9,
                                 np.clip(np.array([1.0, 1.0, 1.0]) * (0.93 + 0.1 * R.uniform()), 0, 1), 0.6, 'plant', 1.0))
            if kind == 'cuke':
                cards.append(CD.Card(np.array([x + 0.2, 0.25 + t[2] / 60.0, z + 0.1]), up, t[1], t[2], t[0], 0.85,
                                     np.array([0.95, 0.97, 0.95]), 0.6, 'plant', 1.0))
    md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    cat = {'footprint': [[-2.1, 0.0, 1.0], [0.0, 0.0, 1.0], [2.1, 0.0, 1.0], [-2.1, -1.2, 0.8], [0.0, -1.2, 0.8], [2.1, -1.2, 0.8]],
           'tags': ['garden', 'interact'],
           'notes': 'The vegetable garden (畑), 6.2 x 3.6 m: four ridges along x (from the back: cucumbers on a bamboo frame, eggplants, '
                    'ground cherries with green onions, young greens), stones along the front edge.',
           'anchors': {'interact': [0.0, 0.0, 2.2], 'perch': [[-2.6, 1.5, -1.35], [2.6, 1.5, -1.35]]}}
    return export_prop(out, 'hatake', 'props', prop, cat, porosity=0.9, far=False, budget=4200, cards=[(mat, md)], asset=a)


def kakashi(out):
    R = rng(9641)
    P = []
    P.append(_w(cyl((0, -0.3, 0), (0.02, 1.55, 0), 0.03, WOOD_GREY, n=5), 'bark', 0.3, 9642))
    P.append(_w(cyl((-0.62, 1.12, 0.02), (0.62, 1.15, 0.02), 0.022, WOOD_GREY, n=5), 'bark', 0.3, 9643))
    # the head: a cloth sack, the sedge hat on it
    P.append(K.lathe([(0.0, -0.13), (0.11, -0.1), (0.13, 0.0), (0.1, 0.1), (0.0, 0.13)], K.col('#d8d0bc'), n=8, base=(0.02, 1.42, 0.03)))
    P.append(K.lathe([(0.0, 0.0), (0.3, 0.0), (0.0, 0.17)], K.col('#b8a068'), n=10, base=(0.02, 1.5, 0.03), pattern='thatch', amount=0.3))
    P.append(K.cbox((0.07, 0.015, 0.01), K.col('#2a2420'), centre=(-0.02, 1.44, 0.15), bevel=0.0))
    P.append(K.cbox((0.07, 0.015, 0.01), K.col('#2a2420'), centre=(0.07, 1.44, 0.15), bevel=0.0))
    # the old kimono over the cross bar, patched, swinging
    kim = K.col('#5a6a7a')
    P += cloth(-0.6, 0.62, 1.2, 0.98, 0.06, kim, (0.0, 1.2, 0.06), 0.2, 0.35, 1)
    P += cloth(-0.25, 0.28, 1.0, 0.35, 0.065, kim * 0.95, (0.0, 1.2, 0.06), 0.4, 1.0, 3,
               stripes=[(0.7, K.col('#8a5a3a'))])
    P.append(K.cbox((0.14, 0.12, 0.004), K.col('#a8884e'), centre=(0.12, 0.58, 0.075), bevel=0.0).swaying((0.0, 1.2, 0.06), 0.8))
    prop = K.Prop('kakashi', 9641).add(P)
    return export_prop(out, 'kakashi', 'props', prop, {'footprint': [[0.0, 0.0, 0.15]], 'tags': ['life'],
                                                      'notes': 'A scarecrow (案山子) in an old patched kimono and a sedge hat.',
                                                      'anchors': {'perch': [[0.02, 1.68, 0.03], [0.6, 1.17, 0.02]]}},
                       porosity=0.8, far=False, budget=900)


# ------------------------------------------------------------------------------------------- the cat
def _cat_prop(pose='sleep'):
    """The calico cat, curled up asleep on the engawa. pose: 'sleep'; 'breath' (the body risen a
    pixel); 'tail' (the tip of the tail lifted and curled, a flick); 'awake' (the head up, ears up,
    eyes open, looking)."""
    hc = np.array([0.13, 0.1, 0.06]) if pose != 'awake' else np.array([0.15, 0.17, 0.08])
    ear_up = 0.0 if pose != 'awake' else 0.05
    rise = 0.03 if pose == 'breath' else 0.0

    def body(Q):
        b = K.sd_ellipsoid(Q - np.array([0.0, 0.085 + rise * 0.5, 0.0]), (0.2, 0.1 + rise * 0.5, 0.15))
        h = K.sd_ellipsoid(Q - hc, (0.075, 0.065, 0.07))
        e1 = K.sd_capsule(Q, hc + (-0.02, 0.05, -0.01), hc + (-0.025, 0.09 + ear_up * 0.3, -0.02), 0.018)
        e2 = K.sd_capsule(Q, hc + (0.04, 0.05, 0.0), hc + (0.055, 0.085 + ear_up * 0.3, -0.01), 0.018)
        tail = K.sd_capsule(Q, (-0.17, 0.05, 0.05), (-0.05, 0.035, 0.15), 0.028)
        if pose == 'tail':
            tail2 = np.minimum(K.sd_capsule(Q, (-0.05, 0.035, 0.15), (0.04, 0.06, 0.17), 0.024),
                               K.sd_capsule(Q, (0.04, 0.06, 0.17), (0.07, 0.12, 0.16), 0.02))
        else:
            tail2 = K.sd_capsule(Q, (-0.05, 0.035, 0.15), (0.09, 0.035, 0.15), 0.024)
        d = K.smin(b, h, 0.04)
        d = np.minimum(d, np.minimum(e1, e2))
        d = K.smin(d, np.minimum(tail, tail2), 0.02)
        return d
    pc = K.sdf_piece(body, (-0.26, -0.02, -0.2), (0.27, 0.3, 0.24), K.col('#ece6d8'), h=0.012, tris=560, pattern='plain', amount=0.0,
                     var=0.02, seed=9651)

    def calico(Pp, N):
        m = np.ones((len(Pp), 3))
        n1 = fbm3(Pp[:, 0] * 9, Pp[:, 1] * 9, Pp[:, 2] * 9, 2, 9652)
        n2 = fbm3(Pp[:, 0] * 8 + 3, Pp[:, 1] * 8, Pp[:, 2] * 8, 2, 9653)
        orange = (n1 > 0.58) & (Pp[:, 1] > 0.06)
        black = (n2 > 0.62) & (Pp[:, 1] > 0.08) & ~orange
        m[orange] = np.array([0.86, 0.58, 0.34]) / np.array([0.925, 0.9, 0.85])
        m[black] = np.array([0.2, 0.18, 0.17]) / np.array([0.925, 0.9, 0.85])
        # the face: closed eyes and the nose a dark line; awake, two dark eyes
        if pose == 'awake':
            face = (Pp[:, 0] > hc[0] + 0.04) & (Pp[:, 2] > hc[2] + 0.02) & (np.abs(Pp[:, 1] - (hc[1] + 0.012)) < 0.012)
        else:
            face = (Pp[:, 0] > 0.17) & (Pp[:, 2] > 0.09) & (np.abs(Pp[:, 1] - 0.11) < 0.008)
        m[face] = np.array([0.25, 0.22, 0.2]) / np.array([0.925, 0.9, 0.85])
        return m
    pc.shade = calico
    return K.Prop('neko_' + pose, 9651).add([pc])


def neko(out):
    """A calico cat asleep, curled up: body, head tucked to the right, tail around the front. Its
    other poses ride along as hidden nodes (Breath, Tail, Awake): W3Life (godot/world3d/
    dressing_life.gd) shows one at a time."""
    hide = {None: {'visible': False}}
    extras = {nm: (_cat_prop(pz), (0.0, 0.0, 0.0), hide) for nm, pz in (('Breath', 'breath'), ('Tail', 'tail'), ('Awake', 'awake'))}
    return export_prop(out, 'neko', 'props', _cat_prop('sleep'), {'footprint': [], 'tags': ['life', 'animal'],
                                                                 'poses': {'sleep': 'Mesh', 'breath': 'Breath', 'tail': 'Tail', 'awake': 'Awake'},
                                                                 'notes': 'A calico cat (三毛猫) asleep, curled up, 0.5 m long; place on the engawa. '
                                                                          'Poses (hidden nodes): Breath, Tail, Awake.'},
                       porosity=0.5, far=False, budget=2600, ground=False, extras=extras)


# ------------------------------------------------------------------------------------------- ground things
def _bit(c, length, width, height, ang, colour, tilt=0.0, **kw):
    """A small flat piece lying on the ground: centre c (x, z), long axis at angle ang (radians)."""
    R = K.rot_y(ang) @ K.rot_z(tilt)
    # tiny ground debris: no outline (a 1-2 px piece would be all outline), no baked dirt or AO
    kw.setdefault('mat', 'noline')
    kw.setdefault('ao', False)
    kw.setdefault('dirt', False)
    return K.cbox((length, height, width), colour, centre=(c[0], height * 0.5, c[1]), bevel=0.0, R=R, **kw)


def mushiro(out):
    """A straw mat (筵) spread on the ground, 1.8 x 0.9 m, its far end rolled a little; on it three round
    bamboo sieves of umeboshi drying in the sun (土用干し: the plums of June, three days and nights in
    the dog days, still out at Obon), a few red shiso leaves drying beside them."""
    R = rng(9731)
    P = []
    W_, D = 1.8, 0.9
    mat = K.col('#b7a06a')
    P.append(K.cbox((W_, 0.012, D), mat, centre=(0, 0.006, 0), bevel=0.0, pattern='thatch', amount=0.15, var=0.04, seed=9732))
    for k in range(int(W_ / 0.12) + 1):
        x = -W_ / 2 + 0.04 + k * 0.12
        if x > W_ / 2 - 0.02:
            break
        P.append(K.cbox((0.012, 0.004, D - 0.02), mat * 0.78, centre=(x, 0.0135, 0), bevel=0.0, var=0.0))
    for z in (-D / 2 + 0.015, D / 2 - 0.015):
        P.append(K.cbox((W_, 0.016, 0.03), mat * 0.86, centre=(0, 0.008, z), bevel=0.0, var=0.02))
    P.append(_w(cyl((W_ / 2 + 0.05, 0.05, -D / 2), (W_ / 2 + 0.05, 0.05, D / 2), 0.05, mat * 0.95, n=7), 'thatch', 0.2, 9733))
    sieve = K.col('#b9a874')
    ume = K.col('#9a3438')
    for k, (cx, cz, r) in enumerate(((-0.52, -0.08, 0.27), (0.08, 0.1, 0.28), (0.58, -0.12, 0.25))):
        # the sieve: a shallow woven dish with a bound rim
        P.append(K.lathe([(0.0, 0.0), (r * 0.8, 0.0), (r, 0.03), (r, 0.04), (r * 0.82, 0.012), (0.0, 0.012)], sieve, n=14,
                         base=(cx, 0.012, cz), pattern='thatch', amount=0.25, var=0.03, seed=9740 + k))
        P.append(K.lathe([(r - 0.012, 0.03), (r + 0.006, 0.03), (r + 0.006, 0.046), (r - 0.012, 0.046)], sieve * 0.82, n=14,
                         base=(cx, 0.012, cz), var=0.0, cap_top=False, cap_bottom=False))
        # the plums in loose rows, wrinkled, red to dark red, a little paler where the sun dried them most
        n = 0
        for row in range(-3, 4):
            zz = row * 0.062
            half = math.sqrt(max(r * r * 0.72 - zz * zz, 0.0))
            xx = -half + R.uniform(0.0, 0.03)
            while xx < half:
                c = ume * R.uniform(0.82, 1.15)
                # (a plum is 1-2 px: a small rounded block without an outline, no lathe)
                P.append(K.cbox((0.046, 0.024, 0.046), c, centre=(cx + xx + R.normal(0, 0.006), 0.034, cz + zz + R.normal(0, 0.006)),
                                bevel=0.0, R=K.rot_y(R.uniform(0, 1.5)), var=0.05, seed=int(R.integers(0, 1 << 20)),
                                mat='noline', ao=False, dirt=False))
                xx += R.uniform(0.055, 0.07)
                n += 1
    # red shiso leaves drying on the mat's corner
    shiso = K.col('#6a2a3c')
    for k in range(9):
        c = (R.uniform(-0.85, -0.6), R.uniform(0.18, 0.4))
        P.append(_bit(c, R.uniform(0.06, 0.09), 0.05, 0.004, R.uniform(0, 3), shiso * R.uniform(0.85, 1.15), var=0.03,
                      seed=int(R.integers(0, 1 << 20))))
    prop = K.Prop('mushiro', 9731).add(P)
    cat = {'footprint': [], 'tags': ['life', 'interact'],
           'notes': 'A straw mat (筵) 1.8 x 0.9 m lying flat, its +x end rolled; umeboshi drying on three round bamboo sieves '
                    '(土用干し), red shiso leaves on the -x corner. Walkable over (no footprint).',
           'anchors': {'perch': [[0.9, 0.1, 0.0]]}}
    return export_prop(out, 'mushiro', 'props', prop, cat, porosity=0.9, far=False, budget=3400)


def wara_kuzu(out):
    """Loose straw bits (藁屑) blown about on the ground: thin pale stalks lying every way, thicker at
    the middle of the patch (about 1.6 x 1.0 m), a few short ones apart."""
    R = rng(9741)
    P = []
    straw = K.col('#c9b27a')
    for k in range(78):
        r = abs(R.normal(0, 0.38))
        a = R.uniform(0, 2 * math.pi)
        c = (math.cos(a) * r * 1.5, math.sin(a) * r * 0.9)
        L_ = R.uniform(0.07, 0.24)
        P.append(_bit(c, L_, PX * 0.9, 0.012, R.uniform(0, math.pi), straw * R.uniform(0.78, 1.1), tilt=R.normal(0, 0.05),
                      var=0.03, seed=int(R.integers(0, 1 << 20))))
    prop = K.Prop('wara_kuzu', 9741).add(P)
    cat = {'footprint': [], 'tags': ['life'], 'notes': 'Loose straw bits on the ground, a patch about 1.6 x 1.0 m (no footprint).'}
    return export_prop(out, 'wara_kuzu', 'props', prop, cat, porosity=0.9, far=False, budget=1100)


def makiwari(out):
    """The chopping block: an old stump of a log (45 cm across) cut flat, deep axe marks, a split
    log standing on it; chips and split pieces all round on the ground, thickest in front."""
    R = rng(9751)
    P = []
    wood_end = K.col('#b89a6e')
    bark = K.col('#7c6550')

    def block(Q):
        d = K.sd_cyl(Q - np.array([0.0, 0.2, 0.0]), 0.23, 0.2)
        return d + K.weathered(Q, 0.012, 0.06, 9752)
    pc = K.sdf_piece(block, (-0.28, -0.02, -0.28), (0.28, 0.42, 0.28), bark, h=0.025, tris=220, pattern='bark', amount=0.3,
                     var=0.05, seed=9753)

    def ends(Pp, N):
        m = np.ones((len(Pp), 3))
        top = N[:, 1] > 0.7
        m[top] = wood_end / bark
        return m
    pc.shade = ends
    P.append(pc)
    for k in range(3):                      # axe cuts on the top: dark slits
        a = R.uniform(0, math.pi)
        P.append(K.cbox((0.2, 0.004, 0.012), K.col('#3c3024'), centre=(R.normal(0, 0.05), 0.405, R.normal(0, 0.05)), bevel=0.0,
                        R=K.rot_y(a)))
    # a split log standing on the block (half round, the split face toward the camera)
    def half(Q):
        q = Q - np.array([0.02, 0.62, 0.0])
        d = K.sd_cyl(q, 0.11, 0.21)
        return np.maximum(d, q[..., 2] - 0.02)
    hp = K.sdf_piece(half, (-0.12, 0.38, -0.13), (0.15, 0.86, 0.05), bark, h=0.02, tris=120, pattern='bark', amount=0.2, seed=9754)

    def split_face(Pp, N):
        m = np.ones((len(Pp), 3))
        m[(N[:, 2] > 0.6) | (N[:, 1] > 0.7)] = wood_end / bark
        return m
    hp.shade = split_face
    P.append(hp)
    # split pieces lying about, and chips
    for k in range(4):
        a = R.uniform(0, 2 * math.pi)
        r = R.uniform(0.38, 0.7)
        c = (math.cos(a) * r, math.sin(a) * r * 0.8 + 0.12)
        P.append(_bit(c, R.uniform(0.3, 0.42), 0.09, 0.07, R.uniform(0, math.pi), wood_end * R.uniform(0.85, 1.0), var=0.04,
                      seed=int(R.integers(0, 1 << 20))))
    chip = K.col('#c7ad84')
    for k in range(70):
        r = abs(R.normal(0, 0.45)) + 0.22
        a = R.uniform(0, 2 * math.pi)
        c = (math.cos(a) * r, math.sin(a) * r * 0.75 + (0.15 if math.sin(a) > 0 else 0.0))
        P.append(_bit(c, R.uniform(0.035, 0.09), R.uniform(0.02, 0.04), 0.012, R.uniform(0, math.pi), chip * R.uniform(0.75, 1.08),
                      tilt=R.normal(0, 0.15), var=0.03, seed=int(R.integers(0, 1 << 20))))
    prop = K.Prop('makiwari', 9751).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.3]], 'tags': ['life', 'interact'],
           'notes': 'The chopping block (薪割り台): a stump 45 cm across with axe cuts, a split log on it, split pieces and '
                    'wood chips around (thickest toward +z).',
           'anchors': {'perch': [[0.0, 0.86, 0.0]]}}
    return export_prop(out, 'makiwari', 'props', prop, cat, porosity=0.8, far=False, budget=2400)


def houki(out):
    """A bamboo broom (竹箒) leaning on a wall (the wall at z = -0.12 behind it): a 1.3 m handle and
    a fan of twigs, worn short on one side."""
    R = rng(9761)
    P = []
    lean = 0.32
    base = np.array([0.0, 0.0, 0.18])
    top = base + np.array([0.06, 1.45 * math.cos(lean), -1.45 * math.sin(lean) * 0.55])
    handle_lo = base + (top - base) * 0.32
    P.append(_w(cyl(handle_lo, top, 0.016, BAMBOO_OLD, n=5), 'plain', 0.0, 9762))
    twig = K.col('#5a4a32')
    d = normalize(top - base)
    side = normalize(np.cross(d, [0, 0, 1.0]))
    for k in range(13):
        f = (k - 6) / 6.0
        a = handle_lo + d * 0.02
        b = base + side * f * 0.2 + np.array([0, 0.01, 0.02 * abs(f)]) + R.normal(0, 0.012, 3)
        b[1] = max(b[1], 0.005)
        P.append(cyl(a, b, 0.006, twig * R.uniform(0.85, 1.15), n=3))
    P.append(_w(cyl(handle_lo - d * 0.02, handle_lo + d * 0.06, 0.024, K.col('#6a5034'), n=6), 'plain', 0.0, 9763))
    prop = K.Prop('houki', 9761).add(P)
    cat = {'footprint': [], 'tags': ['life', 'interact'], 'notes': 'A bamboo broom leaning back against a wall behind it (-z).'}
    return export_prop(out, 'houki', 'props', prop, cat, porosity=0.8, far=False, budget=500)


def teoke(out):
    """A small wooden bucket (手桶): staves, two bamboo hoops, a handle bar on two raised staves."""
    P = []
    wood = K.col('#b39a72')
    P.append(K.lathe([(0.0, 0.0), (0.13, 0.0), (0.145, 0.24), (0.13, 0.24), (0.12, 0.02), (0.0, 0.02)], wood, n=12, pattern='planks',
                     amount=0.3, smooth=False))
    for y in (0.05, 0.19):
        P.append(K.lathe([(0.134 + y * 0.06, y - 0.012), (0.142 + y * 0.06, y), (0.134 + y * 0.06, y + 0.012)], BAMBOO_OLD * 0.9, n=12,
                         cap_top=False, cap_bottom=False))
    for s in (-1, 1):
        P.append(K.cbox((0.035, 0.18, 0.02), wood * 0.95, centre=(s * 0.13, 0.31, 0.0), bevel=0.0))
    P.append(K.cbox((0.3, 0.025, 0.025), wood * 0.9, centre=(0.0, 0.38, 0.0), bevel=0.0))
    P.append(K.cprism(10, 0.118, 0.118, 0.01, WATER, base=(0, 0.2, 0), bevel=0.0))
    prop = K.Prop('teoke', 9771).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.16]], 'tags': ['life', 'interact', 'water'], 'notes': 'A small wooden bucket with water in it.'}
    return export_prop(out, 'teoke', 'props', prop, cat, porosity=0.7, far=False, budget=900)


def _hen_prop(name, seed, pose='up'):
    """A hen (地鶏): plump red-brown body, darker wings, a cocked tail of dark feathers, a small red comb
    and wattle, yellow beak and legs. pose: 'up' (standing, head up), 'peck' (the head down at the
    ground), 'step' (mid-stride: head forward, one foot lifted), 'look' (head up, turned toward the
    camera)."""
    R = rng(seed)
    body_c = K.col('#8c5530')
    hx, hy, hz = {'up': (0.13, 0.27, 0.0), 'peck': (0.17, 0.05, 0.0), 'step': (0.17, 0.23, 0.0), 'look': (0.12, 0.28, 0.035)}[pose]
    peck = pose == 'peck'

    def body(Q):
        b = K.sd_ellipsoid(Q - np.array([0.0, 0.17, 0.0]), (0.15, 0.1, 0.085))
        n = K.sd_capsule(Q, (0.08, 0.2, 0.0), (hx - 0.02, hy, hz * 0.7), 0.045)
        h = K.sd_ellipsoid(Q - np.array([hx, hy, hz]), (0.05, 0.045, 0.04))
        tail = K.sd_ellipsoid(Q - np.array([-0.15, 0.25, 0.0]), (0.05, 0.08, 0.03))
        d = K.smin(b, n, 0.04)
        d = K.smin(d, h, 0.02)
        d = K.smin(d, tail, 0.04)
        return d
    pc = K.sdf_piece(body, (-0.22, 0.0, -0.11), (0.25, 0.36, 0.13), body_c, h=0.012, tris=420, pattern='plain', amount=0.0,
                     var=0.03, seed=seed + 1)

    def plumage(Pp, N):
        m = np.ones((len(Pp), 3))
        wing = (np.abs(Pp[:, 2]) > 0.05) & (Pp[:, 1] > 0.12) & (Pp[:, 1] < 0.24) & (Pp[:, 0] < 0.08)
        m[wing] = 0.72
        tail = Pp[:, 0] < -0.12
        m[tail] = np.array([0.22, 0.2, 0.18]) / (body_c + 1e-6)
        neck = Pp[:, 0] > 0.07
        m[neck] = np.array([0.72, 0.5, 0.28]) / (body_c + 1e-6)
        return m
    pc.shade = plumage
    P = [pc]
    red = K.col('#c42a22')
    up = 0.0 if peck else 1.0
    P.append(K.cbox((0.05, 0.035, 0.012), red, centre=(hx + 0.005, hy + 0.045 * up + 0.01 * (1 - up), hz), bevel=0.0))
    P.append(K.cbox((0.02, 0.03, 0.012), red, centre=(hx + 0.03, hy - 0.04 * up + 0.02 * (1 - up), hz), bevel=0.0))
    beak = K.col('#d8a838')
    P.append(K.cbox((0.035, 0.014, 0.014), beak, centre=(hx + 0.055, hy - 0.005 - 0.02 * (1 - up), hz), bevel=0.0,
                    R=K.rot_z(-0.9 * (1 - up))))
    leg = K.col('#c89a3a')
    for s in (-1, 1):
        if pose == 'step' and s > 0:          # the lifted foot, toes curled under
            P.append(cyl((0.02, 0.06, s * 0.035), (0.01, 0.1, s * 0.03), 0.008, leg, n=3))
            P.append(K.cbox((0.035, 0.006, 0.012), leg, centre=(0.035, 0.055, s * 0.035), bevel=0.0, R=K.rot_z(-0.5)))
            continue
        P.append(cyl((0.0, 0.0, s * 0.035), (0.01, 0.1, s * 0.03), 0.008, leg, n=3))
        P.append(K.cbox((0.06, 0.006, 0.012), leg, centre=(0.03, 0.004, s * 0.035), bevel=0.0))
    return K.Prop(name + '_' + pose, seed).add(P)


def niwatori(out, name, seed, peck=False):
    """A hen; the base pose standing (a) or pecking (b), the others as hidden nodes (Up, Peck, Step,
    Look) for W3Life."""
    base = 'peck' if peck else 'up'
    hide = {None: {'visible': False}}
    extras = {pz.capitalize(): (_hen_prop(name, seed, pz), (0.0, 0.0, 0.0), hide) for pz in ('up', 'peck', 'step', 'look') if pz != base}
    poses = {pz: ('Mesh' if pz == base else pz.capitalize()) for pz in ('up', 'peck', 'step', 'look')}
    cat = {'footprint': [], 'tags': ['life', 'animal'], 'poses': poses,
           'notes': 'A hen, about 0.36 m tall, facing +x' + (' and pecking at the ground.' if peck else ', head up.')
                    + ' Poses (hidden nodes): ' + ', '.join(n for n in extras) + '.'}
    return export_prop(out, name, 'props', _hen_prop(name, seed, base), cat, porosity=0.5, far=False, budget=3600, extras=extras)


# ------------------------------------------------------------------------------------------- crows
CROW = K.col('#1d1c22')


def _crow_prop(pose='stand'):
    """A jungle crow (ハシブトガラス), 0.56 m from bill to tail, facing +x, origin at its feet: a deep
    body tilted up to the head, the steep forehead and the thick arched bill that make it a
    ハシブト, a long tail, black with a blue-violet sheen on top. pose: 'stand', 'peck' (bill to the
    ground), 'caw' (neck stretched forward, bill open), 'hop' (crouched, wings a little open),
    'fly_a' (wings up), 'fly_b' (wings down)."""
    fly = pose.startswith('fly')
    tilt = {'stand': 0.38, 'peck': -0.2, 'caw': 0.18, 'hop': 0.3, 'fly_a': 0.05, 'fly_b': 0.05}[pose]
    by = {'stand': 0.2, 'peck': 0.19, 'caw': 0.19, 'hop': 0.16, 'fly_a': 0.2, 'fly_b': 0.2}[pose]
    bc = np.array([0.0, by, 0.0])
    ax = np.array([math.cos(tilt), math.sin(tilt), 0.0])
    if pose == 'peck':
        H = np.array([0.17, 0.075, 0.0])
        bd = normalize(np.array([0.55, -1.0, 0.0]))
    elif pose == 'caw':
        H = np.array([0.19, 0.28, 0.0])
        bd = normalize(np.array([1.0, 0.25, 0.0]))
    else:
        H = bc + ax * 0.15 + np.array([0.0, 0.07, 0.0])
        bd = normalize(np.array([1.0, -0.12, 0.0]))
    up_b = normalize(np.cross(np.array([0.0, 0.0, 1.0]), bd))
    tail_a = bc - ax * 0.12
    tail_b = bc - ax * 0.32 + np.array([0.0, -0.03 if not fly else 0.0, 0.0])

    def body(Q):
        q = Q - bc
        lq = np.stack([q[..., 0] * ax[0] + q[..., 1] * ax[1], -q[..., 0] * ax[1] + q[..., 1] * ax[0], q[..., 2]], -1)
        b = K.sd_ellipsoid(lq, (0.15, 0.085, 0.075))
        h = K.sd_ellipsoid(Q - H, (0.06, 0.055, 0.05))
        fore = K.sd_ellipsoid(Q - (H + bd * 0.03 + up_b * 0.03), (0.035, 0.03, 0.035))
        n = K.sd_capsule(Q, bc + ax * 0.08, H, 0.05)
        d = K.smin(b, n, 0.04)
        d = K.smin(d, h, 0.025)
        d = K.smin(d, fore, 0.02)
        # the bill: thick at the base, arched on top, a little hook
        if pose == 'caw':
            ob = normalize(bd + up_b * 0.35)
            lb = normalize(bd - up_b * 0.45)
            u = K.sd_capsule(Q, H + bd * 0.04 + up_b * 0.012, H + ob * 0.11 + up_b * 0.01, 0.014)
            l = K.sd_capsule(Q, H + bd * 0.04 - up_b * 0.012, H + lb * 0.1, 0.011)
            bill = np.minimum(u, l)
        else:
            bill = K.smin(K.sd_capsule(Q, H + bd * 0.04, H + bd * 0.1 + up_b * 0.004, 0.02),
                          K.sd_capsule(Q, H + bd * 0.1 + up_b * 0.004, H + bd * 0.125 - up_b * 0.012, 0.009), 0.012)
        d = K.smin(d, bill, 0.012)
        # the tail: long, flat, a little spread at the end
        tq = Q - (tail_a + tail_b) * 0.5
        td = normalize(tail_b - tail_a)
        tl = np.stack([tq[..., 0] * td[0] + tq[..., 1] * td[1], -tq[..., 0] * td[1] + tq[..., 1] * td[0], tq[..., 2]], -1)
        tail = K.sd_ellipsoid(tl, (0.11, 0.016, 0.042 + 0.0))
        d = K.smin(d, tail, 0.03)
        return d
    lo = (-0.36, 0.0, -0.12)
    hi = (0.36, 0.42, 0.12)
    pc = K.sdf_piece(body, lo, hi, CROW, h=0.012, tris=520, pattern='plain', amount=0.0, var=0.0, seed=9851)
    sheen = np.array([0.2, 0.23, 0.36]) / np.maximum(CROW, 1e-4)

    def gloss(Pp, N):
        m = np.ones((len(Pp), 3))
        top = np.clip(N[:, 1], 0, 1)[:, None]
        m = m * (1 - 0.55 * top) + sheen * 0.55 * top          # blue-violet sheen on the back and the crown
        bill = (Pp[:, 0] - H[0]) * bd[0] + (Pp[:, 1] - H[1]) * bd[1] > 0.045
        m[bill] = 0.85
        return m
    pc.shade = gloss
    P = [pc]
    # the eye: one dark-brown glint on each side of the head
    for s in (-1, 1):
        P.append(K.cbox((0.014, 0.014, 0.006), K.col('#3a2a22'), centre=tuple(H + bd * 0.02 + up_b * 0.012 + np.array([0, 0, s * 0.045])),
                        bevel=0.0, mat='noline', ao=False, dirt=False))
    leg = K.col('#24222a')
    if not fly:
        kh = 0.75 if pose == 'hop' else 1.0
        for s in (-1, 1):
            P.append(cyl((0.0, 0.0, s * 0.03), (-0.01, 0.13 * kh, s * 0.028), 0.01, leg, n=3))
            P.append(K.cbox((0.07, 0.008, 0.012), leg, centre=(0.02, 0.004, s * 0.03), bevel=0.0))
            P.append(K.cbox((0.03, 0.008, 0.01), leg, centre=(-0.025, 0.004, s * 0.03), bevel=0.0))
    # the wings: folded on the sides (in the body) or open
    if fly or pose == 'hop':
        sh = bc + ax * 0.04 + np.array([0.0, 0.03, 0.0])
        if pose == 'fly_a':
            ang, span = 0.75, 0.46
        elif pose == 'fly_b':
            ang, span = -0.55, 0.44
        else:
            ang, span = 0.35, 0.16
        for s in (-1, 1):
            # inner and outer wing: broad, the outer narrower with the primaries fanned (a ragged end)
            Rw = K.rot_x(-s * ang)
            inner = K.cbox((0.2, 0.014, span * 0.5), CROW, centre=tuple(sh + Rw @ np.array([-0.02, 0.0, s * span * 0.25])), bevel=0.0, R=Rw)
            P.append(inner)
            if span > 0.3:
                Ro = K.rot_x(-s * (ang * 1.2)) @ K.rot_y(s * 0.25)
                tip0 = sh + Rw @ np.array([-0.02, 0.0, s * span * 0.5])
                outer = K.cbox((0.15, 0.012, span * 0.5), CROW, centre=tuple(tip0 + Ro @ np.array([-0.03, 0.0, s * span * 0.22])),
                               bevel=0.0, R=Ro)
                P.append(outer)
                for f in range(4):           # the fingered primaries
                    fz = s * (span * 0.47)
                    fp = tip0 + Ro @ np.array([0.02 - f * 0.035, 0.0, fz])
                    P.append(K.cbox((0.022, 0.01, 0.07), CROW, centre=tuple(fp), bevel=0.0, R=Ro, mat='noline'))
    return K.Prop('karasu_' + pose, 9851).add(P)


def karasu(out):
    """The crows of the great camphor (G5R3-11 5.3: they take dango up to their nest at the top):
    one asset, the standing pose as its mesh, the others as hidden nodes for W3Life."""
    hide = {None: {'visible': False}}
    names = {'peck': 'Peck', 'caw': 'Caw', 'hop': 'Hop', 'fly_a': 'FlyA', 'fly_b': 'FlyB'}
    extras = {nm: (_crow_prop(pz), (0.0, 0.0, 0.0), hide) for pz, nm in names.items()}
    poses = {'stand': 'Mesh'}
    poses.update({pz: nm for pz, nm in names.items()})
    cat = {'footprint': [], 'tags': ['life', 'animal'], 'poses': poses,
           'notes': 'A jungle crow (ハシブトガラス), 0.56 m, facing +x, origin at its feet. Poses (hidden nodes): '
                    + ', '.join(names.values()) + '. Moved by W3Life (godot/world3d/dressing_life.gd).'}
    return export_prop(out, 'karasu', 'props', _crow_prop('stand'), cat, porosity=0.3, far=False, budget=5200, ground=False,
                       extras=extras)


def build(out):
    st = {}
    st['monohoshi'] = monohoshi(out)
    st['kakehi_yard'] = kakehi_yard(out)
    st['mizugame'] = mizugame(out)
    st['endai'] = endai(out)
    st['nougu'] = nougu(out)
    st['fence_yotsume_a'] = fence_yotsume(out, 'fence_yotsume_a', 9701, 'asagao')
    st['fence_yotsume_b'] = fence_yotsume(out, 'fence_yotsume_b', 9711, 'gourd')
    st['fence_yotsume_c'] = fence_yotsume(out, 'fence_yotsume_c', 9721, 'few')
    st['shiorido'] = shiorido(out)
    st['hatake'] = hatake(out)
    st['kakashi'] = kakashi(out)
    st['neko'] = neko(out)
    # the round-3 baskets and straw under new names (the assembly's fixed slots for the old names lapse)
    st['kago_tall'] = DR.basket(out, 'kago_tall', 'tall', 8351)
    st['zaru'] = DR.basket(out, 'zaru', 'flat', 8355)
    st['wara_sheaves'] = DR.straw(out, 'wara_sheaves', 'sheaf', 8361)
    st['wara_heap'] = DR.straw(out, 'wara_heap', 'heap', 8365)
    st['mushiro'] = mushiro(out)
    st['wara_kuzu'] = wara_kuzu(out)
    st['makiwari'] = makiwari(out)
    st['houki'] = houki(out)
    st['teoke'] = teoke(out)
    st['niwatori_a'] = niwatori(out, 'niwatori_a', 9811, peck=False)
    st['niwatori_b'] = niwatori(out, 'niwatori_b', 9821, peck=True)
    st['karasu'] = karasu(out)
    return st
