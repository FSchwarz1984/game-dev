"""The dosojin (道祖神) by the road: two stone figures side by side on one low stone, the right one
under an extremely wide bamboo-and-sedge hat (斗笠: her hat, the clue in plain sight); before them a
stone ledge with a dish and two white dango (script-02 scene 2). The dango are separate nodes
(Dango_0, Dango_1) so the story can take one and fade the other (遠化: the far mesh is in the node's
meta w3a_far_mesh)."""
from __future__ import annotations

import math

import numpy as np

from ..core import rng
from . import kit as K
from .common import export_prop

STONE = K.col('#86837a')
HAT = K.col('#cdb98c')
CORD = K.col('#9a3b2c')
DANGO = K.col('#f2eee4')


def figure(P, h, seed, hands=True):
    """A small rounded stone figure (a hooded body, a round head), base at y = 0."""
    body_h = h * 0.62
    t = np.clip(P[..., 1] / body_h, 0, 1)
    r_body = 0.17 + 0.03 * np.sin(t * math.pi) - 0.05 * t ** 2
    q = P.copy()
    q[..., 2] = q[..., 2] * 1.25                      # a little flatter front to back
    body = np.maximum(np.hypot(q[..., 0], q[..., 2]) - r_body, np.maximum(-P[..., 1], P[..., 1] - body_h))
    body = np.maximum(body, -P[..., 1])
    sh = K.sd_ellipsoid(P - np.array([0, body_h * 0.92, 0]), (0.16, 0.08, 0.13))   # shoulders
    body = K.smin(body, sh, 0.05)
    head = K.sd_ellipsoid(P - np.array([0, h - 0.11, 0.0]), (0.105, 0.115, 0.1))
    d = K.smin(body, head, 0.035)
    if hands:                                           # hands together in front (a soft bump)
        d = K.smin(d, np.linalg.norm(P - np.array([0, body_h * 0.62, 0.13]), axis=-1) - 0.05, 0.04)
    return d + K.weathered(P, 0.008, 0.06, seed)


def hat_piece(seed, R):
    """斗笠: a wide shallow cone with a rolled rim, a small knob at the top; tilted a little."""
    prof = [(0.0, 0.2), (0.035, 0.19), (0.1, 0.158), (0.25, 0.092), (0.41, 0.032), (0.49, 0.008), (0.502, -0.004),
            (0.49, -0.013), (0.42, 0.01), (0.25, 0.068), (0.1, 0.13), (0.035, 0.158), (0.0, 0.162)]

    def shade(P, N):
        # woven rings: a darker ring every 7 cm, a lighter top
        rr = np.hypot(P[:, 0], P[:, 2])
        m = np.ones((len(P), 3))
        m[(np.floor(rr / 0.07) % 2) == 0] *= 0.93
        m *= (0.9 + 0.1 * np.clip(N[:, 1], 0, 1))[:, None]
        return m
    return K.lathe(prof, HAT, n=16, pattern='thatch', amount=0.2, var=0.04, seed=seed, cap_top=False, cap_bottom=False,
                   shade=shade)


def build(out):
    R = rng(8001)
    pieces = []
    # the shared low stone (台石)
    def base_f(P):
        return K.sd_box(P - np.array([0, 0.06, 0]), (0.78, 0.08, 0.3), 0.05) + K.weathered(P, 0.012, 0.1, 8002)
    pieces.append(K.sdf_piece(base_f, (-0.86, -0.05, -0.35), (0.86, 0.18, 0.35), STONE * 0.92, h=0.025, tris=200,
                              pattern='stone', amount=0.8, var=0.06, seed=8002))
    figs = [(-0.42, 0.8, 8003, 0.08), (0.4, 0.74, 8004, -0.06)]
    for x, h, sd, yaw in figs:
        f = lambda P, h=h, sd=sd: figure(P, h, sd)
        pc = K.sdf_piece(f, (-0.24, -0.02, -0.22), (0.24, h + 0.04, 0.24), STONE * (1 + R.normal(0, 0.03)), h=0.014,
                         tris=540, pattern='stone', amount=0.65, var=0.06, seed=sd)
        pieces.append(pc.moved(K.rot_y(yaw), (x, 0.13, 0.0)))
    # the hat on the right figure, tilted forward and to the side
    hat = hat_piece(8005, R)
    Rh = K.rot_y(0.3) @ K.rot_x(-0.22) @ K.rot_z(-0.08)          # tipped back: the face shows under the brim
    pieces.append(hat.moved(Rh, (0.41, 0.13 + 0.74 - 0.1, -0.02)))
    # its cord, hanging under the brim
    cord = K.rod([[0.3, 0.8, 0.1], [0.33, 0.66, 0.16], [0.4, 0.62, 0.18], [0.47, 0.66, 0.16], [0.51, 0.8, 0.1]], 0.009,
                 CORD, n=3, cap=True, step=0.03, var=0.0, dirt=False)
    pieces.append(cord)
    # the stone ledge in front, and the dish on it
    def ledge_f(P):
        return K.sd_box(P - np.array([0, 0.09, 0]), (0.36, 0.09, 0.15), 0.035) + K.weathered(P, 0.01, 0.08, 8006)
    pieces.append(K.sdf_piece(ledge_f, (-0.42, -0.05, -0.2), (0.42, 0.22, 0.2), STONE * 0.88, h=0.02, tris=160,
                              pattern='stone', amount=0.7, var=0.06, seed=8006).moved(None, (0.0, 0.0, 0.52)))
    dish = K.lathe([(0.0, 0.0), (0.1, 0.0), (0.15, 0.025), (0.165, 0.036), (0.15, 0.04), (0.1, 0.016), (0.0, 0.016)],
                   K.col('#7a776f'), n=12, pattern='stone', amount=0.1, var=0.03, seed=8007)
    pieces.append(dish.moved(None, (0.0, 0.18, 0.52)))
    prop = K.Prop('dosojin', 8001).add(pieces)

    def dango(sd):
        p = K.lathe([(0.0, 0.0), (0.045, 0.008), (0.065, 0.04), (0.06, 0.072), (0.04, 0.092), (0.0, 0.1)], DANGO, n=10,
                    var=0.0, seed=sd, dirt=False)
        return K.Prop('dango', sd).add(p)
    extras = {'Dango_0': (dango(8010), (-0.06, 0.196, 0.52)), 'Dango_1': (dango(8011), (0.07, 0.196, 0.54))}
    cat = {'footprint': [[-0.4, 0.0, 0.42], [0.4, 0.0, 0.42], [0.0, 0.52, 0.42]], 'tags': ['interact', 'stone', 'sacred'],
           'notes': 'Two stone figures, the right one under her wide hat (斗笠); a dish with two white dango on the '
                    'ledge before them. Nodes Dango_0 / Dango_1 can be hidden or faded (meta w3a_far_mesh).',
           'anchors': {'interact': [0.0, 0.0, 1.25], 'dango': [[-0.06, 0.196, 0.52], [0.07, 0.196, 0.54]],
                       'hat': [0.41, 0.97, -0.02]}}
    return {'dosojin': export_prop(out, 'dosojin', 'props', prop, cat, porosity=0.5, extras=extras, budget=2400)}
