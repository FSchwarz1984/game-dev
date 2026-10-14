"""Small shape helpers on top of sdf.py: half-spaces, roofs, scattered stones, ropes."""
import math

import numpy as np

from .core import KZ, Rng, normalize
from .sdf import Box, Capsule, Cyl, Displace, Ellipsoid, Planes, rot
from .render import Line


def hs(n, p):
    """Half-space n . q <= n . p (n points outward)."""
    n = np.asarray(n, np.float64)
    return (n, float(np.dot(n, np.asarray(p, np.float64))))


def round_cyl(r, y0, y1, pos, mat, part='body', edge=0.02, kz=KZ, **kw):
    """A vertical round thing drawn the 3/4 way: its own depth compressed by KZ."""
    return Cyl(r, y0, y1, rz=r * kz, r=edge, pos=pos, mat=mat, part=part, **kw)


def stone_lump(center, size, mat, seed=0, part='body', amp=0.25, freq=None, yaw=0.0, round_r=None, **kw):
    """An irregular stone: a rounded box pushed by noise. size: (w, h, d) metres."""
    w, h, d = size
    rr = round_r if round_r is not None else min(w, h, d) * 0.35
    b = Box([w / 2, h / 2, d / 2], r=rr, pos=center, R=rot(yaw=yaw), mat=mat, part=part, **kw)
    a = min(w, h, d) * amp
    f = freq if freq is not None else 2.2 / max(min(w, h, d), 0.05)
    return Displace(b, a, f, seed=seed, octaves=3)


def rope_line(pts, mat, part='body', width=1, sag=0.0, n=24, bias=0.02, **kw):
    """A cord through points; with sag > 0 a two-point cord hangs in a catenary-like curve."""
    pts = np.asarray(pts, np.float64)
    if sag > 0 and len(pts) == 2:
        f = np.linspace(0, 1, n)[:, None]
        P = pts[0] + (pts[1] - pts[0]) * f
        P[:, 1] -= sag * 4 * f[:, 0] * (1 - f[:, 0])
        pts = P
    return Line(pts, mat, part=part, width_px=width, bias=bias, **kw)


def lerp3(a, b, t):
    return np.asarray(a, np.float64) + (np.asarray(b, np.float64) - np.asarray(a, np.float64)) * t
