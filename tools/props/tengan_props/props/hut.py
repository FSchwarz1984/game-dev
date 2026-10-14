"""The porter's hut (歩荷小屋): a Q-proportion one-room house with a hipped thatch roof.

Local frame: origin = the middle of the front (south) wall at ground level (the hut pad's top);
x east, y up, z south; the walls stand on x in [-W/2, W/2], z in [-D, 0] (the region marker's
footprint, 5.2 x 3.8 m). The door is 47 px tall (2.35 m): 1.2x her 39 px sprite (knowledge/15 Q
proportion). The eave sits high enough that the whole door shows under it in the oblique view.

Layers: body (walls, foundation, things on the walls; sorted at the front wall) and roof (thatch,
ridge; sorted at the eave line). Both cut x-ray holes. The door (hut_door), the lantern by the door,
the firewood and the rest are separate props so they sort on their own and can change state.
"""
import math

import numpy as np

from .. import materials as M
from ..core import KZ, Rng, hash01, normalize
from ..pipeline import Layer, PropDef
from ..render import Line
from ..sdf import Box, Capsule, Cyl, Diff, Displace, Ellipsoid, Planes, Prism, rot
from ..shapes import hs, rope_line, stone_lump

W = 5.2            # wall width (x)
D = 3.8            # wall depth (z)
SILL = 0.30        # top of the sill (土台) above the pad
EAVE_Y = 3.10      # underside of the thatch at the eave
CUT_H = 0.46       # thickness of the thatch at the eave (the cut face)
OV_F = 0.50        # eave overhang, front and back
OV_S = 0.50        # eave overhang, sides
PITCH = 48.0       # front and back slopes
HIP = 60.0         # the hips (steeper: a longer ridge, as on a real 寄棟)
DOOR_X = (0.42, 1.52)
DOOR_TOP = 2.65
WIN = (-1.95, -0.65, 1.35, 2.05)    # x0, x1, y0, y1


def roof_geometry():
    ye = EAVE_Y + CUT_H
    zf = OV_F
    zb = -D - OV_F
    xs = W / 2 + OV_S
    zr = (zf + zb) / 2
    tp = math.tan(math.radians(PITCH))
    th = math.tan(math.radians(HIP))
    yr = ye + (zf - zr) * tp
    xr = xs - (yr - ye) / th
    return dict(ye=ye, zf=zf, zb=zb, xs=xs, zr=zr, yr=yr, xr=xr, tp=tp, th=th)


def _roof_mat(seed):
    def f(ctx):
        cut = (ctx.N[:, 2] > 0.80) & (np.abs(ctx.N[:, 1]) < 0.5)
        a = M.thatch(ctx, seed=seed, moss=0.45, weeds=1.0)
        b = M.thatch_cut(ctx, seed=seed + 1)
        pal = np.where(cut, b['pal'], a['pal'])
        tone = np.where(cut, b['tone'], a['tone'])
        return dict(pal=pal, tone=tone)
    return f


def roof_solids(state='intact'):
    g = roof_geometry()
    ye, zf, zb, xs, tp, th = g['ye'], g['zf'], g['zb'], g['xs'], g['tp'], g['th']
    planes = [
        hs((0, 1, tp), (0, ye, zf)),          # front slope
        hs((0, 1, -tp), (0, ye, zb)),         # back slope
        hs((-th, 1, 0), (-xs, ye, 0)),        # west hip
        hs((th, 1, 0), (xs, ye, 0)),          # east hip
        hs((0, -1, 0), (0, EAVE_Y, 0)),       # underside
        hs((0, 0, 1), (0, 0, zf)),            # front cut face
        hs((0, 0, -1), (0, 0, zb)),
        hs((1, 0, 0), (xs, 0, 0)),
        hs((-1, 0, 0), (-xs, 0, 0)),
    ]
    lb = ([-xs - 0.1, EAVE_Y - 0.1, zb - 0.1], [xs + 0.1, g['yr'] + 0.1, zf + 0.1])
    mass = Planes(planes, lb, r=0.07, mat=_roof_mat(31), part='roof',
                  data={'cut_y0': EAVE_Y, 'cut_h': CUT_H})
    roof = Displace(mass, 0.035, 2.6, seed=4, octaves=3)
    out = [roof]
    # the ridge: a straw bundle wrapped in cedar bark, held by bamboo ties, with crossed poles
    yr, zr, xr = g['yr'], g['zr'], g['xr']
    ridge = Box([xr + 0.18, 0.15, 0.24], r=0.12, pos=(0, yr + 0.05, zr), part='roof',
                mat=(M.timber, dict(pal='bark', axis=0, base=0.5, seed=5)))
    out.append(Displace(ridge, 0.015, 6.0, seed=9))
    # saddle boards (馬乗り) straddling the ridge at intervals
    n = 7
    for i in range(n):
        x = -xr + 0.1 + (2 * xr - 0.2) * i / (n - 1)
        out.append(Box([0.07, 0.10, 0.30], r=0.025, pos=(x, yr + 0.18, zr), part='roof',
                       mat=(M.timber, dict(pal='wood_dark', axis=2, base=0.45, seed=11 + i))))
    # crossed poles (烏おどり) at both ends of the ridge
    for sx in (-1, 1):
        xe = sx * (xr + 0.05)
        for k in (-1, 1):
            a = (xe - k * 0.05, yr - 0.05, zr - k * 0.35)
            b = (xe + k * 0.02, yr + 0.62, zr + k * 0.30)
            out.append(Capsule(a, b, 0.045, part='roof',
                               mat=(M.timber, dict(pal='wood_dark', axis=1, base=0.5, seed=21 + k))))
    return out


def body_solids(state='intact'):
    out = []
    rng = Rng(7)
    hw = W / 2
    # ---- foundation: a row of irregular flat stones under the sill, a little proud of the wall
    x = -hw - 0.12
    k = 0
    while x < hw + 0.1:
        w = rng.range(0.38, 0.62)
        h = rng.range(0.15, 0.22)
        out.append(stone_lump((x + w / 2, h / 2 - 0.02, -0.12), (w, h, 0.42), seed=40 + k, amp=0.18,
                              mat=(M.stone, dict(pal='stone', seed=40 + k, moss=0.45, lichen=0.3, base=0.5))))
        x += w + rng.range(-0.02, 0.03)
        k += 1
    # side stones (they show as the corners turn)
    for sx in (-1, 1):
        for j in range(3):
            z = -0.6 - j * 1.1
            out.append(stone_lump((sx * (hw + 0.06), 0.08, z), (0.4, 0.2, 0.9), seed=70 + j + (sx > 0) * 5,
                                  amp=0.18, mat=(M.stone, dict(pal='stone', seed=70 + j, moss=0.4, base=0.48))))
    # ---- the sill (土台) and the wall mass (side walls splay 0.1 m so 2 px of them show: knowledge/15)
    out.append(Box([hw + 0.04, 0.07, D / 2], r=0.015, pos=(0, 0.23, -D / 2),
                   mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.42, seed=3))))
    splay = 0.10 / D
    wall_planes = [
        hs((0, 0, 1), (0, 0, 0)),
        hs((0, 0, -1), (0, 0, -D)),
        hs((-1, 0, splay), (-hw, 0, 0)),
        hs((1, 0, splay), (hw, 0, 0)),
        hs((0, -1, 0), (0, SILL, 0)),
        hs((0, 1, 0), (0, EAVE_Y + 0.2, 0)),
    ]
    # the wall mass: west/east sides are boards; the front faces are covered by the panels below
    sides = Planes(wall_planes, ([-hw - 0.15, SILL, -D], [hw + 0.15, EAVE_Y + 0.2, 0.0]),
                   mat=(M.boards, dict(pal='wood_old', vertical=True, board=0.28, seed=8, base=0.5)))
    out.append(sides)
    # ---- the front wall: wainscot boards below, earth plaster above, a window, the door opening
    wy = 1.18
    wain = Box([hw - 0.08, (wy - SILL) / 2, 0.03], pos=(0, (wy + SILL) / 2, 0.0),
               mat=(M.boards, dict(pal='wood_old', vertical=True, board=0.3, seed=12, base=0.56,
                                   nails=[(x0, wy - 0.12) for x0 in np.arange(-2.4, 2.5, 0.6)])))
    # battens (押縁) over the board joints
    plaster = Box([hw - 0.08, (EAVE_Y - wy) / 2, 0.02], pos=(0, (EAVE_Y + wy) / 2, -0.01),
                  mat=(M.plaster, dict(seed=17, fallen=0.55, cracks=0.6, tide=0.0, base=0.62)))
    win_cut = Box([(WIN[1] - WIN[0]) / 2, (WIN[3] - WIN[2]) / 2, 0.2],
                  pos=((WIN[0] + WIN[1]) / 2, (WIN[2] + WIN[3]) / 2, 0.0))
    door_cut = Box([(DOOR_X[1] - DOOR_X[0]) / 2, (DOOR_TOP - SILL + 0.1) / 2, 0.2],
                   pos=((DOOR_X[0] + DOOR_X[1]) / 2, (DOOR_TOP + SILL - 0.1) / 2, 0.0))
    out.append(Diff(wain, door_cut))
    out.append(Diff(plaster, win_cut, door_cut))
    # door opening: a dark recess (the door itself is the hut_door prop, in front of it)
    out.append(Box([(DOOR_X[1] - DOOR_X[0]) / 2, (DOOR_TOP - SILL) / 2, 0.02],
                   pos=((DOOR_X[0] + DOOR_X[1]) / 2, (DOOR_TOP + SILL) / 2, -0.25), mat=M.interior))
    # threshold (敷居) under the door
    out.append(Box([(DOOR_X[1] - DOOR_X[0]) / 2 + 0.12, 0.05, 0.08], r=0.01,
                   pos=((DOOR_X[0] + DOOR_X[1]) / 2, SILL + 0.02, 0.02),
                   mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.5, seed=4))))
    # ---- posts (柱): corners, door jambs, one between; 0.16 m square
    for px in (-hw + 0.08, -0.55, DOOR_X[0] - 0.07, DOOR_X[1] + 0.07, hw - 0.08):
        out.append(Box([0.08, (EAVE_Y - SILL) / 2 + 0.05, 0.08], r=0.02, pos=(px, (EAVE_Y + SILL) / 2, -0.02),
                       mat=(M.timber, dict(pal='wood_dark', axis=1, base=0.5, seed=int(px * 10) + 50))))
    # head beam (桁) along the top of the front wall, and the door lintel (鴨居)
    out.append(Box([hw + 0.10, 0.11, 0.10], r=0.02, pos=(0, EAVE_Y - 0.06, 0.01),
                   mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.48, seed=61))))
    out.append(Box([(DOOR_X[1] - DOOR_X[0]) / 2 + 0.16, 0.06, 0.07], r=0.01,
                   pos=((DOOR_X[0] + DOOR_X[1]) / 2, DOOR_TOP + 0.05, 0.03),
                   mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.52, seed=62))))
    # a waist rail between wainscot and plaster
    out.append(Box([hw - 0.08, 0.035, 0.05], r=0.01, pos=(0, wy, 0.02),
                   mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.55, seed=63))))
    # ---- the window (連子窓): a frame, vertical slats, paper behind
    wx0, wx1, wy0, wy1 = WIN
    cx = (wx0 + wx1) / 2
    cy = (wy0 + wy1) / 2
    out.append(Box([(wx1 - wx0) / 2, (wy1 - wy0) / 2, 0.02], pos=(cx, cy, -0.10),
                   mat=(M.paper, dict(seed=3, base=0.62)), data={'window_paper': True}))
    for x0 in np.arange(wx0 + 0.11, wx1 - 0.05, 0.13):
        out.append(Box([0.025, (wy1 - wy0) / 2, 0.025], pos=(x0, cy, -0.02),
                       mat=(M.timber, dict(pal='bamboo', axis=1, base=0.55, seed=int(x0 * 50) + 300, checks=False))))
    for (fx, fy, hx, hy) in ((cx, wy1 + 0.03, (wx1 - wx0) / 2 + 0.06, 0.035),
                             (cx, wy0 - 0.03, (wx1 - wx0) / 2 + 0.08, 0.04)):
        out.append(Box([hx, hy, 0.05], r=0.01, pos=(fx, fy, 0.02),
                       mat=(M.timber, dict(pal='wood_dark', axis=0, base=0.55, seed=70))))
    for fx in (wx0 - 0.03, wx1 + 0.03):
        out.append(Box([0.035, (wy1 - wy0) / 2 + 0.05, 0.05], r=0.01, pos=(fx, cy, 0.02),
                       mat=(M.timber, dict(pal='wood_dark', axis=1, base=0.52, seed=71))))
    # ---- things on the wall: straw sandals on a peg, a straw raincoat, a rope coil, dried herbs
    out += wall_things()
    return out


def wall_things():
    out = []
    # peg + a pair of straw sandals (草鞋) left of the door
    px, py = -0.25, 1.95
    out.append(Capsule((px, py, 0.02), (px, py + 0.02, 0.12), 0.02, mat=(M.timber, dict(pal='wood_dark', axis=2))))
    for k, dx in enumerate((-0.07, 0.07)):
        sole = Box([0.055, 0.16, 0.015], r=0.012, pos=(px + dx, py - 0.18, 0.045 + k * 0.01), R=rot(roll=dx * 60),
                   mat=(M.straw, dict(seed=80 + k, base=0.62, axis=1)))
        out.append(sole)
    # the straw raincoat (蓑) hanging at the east end of the wall
    mino = Planes([hs((0, 0, 1), (0, 0, 0.10)), hs((0, 0, -1), (0, 0, 0.0)),
                   hs((-1.0, 0.32, 0), (-0.18, 2.55, 0)), hs((1.0, 0.32, 0), (0.18, 2.55, 0)),
                   hs((0, -1, 0), (0, 1.55, 0)), hs((0, 1, 0), (0, 2.62, 0))],
                  ([-0.6, 1.5, -0.05], [0.6, 2.7, 0.15]), r=0.03, pos=(2.05, 0, 0.02),
                  mat=(M.straw, dict(seed=90, base=0.48, pal='thatch', axis=1)))
    out.append(Displace(mino, 0.02, 9.0, seed=91))
    out.append(Capsule((2.05, 2.62, 0.04), (2.05, 2.70, 0.10), 0.02, mat=(M.timber, dict(pal='wood_dark', axis=2))))
    # coil of straw rope on a peg, right of the window
    out.append(Diff(Cyl(0.14, -0.035, 0.035, rz=0.14, r=0.02, pos=(-0.30, 2.45, 0.06), R=rot(pitch=90),
                        mat=(M.straw, dict(pal='rope', seed=95, base=0.6, axis=2))),
                    Cyl(0.07, -0.1, 0.1, rz=0.07, pos=(-0.30, 2.45, 0.06), R=rot(pitch=90))))
    # a bunch of dried herbs hanging from the head beam
    for k, hx in enumerate((-1.45, -1.25)):
        out.append(Ellipsoid([0.07, 0.17, 0.04], pos=(hx, 2.72, 0.07),
                             mat=(M.straw, dict(pal='leaf', seed=100 + k, base=0.4, axis=1))))
    return out


def build(state='intact'):
    solids = body_solids(state) + roof_solids(state)
    lines = []
    # strings: the herbs and the sandals hang on cords
    lines.append(rope_line([(-1.45, 2.88, 0.07), (-1.45, 3.0, 0.07)], (M.rope, {}), width=1))
    lines.append(rope_line([(-1.25, 2.88, 0.07), (-1.25, 3.0, 0.07)], (M.rope, {}), width=1))
    # bamboo ties around the ridge bundle
    g = roof_geometry()
    for i in range(6):
        x = -g['xr'] + 0.25 + (2 * g['xr'] - 0.5) * i / 5
        lines.append(rope_line([(x, g['yr'] - 0.06, g['zr'] + 0.24), (x, g['yr'] + 0.18, g['zr'] + 0.10)],
                               (M.rope, dict(pal='bamboo')), part='roof', width=1))
    layers = [Layer('body', sort_px=0, occluder=True, kb=0.30),
              Layer('roof', sort_px=int(round(OV_F * 20)), occluder=True, kb=0.34)]
    meta = {
        'footprint_m': [W, D],
        'block': [[x, -D / 2, 0.0] for x in ()],
        'block_rect_m': [-W / 2 - 0.05, -D - 0.05, W / 2 + 0.05, 0.05],
        'door_m': [(DOOR_X[0] + DOOR_X[1]) / 2, 0.0],
        'window_m': [(WIN[0] + WIN[1]) / 2, (WIN[2] + WIN[3]) / 2],
        'eave_front_z_m': OV_F,
        'roof_top_m': g['yr'] + 0.7,
    }
    return PropDef('hut', solids, lines, layers=layers, kind='building', meta=meta)


PROPS = {'hut': build}
STATES = {'hut': ['intact']}
