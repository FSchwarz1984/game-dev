"""Wood: skeletons of swept tubes (trunk, limbs, branches, roots) for the renderer's toon_solid
material (docs/knowledge/21 section 2.1):
  COLOR.rgb  albedo tint (sRGB): multiplies the tiling bark texture; carries the big variations
             (earth near the ground, damp green where moss grows, paler high limbs)
  COLOR.a    baked ambient occlusion (crotches, undersides, between the buttresses)
  UV         bark texture coordinates at 20 texels per metre of true surface length
             (u around the ring, v along it; the texture tiles, albedo_mode 1)
  UV2        (pattern 7 = moss on what faces up, amount) per vertex
The ring seam sits on the side facing away from the camera (as the leaned view sees it).
"""
from __future__ import annotations

import math

import numpy as np

from .core import LEAN_K, PITCH, TEXEL_PER_M, normalize, rng
from .mesh import MeshData
from .tube import Spine, tube


def view_back_upright():
    """Direction from the scene toward the camera, for upright (leaned) objects in object space:
    the renderer shears z by -k*y, so these objects are seen along (0, sin p, k sin p + cos p)."""
    p = math.radians(PITCH)
    return normalize(np.array([0.0, math.sin(p), LEAN_K * math.sin(p) + math.cos(p)]))


class Limb:
    def __init__(self, name, pts, radii, kind='limb', n_around=None, rfun=None, step=None, cap_end=True,
                 parent=None, tags=None, yscale=None, moss=0.0, tint=(1.0, 1.0, 1.0), step_fn=None):
        self.name = name
        self.pts = np.asarray(pts, np.float64)
        self.radii = np.asarray(radii, np.float64)
        self.kind = kind            # trunk | limb | branch | twig | root
        self.n_around = n_around
        self.rfun = rfun
        self.step = step
        self.cap_end = cap_end
        self.parent = parent
        self.tags = tags or {}
        self.yscale = yscale
        self.moss = moss            # moss amount on upward faces (UV2.y)
        self.tint = np.asarray(tint, np.float64)
        self.step_fn = step_fn
        self.spine = None
        self.info = None
        self.md = None


def build_limb(L: Limb, seg_px=6.0, step_k=0.6, min_step=0.25, max_step=0.9):
    """Rings every step metres (scaled with the radius), n_around so a segment spans ~seg_px."""
    rmax = float(np.max(L.radii))
    step = L.step or float(np.clip(rmax * step_k, min_step, max_step))
    L.spine = Spine(L.pts, L.radii, step=step, step_fn=L.step_fn)
    n = L.n_around or int(np.clip(round(2 * math.pi * rmax * TEXEL_PER_M / seg_px), 5, 40))
    md, info = tube(L.spine, n_around=n, rfun=L.rfun, cap_end=L.cap_end, yscale=L.yscale, ref=-view_back_upright(),
                    u_mode='front')
    L.md = md
    L.info = info
    return L


def wood_mesh(limbs, tex_size=256, colour_fn=None, ao_fn=None, moss_fn=None):
    """All limbs as one surface for toon_solid (albedo_mode 1). colour_fn(P, N, limb) -> (n, 3) tint,
    ao_fn(P, N, limb) -> (n,) AO, moss_fn(P, N, limb) -> (n,) moss amount."""
    out = MeshData()
    for L in limbs:
        a = L.md.arrays()
        P, N = a['p'], a['n']
        uv = a['uv'] * TEXEL_PER_M / tex_size
        col = np.tile(L.tint, (len(P), 1))
        if colour_fn is not None:
            col = col * colour_fn(P, N, L)
        ao = np.ones(len(P)) if ao_fn is None else ao_fn(P, N, L)
        moss = np.full(len(P), L.moss) if moss_fn is None else moss_fn(P, N, L)
        C = np.concatenate([np.clip(col, 0, 1), np.clip(ao, 0, 1)[:, None]], axis=1)
        uv2 = np.stack([np.full(len(P), 7.0), np.clip(moss, 0, 1)], axis=1)
        out.add(P, N, uv, a['idx'], uv2=uv2, col=C)
    return out


def offshoots(parent: Limb, R, n, frac_range=(0.45, 0.95), length=(2.0, 4.0), radius_k=(0.35, 0.55),
              up_bias=0.35, spread=0.9, name='b', kind='branch', bend=0.25, min_r=0.05, side_bias=None,
              moss=0.0, segs=4):
    """Branches leaving a parent limb along its outer part. Returns a list of Limb."""
    sp = parent.spine
    out = []
    for i in range(n):
        f = R.uniform(*frac_range)
        p0, t0, r0 = sp.point_at(f)
        side = normalize(np.cross(t0, [0, 1, 0]) + 1e-6)
        sgn = side_bias if side_bias is not None else (1 if R.uniform() < 0.5 else -1)
        d = normalize(t0 * (1 - spread * 0.5) + side * sgn * spread + np.array([0, up_bias, 0]) + R.normal(0, 0.25, 3))
        Ln = R.uniform(*length)
        r_start = max(min_r * 1.5, r0 * R.uniform(*radius_k))
        pts = [p0 - d * r0 * 0.3]
        pos = p0.copy()
        dd = d.copy()
        for j in range(1, segs + 1):
            dd = normalize(dd + R.normal(0, bend, 3) + np.array([0, 0.06, 0]))
            pos = pos + dd * Ln / segs
            pts.append(pos.copy())
        radii = np.linspace(r_start, max(min_r, r_start * 0.3), len(pts))
        out.append(Limb(f'{name}{i}', pts, radii, kind=kind, parent=parent, moss=moss))
    return out


# ------------------------------------------------------------------------------------------------
# a tiling bark texture, painted at one texel per native pixel
def bark_texture(seed, size=256, spacing=(3, 6), ridge=('#5d564b', '#6c6557', '#7a7262'), lip='#8a8270',
                 fissure='#3a332e', deep='#2b2623', lichen=('#8f9178', '#a3a58a'), lichen_p=0.002,
                 moss=('#4c5a33', '#5a6a3a'), moss_p=0.0015, break_p=0.035, wave=(2.5, 1.2), merge_p=0.25):
    """Camphor-like bark: one-texel dark fissures running up the trunk, wavy, now and then
    merging and splitting, with ridges between them (2-3 flat tones per ridge, a lighter lip on one
    edge), short dark breaks across ridges, rare lichen and moss specks. Tiles both ways (the waves
    are periodic in y, the fissure set wraps in x). Returns (size, size, 3) uint8."""
    from .core import hex_rgb
    R = rng(seed)
    S = size
    C = lambda h: np.array(hex_rgb(h), np.float64)
    # fissure base positions across the tile
    xs0 = []
    x = 0.0
    while x < S - spacing[0]:
        xs0.append(x)
        x += R.uniform(*spacing)
    xs0 = np.array(xs0)
    n = len(xs0)
    y = np.arange(S)
    # each fissure wanders: two periodic waves (integer cycles per tile so it tiles in y)
    paths = np.zeros((n, S))
    for i in range(n):
        f1, f2 = int(R.integers(1, 4)), int(R.integers(4, 9))
        p1, p2 = R.uniform(0, 2 * math.pi, 2)
        paths[i] = xs0[i] + wave[0] * np.sin(2 * math.pi * f1 * y / S + p1) + wave[1] * np.sin(2 * math.pi * f2 * y / S + p2)
    # some fissures are interrupted: they fade out over a stretch (the ridges on both sides merge)
    alive = np.ones((n, S), bool)
    for i in range(n):
        if R.uniform() < merge_p:
            start = int(R.integers(0, S))
            length = int(R.integers(10, 40))
            idx = (start + np.arange(length)) % S
            alive[i, idx] = False
    img = np.zeros((S, S, 3))
    tone = np.zeros((S, S), int)
    ridge_c = [C(h) for h in ridge]
    for yy in range(S):
        px = np.round(paths[:, yy]).astype(int) % S
        order = np.argsort(px)
        px_sorted = px[order]
        al = alive[order, yy]
        row = np.zeros(S, int)            # ridge id per x
        # ridge id: number of alive fissures to the left (wrapping)
        cuts = px_sorted[al]
        if len(cuts) == 0:
            continue
        rid = np.searchsorted(cuts, np.arange(S), side='right') % len(cuts)
        img_row = np.zeros((S, 3))
        for xx in range(S):
            r = rid[xx]
            seg_len = 9 + (r * 37) % 15
            seg = (yy + (r * 53) % seg_len) // seg_len
            h = (r * 2654435761 + seg * 40503 + seed * 97) % 1000 / 1000.0
            img_row[xx] = ridge_c[0] if h < 0.3 else (ridge_c[1] if h < 0.8 else ridge_c[2])
        img[yy] = img_row
        # fissures and lips
        for xx in cuts:
            img[yy, xx % S] = C(fissure) if R.uniform() > 0.3 else C(deep)
            img[yy, (xx + 1) % S] = C(lip) if R.uniform() < 0.75 else img[yy, (xx + 1) % S]
    # breaks: short dark dashes across a ridge
    k = int(break_p * S * S / 6)
    for _ in range(k):
        bx = int(R.integers(0, S))
        by = int(R.integers(0, S))
        L = int(R.integers(2, 5))
        for d in range(L):
            img[by, (bx + d) % S] = C(fissure)
        img[(by + 1) % S, bx % S] = img[(by + 1) % S, bx % S] * 0.92
    for cols, p in ((lichen, lichen_p), (moss, moss_p)):
        for colhex in cols:
            m = int(p * S * S)
            px = R.integers(0, S, size=m)
            py = R.integers(0, S, size=m)
            for a_, b_ in zip(px, py):
                img[b_, a_] = C(colhex)
                img[b_, (a_ + 1) % S] = C(colhex)
    return np.clip(np.round(img), 0, 255).astype(np.uint8)
