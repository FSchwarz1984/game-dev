"""Render a prop's solids into per-layer G-buffers by sphere tracing along the oblique view ray.

Screen <-> world (core.py): sx = ax + 20 x, sy = ay + 20 (z - y). The view ray through pixel centre
(sx, sy) is P(t) = (X, (t - S)/2, (t + S)/2) with X = (sx - ax)/20, S = (sy - ay)/20 and t = y + z,
the depth (larger = nearer). We march from the near end (largest t) into the scene.

Each layer ('part') is rendered on its own z-buffer from its own solids, so a lower layer keeps the
pixels an upper layer covers (x-ray holes and the 遠化 recede never open onto nothing). Ambient
occlusion and the key-light occlusion use every solid of the prop and the ground plane.
"""
import math

import numpy as np

from .core import PPM, SQ2, normalize

EPS = 0.0015
MAX_STEPS = 160


class GBuffer:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.t = np.full((H, W), -np.inf)
        self.sid = np.full((H, W), -1, np.int32)        # solid index (lines: 10000 + line index)
        self.P = np.zeros((H, W, 3))
        self.N = np.zeros((H, W, 3))
        self.u = np.zeros((H, W))                       # lines: arclength (m); solids: free

    @property
    def hit(self):
        return self.sid >= 0


class Frame:
    """The pixel frame shared by all layers of a prop: size and the anchor (screen px of the origin)."""

    def __init__(self, lo, hi, margin=4):
        # world bbox -> screen bbox
        x0 = math.floor(lo[0] * PPM) - margin
        x1 = math.ceil(hi[0] * PPM) + margin
        y0 = math.floor((lo[2] - hi[1]) * PPM) - margin
        y1 = math.ceil((hi[2] - lo[1]) * PPM) + margin
        self.ax = -x0
        self.ay = -y0
        self.W = x1 - x0
        self.H = y1 - y0

    def rays(self, x0, x1, y0, y1):
        xs = np.arange(max(0, x0), min(self.W, x1))
        ys = np.arange(max(0, y0), min(self.H, y1))
        if xs.size == 0 or ys.size == 0:
            return None
        YY, XX = np.meshgrid(ys, xs, indexing='ij')
        X = (XX + 0.5 - self.ax) / PPM
        S = (YY + 0.5 - self.ay) / PPM
        return YY.ravel(), XX.ravel(), X.ravel(), S.ravel()

    def screen_box(self, lo, hi, pad=1):
        x0 = int(math.floor(self.ax + lo[0] * PPM)) - pad
        x1 = int(math.ceil(self.ax + hi[0] * PPM)) + pad
        y0 = int(math.floor(self.ay + (lo[2] - hi[1]) * PPM)) - pad
        y1 = int(math.ceil(self.ay + (hi[2] - lo[1]) * PPM)) + pad
        return x0, x1, y0, y1

    def to_screen(self, P):
        P = np.asarray(P, np.float64)
        return self.ax + P[..., 0] * PPM, self.ay + (P[..., 2] - P[..., 1]) * PPM


def trace_solid(solid, frame):
    """Sphere-trace one solid over its screen box. Returns (ys, xs, t, P) of the hits."""
    lo, hi = solid.bbox()
    box = frame.screen_box(lo, hi)
    r = frame.rays(*box)
    if r is None:
        return None
    ys, xs, X, S = r
    # the t interval where the ray is inside the bbox (y and z slabs)
    t_hi = np.minimum(2 * hi[1] + S, 2 * hi[2] - S)
    t_lo = np.maximum(2 * lo[1] + S, 2 * lo[2] - S)
    ok = (t_lo <= t_hi) & (X >= lo[0] - 1e-6) & (X <= hi[0] + 1e-6)
    ys, xs, X, S, t, t_lo = ys[ok], xs[ok], X[ok], S[ok], t_hi[ok], t_lo[ok]
    n = ys.size
    hit = np.zeros(n, bool)
    alive = np.ones(n, bool)
    L = max(1.0, solid.lipschitz)
    idx = np.arange(n)
    for _ in range(MAX_STEPS):
        a = idx[alive]
        if a.size == 0:
            break
        P = np.stack([X[a], (t[a] - S[a]) / 2, (t[a] + S[a]) / 2], -1)
        d = solid.sdf(P) / L
        h = d < EPS
        hit[a[h]] = True
        alive[a[h]] = False
        step = np.maximum(d * SQ2, 0.0008)
        t[a] = t[a] - np.where(h, 0.0, step)
        gone = t[a] < t_lo[a]
        alive[a[gone]] = False
    k = np.nonzero(hit)[0]
    P = np.stack([X[k], (t[k] - S[k]) / 2, (t[k] + S[k]) / 2], -1)
    return ys[k], xs[k], t[k], P


def solid_normals(solid, P, h=0.0025):
    e = np.eye(3) * h
    g = np.stack([solid.sdf(P + e[i]) - solid.sdf(P - e[i]) for i in range(3)], -1)
    return normalize(g)


def render_part(solids, lines, frame, part):
    """Z-buffer of one layer."""
    G = GBuffer(frame.W, frame.H)
    for i, s in enumerate(solids):
        if s.part != part:
            continue
        res = trace_solid(s, frame)
        if res is None:
            continue
        ys, xs, t, P = res
        if ys.size == 0:
            continue
        nearer = t > G.t[ys, xs]
        ys, xs, t, P = ys[nearer], xs[nearer], t[nearer], P[nearer]
        G.t[ys, xs] = t
        G.sid[ys, xs] = i
        G.P[ys, xs] = P
        G.N[ys, xs] = solid_normals(s, P)
    for j, ln in enumerate(lines):
        if ln.part != part:
            continue
        draw_line(G, frame, ln, 10000 + j)
    return G


class Line:
    """A thin 3D polyline drawn in screen space (ropes, cords, straws, cracks that stand proud).
    width_px: 1 or 2. Depth bias pushes it in front of the surface it lies on."""

    def __init__(self, pts, mat, part='body', width_px=1, bias=0.02, tag=None, data=None):
        self.pts = np.asarray(pts, np.float64)
        self.mat = mat
        self.part = part
        self.width = int(width_px)
        self.bias = float(bias)
        self.tag = tag
        self.data = data or {}

    def bbox(self):
        r = 0.05
        return self.pts.min(0) - r, self.pts.max(0) + r


def draw_line(G, frame, ln, sid):
    P = ln.pts
    seg = np.diff(P, axis=0)
    sx, sy = frame.to_screen(P)
    lens = np.hypot(np.diff(sx), np.diff(sy))
    acc = 0.0
    for k in range(len(seg)):
        n = max(2, int(math.ceil(lens[k] * 3)) + 1)
        f = np.linspace(0, 1, n)[:, None]
        Q = P[k] + seg[k] * f
        qx, qy = frame.to_screen(Q)
        tq = Q[:, 1] + Q[:, 2] + ln.bias
        tang = normalize(seg[k][None, :].repeat(n, 0))
        arc = acc + np.linalg.norm(seg[k]) * f[:, 0]
        acc += np.linalg.norm(seg[k])
        offs = [(0, 0)] if ln.width <= 1 else [(0, 0), (1, 0), (0, 1), (1, 1)]
        for ox, oy in offs:
            xs = np.floor(qx + ox * 0.5).astype(np.int64)
            ys = np.floor(qy + oy * 0.5).astype(np.int64)
            ok = (xs >= 0) & (ys >= 0) & (xs < G.W) & (ys < G.H)
            xs, ys, t, Qk, tg, ar = xs[ok], ys[ok], tq[ok], Q[ok], tang[ok], arc[ok]
            nearer = t > G.t[ys, xs]
            xs, ys, t, Qk, tg, ar = xs[nearer], ys[nearer], t[nearer], Qk[nearer], tg[nearer], ar[nearer]
            G.t[ys, xs] = t
            G.sid[ys, xs] = sid
            G.P[ys, xs] = Qk
            # a cord's normal: the view direction made perpendicular to the cord, tipped up a little
            v = np.array([0.0, 0.62, 0.78])
            nn = normalize(v[None, :] - (tg @ v)[:, None] * tg)
            G.N[ys, xs] = nn
            G.u[ys, xs] = ar


def ao_field(solids, P, N, dists=(0.04, 0.09, 0.18, 0.34), ground=True, skip=None):
    """SDF ambient occlusion at points P with normals N: 1 open .. 0 enclosed."""
    occ = np.zeros(len(P))
    w = 1.0
    tot = 0.0
    for d in dists:
        Q = P + N * d
        best = np.full(len(P), np.inf)
        for i, s in enumerate(solids):
            if skip is not None and i in skip:
                continue
            lo, hi = s.bbox()
            m = np.all((Q >= lo - d - 0.05) & (Q <= hi + d + 0.05), axis=1)
            if not m.any():
                continue
            v = np.full(len(P), np.inf)
            v[m] = s.sdf(Q[m])
            best = np.minimum(best, v)
        if ground:
            best = np.minimum(best, Q[:, 1])
        occ += w * np.clip((d - best) / d, 0.0, 1.0)
        tot += w
        w *= 0.7
    return np.clip(1.0 - occ / tot, 0.0, 1.0)


def occlusion_toward(solids, P, D, max_dist=1.6, steps=24, skip=None):
    """Soft visibility of direction D from points P (key-light shadow on the prop itself)."""
    vis = np.ones(len(P))
    t = np.full(len(P), 0.03)
    for _ in range(steps):
        Q = P + D[None, :] * t[:, None]
        best = np.full(len(P), np.inf)
        for i, s in enumerate(solids):
            if skip is not None and i in skip:
                continue
            lo, hi = s.bbox()
            m = np.all((Q >= lo - 0.1) & (Q <= hi + 0.1), axis=1)
            if not m.any():
                continue
            v = np.full(len(P), np.inf)
            v[m] = s.sdf(Q[m])
            best = np.minimum(best, v)
        vis = np.minimum(vis, np.clip(8.0 * best / t, 0.0, 1.0))
        t = t + np.clip(best, 0.02, 0.25)
        if np.all(t > max_dist):
            break
    return np.clip(vis, 0.0, 1.0)


def heightfield(solids, lo, hi, res=PPM):
    """Top and bottom heights of the prop over the ground grid (1 cell = 1/res m), for shadows.
    Returns (top, bottom, x0, z0) with top/bottom NaN where nothing stands."""
    nx = int(math.ceil((hi[0] - lo[0]) * res)) + 1
    nz = int(math.ceil((hi[2] - lo[2]) * res)) + 1
    xs = lo[0] + (np.arange(nx) + 0.5) / res
    zs = lo[2] + (np.arange(nz) + 0.5) / res
    top = np.full((nz, nx), -np.inf)
    bot = np.full((nz, nx), np.inf)
    for s in solids:
        if s.data.get('no_shadow'):
            continue
        slo, shi = s.bbox()
        i0 = max(0, int((slo[0] - lo[0]) * res) - 1)
        i1 = min(nx, int((shi[0] - lo[0]) * res) + 2)
        k0 = max(0, int((slo[2] - lo[2]) * res) - 1)
        k1 = min(nz, int((shi[2] - lo[2]) * res) + 2)
        if i1 <= i0 or k1 <= k0:
            continue
        ZZ, XX = np.meshgrid(zs[k0:k1], xs[i0:i1], indexing='ij')
        X = XX.ravel()
        Z = ZZ.ravel()
        L = max(1.0, s.lipschitz)
        for direction in (-1, 1):
            y = np.full(X.size, shi[1] + 0.01 if direction < 0 else max(slo[1], 0.0) - 0.01)
            end = slo[1] - 0.01 if direction < 0 else shi[1] + 0.01
            hit = np.zeros(X.size, bool)
            alive = np.ones(X.size, bool)
            for _ in range(96):
                a = np.nonzero(alive)[0]
                if a.size == 0:
                    break
                P = np.stack([X[a], y[a], Z[a]], -1)
                d = s.sdf(P) / L
                h = d < 0.004
                hit[a[h]] = True
                alive[a[h]] = False
                y[a] = y[a] + direction * np.where(h, 0.0, np.maximum(d, 0.002))
                past = (y[a] < end) if direction < 0 else (y[a] > end)
                alive[a[past]] = False
            hy = np.where(hit, y, np.nan).reshape(ZZ.shape)
            if direction < 0:
                top[k0:k1, i0:i1] = np.fmax(top[k0:k1, i0:i1], np.where(np.isnan(hy), -np.inf, hy))
            else:
                bot[k0:k1, i0:i1] = np.fmin(bot[k0:k1, i0:i1], np.where(np.isnan(hy), np.inf, hy))
    top = np.where(np.isfinite(top), top, np.nan)
    bot = np.where(np.isfinite(bot), np.maximum(bot, 0.0), np.nan)
    bot = np.where(np.isnan(top), np.nan, np.where(bot < 0.03, 0.0, bot))
    return top, bot, lo[0], lo[2]
