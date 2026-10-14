"""Saji's scripted animations (script-02-draft scene 10-12): pinned under the shrine's fallen eave
beam, crawling out, dusting herself off, hopping up onto the back-frame, sitting on it, pointing,
sniffing out luck."""

from __future__ import annotations

import math

import numpy as np

import geom as G
import poses as Po


def rest(m):
    return dict(m.rest_pose())


def _f(m, seq, wind=None):
    return Po.frames(m, [p for p, c in seq], [c for p, c in seq], wind=wind)


def front_pivot(m, pose, margin=1.0):
    """For a body lying toward the camera (the front view of the prone poses) the ground point
    moves to the front of the body (her head end): nothing may fall below the pivot row. The
    anchors ('hip' for the beam) say where the rest of her is."""
    p = dict(pose)
    bw = m.bones(p)
    zmax = max(bw[b][2, 3] for b in ('head', 'handL', 'handR')) + 5.0
    M = np.array(p['root_m'], float)
    M[2, 3] -= zmax + margin
    p['root_m'] = M
    return p


# ------------------------------------------------------------------ pinned and crawling
# Prone, head toward +Z (the view decides where that is: 'front' = head toward the camera, the
# beam then lies east-west across her hips). The upper body is propped on the elbows and the head
# is up, so the face, both arms and the whole upper body read; the legs kick up behind the beam.

def prone_pose(m, kick=0.0, prop=1.0, head=0.0, armk=0.0, turn=0.0):
    """Face down, trunk arched up from the hips on her forearms; `turn` turns her head toward the
    camera in the side views (+ = to her left), `kick` alternates the calves."""
    p = rest(m)
    p.update({'spine': (-18 * prop, 0, 0), 'chest': (-24 * prop, 0, 0), 'neck': (-8 * prop, 0, 0),
              'head': (-16 * prop + head, turn, 0)})
    p.update(Po.arms(L=dict(swing=70 + 16 * armk, out=24, elbow=70 - 20 * armk),
                     R=dict(swing=70 - 16 * armk, out=24, elbow=70 + 20 * armk)))
    p.update({'thighL': (8, 0, 6), 'thighR': (8, 0, -6), 'shinL': (88 + 42 * kick, 0, 0), 'shinR': (130 - 42 * kick, 0, 0),
              'footL': (24, 0, 0), 'footR': (24, 0, 0)})
    return Po.place(m, p, Po.prone(+1), centre_bone='pelvis',
                    ground_pts=[('pelvis', (0, 0.6, 1.8), 1.6), ('thighL', (0, -2.8, 1.0), 1.3), ('thighR', (0, -2.8, 1.0), 1.3),
                                ('farmL', (0, -1.6, 0), 1.0), ('farmR', (0, -1.6, 0), 1.0)])


TURN = {'front': 0.0, 'right': -38.0, 'left': 38.0}


def pinned(m, view):
    """Pinned under the beam across her hips: kicking, propped on her forearms, face to the
    camera, shouting. The beam is an occluder (see Saji.shapes)."""
    t = TURN.get(view, 0.0)
    b = {'beam': True}
    seq = [(prone_pose(m, 1.0, 1.0, 0, 0.0, t), dict(b, expr='shut', mouth='shout')),
           (prone_pose(m, 0.3, 1.0, 4, 0.6, t), dict(b, expr='shut', mouth='shout')),
           (prone_pose(m, -1.0, 1.0, 0, 1.0, t), dict(b, expr='wide', mouth='open')),
           (prone_pose(m, -0.3, 1.0, -4, 0.6, t), dict(b, expr='shut', mouth='shout'))]
    if view == 'front':
        seq = [(front_pivot(m, p), c) for p, c in seq]
    return _f(m, seq)


def crawl(m, view):
    """Out from under the beam on her forearms: one elbow forward, pull, the other."""
    t = TURN.get(view, 0.0) * 0.4
    seq = []
    for i in range(4):
        a = math.cos(i * math.pi / 2)
        p = prone_pose(m, kick=0.0, prop=0.7, head=6, armk=a, turn=t)
        p['thighL'] = (6 - 12 * a, 0, 6)
        p['thighR'] = (6 + 12 * a, 0, -6)
        p['shinL'] = (30 + 20 * a, 0, 0)
        p['shinR'] = (30 - 20 * a, 0, 0)
        seq.append((p, {'expr': 'down' if i % 2 else 'open', 'mouth': 'closed'}))
    if view == 'front':
        seq = [(front_pivot(m, p), c) for p, c in seq]
    return _f(m, seq)


# ------------------------------------------------------------------ standing

def dust(m, view):
    """Up again: pats her skirt down, left, right, looks up."""
    r = rest(m)
    patL = Po.arm('L', swing=26, out=4, elbow=40)
    patR = Po.arm('R', swing=26, out=4, elbow=40)
    seq = [(Po.merged(r, patL, {'spine': (8, 0, 0), 'head': (10, 0, 0)}), {'expr': 'down'}),
           (Po.merged(r, patL, Po.arm('L', swing=34, out=2, elbow=56), {'spine': (8, 0, 0), 'head': (10, 0, 0)}), {'expr': 'down'}),
           (Po.merged(r, patR, {'spine': (8, 0, 0), 'head': (10, 0, 0)}), {'expr': 'down'}),
           (Po.merged(r, patR, Po.arm('R', swing=34, out=2, elbow=56), {'spine': (8, 0, 0), 'head': (10, 0, 0)}), {'expr': 'down'}),
           (Po.merged(r, {'spine': (-2, 0, 0)}), {'expr': 'open'})]
    return _f(m, seq)


def hop(m, view):
    """Crouch, spring, tuck at the top, land (onto the back-frame or just for joy)."""
    P = m.P
    r = rest(m)
    crouch = Po.merged(r, Po.legs_ik(P, {'L': (1.0, 0, 0), 'R': (-1.0, 0, 0)}, pelvis_y=P['hip'] - 3.0),
                       Po.arms(L=dict(swing=-30, out=16, elbow=20), R=dict(swing=-30, out=16, elbow=20)), {'spine': (14, 0, 0)})
    spring = Po.merged(r, {'pelvis_y': P['hip'] + 3, 'footL': (30, 0, 0), 'footR': (30, 0, 0)},
                       Po.arms(L=dict(swing=60, out=30, elbow=30), R=dict(swing=60, out=30, elbow=30)), {'spine': (-4, 0, 0)})
    tuck = Po.merged(r, {'pelvis_y': P['hip'] + 6, 'thighL': (-50, 0, 6), 'thighR': (-50, 0, -6),
                         'shinL': (90, 0, 0), 'shinR': (90, 0, 0)},
                     Po.arms(L=dict(swing=40, out=50, elbow=60), R=dict(swing=40, out=50, elbow=60)))
    land = Po.merged(r, Po.legs_ik(P, {'L': (0.8, 0, 0), 'R': (-0.8, 0, 0)}, pelvis_y=P['hip'] - 2.0),
                     Po.arms(L=dict(swing=20, out=30, elbow=20), R=dict(swing=20, out=30, elbow=20)), {'spine': (8, 0, 0)})
    seq = [(crouch, {}), (spring, {'mouth': 'open'}), (tuck, {'expr': 'happy', 'mouth': 'open'}),
           (Po.blend(tuck, spring, 0.5), {'expr': 'happy'}), (land, {}), (r, {})]
    wind = [(0, 0, 0), (0, -0.2, 0), (0, 0.4, 0), (0, 0.3, 0), (0, -0.3, 0), (0, 0, 0)]
    return _f(m, seq, wind)


def point(m, view):
    """「那边在冒烟！」 points with her right arm, a little bounce."""
    r = rest(m)
    up = Po.arm('R', swing=110, out=14, elbow=4)
    seq = [(Po.merged(r, Po.arm('R', swing=60, out=14, elbow=40)), {'mouth': 'open'}),
           (Po.merged(r, up, {'spine': (-3, 0, 0)}), {'mouth': 'talk'}),
           (Po.merged(r, up, {'spine': (-3, 0, 0), 'pelvis_y': m.P['hip'] + 1}), {'mouth': 'open'}),
           (Po.merged(r, up, {'spine': (-3, 0, 0)}), {'mouth': 'talk'})]
    return _f(m, seq)


def sniff(m, view):
    """Sniffing out luck: nose up, eyes closed, two little sniffs."""
    r = rest(m)
    hands = Po.arms(L=dict(swing=-20, out=6, elbow=40), R=dict(swing=-20, out=6, elbow=40))
    seq = [(Po.merged(r, hands, {'head': (-14, 0, 0), 'neck': (-4, 0, 0)}), {'expr': 'happy'}),
           (Po.merged(r, hands, {'head': (-18, 0, 0), 'neck': (-6, 0, 0)}), {'expr': 'happy'}),
           (Po.merged(r, hands, {'head': (-14, 0, 0), 'neck': (-4, 0, 0)}), {'expr': 'happy'}),
           (Po.merged(r, hands, {'head': (-18, 0, 0), 'neck': (-6, 0, 0)}), {'expr': 'happy'}),
           (Po.merged(r, hands, {'head': (-6, 0, 0)}), {'expr': 'open'})]
    return _f(m, seq)


def talk(m, view):
    r = rest(m)
    seq = [(r, {'mouth': 'talk'}), (r, {'mouth': 'closed'}), (Po.merged(r, Po.arm('R', swing=40, out=16, elbow=60)), {'mouth': 'open'}),
           (r, {'mouth': 'closed'})]
    return _f(m, seq)


# ------------------------------------------------------------------ riding on the back-frame

def ride_pose(m, swing=0.0, breath=0, arms_mode='rail'):
    """Sitting on the frame's top rail: thighs forward, calves hanging and swinging, hands on the
    rail beside her hips. The seat (the underside of her hips) is the anchor 'seat'."""
    p = rest(m)
    p.update({'thighL': (-84, 0, 8), 'thighR': (-84, 0, -8), 'shinL': (80 + swing, 0, 0), 'shinR': (80 - swing, 0, 0),
              'footL': (6, 0, 0), 'footR': (6, 0, 0), 'chest': (2.4 * breath, 0, 0)})
    if arms_mode == 'rail':
        p.update(Po.arms(L=dict(swing=-10, out=26, elbow=10), R=dict(swing=-10, out=26, elbow=10)))
    return Po.place(m, p, np.eye(3), ground_pts=[('footL', (0, -0.5, 0.5), 0.9), ('footR', (0, -0.5, 0.5), 0.9)], lift=0.6)


def ride(m, view):
    seq = [(ride_pose(m, 12, 0), {}), (ride_pose(m, 4, 0), {}), (ride_pose(m, -8, 1), {}), (ride_pose(m, -12, 1), {}),
           (ride_pose(m, -4, 0), {'expr': 'blink'}), (ride_pose(m, 8, 0), {})]
    return _f(m, seq)


def ride_point(m, view):
    seq = []
    for i, (sw, el) in enumerate(((60, 40), (110, 4), (110, 4), (110, 4))):
        p = ride_pose(m, 6 * (-1) ** i)
        p.update(Po.arm('R', swing=sw, out=14, elbow=el))
        seq.append((p, {'mouth': 'talk' if i % 2 else 'open'}))
    return _f(m, seq)


def ride_talk(m, view):
    seq = []
    for i in range(4):
        p = ride_pose(m, 8 * math.cos(i * math.pi / 2))
        seq.append((p, {'mouth': 'talk' if i % 2 == 0 else 'closed'}))
    return _f(m, seq)
