"""Vector geometry -> rasters: splines, polygon fill, signed distance, organic
outlines and polyline distance fields. All rasters are world-space (x east,
z south) at PPM pixels per metre."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from . import noise

PPM = 20  # pixels per metre (the project scale: 1 m = 20 native px)


def catmull_rom(points, closed=True, step_px=4.0, alpha=0.5):
    """Centripetal Catmull-Rom through `points` (metres) -> dense polyline in metres.

    Centripetal parameterisation never loops or cusps, so a few hand-placed
    control points give a smooth, natural contour."""
    P = np.asarray(points, np.float64)
    n = len(P)
    if n < 3:
        return P.copy()
    if closed:
        segs = [(P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]) for i in range(n)]
    else:
        ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
        segs = [(ext[i], ext[i + 1], ext[i + 2], ext[i + 3]) for i in range(n - 1)]
    out = []
    for p0, p1, p2, p3 in segs:
        def tj(ti, a, b):
            return ti + max(np.linalg.norm(b - a), 1e-6) ** alpha
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        seg_len = np.linalg.norm(p2 - p1) * PPM
        m = max(2, int(np.ceil(seg_len / step_px)))
        t = np.linspace(t1, t2, m, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        c = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2
        out.append(c)
    if not closed:
        out.append(P[-1:])
    return np.vstack(out)


class Frame:
    """A world-space raster window: metres <-> pixels."""

    def __init__(self, x0, z0, x1, z1):
        self.x0, self.z0, self.x1, self.z1 = x0, z0, x1, z1
        self.W = int(round((x1 - x0) * PPM))
        self.H = int(round((z1 - z0) * PPM))
        self._grid = None

    def to_px(self, pts):
        P = np.asarray(pts, np.float64)
        return np.stack([(P[:, 0] - self.x0) * PPM, (P[:, 1] - self.z0) * PPM], 1)

    def grid(self):
        """World-pixel coordinates of pixel centres (absolute world px, float32)."""
        if self._grid is None:
            X, Y = noise.grid(self.H, self.W, self.x0 * PPM + 0.5, self.z0 * PPM + 0.5)
            self._grid = (X, Y)
        return self._grid


def fill_polygon(frame, pts_m):
    """Even-odd polygon fill (PIL) -> bool mask, pixel centres inside."""
    px = frame.to_px(pts_m)
    im = Image.new('L', (frame.W, frame.H), 0)
    ImageDraw.Draw(im).polygon([(float(x) - 0.5, float(y) - 0.5) for x, y in px], fill=255, outline=None)
    return np.asarray(im) > 127


def draw_polyline(frame, pts_m, width_px=1):
    px = frame.to_px(pts_m)
    im = Image.new('L', (frame.W, frame.H), 0)
    ImageDraw.Draw(im).line([(float(x) - 0.5, float(y) - 0.5) for x, y in px], fill=255, width=int(width_px))
    return np.asarray(im) > 127


def sdf(mask):
    """Signed distance in px: > 0 inside, < 0 outside (pixel-centre approx)."""
    inside = ndi.distance_transform_edt(mask)
    outside = ndi.distance_transform_edt(~mask)
    return (inside - outside + np.where(mask, -0.5, 0.5)).astype(np.float32)


def remove_specks(mask, min_px=24):
    """Drop tiny islands and fill tiny holes left by edge noise."""
    lab, n = ndi.label(mask)
    if n:
        sizes = ndi.sum(mask, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= min_px
        mask = keep[lab]
    lab, n = ndi.label(~mask)
    if n:
        sizes = ndi.sum(~mask, lab, range(1, n + 1))
        small = np.zeros(n + 1, bool)
        small[1:] = sizes < min_px
        mask = mask | small[lab]
    return mask


def organic_mask(frame, pts_m, edge, seed, damp=None, smooth=True, bbox_pad_m=4.0):
    """Closed contour -> natural outline mask.

    edge = {amp: m, wave: m, rough: m, bite: 0..1}
      amp/wave : the medium undulation (a few metres long);
      rough    : pixel-scale raggedness (sod clumps, chipped rock);
      bite     : occasional deeper notches (gullies) and bulges (outcrops).
    damp: optional float raster 0..1 multiplying the displacement (1 = full);
    used to straighten the outline where stairs and ramps attach.
    The raster is computed only in the contour's bounding box."""
    pts = catmull_rom(pts_m, closed=True) if smooth else np.asarray(pts_m, np.float64)
    amp = edge.get('amp', 0.45) * PPM
    wave = max(edge.get('wave', 5.0), 0.5) * PPM
    rough = edge.get('rough', 0.12) * PPM
    bite = edge.get('bite', 0.35)
    pad = bbox_pad_m + edge.get('amp', 0.45) * 2 + 1
    xs, zs = pts[:, 0], pts[:, 1]
    bx0 = max(frame.x0, xs.min() - pad)
    bz0 = max(frame.z0, zs.min() - pad)
    bx1 = min(frame.x1, xs.max() + pad)
    bz1 = min(frame.z1, zs.max() + pad)
    out = np.zeros((frame.H, frame.W), bool)
    if bx1 <= bx0 or bz1 <= bz0:
        return out
    i0 = int(np.floor((bz0 - frame.z0) * PPM))
    i1 = int(np.ceil((bz1 - frame.z0) * PPM))
    j0 = int(np.floor((bx0 - frame.x0) * PPM))
    j1 = int(np.ceil((bx1 - frame.x0) * PPM))
    sub = Frame(frame.x0 + j0 / PPM, frame.z0 + i0 / PPM, frame.x0 + j1 / PPM, frame.z0 + i1 / PPM)
    m = fill_polygon(sub, pts)
    d = sdf(m)
    reach = amp * 2.8 + rough * 2.0 + 3.0
    band = np.abs(d) < reach          # the displacement only matters near the contour
    X, Y = sub.grid()
    X = X[band]
    Y = Y[band]
    # character: some stretches of an edge are calm, others rugged
    ch = 0.45 + 0.9 * noise.fbm(X / (wave * 2.6) - 11.0, Y / (wave * 2.6) + 5.0, seed + 71, 2)
    # medium undulation: warped fbm so the wiggles are irregular in length
    wx, wy = noise.warp(X, Y, wave * 1.7, wave * 0.35, seed + 3)
    disp = (noise.fbm(wx / wave, wy / wave, seed, 3) - 0.5) * 2.0 * amp * ch
    # bites and bulges: sparse, larger; bulges round, bites sharper
    if bite > 0:
        b = noise.fbm(X / (wave * 0.8) + 40.0, Y / (wave * 0.8) - 7.0, seed + 29, 2)
        disp += np.clip((b - 0.62) * 6.0, 0, 1) ** 0.7 * bite * amp * 1.6
        disp -= np.clip((0.36 - b) * 6.0, 0, 1) ** 1.6 * bite * amp * 1.4
    # pixel-scale raggedness in small clumps (a few px wide), not salt-and-pepper
    disp += (noise.fbm(X / 3.1, Y / 3.1, seed + 51, 2) - 0.5) * 2.0 * rough * (0.6 + 0.5 * ch)
    if damp is not None:
        disp *= damp[i0:i1, j0:j1][band]
    dd = d.copy()
    dd[band] += disp
    m2 = remove_specks(dd > 0)
    out[i0:i1, j0:j1] = m2
    return out


def polyline_field(frame, pts_m, smooth=True, step_px=2.0, reach_m=6.0):
    """Distance (px) to a polyline, arc length (px) of the nearest point and the
    signed side, for every pixel within `reach_m` of the line's bounding box
    (dist = 1e6 elsewhere). Returns (dist, along, side, total_len_px)."""
    P = catmull_rom(pts_m, closed=False, step_px=step_px) if (smooth and len(pts_m) > 2) else np.asarray(pts_m, np.float64)
    H, W = frame.H, frame.W
    px = frame.to_px(P)
    j0 = max(0, int(np.floor(px[:, 0].min() - reach_m * PPM)))
    j1 = min(W, int(np.ceil(px[:, 0].max() + reach_m * PPM)))
    i0 = max(0, int(np.floor(px[:, 1].min() - reach_m * PPM)))
    i1 = min(H, int(np.ceil(px[:, 1].max() + reach_m * PPM)))
    dist_full = np.full((H, W), 1e6, np.float32)
    along_full = np.zeros((H, W), np.float32)
    side_full = np.zeros((H, W), np.float32)
    if j1 <= j0 or i1 <= i0:
        return dist_full, along_full, side_full, 0.0
    # densify to <= 0.7 px spacing so the nearest-pixel transform is exact enough
    seg = np.diff(px, axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    dense = [px[:1]]
    for i in range(len(seg)):
        k = max(1, int(np.ceil(L[i] / 0.7)))
        t = np.arange(1, k + 1)[:, None] / k
        dense.append(px[i] + seg[i] * t)
    D = np.vstack(dense)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(D, axis=0).T))])
    tg = np.gradient(D, axis=0)
    tg /= np.maximum(np.hypot(tg[:, 0], tg[:, 1]), 1e-6)[:, None]
    h, w = i1 - i0, j1 - j0
    ix = np.round(D[:, 0] - 0.5).astype(int) - j0
    iy = np.round(D[:, 1] - 0.5).astype(int) - i0
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    ix, iy, s_ok, tg_ok = ix[ok], iy[ok], s[ok], tg[ok]
    feat = np.ones((h, w), bool)
    feat[iy, ix] = False
    along_img = np.zeros((h, w), np.float32)
    tx_img = np.zeros((h, w), np.float32)
    ty_img = np.zeros((h, w), np.float32)
    along_img[iy, ix] = s_ok
    tx_img[iy, ix] = tg_ok[:, 0]
    ty_img[iy, ix] = tg_ok[:, 1]
    dist, (ni, nj) = ndi.distance_transform_edt(feat, return_indices=True)
    yy, xx = np.indices((h, w))
    rx = xx - nj
    ry = yy - ni
    dist_full[i0:i1, j0:j1] = dist
    along_full[i0:i1, j0:j1] = along_img[ni, nj]
    side_full[i0:i1, j0:j1] = np.sign(tx_img[ni, nj] * ry - ty_img[ni, nj] * rx)
    return dist_full, along_full, side_full, float(s[-1])


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
