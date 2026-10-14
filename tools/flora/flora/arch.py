"""Tree architecture helpers shared by the species: trunk paths, limbs that end inside foliage
masses, mass layouts inside a crown envelope, bark textures."""
import math

import numpy as np

from .core import Rng, normalize, vnoise2, fbm2, hash01


def bezier(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + (t ** 3) * p3


def trunk_path(h, lean=(0.0, 0.0), wobble=0.15, seed=1, n=32, bend=0.0):
    """A trunk centre line from the ground to height h (metres), leaning by lean=(dx, dz) at the
    top, with a slow wobble."""
    rng = Rng(seed)
    t = np.linspace(0, 1, n)
    ph1, ph2 = rng.range(0, 6.28), rng.range(0, 6.28)
    x = lean[0] * t ** (1.3 + bend) + wobble * np.sin(t * 4.1 + ph1) * t
    z = lean[1] * t ** (1.3 + bend) + wobble * 0.7 * np.sin(t * 3.3 + ph2) * t
    y = h * t
    return np.stack([x, y, z], axis=-1)


def collar(rr, k=1.45, length=0.12):
    """Radii along a limb with a flared branch collar where it leaves its parent."""
    rr = np.asarray(rr, dtype=np.float64).copy()
    n = len(rr)
    t = np.linspace(0, 1, n)
    return rr * (1 + (k - 1) * np.exp(-t / max(1e-3, length)))


def limb_to(start, end, rise=0.45, out=0.35, seed=1, n=20, sag=0.0):
    """A limb from `start` to `end` that first rises, then bends out (how branches grow toward the
    light). sag pulls the middle down (heavy horizontal limbs)."""
    rng = Rng(seed)
    start = np.asarray(start, float)
    end = np.asarray(end, float)
    d = end - start
    up = np.array([0, 1.0, 0])
    p1 = start + up * (abs(d[1]) * rise + 0.2) + d * 0.18
    p2 = start + d * (0.6 + out * 0.3) + up * (0.15 * np.linalg.norm(d) * (1 - sag)) - up * sag * np.linalg.norm(d) * 0.25
    p2 = p2 + np.array([rng.range(-0.3, 0.3), rng.range(-0.15, 0.15), rng.range(-0.3, 0.3)])
    return bezier(start, p1, p2, end, n)


def point_on(path, t):
    path = np.asarray(path, float)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    x = t * s[-1]
    return np.array([np.interp(x, s, path[:, i]) for i in range(3)])


def dome_layout(center, radii, n, rng, shell=0.55, top_bias=0.5, min_sep=0.9):
    """Mass centres inside an envelope ellipsoid, favouring its outer upper shell; returns (n, 3)
    world points and a 0..1 'outerness' per point."""
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 400:
        tries += 1
        d = rng.unit3()
        if d[1] < -0.55:            # nothing hangs below the crown's belly
            continue
        if rng() < top_bias and d[1] < 0.0:
            continue
        rr = shell + (1 - shell) * rng() ** 0.6
        p = center + d * radii * rr
        ok = True
        for q in pts:
            if np.linalg.norm((p - q) / radii) < min_sep * (1.0 / max(1, n) ** 0.33):
                ok = False
                break
        if ok:
            pts.append(p)
    pts = np.array(pts)
    outer = np.linalg.norm((pts - center) / radii, axis=1)
    return pts, outer


# ---------------------------------------------------------------- bark textures
def bark_smooth(seed, streak=0.10, lichen_mat=None, moss_mat=None, moss_h=0.6, lichen_p=0.0):
    """Smooth bark (maple, beech): soft vertical streaks, lichen patches, moss at the foot."""
    def fx(u, v, n, P, base, T):
        dv = (vnoise2(v * 3.0, u * 1.2, seed) - 0.5) * streak * 2
        dv += (vnoise2(v * 9.0, u * 6.0, seed + 3) - 0.5) * 0.06
        mat = np.zeros(len(u), np.int64)
        if lichen_mat is not None and lichen_p > 0:
            q = vnoise2(P[:, 0] * 6 + v * 2, P[:, 1] * 4, seed + 7)
            mat = np.where(q > 1 - lichen_p, lichen_mat, mat)
        if moss_mat is not None:
            q = vnoise2(v * 4, u * 3, seed + 9)
            mm = (P[:, 1] < moss_h * (0.6 + 0.8 * q)) & (n[:, 0] > -0.2)
            mat = np.where(mm, moss_mat, mat)
        return dv, mat
    return fx


def bark_furrowed(seed, pitch=0.22, depth=0.22, moss_mat=None, moss_k=0.6, lichen_mat=None, n_furrows=26):
    """Deep vertical furrows that wander, merge and split, with plates between them broken by the
    odd horizontal crack (camphor, old trunks)."""
    def fx(u, v, n, P, base, T):
        circ = v / (2 * math.pi)
        x = circ * n_furrows + (vnoise2(circ * 7, u * 0.7, seed) - 0.5) * 1.8
        fi = np.floor(x)
        ff = x - fi
        w = 0.22 + 0.18 * vnoise2(fi * 3.1, u * 1.3, seed + 2)
        furrow = ff < w
        ridge_lit = (ff > w) & (ff < w + 0.20)
        # plates: each strip between furrows is cut into lengths by thin cracks
        seg = u * (0.55 + 0.45 * hash01(fi.astype(np.int64), np.int64(seed)))
        crack = ((seg - np.floor(seg)) < 0.05) & ~furrow & (hash01(fi.astype(np.int64), np.floor(seg).astype(np.int64), np.int64(seed + 9)) < 0.5)
        dv = np.where(furrow, -depth, 0.0) + np.where(ridge_lit, 0.08, 0.0) + np.where(crack, -depth * 0.6, 0.0)
        dv += (hash01(fi.astype(np.int64), np.floor(seg).astype(np.int64), np.int64(seed + 4)) - 0.5) * 0.10
        mat = np.zeros(len(u), np.int64)
        if moss_mat is not None:
            q = vnoise2(P[:, 0] * 1.6, P[:, 1] * 1.3 + P[:, 2], seed + 11)
            low = np.clip(1.2 - P[:, 1] * 0.35, 0, 1)
            mm = (q + low * 0.22 > moss_k) & (n[:, 1] > -0.3) & ~furrow
            mat = np.where(mm, moss_mat, mat)
        if lichen_mat is not None:
            q = vnoise2(P[:, 0] * 2.2 + v * 0.8, P[:, 1] * 1.6, seed + 13)
            mat = np.where((q > 0.88) & ~furrow & (mat == 0), lichen_mat, mat)
        return dv, mat
    return fx


def bark_fibrous(seed, moss_mat=None):
    """Sugi: long fibrous strips peeling in vertical ribbons."""
    def fx(u, v, n, P, base, T):
        circ = v / (2 * math.pi)
        x = circ * 26 + (vnoise2(circ * 4, u * 0.35, seed) - 0.5) * 1.2
        fi = np.floor(x)
        ff = x - fi
        strip = (vnoise2(fi * 2.7, u * 0.6, seed + 1) - 0.5) * 0.16
        groove = ff < 0.22
        dv = strip + np.where(groove, -0.16, 0.0) + np.where((ff > 0.22) & (ff < 0.4), 0.05, 0.0)
        mat = np.zeros(len(u), np.int64)
        if moss_mat is not None:
            q = vnoise2(P[:, 0] * 4, P[:, 1] * 3, seed + 5)
            q2 = vnoise2(v * 2.2, u * 2.5, seed + 6)
            mat = np.where((P[:, 1] < 0.2 + 0.45 * q) & (q2 > 0.5) & (n[:, 0] < 0.2), moss_mat, mat)
        return dv, mat
    return fx


def bark_plates(seed, red_mat=None, red_from=2.0, moss_mat=None):
    """Pine: irregular plates with dark cracks; the upper trunk turns red-orange and flaky."""
    def fx(u, v, n, P, base, T):
        circ = v / (2 * math.pi)
        X = circ * 18
        Y = u * 3.2
        jx = X + (vnoise2(X * 0.7, Y * 0.5, seed) - 0.5) * 1.4
        jy = Y + (vnoise2(X * 0.5, Y * 0.7, seed + 1) - 0.5) * 1.2 + np.floor(jx) * 0.37
        fx_ = jx - np.floor(jx)
        fy_ = jy - np.floor(jy)
        crack = (fx_ < 0.14) | (fy_ < 0.16)
        dv = np.where(crack, -0.2, (hash01(np.floor(jx).astype(np.int64), np.floor(jy).astype(np.int64), np.int64(seed)) - 0.5) * 0.12)
        mat = np.zeros(len(u), np.int64)
        if red_mat is not None:
            q = vnoise2(X * 0.4, u * 0.8, seed + 3)
            red = (P[:, 1] > red_from - 0.8 + q * 1.6)
            mat = np.where(red, red_mat, mat)
            dv = np.where(red, dv * 0.6, dv)
        if moss_mat is not None:
            q = vnoise2(P[:, 0] * 4, P[:, 1] * 3, seed + 5)
            mat = np.where((P[:, 1] < 0.35 + 0.4 * q) & (n[:, 0] < 0.4) & (mat == 0), moss_mat, mat)
        return dv, mat
    return fx


def bark_blocky(seed):
    """Persimmon: dark bark broken into small square blocks."""
    def fx(u, v, n, P, base, T):
        circ = v / (2 * math.pi)
        X = circ * 22
        Y = u * 6.0
        jx = X + np.floor(Y) * 0.5
        crack = ((jx - np.floor(jx)) < 0.2) | ((Y - np.floor(Y)) < 0.18)
        dv = np.where(crack, -0.2, (hash01(np.floor(jx).astype(np.int64), np.floor(Y).astype(np.int64), np.int64(seed)) - 0.5) * 0.14)
        return dv, None
    return fx
