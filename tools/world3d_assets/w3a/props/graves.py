"""The nine nameless graves (無縁墓) on their bench below the camphor: small weathered stones of
mixed kinds in a row (natural stones, a square pillar, a little five-ring tower, a leaning slab,
a round-topped stele, stacked river stones, a broken pillar, a round-headed stone, a sunken one),
moss on their tops, some leaning. Beside each a bamboo pole with a hook for a paper lantern
(anchors.hook_0..9: ten lanterns, the tenth on a taller pole at the east end), incense holders
with a few sticks, bamboo flower tubes and water cups.

Laid out along x from -4.6 to 4.6 m (1.15 m apart, as the renderer's placeholder), origin at the
'graves' marker, ground at y = 0."""
from __future__ import annotations

import math

import numpy as np

from ..core import rng
from . import kit as K
from .common import export_prop

GREYS = ['#8e8b82', '#9a958a', '#7f7d76', '#87837a', '#929089', '#7c7a71', '#958f84', '#84827a', '#8b887f']
BAMBOO = K.col('#9a9a5c')
BAMBOO_DRY = K.col('#a89c6a')
CUP = K.col('#ded8c8')


def _stone(pc, c, amount=0.6, seed=0):
    pc.pattern = K.PAT['stone']
    pc.amount = amount
    pc.var = 0.06
    pc.seed = seed
    pc.colour = c
    return pc


def _tilt(pieces, ax, az, pivot=(0, 0, 0)):
    """Lean pieces about a pivot on the ground (radians about x and z)."""
    R = K.rot_z(az) @ K.rot_x(ax)
    out = []
    for p in pieces:
        P = (p.p - pivot) @ R.T + pivot
        N = p.n @ R.T
        out.append(K.Piece(P, N, p.idx, p.colour, p.pattern, p.amount, p.mat, p.var, p.seed, p.ao, p.dirt, p.emissive, p.shade))
    return out


def natural_stone(c, seed, w=0.42, h=0.62, d=0.3, sunk=0.0):
    def f(P):
        q = P - np.array([0, h * 0.45 - sunk, 0])
        e = K.sd_ellipsoid(q, (w / 2, h * 0.55, d / 2))
        flat = q[..., 2] - d * 0.32                      # a flattish face toward the camera
        e = K.smax(e, flat, 0.05)
        return e + K.weathered(P, 0.018, 0.09, seed)
    return K.sdf_piece(f, (-w / 2 - 0.05, -0.05, -d / 2 - 0.05), (w / 2 + 0.05, h + 0.05, d / 2 + 0.05), c, h=0.02,
                       tris=260, pattern='stone', amount=0.7, var=0.07, seed=seed)


def grave(i, R):
    """Pieces of grave i (local: origin at its foot, front toward +z)."""
    c = K.col(GREYS[i % len(GREYS)])
    sd = int(R.integers(0, 1 << 20))
    out = []
    base = lambda w, d, h=0.09: _stone(K.cbox((w, h, d), c * 0.88, centre=(0, h / 2, 0), bevel=0.02, jitter=0.006, seed=sd), c * 0.88, 0.7, sd)
    if i == 0:                                               # natural stone, leaning
        out += _tilt([natural_stone(c, sd, 0.44, 0.62, 0.3)], -0.06, 0.1)
    elif i == 1:                                             # square pillar on a base, pyramid cap
        out.append(base(0.44, 0.38))
        out.append(_stone(K.cbox((0.24, 0.62, 0.22), c, centre=(0, 0.09 + 0.31, 0), bevel=0.018, jitter=0.005, seed=sd), c, 0.5, sd))
        out.append(_stone(K.convex([(-0.12, 0.71, -0.11), (0.12, 0.71, -0.11), (0.12, 0.71, 0.11), (-0.12, 0.71, 0.11),
                                    (0.0, 0.79, 0.0)], c), c, 0.6, sd))
    elif i == 2:                                             # five-ring tower (gorinto), small
        y = 0.0
        out.append(_stone(K.cbox((0.3, 0.22, 0.3), c, centre=(0, 0.11, 0), bevel=0.02, jitter=0.006, seed=sd), c, 0.6, sd))
        y = 0.22
        out.append(_stone(K.lathe([(0.0, 0), (0.1, 0.01), (0.15, 0.08), (0.14, 0.15), (0.08, 0.2), (0.0, 0.21)], c, n=10,
                                  base=(0, y, 0)), c, 0.4, sd))
        y += 0.2
        out.append(_stone(K.cprism(4, 0.26, 0.08, 0.13, c, base=(0, y, 0), bevel=0.015, rot=math.pi / 4), c, 0.7, sd))
        y += 0.13
        out.append(_stone(K.lathe([(0.0, 0), (0.09, 0.0), (0.1, 0.03), (0.07, 0.06), (0.0, 0.065)], c, n=10, base=(0, y, 0)), c, 0.5, sd))
        y += 0.06
        out.append(_stone(K.lathe([(0.0, 0), (0.05, 0.01), (0.06, 0.04), (0.04, 0.08), (0.0, 0.11)], c, n=8, base=(0, y, 0)), c, 0.4, sd))
        out = _tilt(out, 0.0, -0.04)
    elif i == 3:                                             # gabled slab (itabi), leaning back
        pts = []
        for z in (-0.04, 0.04):
            pts += [(-0.16, 0.0, z), (0.16, 0.0, z), (0.16, 0.62, z), (-0.16, 0.62, z), (0.0, 0.74, z)]
        out += _tilt([_stone(K.convex(pts, c), c, 0.5, sd)], -0.14, 0.03)
    elif i == 4:                                             # round-topped stele on a base
        out.append(base(0.42, 0.32))
        pts = []
        for z in (-0.06, 0.06):
            pts += [(-0.15, 0.09, z), (0.15, 0.09, z)]
            for k in range(9):
                a = math.pi * k / 8
                pts.append((math.cos(a) * 0.15, 0.5 + math.sin(a) * 0.17 * (1.0 if abs(z) < 0.07 else 1.0), z))
        out.append(_stone(K.convex(pts, c), c, 0.5, sd))
    elif i == 5:                                             # two river stones stacked
        def f(P):
            a = K.sd_ellipsoid(P - np.array([0, 0.14, 0]), (0.22, 0.15, 0.18))
            b = K.sd_ellipsoid(P - np.array([0.02, 0.37, 0.0]), (0.15, 0.11, 0.12))
            return K.smin(a, b, 0.03) + K.weathered(P, 0.01, 0.08, sd)
        out.append(K.sdf_piece(f, (-0.25, -0.03, -0.21), (0.25, 0.5, 0.21), c, h=0.018, tris=300, pattern='stone',
                               amount=0.6, var=0.06, seed=sd))
    elif i == 6:                                             # broken pillar, slanted break
        out.append(base(0.36, 0.32))
        pts = [(-0.1, 0.09, -0.1), (0.1, 0.09, -0.1), (0.1, 0.09, 0.1), (-0.1, 0.09, 0.1),
               (-0.1, 0.84, -0.1), (0.1, 0.72, -0.1), (0.1, 0.7, 0.1), (-0.1, 0.8, 0.1)]
        out.append(_stone(K.convex(pts, c), c, 0.45, sd))
        out = _tilt(out, 0.02, 0.07)
    elif i == 7:                                             # round-headed stone
        out.append(_stone(K.lathe([(0.0, 0.0), (0.15, 0.0), (0.15, 0.06), (0.13, 0.08), (0.12, 0.35), (0.1, 0.42),
                                   (0.0, 0.43)], c, n=10), c, 0.4, sd))
        out.append(_stone(K.lathe([(0.0, 0.0), (0.075, 0.02), (0.09, 0.08), (0.075, 0.15), (0.0, 0.17)], c, n=10,
                                  base=(0, 0.42, 0)), c, 0.6, sd))
    else:                                                    # low sunken stone, mossy
        out.append(natural_stone(c * 0.95, sd, 0.5, 0.42, 0.34, sunk=0.06))
        out[-1].amount = 0.9
    return out


def offering(kind, R, seed):
    out = []
    if kind == 'incense':
        out.append(_stone(K.cbox((0.16, 0.07, 0.11), K.col('#6a6862'), centre=(0, 0.035, 0), bevel=0.012), K.col('#6a6862'), 0.3, seed))
        for k in range(3):
            x = -0.04 + 0.04 * k + R.normal(0, 0.006)
            out.append(K.rod([[x, 0.06, 0], [x + R.normal(0, 0.01), 0.2, R.normal(0, 0.01)]], 0.006, K.col('#4a5a3a'), n=3,
                             cap=True, step=0.2, var=0.0, dirt=False))
            out.append(K.cbox((0.014, 0.014, 0.014), K.col('#d8d2c4'), centre=(x, 0.205, 0), bevel=0.0, var=0.0))
    elif kind == 'flowers':
        out.append(K.lathe([(0.03, 0), (0.034, 0.01), (0.034, 0.17), (0.03, 0.175)], BAMBOO, n=7, var=0.04, seed=seed))
        for k in range(3):
            a = 2 * math.pi * k / 3 + R.uniform(0, 1)
            out.append(K.rod([[0, 0.15, 0], [math.cos(a) * 0.06, 0.32, math.sin(a) * 0.04]], 0.006, BAMBOO_DRY * 0.8, n=3,
                             cap=True, step=0.2, var=0.0, dirt=False))
    elif kind == 'cup':
        out.append(K.lathe([(0.0, 0), (0.028, 0), (0.036, 0.05), (0.03, 0.052), (0.0, 0.04)], CUP, n=8, var=0.0,
                           seed=seed, dirt=False))
    return out


def hook_pole(h, R, seed):
    """A bamboo pole with a short arm and a hook at the top; returns (pieces, hook point)."""
    lean = R.normal(0, 0.02)
    top = np.array([lean, h, 0.0])
    out = [K.rod([[0, -0.1, 0], [lean * 0.5, h * 0.5, 0], top], 0.017, BAMBOO * (1 + R.normal(0, 0.04)), n=5, cap=True,
                 step=0.6, var=0.03, seed=seed)]
    arm_end = top + np.array([0.0, -0.02, 0.15])
    out.append(K.rod([top + np.array([0, -0.03, 0]), arm_end], 0.01, BAMBOO * 0.92, n=4, cap=True, step=0.2, var=0.0))
    out.append(K.rod([arm_end, arm_end + np.array([0, -0.05, 0.0])], 0.005, K.col('#3a332c'), n=3, cap=True, step=0.05,
                     var=0.0, dirt=False))
    return out, arm_end + np.array([0, -0.05, 0])


def build(out):
    R = rng(7901)
    pieces = []
    hooks = []
    stones = []
    kinds = {1: 'incense', 2: 'incense', 5: 'incense', 7: 'incense', 0: 'flowers', 4: 'flowers', 8: 'flowers',
             3: 'cup', 6: 'cup'}
    for i in range(9):
        x = -4.6 + i * 1.15 + R.uniform(-0.1, 0.1)
        z = R.uniform(-0.15, 0.1)
        yaw = R.normal(0, 0.12)
        g = grave(i, R)
        Rm = K.rot_y(yaw)
        pieces += [p.moved(Rm, (x, 0, z)) for p in g]
        stones.append([round(x, 2), round(z, 2), 0.3])
        o = offering(kinds[i], R, 7950 + i)
        pieces += [p.moved(K.rot_y(yaw), (x + R.uniform(-0.08, 0.08), 0, z + 0.33)) for p in o]
        hp, hk = hook_pole(1.25 + R.uniform(-0.08, 0.08), R, 7960 + i)
        off = np.array([x + 0.42, 0, z + 0.05])
        pieces += [p.moved(None, off) for p in hp]
        hooks.append([round(float(v), 3) for v in hk + off])
    hp, hk = hook_pole(1.5, R, 7970)                         # the tenth lantern, east end
    off = np.array([5.35, 0, 0.1])
    pieces += [p.moved(None, off) for p in hp]
    hooks.append([round(float(v), 3) for v in hk + off])
    prop = K.Prop('graves', 7901).add(pieces)
    cat = {'footprint': stones, 'tags': ['interact', 'stone', 'graves'],
           'notes': 'The nine nameless graves (無縁墓) in a row 9.2 m long on their bench, origin at the graves marker. '
                    'anchors.hook_0..9: where the ten paper lanterns (lights/lantern_paper, anchors.hang) hang.'}
    markers = {'hook': hooks}
    return {'graves': export_prop(out, 'graves', 'props', prop, cat, porosity=0.5, markers=markers, budget=4000)}
