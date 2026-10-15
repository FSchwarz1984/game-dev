"""Roads and paths as real geometry on the terrain (round 4, G5R2-1 ⑥: the round-3 road was a soft
brown band painted on the ground, "a child's doodle" with no depth). Everything here is built from
stones, logs and steps laid along the route and fitted to the final heightfield:

  ishidatami   paving of irregular flat stones (Hakone's old Tokaido, the Kumano Kodo): Voronoi cells
               on the road strip, rounded, set a few centimetres proud, worn pale in the middle and
               mossy at the edges and in the joints; long kerb stones along both sides; a stone gutter
               on the uphill side; on slopes a line of upright stones across the road every 15-25 m
               that turns the rain off it (横断排水)
  steps        natural-stone steps (登山道): one to three rough stones make each riser, a flat earth
               tread behind; log steps (丸太段): a log held by two stakes; cut-stone steps for the
               shrine approach (参道), each step one dressed block
  stepping     stepping stones (飛び石)
  trail        the earth itself stays the path (the terrain's worn earth, now with crisp edges), with
               half-buried stones and roots crossing it

Output (export.py writes it): per 16 m chunk two meshes, 'flat' (paving, stepping stones; casts no
shadow) and 'solid' (steps, kerbs, logs, stakes, drains, roots; casts shadows), vertex layout of the
renderer's toon_solid (COLOR = albedo sRGB + AO, UV2 = pattern id, amount). Meshes are not leaned
(ground-hugging: material lean 0).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import Voronoi

from . import geom, noise

CHUNK = 16.0
PAT_PLAIN, PAT_PLANKS, PAT_BARK, PAT_STONE, PAT_MOSS = 0.0, 1.0, 2.0, 4.0, 7.0

GRANITE = np.array([0.56, 0.545, 0.515])       # sRGB, warm grey (knowledge/21: no blue-grey on slopes)
GRANITE_WORN = np.array([0.64, 0.625, 0.59])
EARTH = np.array([0.47, 0.40, 0.31])
EARTH_DARK = np.array([0.36, 0.30, 0.235])
BARK = np.array([0.34, 0.28, 0.22])
LOG_END = np.array([0.70, 0.60, 0.44])
ROOT = np.array([0.40, 0.33, 0.25])


# ------------------------------------------------------------------------------------------- mesh sink
class Sink:
    """Accumulates triangles per (chunk, layer)."""

    def __init__(self):
        self.parts = {}

    def _get(self, x, z, layer):
        key = (int(math.floor(x / CHUNK)), int(math.floor(z / CHUNK)), layer)
        if key not in self.parts:
            self.parts[key] = {'p': [], 'n': [], 'c': [], 'u': [], 'i': [], 'count': 0}
        return self.parts[key]

    def add(self, P, N, C, U, idx, layer='solid', at=None):
        P = np.asarray(P, np.float64)
        if len(P) == 0:
            return
        at = P.mean(axis=0) if at is None else at
        d = self._get(at[0], at[2], layer)
        d['p'].append(P)
        d['n'].append(np.asarray(N, np.float64))
        d['c'].append(np.asarray(C, np.float64))
        d['u'].append(np.asarray(U, np.float64))
        d['i'].append(np.asarray(idx, np.int64) + d['count'])
        d['count'] += len(P)

    def finish(self):
        out = []
        for key, d in sorted(self.parts.items()):
            P = np.concatenate(d['p'])
            out.append({'key': key, 'p': P, 'n': np.concatenate(d['n']), 'c': np.concatenate(d['c']),
                        'u': np.concatenate(d['u']), 'i': np.concatenate(d['i'])})
        return out

    def tri_count(self):
        return sum(sum(len(i) for i in d['i']) for d in self.parts.values())


# ------------------------------------------------------------------------------------------- 2D helpers
def poly_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def clip_halfplane(P, n, c):
    """Keep the part of convex polygon P (k, 2) where n . p <= c."""
    out = []
    k = len(P)
    for i in range(k):
        a, b = P[i], P[(i + 1) % k]
        da, db = n @ a - c, n @ b - c
        if da <= 0:
            out.append(a)
        if (da <= 0) != (db <= 0):
            t = da / (da - db)
            out.append(a + (b - a) * t)
    return np.array(out) if len(out) >= 3 else None


def shrink(P, d):
    """Inset a convex CCW polygon by d (edge offset)."""
    Q = P
    k = len(P)
    for i in range(k):
        a, b = P[i], P[(i + 1) % k]
        e = b - a
        L = np.hypot(*e)
        if L < 1e-9:
            continue
        n = np.array([e[1], -e[0]]) / L          # outward for CCW
        Q = clip_halfplane(Q, n, n @ a - d)
        if Q is None:
            return None
    return Q


def chaikin(P, iters=1, k=0.25):
    for _ in range(iters):
        Q = []
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            Q.append(a * (1 - k) + b * k)
            Q.append(a * k + b * (1 - k))
        P = np.array(Q)
    return P


def ccw(P):
    return P if poly_area(P) > 0 else P[::-1]


# ------------------------------------------------------------------------------------------- the route frame
class Route:
    """A centreline resampled every 5 cm: position, unit tangent and left normal by arc length."""

    def __init__(self, pts, smooth=8):
        pts = np.asarray(pts, np.float64)
        if len(pts) >= 3 and smooth:
            pts = geom.catmull(pts, smooth)
        P, s = geom.resample_polyline(pts, 0.05)
        T = np.gradient(P, axis=0)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        self.P, self.s, self.T = P, s, T
        self.N = np.stack([-T[:, 1], T[:, 0]], 1)          # left of the direction of travel
        self.length = float(s[-1])

    def at(self, s):
        s = np.clip(s, 0.0, self.length)
        i = np.clip(np.searchsorted(self.s, s) - 1, 0, len(self.s) - 2)
        f = ((s - self.s[i]) / np.maximum(self.s[i + 1] - self.s[i], 1e-9))[..., None]
        P = self.P[i] * (1 - f) + self.P[i + 1] * f
        T = self.T[i] * (1 - f) + self.T[i + 1] * f
        T /= np.maximum(np.linalg.norm(T, axis=-1, keepdims=True), 1e-9)
        N = np.stack([-T[..., 1], T[..., 0]], -1)
        return P, T, N

    def to_world(self, st):
        st = np.asarray(st, np.float64)
        P, T, N = self.at(st[..., 0])
        return P + N * st[..., 1:2]


# ------------------------------------------------------------------------------------------- the ground
class Ground:
    def __init__(self, h, x0, z0, cell):
        self.h, self.x0, self.z0, self.cell = h, x0, z0, cell

    def height(self, x, z):
        fx = (np.asarray(x, np.float64) - self.x0) / self.cell
        fz = (np.asarray(z, np.float64) - self.z0) / self.cell
        i = np.clip(np.floor(fx).astype(int), 0, self.h.shape[1] - 2)
        j = np.clip(np.floor(fz).astype(int), 0, self.h.shape[0] - 2)
        tx, tz = np.clip(fx - i, 0, 1), np.clip(fz - j, 0, 1)
        a, b = self.h[j, i], self.h[j, i + 1]
        c, d = self.h[j + 1, i], self.h[j + 1, i + 1]
        return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + d * tx) * tz

    def normal(self, x, z, e=0.25):
        dx = (self.height(x + e, z) - self.height(x - e, z)) / (2 * e)
        dz = (self.height(x, z + e) - self.height(x, z - e)) / (2 * e)
        n = np.stack([-dx, np.ones_like(dx), -dz], -1)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)


# ------------------------------------------------------------------------------------------- one stone
def slab(sink, ground, poly, prot, depth, colour, moss, R, layer='flat', dome=0.012, bevel=0.03, flat_top=None,
         ao_top=1.0, ao_bottom=0.45, pattern=PAT_STONE):
    """A stone set in the ground: outline `poly` (world x, z; CCW seen from above), its top `prot`
    metres above the ground (following the ground's slope, slightly domed), its skirt going `depth`
    below. The top is inset by `bevel` so the sides slope out (a chamfer that catches the light).
    flat_top: a fixed height for the top (steps) instead of the ground + prot."""
    poly = ccw(np.asarray(poly, np.float64))
    n = len(poly)
    c = poly.mean(axis=0)
    top2 = c + (poly - c) * np.clip(1.0 - bevel / max(np.sqrt(abs(poly_area(poly))) * 0.5, 0.05), 0.55, 0.98)
    gy = ground.height(poly[:, 0], poly[:, 1])
    gc = float(ground.height(c[0], c[1]))
    if flat_top is None:
        ty = ground.height(top2[:, 0], top2[:, 1]) + prot
        cy = gc + prot + dome
    else:
        ty = np.full(n, flat_top) + R.normal(0, 0.006, n)
        cy = flat_top + dome * 0.5
    by = np.minimum(gy - depth, ty - 0.05)
    # vertices: centre, top ring, bottom ring
    P = [np.array([c[0], cy, c[1]])]
    for k in range(n):
        P.append(np.array([top2[k, 0], ty[k], top2[k, 1]]))
    for k in range(n):
        P.append(np.array([poly[k, 0], by[k], poly[k, 1]]))
    P = np.array(P)
    idx = []
    for k in range(n):
        idx.append((0, 1 + (k + 1) % n, 1 + k))                       # top fan (CCW seen from above -> up)
    for k in range(n):
        a, b = 1 + k, 1 + (k + 1) % n
        c_, d = 1 + n + k, 1 + n + (k + 1) % n
        idx.append((a, b, d))
        idx.append((a, d, c_))
    idx = np.array(idx)
    # flat-ish shading: the top is lit by its dome-tilted normal, the sides per face (crisp chamfers).
    # Godot's front faces: (b - a) x (c - a) points INTO the solid (knowledge/22 §7).
    out_p, out_n, out_c, out_u = [], [], [], []
    tri = []
    col = np.clip(colour, 0, 1)
    ctr = np.array([c[0], (cy + float(np.mean(by))) * 0.5, c[1]])
    for ti, t in enumerate(idx):
        a, b, cc = P[t[0]], P[t[1]], P[t[2]]
        fn = np.cross(b - a, cc - a)
        L = np.linalg.norm(fn)
        if L < 1e-12:
            continue
        fn /= L
        is_top = ti < n
        outward = np.array([0.0, 1.0, 0.0]) if is_top else ((a + b + cc) / 3 - ctr) * np.array([1.0, 0.2, 1.0])
        if fn @ outward < 0:
            fn = -fn
        order = (t[0], t[2], t[1]) if np.cross(b - a, cc - a) @ fn > 0 else (t[0], t[1], t[2])
        k0 = len(out_p)
        for vi in order:
            out_p.append(P[vi])
            if is_top:
                nn = fn * 0.4 + np.array([0, 0.6, 0])
                out_n.append(nn / np.linalg.norm(nn))
            else:
                out_n.append(fn)
            ao = ao_top if vi <= n else ao_bottom
            if vi == 0:
                ao = min(1.0, ao_top + 0.05)
            out_c.append(np.concatenate([col, [ao]]))
            out_u.append([pattern, moss])
        tri.append((k0, k0 + 1, k0 + 2))
    if not tri:
        return 0
    sink.add(out_p, out_n, out_c, out_u, np.array(tri), layer, at=np.array([c[0], 0, c[1]]))
    return len(tri)


def box_stone(sink, ground, centre_xz, along, size, top_y, colour, moss, R, layer='solid', jag=0.04, pattern=PAT_STONE,
              bottom=None, ao=(1.0, 0.5)):
    """A rough block (a riser stone, a kerb): rectangle `size` = (length along `along`, width) in
    plan with jagged, rounded corners, its top at top_y (flat, a little tilted at random)."""
    along = np.asarray(along, np.float64)
    along = along / np.linalg.norm(along)
    side = np.array([-along[1], along[0]])
    L, W = size
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append(np.asarray(centre_xz) + along * sx * L / 2 * (1 + R.normal(0, jag)) + side * sy * W / 2 * (1 + R.normal(0, jag)))
    poly = chaikin(np.array(pts), 1, 0.22)
    poly = poly + R.normal(0, jag * 0.25 * min(L, W), poly.shape)
    gy = float(ground.height(centre_xz[0], centre_xz[1]))
    return slab(sink, ground, poly, 0.0, (gy - bottom) if bottom is not None else 0.12, colour, moss, R, layer=layer,
                flat_top=top_y, dome=0.0, bevel=0.025, ao_top=ao[0], ao_bottom=ao[1], pattern=pattern)


def cylinder(sink, a, b, r, colour, end_colour, R, layer='solid', n=7, pattern=PAT_BARK, moss=0.0, ao=1.0):
    """A log or stake from a to b (world 3D), its ends showing the light end grain."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ax = b - a
    L = np.linalg.norm(ax)
    ax /= L
    u = np.cross(ax, [0, 1, 0])
    if np.linalg.norm(u) < 0.1:
        u = np.cross(ax, [1, 0, 0])
    u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    ring = [u * math.cos(2 * math.pi * k / n + 0.3) + v * math.sin(2 * math.pi * k / n + 0.3) for k in range(n)]
    P, N, C, U, T = [], [], [], [], []
    col = np.concatenate([np.clip(colour, 0, 1), [ao]])
    ecol = np.concatenate([np.clip(end_colour, 0, 1), [ao]])
    for k in range(n):
        d0, d1 = ring[k], ring[(k + 1) % n]
        nn = (d0 + d1) / np.linalg.norm(d0 + d1)
        q = [a + d0 * r, b + d0 * r, b + d1 * r, a + d1 * r]
        k0 = len(P)
        P += q
        N += [nn] * 4
        C += [col] * 4
        U += [[pattern, moss]] * 4
        T += [(k0, k0 + 2, k0 + 1), (k0, k0 + 3, k0 + 2)]
    for end, sgn in ((a, -1), (b, 1)):
        k0 = len(P)
        P.append(end)
        N.append(ax * sgn)
        C.append(ecol)
        U.append([PAT_PLAIN, 0.0])
        for k in range(n):
            P.append(end + ring[k] * r)
            N.append(ax * sgn)
            C.append(ecol)
            U.append([PAT_PLAIN, 0.0])
        for k in range(n):
            i, j = k0 + 1 + k, k0 + 1 + (k + 1) % n
            T.append((k0, i, j) if sgn > 0 else (k0, j, i))
    # winding: make every triangle face its normal
    P, N = np.array(P), np.array(N)
    T2 = []
    for t in T:
        fn = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
        T2.append(t if fn @ N[t[0]] < 0 else (t[0], t[2], t[1]))
    sink.add(P, N, np.array(C), np.array(U), np.array(T2), layer)
    return len(T2)


# ------------------------------------------------------------------------------------------- road kinds
def ishidatami(sink, ground, route, s0, s1, width, R, seed, gutter_side=0, drains=True, worn=1.0):
    """Paving between arc lengths s0..s1 of a route of the given width; kerbs both sides; the gutter
    on gutter_side (+1 left of travel, -1 right, 0 none); cross drains on slopes."""
    hw = width * 0.5
    kerb_w = 0.24
    inner = hw - kerb_w - 0.02
    # seeds: a jittered grid in (s, t) with varied spacing (bigger stones in the middle)
    seeds = []
    s = s0
    row = 0
    while s < s1:
        step = R.uniform(0.42, 0.62)
        t = -inner + R.uniform(0.05, 0.25)
        while t < inner:
            sp = R.uniform(0.38, 0.62) * (1.15 - 0.3 * abs(t) / inner)
            seeds.append((s + R.normal(0, 0.09), t + R.normal(0, 0.06)))
            t += sp
        s += step
        row += 1
    seeds = np.array(seeds)
    # cross drains: lines across the road (in s, t) where the stones are replaced by a row of upright ones
    drain_lines = []
    if drains:
        L = s1 - s0
        k = int(L / R.uniform(15, 22))
        for i in range(k):
            sd = s0 + (i + 0.5 + R.uniform(-0.2, 0.2)) * L / max(k, 1)
            h0 = float(ground.height(*route.at(np.array([sd]))[0][0]))
            h1 = float(ground.height(*route.at(np.array([min(sd + 2.0, route.length)]))[0][0]))
            if abs(h1 - h0) / 2.0 > 0.05:
                drain_lines.append((sd, R.uniform(0.45, 0.75) * (1 if R.uniform() < 0.5 else -1)))
    if drain_lines:
        keep = np.ones(len(seeds), bool)
        for sd, slope in drain_lines:
            dist = np.abs((seeds[:, 0] - sd) - seeds[:, 1] * slope) / math.sqrt(1 + slope * slope)
            keep &= dist > 0.22
        seeds = seeds[keep]
    # Voronoi with the seeds mirrored across the strip edges (finite cells inside)
    mir = np.concatenate([seeds, seeds * [1, -1] + [0, 2 * inner], seeds * [1, -1] - [0, 2 * inner],
                          seeds + [s1 - s0 + 2.0, 0], seeds - [s1 - s0 + 2.0, 0]])
    vor = Voronoi(mir)
    tris = 0
    for i in range(len(seeds)):
        reg = vor.regions[vor.point_region[i]]
        if -1 in reg or len(reg) < 3:
            continue
        poly = vor.vertices[reg]
        poly = ccw(poly)
        for n_, c_ in ((np.array([0.0, 1.0]), inner), (np.array([0.0, -1.0]), inner), (np.array([1.0, 0.0]), s1),
                       (np.array([-1.0, 0.0]), -s0)):
            if poly is None:
                break
            poly = clip_halfplane(poly, n_, c_)
        if poly is None:
            continue
        for sd, slope in drain_lines:
            if poly is None:
                break
            # cut away the drain's band
            cs = poly.mean(axis=0)
            side = np.sign((cs[0] - sd) - cs[1] * slope)
            nrm = np.array([1.0, -slope]) / math.sqrt(1 + slope * slope)
            poly = clip_halfplane(poly, -side * nrm, -side * (sd / math.sqrt(1 + slope * slope)) - 0.17)
        if poly is None or abs(poly_area(poly)) < 0.02:
            continue
        poly = shrink(poly, R.uniform(0.018, 0.03))
        if poly is None or abs(poly_area(poly)) < 0.015:
            continue
        poly = chaikin(poly, 1, 0.2)
        wp = route.to_world(poly)
        tc = abs(float(np.mean(poly[:, 1]))) / inner
        n1 = noise.fbm(np.array(wp[:, 0].mean() / 3.0), np.array(wp[:, 1].mean() / 3.0), 2, seed + 7)
        wear = np.clip((1.0 - tc * 1.3) * worn, 0, 1)
        colour = GRANITE * (0.86 + 0.18 * R.uniform()) * (1 - 0.1 * n1)
        colour = colour * (1 - 0.35 * wear) + GRANITE_WORN * 0.35 * wear
        moss = float(np.clip(0.15 + 0.85 * tc + (n1 - 0.5) * 0.6 - wear * 0.4, 0, 1))
        tris += slab(sink, ground, ccw(wp), R.uniform(0.025, 0.045), 0.07, colour, moss, R, layer='flat', dome=R.uniform(0.006, 0.02))
    # kerbs: long stones end to end along both edges
    for side in (-1, 1):
        s = s0 + R.uniform(0, 0.2)
        while s < s1 - 0.2:
            L = min(R.uniform(0.5, 0.9), s1 - s)
            sm = s + L / 2
            P, T, N = route.at(np.array([sm]))
            c = P[0] + N[0] * side * (hw - kerb_w / 2)
            gy = float(ground.height(c[0], c[1]))
            colour = GRANITE * (0.8 + 0.15 * R.uniform())
            tris += box_stone(sink, ground, c, T[0], (L - 0.04, kerb_w * R.uniform(0.85, 1.05)), gy + R.uniform(0.05, 0.09), colour,
                              R.uniform(0.5, 1.0), R, layer='solid', jag=0.05)
            s += L
    # the gutter on the uphill side: its outer edge a line of smaller stones, the bed dark gravel
    if gutter_side:
        s = s0
        while s < s1 - 0.15:
            L = min(R.uniform(0.25, 0.45), s1 - s)
            sm = s + L / 2
            P, T, N = route.at(np.array([sm]))
            c = P[0] + N[0] * gutter_side * (hw + 0.42)
            gy = float(ground.height(c[0], c[1]))
            tris += box_stone(sink, ground, c, T[0], (L - 0.03, 0.18), gy + 0.04, GRANITE * (0.72 + 0.15 * R.uniform()), 0.9, R,
                              layer='solid', jag=0.08)
            s += L
    # the cross drains: upright stones set on edge in a slanting line
    for sd, slope in drain_lines:
        t = -hw
        while t < hw - 0.05:
            L = R.uniform(0.22, 0.34)
            tm = min(t + L / 2, hw)
            st = np.array([sd + tm * slope, tm])
            c = route.to_world(st[None, :])[0]
            P, T, N = route.at(np.array([st[0]]))
            along = N[0] + T[0] * slope
            gy = float(ground.height(c[0], c[1]))
            tris += box_stone(sink, ground, c, along, (L - 0.025, 0.12), gy + 0.06, GRANITE * (0.75 + 0.15 * R.uniform()), 0.4, R,
                              layer='solid', jag=0.06)
            t += L
    return tris


def steps(sink, ground, route, s0, s1, width, R, kind='stone', count=None, rise=0.17):
    """Steps between s0 and s1 (heights from the terrain under the centreline). kind: 'stone'
    (natural rough stones), 'log' (logs and stakes), 'cut' (dressed granite blocks, the 参道)."""
    P0 = route.at(np.array([s0]))[0][0]
    P1 = route.at(np.array([s1]))[0][0]
    h0 = float(ground.height(P0[0], P0[1]))
    h1 = float(ground.height(P1[0], P1[1]))
    dh = h1 - h0
    n = count or max(2, int(round(abs(dh) / rise)))
    tris = 0
    hw = width / 2
    for i in range(n):
        # step i: its riser at sa (the lower edge), its tread from sa to sb at the height of the next level
        sa = s0 + (s1 - s0) * i / n
        sb = s0 + (s1 - s0) * (i + 1) / n
        if dh >= 0:
            top = h0 + dh * (i + 1) / n
            front = sa
        else:
            top = h0 + dh * i / n
            front = sb
        Pm, T, N = route.at(np.array([(sa + sb) / 2]))
        Pa = route.at(np.array([front]))[0][0]
        T0, N0 = T[0], N[0]
        if kind == 'cut':
            # one dressed block per step: the whole tread, a clean front edge, chamfered
            c = Pm[0]
            colour = GRANITE * (0.9 + 0.1 * R.uniform())
            tris += box_stone(sink, ground, c, T0, (abs(sb - sa) + 0.06, width), top, colour, R.uniform(0.2, 0.6), R,
                              layer='solid', jag=0.008, bottom=top - abs(dh) / n - 0.12, ao=(1.0, 0.55))
            continue
        # the tread: packed earth, a little lower at the middle, flat
        tread = []
        for (ss, tt) in ((sa, -hw), (sb, -hw), (sb, hw), (sa, hw)):
            tread.append(route.to_world(np.array([[ss, tt * (1 + R.normal(0, 0.05))]]))[0])
        tread = chaikin(np.array(tread), 1, 0.15)
        tcol = EARTH * (0.88 + 0.16 * R.uniform())
        tris += slab(sink, ground, ccw(tread), 0.0, 0.15, tcol, 0.5, R, layer='solid', flat_top=top - 0.02, dome=-0.01, bevel=0.02,
                     pattern=PAT_MOSS, ao_top=0.95)
        if kind == 'log':
            r = R.uniform(0.07, 0.09)
            a = np.array([Pa[0] - N0[0] * hw * 1.05, top - r * 0.6, Pa[1] - N0[1] * hw * 1.05])
            b = np.array([Pa[0] + N0[0] * hw * 1.05, top - r * 0.6 + R.normal(0, 0.01), Pa[1] + N0[1] * hw * 1.05])
            tris += cylinder(sink, a, b, r, BARK * (0.9 + 0.2 * R.uniform()), LOG_END, R, n=7, moss=0.3)
            for sd in (-1, 1):
                q = np.array([Pa[0] + N0[0] * sd * hw * 0.8 - T0[0] * r * 1.4 * np.sign(dh or 1),
                              top - 0.35, Pa[1] + N0[1] * sd * hw * 0.8 - T0[1] * r * 1.4 * np.sign(dh or 1)])
                tris += cylinder(sink, q, q + np.array([0, 0.38 + r, 0]), 0.035, BARK * 0.85, LOG_END * 0.9, R, n=5)
        else:
            # one to three rough stones across the front edge
            k = int(R.integers(1, 4))
            cuts = np.sort(R.uniform(0.25, 0.75, k - 1)) if k > 1 else np.array([])
            edges = np.concatenate([[0.0], cuts, [1.0]])
            for j in range(k):
                ta = -hw + width * edges[j]
                tb = -hw + width * edges[j + 1]
                tm = (ta + tb) / 2
                c = route.to_world(np.array([[front, tm]]))[0]
                depth_ = R.uniform(0.24, 0.34)
                c = c + T0 * depth_ * 0.35 * (1 if dh >= 0 else -1)
                colour = GRANITE * (0.78 + 0.2 * R.uniform())
                tris += box_stone(sink, ground, c, N0, (tb - ta - 0.03, depth_), top + R.uniform(-0.005, 0.02), colour,
                                  R.uniform(0.3, 0.9), R, layer='solid', jag=0.07, bottom=top - abs(dh) / n - 0.1)
    return tris


def stepping_stones(sink, ground, route, s0, s1, R, spacing=(0.55, 0.7), size=(0.34, 0.5), wander=0.12):
    s = s0 + 0.2
    tris = 0
    k = 0
    while s < s1:
        P, T, N = route.at(np.array([s]))
        off = (wander if k % 2 else -wander) + R.normal(0, 0.04)
        c = P[0] + N[0] * off
        r = R.uniform(*size) / 2
        m = int(R.integers(7, 10))
        ang = np.sort(R.uniform(0, 2 * math.pi, m))
        poly = np.stack([c[0] + np.cos(ang) * r * R.uniform(0.82, 1.12, m), c[1] + np.sin(ang) * r * 0.85 * R.uniform(0.82, 1.12, m)], 1)
        poly = chaikin(poly, 1, 0.25)
        colour = GRANITE * (0.86 + 0.16 * R.uniform())
        tris += slab(sink, ground, poly, R.uniform(0.04, 0.06), 0.08, colour, R.uniform(0.1, 0.5), R, layer='flat', dome=0.015)
        s += R.uniform(*spacing)
        k += 1
    return tris


def trail_details(sink, ground, route, s0, s1, width, R, trees=(), stones=1.0):
    """A worn earth path: half-buried stones in and beside it, roots crossing where trees stand near."""
    tris = 0
    L = s1 - s0
    n = int(L / 2.6 * stones)
    for k in range(n):
        s = s0 + R.uniform(0, L)
        t = R.uniform(-width * 0.7, width * 0.7)
        c = route.to_world(np.array([[s, t]]))[0]
        r = R.uniform(0.07, 0.16)
        m = 7
        ang = np.sort(R.uniform(0, 2 * math.pi, m))
        poly = np.stack([c[0] + np.cos(ang) * r * R.uniform(0.7, 1.2, m), c[1] + np.sin(ang) * r * R.uniform(0.7, 1.1, m)], 1)
        tris += slab(sink, ground, chaikin(poly, 1), R.uniform(0.02, 0.06), 0.06, GRANITE * (0.75 + 0.2 * R.uniform()),
                     R.uniform(0.2, 0.8), R, layer='solid', dome=0.02)
    # roots: from trees within 3.5 m of the path, a root or two crossing it, half buried
    for (tx, tz, tr) in trees:
        P = route.P
        d = np.hypot(P[:, 0] - tx, P[:, 1] - tz)
        i = int(np.argmin(d))
        if d[i] > 3.5 or not (s0 <= route.s[i] <= s1):
            continue
        for j in range(int(R.integers(1, 3))):
            si = route.s[i] + R.normal(0, 0.6)
            Pp, T, N = route.at(np.array([si]))
            a2 = np.array([tx, tz]) + (Pp[0] - np.array([tx, tz])) / max(d[i], 0.1) * tr
            b2 = Pp[0] + (Pp[0] - np.array([tx, tz])) / max(d[i], 0.1) * (width * 0.9 + R.uniform(0.2, 0.8)) + T[0] * R.normal(0, 0.4)
            pts = [a2 + (b2 - a2) * f for f in np.linspace(0, 1, 6)]
            for q in range(len(pts) - 1):
                p0, p1 = pts[q], pts[q + 1]
                y0 = float(ground.height(*p0)) - 0.02 - q * 0.004
                y1 = float(ground.height(*p1)) - 0.02 - (q + 1) * 0.004
                r = 0.07 * (1 - q / len(pts)) + 0.025
                tris += cylinder(sink, [p0[0], y0, p0[1]], [p1[0], y1, p1[1]], r, ROOT * (0.9 + 0.2 * R.uniform()), ROOT * 0.8, R, n=5,
                                 moss=0.3, ao=0.85)
    return tris


# ------------------------------------------------------------------------------------------- segments
def resolve(route, control_pts, segments):
    """Segments -> [(s0, s1, seg)]: a segment gives either arc lengths ('from'/'to', metres, negative
    counts from the end) or control point indices ('from_pt'/'to_pt' with 'from_off'/'to_off')."""
    cp = np.asarray(control_pts, np.float64)
    out = []
    for sg in segments:
        if 'from_pt' in sg:
            def arc_of(i):
                d = np.hypot(route.P[:, 0] - cp[i, 0], route.P[:, 1] - cp[i, 1])
                return float(route.s[int(np.argmin(d))])
            a = arc_of(int(sg['from_pt'])) + float(sg.get('from_off', 0.0))
            b = arc_of(int(sg['to_pt'])) + float(sg.get('to_off', 0.0))
        else:
            a, b = float(sg['from']), float(sg['to'])
            a = a if a >= 0 else route.length + a
            b = b if b >= 0 else route.length + b
        a, b = max(0.0, a), min(route.length, b)
        if b - a > 0.2:
            out.append((a, b, sg))
    return out


def kinds_on_grid(route, ranges, Xs, Zs, width, pad=3.0):
    """Distance to the centreline and the segment kind index (into `ranges`, -1 none) on a grid,
    computed inside the route's bounding box only."""
    d = np.full(Xs.shape, np.inf)
    arc = np.zeros(Xs.shape)
    lo = route.P.min(axis=0) - (width + pad)
    hi = route.P.max(axis=0) + (width + pad)
    m = (Xs >= lo[0]) & (Xs <= hi[0]) & (Zs >= lo[1]) & (Zs <= hi[1])
    if not m.any():
        return d, arc, np.full(Xs.shape, -1)
    jj, ii = np.nonzero(m)
    j0, j1, i0, i1 = jj.min(), jj.max() + 1, ii.min(), ii.max() + 1
    sub_d, sub_arc, _ = geom.polyline_field(Xs[j0:j1, i0:i1], Zs[j0:j1, i0:i1], route.P[::4])
    d[j0:j1, i0:i1] = sub_d
    arc[j0:j1, i0:i1] = sub_arc
    k = np.full(Xs.shape, -1)
    for idx, (a, b, sg) in enumerate(ranges):
        k = np.where((arc >= a) & (arc <= b) & np.isfinite(d), idx, k)
    return d, arc, k


# ------------------------------------------------------------------------------------------- the build
def build(L, h, x0, z0, cell, placements, seed):
    """Reads the layout's `road.segments`, `paths[*].kind` / `segments` and `steps`; returns (chunks,
    stats)."""
    R = np.random.default_rng(seed + 4040)
    ground = Ground(h, x0, z0, cell)
    sink = Sink()
    stats = {}
    trees = [(p['x'], p['z'], 0.35 * p.get('scale', 1.0)) for p in placements if p['kind'] in ('cedar', 'broadleaf', 'beech', 'maple', 'pine')]

    def run(route, ranges, width, name, gutter=0):
        for a, b, sg in ranges:
            k = sg['kind']
            if b - a < 0.3:
                continue
            if k == 'ishidatami':
                t = ishidatami(sink, ground, route, a, b, width, R, seed, gutter_side=sg.get('gutter', gutter),
                               drains=sg.get('drains', True), worn=sg.get('worn', 1.0))
            elif k in ('steps_stone', 'steps_log', 'steps_cut'):
                t = steps(sink, ground, route, a, b, sg.get('width', width), R, kind=k.split('_')[1], count=sg.get('count'))
            elif k == 'stepping':
                t = stepping_stones(sink, ground, route, a, b, R)
            elif k == 'trail':
                t = trail_details(sink, ground, route, a, b, width, R, trees, stones=sg.get('stones', 1.0))
            else:
                t = 0
            stats[f'{name}:{k}'] = stats.get(f'{name}:{k}', 0) + t

    RD = L['road']
    road = Route(RD['points'], 10)
    run(road, resolve(road, RD['points'], RD.get('segments', [])), RD['width'], 'road', gutter=0)
    for P in L['paths']:
        if not P.get('segments'):
            continue
        rt = Route(P['points'], 8)
        run(rt, resolve(rt, P['points'], P['segments']), P['width'], P['id'])
    for st in L.get('steps', []):
        rt = Route([st['from'], st['to']], 0)
        k = st.get('kind', 'cut')
        t = steps(sink, ground, rt, 0.0, rt.length, st['width'], R, kind=k, count=st.get('count'))
        stats[f"{st['id']}:steps_{k}"] = t
    stats['triangles'] = sink.tri_count()
    return sink.finish(), stats
