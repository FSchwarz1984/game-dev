"""Signed-distance solids in prop-local world coordinates (metres; x east, y up, z south).

A Solid knows its distance function, its world bounding box, its material and the sprite layer
('part') it is drawn into. Solids are rendered one at a time by sphere tracing along the oblique
view ray (render.py) and combined in a z-buffer, so a prop is a list of solids. Combinators (Diff,
SmoothUnion, Displace) build one solid out of several when shapes must blend or cut.

Every solid may carry a rotation R (3x3, columns = its local axes in world coordinates) and a
position: local = (P - pos) @ R. Materials receive the local coordinates.
"""
import math

import numpy as np

from .core import fbm3, normalize


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotation matrix, columns = local axes in world coords. yaw about +y (degrees, x toward -z),
    then pitch about the local x axis, then roll about the local z axis."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def axes(x_axis, y_axis=None):
    """Rotation from a local x axis (and an approximate local y axis) given in world coords."""
    x = normalize(np.asarray(x_axis, np.float64))
    y = np.asarray(y_axis if y_axis is not None else (0.0, 1.0, 0.0), np.float64)
    if abs(np.dot(x, normalize(y))) > 0.98:
        y = np.array([0.0, 0.0, 1.0])
    z = normalize(np.cross(x, y))
    y = np.cross(z, x)
    return np.stack([x, y, z], axis=1)


class Solid:
    """Base class. Subclasses implement _d(Q) on local coords Q (N, 3) and _lbox() (local AABB)."""
    lipschitz = 1.0

    def __init__(self, mat=None, part='body', pos=(0.0, 0.0, 0.0), R=None, tag=None, data=None):
        self.mat = mat
        self.part = part
        self.pos = np.asarray(pos, np.float64)
        self.R = np.eye(3) if R is None else np.asarray(R, np.float64)
        self.tag = tag
        self.data = data or {}

    def local(self, P):
        return (np.asarray(P, np.float64) - self.pos) @ self.R

    def to_world(self, Q):
        return np.asarray(Q, np.float64) @ self.R.T + self.pos

    def sdf(self, P):
        return self._d(self.local(P))

    def bbox(self):
        lo, hi = self._lbox()
        cs = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        w = self.to_world(cs)
        return w.min(0), w.max(0)

    def _lbox(self):
        raise NotImplementedError


class Box(Solid):
    """Axis box with half sizes `half` (local), corner rounding r."""

    def __init__(self, half, r=0.0, **kw):
        super().__init__(**kw)
        self.half = np.asarray(half, np.float64)
        self.r = float(r)

    def _d(self, Q):
        q = np.abs(Q) - self.half + self.r
        out = np.linalg.norm(np.maximum(q, 0.0), axis=-1) + np.minimum(q.max(-1), 0.0)
        return out - self.r

    def _lbox(self):
        return -self.half, self.half


class Cyl(Solid):
    """Vertical (local y) elliptic cylinder from y0 to y1, radii rx (x) and rz (z), edge rounding r."""

    def __init__(self, rx, y0, y1, rz=None, r=0.0, **kw):
        super().__init__(**kw)
        self.rx = float(rx)
        self.rz = float(rz if rz is not None else rx)
        self.y0, self.y1 = float(y0), float(y1)
        self.r = float(r)

    def _d(self, Q):
        m = min(self.rx, self.rz)
        rad = (np.hypot(Q[:, 0] / self.rx, Q[:, 2] / self.rz) - 1.0) * m
        hy = (self.y1 - self.y0) / 2
        cy = (self.y1 + self.y0) / 2
        dy = np.abs(Q[:, 1] - cy) - hy
        a = rad + self.r
        b = dy + self.r
        out = np.minimum(np.maximum(a, b), 0.0) + np.hypot(np.maximum(a, 0.0), np.maximum(b, 0.0))
        return out - self.r

    def _lbox(self):
        return np.array([-self.rx, self.y0, -self.rz]), np.array([self.rx, self.y1, self.rz])


class Cone(Solid):
    """Vertical frustum: radius r0 at y0, r1 at y1 (elliptic in z by kz)."""

    def __init__(self, r0, r1, y0, y1, kz=1.0, **kw):
        super().__init__(**kw)
        self.r0, self.r1 = float(r0), float(r1)
        self.y0, self.y1 = float(y0), float(y1)
        self.kz = float(kz)

    def _d(self, Q):
        x = np.hypot(Q[:, 0], Q[:, 2] / self.kz)
        y = Q[:, 1]
        h = self.y1 - self.y0
        # 2D distance to the trapezoid (x >= 0) with corners (0,y0) (r0,y0) (r1,y1) (0,y1)
        k = (y - self.y0) / h
        rr = self.r0 + (self.r1 - self.r0) * np.clip(k, 0, 1)
        dx = x - rr
        slope = (self.r1 - self.r0) / h
        dside = dx / math.sqrt(1 + slope * slope)
        dcap = np.maximum(self.y0 - y, y - self.y1)
        inside = np.maximum(dside, dcap)
        out = np.where((dside > 0) & (dcap > 0), np.hypot(dside, dcap), inside)
        return out * min(1.0, self.kz)

    def _lbox(self):
        r = max(self.r0, self.r1)
        return np.array([-r, self.y0, -r * self.kz]), np.array([r, self.y1, r * self.kz])


class Capsule(Solid):
    """Segment a-b (world coords, before pos/R) with radius r (r1 at b: tapered)."""

    def __init__(self, a, b, r, r1=None, **kw):
        super().__init__(**kw)
        self.a = np.asarray(a, np.float64)
        self.b = np.asarray(b, np.float64)
        self.r0 = float(r)
        self.r1 = float(r1 if r1 is not None else r)

    def _d(self, Q):
        ba = self.b - self.a
        pa = Q - self.a
        h = np.clip((pa @ ba) / max(ba @ ba, 1e-12), 0.0, 1.0)
        rr = self.r0 + (self.r1 - self.r0) * h
        return np.linalg.norm(pa - h[:, None] * ba, axis=-1) - rr

    def axial(self, P):
        """(h along the segment 0..1, angle around it, distance from the axis) for materials."""
        Q = self.local(P)
        ba = self.b - self.a
        L = np.linalg.norm(ba)
        t = ba / max(L, 1e-12)
        pa = Q - self.a
        h = (pa @ t) / max(L, 1e-12)
        radial = pa - (pa @ t)[:, None] * t
        ref = np.array([0.0, 1.0, 0.0]) if abs(t[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = normalize(ref - (ref @ t) * t)
        e2 = np.cross(t, e1)
        ang = np.arctan2(radial @ e2, radial @ e1)
        return h, ang, np.linalg.norm(radial, axis=-1)

    def _lbox(self):
        r = max(self.r0, self.r1)
        return np.minimum(self.a, self.b) - r, np.maximum(self.a, self.b) + r


class Ellipsoid(Solid):
    def __init__(self, radii, **kw):
        super().__init__(**kw)
        self.radii = np.asarray(radii, np.float64)

    def _d(self, Q):
        k0 = np.linalg.norm(Q / self.radii, axis=-1)
        k1 = np.linalg.norm(Q / (self.radii * self.radii), axis=-1)
        return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -self.radii.min())

    def _lbox(self):
        return -self.radii, self.radii


class Planes(Solid):
    """Convex polytope: intersection of half-spaces n . q <= d (local coords; n need not be unit)."""

    def __init__(self, planes, lbox, r=0.0, soft=0.0, **kw):
        super().__init__(**kw)
        self.N = np.array([normalize(np.asarray(p[0], np.float64)) for p in planes])
        self.D = np.array([p[1] / np.linalg.norm(p[0]) for p in planes])
        self.lb = (np.asarray(lbox[0], np.float64), np.asarray(lbox[1], np.float64))
        self.r = float(r)
        self.soft = float(soft)

    def _d(self, Q):
        e = Q @ self.N.T - self.D
        if self.soft <= 0:
            return e.max(-1) - self.r
        # smooth maximum: edges and corners rounded with a radius of about `soft`
        d = e[:, 0]
        k2 = self.soft * self.soft
        for i in range(1, e.shape[1]):
            f = e[:, i]
            d = 0.5 * (d + f + np.sqrt((d - f) ** 2 + k2))
        return d - self.r

    def _lbox(self):
        return self.lb


class Prism(Solid):
    """A straight extrusion of a convex 2D polygon (in the local x-y plane) along local z from z0 to z1."""

    def __init__(self, poly, z0, z1, r=0.0, **kw):
        super().__init__(**kw)
        self.poly = np.asarray(poly, np.float64)
        self.z0, self.z1 = float(z0), float(z1)
        self.r = float(r)
        P = self.poly
        n = len(P)
        area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
        self.sign = 1.0 if area > 0 else -1.0
        e = np.roll(P, -1, axis=0) - P
        nrm = np.stack([e[:, 1], -e[:, 0]], -1) * self.sign
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        self.en = nrm
        self.ed = np.sum(nrm * P, axis=-1)

    def _d(self, Q):
        d2 = (Q[:, :2] @ self.en.T - self.ed).max(-1)
        cz = (self.z0 + self.z1) / 2
        hz = (self.z1 - self.z0) / 2
        dz = np.abs(Q[:, 2] - cz) - hz
        a = d2 + self.r
        b = dz + self.r
        out = np.minimum(np.maximum(a, b), 0.0) + np.hypot(np.maximum(a, 0.0), np.maximum(b, 0.0))
        return out - self.r

    def _lbox(self):
        lo = np.array([self.poly[:, 0].min(), self.poly[:, 1].min(), self.z0])
        hi = np.array([self.poly[:, 0].max(), self.poly[:, 1].max(), self.z1])
        return lo, hi


class Fn(Solid):
    """Any distance function f(Q) on local coords with an explicit local box."""

    def __init__(self, f, lbox, lipschitz=1.0, **kw):
        super().__init__(**kw)
        self.f = f
        self.lb = (np.asarray(lbox[0], np.float64), np.asarray(lbox[1], np.float64))
        self.lipschitz = lipschitz

    def _d(self, Q):
        return self.f(Q)

    def _lbox(self):
        return self.lb


# ---------------------------------------------------------------- combinators (world-space children)
class Diff(Solid):
    """a minus b (b is carved out; the cut faces keep a's material). Children use their own transforms."""

    def __init__(self, a, *bs, **kw):
        kw.setdefault('mat', a.mat)
        kw.setdefault('part', a.part)
        super().__init__(**kw)
        self.a = a
        self.bs = bs
        self.lipschitz = max([a.lipschitz] + [b.lipschitz for b in bs])

    def sdf(self, P):
        d = self.a.sdf(P)
        for b in self.bs:
            d = np.maximum(d, -b.sdf(P))
        return d

    def local(self, P):
        return self.a.local(P)

    def to_world(self, Q):
        return self.a.to_world(Q)

    def bbox(self):
        return self.a.bbox()

    def cut_by(self, P, eps=0.004):
        """Which pixels lie on a carved face (for materials)."""
        out = np.zeros(len(P), bool)
        for b in self.bs:
            out |= np.abs(b.sdf(P)) < eps
        return out


class Union(Solid):
    """Hard or smooth (k > 0) union of children; materials see the first child's local frame."""

    def __init__(self, *cs, k=0.0, **kw):
        kw.setdefault('mat', cs[0].mat)
        kw.setdefault('part', cs[0].part)
        super().__init__(**kw)
        self.cs = cs
        self.k = float(k)
        self.lipschitz = max(c.lipschitz for c in cs)

    def sdf(self, P):
        d = self.cs[0].sdf(P)
        for c in self.cs[1:]:
            e = c.sdf(P)
            if self.k > 0:
                h = np.clip(0.5 + 0.5 * (e - d) / self.k, 0.0, 1.0)
                d = e + (d - e) * h - self.k * h * (1.0 - h)
            else:
                d = np.minimum(d, e)
        return d

    def which(self, P):
        ds = np.stack([c.sdf(P) for c in self.cs], -1)
        return ds.argmin(-1)

    def local(self, P):
        return self.cs[0].local(P)

    def to_world(self, Q):
        return self.cs[0].to_world(Q)

    def bbox(self):
        los, his = zip(*[c.bbox() for c in self.cs])
        return np.min(los, 0) - self.k, np.max(his, 0) + self.k


class Displace(Solid):
    """Child surface pushed in/out by fbm noise (world coords): amp metres at frequency freq (1/m)."""

    def __init__(self, child, amp, freq, seed=0, octaves=3, bias=0.0, **kw):
        kw.setdefault('mat', child.mat)
        kw.setdefault('part', child.part)
        super().__init__(**kw)
        self.c = child
        self.amp, self.freq = float(amp), float(freq)
        self.seed, self.oct = int(seed), int(octaves)
        self.bias = float(bias)
        self.lipschitz = child.lipschitz * (1.0 + self.amp * self.freq * 2.5)

    def sdf(self, P):
        P = np.asarray(P, np.float64)
        n = fbm3(P[:, 0] * self.freq, P[:, 1] * self.freq, P[:, 2] * self.freq, self.oct, self.seed)
        return self.c.sdf(P) - self.amp * ((n - 0.5) * 2.0 + self.bias)

    def local(self, P):
        return self.c.local(P)

    def to_world(self, Q):
        return self.c.to_world(Q)

    def bbox(self):
        lo, hi = self.c.bbox()
        return lo - self.amp * (1 + abs(self.bias)), hi + self.amp * (1 + abs(self.bias))
