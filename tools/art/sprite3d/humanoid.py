"""The shared chibi rig: skeleton layout, leg IK, the walk / run / idle cycles and secondary motion
(hair, sleeves, hems and ribbons that lag behind the body).

All characters use the same bone names; proportions come from a dict (heights in px). Model frame:
X = her left, Y = up, Z = forward. A pose is a dict bone -> (rx, ry, rz) degrees plus 'root':
(x, y, z, yaw, pitch, roll) for the whole body. Positive 'swing' = forward; a forward swing of a
limb that hangs down is a negative rotation about X."""

from __future__ import annotations

import math

import numpy as np

from geom import Skeleton, M4, euler, Ry, Rx, Rz

BONES_SIDE = ('L', 'R')


def build_skeleton(P: dict) -> Skeleton:
    """P: proportions. hip (pelvis height), spine, chest (lengths up the torso), neck, sh_w (half
    shoulder width), sh_h (shoulder height above the chest joint), uarm, farm, hip_w (half hip width),
    thigh, shin."""
    sk = Skeleton()
    sk.add('root', None, (0, 0, 0))
    sk.add('pelvis', 'root', (0, P['hip'], 0))
    sk.add('spine', 'pelvis', (0, P['spine'], 0))
    sk.add('chest', 'spine', (0, P['chest'], 0))
    sk.add('neck', 'chest', (0, P['neck'], 0))
    sk.add('head', 'neck', (0, P['neck2'], 0))
    for s, sx in (('L', 1), ('R', -1)):
        sk.add('uarm' + s, 'chest', (sx * P['sh_w'], P['sh_h'], 0))
        sk.add('farm' + s, 'uarm' + s, (0, -P['uarm'], 0))
        sk.add('hand' + s, 'farm' + s, (0, -P['farm'], 0))
        sk.add('thigh' + s, 'pelvis', (sx * P['hip_w'], -P['hip_d'], 0))
        sk.add('shin' + s, 'thigh' + s, (0, -P['thigh'], 0))
        sk.add('foot' + s, 'shin' + s, (0, -P['shin'], 0))
    return sk


def leg_ik(hip, foot, a, b, foot_pitch=0.0):
    """hip, foot: (y, z) in the pelvis frame (foot = ankle). Returns thigh rx, shin rx, foot rx (deg)
    with the knee bending forward and the foot at world pitch foot_pitch (deg, + = toes down)."""
    dy, dz = foot[0] - hip[0], foot[1] - hip[1]
    d = math.hypot(dy, dz)
    d = min(max(d, abs(a - b) + 1e-3), a + b - 1e-3)
    alpha = math.atan2(dz, -dy)                       # from straight down, forward positive
    t1 = math.acos(max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d))))
    t2 = math.acos(max(-1.0, min(1.0, (b * b + d * d - a * a) / (2 * b * d))))
    thigh = -(alpha + t1)
    shin = t1 + t2
    foot_r = alpha - t2 + math.radians(foot_pitch)
    return math.degrees(thigh), math.degrees(shin), math.degrees(foot_r)


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------
# Locomotion cycles. phase in [0, 1); the left foot contacts at phase 0, the right at 0.5.


def foot_track(phase, stride, lift, stance=0.5, toe_off=18.0, heel=6.0):
    """Ankle target relative to the hip column: (forward z, height y, foot pitch deg). Planted at
    contact (z = +stride/2), slides back linearly during stance, lifts and swings forward."""
    p = phase % 1.0
    if p < stance:
        t = p / stance
        z = stride / 2 - stride * t
        y = 0.0
        # heel rises over the last 30 % of stance (toe-off); flat at contact with a slight heel strike
        pitch = toe_off * smooth01((t - 0.7) / 0.3) - heel * (1 - smooth01(t / 0.15))
    else:
        t = (p - stance) / (1 - stance)
        e = 0.5 - 0.5 * math.cos(math.pi * t)          # eased swing
        z = -stride / 2 + stride * e
        y = lift * math.sin(math.pi * t)
        pitch = toe_off * (1 - smooth01(t / 0.35)) - heel * smooth01((t - 0.75) / 0.25)
    return z, y, pitch


def locomotion_pose(P, phase, kind='walk', extra=None):
    """A pose dict for the walk or run cycle at `phase`. P: proportions (with cycle parameters)."""
    C = P['cycles'][kind]
    pose = {}
    stride, lift = C['stride'], C['lift']
    # hips: down after each contact, up at passing; values are px and later snapped by the caller
    two = (phase * 2) % 1.0
    bob = C['bob'](two)
    sway = C.get('sway', 0.0) * math.sin(2 * math.pi * phase)          # side to side over the stance foot
    hip_h = P['hip'] + bob
    pose['root'] = (sway, 0.0, 0.0, 0.0, 0.0, 0.0)
    pose['pelvis_y'] = hip_h
    a, b = P['thigh'], P['shin']
    ankle = P.get('ankle', 1.2)
    for s, off in (('L', 0.0), ('R', 0.5)):
        z, y, pitch = foot_track(phase + off, stride, lift, C.get('stance', 0.5), C.get('toe_off', 18), C.get('heel', 6))
        hip = (-P['hip_d'], 0.0)
        foot = (-hip_h + ankle + y, z)
        th, sh, ft = leg_ik(hip, foot, a, b, pitch)
        pose['thigh' + s] = (th, 0, (1 if s == 'L' else -1) * C.get('splay', 1.0))
        pose['shin' + s] = (sh, 0, 0)
        pose['foot' + s] = (ft, 0, 0)
    # torso: lean forward, counter-twist against the hips, chest bob lag
    swing = math.sin(2 * math.pi * phase)                                # +1 when the left leg is back
    pose['pelvis'] = (C.get('pelvis_tilt', 0.0), C.get('twist', 3.0) * swing, 0.0)
    pose['spine'] = (C.get('lean', 4.0), -C.get('twist', 3.0) * swing * 0.6, 0.0)
    pose['chest'] = (C.get('lean2', 2.0), -C.get('twist', 3.0) * swing * 0.6, 0.0)
    pose['head'] = (-C.get('lean', 4.0) - C.get('lean2', 2.0) + C.get('head_pitch', 0.0), C.get('twist', 3.0) * swing * 0.5, 0.0)
    # arms swing against the legs (left arm forward when the right leg is forward: phase 0.5)
    arm = C.get('arm', 22.0)
    for s, sgn in (('L', -1.0), ('R', 1.0)):
        sw = arm * sgn * math.cos(2 * math.pi * (phase - C.get('arm_lag', 0.04)))
        out = C.get('arm_out', 10.0) * (1 if s == 'L' else -1)
        pose['uarm' + s] = (-sw, 0.0, out)
        bend = C.get('elbow', 18.0) + C.get('elbow_swing', 10.0) * max(0.0, sgn * math.cos(2 * math.pi * phase))
        pose['farm' + s] = (-bend, 0.0, 0.0)
    if extra:
        pose.update(extra)
    return pose


def bob_walk(t):
    """t in [0,1) within one step: 0 contact, .25 down, .5 passing, .75 up -> px offset."""
    return -0.6 * math.cos(2 * math.pi * (t - 0.25))


def bob_run(t):
    return -0.9 * math.cos(2 * math.pi * (t - 0.30))


# ---------------------------------------------------------------------------------------------
# Secondary motion: chains of point masses (verlet) hanging from moving anchors.


class Chain:
    """A dangling chain: n segments of length seg, hanging from an anchor that the caller moves.
    Simulated in the character's body frame (verlet); `wind` is a constant acceleration (the drag
    while walking), gravity pulls -Y, `stiff` pulls each segment toward its rest direction. Inside
    the constraint loop every node is kept out of the body (`collide`, a point -> point function)
    and above the ground, and segment lengths are kept: a segment that reaches the ground lies
    along it instead of shrinking."""

    def __init__(self, n, seg, rest_dir=(0, -1, 0), damping=0.12, stiff=0.08, gravity=0.35):
        self.n, self.seg = n, seg
        self.rest = np.asarray(rest_dir, float) / np.linalg.norm(rest_dir)
        self.damping, self.stiff, self.gravity = damping, stiff, gravity
        self.p = None
        self.prev = None

    def reset(self, anchor, rest=None):
        r = self.rest if rest is None else np.asarray(rest, float)
        self.p = np.array([np.asarray(anchor, float) + r * self.seg * i for i in range(self.n + 1)], float)
        self.prev = self.p.copy()

    def _fix(self, a, b, r, ground, collide):
        d = b - a
        ln = np.linalg.norm(d)
        if ln < 1e-6:
            d, ln = r.copy(), 1.0
        b = a + d / ln * self.seg
        if collide is not None:
            b = collide(b)
            d = b - a
            ln = np.linalg.norm(d)
            if ln > 1e-6:
                b = a + d / ln * self.seg
        if ground is not None and b[1] < ground:
            dy = ground - a[1]
            hz = math.sqrt(max(self.seg * self.seg - dy * dy, 0.0))
            hv = np.array([b[0] - a[0], b[2] - a[2]])
            lh = np.linalg.norm(hv)
            if lh < 1e-6:
                hv = np.array([r[0], r[2]])
                lh = np.linalg.norm(hv)
                if lh < 1e-6:
                    hv, lh = np.array([0.0, -1.0]), 1.0
            b = np.array([a[0] + hv[0] / lh * hz, ground, a[2] + hv[1] / lh * hz])
        return b

    def step(self, anchor, rest_dir=None, wind=(0, 0, 0), substeps=4, collide=None, ground=None):
        r = self.rest if rest_dir is None else np.asarray(rest_dir, float) / np.linalg.norm(rest_dir)
        if self.p is None:
            self.reset(anchor, r)
        target = np.asarray(anchor, float)
        start = self.p[0].copy()
        w = np.asarray(wind, float)
        for s in range(substeps):
            self.p[0] = start + (target - start) * (s + 1) / substeps
            vel = (self.p[1:] - self.prev[1:]) * (1 - self.damping)
            self.prev[1:] = self.p[1:].copy()
            acc = np.array([0, -self.gravity, 0]) + w
            self.p[1:] += vel + acc / (substeps * substeps)
            for _ in range(3):
                for i in range(self.n):
                    a, b = self.p[i], self.p[i + 1]
                    want = a + r * self.seg
                    b = b + (want - b) * self.stiff
                    seg_dir = (a - self.p[i - 1]) if i > 0 else r
                    nl = np.linalg.norm(seg_dir)
                    seg_dir = seg_dir / nl if nl > 1e-6 else r
                    self.p[i + 1] = self._fix(a, b, seg_dir, ground, collide)
        self.prev[0] = self.p[0].copy()
        return self.p.copy()


def periodic(sim_step, frames, warm=3):
    """Runs sim_step(i) over `warm` + 1 cycles of `frames` frames and returns the last cycle's
    outputs (so a looping animation's secondary motion joins up)."""
    out = []
    for c in range(warm + 1):
        for i in range(frames):
            r = sim_step(i)
            if c == warm:
                out.append(r)
    return out


def chain_rotations(points, rest=(0, -1, 0)):
    """World-frame rotations (3x3) that turn `rest` onto each segment of a chain."""
    from geom import rot_to
    out = []
    for i in range(len(points) - 1):
        d = points[i + 1] - points[i]
        out.append(rot_to(rest, d))
    return out
