"""A z-buffered multi-channel canvas and the primitives that draw into it.

Every primitive turns into fragments (pixel, depth, normal, attributes); `Canvas.write` keeps the
nearest fragment per pixel. Depth is D = Y + Z in metres (larger = nearer the camera). Normals are
stored in camera space (x right, y screen-up, z toward the viewer).

Fields kept per pixel:
  depth   float  nearest depth, -inf where empty
  n       3x float camera-space geometric normal
  wpos    3x float world position of the visible surface (metres)
  part    uint8  PART_* (what the pixel is)
  mat     uint8  material id (picks a colour ramp in the painter)
  cell    int32  leaf cluster id (-1 if none)
  mass    int32  foliage mass id (-1 if none)
  u, v    float  surface coordinates (bark: metres along the branch, angle around it)
  tone    float  free per-primitive shading bias (painters add to it)
"""
import math

import numpy as np

from .core import KZ, PPM, SQ2, normalize, world_to_cam

PART_NONE, PART_TRUNK, PART_LIMB, PART_LEAF, PART_CORE, PART_ROOT, PART_GROUND, PART_DETAIL, PART_INNER, PART_BLADE = range(10)


class Canvas:
    def __init__(self, W, H, ax, ay):
        self.W, self.H = int(W), int(H)
        self.ax, self.ay = float(ax), float(ay)
        H, W = self.H, self.W
        self.depth = np.full((H, W), -np.inf)
        self.n = np.zeros((H, W, 3))
        self.wpos = np.zeros((H, W, 3))
        self.part = np.zeros((H, W), np.uint8)
        self.mat = np.zeros((H, W), np.uint8)
        self.cell = np.full((H, W), -1, np.int32)
        self.mass = np.full((H, W), -1, np.int32)
        self.u = np.zeros((H, W))
        self.v = np.zeros((H, W))
        self.tone = np.zeros((H, W))
        self.extra = {}

    # ---- projection helpers
    def to_screen(self, P):
        P = np.asarray(P, dtype=np.float64)
        return self.ax + P[..., 0] * PPM, self.ay + (P[..., 2] - P[..., 1]) * PPM

    def pixel_world(self, px, py, D):
        X = (px + 0.5 - self.ax) / PPM
        S = (py + 0.5 - self.ay) / PPM
        Y = (D - S) / 2
        Z = (D + S) / 2
        return np.stack([X, Y, Z], axis=-1)

    @property
    def filled(self):
        return np.isfinite(self.depth)

    # ---- fragment resolve + z-test
    def write(self, ys, xs, D, fields, test=True):
        """Write fragments; keeps the nearest per pixel (within the batch and against the canvas).
        fields: dict name -> array (len N) or (N, 3); names are canvas attributes."""
        ys = np.asarray(ys).ravel().astype(np.int64)
        xs = np.asarray(xs).ravel().astype(np.int64)
        D = np.asarray(D, dtype=np.float64).ravel()
        if ys.size == 0:
            return np.zeros(0, bool)
        ok = (xs >= 0) & (ys >= 0) & (xs < self.W) & (ys < self.H) & np.isfinite(D)
        idx = np.nonzero(ok)[0]
        if idx.size == 0:
            return np.zeros(0, bool)
        pix = ys[idx] * self.W + xs[idx]
        order = np.lexsort((D[idx], pix))            # by pixel, then depth ascending
        ps = pix[order]
        last = np.r_[ps[1:] != ps[:-1], True]        # nearest fragment of each pixel
        win = idx[order[last]]
        wp = ps[last]
        if test:
            keep = D[win] > self.depth.ravel()[wp]
            win, wp = win[keep], wp[keep]
        self.depth.ravel()[wp] = D[win]
        for name, arr in fields.items():
            a = np.asarray(arr)
            tgt = self.extra[name] if name in self.extra else getattr(self, name)
            if tgt.ndim == 3:
                tgt.reshape(-1, 3)[wp] = a if a.ndim <= 1 and a.size in (1, 3) and len(D) != a.size else a.reshape(-1, 3)[win]
            else:
                tgt.ravel()[wp] = a if a.ndim == 0 else a.ravel()[win]
        return wp

    def add_extra(self, name, fill=0.0, dtype=np.float64):
        self.extra[name] = np.full((self.H, self.W), fill, dtype)
        setattr(self, name, self.extra[name])


# ------------------------------------------------------------------ ellipsoids (analytic)
def ellipsoids(cv, C, R, part, mat, cell=None, mass=None, tone=None, chunk=1500, dmul=None, bumps=None,
               nkz=1.0, mask=None):
    """Axis-aligned ellipsoids. C, R: (N, 3) world centres and radii (metres).
    Returns nothing; writes the visible front surfaces. dmul: optional (N,) depth bias (metres).
    bumps: optional (N, 3) = (count, amplitude, phase): the outline is scalloped by scaling the
    ellipsoid per pixel with 1 + a*max(0, cos(k*theta + phase))**0.7 (leaf clumps, not bubbles)."""
    C = np.atleast_2d(np.asarray(C, dtype=np.float64))
    R = np.atleast_2d(np.asarray(R, dtype=np.float64))
    N = len(C)
    cell = np.full(N, -1) if cell is None else np.broadcast_to(np.asarray(cell), (N,))
    mass = np.full(N, -1) if mass is None else np.broadcast_to(np.asarray(mass), (N,))
    tone = np.zeros(N) if tone is None else np.broadcast_to(np.asarray(tone, dtype=np.float64), (N,))
    part = np.broadcast_to(np.asarray(part), (N,))
    mat = np.broadcast_to(np.asarray(mat), (N,))
    dmul = np.zeros(N) if dmul is None else np.broadcast_to(np.asarray(dmul, dtype=np.float64), (N,))
    bumps = np.zeros((N, 4)) if bumps is None else np.asarray(bumps, dtype=np.float64)
    if bumps.shape[1] == 3:
        bumps = np.concatenate([bumps, np.full((N, 1), 0.7)], axis=1)
    # sort by size so chunks share similar bounding boxes
    order = np.argsort(R[:, 0] + R[:, 1] + R[:, 2])
    for s in range(0, N, chunk):
        sel = order[s:s + chunk]
        _ellipsoid_chunk(cv, C[sel], R[sel], part[sel], mat[sel], cell[sel], mass[sel], tone[sel], dmul[sel], bumps[sel],
                         nkz, mask)


def _ellipsoid_chunk(cv, C, R, part, mat, cell, mass, tone, dmul, bumps, nkz=1.0, mask=None):
    sx = cv.ax + C[:, 0] * PPM
    sy = cv.ay + (C[:, 2] - C[:, 1]) * PPM
    grow = 1 + bumps[:, 1]
    hx = R[:, 0] * PPM * grow
    hy = np.sqrt(R[:, 1] ** 2 + R[:, 2] ** 2) * PPM * grow
    bw = int(math.ceil(2 * hx.max())) + 3
    bh = int(math.ceil(2 * hy.max())) + 3
    x0 = np.floor(sx - hx - 1).astype(np.int64)
    y0 = np.floor(sy - hy - 1).astype(np.int64)
    gy, gx = np.mgrid[0:bh, 0:bw]
    px = x0[:, None, None] + gx[None]
    py = y0[:, None, None] + gy[None]
    X = (px + 0.5 - cv.ax) / PPM
    S = (py + 0.5 - cv.ay) / PPM
    cx, cy, cz = (C[:, i][:, None, None] for i in range(3))
    a, b, c = (R[:, i][:, None, None] for i in range(3))
    if np.any(bumps[:, 1] > 0):
        th = np.arctan2(py + 0.5 - sy[:, None, None], px + 0.5 - sx[:, None, None])
        k, amp, ph = (bumps[:, i][:, None, None] for i in range(3))
        pw = bumps[:, 3][:, None, None] if bumps.shape[1] > 3 else 0.7
        f = 1 + amp * np.maximum(0, np.cos(k * th + ph)) ** pw
        a, b, c = a * f, b * f, c * f
    u2 = ((X - cx) / a) ** 2
    k = S - cz
    A = 1 / b ** 2 + 1 / c ** 2
    B = -2 * cy / b ** 2 + 2 * k / c ** 2
    Cq = cy ** 2 / b ** 2 + k ** 2 / c ** 2 - 1 + u2
    disc = B * B - 4 * A * Cq
    m = disc >= 0
    Y = (-B + np.sqrt(np.maximum(disc, 0))) / (2 * A)
    Z = S + Y
    # nkz: the shape was compressed in depth for drawing; light it as the round natural shape
    nw = np.stack([(X - cx) / a ** 2, (Y - cy) / b ** 2, (Z - cz) / c ** 2 * nkz], axis=-1)
    nw = normalize(nw)
    D = Y + Z + dmul[:, None, None]
    if mask is not None:
        inside = (px >= 0) & (py >= 0) & (px < cv.W) & (py < cv.H)
        mm = np.zeros_like(m)
        mm[inside] = mask[py[inside], px[inside]]
        m &= mm
    ii = np.nonzero(m)
    n_c = world_to_cam(nw[ii])
    rep = lambda arr: np.broadcast_to(arr[:, None, None], m.shape)[ii]
    cv.write(py[ii], px[ii], D[ii], {
        'n': n_c,
        'wpos': np.stack([X[ii], Y[ii], Z[ii]], axis=-1),
        'part': rep(part), 'mat': rep(mat), 'cell': rep(cell), 'mass': rep(mass), 'tone': rep(tone),
    })


# ------------------------------------------------------------------ point splats (parametric surfaces)
def splat(cv, P, Nw, fields, test=True):
    """Project world points P (N, 3) with world normals Nw (N, 3) to single pixels; z-tested.
    Only points whose normal faces the camera are drawn (back faces would only lose the z-test)."""
    P = np.asarray(P, dtype=np.float64).reshape(-1, 3)
    Nc = world_to_cam(np.asarray(Nw, dtype=np.float64).reshape(-1, 3))
    front = (Nc[:, 2] > -0.05) & (P[:, 1] > -0.005)      # nothing below the ground plane
    P, Nc = P[front], Nc[front]
    fields = {k: (np.asarray(v)[front] if np.ndim(v) > 0 else v) for k, v in fields.items()}
    sx = cv.ax + P[:, 0] * PPM
    sy = cv.ay + (P[:, 2] - P[:, 1]) * PPM
    D = P[:, 1] + P[:, 2]
    fields = dict(fields)
    fields['n'] = Nc
    fields['wpos'] = P
    return cv.write(np.floor(sy), np.floor(sx), D, fields, test=test)


def frames_along(path):
    """Rotation-minimising frames along a polyline (N, 3): tangent, normal, binormal."""
    path = np.asarray(path, dtype=np.float64)
    T = np.gradient(path, axis=0)
    T = normalize(T)
    N = np.zeros_like(T)
    ref = np.array([0.0, 0.0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = ref - T[0] * np.dot(ref, T[0])
    N[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(T)):
        n = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        ln = np.linalg.norm(n)
        N[i] = n / ln if ln > 1e-9 else N[i - 1]
    Bn = np.cross(T, N)
    return T, N, Bn


def resample(path, step):
    """Resample a polyline at roughly uniform arc length `step` (metres); returns points and s."""
    path = np.asarray(path, dtype=np.float64)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    L = s[-1]
    n = max(2, int(math.ceil(L / step)) + 1)
    t = np.linspace(0, L, n)
    out = np.stack([np.interp(t, s, path[:, i]) for i in range(3)], axis=-1)
    return out, t


def tube(cv, path, radius, part, mat, mass=-1, tone=0.0, rfun=None, dens=2.6, u0=0.0, cap=True,
         cell=-1, extra=None, kz=KZ):
    """Swept tube along a world polyline. radius: scalar, (N,) per path point, or callable(s01).
    rfun(s_metres, theta, r) -> radius modulation (bark ridges, buttresses). Writes u = metres along
    the tube (from u0), v = angle around it (0 = facing the camera side), tone bias."""
    path = np.asarray(path, dtype=np.float64)
    pts, s = resample(path, 1.0 / (PPM * dens))
    L = max(s[-1], 1e-6)
    if callable(radius):
        r = np.array([radius(x / L) for x in s])
    else:
        rr = np.asarray(radius, dtype=np.float64)
        if rr.ndim == 0:
            r = np.full(len(s), float(rr))
        else:
            s_in = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
            r = np.interp(s, s_in, rr)
    T, Nn, Bn = frames_along(pts)
    rmax = r.max()
    na = max(10, int(math.ceil(2 * math.pi * rmax * PPM * dens)))
    th = np.linspace(0, 2 * math.pi, na, endpoint=False)
    cos, sin = np.cos(th)[None, :], np.sin(th)[None, :]
    R = r[:, None] * np.ones_like(cos)
    if rfun is not None:
        R = rfun(s[:, None] + u0 + 0 * cos, th[None, :] + 0 * R, R)
    dirs = Nn[:, None, :] * cos[..., None] + Bn[:, None, :] * sin[..., None]
    sq = np.array([1.0, 1.0, kz])                 # the cross-section's own depth is compressed
    P = pts[:, None, :] + dirs * R[..., None] * sq
    # normals: radial direction corrected for taper and modulation slope (approximate)
    dRds = np.gradient(R, axis=0) / max(1e-6, (s[1] - s[0]) if len(s) > 1 else 1)
    Nw = normalize(dirs - T[:, None, :] * dRds[..., None])
    if rfun is not None:   # tilt normals with the angular modulation, so ridges catch the light
        dRdt = np.gradient(R, axis=1) / (th[1] - th[0])
        tang = -Nn[:, None, :] * sin[..., None] + Bn[:, None, :] * cos[..., None]
        Nw = normalize(Nw - tang * (dRdt / np.maximum(R, 1e-6))[..., None])
    U = (s[:, None] + u0) * np.ones_like(cos)
    V = th[None, :] * np.ones_like(R)
    f = {'part': part, 'mat': mat, 'mass': mass, 'cell': cell, 'tone': tone,
         'u': U.ravel(), 'v': V.ravel()}
    if extra:
        f.update(extra)
    f = {k: (np.full(U.size, v) if np.ndim(v) == 0 else np.asarray(v).ravel()) for k, v in f.items()}
    splat(cv, P.reshape(-1, 3), Nw.reshape(-1, 3), f)
    if cap:   # round cap at the thin end, so a limb tip never shows an open ring
        e = pts[-1]
        rc = float(r[-1])
        if rc * PPM > 0.6:
            _sphere_splat(cv, e, rc, part, mat, mass, tone, s[-1] + u0, cell, kz)


def _sphere_splat(cv, c, r, part, mat, mass, tone, u, cell, kz=KZ):
    n = max(8, int(4 * math.pi * r * PPM * 2))
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    th = math.pi * (1 + 5 ** 0.5) * k
    d = np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], axis=-1)
    P = c[None, :] + d * r * np.array([1.0, 1.0, kz])
    f = {'part': np.full(n, part), 'mat': np.full(n, mat), 'mass': np.full(n, mass),
         'tone': np.full(n, tone), 'u': np.full(n, u), 'v': th % (2 * math.pi), 'cell': np.full(n, cell)}
    splat(cv, P, d, f)


# ------------------------------------------------------------------ flat 2D strokes (grass, petals)
def stroke2d(cv, x0, y0, x1, y1, w0, w1, D0, D1, n_cam, fields, test=True):
    """A tapered line in screen space at a given depth (metres) with a fixed camera normal.
    fields values may be scalars or callables(t, s) of the along/across parameters."""
    L = max(1e-6, math.hypot(x1 - x0, y1 - y0))
    dx, dy = (x1 - x0) / L, (y1 - y0) / L
    if max(w0, w1) <= 0.55:
        # a hair-thin stroke (thread, stamen, stalk): one pixel per step, a clean pixel-art line
        n = max(2, int(math.ceil(L * 2)) + 1)
        tt = np.linspace(0, 1, n)
        px = np.floor(x0 + (x1 - x0) * tt).astype(np.int64)
        py = np.floor(y0 + (y1 - y0) * tt).astype(np.int64)
        key = py * 100000 + px
        _, first = np.unique(key, return_index=True)
        first = np.sort(first)
        px, py, tt = px[first], py[first], tt[first]
        ss = np.zeros_like(tt)
        D = D0 + (D1 - D0) * tt
        f = {}
        for k, v in fields.items():
            f[k] = v(tt, ss) if callable(v) else (np.full(len(tt), v) if np.ndim(v) == 0 else np.broadcast_to(v, (len(tt),) + np.shape(v)))
        f['n'] = n_cam(tt, ss) if callable(n_cam) else np.broadcast_to(np.asarray(n_cam, dtype=np.float64), (len(tt), 3))
        cv.write(py, px, D, f, test=test)
        return
    wm = max(w0, w1)
    xa, xb = int(math.floor(min(x0, x1) - wm - 1)), int(math.ceil(max(x0, x1) + wm + 1))
    ya, yb = int(math.floor(min(y0, y1) - wm - 1)), int(math.ceil(max(y0, y1) + wm + 1))
    gy, gx = np.mgrid[ya:yb + 1, xa:xb + 1]
    qx, qy = gx + 0.5 - x0, gy + 0.5 - y0
    t = np.clip((qx * dx + qy * dy) / L, 0, 1)
    ex, ey = gx + 0.5 - (x0 + dx * t * L), gy + 0.5 - (y0 + dy * t * L)
    d = np.hypot(ex, ey)
    w = w0 + (w1 - w0) * t
    m = d <= w
    if not m.any():
        return
    s = (ex * -dy + ey * dx) / np.maximum(w, 0.01)
    ii = np.nonzero(m)
    tt, ss = t[ii], s[ii]
    D = D0 + (D1 - D0) * tt
    f = {}
    for k, v in fields.items():
        f[k] = v(tt, ss) if callable(v) else (np.full(len(tt), v) if np.ndim(v) == 0 else np.broadcast_to(v, (len(tt),) + np.shape(v)))
    nc = n_cam(tt, ss) if callable(n_cam) else np.broadcast_to(np.asarray(n_cam, dtype=np.float64), (len(tt), 3))
    f['n'] = nc
    cv.write(gy[ii], gx[ii], D, f, test=test)
