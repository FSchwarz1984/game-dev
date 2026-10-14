"""Pose helpers for scripted animations: building poses from a few readable parameters, blending
keyframes, putting a lying or sitting body on the ground, and frame lists for the builder.

Conventions (model frame: X her left, Y up, Z forward): a forward swing of a limb that hangs down
is a negative rotation about X; bending the spine forward is positive; looking up is a negative
head pitch. 'root_m' in a pose is an explicit 4x4 placement of the whole body (lying, falling)."""

from __future__ import annotations

import copy
import math

import numpy as np

import geom as G
import humanoid as Hu
from model import FrameSpec


def arm(side, swing=0.0, out=8.0, twist=0.0, elbow=14.0):
    """Upper arm swung forward by `swing` deg and out to the side by `out`; elbow bend `elbow`."""
    sx = 1 if side == 'L' else -1
    return {'uarm' + side: (-swing, twist * sx, sx * out), 'farm' + side: (-elbow, 0.0, 0.0)}


def arms(swing=0.0, out=8.0, elbow=14.0, twist=0.0, L=None, R=None):
    d = {}
    d.update(arm('L', **(L if L is not None else dict(swing=swing, out=out, elbow=elbow, twist=twist))))
    d.update(arm('R', **(R if R is not None else dict(swing=swing, out=out, elbow=elbow, twist=twist))))
    return d


def legs_ik(P, feet, pelvis_y=None, splay=1.5):
    """feet: {'L': (z, y, pitch), 'R': ...} ankle targets in the body frame (z forward, y height
    of the ankle above the ground). Returns pose entries (thigh/shin/foot) and the pelvis height."""
    hip_y = P['hip'] if pelvis_y is None else pelvis_y
    out = {'pelvis_y': hip_y}
    for s, sx in (('L', 1), ('R', -1)):
        z, y, pitch = feet[s]
        th, sh, ft = Hu.leg_ik((-P['hip_d'], 0.0), (-hip_y + y + P.get('ankle', 1.2), z), P['thigh'], P['shin'], pitch)
        out['thigh' + s] = (th, 0.0, sx * splay)
        out['shin' + s] = (sh, 0.0, 0.0)
        out['foot' + s] = (ft, 0.0, 0.0)
    return out


def blend(a: dict, b: dict, t: float) -> dict:
    """Linear blend of two poses (Euler angles, pelvis height, root tuple; root_m by matrix lerp)."""
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if va is None:
            va = (0.0,) * len(vb) if isinstance(vb, tuple) else vb
        if vb is None:
            vb = (0.0,) * len(va) if isinstance(va, tuple) else va
        if k == 'root_m':
            out[k] = va * (1 - t) + vb * t
            # re-orthonormalise the rotation
            U, _, Vt = np.linalg.svd(out[k][:3, :3])
            out[k][:3, :3] = U @ Vt
        elif isinstance(va, tuple):
            out[k] = tuple(x * (1 - t) + y * t for x, y in zip(va, vb))
        elif isinstance(va, (int, float)):
            out[k] = va * (1 - t) + vb * t
        else:
            out[k] = vb if t >= 0.5 else va
    return out


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def merged(base: dict, *over) -> dict:
    out = dict(base)
    for o in over:
        if o:
            out.update(o)
    return out


def frames(m, poses, ctxs=None, wind=None, snap=True):
    """FrameSpecs from a list of poses (pelvis heights snapped to whole pixels)."""
    out = []
    for i, p in enumerate(poses):
        p = dict(p)
        if snap and 'pelvis_y' in p:
            p['pelvis_y'] = m.P['hip'] + round(p['pelvis_y'] - m.P['hip'])
        ctx = dict(ctxs[i]) if ctxs else {}
        w = wind[i] if wind else (0, 0, 0)
        out.append(FrameSpec(p, ctx, wind=w))
    return out


# ---------------------------------------------------------------------------------------------
# Whole-body placement


def lying_back(head_dir=+1):
    """On her back, head toward +Z (head_dir=+1) or -Z: Y -> Z, Z -> up."""
    R = G.Ry(180) @ G.Rx(-90) if head_dir > 0 else G.Rx(-90) @ G.Rz(180) @ G.Ry(180)
    return R


def prone(head_dir=+1):
    """Face down, head toward +Z: Y -> Z, Z -> -Y."""
    return G.Rx(90) if head_dir > 0 else G.Ry(180) @ G.Rx(90)


def place(m, pose, R, centre_bone='pelvis', lift=0.0, ground_pts=None):
    """Turn the whole body by R, put `centre_bone` over the ground point and rest the lowest
    contact point on the ground (y = 0) plus `lift`. ground_pts: [(bone, (x, y, z), radius)]."""
    p = dict(pose)
    p['root_m'] = G.M4(R, (0, 0, 0))
    bw = m.bones(p)
    c = bw[centre_bone][:3, 3]
    pts = ground_pts or default_contacts(m)
    lows = []
    for bone, off, r in pts:
        if bone in bw:
            q = bw[bone] @ np.array([off[0], off[1], off[2], 1.0])
            lows.append(q[1] - r)
    low = min(lows) if lows else 0.0
    p['root_m'] = G.M4(R, (-c[0], -low + lift, -c[2]))
    return p


def default_contacts(m):
    """Points (bone, offset, radius) that can touch the ground: head, back, hips, knees, feet."""
    P = m.P
    return [('head', (0, 4.8, 0.3), 4.8), ('head', (0, 5.0, -0.5), 5.2), ('chest', (0, 0.3, 0), 2.8),
            ('spine', (0, 0.8, 0), 2.6), ('pelvis', (0, 0.0, 0), 2.6),
            ('shinL', (0, 0, 0), 1.6), ('shinR', (0, 0, 0), 1.6),
            ('footL', (0, -0.4, 0.5), 1.0), ('footR', (0, -0.4, 0.5), 1.0),
            ('handL', (0, -0.4, 0), 0.9), ('handR', (0, -0.4, 0), 0.9)]
