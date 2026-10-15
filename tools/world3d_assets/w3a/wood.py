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


def wood_mesh(limbs, tex_size=256, colour_fn=None, ao_fn=None, moss_fn=None, u_scale=1.0):
    """All limbs as one surface for toon_solid (albedo_mode 1). colour_fn(P, N, limb) -> (n, 3) tint,
    ao_fn(P, N, limb) -> (n,) AO, moss_fn(P, N, limb) -> (n,) moss amount. u_scale: the texture's
    across direction stretched on limbs and branches (fewer grain lines round them)."""
    out = MeshData()
    for L in limbs:
        a = L.md.arrays()
        P, N = a['p'], a['n']
        uv = a['uv'] * TEXEL_PER_M / tex_size
        if L.kind != 'trunk' and u_scale != 1.0:
            uv = uv * np.array([u_scale, 1.0])
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
    """The species' bark (same arguments as before round 4b): drawn as flowing grain by
    bark_flow_texture. The round-4 painter cut every ridge into flat-toned segments with short dark
    breaks across, which read as bricks laid in courses (lead 12:55); break_p is no longer used."""
    from .core import hex_rgb
    c0 = np.array(hex_rgb(ridge[0]), np.float64)
    cf = np.array(hex_rgb(fissure), np.float64)
    sh = '#%02x%02x%02x' % tuple(int(round(v)) for v in (c0 * 0.6 + cf * 0.4))
    sp = (max(2.0, float(spacing[0])), max(float(spacing[0]) + 1.0, float(spacing[1])))
    k = size / 256.0
    return bark_flow_texture(seed, size=size, spacing=sp, ridge=ridge, lip=lip, shadow=sh, fissure=fissure, deep=deep,
                             moss=(moss[0], moss[-1], moss[0]), lichen=lichen, flow=2.6 * min(1.0, k * 1.5), wander=wave,
                             split_p=0.45, gap_p=merge_p, cross_n=max(2, int(26 * k * k)), moss_k=min(0.08, moss_p * 30.0),
                             lichen_k=lichen_p)


def _wrap_noise(R, S, cells, octaves=2):
    """Smooth value noise that tiles both ways (size S x S), 0..1."""
    from scipy import ndimage
    out = np.zeros((S, S))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = int(cells * 2 ** o)
        g = R.uniform(size=(n, n))
        z = ndimage.zoom(np.tile(g, (3, 3)), S / n, order=3, mode='grid-wrap')
        out += amp * z[S:2 * S, S:2 * S]
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / max(out.max() - out.min(), 1e-9)


def bark_flow_texture(seed, size=256, spacing=(6, 11), ridge=('#665e53', '#746c60', '#827a6c'), lip='#938a7a',
                      shadow='#5c554b', fissure='#4a423b', deep='#37302b', moss=('#55623a', '#627142', '#4a5733'),
                      lichen=('#8e9379', '#a3a68b'), flow=2.6, wander=(2.2, 1.1), split_p=0.5, gap_p=0.35, cross_n=26,
                      moss_k=0.07, lichen_k=0.0022):
    """Bark of an old trunk at one texel per native pixel, drawn as flowing grain (lead 12:55: the
    round-4 bark read as bricks laid in courses): long one-texel fissures running up the texture (v),
    waving together and each on its own (no straight runs, never a horizontal band), forking around
    lens-shaped plates and joining again, now and then fading out so two ridges merge; the ridges
    between them shaded across (a lit lip on the left, a darker side on the right) and only slowly
    along, so no ridge is cut into blocks; a few short cracks across, slanted and broken off; moss
    in the fissures and on the shaded sides in patches; a few lichen spots. Tiles both ways (every
    wave has whole cycles per tile, the fissure set wraps across). Returns (size, size, 3) uint8."""
    from .core import hex_rgb
    R = rng(seed)
    S = size
    C = lambda h: np.array(hex_rgb(h), np.float64)
    ridge_c = [C(h) for h in ridge]
    y = np.arange(S)
    # fissure base positions across the tile (wrapping)
    xs0 = []
    x = R.uniform(0, 3)
    while x < S - spacing[0] * 0.6:
        xs0.append(x)
        x += R.uniform(*spacing)
    xs0 = np.array(xs0)
    n = len(xs0)
    # a common flow (the grain waves together) and each fissure's own wander
    common = flow * np.sin(2 * math.pi * 1 * y / S + R.uniform(0, 2 * math.pi)) + 0.8 * flow * np.sin(2 * math.pi * 2 * y / S + R.uniform(0, 2 * math.pi))
    paths = np.zeros((n, S))
    for i in range(n):
        f1, f2 = int(R.integers(1, 3)), int(R.integers(3, 6))
        p1, p2 = R.uniform(0, 2 * math.pi, 2)
        a1 = wander[0] * R.uniform(0.5, 1.2)
        a2 = wander[1] * R.uniform(0.4, 1.1)
        paths[i] = xs0[i] + common + a1 * np.sin(2 * math.pi * f1 * y / S + p1) + a2 * np.sin(2 * math.pi * f2 * y / S + p2)
    alive = np.ones((n, S), bool)
    for i in range(n):
        if R.uniform() < gap_p:
            start = int(R.integers(0, S))
            length = int(R.integers(14, 48))
            alive[i, (start + np.arange(length)) % S] = False
    wide = R.uniform(size=n) < 0.3                    # the main furrows: two texels
    # ridge tone per ridge (between fissure i and i+1), varying slowly along y; the boundary between
    # two tones runs slanted across the ridge
    base_t = R.uniform(0.2, 1.8, n)
    tf = R.integers(1, 3, n)
    tph = R.uniform(0, 2 * math.pi, n)
    slant = R.choice([-1.0, 1.0], n) * R.uniform(0.15, 0.4, n)
    mossn = _wrap_noise(R, S, 6, 3)
    patch = _wrap_noise(R, S, 12, 2)
    img = np.zeros((S, S, 3))
    kind = np.zeros((S, S), np.int8)         # 0 ridge, 1 fissure, 2 lip, 3 shadow side
    for yy in range(S):
        px = paths[:, yy]
        order = np.argsort(px % S)
        cuts = (px[order] % S)
        al = alive[order, yy]
        live = cuts[al]
        live_idx = order[al]
        if len(live) == 0:
            continue
        xs = np.arange(S)
        # the ridge's tone follows all fissures, the faded ones too: where a fissure fades out the two
        # ridges merge without a step in tone across them (a step there read as a block)
        k = np.searchsorted(cuts, xs + 0.5, side='right') - 1
        left = np.where(k >= 0, cuts[k % n], cuts[-1] - S)
        right = np.where(k + 1 < n, cuts[(k + 1) % n], cuts[0] + S)
        rid = order[k % n]
        w = np.maximum(right - left, 1.0)
        u = (xs + 0.5 - left) / w
        tone = base_t[rid] + 0.85 * np.sin(2 * math.pi * tf[rid] * yy / S + tph[rid]) + slant[rid] * (u - 0.5) * 3.0
        ti = np.clip(np.round(tone), 0, 2).astype(int)
        row = np.array([ridge_c[t] for t in ti])
        row *= (0.97 + 0.06 * patch[yy])[:, None] if False else 1.0
        img[yy] = row
        kind[yy] = 0
        # the lit lip just right of each fissure, the shaded side just left of the next
        for xi, fi in zip(live, live_idx):
            xr = int(math.floor(xi)) % S
            kind[yy, (xr + 1 + (1 if wide[fi] else 0)) % S] = 2
            kind[yy, (xr - 1) % S] = 3
            kind[yy, xr] = 1
            if wide[fi]:
                kind[yy, (xr + 1) % S] = 1
        for xi, fi in zip(live, live_idx):
            xr = int(math.floor(xi)) % S
            img[yy, xr] = C(deep) if wide[fi] or R.uniform() < 0.25 else C(fissure)
            if wide[fi]:
                img[yy, (xr + 1) % S] = C(fissure)
            lp = (xr + 2 if wide[fi] else xr + 1) % S
            if R.uniform() < 0.8:
                img[yy, lp] = C(lip)
            if R.uniform() < 0.7:
                img[yy, (xr - 1) % S] = C(shadow)
        # where a fissure fades out, its ends taper (the fissure texel lighter for a few rows)
    for i in range(n):
        if not alive[i].all():
            for yy in range(S):
                if alive[i, yy] and (not alive[i, (yy - 1) % S] or not alive[i, (yy + 1) % S] or not alive[i, (yy - 2) % S]
                                     or not alive[i, (yy + 2) % S]):
                    xr = int(math.floor(paths[i, yy])) % S
                    img[yy, xr] = C(shadow)
    # forks: a branch peels off a fissure and comes back (lens-shaped plates)
    for i in range(n):
        if R.uniform() > split_p:
            continue
        for _ in range(int(R.integers(1, 3))):
            y0 = int(R.integers(0, S))
            Lb = int(R.integers(22, 70))
            side = 1 if R.uniform() < 0.6 else -1
            gap = (xs0[(i + side) % n] - xs0[i]) * side % S if n > 1 else 8
            dmax = max(2.0, min(R.uniform(2.0, 4.5), 0.45 * gap))
            prev = None
            for t in range(Lb):
                yy = (y0 + t) % S
                if not alive[i, yy]:
                    break
                tt = t / (Lb - 1)
                off = dmax * math.sin(math.pi * tt) ** 0.75
                xb = int(math.floor(paths[i, yy] + side * off)) % S
                img[yy, xb] = C(fissure)
                if prev is not None and abs(xb - prev) > 1 and abs(xb - prev) < S // 2:
                    lo_, hi_ = sorted((prev, xb))
                    img[yy, lo_ + 1:hi_] = C(fissure)
                if R.uniform() < 0.6:
                    img[yy, (xb + 1) % S] = C(lip) if side > 0 else img[yy, (xb + 1) % S]
                prev = xb
    # short slanted cracks across a ridge, broken off before the next fissure
    for _ in range(cross_n):
        i = int(R.integers(0, n))
        yy = int(R.integers(0, S))
        if not alive[i, yy]:
            continue
        L_ = int(R.integers(2, 5))
        dy = 1 if R.uniform() < 0.5 else -1
        x0 = int(math.floor(paths[i, yy])) + 1
        for t in range(L_):
            xx = (x0 + t) % S
            yv = (yy + dy * (t // 2 + (t % 2) * int(R.uniform() < 0.5))) % S
            img[yv, xx] = C(fissure) if t < L_ - 1 else C(shadow)
    # moss in the fissures and on the shaded sides, in patches; lichen spots on the ridges
    mz = (mossn > 1.0 - moss_k * 4.0) & (patch > 0.45)
    mc = [C(h) for h in moss]
    pick = np.clip((patch * 2.999).astype(int), 0, len(mc) - 1)
    for yy, xx in zip(*np.nonzero(mz & ((kind == 1) | (kind == 3)))):
        img[yy, xx] = mc[2] if kind[yy, xx] == 1 else mc[pick[yy, xx] % 2]
    for yy, xx in zip(*np.nonzero(mz & (kind == 0) & (patch > 0.68))):
        img[yy, xx] = mc[1] if mossn[yy, xx] > 1.0 - moss_k * 2.0 else mc[0]
    lc = [C(h) for h in lichen]
    for _ in range(int(lichen_k * S * S)):
        bx, by = int(R.integers(0, S)), int(R.integers(0, S))
        if kind[by, bx] != 0:
            continue
        c_ = lc[int(R.integers(0, len(lc)))]
        img[by, bx] = c_
        if R.uniform() < 0.6:
            img[by, (bx + 1) % S] = c_
        if R.uniform() < 0.4:
            img[(by + 1) % S, bx] = c_
    return np.clip(np.round(img), 0, 255).astype(np.uint8)
