"""The yard and the garden of the home (round 4): the life of the house around it.

  monohoshi       laundry pole on two forked posts: an indigo kimono through its sleeves, two
                  tenugui, a small red cloth (cloth swings with the wind: mesh-mode foliage)
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
    # the kimono through its sleeves: sleeves along the pole, the body hanging
    kx = -0.75
    P += cloth(kx - 0.7, kx + 0.7, hp - 0.03, hp - 0.42, z, INDIGO, (kx, hp, z), 0.15, 0.3, 1)
    P += cloth(kx - 0.32, kx + 0.32, hp - 0.42, hp - 1.35, z + 0.004, INDIGO * 1.06, (kx, hp, z), 0.35, 0.9, 3,
               stripes=[(hp - 0.7, K.col('#d8d4c4')), (hp - 1.05, K.col('#d8d4c4'))])
    P.append(K.cbox((0.64, 0.05, 0.016), K.col('#a83a2e'), centre=(kx, hp - 0.45, z + 0.012), bevel=0.0, var=0.0).swaying((kx, hp, z), 0.35))
    # two tenugui folded over the pole, a blue stripe at the hem
    for k, x in enumerate((0.45, 0.85)):
        P += cloth(x - 0.16, x + 0.16, hp - 0.02, hp - 0.62, z, WHITE_CLOTH * (1.0 - 0.03 * k), (x, hp, z), 0.3, 0.9, 2,
                   stripes=[(hp - 0.52, K.col('#3a5a8a'))])
    # a small red cloth
    P += cloth(1.25, 1.52, hp - 0.02, hp - 0.42, z, K.col('#b04034'), (1.38, hp, z), 0.35, 1.0, 2)
    prop = K.Prop('monohoshi', 9501).add(P)
    cat = {'footprint': [[-span / 2, 0.0, 0.12], [span / 2, 0.0, 0.12]], 'tags': ['life'],
           'notes': 'Laundry pole on two forked posts (3.6 m), an indigo kimono through its sleeves, two tenugui, a red cloth; '
                    'the cloth swings with the wind (foliage material, mesh mode).',
           'anchors': {'perch': [[-span / 2, hp + 0.12, 0.0], [span / 2, hp + 0.12, 0.0], [0.1, hp + 0.03, 0.0]]}}
    return export_prop(out, 'monohoshi', 'props', prop, cat, porosity=0.8, far=False, budget=1800)


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
def neko(out):
    """A calico cat asleep, curled up: body, head tucked to the right, tail around the front."""
    def body(Q):
        b = K.sd_ellipsoid(Q - np.array([0.0, 0.085, 0.0]), (0.2, 0.1, 0.15))
        h = K.sd_ellipsoid(Q - np.array([0.13, 0.1, 0.06]), (0.075, 0.065, 0.07))
        e1 = K.sd_capsule(Q, (0.11, 0.15, 0.05), (0.105, 0.19, 0.04), 0.018)
        e2 = K.sd_capsule(Q, (0.17, 0.15, 0.06), (0.185, 0.185, 0.05), 0.018)
        tail = K.sd_capsule(Q, (-0.17, 0.05, 0.05), (-0.05, 0.035, 0.15), 0.028)
        tail2 = K.sd_capsule(Q, (-0.05, 0.035, 0.15), (0.09, 0.035, 0.15), 0.024)
        d = K.smin(b, h, 0.04)
        d = np.minimum(d, np.minimum(e1, e2))
        d = K.smin(d, np.minimum(tail, tail2), 0.02)
        return d
    pc = K.sdf_piece(body, (-0.26, -0.02, -0.2), (0.27, 0.22, 0.22), K.col('#ece6d8'), h=0.012, tris=560, pattern='plain', amount=0.0,
                     var=0.02, seed=9651)

    def calico(Pp, N):
        m = np.ones((len(Pp), 3))
        n1 = fbm3(Pp[:, 0] * 9, Pp[:, 1] * 9, Pp[:, 2] * 9, 2, 9652)
        n2 = fbm3(Pp[:, 0] * 8 + 3, Pp[:, 1] * 8, Pp[:, 2] * 8, 2, 9653)
        orange = (n1 > 0.58) & (Pp[:, 1] > 0.06)
        black = (n2 > 0.62) & (Pp[:, 1] > 0.08) & ~orange
        m[orange] = np.array([0.86, 0.58, 0.34]) / np.array([0.925, 0.9, 0.85])
        m[black] = np.array([0.2, 0.18, 0.17]) / np.array([0.925, 0.9, 0.85])
        # closed eyes and the nose: a dark line on the face
        face = (Pp[:, 0] > 0.17) & (Pp[:, 2] > 0.09) & (np.abs(Pp[:, 1] - 0.11) < 0.008)
        m[face] = np.array([0.25, 0.22, 0.2]) / np.array([0.925, 0.9, 0.85])
        return m
    pc.shade = calico
    prop = K.Prop('neko', 9651).add([pc])
    return export_prop(out, 'neko', 'props', prop, {'footprint': [], 'tags': ['life', 'animal'],
                                                   'notes': 'A calico cat (三毛猫) asleep, curled up, 0.5 m long; place on the engawa.'},
                       porosity=0.5, far=False, budget=800, ground=False)


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
    return st
