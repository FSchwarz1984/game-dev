"""Shione's base set beyond locomotion: seiza (formal sitting), kneeling on one knee, the bow."""

from __future__ import annotations

import numpy as np

import poses as Po


def rest(m):
    return dict(m.rest_pose())


def _f(m, seq):
    return Po.frames(m, [p for p, c in seq], [c for p, c in seq])


def seiza_pose(m, breath=0):
    """Kneeling, sitting back on the heels, hands in her lap, back straight."""
    p = rest(m)
    p.update({'thighL': (-88, 0, 4), 'thighR': (-88, 0, -4), 'shinL': (172, 0, 0), 'shinR': (172, 0, 0),
              'footL': (-80, 0, 0), 'footR': (-80, 0, 0), 'chest': (2.4 * breath, 0, 0)})
    p.update(Po.arms(L=dict(swing=34, out=-2, elbow=46), R=dict(swing=34, out=-2, elbow=46)))
    return Po.place(m, p, np.eye(3), ground_pts=[('shinL', (0, -3.0, 0), 1.3), ('shinR', (0, -3.0, 0), 1.3),
                                                 ('footL', (0, -0.4, 0.5), 1.0), ('footR', (0, -0.4, 0.5), 1.0)])


def sit(m, view):
    s0, s1 = seiza_pose(m, 0), seiza_pose(m, 1)
    c = {'pooled': True}
    return _f(m, [(s0, c), (s0, c), (s1, c), (s1, c), (s0, dict(c, expr='blink')), (s0, c)])


def kneel_pose(m, breath=0):
    """Down on her right knee, the left foot planted, a hand on the left knee."""
    P = m.P
    p = rest(m)
    p.update({'thighL': (-82, 0, 6), 'shinL': (84, 0, 0), 'footL': (-2, 0, 0),
              'thighR': (-6, 0, -4), 'shinR': (94, 0, 0), 'footR': (40, 0, 0),
              'spine': (6, 0, 0), 'chest': (2.4 * breath, 0, 0)})
    p.update(Po.arm('L', swing=40, out=8, elbow=36))
    p.update(Po.arm('R', swing=6, out=10, elbow=16))
    return Po.place(m, p, np.eye(3), ground_pts=[('shinR', (0, 0, 0), 1.3), ('footL', (0, -0.4, 0.5), 1.0),
                                                 ('footR', (0, -0.4, 0.5), 1.0)])


def kneel(m, view):
    k0, k1 = kneel_pose(m, 0), kneel_pose(m, 1)
    c = {'pooled': True}
    return _f(m, [(k0, c), (k0, c), (k1, c), (k1, c), (k0, dict(c, expr='blink')), (k0, c)])


def bow(m, view):
    r = rest(m)
    def b(k):
        # hands slide down the front of the thighs: the arms hang, less the trunk's bend
        sw = 14 - 0.75 * (40 * k)
        hands = Po.arms(L=dict(swing=sw, out=-8, elbow=14), R=dict(swing=sw, out=-8, elbow=14))
        return Po.merged(r, hands, {'spine': (26 * k, 0, 0), 'chest': (14 * k, 0, 0), 'head': (12 * k, 0, 0),
                                    'neck': (4 * k, 0, 0)})
    seq = [(b(0.2), {}), (b(0.6), {'expr': 'down'}), (b(1.0), {'expr': 'blink'}), (b(1.0), {'expr': 'blink'}),
           (b(1.0), {'expr': 'blink'}), (b(0.5), {'expr': 'down'}), (b(0.1), {})]
    return _f(m, seq)
