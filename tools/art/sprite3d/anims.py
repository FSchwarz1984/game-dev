"""Shared animations: idle (breathing), walk and run cycles, built on humanoid.locomotion_pose.
Each animation returns a list of FrameSpec; the sheet builder simulates the chains over them and
renders every direction.

Snapping (pixel stability): the pelvis height is rounded to whole pixels per frame, so the body
bobs in clean 1-px steps, and the head unit keeps the rest pose's sub-pixel phase (model.py), so
the face does not shimmer while she walks."""

from __future__ import annotations

import math

import humanoid as Hu
from model import FrameSpec


def snap_pelvis(P, pose):
    if 'pelvis_y' in pose:
        pose['pelvis_y'] = P['hip'] + round(pose['pelvis_y'] - P['hip'])
    return pose


def cycle(model, kind, frames, extra=None, wind=0.0):
    P = model.P
    out = []
    for i in range(frames):
        ph = i / frames
        pose = Hu.locomotion_pose(P, ph, kind, extra(ph) if callable(extra) else extra)
        snap_pelvis(P, pose)
        out.append(FrameSpec(pose, {}, wind=(0, 0, -wind)))
    return out


def idle(model, frames=12, blink=(9,), extra=None):
    """Slow breathing: on the in-breath the whole upper body (chest, shoulders, head, hat) rises
    one pixel for a third of the cycle, the arms settle out a frame later; hair, ribbons and hems
    stir in a light, irregular breeze. The legs and feet never move."""
    P = model.P
    base = model.rest_pose()
    out = []
    for i in range(frames):
        ph = i / frames
        pose = dict(base)
        breath = 1 if 0.30 <= ph < 0.70 else 0
        if breath:
            pose['offset_spine'] = (0.0, 1.0, 0.0)
        lag = 1 if 0.38 <= ph < 0.78 else 0
        for s, sx in (('L', 1), ('R', -1)):
            u = base.get('uarm' + s, (0, 0, 0))
            pose['uarm' + s] = (u[0], u[1], u[2] + sx * 1.5 * lag)
        if extra:
            pose.update(extra(ph) if callable(extra) else extra)
        gust = 0.10 * math.sin(2 * math.pi * ph) + 0.05 * math.sin(4 * math.pi * ph + 1.3)
        ctx = {'expr': 'blink' if i in blink else 'open'}
        out.append(FrameSpec(pose, ctx, wind=(0.04 * math.sin(2 * math.pi * ph + 0.7), 0, -0.05 + gust)))
    return out


# ---------------------------------------------------------------------------------------------
# Registry helpers. An animation spec: make(model, view) -> [FrameSpec], fps, loop, views, sheets,
# and for locomotion its nominal ground speed in m/s (the engine scales playback to the real
# speed so the feet do not skate).

PPM = 20.0


def loco_spec(kind, frames, fps, views, sheets, wind):
    def make(m, view, kind=kind, frames=frames, wind=wind):
        return cycle(m, kind, frames, wind=wind)
    spec = {'make': make, 'fps': fps, 'loop': True, 'views': views, 'sheets': sheets, 'kind': kind}
    return spec


def with_speed(spec, model):
    """Fill in the nominal speed (m/s) of a walk/run spec from the model's stride."""
    C = model.P['cycles'][spec['kind']]
    frames = 8
    spec['speed'] = round(2 * C['stride'] * spec['fps'] / frames / PPM, 3)
    return spec


def idle_spec(fps, views, sheets, frames=12):
    def make(m, view, frames=frames):
        return idle(m, frames)
    return {'make': make, 'fps': fps, 'loop': True, 'views': views, 'sheets': sheets}
