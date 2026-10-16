"""The home at the pass (母屋, round 4): the house a family lives in, in Q proportion, the size of a
real farmhouse (G5R2-1 ④: warmer, bigger, several times the detail of the round-3 hut).

A hipped thatch (寄棟の茅葺) in three trimmed courses with a thick cut eave and a turf ridge
(芝棟: grass, iris and a mountain lily growing on it); the main house (7.6 x 4.4 m walls) on stones,
smoke-darkened posts, earth plaster over boards; along the front an engawa (縁側) under the deep
eave; behind it shoji (one slid open: tatami, a low table, a brazier glowing at night), a reed blind
(簾) half down, a wind chime (風鈴) at the corner; the east bay is the doma (土間) door with an indigo
noren; under the eave hang bunches of onions (吊り玉葱, the summer harvest drying; round 5: the dried
persimmons of round 4 were late autumn) and red peppers, two bon lanterns (盆提灯) light the engawa at
Obon (paper lit from inside after dusk); a straw raincoat
and a sedge hat on the wall; on the engawa a tea tray, a fan, a mosquito-coil pig; the step stone
with geta; potted morning glories at the engawa's ends; a drip line of pebbles where the rain falls
off the thatch. To the west a board-roofed lean-to (下屋, stones on the boards) with the kitchen
range's chimney (anchors.smoke).

Materials: solid (wood, stone, plaster), roof (thatch), shoji (paper lit from inside after dusk),
lit (the brazier's embers), sway / swaynl (cloth, paper strips, hanging fruit: the foliage material
in mesh mode, each piece swings with the wind by whole pixels), cards (the plants on the ridge and
the morning glories). Origin: the middle of the main house's footprint on the ground; the front
(+z) faces south. The doma door is the node Door (a sliding board door, open)."""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import flora as FL
from .. import foliage as FO
from ..core import PX, fbm3, normalize, rng
from . import kit as K
from .common import export_prop

# ------------------------------------------------------------------------------------------- colours
POST = K.col('#4f3f33')       # posts and beams darkened by decades of hearth smoke
BEAM = K.col('#5a4838')
BOARD = K.col('#6e5b49')      # weathered boards (腰板, the lean-to)
BOARD_OLD = K.col('#7d7366')  # silvered boards on the weather side
DECK = K.col('#8a6e52')       # the engawa, polished by feet
PLASTER = K.col('#cdbf9c')    # earth plaster (土壁)
PAPER = K.col('#efe9d8')      # shoji paper
KUMIKO = K.col('#a48a68')
THATCH = K.col('#7a705a')     # aged thatch: grey-brown, not gold
STONE = K.col('#8b877d')
STONE_DARK = K.col('#6f6c64')
DARK = K.col('#1f1a16')
TATAMI = K.col('#b4aa74')
TATAMI_EDGE = K.col('#36452f')
INDIGO = K.col('#2e3c62')
PERSIMMON = K.col('#a8552a')
CHILLI = K.col('#a8281e')
STRAW = K.col('#b49a62')
CERAMIC = K.col('#6a5446')
IRON = K.col('#3c3a38')
TURF = K.col('#4c5a33')
EARTH = K.col('#5e4c3a')
BAMBOO = K.col('#9a9a5c')

# ------------------------------------------------------------------------------------------- sizes (m)
WX, WZ = 3.8, 2.2               # half extents of the main house's walls
FLOOR = 0.5                     # floor level (engawa, tatami)
PLATE = 2.85                    # wall plate
HW, HD = 4.9, 3.3               # half extents of the roof edge
EAVE = 3.05                     # outer thatch height at the eave edge
THICK = 0.45                    # thatch thickness (the cut eave shows about 0.6 m)
TAN_F, TAN_E = 0.92, 1.35       # slope of the long sides and of the hip ends
TIERS = (0.8, 1.6, 2.35)        # runs (m in from the eave) where an upper course begins
TIER_STEP = 0.2
BAYS = (-3.8, -1.9, 0.0, 1.9, 3.8)
ENG_Z0, ENG_Z1 = WZ, 3.05       # the engawa, front wall to its edge
ENG_X0, ENG_X1 = -3.8, 1.9      # it runs past three bays; the fourth is the doma door
LINTEL = FLOOR + 1.78
GX0, GX1 = -6.05, -3.8          # the lean-to (下屋) on the west
GZ0, GZ1 = -1.7, 1.75
G_ROOF_BACK, G_ROOF_FRONT = 2.45, 2.0


def _w(pc, pattern='planks', amount=0.3, seed=0, var=0.05):
    pc.pattern = K.PAT[pattern]
    pc.amount = amount
    pc.seed = seed
    pc.var = var
    return pc


def cyl(p0, p1, r, colour, n=6, bevel=0.0, **kw):
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    return K.cprism(n, r, r, float(np.linalg.norm(d)), colour, base=p0, bevel=bevel, R=K.frame_to(d), **kw)


def bar(x0, x1, y0, y1, z, colour, depth=0.02, **kw):
    """An axis-aligned bar in the x-y plane at z (its front face at z + depth / 2)."""
    return K.cbox((x1 - x0, y1 - y0, depth), colour, centre=((x0 + x1) / 2, (y0 + y1) / 2, z), bevel=0.0, var=0.0, **kw)


# ------------------------------------------------------------------------------------------- thatch
def _step(run, at, w=0.05):
    t = np.clip((run - (at - w)) / (2 * w), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def thatch_sdf(P, seed=9201):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    wob = (fbm3(x * 0.7 + 3.0, z * 0.7, y * 0.1, octaves=2, seed=seed + 3) - 0.5)
    run_f = HD + wob * 0.12 - np.abs(z)
    run_e = (HW + wob * 0.12 - np.abs(x)) * (TAN_E / TAN_F)
    run = K.smin(run_f, run_e, 0.55)
    run = K.smin(run, HD - 0.14, 0.35)
    # the courses are laid by hand: each trimmed edge wanders a little along the roof
    steps = 0.0
    for i, r in enumerate(TIERS):
        wav = 0.07 * np.sin(x * (1.3 + 0.4 * i) + i * 1.7) + 0.05 * (fbm3(x * 1.1, z * 0.3 + i * 5, 0.0, 2, seed + 10 + i) - 0.5)
        steps = steps + _step(run, r + wav)
    h = EAVE + wob * 0.07 + TAN_F * run + steps * TIER_STEP
    d_out = (y - h) / math.sqrt(1 + TAN_F ** 2)
    shell = np.maximum(d_out, -(d_out + THICK * 0.95))
    qx = np.abs(x) - (HW - 1.0) - wob * 0.14
    qz = np.abs(z) - (HD - 1.0) - wob * 0.14
    edge = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - 1.0
    d = np.maximum(shell, edge)
    d = d + (fbm3(x * 2.0, y * 2.0, z * 2.0, octaves=3, seed=seed) - 0.5) * 0.07
    d = d + (fbm3(x * 8.0, y * 3.0, z * 8.0, octaves=2, seed=seed + 1) - 0.5) * 0.045 * (np.abs(edge) < 0.22)
    return d


def thatch_shade(P, N):
    """Old thatch: grey-brown slopes with rain streaks down the fall line; patches re-thatched a few
    years ago (warmer, a little lighter); moss toward the eaves; the cut faces pale straw ends
    (quieter than round 3's gold)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    m = np.ones((len(P), 3))
    streak = fbm3(x * 2.6, y * 0.35, z * 0.5, octaves=2, seed=9205)
    m *= (0.86 + 0.26 * streak)[:, None]
    top = np.clip(N[:, 1], 0, 1)[:, None]
    m = m * (1 - 0.22 * top) + np.array([0.86, 0.86, 0.85]) * 0.22 * top
    # re-thatched patches: newer straw, warmer
    patch = fbm3(x * 0.55 + 7.0, y * 0.55, z * 0.55, octaves=2, seed=9207)
    newer = (patch > 0.64)[:, None] & (top > 0.3)
    m = np.where(newer, m * np.array([1.08, 1.04, 0.95]), m)
    # moss: low on the slopes (water runs off the courses), in small broken drifts, olive not green
    mn = fbm3(x * 1.1, y * 1.1, z * 1.1, octaves=3, seed=9206) + (fbm3(x * 5.0, y * 5.0, z * 5.0, 2, 9208) - 0.5) * 0.3
    moss = (mn > 0.6) & (y < EAVE + 1.2) & (N[:, 1] > 0.25)
    m[moss] = m[moss] * np.array([0.82, 0.9, 0.74])
    cut = np.abs(N[:, 1]) < 0.5
    m[cut] = np.array([1.26, 1.18, 1.05])
    return m


def roof_height(x, z):
    run_f = HD - abs(z)
    run_e = (HW - abs(x)) * (TAN_E / TAN_F)
    run = float(K.smin(np.array(run_f), np.array(run_e), 0.55))
    run = float(K.smin(np.array(run), np.array(HD - 0.14), 0.35))
    steps = sum(float(_step(np.array(run), r)) for r in TIERS) * TIER_STEP
    return EAVE + TAN_F * run + steps


def thatch_piece():
    return K.sdf_piece(thatch_sdf, (-HW - 0.25, EAVE - THICK - 0.3, -HD - 0.25),
                       (HW + 0.25, EAVE + TAN_F * HD + 0.4 + len(TIERS) * TIER_STEP, HD + 0.25), THATCH, h=0.05, tris=6500,
                       pattern='thatch', amount=0.5, var=0.04, seed=9201, mat='roof', shade=thatch_shade, dirt=False)


def ridge_pieces(R):
    """芝棟: the ridge is capped with turf (earth and roots holding the top courses), grass and iris
    grow on it; three ties of rope; crossed sticks at the ends; the smoke hood near the east end."""
    P = []
    ridge_y = roof_height(0.0, 0.0) - 0.04
    L = HW - (HD - 0.14) * TAN_F / TAN_E
    sd = lambda: int(R.integers(0, 1 << 20))

    def turf_f(Q):
        # a long rounded mound along x, a little lumpy, its ends rounded down into the hips
        ax = np.clip(Q[..., 0], -L + 0.15, L - 0.15)
        d = np.sqrt((Q[..., 0] - ax) ** 2 + ((Q[..., 1] - ridge_y - 0.05) / 0.85) ** 2 + (Q[..., 2] / 1.0) ** 2) - 0.36
        return d + (fbm3(Q[..., 0] * 2.5, Q[..., 1] * 2.5, Q[..., 2] * 2.5, 2, 9231) - 0.5) * 0.08
    turf = K.sdf_piece(turf_f, (-L - 0.6, ridge_y - 0.45, -0.6), (L + 0.6, ridge_y + 0.5, 0.6), TURF, h=0.045, tris=700,
                       pattern='moss', amount=0.8, var=0.08, seed=9231, mat='roof')

    def turf_shade(Pp, N):
        m = np.ones((len(Pp), 3))
        low = (Pp[:, 1] < ridge_y - 0.05)[:, None]
        return np.where(low, EARTH / TURF, m)
    turf.shade = turf_shade
    P.append(turf)
    for k in range(3):
        x = -L * 0.6 + L * 0.6 * k
        P.append(K.lathe([(0.375, -0.035), (0.385, 0.0), (0.375, 0.035)], K.col('#3a3026'), n=8, R=K.rot_z(math.pi / 2),
                         base=(x, ridge_y + 0.02, 0), var=0.0, cap_top=False, cap_bottom=False))
    for x in (-L - 0.05, L + 0.05):
        for s in (-1, 1):
            a = np.array([x, ridge_y + 0.62, s * 0.2])
            b = np.array([x, ridge_y - 0.15, -s * 0.62])
            P.append(_w(cyl(b, a, 0.04, BEAM, n=4, pattern='bark', amount=0.2), 'bark', 0.2, sd()))
    # the smoke hood (煙出し) over the doma side: a small gabled thatch hat on posts
    hx_ = L * 0.55
    for dx in (-0.32, 0.32):
        for dz in (-0.22, 0.22):
            P.append(_w(cyl((hx_ + dx, ridge_y - 0.1, dz), (hx_ + dx, ridge_y + 0.55, dz), 0.035, BEAM, n=4), 'bark', 0.2, sd()))
    P.append(K.cbox((0.6, 0.35, 0.42), DARK, centre=(hx_, ridge_y + 0.38, 0.0), bevel=0.0, var=0.0, mat='roof'))

    def hood_f(Q):
        q = Q - np.array([hx_, ridge_y + 0.62, 0.0])
        roofp = np.abs(q[..., 2]) * 0.9 + q[..., 1] - 0.3
        slab = np.maximum(roofp, -(roofp + 0.14))
        return np.maximum(slab, K.sd_box(q, (0.55, 0.45, 0.45), 0.05)) + (fbm3(Q[..., 0] * 6, Q[..., 1] * 6, Q[..., 2] * 6, 2, 9233) - 0.5) * 0.03
    P.append(K.sdf_piece(hood_f, (hx_ - 0.65, ridge_y + 0.1, -0.55), (hx_ + 0.65, ridge_y + 1.05, 0.55), THATCH, h=0.035, tris=320,
                         pattern='thatch', amount=0.5, var=0.04, seed=9233, mat='roof', shade=thatch_shade, dirt=False))
    return P, ridge_y, L


# ------------------------------------------------------------------------------------------- the frame
def frame_pieces(R):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))

    def stone(x, z, s=1.0, top=0.12):
        def f(Q, s0=sd()):
            return K.sd_ellipsoid(Q - np.array([0, top * 0.4, 0]), (0.22 * s, top, 0.2 * s)) + K.weathered(Q, 0.02, 0.08, s0)
        return K.sdf_piece(f, (-0.3 * s, -0.1, -0.28 * s), (0.3 * s, top + 0.08, 0.28 * s), STONE * (1 + R.normal(0, 0.05)),
                           h=0.035, tris=40, pattern='stone', amount=0.7, var=0.06, seed=sd()).moved(None, (x, 0, z))
    # foundation stones under the posts (front and the sides' middles; the back is hidden)
    for x in BAYS:
        P.append(stone(x, WZ))
    for x in (-WX, WX):
        P.append(stone(x, 0.0))
    # sills on the stones, the floor beam (足固め) along the front
    P.append(_w(K.beam((-WX - 0.08, 0.2, WZ), (WX + 0.08, 0.2, WZ), 0.16, 0.14, POST), 'bark', 0.3, sd()))
    P.append(_w(K.beam((-WX - 0.08, 0.2, -WZ), (WX + 0.08, 0.2, -WZ), 0.16, 0.14, POST), 'bark', 0.3, sd()))
    for x in (-WX, WX):
        P.append(_w(K.beam((x, 0.2, -WZ - 0.08), (x, 0.2, WZ + 0.08), 0.16, 0.14, POST), 'bark', 0.3, sd()))
    P.append(_w(K.beam((-WX, FLOOR - 0.06, WZ + 0.005), (WX, FLOOR - 0.06, WZ + 0.005), 0.12, 0.12, BEAM), 'bark', 0.3, sd()))
    # posts: front row, back corners, side middles; hand-hewn, a little uneven
    for x in BAYS:
        P.append(_w(K.cbox((0.17, PLATE - 0.27, 0.17), POST, centre=(x, 0.27 + (PLATE - 0.27) / 2, WZ), bevel=0.02, jitter=0.006,
                           seed=sd()), 'bark', 0.35, sd()))
    for x in (-WX, WX):
        for z in (-WZ, 0.0):
            P.append(_w(K.cbox((0.17, PLATE - 0.27, 0.17), POST, centre=(x, 0.27 + (PLATE - 0.27) / 2, z), bevel=0.02), 'bark', 0.35, sd()))
    # wall plates and the tie beam ends that stick out under the eave
    for z in (-WZ, WZ):
        P.append(_w(K.beam((-WX - 0.3, PLATE, z), (WX + 0.3, PLATE, z), 0.18, 0.22, BEAM), 'bark', 0.3, sd()))
    for x in (-WX, WX):
        P.append(_w(K.beam((x, PLATE + 0.04, -WZ - 0.3), (x, PLATE + 0.04, WZ + 0.3), 0.16, 0.18, BEAM), 'bark', 0.3, sd()))
    # lintels (鴨居) and the sill (敷居) of the openings; the head rail (内法長押) over them
    P.append(_w(K.beam((-WX, LINTEL + 0.03, WZ + 0.01), (WX, LINTEL + 0.03, WZ + 0.01), 0.11, 0.09, POST * 1.05), 'planks', 0.25, sd()))
    P.append(_w(K.beam((-WX, LINTEL + 0.15, WZ + 0.04), (WX, LINTEL + 0.15, WZ + 0.04), 0.05, 0.1, BEAM * 1.06), 'planks', 0.2, sd()))
    P.append(_w(K.beam((-WX, FLOOR + 0.015, WZ + 0.0), (ENG_X1, FLOOR + 0.015, WZ + 0.0), 0.11, 0.04, POST * 1.08), 'planks', 0.2, sd()))
    # the small wall above the lintels (plaster), and the walls of the sides and back
    for x0, x1 in zip(BAYS[:-1], BAYS[1:]):
        P.append(_w(K.cbox((x1 - x0 - 0.17, PLATE - LINTEL - 0.27, 0.06), PLASTER * (1 + R.normal(0, 0.025)),
                           centre=((x0 + x1) / 2, (LINTEL + 0.2 + PLATE - 0.1) / 2, WZ - 0.02), bevel=0.0), 'plain', 0.2, sd()))
        P.append(_w(K.cbox((x1 - x0 - 0.17, PLATE - 0.6, 0.06), PLASTER * 0.96, centre=((x0 + x1) / 2, (0.35 + PLATE) / 2, -WZ + 0.02),
                           bevel=0.0), 'plain', 0.2, sd()))
    for x in (-WX, WX):
        for z0, z1 in ((-WZ + 0.09, -0.09), (0.09, WZ - 0.09)):
            P.append(_w(K.cbox((0.06, 0.7, z1 - z0), BOARD, centre=(x - np.sign(x) * 0.02, 0.62, (z0 + z1) / 2), bevel=0.0), 'planks', 0.4, sd()))
            P.append(_w(K.cbox((0.06, PLATE - 1.1, z1 - z0), PLASTER * (1 + R.normal(0, 0.025)),
                               centre=(x - np.sign(x) * 0.02, (0.97 + PLATE) / 2, (z0 + z1) / 2), bevel=0.0), 'plain', 0.2, sd()))
    # rafter ends showing under the front eave, and the purlin at their feet
    for k in range(17):
        xx = -HW + 0.25 + k * (2 * HW - 0.5) / 16
        P.append(_w(K.beam((xx, PLATE + 0.1, WZ - 0.25), (xx, PLATE + 0.75, HD - 0.3), 0.07, 0.07, POST * 0.92, bevel=0.0), 'bark', 0.3, sd()))
    return P


# ------------------------------------------------------------------------------------------- engawa
def engawa_pieces(R):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))
    # the deck: tilted 1 degree toward the front (rain runs off; the board pattern runs along x)
    tilt = 0.015
    d = ENG_Z1 - ENG_Z0
    pts = []
    for x in (ENG_X0, ENG_X1):
        for z, dy in ((ENG_Z0, 0.0), (ENG_Z1, -tilt * d)):
            pts += [(x, FLOOR + dy, z), (x, FLOOR + dy - 0.06, z)]
    P.append(_w(K.convex(pts, DECK), 'planks', 0.45, sd()))
    # the edge beam (縁框), worn lighter on top
    P.append(_w(K.beam((ENG_X0 - 0.05, FLOOR - 0.045 - tilt * d, ENG_Z1 + 0.02), (ENG_X1 + 0.05, FLOOR - 0.045 - tilt * d, ENG_Z1 + 0.02),
                       0.1, 0.11, DECK * 0.92), 'planks', 0.3, sd()))
    # short posts on stones under it
    for x in (ENG_X0 + 0.15, -2.0, -0.1, ENG_X1 - 0.15):
        P.append(_w(K.cbox((0.09, FLOOR - 0.16, 0.09), POST, centre=(x, (FLOOR - 0.1) / 2 + 0.04, ENG_Z1 - 0.06), bevel=0.01), 'bark', 0.3, sd()))

        def f(Q, s0=sd()):
            return K.sd_ellipsoid(Q - np.array([0, 0.03, 0]), (0.13, 0.08, 0.12)) + K.weathered(Q, 0.012, 0.06, s0)
        P.append(K.sdf_piece(f, (-0.18, -0.06, -0.17), (0.18, 0.12, 0.17), STONE, h=0.03, tris=30, pattern='stone', amount=0.6,
                             var=0.06, seed=sd()).moved(None, (x, 0, ENG_Z1 - 0.06)))
    # the dark gap under the deck
    P.append(K.cbox((ENG_X1 - ENG_X0 - 0.1, FLOOR - 0.2, 0.03), DARK, centre=((ENG_X0 + ENG_X1) / 2, (FLOOR - 0.2) / 2 + 0.1, ENG_Z1 - 0.2),
                    bevel=0.0, var=0.0, ao=False))
    # the step stone (沓脱石) and the geta on it
    def step_f(Q):
        return K.sd_box(Q - np.array([0, 0.14, 0]), (0.38, 0.14, 0.24), 0.07) + K.weathered(Q, 0.015, 0.1, 9260)
    P.append(K.sdf_piece(step_f, (-0.45, -0.05, -0.3), (0.45, 0.32, 0.3), STONE * 1.04, h=0.03, tris=160, pattern='stone',
                         amount=0.5, var=0.05, seed=9260).moved(None, (-1.15, 0, ENG_Z1 + 0.38)))
    for dx, rot in ((-0.1, 0.12), (0.1, -0.05)):
        g = [_w(K.cbox((0.1, 0.025, 0.22), K.col('#9c8462'), centre=(0, 0.06, 0), bevel=0.005), 'planks', 0.2, 9261),
             K.cbox((0.08, 0.035, 0.03), K.col('#3a2f26'), centre=(0, 0.03, 0.06), bevel=0.0),
             K.cbox((0.08, 0.035, 0.03), K.col('#3a2f26'), centre=(0, 0.03, -0.06), bevel=0.0),
             K.cbox((0.012, 0.012, 0.012), K.col('#8a2a20'), centre=(0, 0.08, 0.07), bevel=0.0)]
        P += [p.moved(K.rot_y(rot), (-1.15 + dx, 0.28, ENG_Z1 + 0.36)) for p in g]
    return P


# ------------------------------------------------------------------------------------------- shoji, interior
def shoji(x0, x1, z, R, open_side=0):
    """A pair of shoji between two posts (x0, x1). open_side -1 / 1: the left / right panel slid over
    the other, leaving that half open. Paper in the shoji material, the frame and the kumiko lattice
    (bars exactly one native pixel wide) in wood; a board at the foot (腰板)."""
    P = []
    y0, y1 = FLOOR + 0.03, LINTEL - 0.02
    half = (x1 - x0 - 0.17) / 2
    a = x0 + 0.085
    panels = [(a, a + half, 0.0), (a + half, a + 2 * half, 0.02)]
    if open_side == -1:
        panels = [(a + half, a + 2 * half, 0.0), (a + half - 0.03, a + 2 * half - 0.03, 0.025)]
    elif open_side == 1:
        panels = [(a, a + half, 0.0), (a + 0.03, a + half + 0.03, 0.025)]
    for (px0, px1, dz) in panels:
        zz = z + 0.03 + dz
        st = 0.035
        P.append(_w(bar(px0, px0 + st, y0, y1, zz, KUMIKO * 0.92, 0.035), 'planks', 0.15, 9270))
        P.append(_w(bar(px1 - st, px1, y0, y1, zz, KUMIKO * 0.92, 0.035), 'planks', 0.15, 9270))
        P.append(_w(bar(px0, px1, y1 - 0.035, y1, zz, KUMIKO * 0.92, 0.035), 'planks', 0.15, 9270))
        P.append(_w(bar(px0, px1, y0, y0 + 0.24, zz, BOARD * 1.1, 0.03), 'planks', 0.3, 9271))
        paper = bar(px0 + st, px1 - st, y0 + 0.24, y1 - 0.035, zz - 0.012, PAPER, 0.012, mat='shoji', pattern='paper', amount=0.2)
        paper.ao = False
        P.append(paper)
        # kumiko: 4 uprights, 5 rails; one pixel wide
        w_ = px1 - px0 - 2 * st
        for k in range(1, 4):
            xx = px0 + st + w_ * k / 4
            P.append(bar(xx - PX / 2, xx + PX / 2, y0 + 0.24, y1 - 0.035, zz + 0.004, KUMIKO, 0.012))
        hgt = (y1 - 0.035) - (y0 + 0.24)
        for k in range(1, 6):
            yy = y0 + 0.24 + hgt * k / 6
            P.append(bar(px0 + st, px1 - st, yy - PX / 2, yy + PX / 2, zz + 0.004, KUMIKO, 0.012))
    # the open half: darkness behind
    if open_side:
        ox0 = a if open_side == -1 else a + half
        P.append(bar(ox0 + 0.02, ox0 + half - 0.02, y0, y1, z - 0.08, DARK, 0.02, ao=False))
    return P


def interior_pieces(R):
    """Seen through the open shoji of the second bay: tatami with their dark green borders, a low
    table with a teapot, a brazier (火鉢) whose charcoal glows at night (lit material; anchors.light)."""
    P = []
    x0, x1 = -1.9, 0.0
    # tatami: two mats lengthwise along x, borders as strips
    P.append(_w(K.cbox((x1 - x0 + 0.4, 0.04, 2.0), TATAMI, centre=((x0 + x1) / 2, FLOOR - 0.01, WZ - 1.05), bevel=0.0), 'planks', 0.15, 9280))
    for zz in (WZ - 0.12, WZ - 1.02, WZ - 1.92):
        P.append(K.cbox((x1 - x0 + 0.4, 0.045, 0.045), TATAMI_EDGE, centre=((x0 + x1) / 2, FLOOR - 0.005, zz), bevel=0.0, var=0.0))
    # the dim back of the room
    P.append(bar(x0 - 0.2, x1 + 0.2, FLOOR, PLATE, WZ - 2.1, K.col('#2a231d'), 0.04))
    # a low round table (ちゃぶ台) with a teapot and a cup
    P.append(K.lathe([(0.0, 0.0), (0.36, 0.0), (0.36, 0.035), (0.0, 0.035)], K.col('#6a4a34'), n=12,
                     base=(-1.25, FLOOR + 0.28, WZ - 0.75), pattern='planks', amount=0.2))
    for dx, dz in ((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)):
        P.append(K.cbox((0.04, 0.28, 0.04), K.col('#4a3426'), centre=(-1.25 + dx, FLOOR + 0.14, WZ - 0.75 + dz), bevel=0.0))
    P.append(K.lathe([(0.0, 0.0), (0.07, 0.0), (0.085, 0.05), (0.07, 0.1), (0.03, 0.12), (0.0, 0.12)], K.col('#5c6a72'), n=8,
                     base=(-1.35, FLOOR + 0.315, WZ - 0.8)))
    P.append(K.lathe([(0.0, 0.0), (0.03, 0.0), (0.035, 0.05), (0.0, 0.05)], K.col('#d8d0bc'), n=6, base=(-1.12, FLOOR + 0.315, WZ - 0.66)))
    # the brazier
    hb = (-0.62, FLOOR, WZ - 0.55)
    P.append(K.lathe([(0.0, 0.0), (0.2, 0.0), (0.24, 0.12), (0.22, 0.26), (0.19, 0.27), (0.0, 0.27)], K.col('#4c5a64'), n=10,
                     base=hb, pattern='plain', amount=0.0))
    P.append(K.lathe([(0.0, 0.0), (0.17, 0.0), (0.17, 0.01), (0.0, 0.01)], K.col('#8a847a'), n=10, base=(hb[0], hb[1] + 0.25, hb[2])))
    emb = K.lathe([(0.0, 0.0), (0.07, 0.0), (0.06, 0.04), (0.0, 0.05)], K.col('#e06a2a'), n=7, base=(hb[0], hb[1] + 0.25, hb[2]),
                  mat='lit', ao=False, dirt=False)
    P.append(emb)
    P.append(K.lathe([(0.0, 0.0), (0.09, 0.0), (0.11, 0.07), (0.09, 0.14), (0.03, 0.16), (0.0, 0.16)], IRON, n=8,
                     base=(hb[0], hb[1] + 0.33, hb[2])))
    return P, (hb[0], hb[1] + 0.35, hb[2])


def doma_pieces(R):
    """The east bay: the doma's wide opening, dark inside, a threshold stone, an indigo noren that
    swings with the wind (three panels with a white wave mark), the sliding door pushed aside."""
    P = []
    x0, x1 = 1.9 + 0.1, 3.8 - 0.1
    P.append(bar(x0, x1, 0.12, LINTEL, WZ - 0.7, DARK, 0.03, ao=False))
    # the doma floor just inside (beaten earth) and the threshold stone
    P.append(K.cbox((x1 - x0, 0.06, 0.8), K.col('#5a4e40'), centre=((x0 + x1) / 2, 0.1, WZ - 0.5), bevel=0.0, var=0.0))

    def thr(Q):
        return K.sd_box(Q - np.array([0, 0.08, 0]), (0.8, 0.08, 0.17), 0.04) + K.weathered(Q, 0.012, 0.1, 9290)
    P.append(K.sdf_piece(thr, (-0.9, -0.05, -0.22), (0.9, 0.2, 0.22), STONE, h=0.03, tris=160, pattern='stone', amount=0.4,
                         var=0.05, seed=9290).moved(None, ((x0 + x1) / 2, 0, WZ + 0.12)))
    # noren: three panels from a rod under the lintel; each sways from the rod
    rod_y = LINTEL - 0.02
    P.append(_w(cyl((x0 - 0.05, rod_y, WZ + 0.14), (x1 + 0.05, rod_y, WZ + 0.14), 0.015, BAMBOO, n=4), 'plain', 0.0, 9291))
    w = (x1 - x0) / 3
    for k in range(3):
        a = x0 + k * w + 0.012
        b = a + w - 0.024
        top = rod_y - 0.02
        for j, (ya, yb, flex) in enumerate(((top, top - 0.32, 0.35), (top - 0.32, top - 0.62, 0.8))):
            pc = bar(a, b, yb, ya, WZ + 0.15, INDIGO * (1.0 + 0.04 * k), 0.012, pattern='plain', amount=0.0)
            pc.swaying(((a + b) / 2, top, WZ + 0.15), flex)
            P.append(pc)
            if j == 1:
                # the white mark: a wave crest across the three panels
                yy = top - 0.46 + 0.04 * math.sin(k * 2.1)
                m = bar(a + 0.06, b - 0.06, yy - 0.035, yy + 0.035, WZ + 0.158, K.col('#e6e2d6'), 0.006, pattern='plain', amount=0.0)
                m.swaying(((a + b) / 2, top, WZ + 0.15), flex)
                P.append(m)
    return P


def sudare(x0, x1, z, R):
    """A reed blind half down in front of the third bay: horizontal reeds (one pixel rows in two
    tones), cloth binding, the rolled part and the cords."""
    P = []
    top, bottom = LINTEL + 0.35, FLOOR + 0.95
    reed_a, reed_b = K.col('#b8a26e'), K.col('#a08a58')
    y = bottom
    k = 0
    while y < top - 0.06:
        h = PX * (1 if k % 3 else 2)
        pc = bar(x0, x1, y, y + h, z, reed_a if k % 2 else reed_b, 0.012, pattern='plain', amount=0.0)
        pc.swaying(((x0 + x1) / 2, top, z), 0.25, mat='swaynl')
        P.append(pc)
        y += h
        k += 1
    for xx in (x0, x1 - 0.03):
        pc = bar(xx, xx + 0.03, bottom, top, z + 0.004, K.col('#3c4a3a'), 0.014, pattern='plain', amount=0.0)
        pc.swaying(((x0 + x1) / 2, top, z), 0.25, mat='swaynl')
        P.append(pc)
    roll = cyl((x0, bottom - 0.03, z + 0.01), (x1, bottom - 0.03, z + 0.01), 0.05, reed_b, n=6)
    roll.swaying(((x0 + x1) / 2, top, z), 0.25, mat='swaynl')
    P.append(roll)
    P.append(_w(cyl((x0 - 0.04, top, z), (x1 + 0.04, top, z), 0.018, BEAM, n=4), 'plain', 0.0, 9300))
    return P


# ------------------------------------------------------------------------------------------- the lean-to
def geya_pieces(R):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))
    hf = G_ROOF_FRONT - 0.12
    # posts and walls of vertical boards, a door and a barred window in front
    for x in (GX0, (GX0 + GX1) / 2):
        P.append(_w(K.cbox((0.13, hf, 0.13), POST, centre=(x, hf / 2, GZ1), bevel=0.015), 'bark', 0.3, sd()))
    P.append(_w(K.cbox((0.13, G_ROOF_BACK - 0.1, 0.13), POST, centre=(GX0, (G_ROOF_BACK - 0.1) / 2, GZ0), bevel=0.015), 'bark', 0.3, sd()))
    boards = []
    x = GX0 + 0.07
    door = (GX0 + 0.3, GX0 + 1.05)
    win = (GX1 - 0.95, GX1 - 0.3)
    while x < GX1 - 0.05:
        wb = R.uniform(0.17, 0.24)
        xb = min(x + wb, GX1 - 0.05)
        c = BOARD_OLD * (1 + R.normal(0, 0.05))
        if door[0] <= x < door[1]:
            pass
        elif win[0] <= x < win[1]:
            P.append(_w(K.cbox((xb - x - 0.008, 0.95, 0.04), c, centre=((x + xb) / 2, 0.55, GZ1 - 0.01), bevel=0.0), 'planks', 0.35, sd()))
            P.append(_w(K.cbox((xb - x - 0.008, hf - 1.62, 0.04), c, centre=((x + xb) / 2, (1.62 + hf) / 2, GZ1 - 0.01), bevel=0.0), 'planks', 0.35, sd()))
        else:
            P.append(_w(K.cbox((xb - x - 0.008, hf - 0.1, 0.04), c, centre=((x + xb) / 2, (hf + 0.1) / 2, GZ1 - 0.01), bevel=0.0), 'planks', 0.35, sd()))
        x = xb
    # the board door (closed), its frame
    P.append(_w(K.cbox((door[1] - door[0], 1.72, 0.045), BOARD * 1.06, centre=((door[0] + door[1]) / 2, 0.92, GZ1 + 0.005), bevel=0.0), 'planks', 0.45, sd()))
    for yy in (0.35, 1.0, 1.6):
        P.append(_w(K.cbox((door[1] - door[0] - 0.04, 0.06, 0.03), POST, centre=((door[0] + door[1]) / 2, yy, GZ1 + 0.035), bevel=0.0), 'bark', 0.2, sd()))
    P.append(_w(K.cbox((door[1] - door[0] + 0.12, 0.07, 0.07), POST, centre=((door[0] + door[1]) / 2, 1.82, GZ1 + 0.01), bevel=0.0), 'bark', 0.2, sd()))
    # the window: dark, with square bars (連子)
    P.append(bar(win[0], win[1], 1.0, 1.62, GZ1 - 0.06, DARK, 0.02, ao=False))
    for k in range(6):
        xx = win[0] + 0.04 + k * (win[1] - win[0] - 0.08) / 5
        P.append(_w(K.cbox((0.035, 0.62, 0.035), BOARD * 1.1, centre=(xx, 1.31, GZ1 + 0.005), bevel=0.0), 'planks', 0.2, sd()))
    P.append(_w(K.cbox((win[1] - win[0] + 0.1, 0.06, 0.06), POST, centre=((win[0] + win[1]) / 2, 0.97, GZ1 + 0.01), bevel=0.0), 'bark', 0.2, sd()))
    P.append(_w(K.cbox((win[1] - win[0] + 0.1, 0.06, 0.06), POST, centre=((win[0] + win[1]) / 2, 1.65, GZ1 + 0.01), bevel=0.0), 'bark', 0.2, sd()))
    # the roof: boards sloping south, held down by battens and river stones (石置き屋根)
    zf, zb = GZ1 + 0.45, GZ0 - 0.25
    x0r, x1r = GX0 - 0.3, GX1 + 0.35
    slope = (G_ROOF_BACK - G_ROOF_FRONT) / (zf - zb)

    def ry(z):
        return G_ROOF_FRONT + (zf - z) * slope
    xx = x0r
    while xx < x1r - 0.02:
        wb = R.uniform(0.2, 0.28)
        xb = min(xx + wb, x1r)
        c = BOARD_OLD * (0.92 + R.normal(0, 0.05))
        pts = []
        for x_ in (xx + 0.004, xb - 0.004):
            for z_ in (zf, zb):
                y_ = ry(z_) + R.normal(0, 0.006)
                pts += [(x_, y_, z_), (x_, y_ - 0.035, z_)]
        P.append(_w(K.convex(pts, c), 'planks', 0.35, sd()))
        xx = xb
    for z_ in (zf - 0.35, (zf + zb) / 2 + 0.2, zb + 0.5):
        P.append(_w(K.beam((x0r - 0.05, ry(z_) + 0.035, z_), (x1r + 0.05, ry(z_) + 0.035, z_), 0.07, 0.05, BEAM), 'bark', 0.3, sd()))
        n = int((x1r - x0r) / 0.42)
        for k in range(n):
            if R.uniform() < 0.15:
                continue
            sx = x0r + 0.2 + k * (x1r - x0r - 0.4) / max(n - 1, 1) + R.normal(0, 0.04)

            def f(Q, s0=sd()):
                return K.sd_ellipsoid(Q, (0.11, 0.07, 0.09)) + K.weathered(Q, 0.01, 0.05, s0)
            P.append(K.sdf_piece(f, (-0.14, -0.09, -0.12), (0.14, 0.09, 0.12), STONE * (1 + R.normal(0, 0.06)), h=0.03, tris=24,
                                 pattern='stone', amount=0.8, var=0.05, seed=sd()).moved(K.rot_y(R.uniform(0, 3)),
                                                                                          (sx, ry(z_) + 0.08, z_ + 0.07)))
    # the chimney of the kitchen range: plastered, soot at the top, a little cap
    cx, cz = GX0 + 0.75, -0.55
    top = 3.95
    P.append(_w(K.cbox((0.34, top - 1.4, 0.34), PLASTER * 0.92, centre=(cx, (top + 1.4) / 2, cz), bevel=0.02, jitter=0.006, seed=9310),
                'plain', 0.2, 9310))
    P.append(K.cbox((0.36, 0.22, 0.36), K.col('#4a443e'), centre=(cx, top - 0.1, cz), bevel=0.015))
    for s in (-1, 1):
        P.append(_w(K.convex([(cx - 0.28, top + 0.08, cz), (cx + 0.28, top + 0.08, cz), (cx - 0.28, top + 0.08, cz + s * 0.3),
                              (cx + 0.28, top + 0.08, cz + s * 0.3), (cx - 0.28, top + 0.2, cz), (cx + 0.28, top + 0.2, cz),
                              (cx - 0.28, top + 0.03, cz + s * 0.3), (cx + 0.28, top + 0.03, cz + s * 0.3)], K.col('#5a524a')),
                    'planks', 0.2, 9311))
    for dx in (-0.12, 0.12):
        P.append(K.cbox((0.03, 0.1, 0.03), K.col('#3a342e'), centre=(cx + dx, top + 0.02, cz), bevel=0.0))
    return P, (cx, top + 0.15, cz)


# ------------------------------------------------------------------------------------------- hanging things
def hangings(R):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))
    # onions tied in bunches by their dried tops, hanging from a bamboo pole under the eave of the first bay
    pole_y = 2.55
    pz = ENG_Z1 - 0.12
    P.append(_w(cyl((-3.55, pole_y, pz), (-2.25, pole_y, pz), 0.02, BAMBOO, n=4), 'plain', 0.0, sd()))
    onion = K.col('#b8864a')
    tops = K.col('#a89660')
    for k in range(4):
        x = -3.38 + k * 0.32 + R.normal(0, 0.02)
        drop = R.uniform(0.18, 0.3)
        knot = (x, pole_y - drop, pz)
        stalk = cyl((x, pole_y, pz), knot, 0.014, tops, n=4)
        stalk.swaying((x, pole_y, pz), 0.35)
        P.append(stalk)
        n_on = int(R.integers(5, 9))
        for j in range(n_on):
            a = j * 2.4 + R.normal(0, 0.3)
            rr = 0.03 + 0.02 * (j % 3)
            cy = knot[1] - 0.07 - 0.05 * (j // 3) - R.uniform(0.0, 0.03)
            c = onion * R.uniform(0.82, 1.12)
            ob = K.lathe([(0.0, -0.035), (0.03, -0.028), (0.04, 0.0), (0.03, 0.026), (0.008, 0.045), (0.0, 0.05)], c, n=6,
                         base=(x + math.cos(a) * rr, cy, pz + 0.02 + math.sin(a) * rr * 0.6), pattern='plain', amount=0.0, var=0.05, seed=sd())
            ob.swaying((x, pole_y, pz), 0.4)
            P.append(ob)
            neck = cyl((x + math.cos(a) * rr * 0.6, cy + 0.045, pz + 0.02), knot, 0.006, tops, n=3)
            neck.swaying((x, pole_y, pz), 0.4)
            P.append(neck)
    # two bon lanterns (盆提灯, gifu style): egg-shaped paper with bellflowers painted, black lacquer
    # caps, a tassel; hung from the engawa's beam to light the dead home at Obon (paper glows after dusk)
    for bx in (-1.95, 1.05):
        by = LINTEL + 0.62
        bz = ENG_Z1 - 0.28
        P.append(cyl((bx, by + 0.42, bz), (bx, by + 0.17, bz), 0.004, K.col('#3a3030'), n=3))
        cap = K.lathe([(0.0, 0.0), (0.05, 0.0), (0.055, 0.025), (0.0, 0.03)], K.col('#2a2224'), n=8, base=(bx, by + 0.15, bz), var=0.0)
        cap.swaying((bx, by + 0.42, bz), 0.15)
        P.append(cap)
        body = K.lathe([(0.0, -0.14), (0.055, -0.13), (0.095, -0.06), (0.1, 0.0), (0.09, 0.07), (0.05, 0.13), (0.0, 0.14)],
                       K.col('#e8e4d8'), n=12, base=(bx, by, bz), mat='shoji', pattern='paper', amount=0.15, var=0.0)

        def flowers(Pp, N, bx=bx, by=by, bz=bz):
            a = np.arctan2(Pp[:, 2] - bz, Pp[:, 0] - bx)
            m = np.ones((len(Pp), 3))
            blue = (np.sin(a * 5.0 + 1.0) > 0.55) & (np.abs(Pp[:, 1] - by) < 0.07)
            m[blue] = np.array([0.62, 0.62, 0.86])
            leaf = (np.sin(a * 5.0 + 2.2) > 0.75) & (Pp[:, 1] - by < -0.03) & (Pp[:, 1] - by > -0.1)
            m[leaf] = np.array([0.66, 0.78, 0.62])
            return m
        body.shade = flowers
        P.append(body)
        foot = K.lathe([(0.0, -0.03), (0.045, -0.03), (0.05, 0.0), (0.0, 0.0)], K.col('#2a2224'), n=8, base=(bx, by - 0.14, bz), var=0.0)
        P.append(foot)
        tassel = K.cbox((0.03, 0.16, 0.03), K.col('#6a4a7a'), centre=(bx, by - 0.26, bz), bevel=0.0, var=0.0)
        tassel.swaying((bx, by - 0.17, bz), 0.6)
        P.append(tassel)
    # red peppers from the east post of the doma
    for k in range(3):
        x = 3.92 + k * 0.07
        for j in range(5):
            y = 2.2 - j * 0.09 - k * 0.03
            ch = K.cbox((0.035, 0.09, 0.03), CHILLI * (0.9 + 0.2 * R.uniform()), centre=(x, y, WZ + 0.12), bevel=0.0, R=K.rot_z(R.normal(0, 0.3)))
            ch.swaying((x, 2.3, WZ + 0.12), 0.4)
            P.append(ch)
    # the wind chime at the engawa's east end
    fx, fy, fz = ENG_X1 - 0.12, 2.42, ENG_Z1 - 0.05
    bell = K.lathe([(0.0, 0.0), (0.06, 0.0), (0.058, 0.05), (0.04, 0.09), (0.0, 0.1)], K.col('#a8d0d0'), n=8, base=(fx, fy - 0.13, fz),
                   pattern='plain', amount=0.0, var=0.0)
    bell.swaying((fx, fy, fz), 0.25)
    P.append(bell)
    P.append(cyl((fx, fy - 0.03, fz), (fx, fy, fz), 0.004, K.col('#3a3a3a'), n=3))
    strip = bar(fx - 0.035, fx + 0.035, fy - 0.43, fy - 0.17, fz, K.col('#d8504a'), 0.006, pattern='paper', amount=0.1)
    strip.swaying((fx, fy - 0.15, fz), 1.0)
    P.append(strip)
    clap = cyl((fx, fy - 0.17, fz), (fx, fy - 0.13, fz), 0.004, K.col('#3a3a3a'), n=3)
    clap.swaying((fx, fy - 0.15, fz), 1.0)
    P.append(clap)
    # straw raincoat (蓑) and sedge hat (笠) on the lean-to wall
    mx, my, mz = GX1 - 1.35, 1.65, GZ1 + 0.05

    def mino(Q):
        q = Q - np.array([mx, my - 0.42, mz + 0.06])
        r = 0.16 + (0.42 - q[..., 1]) * 0.28
        d = np.sqrt((q[..., 0] / np.maximum(r, 0.05)) ** 2 + (q[..., 2] / 0.12) ** 2) - 1.0
        d = np.maximum(d * 0.12, np.abs(q[..., 1]) - 0.42)
        return d + (fbm3(Q[..., 0] * 14, Q[..., 1] * 3, Q[..., 2] * 14, 2, 9320) - 0.5) * 0.035
    P.append(K.sdf_piece(mino, (mx - 0.5, my - 0.95, mz - 0.1), (mx + 0.5, my + 0.05, mz + 0.25), STRAW * 0.92, h=0.025, tris=320,
                         pattern='thatch', amount=0.4, var=0.05, seed=9320))
    P.append(K.lathe([(0.0, 0.0), (0.25, 0.0), (0.0, 0.14)], STRAW * 1.05, n=10, R=K.rot_x(-1.25), base=(mx + 0.55, 1.85, mz + 0.08),
                     pattern='thatch', amount=0.3))
    return P


def engawa_things(R):
    P = []
    y = FLOOR - 0.005
    # a tray with a teapot and two cups, a round fan, a mosquito-coil pig
    tx, tz = -0.75, ENG_Z0 + 0.42
    P.append(_w(K.cbox((0.36, 0.025, 0.24), K.col('#5a3a26'), centre=(tx, y + 0.012, tz), bevel=0.006), 'planks', 0.2, 9330))
    P.append(K.lathe([(0.0, 0.0), (0.06, 0.0), (0.075, 0.04), (0.06, 0.09), (0.025, 0.1), (0.0, 0.1)], K.col('#7a8a80'), n=8, base=(tx - 0.08, y + 0.025, tz)))
    for dx in (0.06, 0.12):
        P.append(K.lathe([(0.0, 0.0), (0.028, 0.0), (0.032, 0.045), (0.0, 0.045)], K.col('#e2dccb'), n=6, base=(tx + dx, y + 0.025, tz + 0.04)))
    fan = K.lathe([(0.0, 0.0), (0.11, 0.0), (0.11, 0.008), (0.0, 0.008)], K.col('#e8e2d0'), n=10, base=(-0.12, y, ENG_Z0 + 0.55))
    P.append(fan)
    P.append(K.cbox((0.02, 0.008, 0.12), K.col('#a08a5a'), centre=(-0.12, y + 0.004, ENG_Z0 + 0.71), bevel=0.0))
    P.append(K.cbox((0.12, 0.012, 0.03), K.col('#c04a3a'), centre=(-0.12, y + 0.009, ENG_Z0 + 0.53), bevel=0.0))
    pig = (1.45, y, ENG_Z0 + 0.5)
    P.append(K.lathe([(0.0, -0.08), (0.06, -0.075), (0.08, 0.0), (0.06, 0.075), (0.0, 0.08)], K.col('#7a7a74'), n=8,
                     R=K.rot_x(math.pi / 2) @ K.rot_y(0.3), base=(pig[0], pig[1] + 0.08, pig[2])))
    P.append(K.lathe([(0.0, 0.0), (0.035, 0.0), (0.035, 0.012), (0.0, 0.012)], K.col('#3a3634'), n=6, R=K.rot_x(math.pi / 2),
                     base=(pig[0] + 0.02, pig[1] + 0.08, pig[2] + 0.085)))
    for dx in (-0.04, 0.04):
        for dz in (-0.04, 0.04):
            P.append(K.cbox((0.02, 0.03, 0.02), K.col('#6a6a64'), centre=(pig[0] + dx, pig[1] + 0.015, pig[2] + dz), bevel=0.0))
    # a cushion (座布団) by the open shoji
    P.append(_w(K.cbox((0.42, 0.05, 0.4), K.col('#7a3a34'), centre=(-1.6, y + 0.025, ENG_Z0 + 0.4), bevel=0.02), 'plain', 0.1, 9331))
    return P


def drip_line(R):
    """雨落ち: a line of pebbles where the rain comes off the front eave (and the lean-to's)."""
    P = []
    for x0, x1, z, y0 in ((-HW + 0.25, HW - 0.25, HD + 0.1, 0.0), (GX0 - 0.25, GX1 - 0.2, GZ1 + 0.55, 0.0)):
        n = int((x1 - x0) / 0.16)
        for k in range(n):
            x = x0 + (k + R.uniform(0.1, 0.9)) * (x1 - x0) / n
            z_ = z + R.normal(0, 0.06)
            s = R.uniform(0.6, 1.1)

            def f(Q, s0=int(R.integers(0, 1 << 20)), s=s):
                return K.sd_ellipsoid(Q, (0.065 * s, 0.03 * s, 0.055 * s)) + K.weathered(Q, 0.006, 0.03, s0)
            P.append(K.sdf_piece(f, (-0.09, -0.04, -0.08), (0.09, 0.04, 0.08), STONE * (0.9 + 0.2 * R.uniform()), h=0.02, tris=16,
                                 pattern='stone', amount=0.4, var=0.05, seed=int(R.integers(0, 1 << 20))).moved(K.rot_y(R.uniform(0, 3)), (x, 0.0, z_)))
    return P


def pot(x, z, R):
    """A morning-glory pot: glazed, three bamboo canes tied at the top (the vine is cards)."""
    P = [K.lathe([(0.0, 0.0), (0.12, 0.0), (0.16, 0.18), (0.17, 0.2), (0.0, 0.2)], K.col('#5a4a3e'), n=9, base=(x, 0, z),
                 pattern='plain', amount=0.0)]
    P.append(K.lathe([(0.0, 0.0), (0.15, 0.0), (0.15, 0.01), (0.0, 0.01)], EARTH, n=9, base=(x, 0.18, z)))
    for a in (0.3, 2.4, 4.4):
        P.append(cyl((x + math.cos(a) * 0.1, 0.15, z + math.sin(a) * 0.1), (x, 1.15, z), 0.008, BAMBOO, n=3))
    return P


# ------------------------------------------------------------------------------------------- cards
def card_layer(a, R, ridge_y, L):
    """The plants on the turf ridge and the morning glories on their canes: one foliage card surface."""
    specs = {
        'grass': [(FL.tuft, dict(W=int(10 + 2 * (i % 3)), H=int(9 + (i % 2) * 3), seed=9400 + i, family='grass')) for i in range(4)],
        'iris': [(FL.iris, dict(W=10, H=int(14 + i * 2), seed=9410 + i)) for i in range(3)],
        'lily': [(FL.lily, dict(W=10, H=int(20 + i * 3), seed=9420 + i)) for i in range(2)],
        'vine': [(FL.vine_leaves, dict(W=int(12 + i * 2), H=int(14 + (i % 2) * 6), seed=9430 + i, flowers=2 + i % 2)) for i in range(4)],
    }
    atlas, rects, sets = FO.build_tiles(specs, width=128)
    tex = a.texture('cards', atlas)
    mat = a.material('cards', 'toon_foliage_noline.gdshader', params=FO.foliage_params(wind_px=1.5, cutaway=False), textures={'leaf_tex': tex})
    cards = []
    # the ridge: a row of tufts, iris fans, two lilies
    n = int(2 * L / 0.22)
    for k in range(n):
        x = -L + 0.1 + (2 * L - 0.2) * (k + R.uniform(0.2, 0.8)) / n
        r = R.uniform()
        kind = 'iris' if r < 0.3 else ('lily' if r < 0.36 else 'grass')
        t = sets[kind][int(R.integers(0, len(sets[kind])))]
        z = R.normal(0, 0.12)
        p = np.array([x, ridge_y + 0.3 + t[2] / 30.0 * 0.5, z])
        nrm = normalize(np.array([R.normal(0, 0.2), 1.0, 0.6]))
        tint = np.clip(np.array([1.0, 1.0, 1.0]) * (0.92 + 0.12 * R.uniform()), 0, 1)
        cards.append(CD.Card(p, nrm, t[1], t[2], t[0], 0.95, tint, 0.9, 'plant', 1.0))
    # morning glories climbing the canes of the two pots
    for (px, pz) in ((ENG_X0 + 0.15, ENG_Z1 + 0.45), (ENG_X1 + 0.35, ENG_Z1 + 0.45)):
        for j in range(4):
            t = sets['vine'][int(R.integers(0, 4))]
            h = 0.35 + j * 0.22
            p = np.array([px + R.normal(0, 0.05), h, pz + R.normal(0, 0.03)])
            cards.append(CD.Card(p, normalize(np.array([0.0, 0.6, 1.0])), t[1], t[2], t[0], 0.9, np.array([1.0, 1.0, 1.0]), 0.5, 'plant', 1.0))
    md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    return [(mat, md)]


def build(out):
    R = rng(9200)
    pieces = frame_pieces(R)
    pieces.append(thatch_piece())
    rp, ridge_y, L = ridge_pieces(R)
    pieces += rp
    pieces += engawa_pieces(R)
    pieces += shoji(BAYS[0], BAYS[1], WZ, R)
    pieces += shoji(BAYS[1], BAYS[2], WZ, R, open_side=-1)
    pieces += shoji(BAYS[2], BAYS[3], WZ, R)
    inter, brazier = interior_pieces(R)
    pieces += inter
    pieces += doma_pieces(R)
    pieces += sudare(BAYS[2] + 0.12, BAYS[3] - 0.12, WZ + 0.2, R)
    gp, smoke = geya_pieces(R)
    pieces += gp
    pieces += hangings(R)
    pieces += engawa_things(R)
    pieces += drip_line(R)
    pieces += pot(ENG_X0 + 0.15, ENG_Z1 + 0.45, R)
    pieces += pot(ENG_X1 + 0.35, ENG_Z1 + 0.45, R)
    prop = K.Prop('hut', 9200).add(pieces)
    # the house takes over the catalog name 'hut' (the assembly places 'hut' at the hut marker and the
    # view from the lookout bakes it by that name)
    a = out.asset('hut', 'buildings')
    cards = card_layer(a, R, ridge_y, L)
    # the doma's sliding door (pushed aside behind the third bay's wall, its edge showing)
    door = K.Prop('door', 9240).add([_w(K.cbox((0.9, 1.85, 0.05), BOARD * 1.04, centre=(0, 0.92, 0), bevel=0.0), 'planks', 0.45, 9240),
                                     _w(K.cbox((0.86, 0.06, 0.03), POST, centre=(0, 0.5, 0.035), bevel=0.0), 'bark', 0.2, 9241),
                                     _w(K.cbox((0.86, 0.06, 0.03), POST, centre=(0, 1.4, 0.035), bevel=0.0), 'bark', 0.2, 9242)])
    extras = {'Door': (door, (2.45, 0.1, WZ - 0.2))}
    door_at = [2.85, 0.0, WZ + 0.9]
    cat = {
        'footprint': [[-2.85, 0.0, 2.2], [-0.95, 0.0, 2.2], [0.95, 0.0, 2.2], [2.85, 0.0, 2.2], [-4.9, 0.0, 1.7]]
                     + [[x, 2.7, 0.5] for x in (-3.4, -2.6, -1.8, -1.0, -0.2, 0.6, 1.4)],
        'tags': ['building', 'interact', 'home'],
        'notes': ('The home (母屋), round 4: main house walls 7.6 x 4.4 m, thatch 9.8 x 6.6 m in three courses with a 0.6 m cut eave, '
                  'ridge %.1f m with a turf ridge (grass, iris, lilies), engawa along three bays, shoji (material minka_shoji: lit '
                  'from inside after dusk), the doma door with a noren (east bay), a board-roofed lean-to on the west with the '
                  'kitchen chimney. Node Door: the doma sliding door. anchors: door (where she stands to go in), smoke (chimney '
                  'top), light (the brazier inside), cat (on the engawa), light_door (a lantern hook by the doma).' % (ridge_y + 0.35)),
        'anchors': {'door': door_at, 'interact': door_at, 'smoke': [float(v) for v in smoke], 'light': [float(v) for v in brazier],
                    'cat': [-2.75, FLOOR, ENG_Z0 + 0.42], 'light_door': [3.95, 2.3, WZ + 0.35],
                    'engawa': [-1.0, FLOOR, ENG_Z1 - 0.2], 'tub_spot': [GX1 - 0.4, 0.0, GZ1 + 1.1]},
    }
    st = {'hut': export_prop(out, 'hut', 'buildings', prop, cat, porosity=0.85, cutaway=False, far=False, extras=extras,
                             budget=24000, cards=cards, asset=a)}
    from .hut import backpack_frame_pieces
    b2 = K.Prop('backpack_frame', 8240).add(backpack_frame_pieces())
    st['backpack_frame'] = export_prop(out, 'backpack_frame', 'objects', b2,
                                       {'footprint': [], 'tags': ['pickup', 'story'],
                                        'notes': '背負子, the old backpack frame (1.05 m), upright; origin at its feet.',
                                        'anchors': {'carry': [0.0, 0.6, -0.05]}}, porosity=0.8, budget=800)
    return st
