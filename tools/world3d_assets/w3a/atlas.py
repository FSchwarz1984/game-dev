"""Unique texture atlases painted in UV space.

Every textured part of an asset is an island: triangles with UVs in texels (one texel = one native
pixel on screen, see tube.py and core.TEXEL_PER_M). Islands are shelf-packed into one atlas; then
the triangles are rasterised in UV space into a G-buffer (world position, normal, island id and any
per-vertex attributes) so painters can decide each texel from what it is in 3D (top of a limb gets
moss, a crevice gets dark, the side near the ground gets earth). Finally the painted atlas is
dilated so nearest sampling at island borders never reads an empty texel.
"""
from __future__ import annotations

import math

import numpy as np


class Island:
    def __init__(self, name, uv_tex, p, n, idx, attrs=None, pad=2):
        """uv_tex: (k, 2) texel coordinates (any origin); p, n: (k, 3); idx: (t, 3).
        attrs: dict of (k, c) arrays interpolated into the G-buffer."""
        self.name = name
        uv = np.asarray(uv_tex, np.float64)
        self.min = np.floor(uv.min(0)) - pad
        self.uv = uv - self.min                      # local texel coords, >= pad
        self.size = np.ceil(self.uv.max(0) + pad).astype(int)
        self.p = np.asarray(p, np.float64)
        self.n = np.asarray(n, np.float64)
        self.idx = np.asarray(idx, np.int64)
        self.attrs = attrs or {}
        self.offset = np.zeros(2, int)


def pack(islands, max_w=2048, gap=0):
    """Shelf packing, tallest first. Returns (W, H) with W, H multiples of 4."""
    order = sorted(range(len(islands)), key=lambda i: (-islands[i].size[1], -islands[i].size[0]))
    total = sum(int(i.size[0] * i.size[1]) for i in islands)
    W = max(int(max(i.size[0] for i in islands)), int(math.ceil(math.sqrt(total * 1.15))))
    W = min(max_w, int(math.ceil(W / 4) * 4))
    x = y = shelf_h = 0
    for i in order:
        isl = islands[i]
        w, h = int(isl.size[0]), int(isl.size[1])
        if x + w > W:
            x = 0
            y += shelf_h + gap
            shelf_h = 0
        isl.offset = np.array([x, y])
        x += w + gap
        shelf_h = max(shelf_h, h)
    H = int(math.ceil((y + shelf_h) / 4) * 4)
    return W, H


def final_uv(isl, W, H):
    """Normalised UVs of an island's vertices in the packed atlas."""
    return (isl.uv + isl.offset[None, :]) / np.array([W, H], np.float64)


def rasterize(islands, W, H, extra=()):
    """UV-space G-buffer. Returns dict with 'mask' (H, W) bool, 'id' (H, W) int (-1 empty),
    'pos', 'nrm' (H, W, 3), 'bary_tri' (H, W) triangle index within island, and every attribute
    named in `extra` that the islands carry."""
    G = {'mask': np.zeros((H, W), bool), 'id': np.full((H, W), -1, np.int32),
         'pos': np.zeros((H, W, 3), np.float64), 'nrm': np.zeros((H, W, 3), np.float64)}
    chans = {}
    for name in extra:
        c = None
        for isl in islands:
            if name in isl.attrs:
                c = np.asarray(isl.attrs[name]).reshape(len(isl.p), -1).shape[1]
                break
        if c is not None:
            chans[name] = c
            G[name] = np.zeros((H, W, c), np.float64)
    for ii, isl in enumerate(islands):
        uv = isl.uv + isl.offset[None, :]
        tri = isl.idx
        A, B, C = uv[tri[:, 0]], uv[tri[:, 1]], uv[tri[:, 2]]
        lo = np.floor(np.minimum(np.minimum(A, B), C) - 0.5).astype(int)
        hi = np.ceil(np.maximum(np.maximum(A, B), C) + 0.5).astype(int)
        lo = np.clip(lo, 0, [W - 1, H - 1])
        hi = np.clip(hi, 0, [W, H])
        ext = hi - lo
        attr_arrays = {k: np.asarray(isl.attrs[k], np.float64).reshape(len(isl.p), -1) for k in chans if k in isl.attrs}
        # batch small triangles (bbox up to S x S), loop over the rest
        S = 8
        small = (ext[:, 0] <= S) & (ext[:, 1] <= S)
        for sel, size in ((np.nonzero(small)[0], S), (np.nonzero(~small)[0], None)):
            if len(sel) == 0:
                continue
            if size is not None:
                gx, gy = np.meshgrid(np.arange(size), np.arange(size))
                gx = gx.reshape(-1)
                gy = gy.reshape(-1)
                for chunk in np.array_split(sel, max(1, len(sel) // 4096)):
                    px = lo[chunk, 0][:, None] + gx[None, :]
                    py = lo[chunk, 1][:, None] + gy[None, :]
                    _fill(G, ii, isl, chunk, px, py, A, B, C, W, H, attr_arrays)
            else:
                for t in sel:
                    xs = np.arange(lo[t, 0], hi[t, 0])
                    ys = np.arange(lo[t, 1], hi[t, 1])
                    gx, gy = np.meshgrid(xs, ys)
                    _fill(G, ii, isl, np.array([t]), gx.reshape(1, -1), gy.reshape(1, -1), A, B, C, W, H, attr_arrays)
    return G


def _fill(G, ii, isl, tris, px, py, A, B, C, W, H, attr_arrays):
    cx = px + 0.5
    cy = py + 0.5
    a = A[tris]
    b = B[tris]
    c = C[tris]
    v0 = b - a
    v1 = c - a
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok_t = np.abs(den) > 1e-12
    den = np.where(ok_t, den, 1.0)
    wx = cx - a[:, 0:1]
    wy = cy - a[:, 1:2]
    l1 = (wx * v1[:, 1:2] - v1[:, 0:1] * wy) / den[:, None]
    l2 = (v0[:, 0:1] * wy - wx * v0[:, 1:2]) / den[:, None]
    l0 = 1 - l1 - l2
    eps = -1e-6
    inside = (l0 >= eps) & (l1 >= eps) & (l2 >= eps) & ok_t[:, None] & (px >= 0) & (py >= 0) & (px < W) & (py < H)
    if not inside.any():
        return
    ti, si = np.nonzero(inside)
    X = px[ti, si]
    Y = py[ti, si]
    tri = isl.idx[tris[ti]]
    w0, w1, w2 = l0[ti, si][:, None], l1[ti, si][:, None], l2[ti, si][:, None]
    P = isl.p[tri[:, 0]] * w0 + isl.p[tri[:, 1]] * w1 + isl.p[tri[:, 2]] * w2
    Nn = isl.n[tri[:, 0]] * w0 + isl.n[tri[:, 1]] * w1 + isl.n[tri[:, 2]] * w2
    Nn = Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
    G['mask'][Y, X] = True
    G['id'][Y, X] = ii
    G['pos'][Y, X] = P
    G['nrm'][Y, X] = Nn
    for k, arr in attr_arrays.items():
        G[k][Y, X] = arr[tri[:, 0]] * w0 + arr[tri[:, 1]] * w1 + arr[tri[:, 2]] * w2


def dilate(img, mask, steps=3):
    """Grow painted texels into empty neighbours (nearest-sampling safety at island borders)."""
    img = img.copy()
    m = mask.copy()
    H, W = m.shape
    for _ in range(steps):
        grown = m.copy()
        acc = np.zeros_like(img, dtype=np.float64)
        cnt = np.zeros((H, W), np.float64)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sm = np.zeros_like(m)
            si = np.zeros_like(img)
            ys = slice(max(dy, 0), H + min(dy, 0))
            yd = slice(max(-dy, 0), H + min(-dy, 0))
            xs = slice(max(dx, 0), W + min(dx, 0))
            xd = slice(max(-dx, 0), W + min(-dx, 0))
            sm[yd, xd] = m[ys, xs]
            si[yd, xd] = img[ys, xs]
            take = sm & ~m
            acc[take] += si[take]
            cnt[take] += 1
            grown |= sm
        new = grown & ~m
        img[new] = (acc[new] / cnt[new][:, None]).astype(img.dtype) if img.ndim == 3 else (acc[new] / cnt[new]).astype(img.dtype)
        m = grown
    return img, m
