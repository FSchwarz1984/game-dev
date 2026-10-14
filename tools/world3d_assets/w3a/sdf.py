"""Signed-distance modelling for organic junctions (the base of the great camphor: trunk, buttress
roots, the crotch where the limbs leave), polygonised with surface nets, put back on the surface,
decimated with quadric error metrics.

Why: swept tubes stuck into each other meet along hard intersection curves, and a radial trunk
function cannot make roots that leave the trunk, arch and dive (it has no undersides). Here every
part is a distance field; parts are joined with a smooth minimum, so every crotch gets a fillet
whose size is set by one number (k), and noise displaces the joined surface.

Parts know their own coordinates (height and angle round the trunk; arc length and angle round
a root or limb), so after meshing each triangle takes the bark mapping of the part that owns it:
fissures run up the trunk, along each root and along each limb, and the seams fall in the crotches.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
from scipy import ndimage, sparse

from .core import normalize
from .tube import Spine, ring_frames


# ------------------------------------------------------------------------------------------- grid
class Grid:
    def __init__(self, lo, hi, h):
        self.lo = np.asarray(lo, np.float64)
        self.h = float(h)
        self.n = (np.ceil((np.asarray(hi, np.float64) - self.lo) / self.h).astype(int) + 1)

    def box(self, lo, hi):
        """Slices of the grid points inside [lo, hi] and their coordinates (..., 3)."""
        i0 = np.clip(np.floor((np.asarray(lo) - self.lo) / self.h).astype(int), 0, self.n)
        i1 = np.clip(np.ceil((np.asarray(hi) - self.lo) / self.h).astype(int) + 1, 0, self.n)
        sl = tuple(slice(int(a), int(b)) for a, b in zip(i0, i1))
        axes = [self.lo[k] + np.arange(i0[k], i1[k]) * self.h for k in range(3)]
        X, Y, Z = np.meshgrid(*axes, indexing='ij')
        return sl, np.stack([X, Y, Z], axis=-1)

    def sample(self, F, P, order=1):
        P = np.asarray(P, np.float64).reshape(-1, 3)
        idx = ((P - self.lo) / self.h).T
        return ndimage.map_coordinates(F, idx, order=order, mode='nearest')

    def gradient(self, F, P, eps=None):
        eps = eps or self.h * 0.5
        P = np.asarray(P, np.float64).reshape(-1, 3)
        g = np.zeros_like(P)
        for c in range(3):
            d = np.zeros(3)
            d[c] = eps
            g[:, c] = (self.sample(F, P + d) - self.sample(F, P - d)) / (2 * eps)
        return g


# ------------------------------------------------------------------------------------ primitives
class Prim:
    """A part: dist(P) -> signed distance (approximate, metres); uv(P) -> (u, v, angle) in metres
    for the bark mapping; family groups parts that share one mapping (trunk and its burls)."""
    name = ''
    family = ''
    group = 'major'

    def bbox(self):
        raise NotImplementedError

    def dist(self, P):
        raise NotImplementedError


class TubeSDF(Prim):
    """A variable-radius tube along a Catmull-Rom spine, with an elliptical cross-section that can
    change along the length (sv: vertical stretch, sl: sideways stretch, both functions of the
    arc length s) and longitudinal ribs (furrows that follow the curve). The ends are rounded.

    uv_mode 'top':   angle 0 on the upper side (roots: the side we see); seam underneath.
    uv_mode 'front': as the swept tubes (wood.build_limb): angle measured from the side facing away
                     from the camera, u = (angle - pi) * r, so a tube built later from the same
                     spine continues the bark."""

    def __init__(self, name, pts, radii, family=None, group='major', step=0.1, sv=None, sl=None,
                 ribs=(0, 0.0, 0.0), uv_ref=None, uv_mode='top', s_end=None, end_taper=None, v0=0.0):
        self.name = name
        self.family = family or name
        self.group = group
        self.sp = Spine(pts, radii, step=step)
        Q, T = self.sp.pos, self.sp.tan
        if s_end is not None and s_end < self.sp.length:
            keep = self.sp.s <= s_end + 1e-9
            k = int(np.sum(keep))
            self.sp.pos, self.sp.tan, self.sp.rad, self.sp.s = Q[:k], T[:k], self.sp.rad[:k], self.sp.s[:k]
            Q, T = self.sp.pos, self.sp.tan
        self.Q, self.T, self.s = Q, T, self.sp.s
        self.r = self.sp.rad.copy()
        if end_taper is not None:            # (s0, s1, factor): radius eased down toward the end
            s0, s1, fac = end_taper
            t = np.clip((self.s - s0) / max(s1 - s0, 1e-6), 0, 1)
            self.r = self.r * (1 - (1 - fac) * t * t * (3 - 2 * t))
        # shape frame: V = up projected off the tangent (falls back to the outward direction)
        up = np.array([0.0, 1.0, 0.0])
        V = up[None, :] - (T @ up)[:, None] * T
        out = normalize(np.array([Q[-1, 0] - Q[0, 0], 0.0, Q[-1, 2] - Q[0, 2]]) + 1e-9)
        Vo = out[None, :] - (T @ out)[:, None] * T
        w = np.clip((np.linalg.norm(V, axis=1) - 0.2) / 0.3, 0, 1)[:, None]
        V = normalize(V * w + normalize(Vo + 1e-9) * (1 - w) + 1e-9)
        V = normalize(V - np.sum(V * T, axis=1)[:, None] * T)
        self.V = V
        self.L = normalize(np.cross(T, V))
        self.sv = np.ones(len(Q)) if sv is None else np.asarray([sv(x) for x in self.s])
        self.sl = np.ones(len(Q)) if sl is None else np.asarray([sl(x) for x in self.s])
        self.ribs = ribs                     # (count, amplitude, twist per metre)
        self.uv_mode = uv_mode
        self.v0 = v0
        if uv_mode == 'front':
            self.N_uv, self.B_uv = ring_frames(T, uv_ref)
        rmax = float(np.max(self.r * np.maximum(self.sv, self.sl))) * (1 + abs(ribs[1])) + 0.05
        self._lo = Q.min(axis=0) - rmax
        self._hi = Q.max(axis=0) + rmax

    def bbox(self):
        return self._lo, self._hi

    def _nearest(self, P):
        P = np.asarray(P, np.float64)
        shp = P.shape[:-1]
        X = P.reshape(-1, 3)
        best = np.full(len(X), np.inf)
        bj = np.zeros(len(X), np.int64)
        bt = np.zeros(len(X))
        Q = self.Q
        for j in range(len(Q) - 1):
            a = Q[j]
            ab = Q[j + 1] - a
            L2 = float(ab @ ab)
            if L2 < 1e-12:
                continue
            t = np.clip(((X - a) @ ab) / L2, 0.0, 1.0)
            d = X - a - t[:, None] * ab
            d2 = np.einsum('ij,ij->i', d, d)
            m = d2 < best
            best[m] = d2[m]
            bj[m] = j
            bt[m] = t[m]
        return X, shp, bj, bt

    def _local(self, P):
        X, shp, j, t = self._nearest(P)
        t1 = t[:, None]
        lerp = lambda A: A[j] * (1 - t1) + A[j + 1] * t1
        C = lerp(self.Q)
        o = X - C
        T = normalize(lerp(self.T))
        V = normalize(lerp(self.V))
        L = normalize(np.cross(T, V))
        r = self.r[j] * (1 - t) + self.r[j + 1] * t
        s = self.s[j] * (1 - t) + self.s[j + 1] * t
        sv = self.sv[j] * (1 - t) + self.sv[j + 1] * t
        sl = self.sl[j] * (1 - t) + self.sl[j + 1] * t
        ov = np.einsum('ij,ij->i', o, V)
        ol = np.einsum('ij,ij->i', o, L)
        ot = np.einsum('ij,ij->i', o, T)
        return dict(X=X, shp=shp, j=j, t=t, C=C, o=o, T=T, V=V, L=L, r=r, s=s, sv=sv, sl=sl, ov=ov, ol=ol, ot=ot)

    def dist(self, P):
        g = self._local(P)
        phi = np.arctan2(g['ol'], g['ov'])
        n, amp, tw = self.ribs
        r = g['r']
        if n:
            r = r * (1 + amp * np.cos(n * phi + tw * g['s'] + 0.7))
        sc = np.sqrt((g['ov'] / g['sv']) ** 2 + (g['ol'] / g['sl']) ** 2 + g['ot'] ** 2)
        d = (sc - r) * np.minimum(g['sv'], g['sl'])
        return d.reshape(g['shp'])

    def uv(self, P):
        """(u, v, angle) per point; u, v in metres of bark."""
        g = self._local(P)
        if self.uv_mode == 'front':
            t1 = g['t'][:, None]
            N = normalize(self.N_uv[g['j']] * (1 - t1) + self.N_uv[g['j'] + 1] * t1)
            B = normalize(np.cross(g['T'], N))
            ang = np.mod(np.arctan2(np.einsum('ij,ij->i', g['o'], B), np.einsum('ij,ij->i', g['o'], N)), 2 * math.pi)
            u = (ang - math.pi) * g['r']
        else:
            ang = np.arctan2(g['ol'], g['ov'])
            u = ang * g['r']
        return u, g['s'] + self.v0, ang, g['r']

    def info(self, P):
        g = self._local(P)
        return g


class TrunkSDF(Prim):
    """A trunk as a radial field about a curved axis: d = (rho - R(theta, y)) / |grad|, closed by a
    dome at the top. theta = 0 north (-z), pi/2 west (-x), pi south (toward the camera)."""

    def __init__(self, name, axis_pts, radius_fn, ref_fn, y_lo, y_top, family=None):
        from .tube import catmull
        self.name = name
        self.family = family or name
        q, _ = catmull(np.asarray(axis_pts, np.float64), 24)
        o = np.argsort(q[:, 1])
        self.ay, self.ax, self.az = q[o, 1], q[o, 0], q[o, 2]
        self.R = radius_fn
        self.Rref = ref_fn
        self.y_lo, self.y_top = y_lo, y_top
        rmax = float(np.max(radius_fn(np.linspace(0, 2 * math.pi, 64), np.zeros(64)))) + 0.3
        self._lo = np.array([self.ax.min() - rmax, y_lo, self.az.min() - rmax])
        self._hi = np.array([self.ax.max() + rmax, y_top + 0.3, self.az.max() + rmax])

    def bbox(self):
        return self._lo, self._hi

    def axis_at(self, y):
        return np.interp(y, self.ay, self.ax), np.interp(y, self.ay, self.az)

    def polar(self, P):
        P = np.asarray(P, np.float64)
        y = P[..., 1]
        cx, cz = self.axis_at(y)
        dx, dz = P[..., 0] - cx, P[..., 2] - cz
        rho = np.hypot(dx, dz)
        th = np.mod(np.arctan2(-dx, -dz), 2 * math.pi)
        return y, rho, th

    def dist(self, P):
        y, rho, th = self.polar(P)
        R = self.R(th, y)
        e = 0.05
        dRy = (self.R(th, y + e) - self.R(th, y - e)) / (2 * e)
        dRt = (self.R(th + e, y) - self.R(th - e, y)) / (2 * e)
        g = np.sqrt(1 + dRy ** 2 + (dRt / np.maximum(rho, 0.3)) ** 2)
        d = (rho - R) / g
        return np.maximum(d, y - self.y_top)

    def uv(self, P):
        y, rho, th = self.polar(P)
        Rr = self.Rref(y)
        u = (th - math.pi) * Rr
        v = y - np.maximum(rho - Rr, 0) * 0.85          # down the flare the bark keeps running
        return u, v, th, Rr


class EllipsoidSDF(Prim):
    def __init__(self, name, centre, radii, axes=None, family=None, group='minor', sign=1.0):
        self.name = name
        self.family = family or name
        self.group = group
        self.c = np.asarray(centre, np.float64)
        self.r = np.asarray(radii, np.float64)
        self.A = np.eye(3) if axes is None else np.asarray(axes, np.float64)   # rows: local axes
        m = float(np.max(self.r)) + 0.05
        self._lo, self._hi = self.c - m, self.c + m

    def bbox(self):
        return self._lo, self._hi

    def dist(self, P):
        P = np.asarray(P, np.float64)
        o = (P - self.c) @ self.A.T
        k0 = np.linalg.norm(o / self.r, axis=-1)
        k1 = np.linalg.norm(o / (self.r * self.r), axis=-1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


# ------------------------------------------------------------------------------------ combination
def smin_exp_field(grid, prims, k, margin=None):
    """Exponential smooth union of prims on the grid (blend radius ~k): -k ln sum exp(-d/k)."""
    acc = np.zeros(tuple(grid.n))
    margin = 4.0 * k if margin is None else margin
    for p in prims:
        lo, hi = p.bbox()
        sl, X = grid.box(lo - margin, hi + margin)
        if X.size == 0:
            continue
        d = p.dist(X)
        acc[sl] += np.exp(-np.clip(d, -8 * k, 40 * k) / k)
    with np.errstate(divide='ignore'):
        F = -k * np.log(np.maximum(acc, 1e-30))
    return np.minimum(F, 40 * k)


def smin_poly(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax_poly(a, b, k):
    return -smin_poly(-a, -b, k)


def min_field(grid, prims, fill=10.0):
    F = np.full(tuple(grid.n), fill)
    for p in prims:
        lo, hi = p.bbox()
        sl, X = grid.box(lo - 0.5, hi + 0.5)
        if X.size == 0:
            continue
        F[sl] = np.minimum(F[sl], p.dist(X))
    return F


# ------------------------------------------------------------------------------------ surface nets
def surface_nets(F, grid):
    """Quad mesh of the zero set of F (inside < 0): one vertex per crossed cell at the mean of its
    edge crossings, one quad per crossed edge. Returns (V, tris) with triangles counter-clockwise
    seen from outside."""
    nx, ny, nz = F.shape
    inside = F < 0
    s = inside.astype(np.int8)
    tot = np.zeros((nx - 1, ny - 1, nz - 1), np.int8)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                tot += s[dx:nx - 1 + dx, dy:ny - 1 + dy, dz:nz - 1 + dz]
    active = (tot > 0) & (tot < 8)
    cid = -np.ones(active.shape, np.int64)
    cid[active] = np.arange(int(active.sum()))
    nv = int(active.sum())
    acc = np.zeros((nv, 3))
    cnt = np.zeros(nv)
    quads = []
    for ax in range(3):
        u, v = (ax + 1) % 3, (ax + 2) % 3
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, F.shape[ax] - 1)
        sl1[ax] = slice(1, F.shape[ax])
        a = F[tuple(sl0)]
        b = F[tuple(sl1)]
        cross = (a < 0) != (b < 0)
        I = np.argwhere(cross)
        if len(I) == 0:
            continue
        fa = a[cross]
        fb = b[cross]
        t = fa / (fa - fb)
        pt = grid.lo + I * grid.h
        pt[:, ax] += t * grid.h
        for du in (0, -1):
            for dv in (0, -1):
                C = I.copy()
                C[:, u] += du
                C[:, v] += dv
                ok = np.all((C >= 0) & (C < np.array(active.shape)), axis=1)
                ids = cid[C[ok, 0], C[ok, 1], C[ok, 2]]
                good = ids >= 0
                np.add.at(acc, ids[good], pt[ok][good])
                np.add.at(cnt, ids[good], 1)
        # quads for edges with all four cells inside the cell range
        ok = (I[:, u] >= 1) & (I[:, v] >= 1) & (I[:, u] < active.shape[u]) & (I[:, v] < active.shape[v]) \
            & (I[:, ax] < active.shape[ax])
        J = I[ok]
        inn = fa[ok] < 0                      # inside at the lower end: the normal points +ax
        cells = []
        for du, dv in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            C = J.copy()
            C[:, u] += du
            C[:, v] += dv
            cells.append(cid[C[:, 0], C[:, 1], C[:, 2]])
        q = np.stack(cells, axis=1)
        q[~inn] = q[~inn][:, ::-1]
        quads.append(q[np.all(q >= 0, axis=1)])
    V = acc / np.maximum(cnt, 1)[:, None]
    Q = np.concatenate(quads)
    # split each quad along its shorter diagonal
    d02 = np.linalg.norm(V[Q[:, 0]] - V[Q[:, 2]], axis=1)
    d13 = np.linalg.norm(V[Q[:, 1]] - V[Q[:, 3]], axis=1)
    A = np.where((d02 <= d13)[:, None], Q[:, [0, 1, 2]], Q[:, [0, 1, 3]])
    B = np.where((d02 <= d13)[:, None], Q[:, [0, 2, 3]], Q[:, [1, 2, 3]])
    return V, np.concatenate([A, B])


def compact(V, T):
    used = np.unique(T)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[T], used


def project(V, F, grid, iters=4, keep=None):
    """Newton steps onto the zero set of the (trilinear) field."""
    V = V.copy()
    for _ in range(iters):
        f = grid.sample(F, V)
        g = grid.gradient(F, V)
        g2 = np.maximum(np.einsum('ij,ij->i', g, g), 1e-6)
        step = (f / g2)[:, None] * g
        nrm = np.linalg.norm(step, axis=1)
        step *= np.minimum(1.0, grid.h * 0.8 / np.maximum(nrm, 1e-12))[:, None]
        if keep is not None:
            step[keep] = 0
        V -= step
    return V


def laplacian(n, T):
    i = np.concatenate([T[:, 0], T[:, 1], T[:, 2], T[:, 1], T[:, 2], T[:, 0]])
    j = np.concatenate([T[:, 1], T[:, 2], T[:, 0], T[:, 0], T[:, 1], T[:, 2]])
    A = sparse.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(axis=1)).ravel()
    return sparse.diags(1.0 / np.maximum(deg, 1)) @ A


def taubin(V, T, iters=4, lam=0.5, mu=-0.53, keep=None):
    W = laplacian(len(V), T)
    V = V.copy()
    for _ in range(iters):
        for f in (lam, mu):
            D = W @ V - V
            if keep is not None:
                D[keep] = 0
            V = V + f * D
    return V


def boundary_vertices(T, n):
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    key = e[:, 0] * n + e[:, 1]
    u, c = np.unique(key, return_counts=True)
    b = u[c == 1]
    out = np.zeros(n, bool)
    out[b // n] = True
    out[b % n] = True
    return out


def vertex_normals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N = np.zeros_like(V)
    for c in range(3):
        np.add.at(N, T[:, c], fn)
    return normalize(N)


# ------------------------------------------------------------------------------------ decimation
def decimate(V, T, target, locked=None, min_dot=0.25, reg=1e-4):
    """Quadric-error edge collapse down to `target` triangles (Garland-Heckbert). Locked vertices
    stay put (an edge with one locked end collapses onto it). Keeps the mesh manifold (link
    condition) and refuses collapses that flip or squash a triangle."""
    V = np.asarray(V, np.float64).copy()
    T = np.asarray(T, np.int64)
    n = len(V)
    locked = np.zeros(n, bool) if locked is None else locked.copy()
    bnd = boundary_vertices(T, n)
    locked |= bnd
    # quadrics
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(b - a, c - a)
    area = np.linalg.norm(fn, axis=1) * 0.5
    nn = fn / np.maximum(2 * area, 1e-12)[:, None]
    p = np.concatenate([nn, -np.einsum('ij,ij->i', nn, a)[:, None]], axis=1)
    K = p[:, :, None] * p[:, None, :] * area[:, None, None]
    Q = np.zeros((n, 4, 4))
    for k in range(3):
        np.add.at(Q, T[:, k], K)
    # a little pull toward each vertex's own position (keeps flat regions from sliding)
    Rg = np.zeros((n, 4, 4))
    Rg[:, 0, 0] = Rg[:, 1, 1] = Rg[:, 2, 2] = 1.0
    Rg[:, :3, 3] = -V
    Rg[:, 3, :3] = -V
    Rg[:, 3, 3] = np.einsum('ij,ij->i', V, V)
    Q += Rg * reg
    faces = [list(f) for f in T]
    alive = [True] * len(faces)
    vf = [set() for _ in range(n)]
    for fi, f in enumerate(faces):
        for v in f:
            vf[v].add(fi)
    dead = [False] * n
    stamp = [0] * n
    nfaces = len(faces)

    def target_pos(u, v):
        if locked[u] and locked[v]:
            return None, 0.0
        if locked[u]:
            x = V[u]
        elif locked[v]:
            x = V[v]
        else:
            Qe = Q[u] + Q[v]
            A = Qe[:3, :3]
            try:
                if abs(np.linalg.det(A)) < 1e-12:
                    raise np.linalg.LinAlgError
                x = np.linalg.solve(A, -Qe[:3, 3])
                if np.linalg.norm(x - (V[u] + V[v]) * 0.5) > 2.0 * np.linalg.norm(V[u] - V[v]) + 1e-6:
                    raise np.linalg.LinAlgError
            except np.linalg.LinAlgError:
                cands = [V[u], V[v], (V[u] + V[v]) * 0.5]
                errs = [np.append(cx, 1) @ (Q[u] + Q[v]) @ np.append(cx, 1) for cx in cands]
                x = cands[int(np.argmin(errs))]
        Qe = Q[u] + Q[v]
        h = np.append(x, 1.0)
        return x, float(h @ Qe @ h)

    heap = []

    def push(u, v):
        if u > v:
            u, v = v, u
        x, cst = target_pos(u, v)
        if x is None:
            return
        cst += 1e-6 * float(np.sum((V[u] - V[v]) ** 2))
        heapq.heappush(heap, (cst, u, v, stamp[u], stamp[v]))

    edges = set()
    for f in faces:
        for i in range(3):
            e = (min(f[i], f[(i + 1) % 3]), max(f[i], f[(i + 1) % 3]))
            edges.add(e)
    for u, v in edges:
        push(u, v)

    def nbrs(u):
        s = set()
        for fi in vf[u]:
            s.update(faces[fi])
        s.discard(u)
        return s

    while nfaces > target and heap:
        cst, u, v, su, sv_ = heapq.heappop(heap)
        if dead[u] or dead[v] or stamp[u] != su or stamp[v] != sv_:
            continue
        shared = vf[u] & vf[v]
        if not shared:
            continue
        # link condition
        common = nbrs(u) & nbrs(v)
        if len(common) != len(shared):
            continue
        x, _ = target_pos(u, v)
        if x is None:
            continue
        # flip / squash test on the faces that stay
        ok = True
        for w in (u, v):
            for fi in vf[w] - shared:
                f = faces[fi]
                P0 = [V[q] for q in f]
                P1 = [x if (q == u or q == v) else V[q] for q in f]
                n0 = np.cross(P0[1] - P0[0], P0[2] - P0[0])
                n1 = np.cross(P1[1] - P1[0], P1[2] - P1[0])
                l0, l1 = np.linalg.norm(n0), np.linalg.norm(n1)
                if l1 < 1e-10 or (l0 > 1e-12 and float(n0 @ n1) < min_dot * l0 * l1):
                    ok = False
                    break
                # refuse needle triangles
                e2 = max(np.sum((P1[0] - P1[1]) ** 2), np.sum((P1[1] - P1[2]) ** 2), np.sum((P1[2] - P1[0]) ** 2))
                e20 = max(np.sum((P0[0] - P0[1]) ** 2), np.sum((P0[1] - P0[2]) ** 2), np.sum((P0[2] - P0[0]) ** 2))
                if l1 / e2 < 0.1 and l1 / e2 < 0.9 * l0 / max(e20, 1e-12):
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        # collapse u into v
        for fi in shared:
            alive[fi] = False
            for q in faces[fi]:
                if q != u:
                    vf[q].discard(fi)
            nfaces -= 1
        for fi in vf[u] - shared:
            f = faces[fi]
            faces[fi] = [v if q == u else q for q in f]
            vf[v].add(fi)
        vf[u] = set()
        dead[u] = True
        V[v] = x
        Q[v] = Q[u] + Q[v]
        locked[v] = locked[v] or locked[u]
        stamp[v] += 1
        for w in nbrs(v):
            push(v, w)
    F2 = np.array([f for f, al in zip(faces, alive) if al], np.int64)
    Vc, Tc, used = compact(V, F2)
    return Vc, Tc, used


# ------------------------------------------------------------------------------------ uv per owner
def corner_uvs(V, T, owner, uv_fns, wrap_fns):
    """Per-corner uv: each triangle uses its owner's mapping; angles are unwrapped within the
    triangle so no triangle spans the texture across a seam. Returns (corner_uv (m, 3, 2))."""
    m = len(T)
    out = np.zeros((m, 3, 2))
    for o in np.unique(owner):
        sel = np.where(owner == o)[0]
        P = V[T[sel]].reshape(-1, 3)
        u, v, ang, rr = uv_fns[o](P)
        u = u.reshape(-1, 3)
        v = v.reshape(-1, 3)
        ang = ang.reshape(-1, 3)
        rr = rr.reshape(-1, 3)
        if wrap_fns[o]:
            a0 = ang[:, :1]
            da = ang - a0
            jump = np.round(da / (2 * math.pi))
            u = u - jump * 2 * math.pi * rr
        out[sel, :, 0] = u
        out[sel, :, 1] = v
    return out


def weld(V, T, cuv, extra=None, tol=1e-5):
    """Split vertices where the corners meeting at them disagree on uv. Returns (V2, T2, uv2, src)
    where src[i] is the original vertex of new vertex i."""
    m = len(T)
    vid = T.reshape(-1)
    uv = cuv.reshape(-1, 2)
    key = np.concatenate([vid[:, None].astype(np.float64), np.round(uv / tol)], axis=1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    T2 = inv.reshape(m, 3)
    src = vid[first]
    return V[src], T2, uv[first], src
