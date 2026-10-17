"""The heightfield of the village, from registry.terrain: a thin-plate spline through the control
points, then road benches, pads (with sharp edges where a stone wall stands), carves (the cutting, the
stream beds), cliffs and bumps. Slope, walkability and its causes come from the same grid."""
from __future__ import annotations

import math

import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import distance_transform_edt, gaussian_filter

from . import registry as reg


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Terrain:
    def __init__(self, R, cell=None, extent=None):
        self.R = R
        T = R["terrain"]
        self.cell = cell or T.get("cell", 0.5)
        x0, y0, x1, y1 = extent or R["coords"]["extent"]
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.xs = np.arange(x0, x1 + 1e-6, self.cell)
        self.ys = np.arange(y0, y1 + 1e-6, self.cell)
        self.X, self.Y = np.meshgrid(self.xs, self.ys)          # row 0 = south
        self.road_profiles = {}
        self._build()

    # ------------------------------------------------------------------------------------------------
    def _build(self):
        R = self.R
        T = R["terrain"]
        cp = np.asarray(T["control"], dtype=float)
        rbf = RBFInterpolator(cp[:, :2], cp[:, 2], kernel="thin_plate_spline", smoothing=2.0)
        pts = np.stack([self.X.ravel(), self.Y.ravel()], axis=1)
        H = rbf(pts).reshape(self.X.shape)
        H = gaussian_filter(H, 1.0)
        self.base = H.copy()
        # bumps
        for b in T.get("bumps", []):
            d = np.hypot(self.X - b["pos"][0], self.Y - b["pos"][1]) / b["r"]
            H += b["h"] * np.clip(1 - d * d, 0, 1) ** 2
        # road benches (the old road, the lane): a smoothed profile along the road, a flat floor, cut and fill
        for c in T.get("carves", []):
            if c["kind"] != "road":
                continue
            rd = R["_index"][c["ref"]]
            P, s = reg.resample(rd["pts"], 0.5)
            hp = self.sample(self.base, P[:, 0], P[:, 1])
            k = int(12.0 / 0.5)
            ker = np.ones(k) / k
            pad = np.pad(hp, (k // 2, k - k // 2 - 1), mode="edge")
            prof = np.convolve(pad, ker, mode="valid")
            self.road_profiles[rd["id"]] = (P, s, prof)
            H = self._bench(H, P, prof, c["floor_w"] / 2.0, c["bank"])
        # pads (later ones win); a wall edge makes the pad's edge a vertical step
        for pad in T.get("pads", []):
            H = self._pad(H, pad)
        # carves: the cutting, the stream beds
        for c in T.get("carves", []):
            if c["kind"] == "path":
                P, _ = reg.resample(c["pts"], 0.25)
                H = self._carve(H, P[:, :2], P[:, 2], c["floor_w"] / 2.0, c["bank"], steep=2.6)
            elif c["kind"] == "stream":
                w = R["_index"][c["ref"]]
                P, _ = reg.resample(w["pts"], 0.25)
                bed = P[:, 2] - 0.35
                H = self._carve(H, P[:, :2], bed, P[:, 3] / 2.0 + 0.1, 1.5, steep=1.3)
        for w in R.get("water", []):
            if w["id"] == "WA-STR-02":
                P, _ = reg.resample(w["pts"], 0.5)
                H = self._carve(H, P[:, :2], P[:, 2] - 0.4, P[:, 3] / 2.0 + 0.1, 2.0, steep=1.2)
        # cliffs: a sharp drop on the given side
        for c in T.get("cliffs", []):
            H = self._cliff(H, c)
        self.H = H
        gy, gx = np.gradient(H, self.cell)
        self.slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        self.gx, self.gy = gx, gy

    def _nearest(self, P, X, Y, radius):
        """Nearest resampled point index and distance for grid cells within `radius` of P."""
        from scipy.spatial import cKDTree
        tree = cKDTree(P)
        m = np.zeros(X.shape, dtype=bool)
        x0, y0 = P.min(axis=0) - radius
        x1, y1 = P.max(axis=0) + radius
        m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        q = np.stack([X[m], Y[m]], axis=1)
        d, i = tree.query(q, distance_upper_bound=radius)
        return m, d, i

    def _bench(self, H, P, prof, half, bank):
        m, d, i = self._nearest(P[:, :2], self.X, self.Y, half + bank)
        ok = np.isfinite(d)
        idx = np.where(m)
        sub = H[idx]
        tgt = prof[np.clip(i, 0, len(prof) - 1)]
        w = np.where(d <= half, 1.0, 1.0 - smoothstep((d - half) / bank))
        w = np.where(ok, w, 0.0)
        sub = sub * (1 - w) + tgt * w
        H[idx] = sub
        return H

    def _carve(self, H, P, hp, half, bank, steep=2.0):
        half = np.broadcast_to(np.asarray(half, dtype=float), (len(P),))
        m, d, i = self._nearest(P, self.X, self.Y, float(half.max()) + bank * 3)
        ok = np.isfinite(d)
        idx = np.where(m)
        sub = H[idx]
        ii = np.clip(i, 0, len(hp) - 1)
        tgt = hp[ii]
        hh = half[ii]
        lim = np.where(d <= hh, tgt, tgt + (d - hh) * steep)
        sub = np.where(ok, np.minimum(sub, lim), sub)
        H[idx] = sub
        return H

    def _pad(self, H, pad):
        poly = pad["poly"]
        inside = reg.points_in_poly(self.X, self.Y, poly)
        if isinstance(pad["h"], list):
            yr = pad.get("y_range")
            ys = np.asarray(poly)[:, 1]
            ya, yb = (yr if yr else (ys.min(), ys.max()))
            t = np.clip((self.Y - ya) / max(yb - ya, 1e-6), 0, 1)
            hv = pad["h"][0] + (pad["h"][1] - pad["h"][0]) * t       # h[0] at the south end
        else:
            hv = np.full(H.shape, float(pad["h"]))
        feather = pad.get("feather", 1.0)
        dist = distance_transform_edt(~inside) * self.cell
        w = np.where(inside, 1.0, 1.0 - smoothstep(dist / max(feather, 1e-6)))
        if feather <= 0:
            w = inside.astype(float)
        wall = pad.get("wall")
        if wall:
            if wall.get("edge") == "all":
                w = inside.astype(float)
            else:
                dw = reg.dist_to_polyline(self.X, self.Y, wall["edge"])
                w = np.where(~inside & (dw < feather + 0.6), 0.0, w)
        return H * (1 - w) + hv * w

    def _cliff(self, H, c):
        """A cliff along a polyline. The low side drops by `drop` at the face (width `w`) and fades back to
        the natural ground over `fade` metres (so no trench is left behind); `raise` lifts the high side
        at the face (for rock bands, where both sides are natural ground)."""
        P, _ = reg.resample(c["pts"], 0.25)
        w = c["w"]
        fade = c.get("fade", 2.5)
        rise = c.get("raise", 0.0)
        side, d = reg.signed_side(self.X, self.Y, P[:, :2])
        mid = len(P) // 2
        j0, j1 = max(mid - 1, 0), min(mid + 1, len(P) - 1)
        tx, ty = P[j1, 0] - P[j0, 0], P[j1, 1] - P[j0, 1]
        nx, ny = -ty, tx                                            # left normal
        want = {"S": (0, -1), "N": (0, 1), "E": (1, 0), "W": (-1, 0)}[c.get("side", "S")]
        low = 1 if (nx * want[0] + ny * want[1]) > 0 else -1
        reach = w + fade + 0.5
        top = self.sample(H, P[:, 0], P[:, 1])
        m, dd, i = self._nearest(P[:, :2], self.X, self.Y, reach)
        idx = np.where(m)
        ok = np.isfinite(dd)
        ii = np.clip(i, 0, len(top) - 1)
        topv = top[ii]
        sub = H[idx]
        sd = side[idx]
        # taper past the two ends of the line (a cliff stops; it does not reach round its own end)
        qx, qy = self.X[idx], self.Y[idx]
        t0 = P[1, :2] - P[0, :2]
        t0 = t0 / max(np.hypot(*t0), 1e-9)
        tn = P[-1, :2] - P[-2, :2]
        tn = tn / max(np.hypot(*tn), 1e-9)
        b0 = np.maximum(0.0, -((qx - P[0, 0]) * t0[0] + (qy - P[0, 1]) * t0[1]))
        bn = np.maximum(0.0, (qx - P[-1, 0]) * tn[0] + (qy - P[-1, 1]) * tn[1])
        endw = 1.0 - smoothstep(np.maximum(b0, bn) / 1.5)
        dd = np.where(endw <= 0, np.inf, dd)
        ok = ok & (endw > 0)
        # low side
        lim = topv - c["drop"] * smoothstep(dd / w) * endw
        back = smoothstep((dd - w) / max(fade, 1e-6))
        lim = lim + (sub - lim) * back
        lo = ok & (sd == low)
        sub = np.where(lo, np.minimum(sub, lim), sub)
        if rise > 0:
            up = topv + rise * smoothstep(dd / w) * endw
            up = up + (sub - up) * back
            hi = ok & (sd != low)
            sub = np.where(hi, np.maximum(sub, up), sub)
        H[idx] = sub
        return H

    # ------------------------------------------------------------------------------------------------
    def sample(self, A, x, y):
        """Bilinear sample of grid A at plan points."""
        fx = (np.asarray(x) - self.x0) / self.cell
        fy = (np.asarray(y) - self.y0) / self.cell
        ix = np.clip(np.floor(fx).astype(int), 0, A.shape[1] - 2)
        iy = np.clip(np.floor(fy).astype(int), 0, A.shape[0] - 2)
        tx = np.clip(fx - ix, 0, 1)
        ty = np.clip(fy - iy, 0, 1)
        a = A[iy, ix] * (1 - tx) + A[iy, ix + 1] * tx
        b = A[iy + 1, ix] * (1 - tx) + A[iy + 1, ix + 1] * tx
        return a * (1 - ty) + b * ty

    def h(self, x, y):
        return self.sample(self.H, x, y)

    def hillshade(self, az=225.0, alt=40.0):
        """Hillshade with the light from `az` (compass degrees the light comes from)."""
        a = math.radians(az)
        lx, ly = math.sin(a), math.cos(a)
        el = math.radians(alt)
        nx, ny, nz = -self.gx, -self.gy, np.ones_like(self.gx)
        n = np.sqrt(nx * nx + ny * ny + nz * nz)
        L = np.array([lx * math.cos(el), ly * math.cos(el), math.sin(el)])
        return np.clip((nx * L[0] + ny * L[1] + nz * L[2]) / n, 0, 1)
