"""The hut (小屋) at the pass, Q proportion: a one-room timber house under a thick hipped thatch
roof (寄棟の茅葺) with a ridge bundle held by crossed sticks; posts on stones, boards below,
earth plaster above; a sliding door (node Door) and its bar (node DoorBar), a lattice window;
under the deep front eave: the old backpack frame leaning on the wall (node BackpackFrame, also
objects/backpack_frame), firewood stacked, a water tub, straw sandals on a nail, a broom, a step
stone. Origin at the hut marker; the front (+z) faces south, the door 3 m in front of the origin
(the hut_door marker). The roof stipples away over her (cutaway)."""
from __future__ import annotations

import math

import numpy as np

from ..core import fbm3, rng
from . import kit as K
from .common import export_prop

POST = K.col('#5e4a3a')
BOARD = K.col('#7d6c5a')
PLASTER = K.col('#cdbd9c')
THATCH = K.col('#8e7e5c')
THATCH_CUT = K.col('#a8915f')
STONE = K.col('#8a867c')
DARK = K.col('#2a2320')
WOOD_NEW = K.col('#9c8262')
LOG_END = K.col('#b49a72')
STRAW = K.col('#c2a868')

WX, WZ = 2.8, 1.9                 # half extents of the walls
HW, HD = 3.65, 2.85               # half extents of the roof edge
EAVE = 2.85                       # outer thatch height at the eave edge
THICK = 0.56                      # thatch thickness seen at the eave
TAN_F, TAN_E = 0.9, 1.35          # slope of the long sides and of the hip ends
WALL_TOP = 2.35


def _soft_min(a, b, k):
    return K.smin(a, b, k)


def thatch_sdf(P, seed=8201):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    # height of the outer surface: hipped (front/back slopes and steeper ends), soft hips and ridge
    run_f = HD - np.abs(z)
    run_e = (HW - np.abs(x)) * (TAN_E / TAN_F)
    run = _soft_min(run_f, run_e, 0.5)
    ridge_run = HD - 0.12
    run = _soft_min(run, ridge_run, 0.35)
    h = EAVE + TAN_F * run
    d_out = (y - h) / math.sqrt(1 + TAN_F ** 2)
    shell = np.maximum(d_out, -(d_out + THICK * 0.95))
    # the trimmed eave: vertical cut faces at the roof edge, corners rounded in plan
    qx = np.abs(x) - (HW - 0.9)
    qz = np.abs(z) - (HD - 0.9)
    edge = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - 0.9
    d = np.maximum(shell, edge)
    # straw lumps on the surface, ragged straw ends on the cut
    d = d + (fbm3(x * 2.2, y * 2.2, z * 2.2, octaves=3, seed=seed) - 0.5) * 0.09
    d = d + (fbm3(x * 9.0, y * 3.0, z * 9.0, octaves=2, seed=seed + 1) - 0.5) * 0.05 * (np.abs(edge) < 0.2)
    return d


def thatch_shade(P, N):
    """Weathered straw: greyer on the open slopes, rain streaks down the slope, moss toward the
    eaves on the shaded side, the cut eave lighter with dark layer lines."""
    y = P[:, 1]
    m = np.ones((len(P), 3))
    streak = fbm3(P[:, 0] * 3.0, P[:, 1] * 0.4, P[:, 2] * 0.6, octaves=2, seed=8205)
    m *= (0.88 + 0.24 * streak)[:, None]
    top = np.clip(N[:, 1], 0, 1)[:, None]
    m = m * (1 - 0.25 * top) + np.array([0.86, 0.86, 0.84]) * 0.25 * top
    moss = (fbm3(P[:, 0] * 1.2, P[:, 1] * 1.2, P[:, 2] * 1.2, octaves=3, seed=8206) > 0.55) & (y < EAVE + 0.9)
    moss &= N[:, 1] > 0.2
    m[moss] = m[moss] * np.array([0.82, 0.9, 0.74])
    cut = np.abs(N[:, 1]) < 0.45
    lay = (np.floor((y - EAVE) / 0.09) % 2 == 0)
    m[cut] = np.array([1.12, 1.08, 1.0]) * np.where(lay[cut], 0.85, 1.0)[:, None]
    return m


def cyl(p0, p1, r, colour, n=6, bevel=0.01, **kw):
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    L = np.linalg.norm(d)
    return K.cprism(n, r, r, L, colour, base=p0, bevel=bevel, R=K.frame_to(d), **kw)


def _w(pc, pattern='planks', amount=0.3, seed=0):
    pc.pattern = K.PAT[pattern]
    pc.amount = amount
    pc.seed = seed
    pc.var = 0.05
    return pc


def house_pieces(R):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))
    # foundation stones under the posts and a stone sill row in front
    posts_x = [-WX, -1.42, -0.32, 0.5, 1.9, WX]
    for x in posts_x:
        for z in (WZ,):                       # the back row is hidden under the roof from our camera
            def f(Q, s=sd()):
                return K.sd_ellipsoid(Q - np.array([0, 0.06, 0]), (0.24, 0.16, 0.22)) + K.weathered(Q, 0.02, 0.08, s)
            P.append(K.sdf_piece(f, (-0.28, -0.12, -0.26), (0.28, 0.24, 0.26), STONE * (1 + R.normal(0, 0.04)), h=0.03,
                                 tris=40, pattern='stone', amount=0.6, var=0.06, seed=sd()).moved(None, (x, 0, z)))
    for x in (-WX, WX):
        P.append(K.sdf_piece(lambda Q: K.sd_ellipsoid(Q - np.array([0, 0.06, 0]), (0.24, 0.16, 0.22)) + K.weathered(Q, 0.02, 0.08, 3),
                             (-0.28, -0.12, -0.26), (0.28, 0.24, 0.26), STONE, h=0.03, tris=60, pattern='stone', amount=0.6,
                             var=0.06, seed=sd()).moved(None, (x, 0, 0)))
    # sills
    for z in (-WZ, WZ):
        P.append(_w(K.beam((-WX - 0.08, 0.27, z), (WX + 0.08, 0.27, z), 0.16, 0.14, POST, bevel=0.015 if z > 0 else 0.0), 'bark', 0.3, sd()))
    for x in (-WX, WX):
        P.append(_w(K.beam((x, 0.27, -WZ - 0.08), (x, 0.27, WZ + 0.08), 0.16, 0.14, POST), 'bark', 0.3, sd()))
    # posts
    for x in posts_x:
        for z in (-WZ, WZ):
            P.append(_w(K.cbox((0.16, WALL_TOP - 0.3, 0.16), POST, centre=(x, 0.3 + (WALL_TOP - 0.3) / 2, z),
                               bevel=0.018 if z > 0 else 0.0, jitter=0.005, seed=sd()), 'bark', 0.35, sd()))
    for x in (-WX, WX):
        P.append(_w(K.cbox((0.16, WALL_TOP - 0.3, 0.16), POST, centre=(x, 0.3 + (WALL_TOP - 0.3) / 2, 0.0), bevel=0.018), 'bark', 0.35, sd()))
    # wall plates and the mid rail
    for z in (-WZ, WZ):
        P.append(_w(K.beam((-WX - 0.25, WALL_TOP, z), (WX + 0.25, WALL_TOP, z), 0.17, 0.2, POST), 'bark', 0.3, sd()))
    for x in (-WX, WX):
        P.append(_w(K.beam((x, WALL_TOP + 0.04, -WZ - 0.25), (x, WALL_TOP + 0.04, WZ + 0.25), 0.15, 0.17, POST), 'bark', 0.3, sd()))
    # walls: boards below, plaster above, between the posts (front has the door and the window)
    def panel(x0, x1, z, y0, y1, c, pat, amt, inset=0.04):
        return _w(K.cbox((x1 - x0, y1 - y0, 0.06), c, centre=((x0 + x1) / 2, (y0 + y1) / 2, z - np.sign(z) * inset), bevel=0.0),
                  pat, amt, sd())

    def side_panel(x, z0, z1, y0, y1, c, pat, amt, inset=0.04):
        return _w(K.cbox((0.06, y1 - y0, z1 - z0), c, centre=(x - np.sign(x) * inset, (y0 + y1) / 2, (z0 + z1) / 2), bevel=0.0),
                  pat, amt, sd())
    spans = list(zip(posts_x[:-1], posts_x[1:]))
    for i, (x0, x1) in enumerate(spans):
        a, b = x0 + 0.08, x1 - 0.08
        # back wall: full
        P.append(panel(a, b, -WZ, 0.34, 1.0, BOARD, 'planks', 0.4))
        P.append(panel(a, b, -WZ, 1.0, WALL_TOP - 0.1, PLASTER * (1 + R.normal(0, 0.03)), 'plain', 0.2))
        if i == 1:            # the doorway (x -1.34 .. -0.4): the door is its own node
            P.append(panel(a, b, WZ, 2.13, WALL_TOP - 0.1, PLASTER, 'plain', 0.2))
            P.append(_w(K.cbox((b - a + 0.16, 0.08, 0.16), POST, centre=((a + b) / 2, 2.13, WZ), bevel=0.012), 'bark', 0.3, sd()))
            P.append(K.cbox((b - a, 1.82, 0.03), DARK, centre=((a + b) / 2, 0.34 + 0.9, WZ - 0.12), bevel=0.0, var=0.0))
        elif i == 3:          # the window (x 0.58 .. 1.82) with a lattice
            P.append(panel(a, b, WZ, 0.34, 1.0, BOARD, 'planks', 0.4))
            P.append(panel(a, b, WZ, 1.78, WALL_TOP - 0.1, PLASTER, 'plain', 0.2))
            P.append(K.cbox((b - a, 0.76, 0.03), DARK, centre=((a + b) / 2, 1.39, WZ - 0.1), bevel=0.0, var=0.0))
            P.append(_w(K.cbox((b - a + 0.1, 0.07, 0.12), POST, centre=((a + b) / 2, 1.0, WZ), bevel=0.01), 'bark', 0.3, sd()))
            P.append(_w(K.cbox((b - a + 0.1, 0.07, 0.12), POST, centre=((a + b) / 2, 1.78, WZ), bevel=0.01), 'bark', 0.3, sd()))
            for k in range(1, 8):
                xx = a + (b - a) * k / 8
                P.append(_w(K.cbox((0.035, 0.76, 0.04), WOOD_NEW * 0.8, centre=(xx, 1.39, WZ + 0.02), bevel=0.0), 'planks', 0.2, sd()))
        else:
            P.append(panel(a, b, WZ, 0.34, 1.0, BOARD, 'planks', 0.4))
            P.append(panel(a, b, WZ, 1.0, WALL_TOP - 0.1, PLASTER * (1 + R.normal(0, 0.03)), 'plain', 0.2))
    for x in (-WX, WX):
        for z0, z1 in ((-WZ + 0.08, -0.08), (0.08, WZ - 0.08)):
            P.append(side_panel(x, z0, z1, 0.34, 1.0, BOARD, 'planks', 0.4))
            P.append(side_panel(x, z0, z1, 1.0, WALL_TOP - 0.1, PLASTER * (1 + R.normal(0, 0.03)), 'plain', 0.2))
    # the mid rail (nuki) across the plaster, front and sides
    for z in (-WZ, WZ):
        P.append(_w(K.beam((-WX, 1.0, z + np.sign(z) * 0.01), (WX, 1.0, z + np.sign(z) * 0.01), 0.06, 0.09, POST * 1.05), 'bark', 0.3, sd()))
    # rafter ends showing under the front eave
    for k in range(13):
        xx = -WX - 0.5 + k * (2 * WX + 1.0) / 12
        P.append(_w(K.beam((xx, WALL_TOP + 0.12, WZ - 0.2), (xx, WALL_TOP + 0.62, HD - 0.15), 0.08, 0.08, POST * 0.9, bevel=0.0), 'bark', 0.3, sd()))
    return P


def ridge_pieces(R):
    P = []
    ridge_y = EAVE + TAN_F * (HD - 0.12) - 0.05
    L = HW - (HD - 0.12) * TAN_F / TAN_E
    bundle = K.lathe([(0.0, -L - 0.25), (0.2, -L - 0.2), (0.27, -L + 0.1), (0.27, L - 0.1), (0.2, L + 0.2), (0.0, L + 0.25)],
                     K.col('#5f5546'), n=8, R=K.rot_z(math.pi / 2), base=(0, ridge_y + 0.12, 0), pattern='bark', amount=0.3,
                     var=0.06, seed=8210)
    P.append(bundle)
    for k in range(6):                        # crossed sticks holding the ridge
        x = -L + (2 * L) * k / 5
        for s in (-1, 1):
            a = np.array([x, ridge_y + 0.62, s * 0.18])
            b = np.array([x, ridge_y - 0.12, -s * 0.55])
            P.append(cyl(b, a, 0.035, K.col('#4e4136'), n=5, pattern='bark', amount=0.2, seed=8211 + k))
    return P, ridge_y


def door_piece():
    out = []
    W, H = 0.98, 1.82
    out.append(_w(K.cbox((W, H, 0.05), BOARD * 1.05, centre=(0, H / 2, 0), bevel=0.012), 'planks', 0.5, 8220))
    for y in (0.15, 0.9, 1.65):                # battens
        out.append(_w(K.cbox((W - 0.06, 0.07, 0.03), POST, centre=(0, y, 0.035), bevel=0.006), 'bark', 0.3, 8221))
    for x in (-W / 2 + 0.04, W / 2 - 0.04):
        out.append(_w(K.cbox((0.06, H, 0.03), POST, centre=(x, H / 2, 0.035), bevel=0.006), 'bark', 0.3, 8222))
    out.append(_w(K.cbox((0.05, 0.12, 0.03), K.col('#3a2e26'), centre=(W / 2 - 0.12, 1.0, 0.06), bevel=0.005), 'plain', 0.0, 8223))
    return out


def bar_pieces():
    """閂: a bar across the door in two brackets."""
    out = [_w(K.beam((-0.62, 0, 0), (0.62, 0, 0), 0.07, 0.09, WOOD_NEW), 'bark', 0.3, 8230)]
    for x in (-0.5, 0.5):
        out.append(_w(K.cbox((0.08, 0.16, 0.07), POST, centre=(x, 0, -0.03), bevel=0.008), 'bark', 0.3, 8231))
    return out


def backpack_frame_pieces(R=None, seed=8240):
    """背負子: two uprights joined by rungs, a shelf at the foot, two worn straps; 1.05 m."""
    w = K.col('#7a6650')
    out = []
    for x in (-0.22, 0.22):
        out.append(_w(cyl((x, 0.0, 0.0), (x * 0.9, 1.05, -0.02), 0.028, w, n=5), 'bark', 0.3, seed))
    for y in (0.35, 0.62, 0.9):
        out.append(_w(cyl((-0.22, y, 0.0), (0.22, y, 0.0), 0.018, w * 0.9, n=4), 'bark', 0.3, seed + 1))
    out.append(_w(K.cbox((0.5, 0.03, 0.22), w * 0.95, centre=(0, 0.12, 0.1), bevel=0.006), 'planks', 0.3, seed + 2))
    for x in (-0.12, 0.12):
        out.append(K.rod([[x, 0.95, -0.03], [x * 1.1, 0.75, -0.13], [x * 1.1, 0.45, -0.12], [x, 0.3, -0.03]], 0.018,
                         K.col('#5a4636'), n=4, cap=True, step=0.12, var=0.0))
    return out


def tub_pieces():
    """桶: staves and two hoops, a ladle."""
    out = [K.lathe([(0.0, 0.0), (0.2, 0.0), (0.23, 0.32), (0.21, 0.33), (0.18, 0.06), (0.0, 0.06)], K.col('#8a7458'), n=12,
                   pattern='planks', amount=0.3, var=0.05, seed=8250)]
    for y in (0.07, 0.25):
        out.append(K.lathe([(0.2 + y * 0.09, y), (0.215 + y * 0.09, y + 0.005), (0.215 + y * 0.09, y + 0.035),
                            (0.2 + y * 0.09, y + 0.04)], K.col('#4a4038'), n=12, var=0.0, cap_top=False, cap_bottom=False))
    out.append(K.lathe([(0.0, 0.0), (0.18, 0.0), (0.18, 0.005), (0.0, 0.005)], K.col('#4b5a5e'), n=10, base=(0, 0.26, 0),
                       var=0.0, ao=False))       # water
    out.append(cyl((0.05, 0.3, 0.0), (0.32, 0.55, 0.05), 0.012, K.col('#7a6650'), n=4))
    return out


def firewood_pieces(R):
    out = []
    for row in range(4):
        for k in range(6):
            x = -0.42 + k * 0.17 + (0.08 if row % 2 else 0) + R.normal(0, 0.01)
            if x > 0.45:
                continue
            y = 0.09 + row * 0.15
            r = 0.075 + R.normal(0, 0.008)
            c = LOG_END * (1 + R.normal(0, 0.05))
            out.append(_w(cyl((x, y, -0.22), (x, y, 0.2 + R.normal(0, 0.03)), r, c, n=6, bevel=0.0), 'bark', 0.4,
                          int(R.integers(0, 1 << 20))))
    return out


def broom_pieces():
    out = [cyl((0.0, 0.25, 0.0), (0.0, 1.45, 0.0), 0.016, K.col('#9a8a5a'), n=4)]
    out.append(K.lathe([(0.03, 0.0), (0.13, 0.02), (0.16, 0.12), (0.06, 0.32), (0.025, 0.34)], K.col('#8a7a50'), n=8,
                       pattern='thatch', amount=0.3, var=0.06, seed=8260))
    return out


def sandals_pieces():
    out = []
    for dx in (-0.06, 0.06):
        out.append(_w(K.cbox((0.09, 0.22, 0.02), STRAW * 0.95, centre=(dx, -0.12, 0.0), bevel=0.008), 'thatch', 0.3, 8270))
    out.append(K.rod([[-0.06, 0.0, 0.01], [0.0, 0.04, 0.02], [0.06, 0.0, 0.01]], 0.007, K.col('#8a3a2c'), n=3, cap=True, step=0.03,
                     var=0.0, dirt=False))
    return out


def build(out):
    R = rng(8200)
    pieces = house_pieces(R)
    thatch = K.sdf_piece(thatch_sdf, (-HW - 0.1, EAVE - THICK - 0.15, -HD - 0.1),
                         (HW + 0.1, EAVE + TAN_F * HD + 0.3, HD + 0.1), THATCH, h=0.05, tris=1650, pattern='bark',
                         amount=0.5, var=0.04, seed=8201, mat='roof', shade=thatch_shade, dirt=False)
    pieces.append(thatch)
    rp, ridge_y = ridge_pieces(R)
    for p in rp:
        p.mat = 'roof'
    pieces += rp
    # under the front eave
    pieces.append(K.sdf_piece(lambda Q: K.sd_box(Q - np.array([0, 0.06, 0]), (0.42, 0.1, 0.26), 0.06) + K.weathered(Q, 0.015, 0.1, 8280),
                              (-0.5, -0.06, -0.32), (0.5, 0.22, 0.32), STONE, h=0.03, tris=120, pattern='stone', amount=0.5,
                              var=0.05, seed=8280).moved(None, (-0.87, 0.0, WZ + 0.55)))       # step stone
    fw = firewood_pieces(R)
    pieces += [p.moved(K.rot_y(math.pi / 2), (2.25, 0.0, WZ + 0.3)) for p in fw]
    pieces += [p.moved(None, (-0.05, 0.0, WZ + 0.45)) for p in tub_pieces()]
    pieces += [p.moved(K.rot_z(-0.2), (0.12, 0.0, WZ + 0.12)) for p in broom_pieces()]
    pieces += [p.moved(None, (-1.62, 1.55, WZ + 0.06)) for p in sandals_pieces()]
    prop = K.Prop('hut', 8200).add(pieces)
    # the separate nodes
    door = K.Prop('door', 8220).add(door_piece())
    bar = K.Prop('door_bar', 8230).add(bar_pieces())
    bp = K.Prop('backpack_frame', 8240).add(backpack_frame_pieces())
    door_pos = (-0.87, 0.32, WZ + 0.06)
    bar_pos = (-0.87, 1.08, WZ + 0.13)
    lean = math.radians(16)
    bp_pos = (-2.2, 0.0, WZ + 0.38)
    extras = {
        'Door': (door, door_pos),
        'DoorBar': (bar, bar_pos),
        'BackpackFrame': (bp, bp_pos, {}),
    }
    # the frame leans on the wall: rotate it about x (top toward the wall)
    extras['BackpackFrame'] = (bp, bp_pos, {None: {'pos': list(bp_pos), 'rot': [-math.degrees(lean), 8.0, 0.0]},
                                            'far': {'pos': list(bp_pos), 'rot': [-math.degrees(lean), 8.0, 0.0]}})
    cat = {'footprint': [[-1.4, 0.0, 2.0], [1.4, 0.0, 2.0], [0.0, -0.6, 2.0], [2.25, 2.2, 0.55]],
           'tags': ['building', 'interact', 'home'],
           'notes': 'Thatched hut, Q proportion: walls 5.6 x 3.8 m, roof 7.3 x 5.7 m, ridge %.1f m, eave underside 2.3 m, '
                    'door 0.98 x 1.82 m. Nodes: Door (slides open toward -x by 0.9 m), DoorBar (lift away to unbar), '
                    'BackpackFrame (the old frame; the same object is objects/backpack_frame). The roof material stipples '
                    'away over her.' % (ridge_y + 0.4),
           'anchors': {'door': [-0.87, 0.0, 3.0], 'interact': [-0.87, 0.0, 2.9], 'door_open_offset': [-0.9, 0.0, 0.0],
                       'firewood': [2.25, 0.4, WZ + 0.3], 'tub': [-0.05, 0.3, WZ + 0.45], 'backpack_frame': list(bp_pos)}}
    st = {'hut': export_prop(out, 'hut', 'buildings', prop, cat, porosity=0.85, cutaway=False, extras=extras, budget=6000)}
    b2 = K.Prop('backpack_frame', 8240).add(backpack_frame_pieces())
    st['backpack_frame'] = export_prop(out, 'backpack_frame', 'objects', b2,
                                       {'footprint': [], 'tags': ['pickup', 'story'],
                                        'notes': '背負子, the old backpack frame (1.05 m), upright; origin at its feet.',
                                        'anchors': {'carry': [0.0, 0.6, -0.05]}}, porosity=0.8, budget=800)
    return st
