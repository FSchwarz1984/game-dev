"""The P3 camera of the game (G5R3-40) in plan coordinates, for the drawings and the scale tables.

Plan coordinates everywhere in tools/design: x east, y north, h up (metres). Godot's are x east, y up,
z south, so godot = (x, h, -y).

The camera is PixelView3D's perspective preset (godot/render3d/pixel_view3d.gd): the viewport is 362 px
high (360 + a 1 px border on each side), the focus is her chest (her feet + 0.9 m), and at the focus 1 m
spans PPM native px on the picture plane, so the camera stands D = K / PPM from the focus, where
K = (H / 2) / tan(fov / 2). Upright things lean back: a point t metres above the base of its object
moves north by k * t, k = tan(pitch / 2) * share (the "lean share"). Character sprites (w3_card) are not
projected: they are drawn texel for pixel at any depth.

The numbers agree with the renderer's own script (scratchpad bin/upright_scale.py, 2026-10-17): at
fov 38, pitch 45, PPM 30 the camera is 17.52 m from the focus, and an upright at her feet covers
19.75 / 22.39 / 24.14 / 28.53 px per metre at shares 0 / 0.3 / 0.5 / 1.0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

VIEW_W, VIEW_H = 640, 360          # the native picture
VIEWPORT_H = 362.0                 # PixelView3D renders 360 + a border row top and bottom
CHEST = 0.9                        # the focus: her chest above her feet


@dataclass
class Cam:
    fov: float = 38.0              # vertical field of view, degrees
    pitch: float = 45.0            # degrees below the horizon
    ppm: float = 30.0              # native px per metre on the picture plane at the focus
    share: float = 0.0             # lean-back share (0 .. 1)
    her: tuple = (0.0, 0.0, 0.0)   # her feet (x, y, h)

    # derived ------------------------------------------------------------------------------------
    @property
    def K(self) -> float:
        return (VIEWPORT_H / 2.0) / math.tan(math.radians(self.fov) / 2.0)

    @property
    def D(self) -> float:
        return self.K / self.ppm

    @property
    def p(self) -> float:
        return math.radians(self.pitch)

    @property
    def k(self) -> float:
        return math.tan(self.p / 2.0) * self.share

    @property
    def f(self) -> np.ndarray:     # forward (north and down)
        return np.array([0.0, math.cos(self.p), -math.sin(self.p)])

    @property
    def u(self) -> np.ndarray:     # screen up
        return np.array([0.0, math.sin(self.p), math.cos(self.p)])

    @property
    def r(self) -> np.ndarray:     # screen right (east)
        return np.array([1.0, 0.0, 0.0])

    @property
    def focus(self) -> np.ndarray:
        x, y, h = self.her
        return np.array([x, y, h + CHEST])

    @property
    def C(self) -> np.ndarray:     # the camera
        return self.focus - self.f * self.D

    # projection ---------------------------------------------------------------------------------
    def project(self, P, lean_t=None):
        """P: (..., 3) plan points. lean_t: (...) height of each point above its object's base (the
        renderer shears uprights north by k * t); None for ground. Returns screen x (px, 0 at the
        centre, right +), screen y (px, 0 at the centre, up +) and depth along the view axis."""
        P = np.asarray(P, dtype=float)
        if lean_t is not None:
            P = P.copy()
            P[..., 1] = P[..., 1] + self.k * np.asarray(lean_t, dtype=float)
        Q = P - self.C
        d = Q @ self.f
        sx = self.K * (Q @ self.r) / d
        sy = self.K * (Q @ self.u) / d
        return sx, sy, d

    def to_pixels(self, sx, sy):
        """Screen-centred px -> image px (origin top-left of the 640x360 picture)."""
        return VIEW_W / 2.0 + sx, VIEW_H / 2.0 - sy

    def ray(self, px, py):
        """Image px -> unit ray direction (plan coords) from the camera."""
        sx = px - VIEW_W / 2.0
        sy = VIEW_H / 2.0 - py
        d = self.f + (sx / self.K) * self.r + (sy / self.K) * self.u
        return d / np.linalg.norm(d, axis=-1, keepdims=True) if d.ndim > 1 else d / np.linalg.norm(d)

    # scales at her feet ---------------------------------------------------------------------------
    def upright_px(self, h, at=None, base_h=None):
        """Screen height (px) of an upright of height h metres standing at `at` (x, y) on ground of
        height base_h (default: at her feet). Exact projection with the lean, so it holds for a 30 m
        tree as well as for a 0.16 m riser."""
        x, y, hh = self.her
        if at is not None:
            x, y = at
        if base_h is not None:
            hh = base_h
        _, y0, _ = self.project(np.array([x, y, hh]), lean_t=0.0)
        _, y1, _ = self.project(np.array([x, y, hh + h]), lean_t=h)
        return float(y1 - y0)

    def upright_ppm_local(self, at=None, base_h=None):
        e = 1e-3
        return self.upright_px(e, at, base_h) / e

    def ground_ppm(self, at=None, base_h=None):
        """(east-west px per metre, north-south px per metre) of the ground at `at`."""
        x, y, hh = self.her
        if at is not None:
            x, y = at
        if base_h is not None:
            hh = base_h
        e = 1e-3
        sx0, sy0, _ = self.project(np.array([x, y, hh]))
        sx1, _, _ = self.project(np.array([x + e, y, hh]))
        _, sy2, _ = self.project(np.array([x, y + e, hh]))
        return float((sx1 - sx0) / e), float((sy2 - sy0) / e)

    def height_for_px(self, px, at=None, base_h=None):
        """How tall (m) an upright standing at `at` must be to cover `px` screen px."""
        # scan up first (far above the camera the projection wraps), then bisect the first crossing
        step, h = 0.05, 0.0
        while h < 40.0 and self.upright_px(h + step, at, base_h) < px:
            h += step
        lo, hi = h, h + step
        for _ in range(50):
            mid = (lo + hi) / 2.0
            if self.upright_px(mid, at, base_h) < px:
                lo = mid
            else:
                hi = mid
        return lo

    # the visible ground on flat land ---------------------------------------------------------------
    def flat_footprint(self, ground_h=None):
        """Corners of the visible ground (flat, at her feet's height) in plan coords: bottom-left,
        bottom-right, top-right, top-left. Rows at the picture's edges (y = 0 and 360)."""
        gh = self.her[2] if ground_h is None else ground_h
        pts = []
        for px, py in ((0, VIEW_H), (VIEW_W, VIEW_H), (VIEW_W, 0), (0, 0)):
            d = self.ray(px, py)
            C = self.C
            t = (gh - C[2]) / d[2]
            pts.append(C + t * d)
        return np.array(pts)


def screen_extent(cam: Cam):
    """Depth (south, north of her feet) and widths (bottom, at her, top) of the visible flat ground."""
    fp = cam.flat_footprint()
    hx, hy, _ = cam.her
    south = hy - fp[0, 1]
    north = fp[2, 1] - hy
    w_bot = fp[1, 0] - fp[0, 0]
    w_top = fp[2, 0] - fp[3, 0]
    # width at her row: intersect the frame's left/right edges with her row
    C = cam.C
    out = []
    for px in (0, VIEW_W):
        # the ray through (px, row of her feet)
        sx, sy, _ = cam.project(np.array([hx, hy, cam.her[2]]))
        _, py = cam.to_pixels(0, sy)
        d = cam.ray(px, py)
        t = (cam.her[2] - C[2]) / d[2]
        out.append((C + t * d)[0])
    w_her = out[1] - out[0]
    # area of the trapezoid-like footprint (exact polygon of the four corners; the sides are straight
    # lines on flat ground because the frame's edges are planes through the camera)
    area = 0.5 * abs(np.dot(fp[:, 0], np.roll(fp[:, 1], -1)) - np.dot(fp[:, 1], np.roll(fp[:, 0], -1)))
    return dict(south=south, north=north, depth=south + north, w_bot=w_bot, w_her=w_her, w_top=w_top,
                area=area)


SHARES = (0.0, 0.3, 0.5, 1.0)


def feet_upright_ppm(share, ppm=30.0, fov=38.0, pitch=45.0):
    return Cam(fov=fov, pitch=pitch, ppm=ppm, share=share).upright_ppm_local()


def ppm_for_feet_upright(target, share, fov=38.0, pitch=45.0):
    """The camera PPM at which an upright at her feet covers `target` px per metre."""
    lo, hi = 5.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if feet_upright_ppm(share, mid, fov, pitch) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


if __name__ == "__main__":
    for s in SHARES:
        c = Cam(share=s)
        print("share %.1f  D %.2f  feet upright %.2f px/m  57 px = %.2f m  ground %s  extent %s" % (
            s, c.D, c.upright_ppm_local(), c.height_for_px(57.0),
            tuple(round(v, 2) for v in c.ground_ppm()),
            {k: round(v, 1) for k, v in screen_extent(c).items()}))
