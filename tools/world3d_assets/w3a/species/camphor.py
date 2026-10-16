"""The giant camphor 御神木: the hero of the art sample.

Scale (lead's brief): crown spread about 34 m (radius ~17), crown base 6-8 m, top 20-22 m; trunk
about 6.5 m across, gnarled and twisting, burls and deep furrows; buttress roots spreading to
~9.5 m and sinking into the ground; massive low limbs reaching out 14-17 m with moss and small
ferns on them; a shimenawa with shide around the trunk (the only "cannot take" marker).

One organism: the limbs grow out of the trunk, the branches out of the limbs and into the leaf
masses they carry; the lowest masses hang on the limb ends, so the crown's lower edge shows the
limbs going in. Budget (contract v1.6): <= 60k triangles for the great camphor.

Round 4b (lead 2026-10-15):
  * the bark is drawn as flowing grain (wood.bark_flow_texture) and follows the trunk's twist; the
    trunk's relief is flutes running down it like wax, not lumps (12:55: the bark read as bricks);
  * a walkable branch path (realm-and-climb draft §3): the lowest limb (G) comes down to the ground
    north of the shrine and lies there half sunk, a mossy ramp; up it to the bowl on top of the
    trunk, up the climbing limb P2 east, back west along P3 over the front of the trunk, round on
    P4 to the nest (the leader's fork) under the crown top. Each is 1-1.5 m wide with a bright moss
    carpet on top (its own mesh), slopes under 27 degrees; the other limbs are thinner or end in
    leaves. Exported: catalog 'climb' (the walk line, widths, the nest) and anchors 'perch_crow'
    (eight perches up the path, each a branch or two above the last) and 'perch_crow_lure';
  * the crown: leaves in clumps (each clump's top lit, its underside dark), fewer fill cards between
    them so gaps show; leaves cleared off the path and a window round the nest.
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
BASE_TRIS = 16000                  # decimation target for the base surface (60k budget since v1.6)
TWIST = 0.1                        # rad per metre (the lobes and the bark grain turn together)
ROPE_Y = 2.45                      # shimenawa height
LIMB_U = 0.62                      # the bark round a limb spread wider (fewer grain lines across it)

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
    trunk = SD.TrunkSDF('trunk', TRUNK_PTS, trunk_R, trunk_ref, y_lo=-2.6, y_top=TRUNK_TOP + 0.2, twist=TWIST)
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
    for name in ('E', 'W', 'P2', 'NE', 'N', 'L', 'G'):
        pts, rr = lim[name]
        s_exit = limb_cut(pts, rr, [probe])
        defs[name] = (pts, rr, s_exit + (2.2 if name == 'G' else 1.6))
    from .. import sdf as SD2
    parents = {'P3': 'P2', 'P4': 'P3', 'P5': 'P4', 'SEu': 'L', 'SWu': 'L'}
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
    # bark-scale relief. On the trunk: flutes running up it along its twist, long and soft, like wax
    # that ran down (lead 12:55: no lumps, no steps in the outline); noise sampled on a cylinder
    # (cos, sin of the twisted angle) so it has no seam. On the roots and limbs: gentle lumps.
    _, Xall = grid.box(grid.lo, grid.lo + (grid.n - 1) * grid.h)
    Yv = Xall[..., 1]
    ax_x, ax_z = trunk.axis_at(Yv)
    thv = np.arctan2(-(Xall[..., 0] - ax_x), -(Xall[..., 2] - ax_z)) + TWIST * Yv
    rrv = trunk_ref(np.clip(Yv, -1.0, TRUNK_TOP)) / 0.62
    # (round 5, G5R3-5 "still too hard, like bricks / like folded paper": the flutes were deep enough to
    # fold the trunk into planes; now a gentle undulation, the bark's lines carry the rest)
    flute = (fbm3(np.cos(thv) * rrv * 1.4, np.sin(thv) * rrv * 1.4, Yv / 2.2, octaves=3, seed=SEED) - 0.5) * 0.09
    lumps = (fbm3(Xall[..., 0] / 1.3, Yv / 1.3, Xall[..., 2] / 1.3, octaves=3, seed=SEED + 3) - 0.5) * 0.12 \
        + (fbm3(Xall[..., 0] / 0.5, Yv / 0.5, Xall[..., 2] / 0.5, octaves=2, seed=SEED + 5) - 0.5) * 0.03
    wt = np.exp(-np.maximum(trunk.dist(Xall), 0.0) / 0.7) * np.clip((TRUNK_TOP + 0.3 - Yv) / 1.2, 0, 1)
    F = F + wt * flute + (1 - wt) * lumps
    del Xall, Yv, ax_x, ax_z, thv, rrv, flute, lumps, wt
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
    is_limb = np.array([False] * (1 + len(roots)) + [True] * len(limbs))[owner]
    cuv[is_limb, :, 0] *= LIMB_U
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
    # green damp at the foot all round (and up the shaded sides), the rope pressing a ring of shade
    # into the bark under it
    foot = np.clip((1.6 - hrel) / 1.4, 0, 1) * (kinds != 'limb') * (0.55 + 0.45 * np.clip(-N2[:, 2] + 0.4, 0, 1))
    col = col * (1 - 0.32 * foot[:, None]) + np.array([0.70, 0.82, 0.56]) * 0.32 * foot[:, None]
    band = np.exp(-((ROPE_Y - 0.28 - V2[:, 1]) / 0.2) ** 2) * (kinds == 'trunk')
    col = col * (1 - 0.3 * band[:, None])
    moss = np.where(kinds == 'trunk', 0.1 + 0.4 * np.clip((V2[:, 1] - 4.4) / 1.2, 0, 1),
                    np.where(kinds == 'root', 0.3 + 0.5 * np.clip(1.5 - hrel, 0, 1), 0.45))
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
    if not keep:
        keep = [len(pts) - 1]
    npts = [q0] + [pts[i] for i in keep]
    nr = [r0] + [rr[i] for i in keep]
    return npts, nr


def _limb_step(r0):
    return lambda f: 0.85 if r0 > 0.9 else 0.75


# Limbs, designed for the leaned camera (docs/knowledge/21 section 1: a point shows at screen
# y = height - 0.819 * z). Round 4b: the south arch limb S became the climbing limb P2 (east from
# the bowl on top of the trunk); P3 comes back west over the front of the trunk and P4 rounds to the
# nest in the leader's fork; G is the low limb that lies on the ground north of the shrine (fitted
# to the terrain at build time, resolve_limbs). Sx and SWs carry the south arch and the south-west
# masses off P3; Na, Nb, Nc are the leader's fork round the nest.
LIMBS_SPEC = [  # name, control points, radii, moss
    ('E', [[0.9, 4.3, 0.35], [4.4, 4.9, 1.4], [8.0, 6.7, 1.3], [11.4, 6.8, 2.9], [14.4, 8.6, 2.3], [16.6, 9.9, 1.0]], [1.35, 1.06, 0.8, 0.56, 0.36, 0.2], 0.7),
    # W leaves north-west and high, so on screen it stays well above G (they read as one limb when
    # W ran west over G: 4b first build)
    ('W', [[-1.0, 4.6, -0.5], [-4.2, 6.5, -2.4], [-7.8, 7.5, -3.2], [-11.4, 8.4, -2.6], [-14.6, 9.0, -1.6], [-16.6, 10.0, -2.4]], [1.3, 1.0, 0.78, 0.56, 0.36, 0.2], 0.7),
    ('P2', [[0.2, 4.9, 0.9], [2.6, 6.4, 1.9], [5.0, 7.7, 2.7], [7.0, 8.6, 3.2], [8.5, 9.5, 3.8], [8.9, 10.6, 5.2], [8.3, 11.6, 6.6]], [1.05, 0.9, 0.78, 0.68, 0.5, 0.34, 0.2], 0.6),
    ('NE', [[0.7, 4.9, -0.6], [3.6, 7.8, -3.2], [6.8, 9.6, -4.8], [9.4, 10.6, -5.8]], [1.15, 0.86, 0.56, 0.3], 0.5),
    ('N', [[0.0, 5.0, -0.6], [-0.3, 8.0, -4.6], [-0.7, 10.4, -8.4], [-1.0, 11.4, -10.8]], [1.05, 0.8, 0.52, 0.3], 0.4),
    ('L', [[0.1, 5.0, -0.1], [-0.4, 9.0, -0.8], [0.4, 13.2, -1.2], [0.0, 16.0, -1.4], [-0.3, 18.0, -1.2], [-0.5, 19.4, -0.9]], [1.32, 0.96, 0.72, 0.56, 0.3, 0.16], 0.3),
    ('SEu', [[-0.1, 8.6, -0.6], [3.6, 11.6, 0.8], [6.6, 13.4, 1.2], [8.0, 14.0, 1.0]], [0.62, 0.46, 0.3, 0.18], 0.25),
    ('SWu', [[0.0, 10.0, -0.9], [-3.6, 12.4, -2.4], [-6.6, 13.6, -2.2], [-8.0, 14.0, -1.8]], [0.56, 0.42, 0.28, 0.16], 0.25),
    ('P3', [[6.6, 8.75, 3.25], [4.4, 9.9, 4.1], [1.6, 11.1, 4.4], [-1.2, 12.3, 3.9], [-3.5, 13.35, 2.8], [-4.8, 14.15, 1.4]], [0.7, 0.66, 0.62, 0.58, 0.55, 0.52], 0.6),
    ('P4', [[-4.7, 14.1, 1.5], [-5.5, 15.0, -0.5], [-4.2, 15.7, -2.1], [-2.2, 16.2, -2.0], [-0.6, 16.35, -1.5]], [0.5, 0.48, 0.46, 0.45, 0.44], 0.6),
    # P5 out of the leader's fork, south-east and up to the crown top: the standing fork (枝窝) at
    # its end, the crows' nest beside it in the twigs Ne / Nf / Ng
    ('P5', [[-0.7, 16.35, -1.45], [0.9, 17.2, -0.3], [2.4, 18.0, 0.5], [3.8, 18.6, -0.1], [4.6, 19.0, -1.0]], [0.45, 0.44, 0.43, 0.42, 0.42], 0.6),
    ('Ne', [[4.6, 19.0, -1.0], [5.6, 20.2, -1.6], [6.0, 21.0, -2.0]], [0.3, 0.2, 0.1], 0.3),
    ('Nf', [[4.5, 19.0, -1.1], [4.2, 20.3, -2.2], [4.0, 21.1, -2.8]], [0.28, 0.18, 0.09], 0.3),
    ('Ng', [[4.7, 19.0, -0.9], [5.4, 19.9, 0.2], [5.8, 20.6, 0.8]], [0.26, 0.17, 0.08], 0.3),
    ('Sx', [[1.2, 11.2, 4.3], [1.0, 13.0, 6.2], [0.9, 14.6, 7.9], [0.8, 15.7, 9.2]], [0.42, 0.34, 0.24, 0.15], 0.3),
    ('SWs', [[-1.6, 12.4, 3.8], [-4.2, 12.7, 5.6], [-6.6, 13.0, 7.0], [-7.6, 13.2, 7.5]], [0.38, 0.3, 0.2, 0.12], 0.3),
    ('Na', [[0.0, 16.2, -1.5], [1.5, 17.6, -2.5], [2.6, 19.3, -3.3], [3.0, 20.4, -3.6]], [0.34, 0.27, 0.18, 0.1], 0.3),
    ('Nb', [[-0.1, 16.2, -1.6], [-1.3, 17.7, -2.9], [-1.9, 19.6, -3.8], [-2.1, 20.6, -4.1]], [0.32, 0.25, 0.16, 0.09], 0.3),
]
# G, the limb on the ground: (x, z, top of the limb, radius); 'g+d' tops are d above the ground
# there, the rest absolute (the ground falls toward the trunk, the limb rises steadily: ~23 deg)
G_SPEC = [(-1.4, 0.1, ('c', 4.1), 1.0), (-2.6, 0.15, ('c', 3.95), 0.98), (-4.2, 0.0, ('t', 4.45), 0.85),
          (-5.6, -0.3, ('t', 3.85), 0.75), (-7.4, -0.65, ('t', 3.05), 0.66), (-9.4, -1.1, ('t', 2.2), 0.6),
          (-11.2, -1.55, ('g', 0.62), 0.55), (-12.6, -1.9, ('g', 0.12), 0.5), (-13.6, -2.2, ('g', -0.12), 0.47),
          (-14.4, -2.45, ('g', -0.45), 0.42)]
CLIMB = ('G', 'P2', 'P3', 'P4', 'P5')     # the walkable limbs, in order up the path
LIMBS = list(LIMBS_SPEC)


def resolve_limbs(ground):
    """LIMBS with the ground limb fitted to the terrain."""
    pts, rr = [], []
    for x, z, (k, v), r in G_SPEC:
        if k == 'c':
            y = v
        elif k == 't':
            y = v - r
        else:
            y = float(ground(x, z)) + v - r
        pts.append([x, round(y, 3), z])
        rr.append(r)
    out = [l for l in LIMBS_SPEC]
    out.insert(3, ('G', pts, rr, 0.8))
    return out


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
        if name in defs and defs[name][2] >= Spine(pts, rr, step=0.1).length - 0.25:
            # the blended base has all of it (a limb another one grows from, up to its end)
            L = WD.Limb(name, pts, rr, kind='limb', moss=moss, n_around=10)
            L.tags['s0'] = 0.0
            L.tags['base_only'] = True
            named[name] = L
            continue
        if name in defs:
            s_cut = defs[name][2]
            s0 = max(s_cut - 0.8, 0.0)
            pts, rr = _trim_limb(name, pts, rr, s0)

        def rfun(th, k, frac, sp, s0=s0, sc=s_cut):
            return np.full(len(th), sp.rad[k] * (0.965 + 0.035 * float(smoothstep(sc, sc + 1.0, sp.s[k] + s0))))
        n_ar = 14 if rr[0] > 0.9 else (12 if name in CLIMB else 10)
        L = WD.Limb(name, pts, rr, kind='limb', moss=moss, n_around=n_ar,
                    step_fn=(lambda f: 0.5) if name in CLIMB else _limb_step(rr[0]), rfun=rfun)
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
    add((-11.4, 9.6, -1.2), (4.4, 2.4, 3.9), flat=0.3, sag=0.7, lump=0.2)        # W inner
    add((-15.2, 10.6, -1.6), (3.2, 2.1, 3.2), flat=0.3, sag=0.8, lump=0.2)       # W outer
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
    # (round 4b: lobes round an opening at the top where the standing fork and the crows' nest are)
    add((-3.0, 18.4, -3.8), (4.8, 2.9, 4.0), flat=0.3, clumps=0.5, lump=0.14)
    add((2.0, 18.9, -5.4), (4.4, 2.7, 3.4), flat=0.3, clumps=0.5, lump=0.14)
    add((8.2, 18.0, -1.4), (3.4, 2.4, 3.6), flat=0.3, lump=0.16)
    add((6.8, 16.6, 2.8), (3.6, 2.2, 3.2), flat=0.3, lump=0.18)
    add((0.4, 21.0, -4.2), (2.8, 1.6, 2.4), flat=0.3, clumps=0.3)
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


def noki_tile(W, seed):
    """ノキシノブ (Lepisorus thunbergianus), the little fern that lives on old bark: narrow strap
    leaves fanning out of one point and arching over and down (cards on the limbs' flanks)."""
    R = rng(seed)
    H = W
    c = LV.Canvas(W, H)
    bx, by = W / 2 + R.uniform(-0.8, 0.8), H * 0.42
    n = int(R.integers(5, 8))
    for k in range(n):
        a = -math.pi / 2 + (k - (n - 1) / 2) * 0.48 + R.normal(0, 0.1)
        L = R.uniform(W * 0.4, W * 0.58)
        steps = int(L * 1.6) + 2
        x, y = bx, by
        for j in range(steps):
            t = j / steps
            x += math.cos(a) * L / steps
            y += math.sin(a) * L / steps + t * 0.6
            c.put(x, y, LV.TOP if (t < 0.5 and math.sin(a) < -0.3) else LV.BODY, k * 0.01)
    c.sep(R, 0.3)
    return c.finish()


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
        'noki': [(noki_tile, dict(W=10, seed=S + 650 + i)) for i in range(3)],
        'bigfern': [(LV.fern_clump, dict(W=16, H=12, seed=S + 670 + i)) for i in range(3)],
    }
    for d in range(8):
        specs[f'spray{d}'] = [(LV.spray, dict(W=18, seed=S + 400 + d * 10, direction=-d * math.pi / 4, n_twigs=3,
                                               gloss=0.15, reach=0.46))]
    atlas, rects, sets = FO.build_tiles(specs)
    # calmer leaf tiles (round 4b): the clumps carry the light and shade, the tiles' own detail stays
    # quiet (the crown top read as noise by day)
    atlas = LV.calm(atlas, 0.78, 0.95)
    return atlas, rects, sets


def _tint(hexcol, body=LV.BODY):
    """The card tint that makes the tile's BODY tone come out as hexcol."""
    c = np.array(hex_rgb(hexcol), np.float64) / 255.0
    return np.clip(c / body, 0, 1)


def crown(M, sets):
    # round 4b (lead 12:55: the crown top read as noise): the clumps carry the light (their own
    # normals: top lit, underside dark), fewer fill cards between them so gaps show the shade inside;
    # at 30 px per metre the cards are smaller in the world, so there are more of them
    return CD.crown_cards(M, (0.0, 12.5, 0.5), (17.0, 7.0, 15.5), sets, seed=SEED + 9,
                          base_tint=_tint('#566e3e'), young_tint=_tint('#6e7c45'), old_tint=_tint('#34504a'),
                          base_y=7.0, top_y=21.0, overlap=1.05, clump_overlap=1.2, fill_density=0.42,
                          interior_frac=0.42, env_k=0.25, clump_k=0.5, up_bias=0.32, max_cards=7900)


def clear_path(cards, sp, climb):
    """No leaves on the walk: a tunnel 1.3 m round the line a metre above the path, and a window
    round the nest open to the camera (so the nest reads from below and the view opens from it)."""
    from ..wood import view_back_upright
    line = sp.pos + np.array([0.0, 0.9, 0.0])
    holes = [(np.array(climb['nest'], np.float64) + np.array([0.0, 0.9, 0.0]), 2.2, 1.5),
             (np.array(climb['crow_nest'], np.float64) + np.array([0.0, 0.3, 0.0]), 1.5, 1.1)]
    back = view_back_upright()
    keep = []
    for c in cards:
        if c.kind == 'epi':
            keep.append(c)
            continue
        d = np.min(np.linalg.norm(line - c.p, axis=1))
        if d < 1.3:
            continue
        cut = False
        for (h, r, rc) in holes:
            q = c.p - h
            if np.linalg.norm(q) < r:
                cut = True
                break
            t = float(np.clip(q @ back, 0.0, 9.0))
            if np.linalg.norm(q - back * t) < rc + 0.1 * t:
                cut = True
                break
        if not cut:
            keep.append(c)
    return keep


def path_plants(R, edges, sets):
    """Ferns and moss cushions along the edges of the path's moss (never on the walk itself)."""
    out = []
    for i, (q, nrm) in enumerate(edges):
        is_fern = R.uniform() < 0.55
        lst = sets['fern' if is_fern else 'moss']
        tl = lst[int(R.integers(0, len(lst)))]
        pos = q + nrm * 0.04 + np.array([0, tl[2] / PPM * (0.3 if is_fern else 0.1), 0])
        tint = _tint('#66813f') if is_fern else _tint('#5f7a36')
        out.append(CD.Card(pos, normalize(nrm * 0.4 + np.array([0.0, 1.0, 0.3])), tl[1], tl[2], tl[0], 0.95,
                           np.clip(tint * (1 + R.normal(0, 0.03)), 0, 1), 0.2 if is_fern else 0.0, 'epi', 2.0))
    return out


def limb_dress(R, named, limbs, sets):
    """Round 5 (G5R3-5: the limb over the iwakura "光秃秃的没什么叶子只有苔藓"; lead: "枝上要有小枝、叶、
    羊齿、ノキシノブ，中间留出走的苔路"): the ground limb and the lowest climbing limb are not bare tubes.
    Along their flanks (never on the moss walk on top): ノキシノブ in little fans, ferns, moss; and
    leaves on the epicormic twigs (胴吹き, the offshoots 'Gb*', 'P2b*'), along their outer half.
    Returns (flank cards, twig leaf cards); the leaf cards go through clear_path."""
    epi = []
    for key, every, f_hi in (('G', 0.36, 0.74), ('P2', 0.55, 0.9)):
        sp = named[key].spine
        n = int(sp.length / every)
        for i in range(n):
            f = (i + R.uniform(0.2, 0.8)) / max(n, 1)
            if f < 0.05 or f > f_hi:
                continue
            p, t, r = sp.point_at(f)
            side = normalize(np.cross(t, [0, 1, 0]) + 1e-6) * (1 if R.uniform() < 0.5 else -1)
            # on the flank: below the top's moss walk, facing out and a little up
            ang = R.uniform(0.2, 1.05)
            nrm = normalize(side * math.cos(ang) + np.array([0, math.sin(ang), 0]) * 0.6)
            pos = p + nrm * (r + 0.02)
            u = R.uniform()
            if u < 0.42:
                tl = sets['noki'][int(R.integers(0, len(sets['noki'])))]
                tint, flex = _tint('#3f5f3a'), 0.25
            elif u < 0.74:
                lst = sets['bigfern'] if R.uniform() < 0.6 else sets['fern']
                tl = lst[int(R.integers(0, len(lst)))]
                tint, flex = _tint('#5d7a3c'), 0.3
                pos = pos + np.array([0, tl[2] / PPM * 0.3, 0])
            else:
                tl = sets['moss'][int(R.integers(0, len(sets['moss'])))]
                tint, flex = _tint('#56703a'), 0.0
            epi.append(CD.Card(pos, normalize(nrm + np.array([0.0, 0.3, 0.35])), tl[1], tl[2], tl[0], 0.85,
                               np.clip(tint * (1 + R.normal(0, 0.03)), 0, 1), flex, 'epi', 2.0))
    leaves = []
    base_t, young_t = _tint('#566e3e'), _tint('#6e7c45')
    for L in limbs:
        if not L.name.startswith(('Gb', 'P2b')) or L.spine is None:
            continue
        sp = L.spine
        n = max(4, int(sp.length / 0.12))
        for i in range(n):
            f = 0.35 + 0.65 * (i + R.uniform(0.0, 1.0)) / n
            p, t, r = sp.point_at(min(f, 1.0))
            for _ in range(2 if f > 0.8 else 1):
                off = normalize(R.normal(0, 1, 3) + np.array([0, 0.5, 0]))
                q = p + off * R.uniform(0.08, 0.26)
                tl = sets['small'][int(R.integers(0, len(sets['small'])))]
                nrm = normalize(off * 0.6 + np.array([0.0, 0.55, 0.35]))
                tint = young_t if R.uniform() < 0.3 else base_t
                leaves.append(CD.Card(q, nrm, tl[1], tl[2], tl[0], float(R.uniform(0.7, 0.9)),
                                      np.clip(tint * (1 + R.normal(0, 0.035)), 0, 1), 0.6, 'clump', 0.95))
    return epi, leaves


def crevice_plants(R, base_md, sets):
    """Ferns and small epiphytes in the trunk's crevices and between the buttresses, on the side
    the camera sees (lead 12:55)."""
    from ..wood import view_back_upright
    a = base_md.arrays()
    P, N, A = a['p'], a['n'], a['col'][:, 3]
    back = view_back_upright()
    cand = np.nonzero((A < 0.5) & (P[:, 1] > 0.35) & (P[:, 1] < 6.2) & ((N @ back) > 0.15) & (N[:, 1] > -0.3))[0]
    R.shuffle(cand)
    chosen = []
    for i in cand:
        if all(np.linalg.norm(P[i] - P[j]) > 0.9 for j in chosen):
            chosen.append(i)
        if len(chosen) >= 14:
            break
    out = []
    for i in chosen:
        is_fern = R.uniform() < 0.6
        lst = sets['fern' if is_fern else 'moss']
        tl = lst[int(R.integers(0, len(lst)))]
        pos = P[i] + N[i] * 0.05 + np.array([0, tl[2] / PPM * 0.25, 0])
        tint = _tint('#5d7a3c') if is_fern else _tint('#566e34')
        out.append(CD.Card(pos, normalize(N[i] * 0.5 + np.array([0.0, 0.8, 0.3])), tl[1], tl[2], tl[0], 0.8,
                           np.clip(tint * (1 + R.normal(0, 0.03)), 0, 1), 0.2, 'epi', 2.0))
    return out


def epiphytes(R, named, sets):
    """Ferns and moss cushions on the tops of the big low limbs (cards, normal up)."""
    out = []
    for key, n_f, n_m in (('E', 9, 10), ('W', 9, 10), ('NE', 4, 5), ('N', 3, 4)):
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


# ------------------------------------------------------------------------------- the branch path
# The walk line on top of the path limbs (the top of each limb; the moss carpet and the exported
# line come from casting onto the real surfaces): (x, top y, z, limb radius there)
PATH_TOPS = [(-13.5, None, -2.18, 0.47), (-12.6, None, -1.9, 0.5), (-11.2, None, -1.55, 0.55), (-9.4, 2.2, -1.1, 0.6),
             (-7.4, 3.05, -0.65, 0.66), (-5.6, 3.85, -0.3, 0.75), (-4.2, 4.45, 0.0, 0.85), (-2.9, 5.0, 0.2, 0.95),
             (-1.6, 5.6, 0.45, 1.0), (-0.3, 6.0, 0.75, 1.0), (1.1, 6.5, 1.3, 1.0), (2.6, 7.3, 1.9, 0.9), (4.0, 8.0, 2.35, 0.82),
             (5.4, 8.7, 2.85, 0.76), (6.35, 9.15, 3.15, 0.72), (6.45, 9.45, 3.5, 0.7), (5.6, 9.95, 3.75, 0.68),
             (4.4, 10.55, 4.1, 0.66), (3.0, 11.15, 4.3, 0.64), (1.6, 11.7, 4.4, 0.62), (0.2, 12.3, 4.2, 0.6), (-1.2, 12.9, 3.9, 0.58),
             (-2.4, 13.4, 3.4, 0.56), (-3.5, 13.9, 2.8, 0.55), (-4.4, 14.35, 1.9, 0.52), (-5.1, 14.85, 0.8, 0.5),
             (-5.4, 15.4, -0.5, 0.48), (-4.9, 15.8, -1.5, 0.47), (-4.0, 16.15, -2.1, 0.46), (-2.9, 16.45, -2.1, 0.45),
             (-1.8, 16.7, -1.85, 0.45), (-0.9, 16.85, -1.55, 0.45), (0.0, 17.2, -0.95, 0.45), (0.9, 17.64, -0.3, 0.44),
             (1.7, 18.05, 0.15, 0.44), (2.4, 18.43, 0.5, 0.43), (3.1, 18.73, 0.25, 0.42), (3.8, 19.02, -0.1, 0.42),
             (4.3, 19.25, -0.6, 0.42), (4.6, 19.4, -1.0, 0.45)]
# crows up the path (arc length along the walk line, m), each a branch or two above the last; the
# last stands on the fork above the nest
PERCH_S = [7.5, 15.5, 22.5, 31.0, 39.5]       # then the nest (lead 14:00: 4-6 stops, the last the nest)
NEST_OFF = np.array([0.5, 0.42, -0.75])       # the crows' nest from the end of the walk (the standing fork)


def _path_line(ground):
    pts, rad = [], []
    for x, y, z, r in PATH_TOPS:
        if y is None:
            y = float(ground(x, z)) + {0: -0.05, 1: 0.12, 2: 0.62}[len(pts)]
        pts.append([x, y, z])
        rad.append(r)
    return Spine(pts, rad, step=0.15)


def _union_sdf(base, named):
    """Distance to the wood: the blended base (grid) and the swept limbs of the path and the nest."""
    from .. import sdf as SD
    grid, F = base['grid'], base['F']
    lo = grid.lo + grid.h
    hi = grid.lo + (grid.n - 2) * grid.h
    tubes = []
    for k in ('G', 'P2', 'P3', 'P4', 'P5', 'L', 'Na', 'Nb', 'Ne', 'Nf', 'Ng', 'Sx', 'SWs', 'W', 'E', 'SEu', 'SWu'):
        L = named.get(k)
        if L is None:
            continue
        tubes.append(SD.TubeSDF('u_' + k, L.pts, L.radii, step=0.12))

    def f(P):
        P = np.asarray(P, np.float64)
        d = np.full(len(P), 50.0)
        inside = np.all((P > lo) & (P < hi), axis=1)
        if inside.any():
            d[inside] = grid.sample(F, P[inside])
        for t in tubes:
            a, b = t.bbox()
            m = np.all((P > a - 0.5) & (P < b + 0.5), axis=1)
            if m.any():
                d[m] = np.minimum(d[m], t.dist(P[m]))
        return d
    return f


def _march(f, O, D, t_max, iters=90):
    t = np.zeros(len(O))
    hit = np.zeros(len(O), bool)
    for _ in range(iters):
        d = f(O + D * t[:, None])
        hit |= d < 0.004
        t = np.where(hit, t, t + np.maximum(d * 0.85, 0.006))
        if np.all(hit | (t > t_max)):
            break
    return O + D * t[:, None], hit & (t <= t_max)


def _grad(f, P, e=0.03):
    g = np.zeros_like(P)
    for i in range(3):
        d = np.zeros(3)
        d[i] = e
        g[:, i] = f(P + d) - f(P - d)
    return normalize(g)


def branch_path(base, named, ground, R):
    """The walkable line on the path limbs and the moss carpet over it. Returns (moss MeshData,
    climb dict, perches, edge points for ferns)."""
    from ..core import fbm3
    f = _union_sdf(base, named)
    sp = _path_line(ground)
    n = len(sp.s)
    T = sp.tan
    up = np.array([0.0, 1.0, 0.0])
    U = normalize(up[None, :] - (T @ up)[:, None] * T)
    S = normalize(np.cross(T, U))
    # the centre line: down onto the wood from above
    O = sp.pos + U * 1.3
    H0, ok0 = _march(f, O, -U, 3.0)
    H0 = np.where(ok0[:, None], H0, sp.pos)
    r_loc = np.clip(sp.rad, 0.42, 1.05)
    C = H0 - U * r_loc[:, None]
    # how far round the limb the moss reaches: about 55 degrees each side, wavy, with tongues down
    # the sides here and there
    w1 = fbm3(sp.s / 2.3, np.zeros(n), np.zeros(n) + 3.1, 2, SEED + 61) - 0.5
    w2 = fbm3(sp.s / 0.45, np.zeros(n) + 1.7, np.zeros(n), 1, SEED + 62) - 0.5
    phi_l = 0.95 * (1 + 0.45 * w1 + 0.35 * w2)
    phi_r = 0.95 * (1 - 0.4 * w1 + 0.35 * (fbm3(sp.s / 0.45, np.zeros(n) + 5.3, np.zeros(n), 1, SEED + 63) - 0.5))
    for _ in range(9):
        c = int(R.integers(0, n))
        L_ = int(R.integers(3, 7))
        side = R.choice([-1, 1])
        sl_ = slice(max(0, c - L_), min(n, c + L_))
        if side < 0:
            phi_l[sl_] += 0.5 * np.hanning(sl_.stop - sl_.start)
        else:
            phi_r[sl_] += 0.5 * np.hanning(sl_.stop - sl_.start)
    K = 6                                      # rings across: 2K + 1
    Pm = np.zeros((n, 2 * K + 1, 3))
    Nm = np.zeros((n, 2 * K + 1, 3))
    for j in range(-K, K + 1):
        ph = np.where(j < 0, -phi_l * (-j) / K, phi_r * j / K)
        Dd = U * np.cos(ph)[:, None] + S * np.sin(ph)[:, None]
        Oj = C + Dd * (r_loc[:, None] + 0.9)
        Hj, okj = _march(f, Oj, -Dd, r_loc.max() + 1.6)
        # a ray that misses (past the side of a limb) keeps the ring on the circle
        Hj = np.where(okj[:, None], Hj, C + Dd * r_loc[:, None])
        Pm[:, j + K] = Hj
    Nm = _grad(f, Pm.reshape(-1, 3)).reshape(Pm.shape)
    Pm = Pm + Nm * 0.035
    # mesh: quads between neighbouring samples; skip the folded ones at the switchback
    idx = []
    W_ = 2 * K + 1
    for i in range(n - 1):
        for j in range(W_ - 1):
            a, b, c, d = i * W_ + j, i * W_ + j + 1, (i + 1) * W_ + j, (i + 1) * W_ + j + 1
            idx.append((a, c, b))
            idx.append((b, c, d))
    idx = np.array(idx)
    P = Pm.reshape(-1, 3)
    N = Nm.reshape(-1, 3)
    # orient: MeshData is counter-clockwise outward (the asset exporter flips to Godot's order once)
    tri_n = np.cross(P[idx[:, 1]] - P[idx[:, 0]], P[idx[:, 2]] - P[idx[:, 0]])
    flip = np.einsum('ij,ij->i', tri_n, N[idx[:, 0]] + N[idx[:, 1]] + N[idx[:, 2]]) < 0
    idx[flip] = idx[flip][:, [0, 2, 1]]
    # uv: across in metres of arc, along in metres; the moss texture is 64 texels
    across = np.zeros((n, W_))
    for j in range(1, W_):
        across[:, j] = across[:, j - 1] + np.linalg.norm(Pm[:, j] - Pm[:, j - 1], axis=1)
    across -= across[:, K:K + 1]
    UVm = np.stack([across, np.repeat(sp.s[:, None], W_, axis=1)], -1).reshape(-1, 2) * TEXEL_PER_M / 64.0
    # colour: a little variation along, thinner and darker at the edges; AO from the crown
    edge = np.abs(np.arange(W_) - K) / K
    tone = 1.0 + 0.06 * (fbm3(sp.s / 1.7, np.zeros(n), np.zeros(n) + 9.0, 2, SEED + 64) - 0.5)
    col = (tone[:, None] * (1.0 - 0.1 * edge[None, :] ** 2))[..., None] * np.ones(3)
    col = col.reshape(-1, 3)
    vis = CD.sky_visibility(P, N, base['masses'], n_rays=12) if 'masses' in base else np.ones(len(P))
    ao = np.clip((0.55 + 0.45 * vis) * (1.0 - 0.15 * np.repeat(edge[None, :], n, axis=0).reshape(-1)), 0.3, 1.0)
    moss = MeshData()
    moss.add(P, N, UVm, idx, uv2=np.tile([0.0, 0.0], (len(P), 1)), col=np.concatenate([col, ao[:, None]], 1))
    # the walk line and its width (what she can walk on: a little inside the moss)
    every = max(1, int(round(0.5 / 0.15)))
    width = (r_loc * (np.sin(np.minimum(phi_l, 1.3)) + np.sin(np.minimum(phi_r, 1.3))) * 0.85)
    climb = {'points': [[round(float(v), 3) for v in q] for q in H0[::every]],
             'width': [round(float(v), 2) for v in width[::every]],
             'nest': [round(float(v), 3) for v in H0[-1]],
             'note': ('Walk line on the great camphor (round 4b): from the foot of the ground limb G (north of the shrine, '
                      'level with the ground) up G to the bowl on top of the trunk, east up P2, back west along P3 across the '
                      'front of the trunk, round on P4 to the nest in the leader\'s fork. Points every 0.5 m on the top of the '
                      'moss (object space of the tree; terrain.json climb.camphor has them in world space), width = what is '
                      'walkable there. Slopes under 27 degrees: walk it like a slope, no climbing move.')}
    perches = []
    for s_ in PERCH_S:
        i = int(np.clip(np.searchsorted(sp.s, s_), 0, n - 1))
        q = H0[i] + U[i] * 0.04 + S[i] * (0.18 if (len(perches) % 2) else -0.18)
        perches.append([round(float(v), 3) for v in q])
    nest_c = H0[-1] + NEST_OFF
    perches.append([round(float(v), 3) for v in nest_c + np.array([0.0, 0.16, 0.0])])
    climb['crow_nest'] = [round(float(v), 3) for v in nest_c]
    edges = []
    for i in range(0, n, 2):
        for jj in (0, W_ - 1):
            if R.uniform() < 0.45:
                edges.append((Pm[i, jj], Nm[i, jj]))
    return moss, climb, perches, edges, sp


def crow_nest(R, c):
    """The crows' nest beside the standing fork (lead 14:00): a cup of dead twigs about 0.7 m across,
    lined with straw rope ends; in it a sandal strap, a soda bottle cap, a button. Returns (twigs for
    the bark material, straw for the rope material, small things for the paper material)."""
    twigs, straw, bits = MeshData(), MeshData(), MeshData()
    c = np.asarray(c, np.float64)
    for k in range(110):
        a = R.uniform(0, 2 * math.pi)
        r = R.uniform(0.22, 0.46)
        y = R.uniform(-0.18, 0.14)
        mid = c + np.array([math.cos(a) * r, y, math.sin(a) * r])
        tang = normalize(np.array([-math.sin(a), R.normal(0, 0.35), math.cos(a)]) + R.normal(0, 0.3, 3))
        Ln = R.uniform(0.3, 0.75) if k % 9 else R.uniform(0.8, 1.1)       # a few long ones stick out
        p0, p1 = mid - tang * Ln / 2, mid + tang * Ln / 2
        sp = Spine([p0, p1], [0.016, 0.01], step=0.3)
        md, _ = tube(sp, n_around=3, cap_end=False)
        a_ = md.arrays()
        n = len(a_['p'])
        shade = R.uniform(0.55, 0.85)
        twigs.add(a_['p'], a_['n'], a_['uv'] * 0.2 + R.uniform(0, 1, 2), a_['idx'], uv2=np.tile([0.0, 0.0], (n, 1)),
                  col=np.tile([shade, shade * 0.95, shade * 0.88, 0.7], (n, 1)))
    for k in range(12):                       # straw rope ends lining the cup
        a = R.uniform(0, 2 * math.pi)
        mid = c + np.array([math.cos(a) * 0.16, 0.1, math.sin(a) * 0.16])
        tang = normalize(np.array([-math.sin(a), 0.1, math.cos(a)]))
        sp = Spine([mid - tang * 0.12, mid + tang * 0.12], [0.02, 0.018], step=0.2)
        md, info = tube(sp, n_around=4, cap_end=True)
        a_ = md.arrays()
        straw.add(a_['p'], a_['n'], _tube_uv(info, len(a_['p'])), a_['idx'], uv2=np.zeros((len(a_['p']), 2)),
                  col=np.ones((len(a_['p']), 4)))

    def disc(centre, r, colour, tilt):
        ang = np.linspace(0, 2 * math.pi, 9)[:-1]
        nrm = normalize(np.array([math.sin(tilt), 1.0, 0.2]))
        side = normalize(np.cross(nrm, [0, 0, 1.0]))
        fwd = np.cross(side, nrm)
        P = [centre] + [centre + (side * math.cos(t) + fwd * math.sin(t)) * r for t in ang]
        idx = [(0, 1 + (i + 1) % 8, 1 + i) for i in range(8)]
        idx += [(0, 1 + i, 1 + (i + 1) % 8) for i in range(8)]
        n = len(P)
        bits.add(np.array(P), np.tile(nrm, (n, 1)), np.zeros((n, 2)), np.array(idx), uv2=np.tile([0.0, 0.0], (n, 1)),
                 col=np.tile(np.concatenate([colour, [1.0]]), (n, 1)))
    disc(c + np.array([0.05, 0.13, 0.04]), 0.035, np.array([0.80, 0.82, 0.84]), 0.3)     # the bottle cap (tin)
    disc(c + np.array([-0.08, 0.12, -0.02]), 0.03, np.array([0.93, 0.91, 0.86]), -0.2)   # a white button
    # the sandal strap: a red-brown cloth band hanging over the rim
    sp = Spine([c + np.array([0.12, 0.12, 0.14]), c + np.array([0.24, 0.06, 0.26]), c + np.array([0.28, -0.12, 0.3])],
               [0.022, 0.022, 0.02], step=0.06)
    md, _ = tube(sp, n_around=4, cap_end=True)
    a_ = md.arrays()
    n = len(a_['p'])
    bits.add(a_['p'], a_['n'], np.zeros((n, 2)), a_['idx'], uv2=np.tile([0.0, 0.0], (n, 1)),
             col=np.tile([0.55, 0.22, 0.16, 1.0], (n, 1)))
    return twigs, straw, bits


def moss_texture(seed=SEED + 70):
    """Bright moss for the path's carpet, 64 x 64, tiles: cushions with a lit top and a dark
    underside, darker gaps between, a few rust sporophyte dots."""
    from skimage import color
    R = rng(seed)
    S_ = 64
    pal = {k: np.clip(color.lab2rgb(np.array([[v]], np.float64))[0, 0], 0, 1) for k, v in {
        'deep': (32.0, -10.0, 16.0), 'shade': (40.0, -14.0, 24.0), 'mid': (49.0, -17.0, 30.0), 'lit': (56.0, -16.0, 34.0),
        'top': (62.0, -13.0, 36.0), 'rust': (40.0, 14.0, 26.0)}.items()}
    img = np.zeros((S_, S_, 3))
    img[:] = pal['shade']
    ys, xs = np.mgrid[0:S_, 0:S_]
    for _ in range(70):
        cx, cy = R.uniform(0, S_, 2)
        r = R.uniform(2.2, 5.0)
        dx = (xs - cx + S_ / 2) % S_ - S_ / 2
        dy = (ys - cy + S_ / 2) % S_ - S_ / 2
        d = np.hypot(dx, dy * 1.15) / r
        m = d < 1.0
        lit = (dx + dy * 1.2) / r
        img[m & (lit < -0.35)] = pal['top']
        img[m & (lit >= -0.35) & (lit < 0.25)] = pal['lit']
        img[m & (lit >= 0.25)] = pal['mid']
        img[(d >= 1.0) & (d < 1.18)] = np.where((d[(d >= 1.0) & (d < 1.18)] > 0)[:, None], pal['deep'], pal['deep'])
    for _ in range(18):
        x, y = R.integers(0, S_, 2)
        img[y, x] = pal['rust']
        img[(y - 1) % S_, x] = pal['mid']
    return np.round(img * 255).astype(np.uint8)


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
    global LIMBS
    LIMBS = resolve_limbs(ground)
    M = masses()
    base_md, base = base_mesh(R, M, ground)
    base['masses'] = M
    limbs, named = skeleton(base['defs'])
    # side branches; the path limbs only send thin ones sideways and down (nothing across the walk)
    for key, n, fr, ln, ub in (('E', 3, (0.55, 0.95), (2.4, 4.0), 0.45), ('W', 3, (0.55, 0.95), (2.4, 4.0), 0.45),
                               ('P2', 1, (0.72, 0.92), (1.8, 2.6), -0.1),
                               ('NE', 2, (0.5, 0.9), (2.4, 3.6), 0.45), ('N', 2, (0.5, 0.9), (2.4, 3.6), 0.45),
                               ('L', 2, (0.3, 0.6), (2.4, 4.0), 0.45), ('SEu', 2, (0.5, 0.9), (2.0, 3.0), 0.45),
                               ('SWu', 2, (0.5, 0.9), (2.0, 3.0), 0.45), ('P3', 2, (0.2, 0.75), (1.4, 2.2), -0.25),
                               ('G', 8, (0.12, 0.72), (0.55, 1.25), 0.35)):
        L = named[key]
        WD.build_limb(L)
        _shift_v(L, L.tags['s0'])
        rk, mr, twig = ((0.3, 0.45) if key in CLIMB else (0.4, 0.6)), 0.05, False
        if key == 'G':     # round 5: epicormic twigs (胴吹き) out of the ground limb's flanks, thin, leafy at the ends
            rk, mr, twig = (0.06, 0.1), 0.022, True
        for b in WD.offshoots(L, R, n, frac_range=fr, length=ln, radius_k=rk, up_bias=ub, name=key + 'b', min_r=mr,
                              moss=0.15, segs=3, spread=1.15 if twig else (1.1 if key in CLIMB else 0.9)):
            b.n_around = 5 if twig else 7
            b.step = 0.3 if twig else 0.7
            limbs.append(b)
    for L in limbs:
        if L.spine is None:
            WD.build_limb(L)
            if 's0' in L.tags:
                _shift_v(L, L.tags['s0'])
    a = out.asset(NAME, 'trees')
    # round 5: round 3's line work (its ukiyo-e grain), the ridges' tones continuous (no plates, no breaks)
    bark_img = WD.bark_lines_texture(SEED, size=256, ridge=('#6c6458', '#7b7365', '#8a8272'), lip='#999080')
    bark_res = a.texture('bark', bark_img)
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                        textures={'albedo_tex': bark_res})

    def ao_fn(P, N, L):
        # baked AO: undersides and the inner limbs, times how much sky the bark sees past the crown
        return wood_ao(P, N, L) * (0.45 + 0.55 * CD.sky_visibility(P, N, M, n_rays=16))
    wood = WD.wood_mesh(limbs, tex_size=256, colour_fn=wood_colour, ao_fn=ao_fn, moss_fn=wood_moss, u_scale=LIMB_U)
    wood.merge(base_md)
    moss_md, climb, perches, moss_edges, path_sp = branch_path(base, named, ground, R)
    rope, shide = shimenawa(base)
    n_twigs, n_straw, n_bits = crow_nest(R, climb['crow_nest'])
    wood.merge(n_twigs)
    rope.merge(n_straw)
    shide.merge(n_bits)
    rope_res = a.texture('rope', rope_texture())
    m_rope = a.material('rope', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': rope_res})
    m_paper = a.material('shide', 'toon_solid.gdshader', params={'porosity': 0.6})
    atlas, rects, sets = leaf_tiles()
    cards = crown(M, sets)
    cards = clear_path(cards, path_sp, climb)
    vis = CD.sky_visibility(np.array([c.p for c in cards]), np.array([c.n for c in cards]), M, n_rays=16)
    for c, v in zip(cards, vis):
        c.ao = float(np.clip(c.ao * (0.62 + 0.38 * v), 0.2, 1.0))
    cards += epiphytes(R, named, sets)
    cards += path_plants(R, moss_edges, sets)
    dress, twig_leaves = limb_dress(R, named, limbs, sets)
    cards += dress
    cards += clear_path(twig_leaves, path_sp, climb)
    cards += crevice_plants(R, base_md, sets)
    if os.environ.get('W3A_DEBUG_KINDS'):
        dbg = {'clump': (0.3, 0.9, 0.3), 'fill': (0.3, 0.4, 1.0), 'interior': (1.0, 0.2, 0.2), 'spray': (1.0, 1.0, 0.2), 'epi': (1.0, 0.2, 1.0)}
        for c in cards:
            c.tint = np.array(dbg.get(c.kind, (1, 1, 1)))
            c.ao = 1.0
    leaf_md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': leaf_res})
    moss_res = a.texture('moss', moss_texture())
    m_moss = a.material('moss', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                        textures={'albedo_tex': moss_res})
    wood_mesh = a.mesh('wood', [(m_bark, wood), (m_moss, moss_md), (m_rope, rope), (m_paper, shide)])
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
    bark_far = a.texture('bark_far', pale_colour(bark_img / 255.0) * 255.0)
    m_bark_far = a.material('bark_far', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                            textures={'albedo_tex': bark_far})
    # the far bark texture applies above the rope only: split the wood by height
    lo_idx = wa['idx'][np.max(wa['p'][wa['idx']][:, :, 1], axis=1) < ROPE_Y + 0.4]
    hi_idx = wa['idx'][np.max(wa['p'][wa['idx']][:, :, 1], axis=1) >= ROPE_Y + 0.4]
    w_lo, w_hi = MeshData(), MeshData()
    w_lo.add(wa['p'], wa['n'], wa['uv'], lo_idx, uv2=wa['uv2'], col=col_far)
    w_hi.add(wa['p'], wa['n'], wa['uv'], hi_idx, uv2=wa['uv2'], col=col_far)
    ma = moss_md.arrays()
    moss_far = MeshData()
    moss_far.add(ma['p'], ma['n'], ma['uv'], ma['idx'], uv2=ma['uv2'],
                 col=np.concatenate([pale_colour(ma['col'][:, :3] * 0.85) / 0.85, ma['col'][:, 3:]], 1))
    wood_far_mesh = a.mesh('wood_far', [(m_bark, w_lo), (m_bark_far, w_hi), (m_moss, moss_far), (m_rope, rope), (m_paper, shide)])
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
        'anchors': {'shimenawa_front': [0.0, ROPE_Y - 0.2, round(surface_rho(base, ROPE_Y, math.pi) + 0.3, 2)],
                    'perch_crow': perches, 'nest': climb['nest']},
        'climb': climb,
        'notes': ('御神木. Trunk 6.5 m across; buttress roots fitted to the ground of the ' + gnote +
                  ' (do not rotate; rebuild after the terrain changes); low limbs reach 16.5 m. Shimenawa at %.2f m.' % ROPE_Y),
    }
    nt = len(wood.arrays()['idx']) + len(rope.arrays()['idx']) + len(shide.arrays()['idx'])
    nt += len(moss_md.arrays()['idx'])
    return {'cards': len(cards), 'wood_tris': nt, 'moss_tris': len(moss_md.arrays()['idx']), 'leaf_tris': len(cards) * 2,
            'atlas': list(atlas.shape[:2]), 'climb_points': len(climb['points']), **base['stats']}
