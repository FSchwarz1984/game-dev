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
    def b(k):
        sw = 14 - 0.75 * (38 * k)
        hands = Po.arms(L=dict(swing=sw, out=-8, elbow=12), R=dict(swing=sw, out=-8, elbow=12))
        return Po.merged(r, hands, {'spine': (24 * k, 0, 0), 'chest': (14 * k, 0, 0), 'head': (12 * k, 0, 0),
                                    'neck': (4 * k, 0, 0)})
    seq = [(b(0.2), {}), (b(0.6), {'expr': 'down'}), (b(1.0), {'expr': 'blink'}), (b(1.0), {'expr': 'blink'}),
           (b(1.0), {'expr': 'blink'}), (b(0.5), {'expr': 'down'}), (b(0.1), {})]
    return _f(m, seq)


# ------------------------------------------------------------------ lying, waking, sitting
# One family: sitting on the ground with the legs out in front, the trunk leaned back by `alpha`
# about the hips (90 = lying on her back, head away from where she faces). The legs stay on the
# ground through the whole sit-up, so the frames blend cleanly.

def sit_ground_pose(m, alpha=0.0, hands='ground', breath=0, lean=0.0):
    p = rest(m)
    a = alpha
    p.update({'pelvis': (-a, 0, 0), 'spine': (lean, 0, 0), 'chest': (2.4 * breath, 0, 0),
              'thighL': (-88 + a, 0, 4), 'thighR': (-88 + a, 0, -4), 'shinL': (4, 0, 0), 'shinR': (4, 0, 0),
              'footL': (-12, 0, 0), 'footR': (-12, 0, 0)})
    if hands == 'ground':
        p.update(Po.arms(L=dict(swing=-14, out=22, elbow=4), R=dict(swing=-14, out=22, elbow=4)))
    elif hands == 'side':
        p.update(Po.arms(L=dict(swing=2, out=10, elbow=6), R=dict(swing=2, out=10, elbow=6)))
    elif hands == 'elbows':
        p.update(Po.arms(L=dict(swing=-40, out=16, elbow=70), R=dict(swing=-40, out=16, elbow=70)))
    return p


def grounded(m, pose):
    """Rest a sitting or lying pose on the ground with the pelvis over the ground point."""
    return Po.place(m, pose, np.eye(3))


SIT = {'coat_pooled': True}


def asleep(m, view):
    """On her back between the roots, the hat over her face, breathing slowly."""
    p0 = grounded(m, Po.merged(sit_ground_pose(m, 90, 'side'), {'head': (6, 0, 0)}))
    p1 = grounded(m, Po.merged(sit_ground_pose(m, 90, 'side', breath=1), {'head': (6, 0, 0)}))
    return _f(m, [(p0, dict(SIT, hat='face')), (p1, dict(SIT, hat='face'))])


def sit_up(m, view):
    """Under the hat -> up on her elbows, the hat slides down -> sitting, catching it -> hat back on."""
    seq = [(grounded(m, Po.merged(sit_ground_pose(m, 90, 'side'), {'head': (6, 0, 0)})), dict(SIT, hat='face')),
           (grounded(m, sit_ground_pose(m, 62, 'elbows')), dict(SIT, hat='chest', expr='blink')),
           (grounded(m, Po.merged(sit_ground_pose(m, 25, 'ground'), Po.arm('L', swing=40, out=10, elbow=60))),
            dict(SIT, hat='chest', expr='down')),
           (grounded(m, Po.merged(sit_ground_pose(m, 0, 'ground'), Po.arm('L', swing=150, out=30, elbow=80))),
            dict(SIT, hat='head')),
           (grounded(m, sit_ground_pose(m, 0, 'ground')), dict(SIT, hat='head'))]
    return _f(m, seq)


def sit_ground(m, view):
    s0 = grounded(m, sit_ground_pose(m))
    s1 = grounded(m, sit_ground_pose(m, breath=1))
    return _f(m, [(s0, dict(SIT)), (s0, dict(SIT)), (s1, dict(SIT)), (s0, dict(SIT, expr='blink'))])


def reach_sit(m, view):
    """From sitting, she reaches out to touch the pale branch: the hand goes through it."""
    seq = []
    for sw, out, el, lean, ex in ((34, 14, 50, 4, 'open'), (70, 16, 14, 8, 'open'), (86, 18, 2, 12, 'wide'),
                                  (86, 18, 2, 12, 'wide'), (50, 14, 36, 6, 'down')):
        p = Po.merged(sit_ground_pose(m, lean=lean), Po.arm('R', swing=sw, out=out, elbow=el))
        seq.append((grounded(m, p), dict(SIT, expr=ex)))
    return _f(m, seq)


def stand_up_ground(m, view):
    """From sitting on the ground: knees up, onto her feet in a crouch, rise."""
    P = m.P
    knees = Po.merged(rest(m), Po.legs_ik(P, {'L': (6.5, 0, -10), 'R': (6.0, 0, -10)}, pelvis_y=2.6, splay=6),
                      {'spine': (18, 0, 0)},
                      Po.arms(L=dict(swing=-10, out=24, elbow=6), R=dict(swing=-10, out=24, elbow=6)))
    crouch = Po.merged(rest(m), Po.legs_ik(P, {'L': (2.0, 0, 0), 'R': (-1.5, 0, 25)}, pelvis_y=P['hip'] - 5.5),
                       {'spine': (28, 0, 0), 'chest': (8, 0, 0)}, Po.arms(L=dict(swing=30, out=10, elbow=20), R=dict(swing=30, out=10, elbow=20)))
    half = Po.merged(rest(m), Po.legs_ik(P, {'L': (1.0, 0, 0), 'R': (-0.8, 0, 8)}, pelvis_y=P['hip'] - 2.4),
                     {'spine': (12, 0, 0)})
    seq = [(knees, dict(SIT)), (crouch, {}), (half, {}), (rest(m), {})]
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
    """At the cliff edge, leaning out to look down at the plain, her right hand lifting the brim."""
    r = rest(m)
    def p(k):
        return Po.merged(r, {'spine': (12 + k, 0, 0), 'chest': (6, 0, 0), 'head': (16, 0, 0), 'neck': (4, 0, 0)},
                         Po.arm('L', swing=-14, out=14, elbow=16), Po.arm('R', swing=120, out=34, elbow=110))
    c = {'expr': 'down', 'hat': 'brim'}
    return _f(m, [(p(0), c), (p(0), c), (p(1.5), c), (p(0), dict(c, expr='blink'))])


def edge_pose(m, swing=0.0, look=0.0, breath=0):
    """Sitting on an edge (branch, cliff top), legs hanging; the seat is at the pelvis."""
    p = rest(m)
    p.update({'thighL': (-82, 0, 14), 'thighR': (-82, 0, -14), 'shinL': (74 + swing, 0, 0), 'shinR': (74 - swing, 0, 0),
              'footL': (14, 0, 0), 'footR': (14, 0, 0), 'spine': (4, 0, 0), 'chest': (2.4 * breath, 0, 0),
              'head': (look, 0, 0)})
    p.update(Po.arms(L=dict(swing=12, out=20, elbow=30), R=dict(swing=12, out=20, elbow=30)))
    # the seat (the underside of the hips) sits on y = seat height: the feet then hang just above
    # the cell's ground row
    return Po.place(m, p, np.eye(3), ground_pts=[('footL', (0, -0.6, 0.6), 1.0), ('footR', (0, -0.6, 0.6), 1.0)],
                    lift=1.0)


def sit_edge(m, view, hat='head'):
    """Sitting on an edge, calves swinging: the cliff top in the morning (hat on), the camphor's
    branch at dusk (sitBranch: the hat hangs on her back since the climb)."""
    c = {'hat': hat}
    seq = [(edge_pose(m, 10, 0, 0), c), (edge_pose(m, 4, 0, 0), c), (edge_pose(m, -6, 0, 1), c),
           (edge_pose(m, -10, 0, 1), c), (edge_pose(m, -4, 0, 0), dict(c, expr='blink')), (edge_pose(m, 6, 0, 0), c)]
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
    """Hangs the tenth... no: one of the nine lanterns on a grave's bamboo hook at face height: the
    lantern from her hip, raised forward, stretched to the hook on her toes, let go, arm down."""
    r = rest(m)
    P = m.P
    toes = Po.legs_ik(P, {'L': (0.4, 0.6, 26), 'R': (-0.4, 0.6, 26)}, pelvis_y=P['hip'] + 1)
    seq = [(Po.merged(r, Po.arm('R', swing=24, out=12, elbow=30)), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=82, out=8, elbow=40)), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=104, out=6, elbow=10), toes, {'spine': (4, 0, 0)}), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=104, out=6, elbow=10), toes, {'spine': (4, 0, 0)}), {'prop': 'lantern'}),
           (Po.merged(r, Po.arm('R', swing=96, out=6, elbow=14), {'spine': (2, 0, 0)}), {'prop': 'lantern_left'}),
           (Po.merged(r, Po.arm('R', swing=36, out=10, elbow=30)), {'prop': 'lantern_left'})]
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
    """Up the camphor's trunk, seen from behind: elbows wide round the trunk (they show below the
    brim; raised hands would vanish under it), hand over hand, knees up in turn."""
    P = m.P
    r = rest(m)
    def p(k):
        a = 1 if k == 0 else -1
        armsP = Po.arms(L=dict(swing=70 + 14 * a, out=62, elbow=80 + 10 * a, twist=-30),
                        R=dict(swing=70 - 14 * a, out=62, elbow=80 - 10 * a, twist=-30))
        legs = {'thighL': (-48 - 26 * a, 0, 12), 'thighR': (-48 + 26 * a, 0, -12), 'shinL': (78 + 18 * a, 0, 0),
                'shinR': (78 - 18 * a, 0, 0), 'footL': (-14, 0, 0), 'footR': (-14, 0, 0)}
        return Po.merged(r, armsP, legs, {'spine': (6, 0, 0), 'head': (-12, 0, 0), 'pelvis_y': P['hip'] + 3 + a})
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
