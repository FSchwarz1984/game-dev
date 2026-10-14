"""Geometry for the 3D character models: rotations, a bone hierarchy, SDF shapes attached to bones,
and the camera. Units: one model unit = one native pixel. Model frame: X = her left, Y = up,
Z = forward (right-handed). World frame: X east, Y up, Z south; facing 'front' = facing south,
toward the camera, so the model frame equals the world frame.

Camera: orthographic, pitched down by PITCH degrees, looking north. Heights keep full scale (one
unit up = one pixel up): the camera's y axis is stretched by 1/cos(pitch), so ground depth shows
at tan(pitch) (the shadow-ellipse ratio the game already uses for characters). On screen this is
the oblique projection  screen_y_up = y - tan(PITCH) * z  (z toward the viewer), screen_x = x.
PITCH is 20 for the 2D game; TENGAN_SPRITE_PITCH overrides it (build.py --pitch), e.g. 39.33 =
atan(sin 55) matches the 3D sample's leaned upright objects (knowledge/21: y - sin55 * z)."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import numpy as np

from render import STRIDE

KINDS = {'ell': 0, 'rcone': 1, 'box': 2, 'cone': 3, 'cyl': 4, 'torus': 5, 'skirt': 6, 'halfell': 7}


def Rx(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float64)


def Ry(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float64)


def Rz(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


def euler(rx=0.0, ry=0.0, rz=0.0):
    """Yaw (about Y) outermost, then pitch (about X), then roll (about Z)."""
    return Ry(ry) @ Rx(rx) @ Rz(rz)


def M4(R=None, t=(0, 0, 0)):
    m = np.eye(4)
    if R is not None:
        m[:3, :3] = R
    m[:3, 3] = t
    return m


def T(x=0.0, y=0.0, z=0.0):
    return M4(None, (x, y, z))


def rot_to(v_from, v_to):
    """Rotation taking unit vector v_from onto v_to (both 3-vectors)."""
    a = np.asarray(v_from, float); a = a / np.linalg.norm(a)
    b = np.asarray(v_to, float); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.999999:
        axis = np.cross(a, [1, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1, 0])
        axis /= np.linalg.norm(axis)
        K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        return np.eye(3) + 2 * K @ K
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * (1.0 / (1.0 + c))


# ---------------------------------------------------------------------------------------------
# Skeleton


class Skeleton:
    """Bones with a parent and a joint offset in the parent's frame (rest pose: no rotation)."""

    def __init__(self):
        self.parent: dict[str, str | None] = {}
        self.offset: dict[str, np.ndarray] = {}
        self.order: list[str] = []

    def add(self, name, parent, offset):
        self.parent[name] = parent
        self.offset[name] = np.asarray(offset, float)
        self.order.append(name)
        return name

    def world(self, rot: dict, root: np.ndarray) -> dict:
        """rot: bone -> 3x3 (or (rx, ry, rz) degrees); root: 4x4 placement of the 'root' bone."""
        out = {}
        for b in self.order:
            p = self.parent[b]
            r = rot.get(b)
            if r is None:
                R = np.eye(3)
            elif isinstance(r, np.ndarray) and r.shape == (3, 3):
                R = r
            else:
                R = euler(*r)
            local = M4(R, self.offset[b])
            out[b] = (root if p is None else out[p]) @ local
        return out


# ---------------------------------------------------------------------------------------------
# Shapes


@dataclass
class Shape:
    kind: str
    bone: str
    params: list
    mat: str
    part: str = ''
    xf: np.ndarray = field(default_factory=lambda: np.eye(4))   # shape frame in its bone's frame
    group: str | None = None
    k: float = 0.0
    bands: list = field(default_factory=list)   # (axis, lo, hi, mat[, amp, count, phase, period])
    occluder: bool = False
    cut: tuple | None = None                     # (nx, ny, nz, d) in the BONE frame: keeps n.p <= d
    cut2: tuple | None = None                    # a second plane (takes the ground clip's slot)

    def bound(self):
        """Bounding sphere (centre in the shape frame, radius)."""
        p = self.params
        if self.kind in ('ell', 'halfell'):
            return np.zeros(3), max(p[0], p[1], p[2])
        if self.kind == 'rcone':
            a, b = np.array(p[0:3]), np.array(p[4:7])
            return (a + b) / 2, np.linalg.norm(b - a) / 2 + max(p[3], p[7])
        if self.kind == 'box':
            return np.zeros(3), math.sqrt(p[0] ** 2 + p[1] ** 2 + p[2] ** 2)
        if self.kind == 'cone':
            s = max(p[4] if len(p) > 4 and p[4] > 0 else 1, p[5] if len(p) > 5 and p[5] > 0 else 1)
            return np.zeros(3), math.sqrt(p[0] ** 2 + (max(p[1], p[2]) * s) ** 2)
        if self.kind == 'cyl':
            return np.zeros(3), math.sqrt(p[0] ** 2 + p[1] ** 2)
        if self.kind == 'torus':
            return np.zeros(3), p[0] + p[1]
        if self.kind == 'skirt':
            s = max(p[3] or 1, p[4] or 1)
            return np.zeros(3), math.sqrt((p[0] + abs(p[5])) ** 2 + ((max(p[1], p[2]) + abs(p[8])) * s) ** 2)
        raise ValueError(self.kind)


def ell(bone, r, mat, at=(0, 0, 0), R=None, **kw):
    return Shape('ell', bone, list(r), mat, xf=M4(R, at), **kw)


def halfell(bone, r, cut, mat, at=(0, 0, 0), R=None, **kw):
    return Shape('halfell', bone, list(r) + [cut], mat, xf=M4(R, at), **kw)


def rcone(bone, a, b, r1, r2, mat, **kw):
    return Shape('rcone', bone, [a[0], a[1], a[2], r1, b[0], b[1], b[2], r2], mat, **kw)


def box(bone, half, mat, round_=0.0, at=(0, 0, 0), R=None, **kw):
    return Shape('box', bone, [half[0], half[1], half[2], round_], mat, xf=M4(R, at), **kw)


def cone(bone, h, r1, r2, mat, round_=0.0, sx=1.0, sz=1.0, at=(0, 0, 0), R=None, **kw):
    return Shape('cone', bone, [h, r1, r2, round_, sx, sz], mat, xf=M4(R, at), **kw)


def cyl(bone, h, r, mat, round_=0.0, at=(0, 0, 0), R=None, **kw):
    return Shape('cyl', bone, [h, r, round_], mat, xf=M4(R, at), **kw)


def torus(bone, R_, r, mat, at=(0, 0, 0), R=None, **kw):
    return Shape('torus', bone, [R_, r], mat, xf=M4(R, at), **kw)


def skirt(bone, h, r_hem, r_waist, mat, sx=1.0, sz=1.0, wave=(0, 0, 0), flare=(0, 0, 0), round_=0.3,
          at=(0, 0, 0), R=None, **kw):
    return Shape('skirt', bone, [h, r_hem, r_waist, sx, sz, wave[0], wave[1], wave[2], flare[0], flare[1], flare[2], round_],
                 mat, xf=M4(R, at), **kw)


# ---------------------------------------------------------------------------------------------
# Camera and assembly

PITCH = float(os.environ.get('TENGAN_SPRITE_PITCH', '20.0'))


def camera(pitch=PITCH):
    c, s = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    m = np.eye(4)
    m[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    return m


def assemble(shapes, bones_world, cam, mat_ids, part_ids, group_ids, ground=None):
    """ground: height (body frame) below which nothing is drawn, or None."""
    rows = []
    for sh in shapes:
        Mw = cam @ bones_world[sh.bone] @ sh.xf          # shape frame -> camera
        inv = np.linalg.inv(Mw)                          # camera -> shape frame
        r = np.zeros(STRIDE, np.float32)
        r[0] = KINDS[sh.kind]
        r[1] = mat_ids[sh.mat]
        r[2] = part_ids.setdefault(sh.part or sh.bone, len(part_ids))
        g = -1
        if sh.group:
            g = group_ids.setdefault(sh.group, len(group_ids))
        r[3] = g
        r[4] = sh.k
        r[5] = 1 if sh.occluder else 0
        r[6:18] = inv[:3, :4].reshape(-1)
        p = list(sh.params)
        r[18:18 + len(p)] = p
        c, rad = sh.bound()
        cc = Mw @ np.array([c[0], c[1], c[2], 1.0])
        r[30:33] = cc[:3]
        r[33] = rad + sh.k + 0.6
        r[34] = len(sh.bands)
        for i, b in enumerate(sh.bands[:4]):
            bb = list(b) + [0, 0, 0, 0][: max(0, 8 - len(b))]
            axis, lo, hi, m = bb[0], bb[1], bb[2], bb[3]
            r[35 + i * 8: 43 + i * 8] = [axis, lo, hi, mat_ids[m], bb[4], bb[5], bb[6], bb[7]]
        R, t = sh.xf[:3, :3], sh.xf[:3, 3]
        for slot, plane in ((68, sh.cut), (72, sh.cut2)):
            if plane is None:
                continue
            # the plane is given in the bone frame; the renderer wants it in the shape frame
            n = np.asarray(plane[:3], float)
            ln = np.linalg.norm(n)
            n, d = n / ln, plane[3] / ln
            r[slot:slot + 3] = R.T @ n
            r[slot + 3] = d - float(n @ t)
        if ground is not None and sh.cut2 is None:
            # body-frame plane -y <= -ground, expressed in the shape frame
            Ms = bones_world[sh.bone] @ sh.xf
            n = np.array([0.0, -1.0, 0.0])
            r[72:75] = Ms[:3, :3].T @ n
            r[75] = -ground - float(n @ Ms[:3, 3])
        rows.append(r)
    return np.array(rows, np.float32)
