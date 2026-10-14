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
                 parent=None, tags=None, yscale=None, moss=0.0, tint=(1.0, 1.0, 1.0)):
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
        self.spine = None
        self.info = None
        self.md = None


def build_limb(L: Limb, seg_px=6.0, step_k=0.6, min_step=0.25, max_step=0.9):
    """Rings every step metres (scaled with the radius), n_around so a segment spans ~seg_px."""
    rmax = float(np.max(L.radii))
    step = L.step or float(np.clip(rmax * step_k, min_step, max_step))
    L.spine = Spine(L.pts, L.radii, step=step)
    n = L.n_around or int(np.clip(round(2 * math.pi * rmax * TEXEL_PER_M / seg_px), 5, 40))
    md, info = tube(L.spine, n_around=n, rfun=L.rfun, cap_end=L.cap_end, yscale=L.yscale, ref=-view_back_upright())
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
def bark_texture(seed, size=256, plate_w=(4, 7), plate_h=(7, 20), base='#6f685b', light='#7d7566',
                 dark='#5e574c', fissure='#3b342f', deep='#2c2623', lichen=('#8f9178', '#a3a58a'),
                 lichen_p=0.0025, crack_p=0.55, wave=3.0, moss_specks=('#4c5a33',), moss_p=0.002,
                 top_lip=True):
    """Vertical plates split by one-texel fissures that meander; horizontal breaks between some
    plates; a slightly lighter top rim on each plate; rare lichen and moss specks. Tiles both ways.
    Returns (size, size, 3) uint8."""
    from .core import hex_rgb, vnoise2
    R = rng(seed)
    S = size
    C = lambda h: np.array(hex_rgb(h), np.float64)
    img = np.zeros((S, S, 3), np.float64)
    # columns: widths summing to S
    widths = []
    while sum(widths) < S:
        widths.append(int(R.integers(plate_w[0], plate_w[1] + 1)))
    widths[-1] -= sum(widths) - S
    if widths[-1] < plate_w[0]:
        widths[-2] += widths[-1]
        widths.pop()
    edges = np.concatenate([[0], np.cumsum(widths)])
    ys, xs = np.mgrid[0:S, 0:S]
    # meander: periodic offset of x by y
    ph = R.uniform(0, 2 * math.pi, 3)
    off = (wave * np.sin(2 * math.pi * ys / S * 2 + ph[0]) + 1.4 * np.sin(2 * math.pi * ys / S * 5 + ph[1])
           + 0.8 * np.sin(2 * math.pi * ys / S * 11 + ph[2]))
    xw = (xs + np.round(off).astype(int)) % S
    col = np.searchsorted(edges, xw, side='right') - 1
    x_in = xw - edges[col]
    wcol = np.array(widths)[col]
    # rows per column: heights summing to S, with a per-column phase
    plate_id = np.zeros((S, S), np.int64)
    top_row = np.zeros((S, S), bool)
    crack = np.zeros((S, S), bool)
    for c in range(len(widths)):
        hs = []
        while sum(hs) < S:
            hs.append(int(R.integers(plate_h[0], plate_h[1] + 1)))
        hs[-1] -= sum(hs) - S
        if hs[-1] < 3:
            hs[-2] += hs[-1]
            hs.pop()
        phase = int(R.integers(0, S))
        bounds = (np.concatenate([[0], np.cumsum(hs)]) + phase) % S
        m = col == c
        yy = ys[m]
        rel = (yy - phase) % S
        idx = np.searchsorted(np.cumsum(hs), rel, side='right')
        plate_id[m] = c * 1000 + idx
        starts = (np.concatenate([[0], np.cumsum(hs)[:-1]]))
        is_top = (rel - starts[np.clip(idx, 0, len(hs) - 1)]) == 0
        top_row[m] = is_top
        # horizontal crack at some plate tops
        crack_plate = R.uniform(size=len(hs)) < crack_p
        crack[m] = is_top & crack_plate[np.clip(idx, 0, len(hs) - 1)]
    pv = np.vectorize(lambda k: 0)(plate_id) if False else None
    # plate tone from a hash of its id
    h = (plate_id * 2654435761 + seed * 97) % 1000 / 1000.0
    base_c, light_c, dark_c = C(base), C(light), C(dark)
    tone = np.where(h[..., None] < 0.33, dark_c, np.where(h[..., None] < 0.75, base_c, light_c))
    img[:] = tone
    # soft value variation inside big areas (periodic noise)
    n = vnoise2(np.cos(2 * math.pi * xs / S) * 3 + 10, np.sin(2 * math.pi * ys / S) * 3 + np.cos(2 * math.pi * ys / S) * 2, seed)
    img *= (0.94 + 0.12 * n)[..., None]
    # lighter top rim of each plate (catches the sky)
    if top_lip:
        lip = np.roll(top_row, 1, axis=0) & ~crack
        img[lip] = img[lip] * 1.08
    # fissures: the first texel of each column, and the cracks
    fis = x_in == 0
    img[fis] = C(fissure)
    deepm = fis & (R.uniform(size=(S, S)) < 0.35)
    img[deepm] = C(deep)
    img[crack] = C(fissure)
    # lichen and moss specks (2x1 or 1x1 clusters)
    for colhex, p in [(lichen[0], lichen_p), (lichen[1], lichen_p * 0.5)] + [(m, moss_p) for m in moss_specks]:
        k = int(p * S * S)
        px = R.integers(0, S, size=k)
        py = R.integers(0, S, size=k)
        ok = ~fis[py, px]
        img[py[ok], px[ok]] = C(colhex)
        img[py[ok], (px[ok] + 1) % S] = C(colhex)
    return np.clip(np.round(img), 0, 255).astype(np.uint8)
