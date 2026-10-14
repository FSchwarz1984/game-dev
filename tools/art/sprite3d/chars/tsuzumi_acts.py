"""Tsuzumi's scripted animations (script-02-draft and the verbs). Each make(m, view) returns the
frames; tsuzumi.py registers them with their views, sheets and timing."""

from __future__ import annotations

import math

import numpy as np

import geom as G
import poses as Po
from model import FrameSpec


def rest(m):
    return dict(m.rest_pose())


def _f(m, seq, wind=None):
    poses = [p for p, c in seq]
    ctxs = [c for p, c in seq]
    return Po.frames(m, poses, ctxs, wind=wind)


# ------------------------------------------------------------------ verbs (all sheets, 4 views)

def take(m, view):
    """Reach out with the left hand, close it, pull it to the chest, hold."""
    r = rest(m)
    seq = [
        (Po.merged(r, Po.arm('L', swing=50, out=6, elbow=12), {'spine': (4, 0, 0)}), {}),
        (Po.merged(r, Po.arm('L', swing=68, out=4, elbow=4), {'spine': (7, 0, 0), 'chest': (2, 0, 0)}), {}),
        (Po.merged(r, Po.arm('L', swing=66, out=4, elbow=10), {'spine': (6, 0, 0), 'chest': (2, 0, 0)}), {}),
        (Po.merged(r, Po.arm('L', swing=36, out=12, elbow=92), {'spine': (2, 0, 0)}), {}),
        (Po.merged(r, Po.arm('L', swing=28, out=12, elbow=108)), {}),
    ]
    return _f(m, seq)


def give(m, view):
    """Both hands at the chest, offer forward, hold it out, return."""
    r = rest(m)
    chest = Po.arms(L=dict(swing=30, out=14, elbow=100), R=dict(swing=30, out=14, elbow=100))
    offer = Po.arms(L=dict(swing=58, out=6, elbow=26), R=dict(swing=58, out=6, elbow=26))
    seq = [(Po.merged(r, chest), {}),
           (Po.merged(r, offer, {'spine': (5, 0, 0)}), {}),
           (Po.merged(r, Po.arms(L=dict(swing=62, out=5, elbow=20), R=dict(swing=62, out=5, elbow=20)),
                      {'spine': (7, 0, 0), 'chest': (2, 0, 0)}), {}),
           (Po.merged(r, chest), {})]
    return _f(m, seq)


def release(m, view):
    """放: gather at the chest, fling both arms out, hold, relax."""
    r = rest(m)
    seq = [(Po.merged(r, Po.arms(L=dict(swing=26, out=16, elbow=110), R=dict(swing=26, out=16, elbow=110)),
                      {'spine': (4, 0, 0)}), {'expr': 'blink'}),
           (Po.merged(r, Po.arms(L=dict(swing=40, out=72, elbow=10), R=dict(swing=40, out=72, elbow=10)),
                      {'spine': (-3, 0, 0), 'chest': (-3, 0, 0)}), {}),
           (Po.merged(r, Po.arms(L=dict(swing=34, out=64, elbow=14), R=dict(swing=34, out=64, elbow=14)),
                      {'spine': (-2, 0, 0)}), {}),
           (Po.merged(r, Po.arms(L=dict(swing=10, out=24, elbow=18), R=dict(swing=10, out=24, elbow=18))), {})]
    return _f(m, seq)


def hurt(m, view):
    r = rest(m)
    fl = Po.arms(L=dict(swing=34, out=16, elbow=112), R=dict(swing=34, out=16, elbow=112))
    seq = [(Po.merged(r, fl, {'spine': (-9, 0, 0), 'chest': (-4, 0, 0), 'head': (-6, 0, 0),
                              'pelvis_y': m.P['hip'] - 1}), {'expr': 'shut', 'mouth': 'open'}),
           (Po.merged(r, fl, {'spine': (-6, 0, 0), 'chest': (-3, 0, 0), 'head': (-3, 0, 0),
                              'pelvis_y': m.P['hip'] - 1}), {'expr': 'shut'}),
           (Po.merged(r, {'spine': (-1, 0, 0)}), {'expr': 'blink'})]
    return _f(m, seq)


def look_up(m, view):
    r = rest(m)
    seq = [(Po.merged(r, {'head': (-26, 0, 0), 'neck': (-6, 0, 0), 'spine': (-3, 0, 0)}), {}),
           (Po.merged(r, {'head': (-26, 0, 0), 'neck': (-6, 0, 0), 'spine': (-3, 0, 0), 'chest': (2.4, 0, 0)}), {})]
    return _f(m, seq)


def bow(m, view):
    """A deep, formal bow: hands together in front of the thighs."""
    r = rest(m)
    hands = Po.arms(L=dict(swing=14, out=-8, elbow=12), R=dict(swing=14, out=-8, elbow=12))
    def b(k):
        return Po.merged(r, hands, {'spine': (24 * k, 0, 0), 'chest': (14 * k, 0, 0), 'head': (12 * k, 0, 0),
                                    'neck': (4 * k, 0, 0)})
    seq = [(b(0.2), {}), (b(0.6), {'expr': 'down'}), (b(1.0), {'expr': 'blink'}), (b(1.0), {'expr': 'blink'}),
           (b(1.0), {'expr': 'blink'}), (b(0.5), {'expr': 'down'}), (b(0.1), {})]
    return _f(m, seq)


# ------------------------------------------------------------------ lying, waking, sitting

def lying_pose(m, breath=0):
    p = rest(m)
    p.update(Po.arms(L=dict(swing=4, out=12, elbow=8), R=dict(swing=4, out=12, elbow=8)))
    p.update({'thighL': (0, 0, 3), 'thighR': (0, 0, -3), 'footL': (40, 0, 0), 'footR': (40, 0, 0),
              'chest': (-2.4 * breath, 0, 0), 'head': (4, 0, 0)})
    return Po.place(m, p, Po.lying_back(+1))


def asleep(m, view):
    """On her back between the roots, the hat over her face, breathing slowly."""
    return _f(m, [(lying_pose(m, 0), {'hat': 'face'}), (lying_pose(m, 1), {'hat': 'face'})])


def sit_ground_pose(m, lean=0.0, hands='ground'):
    """Sitting on the ground, legs out in front, hands beside the hips."""
    p = rest(m)
    p.update({'thighL': (-88, 0, 4), 'thighR': (-88, 0, -4), 'shinL': (4, 0, 0), 'shinR': (4, 0, 0),
              'footL': (-10, 0, 0), 'footR': (-10, 0, 0), 'spine': (lean, 0, 0), 'chest': (2, 0, 0)})
    if hands == 'ground':
        p.update(Po.arms(L=dict(swing=-14, out=22, elbow=4), R=dict(swing=-14, out=22, elbow=4)))
    elif hands == 'lap':
        p.update(Po.arms(L=dict(swing=40, out=8, elbow=52), R=dict(swing=40, out=8, elbow=52)))
    return p


def sitting(m, pose):
    """Rest a sitting pose on the ground with the pelvis over the ground point."""
    return Po.place(m, pose, np.eye(3), ground_pts=[('pelvis', (0, -1.0, -0.6), 1.6), ('shinL', (0, -3, 0), 1.6),
                                                    ('shinR', (0, -3, 0), 1.6)])


def sit_up(m, view):
    """Lying under the hat -> pushes up on her elbows, the hat slides into her lap -> sitting with
    the hat in her hands -> puts it back on."""
    lie = lying_pose(m, 0)
    up30 = Po.place(m, Po.merged(rest(m), {'thighL': (0, 0, 3), 'thighR': (0, 0, -3), 'footL': (40, 0, 0), 'footR': (40, 0, 0),
                                           'pelvis': (-60, 0, 0), 'spine': (10, 0, 0)},
                                 Po.arms(L=dict(swing=-30, out=20, elbow=60), R=dict(swing=-30, out=20, elbow=60))),
                    Po.lying_back(+1))
    sit_lap = sitting(m, sit_ground_pose(m, lean=6, hands='lap'))
    sit_on = sitting(m, Po.merged(sit_ground_pose(m, lean=2, hands='ground'),
                                  Po.arm('L', swing=150, out=30, elbow=80)))
    seq = [(lie, {'hat': 'face'}), (up30, {'hat': 'chest', 'expr': 'blink'}), (sit_lap, {'hat': 'lap', 'expr': 'down'}),
           (sit_lap, {'hat': 'lap'}), (sit_on, {'hat': 'head'}), (sitting(m, sit_ground_pose(m)), {'hat': 'head'})]
    return _f(m, seq)


def sit_ground(m, view):
    s0 = sitting(m, sit_ground_pose(m))
    s1 = sitting(m, Po.merged(sit_ground_pose(m), {'chest': (4.4, 0, 0)}))
    return _f(m, [(s0, {}), (s0, {}), (s1, {}), (s0, {'expr': 'blink'})])


def reach_sit(m, view):
    """From sitting, she reaches out to touch the pale branch: the hand goes through it."""
    base = sit_ground_pose(m)
    seq = []
    for sw, el, lean, ex in ((30, 40, 4, 'open'), (62, 10, 9, 'open'), (70, 4, 12, 'wide'), (70, 4, 12, 'wide'), (40, 30, 6, 'down')):
        p = Po.merged(base, Po.arm('R', swing=sw, out=6, elbow=el), {'spine': (lean, 0, 0)})
        seq.append((sitting(m, p), {'expr': ex}))
    return _f(m, seq)


def stand_up_ground(m, view):
    """From sitting on the ground: knees up, onto one knee, rise."""
    P = m.P
    knees = sitting(m, Po.merged(rest(m), {'thighL': (-70, 0, 6), 'thighR': (-70, 0, -6), 'shinL': (100, 0, 0),
                                          'shinR': (100, 0, 0), 'footL': (-30, 0, 0), 'footR': (-30, 0, 0),
                                          'spine': (16, 0, 0)},
                                 Po.arms(L=dict(swing=-10, out=24, elbow=6), R=dict(swing=-10, out=24, elbow=6))))
    crouch = Po.merged(rest(m), Po.legs_ik(P, {'L': (2.0, 0, 0), 'R': (-1.5, 0, 25)}, pelvis_y=P['hip'] - 5.5),
                       {'spine': (28, 0, 0), 'chest': (8, 0, 0)}, Po.arms(L=dict(swing=30, out=10, elbow=20), R=dict(swing=30, out=10, elbow=20)))
    half = Po.merged(rest(m), Po.legs_ik(P, {'L': (1.0, 0, 0), 'R': (-0.8, 0, 8)}, pelvis_y=P['hip'] - 2.4),
                     {'spine': (12, 0, 0)})
    seq = [(knees, {}), (crouch, {}), (half, {}), (rest(m), {})]
    return _f(m, seq)


# ------------------------------------------------------------------ standing script poses

def touch(m, view):
    """Reaches out to the door (the branch, the hut): the hand passes through it."""
    r = rest(m)
    seq = []
    for sw, el, lean, ex in ((24, 50, 0, 'open'), (58, 14, 4, 'open'), (72, 4, 8, 'wide'), (72, 4, 8, 'wide'),
                             (72, 4, 8, 'wide'), (40, 30, 3, 'down')):
        seq.append((Po.merged(r, Po.arm('R', swing=sw, out=5, elbow=el), {'spine': (lean, 0, 0)}), {'expr': ex}))
    return _f(m, seq)


def look_over(m, view):
    """At the cliff edge, leaning out to look down at the plain."""
    r = rest(m)
    def p(k):
        return Po.merged(r, {'spine': (20 + k, 0, 0), 'chest': (8, 0, 0), 'head': (22, 0, 0), 'neck': (6, 0, 0)},
                         Po.arms(L=dict(swing=-18, out=14, elbow=16), R=dict(swing=-18, out=14, elbow=16)))
    return _f(m, [(p(0), {'expr': 'down'}), (p(0), {'expr': 'down'}), (p(1.5), {'expr': 'down'}), (p(0), {'expr': 'blink'})])


def edge_pose(m, swing=0.0, look=0.0, breath=0):
    """Sitting on an edge (branch, cliff top), legs hanging; the seat is at the pelvis."""
    p = rest(m)
    p.update({'thighL': (-84, 0, 5), 'thighR': (-84, 0, -5), 'shinL': (74 + swing, 0, 0), 'shinR': (74 - swing, 0, 0),
              'footL': (14, 0, 0), 'footR': (14, 0, 0), 'spine': (4, 0, 0), 'chest': (2.4 * breath, 0, 0),
              'head': (look, 0, 0)})
    p.update(Po.arms(L=dict(swing=12, out=20, elbow=30), R=dict(swing=12, out=20, elbow=30)))
    # the seat (the underside of the hips) sits on y = seat height: the feet then hang just above
    # the cell's ground row
    return Po.place(m, p, np.eye(3), ground_pts=[('footL', (0, -0.6, 0.6), 1.0), ('footR', (0, -0.6, 0.6), 1.0)],
                    lift=1.0)


def sit_edge(m, view):
    seq = [(edge_pose(m, 10, 0, 0), {}), (edge_pose(m, 4, 0, 0), {}), (edge_pose(m, -6, 0, 1), {}),
           (edge_pose(m, -10, 0, 1), {}), (edge_pose(m, -4, 0, 0), {'expr': 'blink'}), (edge_pose(m, 6, 0, 0), {})]
    return _f(m, seq)


def stand_up(m, view):
    """From sitting on an edge to standing on it (she rises to look at the sky-shore)."""
    P = m.P
    e = edge_pose(m, 0, 0, 0)
    lean = Po.merged(e, {'spine': (24, 0, 0), 'thighL': (-70, 0, 5), 'thighR': (-70, 0, -5)},
                     Po.arms(L=dict(swing=-20, out=26, elbow=6), R=dict(swing=-20, out=26, elbow=6)))
    crouch = Po.merged(rest(m), Po.legs_ik(P, {'L': (1.6, 0, 0), 'R': (-1.6, 0, 0)}, pelvis_y=P['hip'] - 4.0),
                       {'spine': (18, 0, 0)})
    return _f(m, [(e, {}), (lean, {}), (crouch, {}), (rest(m), {'expr': 'wide'})])


def fall(m, view):
    """Falling through the faded branch: arms up, legs bent, hair and coat streaming up."""
    r = rest(m)
    def p(k):
        return Po.merged(r, Po.arms(L=dict(swing=40 + 8 * k, out=60, elbow=20), R=dict(swing=30 - 8 * k, out=70, elbow=30)),
                         {'thighL': (-40, 0, 6), 'thighR': (-20, 0, -6), 'shinL': (70, 0, 0), 'shinR': (50, 0, 0),
                          'spine': (-6, 0, 0), 'head': (-10, 0, 0)})
    up = (0, 0.9, 0)
    return Po.frames(m, [p(0), p(1), p(0), p(-1)], [{'expr': 'wide', 'mouth': 'open', 'hat': 'off'}] * 4,
                     wind=[up, up, up, up])


def hang_lantern(m, view):
    """Raises the lantern to the hook over a grave: arm half up, up, on her toes, hold, lantern
    left on the hook, arm down."""
    r = rest(m)
    P = m.P
    toes = Po.legs_ik(P, {'L': (0.3, 0.8, 30), 'R': (-0.3, 0.8, 30)}, pelvis_y=P['hip'] + 1)
    seq = [(Po.merged(r, Po.arm('R', swing=60, out=10, elbow=60)), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=150, out=10, elbow=20)), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=168, out=6, elbow=6), toes, {'head': (-14, 0, 0)}), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=168, out=6, elbow=6), toes, {'head': (-14, 0, 0)}), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=150, out=10, elbow=20)), {}),
           (Po.merged(r, Po.arm('R', swing=40, out=10, elbow=40)), {})]
    return _f(m, seq)


def eat(m, view):
    """A dango from the offering plate: to the mouth, bite, chew, down."""
    r = rest(m)
    seq = [(Po.merged(r, Po.arm('R', swing=40, out=10, elbow=60)), {'prop': 'dango3'}),
           (Po.merged(r, Po.arm('R', swing=40, out=18, elbow=130), {'head': (4, 0, 0)}), {'prop': 'dango3', 'mouth': 'open'}),
           (Po.merged(r, Po.arm('R', swing=36, out=18, elbow=122), {'head': (2, 0, 0)}), {'prop': 'dango2', 'mouth': 'chew', 'expr': 'happy'}),
           (Po.merged(r, Po.arm('R', swing=36, out=18, elbow=122)), {'prop': 'dango2', 'mouth': 'closed', 'expr': 'happy'}),
           (Po.merged(r, Po.arm('R', swing=30, out=10, elbow=50)), {'prop': 'dango2', 'mouth': 'chew'})]
    return _f(m, seq)


def climb(m, view):
    """Up the camphor's trunk (seen from behind): hand over hand, knees in turn."""
    P = m.P
    r = rest(m)
    def p(k):
        a = 1 if k == 0 else -1
        armsP = Po.arms(L=dict(swing=150 + 18 * a, out=14, elbow=40 - 20 * a), R=dict(swing=150 - 18 * a, out=14, elbow=40 + 20 * a))
        legs = {'thighL': (-50 - 30 * a, 0, 8), 'thighR': (-50 + 30 * a, 0, -8), 'shinL': (80 + 20 * a, 0, 0),
                'shinR': (80 - 20 * a, 0, 0), 'footL': (-20, 0, 0), 'footR': (-20, 0, 0)}
        return Po.merged(r, armsP, legs, {'spine': (8, 0, 0), 'pelvis_y': P['hip'] + 2 + a})
    return _f(m, [(p(0), {}), (Po.blend(p(0), p(1), 0.5), {}), (p(1), {}), (Po.blend(p(1), p(0), 0.5), {})])


def strain(m, view):
    """At the fallen beam: knees bent, hands under it, shaking, a little lift (no back-frame)."""
    P = m.P
    r = rest(m)
    def p(dy, sh):
        return Po.merged(r, Po.legs_ik(P, {'L': (2.2, 0, 0), 'R': (-1.4, 0, 0)}, pelvis_y=P['hip'] - 4 + dy, splay=8),
                         Po.arms(L=dict(swing=58, out=-4, elbow=30), R=dict(swing=58, out=-4, elbow=30)),
                         {'spine': (22, sh, 0), 'chest': (6, 0, 0), 'head': (-14, 0, 0)})
    seq = [(p(0, 0), {'expr': 'open'}), (p(0, 2), {'expr': 'shut', 'mouth': 'shout'}), (p(0, -2), {'expr': 'shut', 'mouth': 'shout'}),
           (p(1, 0), {'expr': 'shut', 'mouth': 'closed'})]
    return _f(m, seq)
