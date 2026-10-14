"""Baked lighting data: sun horizon angles (for continuous cliff shadows) and
sky visibility (ambient occlusion).

The sun always comes from the upper left (west-north-west, fixed azimuth), so
for every pixel we store the elevation angle of the terrain horizon in that
direction. At run time a pixel is in sun when the sun's elevation is above
its horizon: shadows lengthen and shorten smoothly with the time of day and
can never jump (R-7). Units: metres, world x east, z south."""
import numpy as np

from .geom import PPM


def _schedule(max_m):
    s = list(range(1, 41)) + list(range(42, 121, 2)) + list(range(126, int(max_m * PPM) + 1, 6))
    return np.array(s, np.float32)


def horizon_world(world, toward_xz=(-0.92, 0.38), max_m=30.0):
    """Horizon elevation (degrees) toward the sun for every world cell."""
    h = np.nan_to_num(world.h, nan=world.void_h).astype(np.float32)
    H, W = h.shape
    d = np.asarray(toward_xz, np.float64)
    d = d / np.linalg.norm(d)
    best = np.zeros((H, W), np.float32)          # tan of the horizon angle
    for s in _schedule(max_m):
        ox = int(round(d[0] * s))
        oz = int(round(d[1] * s))
        # sample h at (z + oz, x + ox); outside the region there is nothing
        ys0, ys1 = max(0, -oz), min(H, H - oz)
        xs0, xs1 = max(0, -ox), min(W, W - ox)
        if ys1 <= ys0 or xs1 <= xs0:
            continue
        sub = h[ys0 + oz:ys1 + oz, xs0 + ox:xs1 + ox]
        t = (sub - h[ys0:ys1, xs0:xs1]) / (s / PPM)
        np.maximum(best[ys0:ys1, xs0:xs1], t, out=best[ys0:ys1, xs0:xs1])
    return np.degrees(np.arctan(best)).astype(np.float32)


def horizon_points(world, px, pz, ph, toward_xz=(-0.92, 0.38), max_m=30.0, start_px=1.0):
    """Horizon elevation (deg) for arbitrary points (world px coords, height m)."""
    h = np.nan_to_num(world.h, nan=world.void_h).astype(np.float32)
    H, W = h.shape
    d = np.asarray(toward_xz, np.float64)
    d = d / np.linalg.norm(d)
    best = np.zeros(len(px), np.float32)
    for s in _schedule(max_m):
        if s < start_px:
            continue
        qx = np.round(px + d[0] * s).astype(np.int64)
        qz = np.round(pz + d[1] * s).astype(np.int64)
        ok = (qx >= 0) & (qx < W) & (qz >= 0) & (qz < H)
        hh = np.full(len(px), -1e9, np.float32)
        hh[ok] = h[qz[ok], qx[ok]]
        t = (hh - ph) / (s / PPM)
        np.maximum(best, t, out=best)
    return np.degrees(np.arctan(np.maximum(best, 0))).astype(np.float32)


def sky_world(world, max_m=4.0, dirs=12):
    """Sky visibility of horizontal surfaces: mean over directions of cos^2 of
    the horizon elevation (cosine-weighted). 1 = open sky."""
    h = np.nan_to_num(world.h, nan=world.void_h).astype(np.float32)
    H, W = h.shape
    acc = np.zeros((H, W), np.float32)
    steps = [1, 2, 3, 5, 8, 12, 18, 26, 36, 50, 66, 80]
    steps = [s for s in steps if s <= max_m * PPM]
    for k in range(dirs):
        a = 2 * np.pi * k / dirs
        dx, dz = np.cos(a), np.sin(a)
        best = np.zeros((H, W), np.float32)
        for s in steps:
            ox, oz = int(round(dx * s)), int(round(dz * s))
            ys0, ys1 = max(0, -oz), min(H, H - oz)
            xs0, xs1 = max(0, -ox), min(W, W - ox)
            if ys1 <= ys0 or xs1 <= xs0:
                continue
            sub = h[ys0 + oz:ys1 + oz, xs0 + ox:xs1 + ox]
            t = (sub - h[ys0:ys1, xs0:xs1]) / (s / PPM)
            np.maximum(best[ys0:ys1, xs0:xs1], t, out=best[ys0:ys1, xs0:xs1])
        acc += 1.0 / (1.0 + best * best)            # cos^2(atan(t))
    return (acc / dirs).astype(np.float32)


def screen_light(S, world, SP, toward_xz=(-0.92, 0.38)):
    """Per screen pixel: horizon angle (deg) and sky visibility."""
    from .painter import KIND_TOP, KIND_FACE, KIND_SIDE
    Hs, W = S.kind.shape
    hz_w = horizon_world(world, toward_xz)
    sky_w = sky_world(world)
    world.horizon = hz_w
    world.sky = sky_w
    hor = np.full((Hs, W), 90.0, np.float32)
    sky = np.zeros((Hs, W), np.float32)
    tm = S.kind == KIND_TOP
    hor[tm] = hz_w.ravel()[S.src[tm]]
    sky[tm] = sky_w.ravel()[S.src[tm]]
    # faces and side strips: march from the pixel itself (just in front of the face)
    fm = (S.kind == KIND_FACE) | (S.kind == KIND_SIDE)
    fy, fx = np.nonzero(fm)
    src_dn = S.src_dn[fm]
    src_up = S.src[fm]
    has_dn = src_dn >= 0
    cell = np.where(has_dn, src_dn, src_up)
    pz = (cell // world.W).astype(np.float32) + np.where(has_dn, 0.0, 1.0)
    px = (cell % world.W).astype(np.float32)
    ph = S.hpx[fm] / PPM
    # start a few px in front of the face (along its smoothed normal), so the
    # pixel-scale raggedness of the edge cannot shadow its own face column by column
    from .mat_face import face_normals
    nxw, nzw = face_normals(world)
    nx = nxw.ravel()[src_up]
    nz = nzw.ravel()[src_up]
    px = px + nx * 4.0
    pz = pz + nz * 4.0
    hor[fm] = horizon_points(world, px, pz, ph, toward_xz, start_px=1.0)
    # vertical faces see half the sky; darker toward the foot
    rel = np.where(S.fd[fm] > 0, S.fk[fm] / np.maximum(S.fd[fm], 1), 0.5)
    sky[fm] = 0.62 - 0.22 * np.clip((rel - 0.45) / 0.55, 0, 1) ** 1.5
    return hor, sky
