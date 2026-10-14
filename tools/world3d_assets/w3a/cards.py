"""Foliage crowns as camera-facing cards on leaf masses and clumps, in the renderer's card layout
(docs/knowledge/21 section 2.2, toon_foliage foliage_mode 1).

Three levels, the way a painter builds a tree (big shapes first, detail only where light falls):
  masses  big lobes of the crown, hung on the limbs: they carry the big light and shadow;
  clumps  bumps on each mass, of very different sizes, mostly on the upper, outer side;
  cards   leaf tiles scattered over the clumps (and thinner over the mass between them, darker:
          the crevices), dark interior cards so gaps look into shade, and sprays sticking out of the
          silhouette on the lit rim and hanging from the lower edge.
The card's light normal (one per card, the renderer's model) blends the mass normal (dominant),
the clump normal (relief) and the whole crown's normal. Cards that neither the camera (as the leaned
view sees upright objects) nor the noon sun can see are dropped.

Vertex layout per card (4 vertices; triangles (0,2,1), (0,3,2): front-facing, see cards_mesh):
  CUSTOM0.xyz anchor (object space), CUSTOM0.w flex 0..1
  UV2         corner offset in native px, whole numbers: BL, BR, TR, TL
  UV          atlas uv of that corner
  NORMAL      light normal of the card
  COLOR.rgb   tint (sRGB) of the grey leaf tile, COLOR.a ambient occlusion
  VERTEX      anchor + the rough corner (culling bounds only)
"""
from __future__ import annotations

import math

import numpy as np

from .core import PITCH, PPM, fbm3, normalize, rng
from .mesh import MeshData
from .wood import view_back_upright

SUN_NOON = normalize(np.array([-0.187, 0.883, -0.430]))     # render3d/world_env.gd at 12:30
SUN_DUSK = normalize(np.array([-0.92, 0.37, 0.13]))          # about 17:30 (west-south-west, low)


class Mass:
    def __init__(self, centre, radii, yaw=0.0, flat=0.3, lump=0.10, lump_scale=0.3, seed=0,
                 density=1.0, tiles=None, interior=True, kind='mass', sag=0.0,
                 clumps=0.45, clump_r=(1.3, 3.0), tint=None, top_bias=0.9, young=0.25, flex=None):
        self.c = np.asarray(centre, np.float64)
        self.r = np.asarray(radii, np.float64)
        self.yaw = yaw
        self.flat = flat            # 0 round bottom .. 1 flat bottom
        self.lump = lump
        self.lump_scale = lump_scale
        self.seed = seed
        self.density = density
        self.tiles = tiles
        self.interior = interior
        self.kind = kind
        self.sag = sag              # the outer part droops
        self.clumps = clumps        # clump cover factor (0 = smooth mass)
        self.clump_r = clump_r
        self.tint = tint            # per-mass tint override (sRGB 0..1)
        self.top_bias = top_bias    # how strongly clumps prefer the upper side
        self.young = young          # share of clumps in the young-leaf tint
        self.flex = flex

    def local(self, p):
        c, s = math.cos(-self.yaw), math.sin(-self.yaw)
        d = p - self.c
        return np.stack([d[..., 0] * c + d[..., 2] * s, d[..., 1], -d[..., 0] * s + d[..., 2] * c], axis=-1)

    def to_world(self, q):
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return np.stack([q[..., 0] * c + q[..., 2] * s, q[..., 1], -q[..., 0] * s + q[..., 2] * c], axis=-1)

    def field(self, p):
        """Implicit value: < 1 inside (ellipsoid metric, bottom flattened)."""
        q = self.local(np.asarray(p, np.float64)) / self.r
        y = q[..., 1]
        y = np.where(y < 0, y * (1 + self.flat * 1.6), y)
        return np.sqrt(q[..., 0] ** 2 + y ** 2 + q[..., 2] ** 2)

    def surface(self, dirs):
        """Points and normals on the (flattened) ellipsoid for unit directions in mass space."""
        q = dirs * self.r[None, :]
        under = q[:, 1] < 0
        q[under, 1] /= (1 + self.flat * 1.6)
        nl = q / (self.r[None, :] ** 2)
        nl[under, 1] *= (1 + self.flat * 1.6)
        return self.to_world(q) + self.c, normalize(self.to_world(nl))


def fib_sphere(n, seed):
    R = rng(seed)
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i + R.uniform(0, 2 * math.pi)
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], axis=1)


def ellipsoid_area(a, b, c):
    p = 1.6075
    return 4 * math.pi * (((a * b) ** p + (a * c) ** p + (b * c) ** p) / 3) ** (1 / p)


class Card:
    __slots__ = ('p', 'n', 'w', 'h', 'tile', 'ao', 'tint', 'flex', 'kind', 'prio')

    def __init__(self, p, n, w, h, tile, ao, tint, flex, kind='surf', prio=1.0):
        self.p, self.n, self.w, self.h, self.tile = p, n, w, h, tile
        self.ao, self.tint, self.flex, self.kind, self.prio = ao, tint, flex, kind, prio


def occluded(points, masses, d, start=0.5, steps=(0.5, 1.0, 1.8, 2.8, 4.0, 5.5, 7.5, 10.0, 13.0), thresh=0.86):
    """True where a ray from the point along d passes well inside any mass (after `start` m)."""
    pts = np.asarray(points, np.float64)
    occ = np.zeros(len(pts), bool)
    for t in steps:
        if t < start:
            continue
        q = pts + d[None, :] * t
        for m in masses:
            occ |= m.field(q) < thresh
    return occ


def crown_cards(masses, crown_centre, crown_radii, tiles, seed=0, base_tint=(0.33, 0.45, 0.22),
                young_tint=(0.40, 0.50, 0.22), old_tint=(0.27, 0.40, 0.24), overlap=1.9, base_y=None, top_y=None,
                env_k=0.35, clump_k=0.30, interior_frac=0.10, spray_rate=1.0, clump_overlap=2.1, fill_density=0.5,
                max_cards=None, trunk_axis=(0.0, 0.0), flex_r=None, tint_jitter=0.035, cull=True):
    """Scatter clumps and cards over the masses. tiles: dict name -> list of (tile index, w, h);
    'mass' and 'small' for the surface, 'interior', and 'spray0'..'spray7' (screen directions,
    0 = right, counter-clockwise in 45 degree steps with y up). Returns a list of Card."""
    R = rng(seed)
    back = view_back_upright()
    cc = np.asarray(crown_centre, np.float64)
    cr = np.asarray(crown_radii, np.float64)
    if base_y is None:
        base_y = min(m.c[1] - m.r[1] for m in masses)
    if top_y is None:
        top_y = max(m.c[1] + m.r[1] for m in masses)
    flex_r = flex_r or max(cr[0], cr[2])
    ax = np.array([trunk_axis[0], trunk_axis[1]])
    cards = []

    def env_normal(p):
        return normalize((p - cc) / cr ** 2)

    def buried(p, skip):
        d = np.zeros(len(p))
        for j, o in enumerate(masses):
            if j == skip:
                continue
            d = np.maximum(d, np.clip(1.0 - o.field(p), 0, 1))
        return d

    def ao_of(p, n, extra):
        hgt = (p[:, 1] - base_y) / max(top_y - base_y, 1e-6)
        a = 1.0 - (0.22 * np.clip(1 - hgt * 1.4, 0, 1) + 0.30 * np.clip(-n[:, 1], 0, 1) + extra)
        return np.clip(a, 0.25, 1.0)

    def flex_of(p):
        d = np.linalg.norm(p[:, [0, 2]] - ax[None, :], axis=1)
        return np.clip(0.25 + 0.75 * d / flex_r, 0, 1)

    def tint_of(m, kind):
        base = np.asarray(m.tint if m.tint is not None else base_tint, np.float64)
        if kind == 'young':
            base = np.asarray(young_tint, np.float64)
        elif kind == 'old':
            base = np.asarray(old_tint, np.float64)
        j = R.normal(0, tint_jitter)
        return np.clip(base * (1 + j) + R.normal(0, tint_jitter * 0.3, 3), 0, 1)

    def pick(name):
        lst = tiles.get(name) or tiles['mass']
        return lst[R.integers(0, len(lst))]

    for mi, m in enumerate(masses):
        mean_px = np.mean([t[1] for t in tiles[m.tiles or 'mass']])
        size_m = mean_px / PPM
        area = ellipsoid_area(*m.r)
        # ---- clumps (upper, outer side preferred)
        nclump = int(m.clumps * area * 0.9 / (math.pi * np.mean(m.clump_r) ** 2))
        if nclump > 0:
            cand = fib_sphere(nclump * 3, m.seed + 3)
            w = np.clip(0.35 + m.top_bias * cand[:, 1] + 0.25 * R.uniform(size=len(cand)), 0.02, None)
            order = np.argsort(-w * R.uniform(0.6, 1.0, size=len(cand)))
            cand = cand[order[:nclump]]
            sp, sn = m.surface(cand)
            for k in range(len(sp)):
                rc = R.uniform(*m.clump_r) * (1.25 if R.uniform() < 0.12 else 1.0)
                cpos = sp[k] + sn[k] * rc * R.uniform(0.05, 0.3) - np.array([0, R.uniform(0, 0.3) * rc * 0.5, 0])
                radii = np.array([rc, rc * R.uniform(0.6, 0.85), rc])
                n = max(3, int(ellipsoid_area(*radii) * clump_overlap / (size_m * size_m * 0.62) * m.density))
                dirs = fib_sphere(n, int(R.integers(0, 1 << 30)))
                q = dirs * radii[None, :]
                q[q[:, 1] < 0, 1] *= 0.55
                pts = cpos + q
                ncl = normalize(q / (radii[None, :] ** 2))
                nm = normalize(sn[k] * (1 - env_k) + env_normal(cpos) * env_k)
                ncard = normalize(nm[None, :] * (1 - clump_k) + ncl * clump_k)
                bur = np.maximum(buried(pts, mi), np.clip(1.0 - m.field(pts), 0, 1) * 0.8)
                keep = (bur < 0.25) | (R.uniform(size=n) < 0.06)
                ao = ao_of(pts, ncard, 0.6 * bur)
                fx = flex_of(pts)
                kind = 'young' if R.uniform() < m.young * (0.5 + sn[k][1]) else ('old' if R.uniform() < 0.15 else 'base')
                for j in np.nonzero(keep)[0]:
                    t = pick('mass' if R.uniform() < 0.7 else 'small')
                    pos = pts[j] - ncard[j] * (t[1] / PPM) * R.uniform(0.1, 0.3)
                    cards.append(Card(pos, ncard[j], t[1], t[2], t[0], float(ao[j]), tint_of(m, kind), float(fx[j]), 'clump', 1.0))
        # ---- fill: the mass surface between the clumps (crevices, darker), all around
        nf = max(6, int(area * overlap * fill_density / (size_m * size_m * 0.62) * m.density))
        dirs = fib_sphere(nf, m.seed + 11)
        sp, sn = m.surface(dirs)
        nz = fbm3(sp[:, 0] * m.lump_scale, sp[:, 1] * m.lump_scale, sp[:, 2] * m.lump_scale, 3, m.seed) - 0.5
        sp = m.c + (sp - m.c) * (1 + m.lump * nz * 2.2)[:, None]
        if m.sag:
            outward = np.linalg.norm((sp - m.c)[:, [0, 2]], axis=1) / max(m.r[0], m.r[2])
            sp[:, 1] -= m.sag * np.clip(outward, 0, 1) ** 2 * m.r[1] * 0.5
        nm = normalize(sn * (1 - env_k) + env_normal(sp) * env_k)
        bur = buried(sp, mi)
        keep = (bur < 0.2) | (R.uniform(size=nf) < 0.08)
        ao = ao_of(sp, nm, 0.10 + 0.55 * bur)
        fx = flex_of(sp)
        for k in np.nonzero(keep)[0]:
            t = pick('mass')
            pos = sp[k] - nm[k] * size_m * R.uniform(0.2, 0.45)
            cards.append(Card(pos, nm[k], t[1], t[2], t[0], float(ao[k]), tint_of(m, 'base'), float(fx[k]) * 0.7, 'fill', 0.8))
        # ---- interior: dark cards inside the mass, so gaps look into shade
        if m.interior:
            ni = max(2, int(nf * interior_frac))
            inner = fib_sphere(ni, m.seed + 29) * m.r[None, :] * R.uniform(0.3, 0.7, size=(ni, 1))
            inner = m.to_world(inner) + m.c
            for k in range(ni):
                t = pick('interior')
                nn = env_normal(inner[k])
                cards.append(Card(inner[k], nn, t[1], t[2], t[0], 0.35, tint_of(m, 'old'), 0.2, 'interior', 0.5))
        # ---- sprays out of the outline: lit rim and the lower edge
        if spray_rate > 0 and 'spray0' in tiles:
            ns = int(spray_rate * area / 7.0)
            dirs = fib_sphere(max(ns * 4, 8), m.seed + 41)
            sp, sn = m.surface(dirs)
            ne = env_normal(sp)
            right = np.array([1.0, 0, 0])
            up_s = normalize(np.cross(back, right))       # screen up for upright objects
            sil = np.abs(ne @ back) < 0.45
            lit = (ne @ SUN_NOON) > 0.05
            low = ne[:, 1] < -0.25
            cand = np.nonzero(sil & (lit | low))[0]
            if len(cand):
                pickn = R.choice(cand, size=min(ns, len(cand)), replace=False)
                for k in pickn:
                    sx, sy = ne[k] @ right, ne[k] @ up_s
                    if low[k] and not lit[k]:
                        sy -= 0.8
                    ang = math.atan2(sy, sx)
                    di = int(round(ang / (math.pi / 4))) % 8
                    t = pick(f'spray{di}')
                    pos = sp[k] + ne[k] * (t[1] / PPM) * 0.25
                    nmk = normalize(sn[k] * 0.6 + ne[k] * 0.4)
                    cards.append(Card(pos, nmk, t[1], t[2], t[0], 0.95 if lit[k] else 0.8,
                                      tint_of(m, 'young' if lit[k] else 'base'), 1.0, 'spray', 1.2))
    if cull:
        P = np.array([c.p for c in cards])
        surf = np.array([c.kind != 'interior' for c in cards])
        cam_hidden = occluded(P, masses, back)
        sun_hidden = occluded(P, masses, SUN_NOON)
        keep = []
        for i, c in enumerate(cards):
            if c.kind == 'interior':
                keep.append(True)
            elif not cam_hidden[i]:
                keep.append(True)
            elif not sun_hidden[i]:
                c.prio = 0.4
                keep.append(R.uniform() < 0.55)
            else:
                keep.append(False)
        cards = [c for c, k in zip(cards, keep) if k]
    if max_cards is not None and len(cards) > max_cards:
        order = sorted(range(len(cards)), key=lambda i: -(cards[i].prio + R.uniform(0, 0.3)))
        cards = [cards[i] for i in sorted(order[:max_cards])]
    return cards


def cards_mesh(cards, atlas_w, atlas_h, rects):
    """Cards -> MeshData in the renderer's layout (module docstring)."""
    n = len(cards)
    P = np.zeros((n * 4, 3))
    N = np.zeros((n * 4, 3))
    UV = np.zeros((n * 4, 2))
    UV2 = np.zeros((n * 4, 2))
    C0 = np.zeros((n * 4, 4))
    CO = np.zeros((n * 4, 4))
    idx = np.zeros((n * 2, 3), np.int64)
    back = view_back_upright()
    right = np.array([1.0, 0, 0])
    up = normalize(np.cross(back, right))
    for i, cd in enumerate(cards):
        x, y, w, h = rects[cd.tile]
        b = i * 4
        hw, hh = w // 2, h // 2
        # BL, BR, TR, TL in native px (x right, y up); whole numbers, exact size
        off = np.array([[-hw, -hh], [w - hw, -hh], [w - hw, h - hh], [-hw, h - hh]], np.float64)
        uvs = np.array([[x, y + h], [x + w, y + h], [x + w, y], [x, y]], np.float64)
        UV[b:b + 4] = uvs / np.array([atlas_w, atlas_h])
        UV2[b:b + 4] = off
        P[b:b + 4] = cd.p + (off[:, :1] * right + off[:, 1:] * up) / PPM
        N[b:b + 4] = cd.n
        C0[b:b + 4, :3] = cd.p
        C0[b:b + 4, 3] = cd.flex
        CO[b:b + 4, :3] = cd.tint
        CO[b:b + 4, 3] = cd.ao
        # Front-facing for the camera: Godot's front faces are clockwise on screen, and with
        # cull_disabled a back face gets its NORMAL flipped (DO_SIDE_CHECK), which would light the
        # card from the wrong side. BL, BR, TR is counter-clockwise on screen (y up), so the
        # triangles are (0,2,1), (0,3,2); export flips once, hence (0,1,2), (0,2,3) here.
        idx[i * 2] = (b, b + 1, b + 2)
        idx[i * 2 + 1] = (b, b + 2, b + 3)
    md = MeshData()
    md.add(P, N, UV, idx, uv2=UV2, col=CO, cus=C0)
    return md
