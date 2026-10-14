"""Swept tubes along smooth spines: trunks, limbs, branches, roots, ropes, bamboo culms.

A spine is a Catmull-Rom curve through control points with a radius at each control point. A tube
is a grid of rings along the spine: ring k is a closed curve around the spine whose radius can
depend on the angle (lobes, buttresses, flattening) and on the position along the spine.

UVs are near-isometric so that textures keep one texel per native pixel everywhere:
  u = arc length around the ring (metres), v = arc length along each column (metres),
both multiplied later by the texel density. The ring seam (theta = 0) is placed on the side facing
away from the fixed camera (north and down), so it is never seen.
"""
from __future__ import annotations

import math

import numpy as np

from .core import cam_vectors, normalize
from .mesh import MeshData


def catmull(pts, n_per_seg=8):
    """Centripetal-ish uniform Catmull-Rom through pts (k, d); returns samples (m, d) and the
    parameter t in [0, k-1] of each sample."""
    P = np.asarray(pts, np.float64)
    k = len(P)
    if k == 2:
        t = np.linspace(0, 1, n_per_seg + 1)
        return P[0] + (P[1] - P[0]) * t[:, None], t
    ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    ts = []
    for i in range(1, k):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        last = i == k - 1
        for j in range(n_per_seg + (1 if last else 0)):
            t = j / n_per_seg
            t2, t3 = t * t, t * t * t
            q = 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append(q)
            ts.append(i - 1 + t)
    return np.array(out), np.array(ts)


class Spine:
    """A smooth curve with a radius profile, resampled at a fixed arc-length step."""

    def __init__(self, pts, radii, step=0.25, dense=16, step_fn=None):
        """step_fn(fraction) -> local ring step (m), for adaptive spacing (dense where the shape
        changes fast); otherwise a fixed step."""
        pts = np.asarray(pts, np.float64)
        radii = np.asarray(radii, np.float64)
        q, t = catmull(pts, dense)
        # arc length
        d = np.linalg.norm(np.diff(q, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(d)])
        L = s[-1]
        if step_fn is None:
            m = max(2, int(math.ceil(L / step)) + 1)
            si = np.linspace(0, L, m)
        else:
            si = [0.0]
            while si[-1] < L:
                si.append(si[-1] + max(0.02, step_fn(si[-1] / L)))
            si = np.array(si)
            si = si * (L / si[-1])
        self.pos = np.stack([np.interp(si, s, q[:, c]) for c in range(3)], axis=1)
        ti = np.interp(si, s, t)
        # radius: smooth (cubic) interpolation of the control radii over the curve parameter
        rr, tr = catmull(radii[:, None], dense)
        self.rad = np.maximum(np.interp(ti, tr, rr[:, 0]), 1e-3)
        self.s = si
        self.length = L
        tan = np.gradient(self.pos, axis=0)
        self.tan = normalize(tan)
        self.t = ti

    def point_at(self, f):
        """Position, tangent and radius at fraction f of the length."""
        s = f * self.length
        p = np.array([np.interp(s, self.s, self.pos[:, c]) for c in range(3)])
        tg = normalize(np.array([np.interp(s, self.s, self.tan[:, c]) for c in range(3)]))
        r = float(np.interp(s, self.s, self.rad))
        return p, tg, r


def ring_frames(tan, ref=None):
    """Per-ring frames (N, B): N points from the spine toward the seam reference (away from the
    camera) projected onto the ring plane; B = T x N. Falls back smoothly when the tangent is close
    to the reference."""
    if ref is None:
        _, _, back = cam_vectors()
        ref = -back                       # away from the camera: north and down
    ref = normalize(np.asarray(ref, np.float64))
    alt = np.array([0.0, 1.0, 0.0])
    N = ref[None, :] - (tan @ ref)[:, None] * tan
    nl = np.linalg.norm(N, axis=1)
    N2 = alt[None, :] - (tan @ alt)[:, None] * tan
    w = np.clip((nl - 0.15) / 0.25, 0, 1)[:, None]
    N = normalize(N * w + normalize(N2) * (1 - w) * 0.5 + 1e-9)
    # smooth the frames a little so a sudden switch cannot twist the tube
    for _ in range(2):
        N[1:-1] = normalize(N[:-2] + 2 * N[1:-1] + N[2:])
        N = normalize(N - (np.sum(N * tan, axis=1))[:, None] * tan)
    B = normalize(np.cross(tan, N))
    return N, B


def tube(spine: Spine, n_around=24, rfun=None, cap_start=False, cap_end=True, ref=None,
         ring_offset=None, end_point=True, yscale=None):
    """Build a tube. rfun(theta (n,), k, frac, spine) -> radius (n,) for ring k; default circular.
    ring_offset(k, frac) -> extra world offset of the ring centre.
    Returns (MeshData, info) where info holds the grid (positions, normals, theta, s) for painting.
    UV: u, v in metres (see module docstring)."""
    m = len(spine.pos)
    N, B = ring_frames(spine.tan, ref)
    th = np.linspace(0, 2 * math.pi, n_around, endpoint=False)
    P = np.zeros((m, n_around + 1, 3))
    R = np.zeros((m, n_around + 1))
    for k in range(m):
        frac = spine.s[k] / max(spine.length, 1e-9)
        r = np.full(n_around, spine.rad[k]) if rfun is None else np.asarray(rfun(th, k, frac, spine), np.float64)
        c = spine.pos[k] + (np.zeros(3) if ring_offset is None else np.asarray(ring_offset(k, frac)))
        ring = c[None, :] + r[:, None] * (np.cos(th)[:, None] * N[k][None, :] + np.sin(th)[:, None] * B[k][None, :])
        if yscale is not None:
            ring[:, 1] = c[1] + (ring[:, 1] - c[1]) * yscale(k, frac)
        P[k, :n_around] = ring
        P[k, n_around] = ring[0]          # duplicate seam column (separate UVs)
        R[k, :n_around] = r
        R[k, n_around] = r[0]
    # normals from the grid (central differences; wraps around the ring)
    Pw = P[:, :n_around]
    dth = np.roll(Pw, -1, axis=1) - np.roll(Pw, 1, axis=1)
    ds = np.zeros_like(Pw)
    ds[1:-1] = Pw[2:] - Pw[:-2]
    ds[0] = Pw[1] - Pw[0]
    ds[-1] = Pw[-1] - Pw[-2]
    nrm = normalize(np.cross(ds, dth))
    # orientation: outward = away from the spine
    radial = Pw - spine.pos[:, None, :]
    flip = np.sum(nrm * radial) < 0
    if flip:
        nrm = -nrm
    # degenerate rings (radius ~0): use the radial direction
    bad = np.linalg.norm(np.cross(ds, dth), axis=2) < 1e-10
    if bad.any():
        nrm[bad] = normalize(radial[bad] + 1e-9)
    NRM = np.concatenate([nrm, nrm[:, :1]], axis=1)
    # UV: u = arc length around each ring; v = arc length along each column
    seg_u = np.linalg.norm(np.diff(P, axis=1), axis=2)
    U = np.concatenate([np.zeros((m, 1)), np.cumsum(seg_u, axis=1)], axis=1)
    seg_v = np.linalg.norm(np.diff(P, axis=0), axis=2)
    V = np.concatenate([np.zeros((1, n_around + 1)), np.cumsum(seg_v, axis=0)], axis=0)
    cols = n_around + 1
    idx = []
    for k in range(m - 1):
        for j in range(n_around):
            a = k * cols + j
            b = k * cols + j + 1
            d = (k + 1) * cols + j
            e = (k + 1) * cols + j + 1
            idx.append((a, b, e))
            idx.append((a, e, d))
    idx = np.array(idx, np.int64)
    pf = P.reshape(-1, 3)
    nf = NRM.reshape(-1, 3)
    # make triangles face outward: compare with the vertex normals
    fa, fb, fc = pf[idx[:, 0]], pf[idx[:, 1]], pf[idx[:, 2]]
    fn = np.cross(fb - fa, fc - fa)
    vn = nf[idx[:, 0]] + nf[idx[:, 1]] + nf[idx[:, 2]]
    if np.sum(np.sum(fn * vn, axis=1) < 0) > len(idx) / 2:
        idx = idx[:, [0, 2, 1]]
    uv = np.stack([U.reshape(-1), V.reshape(-1)], axis=1)
    md = MeshData()
    md.add(pf, nf, uv, idx)
    info = {'P': P, 'N': NRM, 'U': U, 'V': V, 'R': R, 'theta': np.concatenate([th, [2 * math.pi]]),
            's': spine.s, 'frac': spine.s / max(spine.length, 1e-9), 'n_around': n_around}
    # caps: a cone to a point (the end of a branch)
    if cap_end:
        tip = spine.pos[-1] + spine.tan[-1] * max(spine.rad[-1], 0.01) * 0.8
        last = P[-1, :n_around]
        base = md.count
        pts = np.vstack([last, tip[None, :]])
        nrm2 = np.vstack([NRM[-1, :n_around] * 0.5 + spine.tan[-1] * 0.5, spine.tan[-1][None, :]])
        uvc = np.vstack([np.stack([U[-1, :n_around], np.full(n_around, V[-1].max())], 1),
                         [[U[-1].max() * 0.5, V[-1].max() + spine.rad[-1]]]])
        tri = [(j, (j + 1) % n_around, n_around) for j in range(n_around)]
        tri = np.array(tri)
        fa, fb, fc = pts[tri[:, 0]], pts[tri[:, 1]], pts[tri[:, 2]]
        if np.sum(np.cross(fb - fa, fc - fa) @ spine.tan[-1]) < 0:
            tri = tri[:, [0, 2, 1]]
        md.add(pts, normalize(nrm2), uvc, tri)
    if cap_start:
        c0 = spine.pos[0]
        first = P[0, :n_around]
        pts = np.vstack([first, c0[None, :]])
        nrm2 = np.vstack([np.tile(-spine.tan[0], (n_around, 1)), -spine.tan[0][None, :]])
        uvc = np.vstack([np.stack([U[0, :n_around], np.zeros(n_around)], 1), [[0, 0]]])
        tri = np.array([(j, (j + 1) % n_around, n_around) for j in range(n_around)])
        fa, fb, fc = pts[tri[:, 0]], pts[tri[:, 1]], pts[tri[:, 2]]
        if np.sum(np.cross(fb - fa, fc - fa) @ (-spine.tan[0])) < 0:
            tri = tri[:, [0, 2, 1]]
        md.add(pts, normalize(nrm2), uvc, tri)
    return md, info
