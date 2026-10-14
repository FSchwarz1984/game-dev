"""The giant camphor 御神木: the hero of the art sample.

Scale (lead's brief): crown spread about 34 m (radius ~17), crown base 6-8 m, top 20-22 m; trunk
about 6.5 m across, gnarled and twisting, burls and deep furrows; buttress roots spreading to
~9.5 m and sinking into the ground; massive low limbs reaching out 14-17 m with moss and small
ferns on them; a shimenawa with shide around the trunk (the only "cannot take" marker).

One organism: the limbs grow out of the trunk, the branches out of the limbs and into the leaf
masses they carry; the lowest masses hang on the limb ends, so the crown's lower edge shows the
limbs going in. Budget (contract 2): <= 20k triangles for the great camphor.
"""
from __future__ import annotations

import math
import os

import numpy as np

from .. import cards as CD
from .. import foliage as FO
from .. import leaves as LV
from .. import wood as WD
from ..core import PPM, TEXEL_PER_M, hex_rgb, normalize, rng
from ..mesh import MeshData
from ..tube import Spine, tube

SEED = 7001
NAME = 'camphor_great'

# ------------------------------------------------------------------------------- the base
# The trunk, its buttress roots and the crotch where the limbs leave are one signed-distance
# surface (w3a/sdf.py): every junction gets a fillet, the roots leave the trunk as tall buttresses,
# arch down, run over the ground (fitted to the saddle terrain) and dive in at different lengths.
GRID_H = 0.15                      # voxel (m) of the base field
K_MAJOR = 0.42                     # blend radius trunk / roots / limbs (m)
K_MINOR = 0.2                      # small roots and burls
BASE_TRIS = 6600                   # decimation target for the base surface
TWIST = 0.08                       # rad per metre
ROPE_Y = 2.45                      # shimenawa height

TRUNK_PTS = [[0, -2.4, 0], [0, -0.9, 0], [0.05, 0.6, 0.05], [0.25, 2.4, -0.05], [0.4, 4.2, -0.15], [0.35, 5.6, -0.25],
             [0.3, 6.6, -0.3]]
TRUNK_R = [3.2, 3.15, 3.05, 2.85, 2.6, 2.3, 2.0]
TRUNK_TOP = 6.5

# theta: 0 north (-z), pi/2 west (-x), pi south (toward the camera), 3pi/2 east.
# The layout around the tree limits the reach: the road passes 9 m east, the shrine terrace starts
# 7 m west-south-west, her path runs 10 m south, in front of the graves.
ROOTS = [  # theta, start height on the trunk, radius, reach from the axis (m), meander (m), knee, fork
    (0.30, 2.0, 0.95, 7.4, 0.7, False, None),
    (1.10, 2.3, 1.05, 8.0, -0.9, False, (0.55, 0.75, 3.0)),
    (1.86, 1.8, 0.85, 6.0, 0.5, False, None),
    (2.52, 2.2, 0.95, 7.8, -0.7, True, None),
    (3.32, 1.6, 0.72, 5.3, 0.45, False, None),
    (3.96, 2.4, 1.0, 7.5, 0.9, False, (0.5, -0.7, 2.6)),
    (4.66, 2.1, 1.0, 7.0, -0.6, False, None),
    (5.46, 2.0, 0.9, 6.6, 0.5, False, None),
]
MINOR_ROOTS = [  # theta at the trunk foot, radius, reach, meander
    (3.64, 0.26, 5.4, -0.5), (5.05, 0.28, 5.8, 0.6), (2.20, 0.24, 4.9, 0.4), (0.72, 0.26, 5.2, -0.4),
    (2.95, 0.2, 4.4, 0.3),
]
BURLS = [  # angle, height (m), amplitude (m), angular width, vertical width
    (2.55, 3.3, 0.40, 0.30, 0.7), (4.0, 3.6, 0.30, 0.25, 0.55), (1.6, 3.9, 0.36, 0.28, 0.6),
    (4.9, 3.4, 0.28, 0.22, 0.5), (3.25, 4.4, 0.24, 0.20, 0.45),
]
HOLLOW = (2.95, 0.8, 0.62, 0.85, 0.75)   # angle, centre height, half-width, half-height, depth


def _angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def _theta(x, z):
    """Angle about the trunk (0 = north, pi/2 = west)."""
    t = np.arctan2(-x, -z)
    return np.where(t < 0, t + 2 * math.pi, t)


def _dir(theta):
    return np.array([-math.sin(theta), 0.0, -math.cos(theta)])


def trunk_ref(y):
    return np.interp(y, [p[1] for p in TRUNK_PTS], TRUNK_R)


def trunk_R(theta, y):
    theta = np.asarray(theta, np.float64)
    y = np.asarray(y, np.float64)
    th = theta + TWIST * y
    r = trunk_ref(y) * (1 + 0.06 * np.sin(5 * th + 0.7) + 0.04 * np.sin(3 * th + 2.1) + 0.02 * np.sin(8 * th + 1.3))
    r = r + 0.42 * np.exp(-np.maximum(y, 0) / 0.9)
    f = np.clip((y - 5.3) / (TRUNK_TOP - 5.3), 0, 1)
    return r * np.sqrt(np.maximum(1 - f * f, 0.0))


def root_spine(theta, h0, r0, reach, meander, knee, ground, R):
    """Control points and radii of a buttress root: inside the trunk at h0, down the trunk as a
    tall buttress, a hump where it meets the ground, then a low ridge half sunk in the soil that
    thins, wanders and fades into the ground at `reach` (heights relative to the ground below)."""
    d = _dir(theta)
    side = np.array([d[2], 0.0, -d[0]])
    rt = float(trunk_R(theta, 0.6))
    ph = R.uniform(0, 2 * math.pi)
    f2 = R.uniform(2.2, 3.4)
    pts, rad = [], []

    def at(rho, lam, y_rel=None, y_abs=None):
        p = d * rho + side * lam
        y = y_abs if y_abs is not None else float(ground(p[0], p[2])) + y_rel
        return np.array([p[0], y, p[2]])
    pts.append(at(rt - 0.75 * r0, 0.0, y_abs=h0))
    rad.append(r0 * 0.9)
    pts.append(at(rt + 0.2 * r0, 0.0, y_abs=h0 * 0.45 + 0.15))
    rad.append(r0)
    pts.append(at(rt + 0.75 * r0 + 0.45, 0.05 * meander, y_rel=0.3 * r0))           # the hump
    rad.append(r0 * 0.82)
    rho1 = rt + 1.5 * r0 + 0.9
    pts.append(at(rho1, 0.15 * meander, y_rel=0.02))
    rad.append(r0 * 0.58)
    n = 4
    for i in range(n):
        t = (i + 1) / n
        rho = rho1 + (reach - rho1) * t
        lam = meander * (0.15 + 0.85 * math.sin(math.pi * t * 0.9 + 0.3)) + 0.25 * math.sin(f2 * t * math.pi + ph)
        rr = r0 * (0.46 - 0.26 * t) * (1 + R.uniform(-0.1, 0.1))
        y_rel = -0.3 * rr - 0.1 * t
        if knee and i == 1:
            y_rel = -1.0 * rr
        if knee and i == 2:
            y_rel = 0.0
        pts.append(at(rho, lam, y_rel=y_rel))
        rad.append(rr)
    pts.append(at(reach + 0.7, lam + 0.2 * meander, y_rel=-1.2 * rad[-1] - 0.3))
    rad.append(rad[-1] * 0.85)
    return pts, rad


def base_parts(R, ground, limb_defs):
    """The parts of the base field: trunk (+ burls), roots, the first metres of each limb."""
    from .. import sdf as SD
    trunk = SD.TrunkSDF('trunk', TRUNK_PTS, trunk_R, trunk_ref, y_lo=-2.6, y_top=TRUNK_TOP + 0.2)
    major = [trunk]
    minor = []
    roots = []
    for i, (th, h0, r0, reach, mea, knee, fork) in enumerate(ROOTS):
        pts, rad = root_spine(th, h0, r0, reach, mea, knee, ground, R)
        s_tall = 1.4 + 0.9 * r0

        def sv(s, s_tall=s_tall):
            t = float(np.clip((s - 0.3 * s_tall) / (1.2 * s_tall), 0, 1))
            return 1.4 + (0.68 - 1.4) * t * t * (3 - 2 * t)

        def sl(s, s_tall=s_tall):
            t = float(np.clip((s - 0.3 * s_tall) / (1.2 * s_tall), 0, 1))
            return 0.7 + (1.25 - 0.7) * t * t * (3 - 2 * t)
        p = SD.TubeSDF(f'root{i}', pts, rad, group='major', sv=sv, sl=sl, ribs=(3, 0.1, 0.25 + 0.05 * i))
        major.append(p)
        roots.append(p)
        if fork is not None:                      # a side root splitting off along the way
            f, dth, ln = fork
            q, tg, rr = p.sp.point_at(f)
            dd = normalize(tg * np.array([1, 0, 1]))
            sd = np.array([dd[2], 0, -dd[0]])
            dn = normalize(dd * math.cos(dth) + sd * math.sin(dth))
            fpts = [q + np.array([0, 0.05, 0])]
            for k in range(1, 4):
                pp = q + dn * ln * k / 3 + sd * 0.25 * math.sin(k)
                fpts.append(np.array([pp[0], float(ground(pp[0], pp[2])) + (-0.08 if k < 3 else -0.6), pp[2]]))
            fr = [rr * 0.7, rr * 0.55, rr * 0.42, rr * 0.3]
            fp = SD.TubeSDF(f'root{i}f', fpts, fr, group='minor', sv=lambda s: 0.7, sl=lambda s: 1.2,
                            ribs=(3, 0.1, 0.3))
            minor.append(fp)
            roots.append(fp)
    for j, (th, r0, reach, mea) in enumerate(MINOR_ROOTS):
        d = _dir(th)
        side = np.array([d[2], 0.0, -d[0]])
        rt = float(trunk_R(th, 0.3))
        pts = []
        for k, t in enumerate((0.0, 0.25, 0.5, 0.75, 0.9, 1.0)):
            rho = rt - 0.3 + (reach - rt + 0.3) * t
            pp = d * rho + side * (mea * math.sin(t * math.pi) + 0.15 * math.sin(t * 7.0 + j))
            y = float(ground(pp[0], pp[2])) + (0.2 if k == 0 else (-0.25 * r0 if k < 5 else -0.6))
            pts.append(np.array([pp[0], y, pp[2]]))
        p = SD.TubeSDF(f'minor{j}', pts, [r0 * 1.5, r0, r0 * 0.9, r0 * 0.75, r0 * 0.6, r0 * 0.5], group='minor',
                       sv=lambda s: 0.75, sl=lambda s: 1.2, ribs=(2, 0.1, 0.4))
        minor.append(p)
        roots.append(p)
    for k, (a, h, amp, wa, wh) in enumerate(BURLS):
        rr = float(trunk_R(a, h))
        dd = _dir(a + TWIST * 0.0)
        c = dd * (rr - 0.55 * amp * 1.8 + amp) + np.array([0, h, 0])
        lat = np.array([dd[2], 0, -dd[0]])
        minor.append(SD.EllipsoidSDF(f'burl{k}', c, (wa * rr * 0.9, wh, amp * 1.8),
                                     axes=[lat, [0, 1, 0], dd], family='trunk'))
    limbs = []
    for name, (pts, rr, s_cut) in limb_defs.items():
        p = SD.TubeSDF('limb_' + name, pts, rr, group='major', uv_mode='front', uv_ref=-WD.view_back_upright(),
                       s_end=s_cut, end_taper=(s_cut - 0.8, s_cut, 0.84), ribs=(4, 0.04, 0.1))
        major.append(p)
        limbs.append(p)
    a, h, hw, hh, dep = HOLLOW
    dd = _dir(a)
    rr = float(trunk_R(a, h))
    hollow = SD.EllipsoidSDF('hollow', dd * (rr + 0.2 - dep * 0.45) + np.array([0, h, 0]), (hw, hh, dep),
                             axes=[[dd[2], 0, -dd[0]], [0, 1, 0], dd])
    return trunk, roots, limbs, major, minor, hollow


def limb_cut(L_pts, L_r, parents):
    """Arc length along a limb where it is well clear of the parts it grows from: the blended
    base takes the limb up to there."""
    from .. import sdf as SD
    sp = Spine(L_pts, L_r, step=0.1)
    for s, q, r in zip(sp.s, sp.pos, sp.rad):
        if all(float(p.dist(q[None, :])[0]) > r * 1.05 for p in parents):
            return float(s)
    return float(sp.length * 0.5)


def _base_key(M):
    """Cache key of the base: its code, the limbs, the crown masses (they shade it) and the ground."""
    import hashlib
    from .. import terrain as TE
    h = hashlib.sha1()
    here = os.path.dirname(os.path.abspath(__file__))
    for f in (os.path.join(here, '..', 'sdf.py'), os.path.join(here, '..', 'tube.py'), os.path.join(here, '..', 'cards.py')):
        h.update(open(f, 'rb').read())
    src = open(os.path.abspath(__file__), encoding='utf-8').read()
    h.update(src[src.index('-' * 40 + ' the base'):src.index('-' * 40 + ' the crown')].encode())
    h.update(repr(LIMBS).encode())
    h.update(repr([(m.c.tolist(), m.r.tolist(), m.flat, m.sag, m.yaw) for m in M]).encode())
    hp = os.path.join(TE.SADDLE, 'height.png')
    if os.path.exists(hp):
        h.update(open(hp, 'rb').read())
    return h.hexdigest()[:16]


def base_mesh(R, M, ground):
    """The blended base (cached in tools/world3d_assets/out/cache: the field and the decimation take
    most of a minute; the cache only saves time, the result is the same)."""
    import pickle
    from .. import sdf as SD
    cdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'out', 'cache')
    os.makedirs(cdir, exist_ok=True)
    path = os.path.join(cdir, f'camphor_base_{_base_key(M)}.pkl')
    if os.path.exists(path):
        d = pickle.load(open(path, 'rb'))
        trunk, roots, limbs, major, minor, hollow = base_parts(R, ground, d['defs'])
        md = MeshData()
        md.add(d['p'], d['n'], d['uv'], d['idx'], uv2=d['uv2'], col=d['col'])
        grid = SD.Grid(d['lo'], d['lo'] + (np.array(d['n_grid']) - 1) * d['h'], d['h'])
        return md, dict(grid=grid, F=d['F'].astype(np.float64), trunk=trunk, roots=roots, limbs=limbs,
                        defs=d['defs'], stats=d['stats'])
    md, base = _base_mesh(R, M, ground)
    base['F'] = base['F'].astype(np.float32).astype(np.float64)     # the same values the cache gives back
    a = md.arrays()
    g = base['grid']
    pickle.dump({'p': a['p'], 'n': a['n'], 'uv': a['uv'], 'idx': a['idx'], 'uv2': a['uv2'], 'col': a['col'],
                 'F': base['F'].astype(np.float32), 'lo': g.lo, 'h': g.h, 'n_grid': [int(x) for x in g.n],
                 'defs': base['defs'], 'stats': base['stats']}, open(path, 'wb'))
    return md, base


def _base_mesh(R, M, ground):
    """The blended base: field, surface nets, projection, decimation, per-owner bark mapping,
    welded seams, colour / AO / moss. Returns (MeshData, parts, field info)."""
    from .. import sdf as SD
    from ..core import fbm3
    # which limbs start in the base, and how far the base takes them
    probe = SD.TrunkSDF('trunk', TRUNK_PTS, trunk_R, trunk_ref, y_lo=-2.6, y_top=TRUNK_TOP + 0.2)
    defs = {}
    lim = {n: (np.array(p), np.array(r)) for n, p, r, _ in LIMBS}
    for name in ('E', 'W', 'S', 'NW', 'NE', 'N', 'L'):
        pts, rr = lim[name]
        s_exit = limb_cut(pts, rr, [probe])
        defs[name] = (pts, rr, s_exit + 1.6)
    from .. import sdf as SD2
    parents = {'SEs': 'S', 'SWs': 'S', 'SEu': 'L', 'SWu': 'L'}
    for name, par in parents.items():
        pts, rr = lim[name]
        ppts, prr = lim[par]
        pp = SD2.TubeSDF('p', ppts, prr)
        s_exit = limb_cut(pts, rr, [pp])
        defs[name] = (pts, rr, s_exit + 1.2)
        # the parent's base part must reach past the junction
        q = pts[0]
        sp = Spine(ppts, prr, step=0.1)
        s_j = float(sp.s[int(np.argmin(np.linalg.norm(sp.pos - q, axis=1)))])
        p0 = defs[par]
        defs[par] = (p0[0], p0[1], max(p0[2], s_j + 1.6))
    trunk, roots, limbs, major, minor, hollow = base_parts(R, ground, defs)
    lo = np.array([-10.0, -2.6, -10.0])
    hi = np.array([10.0, 12.6, 10.0])
    for p in major + minor:
        a, b = p.bbox()
        lo = np.minimum(lo, a - 0.6)
        hi = np.maximum(hi, b + 0.6)
    lo[1] = max(lo[1], -2.6)
    grid = SD.Grid(lo, hi, GRID_H)
    Fa = SD.smin_exp_field(grid, major, K_MAJOR)
    Fb = SD.min_field(grid, minor, fill=10.0)
    F = SD.smin_poly(Fa, Fb, K_MINOR)
    sl, X = grid.box(hollow.bbox()[0] - 0.4, hollow.bbox()[1] + 0.4)
    F[sl] = SD.smax_poly(F[sl], -hollow.dist(X), 0.16)
    # bark-scale lumps: displaced surface (less on thin parts)
    _, Xall = grid.box(grid.lo, grid.lo + (grid.n - 1) * grid.h)
    nz = (fbm3(Xall[..., 0] / 1.3, Xall[..., 1] / 1.3, Xall[..., 2] / 1.3, octaves=3, seed=SEED) - 0.5) * 0.2 \
        + (fbm3(Xall[..., 0] / 0.45, Xall[..., 1] / 0.45, Xall[..., 2] / 0.45, octaves=2, seed=SEED + 5) - 0.5) * 0.07
    F = F + nz
    del Xall
    V, T = SD.surface_nets(F, grid)
    # drop what is well under the ground
    gy = ground(V[:, 0], V[:, 2])
    under = V[:, 1] < gy - 0.45
    T = T[~np.all(under[T], axis=1)]
    V, T, _ = SD.compact(V, T)
    V = SD.project(V, F, grid, iters=3)
    keep = SD.boundary_vertices(T, len(V))
    V = SD.taubin(V, T, iters=3, keep=keep)
    V = SD.project(V, F, grid, iters=2, keep=keep)
    n_raw = len(T)
    V, T, _ = SD.decimate(V, T, BASE_TRIS)
    keep = SD.boundary_vertices(T, len(V))
    V = SD.project(V, F, grid, iters=2, keep=keep)
    from scipy import ndimage
    Fs = ndimage.gaussian_filter(F, 0.9)
    N = normalize(grid.gradient(Fs, V, eps=grid.h))
    # owners: the part each triangle belongs to (its bark mapping)
    parts = [trunk] + roots + limbs
    fam = {p.name: i for i, p in enumerate(parts)}
    cen = V[T].mean(axis=1)
    D = np.stack([p.dist(cen) for p in parts], axis=1)
    for p in minor:
        if p.family == 'trunk':              # burls belong to the trunk's mapping
            D[:, 0] = np.minimum(D[:, 0], p.dist(cen))
    owner = np.argmin(D, axis=1)
    uv_fns = [p.uv for p in parts]
    wraps = [True] * len(parts)
    cuv = SD.corner_uvs(V, T, owner, uv_fns, wraps)
    V2, T2, UV, src = SD.weld(V, T, cuv)
    N2 = N[src]
    # crotch measure: near two different parts at once
    Dv = np.stack([p.dist(V2) for p in parts], axis=1)
    Dv[:, 0] = np.minimum(Dv[:, 0], np.min(np.stack([p.dist(V2) for p in minor if p.family == 'trunk'], 1), axis=1))
    Ds = np.sort(np.maximum(Dv, 0), axis=1)
    crotch = np.exp(-Ds[:, 1] / 0.45) * np.clip(1 - Ds[:, 0] / 0.5, 0, 1)
    # cavity AO from the field along the normal
    ao_f = np.ones(len(V2))
    for i, dl in enumerate((0.25, 0.55, 1.0, 1.7)):
        f = grid.sample(F, V2 + N2 * dl)
        ao_f -= np.clip(dl - f, 0, None) / dl * (0.5 ** i) * 0.55
    ao_f = np.clip(ao_f, 0.25, 1)
    own_v = np.zeros(len(V2), np.int64)
    own_v[T2.reshape(-1)] = np.repeat(owner, 3)
    kinds = np.array(['trunk'] + ['root'] * len(roots) + ['limb'] * len(limbs))[own_v]
    gy = ground(V2[:, 0], V2[:, 2])
    hrel = V2[:, 1] - gy
    vis = CD.sky_visibility(V2, N2, M, n_rays=16)
    ao = ao_f ** 0.7 * (1 - 0.25 * crotch) * (1 - 0.3 * np.clip((0.25 - hrel) / 0.4, 0, 1)) * (0.68 + 0.32 * vis)
    ao = np.clip(ao, 0.22, 1.0)
    col = np.ones((len(V2), 3))
    g = np.clip((0.35 - hrel) / 0.5, 0, 1)[:, None]                      # earth at the foot
    col = col * (1 - g) + np.array([0.80, 0.74, 0.64]) * g
    damp = np.clip(-N2[:, 2] * 0.7 + 0.3, 0, 1) * np.clip(1.4 - V2[:, 1] / 4.0, 0, 1) * (kinds != 'limb')
    col = col * (1 - 0.3 * damp[:, None]) + np.array([0.78, 0.86, 0.70]) * 0.3 * damp[:, None]
    mossc = np.clip(crotch * 1.3, 0, 1)[:, None] * 0.45                 # moss pooled in the crotches
    col = col * (1 - mossc) + np.array([0.66, 0.80, 0.50]) * mossc
    moss = np.where(kinds == 'trunk', 0.1 + 0.4 * np.clip((V2[:, 1] - 4.4) / 1.2, 0, 1),
                    np.where(kinds == 'root', 0.12 + 0.18 * np.clip(1.2 - hrel, 0, 1), 0.45))
    moss = np.clip(moss + 0.85 * crotch + 0.25 * np.clip(-N2[:, 2], 0, 1) * (kinds != 'limb'), 0, 1)
    md = MeshData()
    C = np.concatenate([np.clip(col, 0, 1), ao[:, None]], axis=1)
    md.add(V2, N2, UV * TEXEL_PER_M / 256.0, T2, uv2=np.stack([np.full(len(V2), 7.0), moss], 1), col=C)
    stats = {'base_raw_tris': int(n_raw), 'base_tris': int(len(T2)), 'base_verts': int(len(V2)),
             'grid': [int(x) for x in grid.n]}
    return md, dict(grid=grid, F=F, trunk=trunk, roots=roots, limbs=limbs, defs=defs, stats=stats)


TRIM = {}   # limb name -> arc length where its swept tube starts (filled by build)


def _trim_limb(name, pts, rr, s0):
    """A limb's control points from arc length s0 on (the blended base covers what is before)."""
    sp = Spine(pts, rr, step=0.05)
    s_ctrl = np.interp(np.arange(len(pts)), sp.t, sp.s)
    q0, _, r0 = sp.point_at(s0 / sp.length)
    keep = [i for i in range(len(pts)) if s_ctrl[i] > s0 + 0.5]
    npts = [q0] + [pts[i] for i in keep]
    nr = [r0] + [rr[i] for i in keep]
    return npts, nr


def _limb_step(r0):
    return lambda f: 0.85 if r0 > 0.9 else 0.75


# Limbs, designed for the leaned camera (docs/knowledge/21 section 1: a point shows at screen
# y = height - 0.819 * z): the south limbs rise steeply so their foliage stays above the trunk
# and the shimenawa on screen, while the long low arms spread east and west.
LIMBS = [  # name, control points, radii, moss
    ('E', [[0.9, 4.3, 0.35], [4.4, 4.9, 1.4], [8.0, 6.7, 1.3], [11.4, 6.8, 2.9], [14.4, 8.6, 2.3], [16.6, 9.9, 1.0]], [1.35, 1.06, 0.8, 0.56, 0.36, 0.2], 0.7),
    ('W', [[-1.0, 4.1, 0.45], [-4.5, 5.1, 1.7], [-8.2, 5.2, 1.2], [-11.6, 7.5, 2.9], [-14.8, 8.1, 2.5], [-16.8, 9.7, 0.9]], [1.4, 1.1, 0.82, 0.56, 0.36, 0.2], 0.7),
    ('S', [[0.2, 4.7, 1.0], [0.5, 8.0, 3.0], [0.9, 11.4, 5.6], [1.0, 14.2, 7.8], [0.8, 15.6, 9.4]], [1.12, 0.86, 0.6, 0.4, 0.24], 0.4),
    ('NW', [[-0.6, 4.9, -0.7], [-3.4, 7.6, -3.6], [-6.6, 9.4, -5.4], [-9.4, 10.4, -6.4]], [1.2, 0.9, 0.6, 0.34], 0.5),
    ('NE', [[0.7, 4.9, -0.6], [3.6, 7.8, -3.2], [6.8, 9.6, -4.8], [9.4, 10.6, -5.8]], [1.15, 0.86, 0.56, 0.3], 0.5),
    ('N', [[0.0, 5.0, -0.6], [-0.3, 8.0, -4.6], [-0.7, 10.4, -8.4], [-1.0, 11.4, -10.8]], [1.05, 0.8, 0.52, 0.3], 0.4),
    ('L', [[0.1, 5.0, -0.1], [-0.4, 9.0, -0.8], [0.4, 13.2, -1.2], [0.0, 16.0, -1.4], [-0.3, 17.6, -1.6]], [1.32, 0.96, 0.6, 0.34, 0.2], 0.3),
    ('SEu', [[-0.1, 8.6, -0.6], [3.6, 11.6, 0.8], [6.6, 13.4, 1.2], [8.0, 14.0, 1.0]], [0.62, 0.46, 0.3, 0.18], 0.25),
    ('SWu', [[0.0, 10.0, -0.9], [-3.8, 12.8, 0.6], [-6.8, 14.0, 1.2], [-8.2, 14.4, 1.0]], [0.56, 0.42, 0.28, 0.16], 0.25),
    ('SEs', [[0.5, 8.0, 3.0], [3.6, 10.0, 5.0], [6.4, 11.6, 6.6], [7.8, 12.2, 7.2]], [0.5, 0.4, 0.28, 0.16], 0.3),
    ('SWs', [[0.5, 8.0, 3.0], [-3.0, 9.8, 5.2], [-6.0, 11.4, 6.8], [-7.4, 12.0, 7.4]], [0.5, 0.4, 0.28, 0.16], 0.3),
]


def skeleton(defs):
    """The limbs as swept tubes, each starting a little inside the end of its blended base part
    (radius eased from 96.5 % so the tube surfaces out of the blend at a shallow angle; bark v
    continues from the base part)."""
    from ..core import smoothstep
    limbs = []
    named = {}
    for name, pts, rr, moss in LIMBS:
        s0 = 0.0
        s_cut = 0.0
        if name in defs:
            s_cut = defs[name][2]
            s0 = max(s_cut - 0.8, 0.0)
            pts, rr = _trim_limb(name, pts, rr, s0)

        def rfun(th, k, frac, sp, s0=s0, sc=s_cut):
            return np.full(len(th), sp.rad[k] * (0.965 + 0.035 * float(smoothstep(sc, sc + 1.0, sp.s[k] + s0))))
        L = WD.Limb(name, pts, rr, kind='limb', moss=moss, n_around=14 if rr[0] > 0.9 else 10,
                    step_fn=_limb_step(rr[0]), rfun=rfun)
        L.tags['s0'] = s0
        limbs.append(L)
        named[name] = L
    return limbs, named


def _shift_v(L, dv):
    for k in range(len(L.md.uv)):
        L.md.uv[k] = L.md.uv[k] + np.array([0.0, dv])


# ------------------------------------------------------------------------------- the crown
def masses():
    """Low shelves on the long arms east, west and north; a high arch on the south side (so the
    trunk and the shimenawa stay in view under it); a mid layer; a dome; fringe masses to break
    the outline."""
    M = []

    def add(c, r, **kw):
        kw.setdefault('seed', len(M) * 31 + 5)
        M.append(CD.Mass(c, r, **kw))
    # tier A: lobes hanging on the low arms, at different heights, undersides lumpy (not shelves)
    add((11.4, 9.0, 3.6), (4.2, 2.3, 3.8), flat=0.3, sag=0.7, lump=0.2)          # E inner
    add((15.4, 10.6, 1.6), (3.4, 2.2, 3.4), flat=0.3, sag=0.8, lump=0.2)         # E outer
    add((9.4, 10.9, -5.6), (4.4, 2.5, 4.2), flat=0.35, sag=0.4, lump=0.18)       # NE
    add((-11.8, 8.7, 3.0), (4.4, 2.4, 3.9), flat=0.3, sag=0.7, lump=0.2)         # W inner
    add((-15.6, 10.2, 1.2), (3.2, 2.1, 3.2), flat=0.3, sag=0.8, lump=0.2)        # W outer
    add((-9.6, 10.2, -6.0), (4.4, 2.5, 4.2), flat=0.35, sag=0.4, lump=0.18)      # NW
    add((-1.0, 11.8, -11.0), (5.6, 2.6, 4.0), flat=0.35, sag=0.3, lump=0.18)     # N
    # the south arch, high
    add((0.8, 16.0, 8.5), (5.0, 2.6, 3.6), flat=0.4, sag=0.3, lump=0.16)         # S
    add((7.4, 12.2, 7.2), (3.6, 2.2, 3.0), flat=0.35, sag=0.5, lump=0.18)        # SE
    add((-7.6, 12.8, 7.4), (3.8, 2.2, 3.0), flat=0.35, sag=0.5, lump=0.18)       # SW
    # tier B
    add((-7.0, 14.4, 1.6), (5.2, 2.8, 4.4), flat=0.35, lump=0.16)
    add((7.4, 13.8, 1.0), (5.4, 2.8, 4.4), flat=0.35, lump=0.16)
    add((0.0, 14.8, -6.4), (6.0, 3.0, 4.6), flat=0.35, lump=0.16)
    add((-1.0, 15.6, 4.6), (4.4, 2.5, 3.4), flat=0.35, lump=0.16)
    # tier C: the dome, one big head and two shoulders
    add((-0.8, 18.8, -1.2), (6.8, 3.4, 5.6), flat=0.3, clumps=0.45, lump=0.14)
    add((5.2, 17.0, 2.4), (3.8, 2.4, 3.4), flat=0.3, lump=0.18)
    add((-5.8, 16.6, -3.2), (3.6, 2.4, 3.4), flat=0.3, lump=0.18)
    add((2.4, 21.2, -2.8), (2.6, 1.5, 2.4), flat=0.3, clumps=0.3)
    # fringe, breaking the outline
    add((17.6, 8.8, -0.8), (2.2, 1.6, 2.2), flat=0.3, clumps=0.3, sag=0.5)
    add((-17.8, 9.4, -0.4), (2.1, 1.5, 2.1), flat=0.3, clumps=0.3, sag=0.5)
    add((12.0, 12.8, 6.4), (2.0, 1.5, 2.0), flat=0.3, clumps=0.3)
    add((-11.4, 12.0, 6.6), (2.4, 1.6, 2.2), flat=0.3, clumps=0.3)
    return M


def fern_tile(W, seed):
    """ノキシノブ: a tuft of strap-shaped fronds fanning up from a point."""
    R = rng(seed)
    H = W
    val = np.zeros((H, W))
    cov = np.zeros((H, W), bool)
    base = (W * 0.5, H * 0.92)
    for k in range(int(R.integers(4, 7))):
        a = -math.pi / 2 + R.normal(0, 0.75)
        L = R.uniform(H * 0.5, H * 0.85)
        m, uu = LV._leaf_mask(H, W, base[0] + math.cos(a) * L * 0.5, base[1] + math.sin(a) * L * 0.5, a, L, R.uniform(1.6, 2.2))
        val[m] = np.where(uu[m] > 0.3, LV.TOP, LV.BODY)
        cov |= m
    return LV._finish(val, cov)


def leaf_tiles():
    S = SEED
    specs = {
        'mass': [(LV.clumps, dict(W=24, seed=S + 100 + i, r=(3.6, 5.2), gloss=0.3, tips=9, tip_len=(2.0, 3.4), fill=1.25,
                                  sep_p=0.5, top_p=0.35, scallop=(6, 9))) for i in range(6)]
              + [(LV.clumps, dict(W=24, seed=S + 150 + i, r=(3.0, 4.6), gloss=0.3, tips=10, tip_len=(2.0, 3.2), fill=1.4,
                                  sep_p=0.5, top_p=0.3, scallop=(6, 9), ragged=0.3, lobes=3)) for i in range(4)],
        'small': [(LV.clumps, dict(W=16, seed=S + 200 + i, r=(2.6, 3.8), gloss=0.3, tips=6, shape=0.40, fill=1.3,
                                   sep_p=0.8, top_p=0.5)) for i in range(5)],
        'interior': [(LV.clumps, dict(W=24, seed=S + 300 + i, r=(2.6, 4.0), gloss=0.0, tips=2, shape=0.46, ragged=0.1, top_p=0.3, sep_p=0.4)) for i in range(2)],
        'fern': [(fern_tile, dict(W=12, seed=S + 500 + i)) for i in range(3)],
        'moss': [(LV.clumps, dict(W=9, seed=S + 600 + i, r=(1.2, 2.0), gloss=0.0, tips=2, shape=0.42, aspect=0.6, top_p=0.6)) for i in range(2)],
    }
    for d in range(8):
        specs[f'spray{d}'] = [(LV.spray, dict(W=18, seed=S + 400 + d * 10, direction=-d * math.pi / 4, n_twigs=3,
                                               gloss=0.15, reach=0.46))]
    return FO.build_tiles(specs)


def _tint(hexcol, body=LV.BODY):
    """The card tint that makes the tile's BODY tone come out as hexcol."""
    c = np.array(hex_rgb(hexcol), np.float64) / 255.0
    return np.clip(c / body, 0, 1)


def crown(M, sets):
    return CD.crown_cards(M, (0.0, 12.5, 0.5), (17.0, 7.0, 15.5), sets, seed=SEED + 9,
                          base_tint=_tint('#566e3e'), young_tint=_tint('#6b7944'), old_tint=_tint('#3a5646'),
                          base_y=7.0, top_y=21.0, overlap=1.05, clump_overlap=0.95, fill_density=0.6,
                          interior_frac=0.5, env_k=0.2, clump_k=0.1, up_bias=0.2, max_cards=3300)


def epiphytes(R, named, sets):
    """Ferns and moss cushions on the tops of the big low limbs (cards, normal up)."""
    out = []
    for key, n_f, n_m in (('E', 9, 10), ('W', 9, 10), ('NW', 4, 5), ('NE', 4, 5), ('N', 3, 4)):
        sp = named[key].spine
        for i in range(n_f + n_m):
            f = R.uniform(0.08, 0.75)
            p, t, r = sp.point_at(f)
            side = normalize(np.cross(t, [0, 1, 0]) + 1e-6)
            top = p + side * R.normal(0, r * 0.35) + np.array([0, r * 0.92, 0])
            is_fern = i < n_f
            lst = sets['fern' if is_fern else 'moss']
            tl = lst[R.integers(0, len(lst))]
            tint = _tint('#5f7a3c') if is_fern else _tint('#4f6232')
            pos = top + np.array([0, tl[2] / PPM * 0.35, 0]) if is_fern else top
            out.append(CD.Card(pos, normalize(np.array([0.0, 1.0, 0.25])), tl[1], tl[2], tl[0], 0.95,
                               np.clip(tint * (1 + R.normal(0, 0.03)), 0, 1), 0.15 if is_fern else 0.0, 'epi', 2.0))
    return out


# ------------------------------------------------------------------------------- wood colour, ao, moss
def wood_colour(P, N, L):
    """Limbs and branches (the base has its own): damp green on the north side low down, paler
    high up."""
    y = P[:, 1]
    col = np.ones((len(P), 3))
    damp = np.clip(-N[:, 2] * 0.7 + 0.3, 0, 1) * np.clip(1.4 - y / 6.0, 0, 1) * 0.5 + np.clip(N[:, 1], 0, 1) * 0.35
    col = col * (1 - 0.35 * damp[:, None]) + np.array([0.78, 0.86, 0.70]) * 0.35 * damp[:, None]
    hi = np.clip((y - 8.0) / 8.0, 0, 1)[:, None]
    col = col * (1 - hi * 0.3) + np.array([1.06, 1.04, 1.02]) * hi * 0.3
    return col


def wood_ao(P, N, L):
    ao = np.ones(len(P))
    ao -= 0.18 * np.clip(-N[:, 1], 0, 1)
    f = np.linalg.norm(P[:, [0, 2]], axis=1)
    ao -= 0.2 * np.clip(1 - f / 4.5, 0, 1) * np.clip(-N[:, 1] + 0.5, 0, 1)
    return np.clip(ao, 0.2, 1)


def wood_moss(P, N, L):
    return np.full(len(P), L.moss)


# ------------------------------------------------------------------------------- the shimenawa
def _tube_uv(info, n_rows, u_scale=0.5, v_div=32.0):
    """uv for a tube made by tube(): u around (0..u_scale), v along (texels / v_div)."""
    k = info['P'].shape[1]
    m = info['P'].shape[0]
    U = info['U'] / np.maximum(info['U'][:, -1:], 1e-6) * u_scale
    V = info['V'] * TEXEL_PER_M / v_div
    uv = np.stack([U.reshape(-1), V.reshape(-1)], axis=1)
    extra = n_rows - m * k
    if extra > 0:
        uv = np.vstack([uv, np.tile([u_scale * 0.5, V.max()], (extra, 1))])
    return uv


def surface_rho(base, y, theta):
    """Distance from the trunk axis to the outermost surface of the blended base at height y."""
    grid, F, trunk = base['grid'], base['F'], base['trunk']
    cx, cz = trunk.axis_at(y)
    rho = np.arange(0.5, 9.0, 0.02)
    d = _dir(theta)
    P = np.stack([cx + d[0] * rho, np.full(len(rho), y), cz + d[2] * rho], axis=1)
    f = grid.sample(F, P)
    inside = np.where(f < 0)[0]
    if len(inside) == 0:
        return float(trunk_R(theta, y))
    i = int(inside[-1])
    if i + 1 < len(rho):
        a, b = f[i], f[i + 1]
        return float(rho[i] + (rho[i + 1] - rho[i]) * a / (a - b))
    return float(rho[i])


def shimenawa(base):
    """A thick twisted straw rope around the trunk at ROPE_Y, pressed onto the bark (over the
    buttress ridges), sagging a little in front, with a bundled knot and shide hanging in front."""
    trunk = base['trunk']
    cx, cz = trunk.axis_at(ROPE_Y)
    c = np.array([cx, ROPE_Y, cz])
    rope_r = 0.24
    th = np.linspace(0, 2 * math.pi, 97)
    # a tied rope does not dip into every hollow: the upper envelope of the surface, smoothed
    from scipy.ndimage import gaussian_filter1d, maximum_filter1d
    rho = np.array([surface_rho(base, ROPE_Y, t) for t in th[:-1]])
    rho = gaussian_filter1d(maximum_filter1d(rho, 9, mode='wrap'), 3.0, mode='wrap')
    rho = np.append(rho, rho[0])
    pts = []
    for t, r_ in zip(th, rho):
        rr = r_ + rope_r * 0.8
        d = _dir(t)
        sag = 0.22 * max(0.0, -math.cos(t)) ** 2
        pts.append(c + d * rr + np.array([0, -sag, 0]))
    spine = Spine(pts, [rope_r] * len(pts), step=0.3)
    md, info = tube(spine, n_around=7, cap_end=False)
    a = md.arrays()
    rope = MeshData()
    rope.add(a['p'], a['n'], _tube_uv(info, len(a['p'])), a['idx'], uv2=np.tile([0.0, 0.0], (len(a['p']), 1)),
             col=np.ones((len(a['p']), 4)))
    front_r = surface_rho(base, ROPE_Y - 0.24, math.pi)
    knot_c = c + np.array([0, -0.24, front_r + rope_r * 1.5])
    for dx, Ln in ((-0.22, 0.55), (0.18, 0.72)):                         # two tails hanging
        s2 = Spine([knot_c + [dx, 0.05, 0.02], knot_c + [dx * 1.3, -Ln * 0.5, 0.08], knot_c + [dx * 1.5, -Ln, 0.12]],
                   [0.11, 0.09, 0.05], step=0.1)
        m2, i2 = tube(s2, n_around=6, cap_end=True)
        a2 = m2.arrays()
        rope.add(a2['p'], a2['n'], _tube_uv(i2, len(a2['p'])), a2['idx'], uv2=np.zeros((len(a2['p']), 2)),
                 col=np.ones((len(a2['p']), 4)))
    s3 = Spine([knot_c + [-0.34, 0.0, -0.06], knot_c + [0.0, 0.03, 0.06], knot_c + [0.34, 0.0, -0.06]],
               [0.2, 0.25, 0.2], step=0.08)                              # the bundle
    m3, i3 = tube(s3, n_around=8, cap_end=True, cap_start=True)
    a3 = m3.arrays()
    rope.add(a3['p'], a3['n'], _tube_uv(i3, len(a3['p'])), a3['idx'], uv2=np.zeros((len(a3['p']), 2)),
             col=np.ones((len(a3['p']), 4)))
    shide = MeshData()
    for ang in (math.pi - 0.62, math.pi - 0.31, math.pi + 0.31, math.pi + 0.62):
        rr = surface_rho(base, ROPE_Y - 0.3, ang) + rope_r * 1.4
        d = _dir(ang)
        sag = 0.22 * max(0.0, -math.cos(ang)) ** 2
        shide.merge(zigzag(c + d * rr + np.array([0, -sag - rope_r * 0.6, 0]), d))
    for side in (-1, 1):
        shide.merge(zigzag(knot_c + np.array([side * 0.48, -0.16, 0.05]), np.array([0.0, 0.0, 1.0])))
    return rope, shide


def zigzag(top, facing, width=0.3, seg=0.19, n=4, thick=0.03):
    """A shide: a paper strip cut and folded into n steps zigzagging down; both sides drawn."""
    facing = normalize(np.asarray(facing, np.float64) * np.array([1, 0, 1]))
    right = normalize(np.cross([0, 1, 0], facing))
    pts, nrm, tri = [], [], []
    for i in range(n):
        x0 = (width * 0.45 if i % 2 else 0.0) - width * 0.25
        a = top + right * x0 + np.array([0, -i * seg, 0]) + facing * thick * (i % 2)
        quad = [a, a + right * width * 0.62, a + right * width * 0.62 + np.array([0, -seg, 0]), a + np.array([0, -seg, 0])]
        for sgn in (1, -1):
            b = len(pts)
            for q in quad:
                pts.append(q + facing * 0.004 * sgn)
                nrm.append(facing * sgn)
            t1, t2 = (b, b + 1, b + 2), (b, b + 2, b + 3)
            pa, pb, pc = (np.array(pts[t]) for t in t1)
            if np.dot(np.cross(pb - pa, pc - pa), facing * sgn) < 0:
                t1, t2 = (b, b + 2, b + 1), (b, b + 3, b + 2)
            tri += [t1, t2]
    md = MeshData()
    k = len(pts)
    md.add(np.array(pts), np.array(nrm), np.zeros((k, 2)), np.array(tri), uv2=np.tile([6.0, 0.0], (k, 1)),
           col=np.tile([0.95, 0.94, 0.90, 1.0], (k, 1)))
    return md


def rope_texture(seed=SEED):
    """Twisted straw: diagonal strands, 32 x 32, tiles both ways."""
    R = rng(seed)
    S = 32
    ys, xs = np.mgrid[0:S, 0:S]
    pal = [np.array(hex_rgb(h), np.float64) for h in ('#7e6a43', '#a08a58', '#bba56c', '#cdb87e')]
    strand = ((xs * 2 + ys) // 6) % 4
    v = np.select([strand == 0, strand == 1, strand == 2, strand == 3], [1, 2, 3, 2])
    v = np.where(((xs * 2 + ys) % 6) == 0, 0, v)
    v = np.where((R.uniform(size=(S, S)) < 0.08) & (v > 0), v - 1, v)
    img = np.zeros((S, S, 3))
    for i in range(4):
        img[v == i] = pal[i]
    return img.astype(np.uint8)


# ------------------------------------------------------------------------------- build
def build(out):
    from ..terrain import ground_fn
    R = rng(SEED)
    ground, gnote = ground_fn('camphor')
    M = masses()
    base_md, base = base_mesh(R, M, ground)
    limbs, named = skeleton(base['defs'])
    for key, n, fr, ln in (('E', 3, (0.55, 0.95), (2.4, 4.0)), ('W', 3, (0.55, 0.95), (2.4, 4.0)),
                           ('S', 2, (0.5, 0.9), (2.0, 3.2)), ('NW', 2, (0.5, 0.9), (2.4, 3.6)),
                           ('NE', 2, (0.5, 0.9), (2.4, 3.6)), ('N', 2, (0.5, 0.9), (2.4, 3.6)),
                           ('L', 3, (0.45, 0.9), (2.4, 4.0)), ('SEu', 2, (0.5, 0.9), (2.0, 3.0)),
                           ('SWu', 2, (0.5, 0.9), (2.0, 3.0))):
        L = named[key]
        WD.build_limb(L)
        _shift_v(L, L.tags['s0'])
        for b in WD.offshoots(L, R, n, frac_range=fr, length=ln, radius_k=(0.4, 0.6), up_bias=0.45, name=key + 'b',
                              min_r=0.06, moss=0.15, segs=3):
            b.n_around = 7
            b.step = 0.7
            limbs.append(b)
    for L in limbs:
        if L.spine is None:
            WD.build_limb(L)
            if 's0' in L.tags:
                _shift_v(L, L.tags['s0'])
    a = out.asset(NAME, 'trees')
    bark_res = a.texture('bark', WD.bark_texture(SEED, size=256, ridge=('#6c6458', '#7b7365', '#8a8272'), lip='#999080',
                                                 fissure='#433b35', deep='#312b27'))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                        textures={'albedo_tex': bark_res})

    def ao_fn(P, N, L):
        # baked AO: undersides and the inner limbs, times how much sky the bark sees past the crown
        return wood_ao(P, N, L) * (0.45 + 0.55 * CD.sky_visibility(P, N, M, n_rays=16))
    wood = WD.wood_mesh(limbs, tex_size=256, colour_fn=wood_colour, ao_fn=ao_fn, moss_fn=wood_moss)
    wood.merge(base_md)
    rope, shide = shimenawa(base)
    rope_res = a.texture('rope', rope_texture())
    m_rope = a.material('rope', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': rope_res})
    m_paper = a.material('shide', 'toon_solid.gdshader', params={'porosity': 0.6})
    atlas, rects, sets = leaf_tiles()
    cards = crown(M, sets)
    vis = CD.sky_visibility(np.array([c.p for c in cards]), np.array([c.n for c in cards]), M, n_rays=16)
    for c, v in zip(cards, vis):
        c.ao = float(np.clip(c.ao * (0.62 + 0.38 * v), 0.2, 1.0))
    cards += epiphytes(R, named, sets)
    if os.environ.get('W3A_DEBUG_KINDS'):
        dbg = {'clump': (0.3, 0.9, 0.3), 'fill': (0.3, 0.4, 1.0), 'interior': (1.0, 0.2, 0.2), 'spray': (1.0, 1.0, 0.2), 'epi': (1.0, 0.2, 1.0)}
        for c in cards:
            c.tint = np.array(dbg.get(c.kind, (1, 1, 1)))
            c.ao = 1.0
    leaf_md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': leaf_res})
    wood_mesh = a.mesh('wood', [(m_bark, wood), (m_rope, rope), (m_paper, shide)])
    leaf_mesh = a.mesh('leaves', [(m_leaf, leaf_md)], custom_aabb=[[-20, 4, -20], [40, 20, 40]])
    a.scene([
        {'name': 'Wood', 'type': 'mesh', 'mesh': wood_mesh},
        {'name': 'Leaves', 'type': 'mesh', 'mesh': leaf_mesh, 'extra_cull_margin': 4.0},
    ], meta={'w3a_kind': 'tree', 'w3a_species': 'camphor'})
    # the half-faded tree (遠化): the crown and the wood above the shimenawa drained and lifted; what
    # the rope protects (the trunk below it, the rope and the shide) keeps its colour
    from ..props.kit import pale_colour
    wa = wood.arrays()
    t = np.clip((wa['p'][:, 1] - (ROPE_Y + 0.15)) / 0.6, 0, 1)[:, None]
    col_far = wa['col'].copy()
    col_far[:, :3] = wa['col'][:, :3] * (1 - t) + pale_colour(wa['col'][:, :3]) * t
    wood_far = MeshData()
    wood_far.add(wa['p'], wa['n'], wa['uv'], wa['idx'], uv2=wa['uv2'], col=col_far)
    la = leaf_md.arrays()
    leaf_far = MeshData()
    lcol = la['col'].copy()
    lcol[:, :3] = pale_colour(la['col'][:, :3] * 0.8) / 0.8
    leaf_far.add(la['p'], la['n'], la['uv'], la['idx'], uv2=la['uv2'], col=np.clip(lcol, 0, 1), cus=la['cus'])
    bark_far = a.texture('bark_far', pale_colour(WD.bark_texture(SEED, size=256, ridge=('#6c6458', '#7b7365', '#8a8272'),
                                                                 lip='#999080', fissure='#433b35', deep='#312b27') / 255.0) * 255.0)
    m_bark_far = a.material('bark_far', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                            textures={'albedo_tex': bark_far})
    # the far bark texture applies above the rope only: split the wood by height
    lo_idx = wa['idx'][np.max(wa['p'][wa['idx']][:, :, 1], axis=1) < ROPE_Y + 0.4]
    hi_idx = wa['idx'][np.max(wa['p'][wa['idx']][:, :, 1], axis=1) >= ROPE_Y + 0.4]
    w_lo, w_hi = MeshData(), MeshData()
    w_lo.add(wa['p'], wa['n'], wa['uv'], lo_idx, uv2=wa['uv2'], col=col_far)
    w_hi.add(wa['p'], wa['n'], wa['uv'], hi_idx, uv2=wa['uv2'], col=col_far)
    wood_far_mesh = a.mesh('wood_far', [(m_bark, w_lo), (m_bark_far, w_hi), (m_rope, rope), (m_paper, shide)])
    leaf_far_mesh = a.mesh('leaves_far', [(m_leaf, leaf_far)], custom_aabb=[[-20, 4, -20], [40, 20, 40]])
    a.scene([
        {'name': 'Wood', 'type': 'mesh', 'mesh': wood_far_mesh},
        {'name': 'Leaves', 'type': 'mesh', 'mesh': leaf_far_mesh, 'extra_cull_margin': 4.0},
    ], meta={'w3a_kind': 'tree', 'w3a_species': 'camphor', 'w3a_far': True}, key='far')
    foot = [[0.0, 0.0, 3.6]]
    for r in base['roots']:                     # where a root stands higher than her shin
        for s_ in np.arange(0.0, r.s[-1], 1.0):
            j = int(np.searchsorted(r.s, s_))
            q = r.Q[min(j, len(r.Q) - 1)]
            top = q[1] + r.r[min(j, len(r.r) - 1)] * r.sv[min(j, len(r.sv) - 1)] - float(ground(q[0], q[2]))
            if top > 0.45 and np.hypot(q[0], q[2]) > 3.4:
                foot.append([round(float(q[0]), 2), round(float(q[2]), 2), round(float(r.r[min(j, len(r.r) - 1)] * 1.05), 2)])
    a.catalog = {
        'category': 'tree',
        'footprint': foot,
        'height': 21.5,
        'crown': {'centre': [0.0, 13.0, 0.5], 'radius': 17.0, 'base': 7.0},
        'tags': ['landmark', 'climbable', 'sacred'],
        'variants': {'far': 'res://world3d/assets/trees/camphor_great/camphor_great_far.tscn'},
        'anchors': {'shimenawa_front': [0.0, ROPE_Y - 0.2, round(surface_rho(base, ROPE_Y, math.pi) + 0.3, 2)]},
        'notes': ('御神木. Trunk 6.5 m across; buttress roots fitted to the ground of the ' + gnote +
                  ' (do not rotate; rebuild after the terrain changes); low limbs reach 16.5 m. Shimenawa at %.2f m.' % ROPE_Y),
    }
    nt = len(wood.arrays()['idx']) + len(rope.arrays()['idx']) + len(shide.arrays()['idx'])
    return {'cards': len(cards), 'wood_tris': nt, 'leaf_tris': len(cards) * 2, 'atlas': list(atlas.shape[:2]),
            **base['stats']}
