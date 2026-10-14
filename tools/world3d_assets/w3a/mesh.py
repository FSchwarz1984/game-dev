"""Triangle mesh data and the small set of builders the assets need.

A MeshData holds one Godot surface: positions, normals, uv, optional uv2 / colour / custom0, and
triangle indices (counter-clockwise seen from outside, Godot's front face is clockwise in screen
space after its own flip: we write indices so that (b - a) x (c - a) points outward and flip once
on export, see export.py).
"""
from __future__ import annotations

import numpy as np

from .core import normalize


class MeshData:
    def __init__(self):
        self.p = []      # list of (n, 3) arrays
        self.n = []
        self.uv = []
        self.uv2 = []
        self.col = []
        self.cus = []
        self.cus1 = []
        self.idx = []
        self.count = 0
        self.has_uv2 = False
        self.has_col = False
        self.has_cus = False
        self.has_cus1 = False

    def add(self, p, n, uv, idx, uv2=None, col=None, cus=None, cus1=None):
        p = np.asarray(p, np.float64).reshape(-1, 3)
        k = len(p)
        self.p.append(p)
        self.n.append(np.asarray(n, np.float64).reshape(-1, 3))
        self.uv.append(np.asarray(uv, np.float64).reshape(-1, 2) if uv is not None else np.zeros((k, 2)))
        if uv2 is not None:
            self.has_uv2 = True
        if col is not None:
            self.has_col = True
        if cus is not None:
            self.has_cus = True
        if cus1 is not None:
            self.has_cus1 = True
        self.cus1.append(None if cus1 is None else np.asarray(cus1, np.float64).reshape(-1, 4))
        self.uv2.append(None if uv2 is None else np.asarray(uv2, np.float64).reshape(-1, 2))
        self.col.append(None if col is None else np.asarray(col, np.float64).reshape(-1, 4))
        self.cus.append(None if cus is None else np.asarray(cus, np.float64).reshape(-1, 4))
        self.idx.append(np.asarray(idx, np.int64).reshape(-1, 3) + self.count)
        self.count += k
        return self

    def merge(self, other: 'MeshData'):
        o = other.arrays()
        if o is None:
            return self
        self.add(o['p'], o['n'], o['uv'], o['idx'], o.get('uv2'), o.get('col'), o.get('cus'), o.get('cus1'))
        return self

    def arrays(self):
        if not self.p:
            return None
        k = self.count
        out = {'p': np.concatenate(self.p), 'n': np.concatenate(self.n), 'uv': np.concatenate(self.uv),
               'idx': np.concatenate(self.idx)}

        def fill(lst, w, default):
            parts = []
            for a, p in zip(lst, self.p):
                parts.append(a if a is not None else np.tile(np.asarray(default, np.float64), (len(p), 1)))
            return np.concatenate(parts).reshape(-1, w)
        if self.has_uv2:
            out['uv2'] = fill(self.uv2, 2, [0, 0])
        if self.has_col:
            out['col'] = fill(self.col, 4, [1, 1, 1, 1])
        if self.has_cus:
            out['cus'] = fill(self.cus, 4, [0, 0, 0, 0])
        if self.has_cus1:
            out['cus1'] = fill(self.cus1, 4, [0, 0, 0, 0])
        assert len(out['p']) == k
        return out

    def transformed(self, M=None, t=(0, 0, 0)):
        """Copy with positions p' = M p + t and normals rotated (M orthogonal-ish)."""
        o = self.arrays()
        r = MeshData()
        if o is None:
            return r
        M = np.eye(3) if M is None else np.asarray(M, np.float64)
        p = o['p'] @ M.T + np.asarray(t, np.float64)
        Minv_t = np.linalg.inv(M).T
        n = normalize(o['n'] @ Minv_t.T)
        cus1 = o.get('cus1')
        if cus1 is not None:
            cus1 = cus1.copy()
            cus1[:, :3] = normalize(cus1[:, :3] @ Minv_t.T)
        r.add(p, n, o['uv'], o['idx'], o.get('uv2'), o.get('col'), o.get('cus'), cus1)
        return r

    def bounds(self):
        o = self.arrays()
        if o is None:
            return np.zeros(3), np.zeros(3)
        return o['p'].min(0), o['p'].max(0)


def smooth_normals(p, idx):
    """Area-weighted vertex normals."""
    p = np.asarray(p, np.float64)
    a, b, c = p[idx[:, 0]], p[idx[:, 1]], p[idx[:, 2]]
    fn = np.cross(b - a, c - a)
    n = np.zeros_like(p)
    for k in range(3):
        np.add.at(n, idx[:, k], fn)
    return normalize(n)


def grid_indices(rows, cols, wrap=False):
    """Indices for a (rows x cols) vertex grid; each row is a ring of `cols` vertices.
    wrap: the last column connects to the first. Triangles face outward when rings go
    counter-clockwise seen from the spine's end (see tube.py)."""
    idx = []
    cc = cols if wrap else cols - 1
    for r in range(rows - 1):
        for c in range(cc):
            c2 = (c + 1) % cols
            a = r * cols + c
            b = r * cols + c2
            d = (r + 1) * cols + c
            e = (r + 1) * cols + c2
            idx.append((a, b, e))
            idx.append((a, e, d))
    return np.array(idx, np.int64).reshape(-1, 3)


def box(sx, sy, sz, center=(0, 0, 0), uv_scale=1.0):
    """Axis-aligned box with per-face normals and world-scaled UVs (metres * uv_scale)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    cx, cy, cz = center
    faces = [
        ((1, 0, 0), (0, 0, -1), (0, 1, 0), hx, sz, sy),
        ((-1, 0, 0), (0, 0, 1), (0, 1, 0), hx, sz, sy),
        ((0, 1, 0), (1, 0, 0), (0, 0, -1), hy, sx, sz),
        ((0, -1, 0), (1, 0, 0), (0, 0, 1), hy, sx, sz),
        ((0, 0, 1), (1, 0, 0), (0, 1, 0), hz, sx, sy),
        ((0, 0, -1), (-1, 0, 0), (0, 1, 0), hz, sx, sy),
    ]
    md = MeshData()
    for n, u, v, d, w, h in faces:
        n, u, v = np.array(n, float), np.array(u, float), np.array(v, float)
        c = np.array([cx, cy, cz]) + n * d
        pts = np.array([c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2,
                        c + u * w / 2 + v * h / 2, c - u * w / 2 + v * h / 2])
        uv = np.array([[0, h], [w, h], [w, 0], [0, 0]]) * uv_scale
        md.add(pts, np.tile(n, (4, 1)), uv, [(0, 1, 2), (0, 2, 3)])
    return md
