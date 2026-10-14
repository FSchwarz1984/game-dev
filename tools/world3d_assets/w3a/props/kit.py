"""Prop kit: the pieces small buildings and objects are made of, for the renderer's toon_solid
(albedo_mode 0: vertex colour; UV2 = surface pattern id and amount; docs/knowledge/21 section 2.1).

  convex(points)        any convex piece (hull), flat shaded: chamfered boxes, prisms, wedges
  cbox / cprism         chamfered box and prism (the 1 px edge chamfer catches the light)
  lathe(profile)        surfaces of revolution: tubs, lanterns, dishes, finials
  rod(points, r)        smooth tubes: ropes, poles, branches, cords (w3a.tube)
  sdf_piece(f, lo, hi)  organic pieces from a distance field: weathered stones, statues, thatch,
                        straw (w3a.sdf: surface nets, projection, decimation)

A Piece carries its colour, pattern and amount; Prop.finish() bakes ambient occlusion against the
whole prop and the ground (rays through a voxel shell), adds dirt near the ground, and returns
one MeshData per material. pale() is the faded (遠化) look: the same colours drained and lifted.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import ConvexHull

from ..core import fbm3, hex_rgb, normalize, rng
from ..mesh import MeshData

PAT = {'plain': 0, 'planks': 1, 'bark': 2, 'thatch': 3, 'stone': 4, 'tiles': 5, 'paper': 6, 'moss': 7}


def col(h):
    """'#rrggbb' -> sRGB floats."""
    return np.array(hex_rgb(h), np.float64) / 255.0


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def frame_to(d):
    """Rotation taking +y to direction d."""
    d = normalize(np.asarray(d, np.float64))
    up = np.array([0.0, 1.0, 0.0])
    v = np.cross(up, d)
    s = np.linalg.norm(v)
    c = float(up @ d)
    if s < 1e-9:
        return np.eye(3) if c > 0 else rot_x(math.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))


class Piece:
    """One part of a prop: geometry (p, n, idx; counter-clockwise outward) and its look."""

    def __init__(self, p, n, idx, colour, pattern='plain', amount=0.3, mat='solid', var=0.05, seed=0,
                 ao=True, dirt=True, emissive=False, shade=None):
        self.p = np.asarray(p, np.float64)
        self.n = np.asarray(n, np.float64)
        self.idx = np.asarray(idx, np.int64)
        self.colour = np.asarray(colour, np.float64)
        self.pattern = PAT.get(pattern, pattern)
        self.amount = amount
        self.mat = mat
        self.var = var
        self.seed = seed
        self.ao = ao
        self.dirt = dirt
        self.emissive = emissive
        self.shade = shade              # optional fn(P, N) -> per-vertex colour multiplier (n, 3)

    def moved(self, R=None, t=(0, 0, 0)):
        R = np.eye(3) if R is None else np.asarray(R, np.float64)
        q = Piece(self.p @ R.T + np.asarray(t, np.float64), self.n @ R.T, self.idx, self.colour, self.pattern,
                  self.amount, self.mat, self.var, self.seed, self.ao, self.dirt, self.emissive, self.shade)
        return q

    @property
    def tris(self):
        return len(self.idx)


def _flat(P, tris, centre):
    """Flat-shaded mesh from triangles, oriented outward from centre."""
    p, n, idx = [], [], []
    for t in tris:
        a, b, c = P[t[0]], P[t[1]], P[t[2]]
        fn = np.cross(b - a, c - a)
        L = np.linalg.norm(fn)
        if L < 1e-12:
            continue
        fn /= L
        if fn @ ((a + b + c) / 3 - centre) < 0:
            b, c = c, b
            fn = -fn
        k = len(p)
        p += [a, b, c]
        n += [fn, fn, fn]
        idx.append((k, k + 1, k + 2))
    return np.array(p), np.array(n), np.array(idx)


def convex(points, colour, **kw):
    P = np.asarray(points, np.float64)
    h = ConvexHull(P)
    p, n, idx = _flat(P, h.simplices, P.mean(axis=0))
    return Piece(p, n, idx, colour, **kw)


def cbox(size, colour, centre=(0, 0, 0), bevel=0.02, R=None, jitter=0.0, seed=0, **kw):
    """Chamfered box (size = full extents), rotated by R about its centre, then moved to centre.
    jitter: corner points pushed a little at random (hand-cut wood, worn stone)."""
    a, b, c = np.asarray(size, np.float64) * 0.5
    e = min(bevel, a * 0.45, b * 0.45, c * 0.45)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                if e <= 1e-6:
                    pts.append((sx * a, sy * b, sz * c))
                else:
                    pts += [(sx * a, sy * (b - e), sz * (c - e)), (sx * (a - e), sy * b, sz * (c - e)),
                            (sx * (a - e), sy * (b - e), sz * c)]
    P = np.array(pts)
    if jitter:
        Rg = rng(seed)
        P = P + Rg.normal(0, jitter, P.shape)
    if R is not None:
        P = P @ np.asarray(R).T
    P = P + np.asarray(centre, np.float64)
    kw.setdefault('seed', seed)
    return convex(P, colour, **kw)


def cprism(n, r0, r1, h, colour, base=(0, 0, 0), bevel=0.015, rot=0.0, R=None, **kw):
    """Chamfered prism / frustum with n sides, from radius r0 at the bottom to r1 at the top."""
    pts = []
    rings = ((0.0, r0), (h, r1)) if bevel <= 1e-6 else ((0.0, r0 - bevel), (bevel, r0), (h - bevel, r1), (h, r1 - bevel))
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        for y, r in rings:
            pts.append((ca * max(r, 1e-4), y, sa * max(r, 1e-4)))
    P = np.array(pts)
    if R is not None:
        P = P @ np.asarray(R).T
    P = P + np.asarray(base, np.float64)
    return convex(P, colour, **kw)


def beam(p0, p1, w, h, colour, up=(0, 1, 0), bevel=0.015, **kw):
    """A squared timber from p0 to p1 (w across, h up)."""
    p0, p1 = np.asarray(p0, np.float64), np.asarray(p1, np.float64)
    d = p1 - p0
    L = np.linalg.norm(d)
    t = d / L
    u = normalize(np.asarray(up, np.float64) - (np.asarray(up) @ t) * t)
    s = np.cross(t, u)
    R = np.stack([s, u, t], axis=1)          # local x = side, y = up, z = along
    return cbox((w, h, L), colour, centre=(p0 + p1) / 2, bevel=bevel, R=R, **kw)


def lathe(profile, colour, n=12, base=(0, 0, 0), R=None, cap_top=True, cap_bottom=True, smooth=True, **kw):
    """Surface of revolution from a profile [(r, y), ...] (bottom to top)."""
    prof = np.asarray(profile, np.float64)
    m = len(prof)
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    P = np.zeros((m, n, 3))
    P[:, :, 0] = prof[:, :1] * np.cos(th)[None, :]
    P[:, :, 2] = prof[:, :1] * np.sin(th)[None, :]
    P[:, :, 1] = prof[:, 1:2]
    # normals from the profile tangent
    dp = np.gradient(prof, axis=0)
    nr = dp[:, 1]
    ny = -dp[:, 0]
    L = np.maximum(np.hypot(nr, ny), 1e-9)
    nr, ny = nr / L, ny / L
    N = np.zeros((m, n, 3))
    N[:, :, 0] = nr[:, None] * np.cos(th)[None, :]
    N[:, :, 2] = nr[:, None] * np.sin(th)[None, :]
    N[:, :, 1] = ny[:, None]
    p = P.reshape(-1, 3)
    nn = N.reshape(-1, 3)
    idx = []
    for k in range(m - 1):
        for j in range(n):
            a = k * n + j
            b = k * n + (j + 1) % n
            c = (k + 1) * n + (j + 1) % n
            d = (k + 1) * n + j
            idx += [(a, c, b), (a, d, c)]
    idx = np.array(idx)
    extra_p, extra_n, extra_i = [], [], []
    k0 = len(p)
    if cap_bottom and prof[0, 0] > 1e-4:
        cb = np.array([0, prof[0, 1], 0])
        extra_p.append(np.vstack([cb, P[0]]))
        extra_n.append(np.tile([0, -1, 0], (n + 1, 1)))
        extra_i += [(k0, k0 + 1 + (j + 1) % n, k0 + 1 + j) for j in range(n)]
        k0 += n + 1
    if cap_top and prof[-1, 0] > 1e-4:
        ct = np.array([0, prof[-1, 1], 0])
        extra_p.append(np.vstack([ct, P[-1]]))
        extra_n.append(np.tile([0, 1, 0], (n + 1, 1)))
        extra_i += [(k0, k0 + 1 + j, k0 + 1 + (j + 1) % n) for j in range(n)]
    if extra_p:
        p = np.vstack([p] + extra_p)
        nn = np.vstack([nn] + extra_n)
        idx = np.vstack([idx, np.array(extra_i)])
    # orient outward
    fa, fb, fc = p[idx[:, 0]], p[idx[:, 1]], p[idx[:, 2]]
    fn = np.cross(fb - fa, fc - fa)
    vn = nn[idx[:, 0]] + nn[idx[:, 1]] + nn[idx[:, 2]]
    flip = np.sum(fn * vn, axis=1) < 0
    idx[flip] = idx[flip][:, [0, 2, 1]]
    if R is not None:
        p = p @ np.asarray(R).T
        nn = nn @ np.asarray(R).T
    p = p + np.asarray(base, np.float64)
    return Piece(p, nn, idx, colour, **kw)


def rod(points, radius, colour, n=6, cap=True, step=0.08, radii=None, **kw):
    """A smooth tube along a Catmull-Rom curve (ropes, poles, sticks, cords)."""
    from ..tube import Spine, tube
    pts = np.asarray(points, np.float64)
    rr = radii if radii is not None else [radius] * len(pts)
    sp = Spine(pts, rr, step=step)
    md, _ = tube(sp, n_around=n, cap_end=cap, cap_start=cap)
    a = md.arrays()
    return Piece(a['p'], a['n'], a['idx'], colour, **kw)


def sdf_piece(f, lo, hi, colour, h=0.04, tris=600, smooth=2, **kw):
    """An organic piece: the zero set of f (vectorised, points (..., 3) -> distance), polygonised on
    a grid of step h inside [lo, hi], put back on the surface and decimated to about `tris`."""
    from .. import sdf as SD
    lo = np.asarray(lo, np.float64) - 2 * h
    hi = np.asarray(hi, np.float64) + 2 * h
    g = SD.Grid(lo, hi, h)
    _, X = g.box(g.lo, g.lo + (g.n - 1) * g.h)
    F = f(X)
    V, T = SD.surface_nets(F, g)
    V, T, _ = SD.compact(V, T)
    V = SD.project(V, F, g, iters=3)
    if smooth:
        keep = SD.boundary_vertices(T, len(V))
        V = SD.taubin(V, T, iters=smooth, keep=keep)
        V = SD.project(V, F, g, iters=2, keep=keep)
    if len(T) > tris:
        V, T, _ = SD.decimate(V, T, tris)
        V = SD.project(V, F, g, iters=2, keep=SD.boundary_vertices(T, len(V)))
    from scipy import ndimage
    N = normalize(g.gradient(ndimage.gaussian_filter(F, 0.7), V, eps=h))
    return Piece(V, N, T, colour, **kw)


# ------------------------------------------------------------------------------------ distance fields
def sd_box(P, half, r=0.0):
    q = np.abs(P) - (np.asarray(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.max(q, axis=-1), 0) - r


def sd_ellipsoid(P, r):
    r = np.asarray(r, np.float64)
    k0 = np.linalg.norm(P / r, axis=-1)
    k1 = np.linalg.norm(P / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_cyl(P, r, h):
    """Vertical cylinder centred at the origin, radius r, half-height h."""
    d = np.stack([np.hypot(P[..., 0], P[..., 2]) - r, np.abs(P[..., 1]) - h], axis=-1)
    return np.minimum(np.max(d, axis=-1), 0) + np.linalg.norm(np.maximum(d, 0), axis=-1)


def sd_capsule(P, a, b, r):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    pa = P - a
    ba = b - a
    t = np.clip(np.sum(pa * ba, axis=-1) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - t[..., None] * ba, axis=-1) - r


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def weathered(P, amp=0.02, scale=0.25, seed=0):
    """Lumps and chips for stone: fbm displacement (add to a distance)."""
    return (fbm3(P[..., 0] / scale, P[..., 1] / scale, P[..., 2] / scale, octaves=3, seed=seed) - 0.5) * 2 * amp


# ------------------------------------------------------------------------------------ finishing
class Prop:
    def __init__(self, name, seed=0):
        self.name = name
        self.pieces = []
        self.seed = seed

    def add(self, *pieces):
        for p in pieces:
            if isinstance(p, (list, tuple)):
                self.add(*p)
            elif p is not None:
                self.pieces.append(p)
        return self

    @property
    def tris(self):
        return sum(p.tris for p in self.pieces)

    def bounds(self):
        P = np.vstack([p.p for p in self.pieces])
        return P.min(axis=0), P.max(axis=0)

    def finish(self, ground=True, ao_strength=0.7, ao_reach=0.9, h=None, pale=False, ground_y=0.0):
        """Bake per-vertex colour (base x variation x shade x AO-free dirt) and AO (COLOR.a), pattern in
        UV2; returns {material key: MeshData}."""
        lo, hi = self.bounds()
        ext = float(np.max(hi - lo))
        h = h or float(np.clip(ext / 70.0, 0.025, 0.08))
        occ, glo = _voxel_shell(self.pieces, lo - ao_reach, hi + ao_reach, h)
        out = {}
        R = rng(self.seed + 17)
        for pc in self.pieces:
            P, N = pc.p, pc.n
            ao = np.ones(len(P))
            if pc.ao:
                ao = _ao(P, N, occ, glo, h, ao_reach, ground_y if ground else None, R)
                ao = 1.0 - ao_strength * (1.0 - ao)
            c = np.tile(pc.colour, (len(P), 1))
            if pc.var:
                nz = fbm3(P[:, 0] * 3.1, P[:, 1] * 3.1, P[:, 2] * 3.1, octaves=2, seed=pc.seed + 3) - 0.5
                c = c * (1 + pc.var * 2.0 * nz)[:, None]
            if pc.shade is not None:
                c = c * pc.shade(P, N)
            if pc.dirt and ground:
                g = np.clip((ground_y + 0.25 - P[:, 1]) / 0.3, 0, 1)[:, None]
                c = c * (1 - 0.25 * g) + np.array([0.36, 0.3, 0.24]) * 0.25 * g
            if pale:
                c = pale_colour(c)
            C = np.concatenate([np.clip(c, 0, 1), np.clip(ao, 0.15, 1)[:, None]], axis=1)
            uv2 = np.tile([float(pc.pattern), float(pc.amount)], (len(P), 1))
            md = out.setdefault(pc.mat, MeshData())
            md.add(P, N, np.zeros((len(P), 2)), pc.idx, uv2=uv2, col=C)
        return out


def pale_colour(c):
    """遠化: the colour drained toward its own grey and lifted toward a cool pale."""
    c = np.asarray(c, np.float64)
    l = (0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2])[..., None]
    d = c * 0.25 + l * 0.75
    return d * 0.55 + np.array([0.84, 0.85, 0.88]) * 0.45


def _voxel_shell(pieces, lo, hi, h):
    """Occupancy of the prop's surfaces on a grid (points sampled on every triangle)."""
    n = np.ceil((hi - lo) / h).astype(int) + 1
    occ = np.zeros(tuple(n), bool)
    for pc in pieces:
        P = pc.p
        T = pc.idx
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        L = np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - a, axis=1))
        k = np.clip(np.ceil(L / (h * 0.5)).astype(int), 1, 40)
        for kk in np.unique(k):
            sel = k == kk
            uu, vv = np.meshgrid(np.linspace(0, 1, kk + 1), np.linspace(0, 1, kk + 1))
            m = (uu + vv) <= 1.0
            uu, vv = uu[m], vv[m]
            S = a[sel, None, :] + (b[sel] - a[sel])[:, None, :] * uu[None, :, None] + (c[sel] - a[sel])[:, None, :] * vv[None, :, None]
            I = np.floor((S.reshape(-1, 3) - lo) / h).astype(int)
            ok = np.all((I >= 0) & (I < n), axis=1)
            I = I[ok]
            occ[I[:, 0], I[:, 1], I[:, 2]] = True
    return occ, lo


def _ao(P, N, occ, lo, h, reach, ground_y, R, n_rays=24):
    """Fraction of a cosine-weighted hemisphere that is open (1) or blocked (0) within reach."""
    u = R.uniform(size=n_rays)
    v = R.uniform(size=n_rays)
    r = np.sqrt(u)
    th = 2 * math.pi * v
    loc = np.stack([r * np.cos(th), np.sqrt(np.maximum(1 - u, 0)), r * np.sin(th)], axis=1)   # y up
    open_ = np.zeros(len(P))
    steps = np.arange(1.6 * h, reach, h * 0.9)
    n = np.array(occ.shape)
    for i in range(len(P)):
        nn = N[i]
        Rm = frame_to(nn)
        dirs = loc @ Rm.T
        Q = P[i][None, None, :] + nn[None, None, :] * h * 0.8 + dirs[:, None, :] * steps[None, :, None]
        I = np.floor((Q - lo) / h).astype(int)
        inside = np.all((I >= 0) & (I < n), axis=2)
        hit = np.zeros(Q.shape[:2], bool)
        Ic = np.clip(I, 0, n - 1)
        hit[inside] = occ[Ic[inside][:, 0], Ic[inside][:, 1], Ic[inside][:, 2]]
        if ground_y is not None:
            hit |= Q[..., 1] < ground_y - 0.01
        blocked = hit.any(axis=1)
        open_[i] = 1.0 - blocked.mean()
    return open_
