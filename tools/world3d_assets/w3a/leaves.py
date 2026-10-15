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


# ------------------------------------------------------------------------------------------------
# a tiny painter for the species tiles below (value canvas + coverage + depth)
class Canvas:
    def __init__(self, W, H):
        self.W, self.H = int(W), int(H)
        self.val = np.zeros((self.H, self.W))
        self.cov = np.zeros((self.H, self.W), bool)
        self.depth = np.full((self.H, self.W), -1e9)
        self.rgb = None

    def _rgb(self):
        if self.rgb is None:
            self.rgb = np.ones((self.H, self.W, 3))
        return self.rgb

    def put(self, x, y, v, d=0.0, col=None):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        if 0 <= xi < self.W and 0 <= yi < self.H and d >= self.depth[yi, xi] - 1e-9:
            self.val[yi, xi] = v
            self.cov[yi, xi] = True
            self.depth[yi, xi] = d
            if col is not None:
                self._rgb()[yi, xi] = col
            elif self.rgb is not None:
                self.rgb[yi, xi] = 1.0

    def line(self, x0, y0, x1, y1, v, d=0.0, col=None):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 1.5) + 1
        for t in np.linspace(0, 1, n):
            self.put(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, v if not callable(v) else v(t), d, col)

    def mask(self, m, v, d=0.0, col=None):
        """Paint a boolean mask (H, W) with value v (scalar or array) at depth d (front wins)."""
        ok = m & (d >= self.depth - 1e-9)
        vv = v if np.isscalar(v) else v[ok]
        self.val[ok] = vv
        self.cov[ok] = True
        self.depth[ok] = d
        if col is not None:
            self._rgb()[ok] = col
        elif self.rgb is not None:
            self.rgb[ok] = 1.0

    def sep(self, R, p=1.0, dirs=((-1, 0), (-1, -1), (-1, 1))):
        self.val[_sep_mask(self.cov, self.depth, R, p, dirs)] = SEP

    def finish(self):
        if self.rgb is None:
            return _finish(self.val, self.cov)
        out = np.zeros((self.H, self.W, 4), np.uint8)
        out[..., :3] = np.clip(np.round(self.rgb * self.val[..., None] * 255), 0, 255).astype(np.uint8)
        out[..., 3] = np.where(self.cov, 255, 0)
        return out


def sugi_spray(W, H, seed, spikes=None, droop=0.5):
    """Sugi (Japanese cedar) foliage as pixel art draws it: a drooping skirt of scale-needles, a
    rounded, sky-lit top edge and a jagged lower fringe of downward points; hanging streaks of
    needle bundles inside."""
    R = rng(seed)
    c = Canvas(W, H)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = W * 0.5
    top = H * 0.18
    # outline: an arch, wider at the bottom, with a fringe of points
    n = spikes or int(max(3, W / 4.5))
    xn = (xs + 0.5 - cx) / (W * 0.5)
    arch = top + (H * 0.18) * xn ** 2 * 1.4                      # rounded top edge
    ph = R.uniform(0, 2 * math.pi)
    fringe = H * (0.78 + 0.16 * np.abs(np.sin((xn * 0.5 + 0.5) * n * math.pi + ph * 0.1))) - H * 0.12 * xn ** 2
    fringe = fringe + R.normal(0, 0.6, size=W)[None, :]
    inside = (ys + 0.5 >= arch) & (ys + 0.5 <= fringe) & (np.abs(xn) <= 1.0)
    val = np.full((H, W), BODY)
    # hanging streaks: alternate columns light/mid in short runs
    streak = (R.uniform(size=(1, W)) < 0.45) & (((ys + (xs * 7) % 5) // 3) % 2 == 0)
    val = np.where(streak, BODY * 0.92 + TOP * 0.08, val)
    # sky-lit top rim (1-2 px under the arch) and a few light needle tips
    rim = inside & (ys + 0.5 < arch + 1.6 + R.uniform(size=(H, W)) * 0.8)
    val = np.where(rim, TOP, val)
    # underside: the row just above the fringe is shade
    under = inside & (ys + 0.5 > fringe - 1.5)
    val = np.where(under & (R.uniform(size=(H, W)) < 0.7), SEP, val)
    c.mask(inside, val, 0.0)
    return c.finish()


def pine_pad(W, H, seed, flat=0.42):
    """A red pine's branch plate: a flat cloud pad; the lit top edge bristles with short upright
    needle strokes, tufts show as small radiating bursts on the body, the underside is a flat dark
    band."""
    R = rng(seed)
    c = Canvas(W, H)
    ys, xs = np.mgrid[0:H, 0:W]
    cx, cy = W * 0.5, H * 0.58
    rx, ry = W * 0.47, H * flat
    # lumpy pad outline: a few overlapping ellipses along the pad
    m = np.zeros((H, W), bool)
    lumps = int(R.integers(3, 5))
    for k in range(lumps):
        lx = cx + (k - (lumps - 1) / 2) * rx * 0.55 + R.normal(0, 1)
        lr = rx * R.uniform(0.38, 0.55)
        lry = ry * R.uniform(0.75, 1.0)
        m |= ((xs + 0.5 - lx) / lr) ** 2 + ((ys + 0.5 - cy) / lry) ** 2 <= 1
    m &= ys + 0.5 <= cy + ry * 0.55                                   # flat underside
    val = np.full((H, W), BODY)
    # bursts on the body
    for b in range(int(W * H / 26)):
        bx, by = R.uniform(0, W), R.uniform(0, H)
        if not m[int(by), int(bx)]:
            continue
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.55 + R.normal(0, 0.15)
            for t in (1, 2):
                x, y = int(bx + math.cos(a) * t), int(by + math.sin(a) * t)
                if 0 <= x < W and 0 <= y < H and m[y, x]:
                    val[y, x] = TOP if t == 2 else BODY
    # dark underside band
    under = m & ~np.roll(m, -1, 0) | m & ~np.roll(m, -2, 0)
    val = np.where(under, SEP, val)
    c.mask(m, val, 0.0)
    # bristles on the top edge
    topedge = m & ~np.roll(m, 1, 0)
    for y, x in np.argwhere(topedge):
        if R.uniform() < 0.55:
            L = int(R.integers(1, 3))
            dx = int(R.integers(-1, 2))
            for t in range(1, L + 1):
                c.put(x + dx * (t > 1) + 0.5, y - t + 0.5, TOP, 1.0)
    return c.finish()


STAR = [  # palmate leaf stamps (x = leaf, o = light lobe)
    ["..o..", "o.x.o", ".xxx.", "xxxxx", "..x.."],
    [".o.o.", "oxxxo", ".xxx.", "..x.."],
    ["..o.", ".oxo", "xxx.", ".x.."],
    ["o...o", ".xox.", ".xxx.", "xxxxx", ".x.x."],
]


def star_leaves(W, H, seed, n=None, airy=0.42, droop=0.2):
    """Maple: small palmate leaves stamped one by one, airy (gaps between them), the upper lobes
    light; nearer leaves overlap farther ones."""
    R = rng(seed)
    c = Canvas(W, H)
    n = n or int(airy * W * H / 11.0)
    cx, cy = W * 0.5, H * 0.5
    items = []
    for i in range(n):
        a = R.uniform(0, 2 * math.pi)
        r = math.sqrt(R.uniform()) * 0.45
        items.append((1 - r + R.normal(0, 0.2), cx + math.cos(a) * r * W, cy + math.sin(a) * r * H * 0.9 + droop * r * H * 0.25))
    items.sort(key=lambda q: q[0])
    for d, px, py in items:
        st = STAR[R.integers(0, len(STAR))]
        flip = R.uniform() < 0.5
        h = len(st)
        w = len(st[0])
        for yy in range(h):
            for xx in range(w):
                ch = st[yy][w - 1 - xx if flip else xx]
                if ch == '.':
                    continue
                c.put(px - w / 2 + xx, py - h / 2 + yy, TOP if ch == 'o' else (BODY if yy < h - 1 else BODY * 0.92), d)
    c.sep(R, 0.35)
    return c.finish()


def broad_leaves(W, H, seed, n=None, size=(4.0, 6.0), wid=(2.4, 3.2), gloss=0.35, droop=0.3):
    """Persimmon / camellia: larger ovate leaves overlapping, glossy glints on some."""
    R = rng(seed)
    c = Canvas(W, H)
    n = n or int(W * H / 14.0)
    cx, cy = W * 0.5, H * 0.5
    items = []
    for i in range(n):
        a = R.uniform(0, 2 * math.pi)
        r = math.sqrt(R.uniform()) * 0.42
        px, py = cx + math.cos(a) * r * W, cy + math.sin(a) * r * H
        oa = math.atan2(py - cy, px - cx) + R.normal(0, 0.5) + droop
        items.append((1 - r + R.normal(0, 0.2), px, py, oa))
    items.sort(key=lambda q: q[0])
    for d, px, py, oa in items:
        L = R.uniform(*size)
        m, uu = _leaf_mask(H, W, px, py, oa, L, R.uniform(*wid))
        v = np.where(uu > 0.3, TOP, BODY)
        c.mask(m, v, d)
        if R.uniform() < gloss:
            gx, gy = int(np.clip(px, 0, W - 1)), int(np.clip(py - 0.5, 0, H - 1))
            if m[gy, gx]:
                c.val[gy, gx] = GLINT
    c.sep(R, 0.75)
    return c.finish()


def bamboo_spray(W, H, seed, n_fans=None):
    """Bamboo: fans of 3-6 long narrow leaves hanging from twig points (fingers of a drooping hand)."""
    R = rng(seed)
    c = Canvas(W, H)
    nf = n_fans or max(2, int(W * H / 140))
    for f in range(nf):
        bx, by = W * R.uniform(0.2, 0.8), H * R.uniform(0.1, 0.4)
        base_a = math.pi / 2 + R.normal(0, 0.45)                     # hanging down
        k = int(R.integers(3, 6))
        for j in range(k):
            a = base_a + (j - (k - 1) / 2) * 0.38 + R.normal(0, 0.08)
            L = R.uniform(6.0, 9.0)
            m, uu = _leaf_mask(H, W, bx + math.cos(a) * L * 0.5, by + math.sin(a) * L * 0.5, a, L, 1.7)
            v = np.where(uu < -0.25, TOP, BODY)
            c.mask(m, v, f + j * 0.01)
    c.sep(R, 0.5)
    return c.finish()


def flower_head(W, seed, colours):
    """Hydrangea mophead: a round head of four-petal florets in three tones (RGB tile; the card
    tint stays white), the upper florets lightest, small dark gaps between them."""
    R = rng(seed)
    H = W
    c = Canvas(W, H)
    cx, cy = W / 2, H / 2
    r = W * 0.46
    pts = []
    for i in range(int(W * H / 6)):
        a = R.uniform(0, 2 * math.pi)
        rr = math.sqrt(R.uniform()) * r
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.92, rr / r))
    pts.sort(key=lambda p: p[1])
    for px, py, rr in pts:
        top = py < cy - r * 0.2
        col = np.array(colours[2] if top else (colours[1] if rr < 0.7 else colours[0])) / 255.0
        for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
            c.put(px + dx, py + dy, 1.0 if (dx, dy) == (0, 0) else 0.92, py * 0.01 + R.uniform(0, 0.005), col)
    c.sep(R, 0.35)
    return c.finish()


def fruit(W, seed, colours):
    """A round fruit (persimmon), shaded as a ball lit from the sky, with a calyx."""
    R = rng(seed)
    c = Canvas(W, W)
    ys, xs = np.mgrid[0:W, 0:W]
    cx, cy = W / 2, W / 2 + 0.3
    r = W * 0.42
    dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
    m = dx * dx + dy * dy * 1.1 <= r * r
    v = np.ones((W, W))
    col = np.zeros((W, W, 3))
    lit = (dx * -0.5 + dy * -0.8) / r
    tone = np.where(lit > 0.35, 2, np.where(lit > -0.35, 1, 0))
    for i in range(3):
        col[tone == i] = np.array(colours[i]) / 255.0
    c.mask(m, 1.0, 0.0, col=np.array([1.0, 1.0, 1.0]))
    c.rgb[m] = col[m]
    # calyx
    for px in (cx - 1, cx, cx + 1):
        c.put(px, cy - r + 0.2, 1.0, 1.0, np.array([0.30, 0.34, 0.18]))
    return c.finish()


def fern_clump(W, H, seed, n_fronds=None):
    """A fern as a little plant sprite: fronds fanning up out of the crown and arching over,
    outer ones drooping more; pinnae as short strokes on both sides of each rachis."""
    R = rng(seed)
    c = Canvas(W, H)
    base = (W * 0.5, H - 1.0)
    n = n_fronds or int(R.integers(7, 11))
    angs = np.linspace(-math.pi + 0.35, -0.35, n) + R.normal(0, 0.08, n)
    order = np.argsort(np.abs(angs + math.pi / 2))[::-1]               # outer fronds behind
    for rank, f in enumerate(order):
        a = angs[f]
        outer = abs(a + math.pi / 2) / (math.pi / 2)
        L = R.uniform(H * 0.6, H * 0.95) * (1.05 - 0.25 * outer)
        steps = max(4, int(L / 1.1))
        x, y = base
        d = rank
        sgn = 1 if math.cos(a) >= 0 else -1
        for s_ in range(steps):
            t = s_ / steps
            a += sgn * (0.02 + 0.10 * t * t) * (0.6 + outer)                # arch over
            x += math.cos(a) * 1.1
            y += math.sin(a) * 1.1
            c.put(x, y, BODY * 0.95, d)
            if s_ >= 1:
                pl = (1 - t) * 2.6 + 0.9
                for sd in (-1, 1):
                    pa = a + sd * 1.35
                    up = math.sin(pa) < 0
                    c.line(x, y, x + math.cos(pa) * pl, y + math.sin(pa) * pl, TOP if up else BODY, d - 0.01)
    c.sep(R, 0.4)
    return c.finish()


def grass_clump(W, H, seed, n=None, arch=0.9, plume=False, plume_col=None, thick=1):
    """Susuki: long arching blades from a tuft; optional drooping plumes on tall stalks (RGB
    plumes when plume_col is given)."""
    R = rng(seed)
    c = Canvas(W, H)
    base = (W * 0.5, H * 0.98)
    n = n or int(R.integers(12, 18))
    for b in range(n):
        side = R.normal(0, 0.45)
        a = -math.pi / 2 + side * 0.9
        L = R.uniform(H * 0.45, H * 0.8)
        steps = int(L)
        x, y = base[0] + R.normal(0, W * 0.04), base[1]
        d = R.uniform(0, 1)
        for s in range(steps):
            t = s / steps
            a += arch * 0.03 * (1 if side >= 0 else -1) * t
            x += math.cos(a)
            y += math.sin(a)
            v = TOP if (t > 0.2 and R.uniform() < 0.35) else BODY
            c.put(x, y, v, d)
            if thick > 1 and t < 0.8:
                c.put(x + (1 if side >= 0 else -1), y, BODY, d - 0.001)
    if plume:
        for p in range(int(R.integers(3, 6))):
            a = -math.pi / 2 + R.normal(0, 0.25)
            L = R.uniform(H * 0.75, H * 0.95)
            x, y = base[0] + R.normal(0, W * 0.05), base[1]
            for s in range(int(L)):
                x += math.cos(a)
                y += math.sin(a)
                c.put(x, y, BODY, 5.0, np.array([0.55, 0.57, 0.36]))
            # the plume: a drooping fan of fine silky lines
            side = 1 if R.uniform() < 0.5 else -1
            for k in range(6):
                fa = math.pi / 2 - side * (0.9 - k * 0.12) + R.normal(0, 0.1)
                fl = R.uniform(3, 5.5)
                col = np.array(plume_col[0 if k % 3 == 0 else 1]) / 255.0
                c.line(x, y, x + math.cos(fa) * fl, y + math.sin(fa) * fl, 1.0, 6.0, col)
    c.sep(R, 0.3)
    return c.finish()


def pine_tufts(W, H, seed, n=None):
    """Red pine needles: a few tufts, each a fan of short straight needles radiating up and out from
    a dark base, tips lighter; gaps between the tufts (not a continuous bar)."""
    R = rng(seed)
    c = Canvas(W, H)
    n = n or int(R.integers(2, 5))
    xs = np.sort(R.uniform(W * 0.18, W * 0.82, n))
    for i, x0 in enumerate(xs):
        y0 = H - 1.5 - R.uniform(0, H * 0.25)
        k = int(R.integers(10, 16))
        spread = R.uniform(1.1, 1.5)
        for j in range(k):
            a = -math.pi / 2 + (j / (k - 1) - 0.5) * 2 * spread + R.normal(0, 0.06)
            L = R.uniform(3.0, 5.5) * (1.0 - 0.25 * abs(j / (k - 1) - 0.5))
            x, y = x0 + R.normal(0, 0.4), y0
            steps = int(L * 1.5) + 1
            for s in range(steps):
                t = s / steps
                px, py = x + math.cos(a) * L * t, y + math.sin(a) * L * t
                v = TOP if t > 0.6 and math.sin(a) < -0.3 else (BODY if t > 0.2 else SEP)
                c.put(px, py, v, i + t * 0.1)
    return c.finish()


def calm(tile, k_l=0.74, k_c=0.9):
    """Compress a tile's value range about its mean (CIELAB L*) and a little of its chroma: vegetation
    stays under the characters and interactables in contrast (reading order, CLAUDE.md §3)."""
    from skimage import color
    t = tile.copy()
    a = t[..., 3] > 0
    if a.sum() < 2:
        return t
    lab = color.rgb2lab(t[..., :3].astype(np.float64) / 255.0)
    Lm = float(lab[..., 0][a].mean())
    lab[..., 0] = np.where(a, Lm + (lab[..., 0] - Lm) * k_l, lab[..., 0])
    lab[..., 1:] = np.where(a[..., None], lab[..., 1:] * k_c, lab[..., 1:])
    rgb = np.clip(color.lab2rgb(lab), 0, 1)
    t[..., :3] = np.where(a[..., None], np.round(rgb * 255), t[..., :3]).astype(np.uint8)
    return t
