"""Distance fields to polylines and polygons on the grid, smooth blends."""
from __future__ import annotations

import numpy as np


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smin(a, b, k):
    """Polynomial smooth minimum (k = blend width)."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def resample_polyline(pts, step):
    """Polyline -> points every `step` metres (keeps the ends)."""
    pts = np.asarray(pts, np.float64)
    seg = np.diff(pts, axis=0)
    lens = np.hypot(seg[:, 0], seg[:, 1])
    total = lens.sum()
    n = max(2, int(np.ceil(total / step)) + 1)
    s = np.linspace(0.0, total, n)
    cum = np.concatenate([[0.0], np.cumsum(lens)])
    out = np.empty((n, pts.shape[1]))
    for k in range(pts.shape[1]):
        out[:, k] = np.interp(s, cum, pts[:, k])
    return out, s


def catmull(pts, samples_per_seg=12):
    """Centripetal-ish Catmull-Rom through the points (open curve, ends clamped)."""
    p = np.asarray(pts, np.float64)
    if len(p) < 3:
        return p
    ext = np.vstack([p[0] * 2 - p[1], p, p[-1] * 2 - p[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0, 1, samples_per_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-1])
    return np.array(out)


def polyline_field(X, Z, pts, values=None):
    """Distance from each grid point to a polyline, plus the arc length and (optionally) the
    interpolated per-vertex values at the nearest point. pts: (n, 2); values: (n,) or (n, k)."""
    P = np.asarray(pts, np.float64)
    best = np.full(X.shape, np.inf)
    arc = np.zeros(X.shape)
    seglen = np.hypot(*(np.diff(P, axis=0).T))
    cum = np.concatenate([[0.0], np.cumsum(seglen)])
    vals = None
    if values is not None:
        V = np.asarray(values, np.float64)
        if V.ndim == 1:
            V = V[:, None]
        vals = np.zeros(X.shape + (V.shape[1],))
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        ab = b - a
        L2 = max(ab @ ab, 1e-12)
        t = np.clip(((X - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / L2, 0.0, 1.0)
        dx = X - (a[0] + ab[0] * t)
        dz = Z - (a[1] + ab[1] * t)
        d = np.hypot(dx, dz)
        m = d < best
        best = np.where(m, d, best)
        arc = np.where(m, cum[i] + t * seglen[i], arc)
        if vals is not None:
            vi = V[i][None, None, :] + (V[i + 1] - V[i])[None, None, :] * t[..., None]
            vals = np.where(m[..., None], vi, vals)
    if vals is not None and vals.shape[-1] == 1:
        vals = vals[..., 0]
    return best, arc, vals


def polygon_sdf(X, Z, poly):
    """Signed distance to a closed polygon (negative inside)."""
    P = np.asarray(poly, np.float64)
    n = len(P)
    d = np.full(X.shape, np.inf)
    inside = np.zeros(X.shape, bool)
    for i in range(n):
        a = P[i]
        b = P[(i + 1) % n]
        ab = b - a
        L2 = max(ab @ ab, 1e-12)
        t = np.clip(((X - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / L2, 0.0, 1.0)
        d = np.minimum(d, np.hypot(X - (a[0] + ab[0] * t), Z - (a[1] + ab[1] * t)))
        cond = ((a[1] > Z) != (b[1] > Z))
        xint = a[0] + (Z - a[1]) * (b[0] - a[0]) / np.where(np.abs(b[1] - a[1]) < 1e-12, 1e-12, (b[1] - a[1]))
        inside ^= cond & (X < xint)
    return np.where(inside, -d, d)
