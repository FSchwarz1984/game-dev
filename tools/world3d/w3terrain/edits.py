"""Human-made edits, only where people would build them: the old road cut into the slope with
natural cut and fill banks, worn footpaths, levelled yards and a raised shrine terrace, stone steps,
contour-following rice terraces, the stream channel and the spring pool, the charcoal kiln."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import geom, noise


def sample_bilinear(h, x0, z0, cell, px, pz):
    fx = (np.asarray(px) - x0) / cell
    fz = (np.asarray(pz) - z0) / cell
    return ndimage.map_coordinates(h, [fz, fx], order=1, mode="nearest")


def road_profile(h, x0, z0, cell, pts, max_grade, window=10.0):
    """Heights along a polyline: the terrain smoothed along the way, then the grade limited."""
    P, s = geom.resample_polyline(pts, 0.5)
    raw = sample_bilinear(h, x0, z0, cell, P[:, 0], P[:, 1])
    n = max(3, int(window / 0.5))
    k = np.ones(n) / n
    sm = np.convolve(np.pad(raw, (n, n), mode="edge"), k, mode="same")[n:-n]
    # limit the grade both ways (iterate to settle)
    ds = 0.5
    for _ in range(6):
        for i in range(1, len(sm)):
            sm[i] = np.clip(sm[i], sm[i - 1] - max_grade * ds, sm[i - 1] + max_grade * ds)
        for i in range(len(sm) - 2, -1, -1):
            sm[i] = np.clip(sm[i], sm[i + 1] - max_grade * ds, sm[i + 1] + max_grade * ds)
    return P, s, sm


def cut_corridor(h, X, Z, P, prof, width, bank, bank_slope=1.0, crown=0.04, wobble_seed=0):
    """Lays a corridor of the given profile into the terrain. Inside half the width the ground is
    the corridor's height (slightly crowned); beyond it the terrain is clamped into a cone of
    slope `bank_slope` around the corridor: cut banks uphill, fill slopes downhill."""
    d, arc, ph = geom.polyline_field(X, Z, P, prof)
    # the edge wanders a little (a road is not ruled)
    wob = (noise.fbm(arc / 6.0, d * 0.0 + wobble_seed, 2, wobble_seed) - 0.5) * 0.5
    hw = width * 0.5 + wob
    inside = d <= hw
    road_h = ph - crown * (d / np.maximum(hw, 0.1)) ** 2
    reach = np.maximum(d - hw, 0.0)
    lim = bank_slope * reach
    clamped = np.clip(h, ph - lim, ph + lim)
    zone = d < hw + bank + np.abs(h - ph) / max(bank_slope, 0.1)
    out = np.where(inside, road_h, np.where(zone, clamped, h))
    # soften the toe and the brow of the banks
    soft = ndimage.gaussian_filter(out, 0.8)
    band = (d > hw - 0.2) & (d < hw + bank + 4.0)
    out = np.where(band, soft * 0.5 + out * 0.5, out)
    return out, d, arc, ph


def flatten_path(h, X, Z, pts, width, depth=0.06, smooth_m=4.0, cell=0.5):
    """Footpaths follow the land: the cross-slope is eased and the tread worn a little lower."""
    P, s = geom.resample_polyline(pts, 0.5)
    hs = ndimage.gaussian_filter(h, smooth_m / cell * 0.5)
    prof = ndimage.map_coordinates(hs, [(P[:, 1] - Z[0, 0]) / cell, (P[:, 0] - X[0, 0]) / cell], order=1, mode="nearest")
    d, arc, ph = geom.polyline_field(X, Z, P, prof)
    k = geom.smoothstep(width * 0.5 + 1.2, width * 0.5 - 0.2, d)
    target = ph - depth * geom.smoothstep(width * 0.5, 0.0, d)
    return h * (1.0 - k * 0.75) + target * k * 0.75, d, arc


def rect_sdf(X, Z, centre, size, angle_deg):
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    lx = (X - centre[0]) * c + (Z - centre[1]) * s
    lz = -(X - centre[0]) * s + (Z - centre[1]) * c
    qx = np.abs(lx) - size[0] * 0.5
    qz = np.abs(lz) - size[1] * 0.5
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0))
    inside = np.minimum(np.maximum(qx, qz), 0.0)
    return outside + inside, lx, lz


def apply_pad(h, X, Z, pad, seed=0):
    sdf, lx, lz = rect_sdf(X, Z, pad["centre"], pad["size"], pad.get("angle", 0.0))
    # organic corners: perturb the edge by noise
    sdf = sdf + (noise.fbm(X / 3.0, Z / 3.0, 2, seed) - 0.5) * 0.5
    f = pad.get("feather", 1.5)
    target = pad["height"]
    if pad.get("raised"):
        # a raised platform: steep (stone-faced) sides, the land around untouched
        k = geom.smoothstep(0.25, -0.05, sdf)
        out = np.where(sdf < 0.25, h * (1 - k) + target * k, h)
        return out, sdf
    k = geom.smoothstep(f, 0.0, sdf)
    walls = pad.get("wall", [])
    if walls:
        # walled sides keep the fill steep (a retaining wall stands there); open sides feather
        a = np.radians(pad.get("angle", 0.0))
        steep = np.zeros_like(h)
        for side in walls:
            if side == "south":
                steep = np.maximum(steep, geom.smoothstep(pad["size"][1] * 0.5 - 1.0, pad["size"][1] * 0.5, lz))
            elif side == "north":
                steep = np.maximum(steep, geom.smoothstep(-pad["size"][1] * 0.5 + 1.0, -pad["size"][1] * 0.5, lz))
            elif side == "west":
                steep = np.maximum(steep, geom.smoothstep(-pad["size"][0] * 0.5 + 1.0, -pad["size"][0] * 0.5, lx))
            elif side == "east":
                steep = np.maximum(steep, geom.smoothstep(pad["size"][0] * 0.5 - 1.0, pad["size"][0] * 0.5, lx))
        k_wall = geom.smoothstep(0.35, 0.0, sdf)
        k = k_wall * steep + k * (1.0 - steep)
    return h * (1.0 - k) + target * k, sdf


def apply_steps(h, X, Z, st):
    a = np.asarray(st["from"], np.float64)
    b = np.asarray(st["to"], np.float64)
    ha = sample_point(h, X, Z, a)
    hb = sample_point(h, X, Z, b)
    ab = b - a
    L = np.hypot(*ab)
    t = ((X - a[0]) * ab[0] + (Z - a[1]) * ab[1]) / (L * L)
    side = np.abs((X - a[0]) * ab[1] - (Z - a[1]) * ab[0]) / L
    inside = (t >= -0.05) & (t <= 1.05) & (side <= st["width"] * 0.5 + 0.3)
    ramp = ha + (hb - ha) * np.clip(t, 0, 1)
    return np.where(inside, ramp, h), (ha, hb)


def sample_point(h, X, Z, p):
    cell = X[0, 1] - X[0, 0]
    return float(ndimage.map_coordinates(h, [[(p[1] - Z[0, 0]) / cell], [(p[0] - X[0, 0]) / cell]], order=1, mode="nearest")[0])


def terraces(h, X, Z, T, seed=0):
    """Rice terraces on the gentle bench: the smoothed land is quantised into flat paddies whose
    edges follow its contour lines (so every paddy has its own organic outline), joined by short
    earthen banks. Returns heights and the paddy mask (1 on the flat water surfaces)."""
    sdf = geom.polygon_sdf(X, Z, T["poly"])
    sdf = sdf + (noise.fbm(X / 9.0, Z / 9.0, 3, seed) - 0.5) * 5.0
    k = geom.smoothstep(T["feather"], -T["feather"], sdf)
    hs = ndimage.gaussian_filter(h, 6.0)
    step = T["step"]
    q = hs / step
    lvl = np.floor(q)
    f = q - lvl
    bankf = T["bank"] / step * 0.35
    # flat until close to the next level, then a short bank up to it
    ramp = geom.smoothstep(1.0 - bankf, 1.0, f)
    ht = (lvl + ramp) * step
    out = h * (1.0 - k) + ht * k
    paddy = (k > 0.85) & (f < 1.0 - bankf - 0.06) & (sdf < -2.0)
    return out, paddy.astype(np.float64), lvl


def carve_stream(h, X, Z, S, cell):
    P = geom.catmull(np.asarray(S["points"], np.float64), 8)
    hs = ndimage.gaussian_filter(h, 2.0)
    floor = ndimage.map_coordinates(hs, [(P[:, 1] - Z[0, 0]) / cell, (P[:, 0] - X[0, 0]) / cell], order=1, mode="nearest")
    # monotonic downstream
    for i in range(1, len(floor)):
        floor[i] = min(floor[i], floor[i - 1] - 0.005)
    d, arc, fl = geom.polyline_field(X, Z, P, floor)
    w = S["width"] * 0.5
    wob = (noise.fbm(arc / 3.0, 0.0 * arc + 3.0, 2, 5) - 0.5) * 0.4
    hw = w + wob
    bed = fl - S["depth"] * geom.smoothstep(hw + 0.5, 0.0, d) ** 0.7
    k = geom.smoothstep(hw + 1.6, hw - 0.1, d)
    out = np.minimum(h, h * (1.0 - k) + bed * k)
    surface = fl - S["depth"] * 0.45
    return out, d, surface, P, floor


def spring_pool(h, X, Z, SP, seed=0):
    c = np.asarray(SP["centre"], np.float64)
    rx, rz = SP["radius"]
    wx, wz = noise.warp(X, Z, 3.0, 0.5, seed)
    e = np.hypot((wx - c[0]) / rx, (wz - c[1]) / rz)
    rim = sample_point(h, X, Z, c)
    basin = rim - SP["depth"] * (1.0 - np.clip(e, 0, 1) ** 2)
    out = np.where(e < 1.0, np.minimum(h, basin), h)
    # the rock face behind it: the bank steepens into bare rock for rock_height metres
    F = np.asarray(SP["rock_face"], np.float64)
    d, arc, _ = geom.polyline_field(X, Z, geom.catmull(F, 6))
    north = Z < np.interp(X, F[:, 0], F[:, 1])
    lift = SP["rock_height"] * geom.smoothstep(0.4, 1.3, d) * geom.smoothstep(4.0, 1.0, d)
    face = np.where(north, lift, 0.0)
    out = out + face * geom.smoothstep(F[0, 0] - 1.0, F[0, 0] + 2.0, X) * geom.smoothstep(F[-1, 0] + 1.0, F[-1, 0] - 2.0, X)
    surface = rim - 0.1
    return out, e, surface


def kiln(h, X, Z, K):
    c = np.asarray(K["centre"], np.float64)
    d = np.hypot(X - c[0], Z - c[1])
    base_h = sample_point(h, X, Z, c)
    dome = base_h + K["height"] * np.sqrt(np.clip(1.0 - (d / K["radius"]) ** 2, 0.0, 1.0))
    return np.maximum(h, np.where(d < K["radius"], dome, -1e9)), d
