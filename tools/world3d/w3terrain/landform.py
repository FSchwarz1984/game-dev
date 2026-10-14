"""The designed landform: saddle, shoulders, south slope with the spur and the ravine, the north
flank, the gully and the far slope, plus multi-scale organic noise and erosion."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import geom, noise


def integrate_grades(d, knots):
    """Height drop over distance d for piecewise-linear grade knots [[d0, g0], ...] (smooth)."""
    k = np.asarray(knots, np.float64)
    xs = np.linspace(0.0, max(float(k[-1, 0]), float(np.max(d)) + 1.0), 4096)
    g = np.interp(xs, k[:, 0], k[:, 1])
    drop = np.concatenate([[0.0], np.cumsum((g[1:] + g[:-1]) * 0.5 * np.diff(xs))])
    return np.interp(d, xs, drop)


def base(L, X, Z):
    seed = int(L["seed"])
    r = L["ridge"]
    hw = float(r["half_width"])
    u = X / hw
    zr = r["z0"] + r["z_curve"] * u * u
    # the ridge undulates (two-dimensional noise, strongest on the shoulders)
    hr = r["h_curve"] * u * u + (noise.fbm(X / 37.0, Z / 53.0, 3, seed + 3) - 0.5) * 2.0 * (0.4 + 0.6 * np.abs(u))

    # south: grades steepen away from the crest; a gentler bench in the south-east hosts the paddies
    ds = np.maximum(Z - zr, 0.0)
    bench = L["gentle_bench"]
    sdf = geom.polygon_sdf(X, Z, bench["poly"])
    bench_k = 1.0 - geom.smoothstep(-bench["feather"], bench["feather"], sdf)
    drop_s = integrate_grades(ds, L["south_grades"])
    drop_s_g = integrate_grades(ds, [[d, g * bench["grade_scale"]] for d, g in L["south_grades"]])
    h_south = hr - (drop_s * (1.0 - bench_k) + drop_s_g * bench_k)

    # north: smooth terms only (no case splits, so no creases): the flank keeps falling north and
    # eases out; the far slope rises beyond the gully; the gully is carved where it exists
    n = L["north"]
    gl = np.asarray(n["gully_line"], np.float64)
    zg = np.interp(X, gl[:, 0], gl[:, 1]) + (noise.fbm(X / 21.0, Z / 40.0, 2, seed + 61) - 0.5) * 3.0
    dn = np.maximum(zr - Z, 0.0)
    fall = integrate_grades(dn, [[0, 0.04], [6, 0.12], [14, n["flank_grade"]], [40, 0.2], [70, 0.08], [140, 0.05]])
    rise = n["far_rise_max"] * geom.smoothstep(0.0, 1.0, np.clip(((zg - 3.0) - Z) / 48.0, 0.0, 1.0)) ** 1.25
    head = geom.smoothstep(-44.0, -30.0, X)              # the gully exists east of its head
    carve = n.get("gully_depth", 2.6) * head * np.exp(-((Z - zg) ** 2) / (2.0 * 4.5 ** 2))
    h_north = hr - fall + rise - carve

    t = geom.smoothstep(-1.5, 1.5, Z - zr)
    h = h_north * (1.0 - t) + h_south * t
    h = ndimage.gaussian_filter(h, 1.0)

    # organic noise at three scales, domain-warped so nothing lines up
    wx, wz = noise.warp(X, Z, 30.0, 9.0, seed + 11)
    nl = L["noise"]
    h += (noise.fbm(wx / nl["large"][0], wz / nl["large"][0], 4, seed + 21) - 0.5) * 2.0 * nl["large"][1]
    h += (noise.fbm(wx / nl["medium"][0], wz / nl["medium"][0], 3, seed + 31) - 0.5) * 2.0 * nl["medium"][1]
    h += (noise.fbm(X / nl["small"][0], Z / nl["small"][0], 2, seed + 41) - 0.5) * 2.0 * nl["small"][1]
    return h, zr, hr


def spur_and_ravine(L, X, Z, h):
    seed = int(L["seed"])
    sp = L["spur"]
    axis = np.asarray(sp["axis"], np.float64)
    crest = np.asarray(sp["crest"], np.float64)
    pts = geom.catmull(axis, 10)
    seg = np.hypot(*(np.diff(axis, axis=0).T))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    seg2 = np.hypot(*(np.diff(pts, axis=0).T))
    cum2 = np.concatenate([[0.0], np.cumsum(seg2)])
    crest2 = np.interp(cum2 / cum2[-1] * cum[-1], cum, crest)
    wx, wz = noise.warp(X, Z, 7.0, 1.6, seed + 71)
    d, arc, ch = geom.polyline_field(wx, wz, pts, crest2)
    # a broad promontory: a rounded crest, then rocky sides
    side = sp["side_grade"]
    half = sp.get("crest_half", 2.0)
    prof = ch - side * np.maximum(d - half, 0.0) - 0.12 * np.minimum(d, half) ** 2
    tip = pts[-1]
    beyond = arc >= cum2[-1] - 0.01
    dtip = np.hypot(wx - tip[0], wz - tip[1])
    prof = np.where(beyond, ch - 0.12 * np.minimum(dtip, half) ** 2 - side * 1.5 * np.maximum(dtip - half, 0.0), prof)
    near = geom.smoothstep(18.0, 9.0, d)
    h2 = geom.smax(h, prof, 1.8)
    h = h * (1.0 - near) + h2 * near

    # the ravine: an open valley that starts as a steep head scarp under the lookout and runs
    # down the slope, deepening, so water has somewhere to go
    rv = L["ravine"]
    ax = geom.catmull(np.asarray(rv["axis"], np.float64), 10)
    a_seg = np.hypot(*(np.diff(np.asarray(rv["axis"]), axis=0).T))
    a_cum = np.concatenate([[0.0], np.cumsum(a_seg)])
    ax_seg = np.hypot(*(np.diff(ax, axis=0).T))
    ax_cum = np.concatenate([[0.0], np.cumsum(ax_seg)])
    tt = ax_cum / ax_cum[-1] * a_cum[-1]
    dep = np.interp(tt, a_cum, rv["depth"])
    hwv = np.interp(tt, a_cum, rv["half_width"])
    wx2, wz2 = noise.warp(X, Z, 9.0, 2.2, seed + 79)
    dr, arc_r, vals = geom.polyline_field(wx2, wz2, ax, np.stack([dep, hwv], -1))
    depth = vals[..., 0]
    halfw = vals[..., 1]
    uu = np.clip(dr / halfw, 0.0, 1.0)
    fw = rv["floor_width"] * 0.5 / halfw
    prof_r = np.where(uu < fw, 1.0, (1.0 - ((uu - fw) / (1.0 - fw)) ** 2) ** 1.6)
    # the head: before the first vertex the valley closes in a steep, rounded scarp
    start = ax[0]
    ds = np.hypot(wx2 - start[0], wz2 - start[1])
    head = arc_r <= 0.01
    prof_r = np.where(head, np.clip(1.0 - ds / (halfw * 0.75), 0.0, 1.0) ** 1.3, prof_r)
    h = h - depth * prof_r
    return h


def erode(L, X, Z, h, cell, protect):
    """Stream-power incision along D8 flow plus hillslope diffusion; protect in [0, 1] blocks it."""
    er = L["erosion"]
    nz, nx = h.shape
    offs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    dist = np.array([np.hypot(a, b) * cell for a, b in offs])
    idx = np.arange(nx * nz).reshape(nz, nx)
    padi = np.pad(idx, 1, mode="edge")
    for _ in range(int(er["iterations"])):
        pad = np.pad(h, 1, mode="edge")
        best = np.zeros_like(h)
        rec = np.full(h.shape, -1, np.int64)
        for k, (dj, di) in enumerate(offs):
            nb = pad[1 + dj:1 + dj + nz, 1 + di:1 + di + nx]
            s = (h - nb) / dist[k]
            m = s > best
            best = np.where(m, s, best)
            rec = np.where(m, padi[1 + dj:1 + dj + nz, 1 + di:1 + di + nx], rec)
        order = np.argsort(-h, axis=None)
        acc = np.ones(nx * nz)
        recf = rec.ravel()
        for i in order:
            r = recf[i]
            if r >= 0:
                acc[r] += acc[i]
        A = acc.reshape(nz, nx) * cell * cell
        inc = er["k"] * np.power(A, er["m"]) * best
        inc = np.minimum(inc, 0.3) * (1.0 - protect)
        h = h - inc
        lap = ndimage.laplace(h)
        h = h + er["diffusion"] * lap * (1.0 - protect * 0.7)
    return h
