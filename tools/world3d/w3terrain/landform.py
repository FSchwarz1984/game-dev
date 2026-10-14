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
    # the ridge itself undulates a little (it is not a parabola)
    hr = r["h_curve"] * u * u + (noise.fbm(X / 37.0, 0.5, 3, seed + 3) - 0.5) * 2.2

    # south: grades steepen away from the crest; a gentler bench in the south-east hosts the paddies
    ds = np.maximum(Z - zr, 0.0)
    bench = L["gentle_bench"]
    sdf = geom.polygon_sdf(X, Z, bench["poly"])
    bench_k = 1.0 - geom.smoothstep(-bench["feather"], bench["feather"], sdf)
    drop_s = integrate_grades(ds, L["south_grades"])
    drop_s_g = integrate_grades(ds, [[d, g * bench["grade_scale"]] for d, g in L["south_grades"]])
    h_south = hr - (drop_s * (1.0 - bench_k) + drop_s_g * bench_k)

    # north: the saddle's north flank falls into the gully; beyond it the far slope rises
    n = L["north"]
    gl = np.asarray(n["gully_line"], np.float64)
    gf = np.asarray(n["gully_floor"], np.float64)
    zg = np.interp(X, gl[:, 0], gl[:, 1])
    gfloor = np.interp(X, gf[:, 0], gf[:, 1])
    # the gully head: west of the spring the floor climbs back onto the slope
    gfloor = gfloor + np.maximum(0.0, -32.0 - X) * 0.45
    dn = np.maximum(zr - Z, 0.0)
    flank = hr - integrate_grades(dn, [[0, 0.04], [6, 0.12], [14, n["flank_grade"]], [60, n["flank_grade"]]])
    dz = Z - zg                                  # < 0 north of the gully line
    w = n["gully_floor_width"] * 0.5
    a = np.abs(dz)
    bankp = np.where(a < w, 0.0, np.where(a < w + 3.0, 0.5 * (a - w) ** 2 / 3.0 * 0.55, 0.5 * 3.0 * 0.55 + 0.55 * (a - w - 3.0)))
    # far side: climbs, then eases toward the north ridge
    far = np.where(dz < 0, np.minimum(bankp, n["far_rise_max"] * np.tanh(bankp / n["far_rise_max"]) * 1.0), bankp)
    h_gully = gfloor + far
    h_north = np.where(dz >= 0, geom.smin(flank, h_gully, 2.5), h_gully)
    t = geom.smoothstep(-2.0, 2.0, Z - zr)
    h = h_north * (1.0 - t) + h_south * t

    # organic noise at three scales, domain-warped so nothing lines up
    wx, wz = noise.warp(X, Z, 30.0, 9.0, seed + 11)
    nl = L["noise"]
    h += (noise.fbm(wx / nl["large"][0], wz / nl["large"][0], 4, seed + 21) - 0.5) * 2.0 * nl["large"][1]
    h += (noise.fbm(wx / nl["medium"][0], wz / nl["medium"][0], 3, seed + 31) - 0.5) * 2.0 * nl["medium"][1]
    h += (noise.fbm(X / nl["small"][0], Z / nl["small"][0], 2, seed + 41) - 0.5) * 2.0 * nl["small"][1]
    return h, zr, hr


def spur_and_ravine(L, X, Z, h):
    sp = L["spur"]
    axis = np.asarray(sp["axis"], np.float64)
    crest = np.asarray(sp["crest"], np.float64)
    pts = geom.catmull(axis, 10)
    # crest heights along the smoothed axis (interpolate by nearest original vertex arc)
    _, s_raw = geom.resample_polyline(axis, 0.5)
    seg = np.hypot(*(np.diff(axis, axis=0).T))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    seg2 = np.hypot(*(np.diff(pts, axis=0).T))
    cum2 = np.concatenate([[0.0], np.cumsum(seg2)])
    crest2 = np.interp(cum2 / cum2[-1] * cum[-1], cum, crest)
    d, arc, ch = geom.polyline_field(X, Z, pts, crest2)
    # a rounded ridge: flat-ish crest, rocky sides
    side = sp["side_grade"]
    prof = ch - side * np.maximum(d - 1.2, 0.0) - 0.15 * np.minimum(d, 1.2) ** 2
    # beyond the tip the spur ends in a drop (the ravine head takes over)
    tip = pts[-1]
    beyond = arc >= cum2[-1] - 0.01
    dtip = np.hypot(X - tip[0], Z - tip[1])
    prof = np.where(beyond, ch - side * 1.6 * np.maximum(dtip - 1.0, 0.0), prof)
    near = geom.smoothstep(16.0, 8.0, d)
    h2 = geom.smax(h, prof, 1.6)
    h = h * (1.0 - near) + h2 * near

    rv = L["ravine"]
    c = np.asarray(rv["centre"], np.float64)
    rx, rz = rv["radius"]
    wx, wz = noise.warp(X, Z, 14.0, 3.0, int(L["seed"]) + 77)
    e = np.hypot((wx - c[0]) / rx, (wz - c[1]) / rz)          # 1 at the rim of the floor ellipse
    out_m = np.maximum(e - 1.0, 0.0) * (rx + rz) * 0.5
    h_rav = rv["floor"] + rv["wall_grade"] * out_m + 0.08 * (out_m ** 1.5)
    h = geom.smin(h, h_rav, 2.5)
    return h


def erode(L, X, Z, h, cell, protect):
    """Stream-power incision along D8 flow plus hillslope diffusion; protect in [0, 1] blocks it."""
    er = L["erosion"]
    nz, nx = h.shape
    offs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    dist = np.array([np.hypot(a, b) * cell for a, b in offs])
    for _ in range(int(er["iterations"])):
        # D8 receivers
        pad = np.pad(h, 1, mode="edge")
        best = np.zeros_like(h)
        rec = np.full(h.shape, -1, np.int64)
        idx = np.arange(nx * nz).reshape(nz, nx)
        padi = np.pad(idx, 1, mode="edge")
        for k, (dj, di) in enumerate(offs):
            nb = pad[1 + dj:1 + dj + nz, 1 + di:1 + di + nx]
            s = (h - nb) / dist[k]
            m = s > best
            best = np.where(m, s, best)
            rec = np.where(m, padi[1 + dj:1 + dj + nz, 1 + di:1 + di + nx], rec)
        # flow accumulation in descending height order
        order = np.argsort(-h, axis=None)
        acc = np.ones(nx * nz)
        recf = rec.ravel()
        for i in order:
            r = recf[i]
            if r >= 0:
                acc[r] += acc[i]
        A = acc.reshape(nz, nx) * cell * cell
        inc = er["k"] * np.power(A, er["m"]) * best
        inc = np.minimum(inc, 0.35) * (1.0 - protect)
        h = h - inc
        # hillslope diffusion (keeps the rills soft, never V-cut)
        lap = ndimage.laplace(h)
        h = h + er["diffusion"] * lap * (1.0 - protect * 0.7)
    return h
