"""Leaf tiles for foliage cards (docs/knowledge/21 section 2.2), painted leaf by leaf, one texel per
native pixel.

Tiles are albedo VALUES (grey, sRGB): the card's COLOR.rgb tints them, the renderer lights them by
the card normal. Three or four flat tones per tile, as pixel art:
  SEP    the dark gap where a clump overlaps the one behind it
  BODY   the clump body
  TOP    the sky-lit upper rim of a clump, and leaf tips sticking out (light comes from the sky
         above at every hour, so this is not a baked sun direction)
  GLINT  a rare one-texel gleam on glossy leaves (camphor, camellia, persimmon)
Alpha is coverage (0 or 255).
"""
from __future__ import annotations

import math

import numpy as np

from .core import rng

SEP, BODY, TOP, GLINT = 0.60, 0.80, 0.93, 1.0


def _leaf_mask(H, W, cx, cy, ang, L, Wd):
    """Pixels of one pointed leaf (lens shape) centred at (cx, cy), pointing along ang."""
    ys, xs = np.mgrid[0:H, 0:W]
    dx = xs + 0.5 - cx
    dy = ys + 0.5 - cy
    ca, sa = math.cos(ang), math.sin(ang)
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    hu = L / 2
    hv = Wd / 2
    t = np.clip(u / hu, -1.2, 1.2)
    width = hv * np.sqrt(np.clip(1 - t * t, 0, 1)) * (1 + 0.15 * (-t))
    m = (np.abs(u) <= hu) & (np.abs(v) <= width + 0.18)
    return m, u / max(hu, 1e-6)


def _finish(val, cov):
    out = np.zeros(val.shape + (4,), np.uint8)
    g = np.clip(np.round(val * 255), 0, 255).astype(np.uint8)
    out[..., 0] = g
    out[..., 1] = g
    out[..., 2] = g
    out[..., 3] = np.where(cov, 255, 0)
    out[~cov, :3] = 0
    return out


def _sep_mask(cov, depth, R, p, dirs=((-1, 0), (-1, -1), (-1, 1))):
    H, W = cov.shape
    sep = np.zeros_like(cov)
    for oy, ox in dirs:
        nb = np.full_like(depth, -1e9)
        ys_ = slice(max(-oy, 0), H - max(oy, 0))
        xs_ = slice(max(-ox, 0), W - max(ox, 0))
        yd = slice(max(oy, 0), H - max(-oy, 0))
        xd = slice(max(ox, 0), W - max(-ox, 0))
        nb[ys_, xs_] = depth[yd, xd]
        sep |= cov & (nb > depth + 0.15)
    return sep & (R.uniform(size=sep.shape) < p)


def clumps(W, seed, H=None, n=None, r=(1.8, 3.4), shape=0.42, aspect=1.0, gloss=0.25, scallop=(5, 8),
           tips=6, tip_len=(1.8, 3.0), lobes=4, ragged=0.25, droop=0.15, sep_p=0.75, top_p=0.85, fill=2.0):
    """A cluster of overlapping scalloped leaf clumps (2-4 texel radius) with leaf tips sticking out.
    Nearer clumps (towards the tile centre) are drawn over farther ones; where a clump overlaps one
    behind it, a one-texel dark gap; the upper rim of each clump is the light tone."""
    R = rng(seed)
    W = int(W)
    H = int(H or W)
    val = np.zeros((H, W))
    cov = np.zeros((H, W), bool)
    depth = np.full((H, W), -1e9)
    ys, xs = np.mgrid[0:H, 0:W]
    cx, cy = W * 0.5, H * 0.5
    rad = shape * min(W, H)
    rm = (r[0] + r[1]) / 2
    if n is None:
        n = max(3, int(fill * math.pi * rad * rad * aspect / (math.pi * rm * rm)))
    phase = R.uniform(0, 2 * math.pi)
    cl = []
    for k in range(n):
        a = R.uniform(0, 2 * math.pi)
        rr = math.sqrt(R.uniform(0, 1))
        edge = 1 + ragged * math.sin(lobes * a + phase) + ragged * 0.5 * R.normal(0, 0.6)
        px = cx + math.cos(a) * rr * rad * edge
        py = cy + math.sin(a) * rr * rad * edge * aspect + droop * rr * rad * 0.3
        rc = R.uniform(*r) * (1.0 - 0.2 * rr)
        cl.append((1 - rr + R.normal(0, 0.3), px, py, rc))
    cl.sort(key=lambda t: t[0])
    for d, px, py, rc in cl:
        dx = xs + 0.5 - px
        dy = ys + 0.5 - py
        dist = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx)
        ns = R.integers(scallop[0], scallop[1] + 1)
        ph = R.uniform(0, 2 * math.pi)
        edge = rc * (1 + 0.24 * np.maximum(0, np.sin(ns * ang + ph)) - 0.08)
        m = dist <= edge
        if not m.any():
            continue
        v = np.full((H, W), BODY)
        top = (dist > edge - 1.2) & (dy < -0.25 * edge)
        v = np.where(top & (R.uniform(size=(H, W)) < top_p), TOP, v)
        val[m] = v[m]
        cov |= m
        depth[m] = d
        if R.uniform() < gloss:
            gx = int(np.clip(px + R.normal(0, 0.6), 0, W - 1))
            gy = int(np.clip(py - rc * 0.45 + R.normal(0, 0.5), 0, H - 1))
            if m[gy, gx]:
                val[gy, gx] = GLINT
    val[_sep_mask(cov, depth, R, sep_p)] = SEP
    if tips:
        edge_pts = np.argwhere(cov & (~np.roll(cov, 1, 0) | ~np.roll(cov, -1, 0) | ~np.roll(cov, 1, 1) | ~np.roll(cov, -1, 1)))
        for t in range(tips):
            if len(edge_pts) == 0:
                break
            ey, ex = edge_pts[R.integers(0, len(edge_pts))]
            oa = math.atan2(ey + 0.5 - cy, ex + 0.5 - cx) + R.normal(0, 0.35)
            L = R.uniform(*tip_len)
            m, uu = _leaf_mask(H, W, ex + 0.5 + math.cos(oa) * L * 0.45, ey + 0.5 + math.sin(oa) * L * 0.45, oa, L, 1.4)
            add = m & ~cov
            val[add] = np.where(uu[add] > 0.2, TOP, BODY)
            cov |= add
    return _finish(val, cov)


def spray(W, seed, direction, H=None, n_twigs=3, leaf_len=(2.4, 4.0), leaf_w=(1.3, 2.0), gloss=0.15, reach=0.46,
          droop=0.25):
    """Leafy twigs reaching out from the tile centre toward `direction` (radians on screen,
    0 = right, pi/2 = down in texture space). For the lit rim and the lower edge of a crown."""
    R = rng(seed)
    W = int(W)
    H = int(H or W)
    val = np.zeros((H, W))
    cov = np.zeros((H, W), bool)
    depth = np.full((H, W), -1e9)
    c = (W * 0.5, H * 0.5)
    leaves = []
    for t in range(n_twigs):
        a = direction + R.normal(0, 0.45)
        length = min(W, H) * reach * R.uniform(0.7, 1.05)
        x, y = c[0] + R.normal(0, W * 0.05), c[1] + R.normal(0, H * 0.05)
        steps = max(2, int(length / 1.6))
        for k in range(steps):
            a += R.normal(0, 0.12) + droop * 0.06 * math.cos(a)
            x += math.cos(a) * 1.6
            y += math.sin(a) * 1.6
            if k < 1:
                continue
            for side in (-1, 1):
                if R.uniform() < 0.85:
                    la = a + side * R.uniform(0.6, 1.1) + 0.25 * droop
                    L = R.uniform(*leaf_len) * (1 - 0.35 * k / steps)
                    Wd = R.uniform(*leaf_w)
                    leaves.append((k / steps + R.normal(0, 0.2), x + math.cos(la) * L * 0.5, y + math.sin(la) * L * 0.5, la, L, Wd))
        leaves.append((1.2, x + math.cos(a) * 1.5, y + math.sin(a) * 1.5, a, R.uniform(*leaf_len), R.uniform(*leaf_w)))
    leaves.sort(key=lambda q: -q[0])
    for d, px, py, ang, L, Wd in leaves:
        m, uu = _leaf_mask(H, W, px, py, ang, L, Wd)
        if not m.any():
            continue
        v = np.where(uu > 0.35, TOP, BODY)
        val[m] = v[m]
        cov |= m
        depth[m] = -d
        if R.uniform() < gloss:
            gx, gy = int(np.clip(px, 0, W - 1)), int(np.clip(py, 0, H - 1))
            if m[gy, gx]:
                val[gy, gx] = GLINT
    val[_sep_mask(cov, depth, R, 1.0, ((-1, 0), (-1, -1)))] = SEP
    return _finish(val, cov)


def trim(t, pad=0):
    a = t[..., 3] > 0
    if not a.any():
        return t
    yy, xx = np.nonzero(a)
    return t[max(0, yy.min() - pad):yy.max() + 1 + pad, max(0, xx.min() - pad):xx.max() + 1 + pad]


def pack_tiles(tiles, width=128, max_h=128):
    """Shelf-pack tiles (list of (h, w, 4)) with 1-texel gaps. Returns (atlas, rects) with
    rects[i] = (x, y, w, h) in texels."""
    order = sorted(range(len(tiles)), key=lambda i: (-tiles[i].shape[0], -tiles[i].shape[1]))
    x = y = sh = 0
    rects = [None] * len(tiles)
    for i in order:
        h, w = tiles[i].shape[:2]
        if x + w > width:
            x = 0
            y += sh + 1
            sh = 0
        rects[i] = (x, y, w, h)
        x += w + 1
        sh = max(sh, h)
    Hh = y + sh
    if Hh > max_h:
        raise ValueError(f'leaf atlas overflow: {Hh} > {max_h} rows (contract 2.3: <= 128x128)')
    Hh = max(4, int(math.ceil(Hh / 4) * 4))
    atlas = np.zeros((Hh, width, 4), np.uint8)
    for i, t in enumerate(tiles):
        x, y, w, h = rects[i]
        atlas[y:y + h, x:x + w] = t
    return atlas, rects
