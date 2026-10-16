"""垣外しをね (Shione Kaito): the oni grave-keeper, gentle and absurdly strong.

Reference: assets/reference/illustrations/shione.png and pack B. Silver-lilac hair with a blunt
fringe, a long low ponytail on HER RIGHT tied with red ribbons near the nape and again near the
ends; one small dark-red crescent horn on HER RIGHT; garnet eyes with two red marks under HER RIGHT
eye (the illustration and every pack image put horn, marks and ponytail on the same side); white
kimono with a plum collar and wide sleeves edged plum and lined pink; a red sash with a bow and
long tails; dark plum hakama to the ankles with the pink inner layer at the front slit; white tabi
boots on dark soles.

Asymmetric, so left and right views are rendered, never mirrored.
Proportions: 34.5 px to the crown (3.2 heads, head 10.6 px), the horn ~1 px above."""

from __future__ import annotations

import math

import numpy as np

import geom as G
from geom import ell, halfell, rcone, box, cone, cyl, skirt, torus
import style as St
from model import Model, ChainSpec, stamp
import face as Face
import humanoid as Hu

C = {
    'E': '#3b1422', 'e': '#9e3548', 'q': '#cc4b5d', 'l': '#ffffff',
    'm': '#b06a62', 'M': '#7a2e3a', 'b': '#f5a0a2', 'k': '#c0394c',
}


class Shione(Model):
    NAME = 'shione'
    FRAME = (56, 60)
    PIVOT = (28, 52)

    def props(self):
        return {
            'hip': 15.0, 'spine': 2.3, 'chest': 2.6, 'neck': 2.6, 'neck2': 1.2,
            'sh_w': 3.1, 'sh_h': 1.5, 'uarm': 4.1, 'farm': 3.7,
            'hip_w': 1.45, 'hip_d': 0.6, 'thigh': 6.6, 'shin': 6.5, 'ankle': 1.3,
            'ao': 2.4, 'shadow_k': 8.0, 'line_gap': 1.6,
            'cycles': {
                'walk': {'stride': 11.0, 'lift': 1.7, 'bob': Hu.bob_walk, 'arm': 16.0, 'arm_out': 8.0, 'elbow': 16.0,
                         'elbow_swing': 8.0, 'lean': 2.0, 'lean2': 0.5, 'twist': 3.0, 'toe_off': 18.0, 'heel': 8.0},
                'run': {'stride': 14.0, 'lift': 3.2, 'bob': Hu.bob_run, 'arm': 28.0, 'arm_out': 10.0, 'elbow': 58.0,
                        'elbow_swing': 16.0, 'lean': 8.0, 'lean2': 3.0, 'twist': 5.0, 'toe_off': 26.0, 'heel': 4.0,
                        'stance': 0.38},
            },
        }

    def rest_pose(self):
        return {'uarmL': (0, 0, 7), 'uarmR': (0, 0, -7), 'farmL': (-18, 0, 0), 'farmR': (-18, 0, 0),
                'thighL': (0, 0, 1.0), 'thighR': (0, 0, -1.0)}

    def palette(self):
        return St.Palette([
            St.Mat('hair', ['#73647c', '#a08ea1', '#c6b3c1', '#e3d3da'], '#3b3150', [0.30, 0.50, 0.76], line=1),
            St.Mat('hairhi', ['#a08ea1', '#c6b3c1', '#e3d3da', '#f6eef2'], '#3b3150', [0.30, 0.50, 0.70], line=1),
            St.Mat('hairln', ['#5a4e62', '#73647c', '#a08ea1', '#c6b3c1'], '#3b3150', [0.30, 0.50, 0.76], line=1),
            St.Mat('plumln', ['#1e121c', '#2a1a27', '#3f2a3b', '#563b50'], '#2a0f1a', [0.30, 0.50, 0.80], line=0),
            St.Mat('horn', ['#3f1520', '#56202d', '#86313f'], '#2a0f1a', [0.45, 0.70], prio=3.0),
            St.Mat('white', ['#a093a9', '#cdbfcc', '#ede5e3', '#fcf9f6'], '#3b3150', [0.32, 0.52, 0.80], line=1),
            St.Mat('plum', ['#2a1a27', '#3f2a3b', '#563b50', '#73526b'], '#2a0f1a', [0.30, 0.50, 0.80], line=0),
            St.Mat('pink', ['#b47c87', '#daa3a7', '#f3cbc8'], '#4a2430', [0.45, 0.74], line=0),
            St.Mat('red', ['#6d2333', '#9e3548', '#cc4b5d'], '#2a0f1a', [0.42, 0.72], prio=2.0, line=0),
            St.Mat('skin', ['#d4907f', '#efbca8', '#fde7d8'], '#6a3438', [0.42, 0.62], line=1, min_tone=1),
            St.Mat('sole', ['#2a1a27', '#3f2a3b', '#563b50'], '#2a0f1a', [0.45, 0.72]),
        ], extra=C)

    def chain_specs(self):
        return {
            'tail': ChainSpec('head', (-3.6, 3.0, -2.4), 6, 2.8, rest=(-0.12, -1, -0.15), damping=0.20, stiff=0.10,
                              gravity=0.35, wind=1.0, collide=self._tail_collide),
            'stl': ChainSpec('spine', (0.9, -0.4, 2.7), 4, 1.7, damping=0.16, stiff=0.08, gravity=0.30, wind=1.1),
            'str': ChainSpec('spine', (-0.6, -0.4, 2.75), 4, 1.8, damping=0.16, stiff=0.08, gravity=0.30, wind=1.1),
            'hem': ChainSpec('spine', (0, 0.6, 0), 1, 15.0, damping=0.28, stiff=0.40, gravity=0.30, wind=0.5),
            'slvL': ChainSpec('farmL', (0, -1.2, -0.3), 1, 3.0, damping=0.22, stiff=0.18, gravity=0.35, wind=0.8),
            'slvR': ChainSpec('farmR', (0, -1.2, -0.3), 1, 3.0, damping=0.22, stiff=0.18, gravity=0.35, wind=0.8),
        }

    def _tail_collide(self, pts, bw):
        """The ponytail hangs outside her right shoulder and sleeve, behind the arm line."""
        m = bw['chest']
        inv = np.linalg.inv(m)
        out = pts.copy()
        for i in range(1, len(pts)):
            p = inv @ np.array([pts[i][0], pts[i][1], pts[i][2], 1.0])
            # stay outside an ellipse around the torso + sleeve (x right side is negative)
            ex, ez = 4.6, 3.4
            d = (p[0] / ex) ** 2 + (p[2] / ez) ** 2
            if d < 1.0 and p[1] < 3.0:
                k = 1.0 / math.sqrt(max(d, 1e-6))
                p[0] *= k; p[2] *= k
            out[i] = (m @ p)[:3]
        return out

    # ------------------------------------------------------------------ shapes
    def head_shapes(self, ctx):
        S = []
        S += [ell('head', (4.7, 4.8, 4.3), 'skin', at=(0, 4.9, 0.3), part='face', group='face', k=1.2),
              ell('head', (3.6, 2.7, 3.1), 'skin', at=(0, 2.6, 1.2), part='face', group='face', k=1.4)]
        hair = dict(group='hair', k=0.8)
        S += [ell('head', (5.05, 5.15, 4.85), 'hair', at=(0, 5.3, -0.3), cut=(0, -1.0, 0.32, -4.3), part='hair',
                  bands=[(4, 0, 6, 'hairln', 0, 0, 0, 50), (1, 2.0, 2.8, 'hairhi')], **hair)]
        # blunt fringe with longer strands at its sides
        S += [ell('head', (4.5, 2.1, 1.5), 'hair', at=(0, 7.4, 3.3), cut=(0, -1.0, 0, -5.8), part='bangs',
                  bands=[(1, 1.0, 1.7, 'hairhi')], **hair)]
        for sx in (1, -1):
            S += [rcone('head', (sx * 3.9, 7.4, 2.6), (sx * 4.1, 2.6, 2.4), 0.95, 0.55, 'hair', part='bangs', **hair)]
        # her left: hair falls loose behind the shoulder; her right is gathered into the ponytail
        S += [rcone('head', (4.4, 6.2, -0.8), (4.7, 1.8, -1.0), 1.35, 0.85, 'hair', part='lockL', **hair),
              ell('head', (4.9, 4.4, 3.1), 'hair', at=(0, 4.0, -2.3), part='hair', **hair)]
        # the horn on her right, above the temple: a crescent curving up and back
        S += [rcone('head', (-3.9, 7.6, 1.2), (-4.6, 9.4, 0.6), 0.75, 0.5, 'horn', part='horn'),
              rcone('head', (-4.6, 9.4, 0.6), (-4.3, 10.6, -0.4), 0.5, 0.22, 'horn', part='horn')]
        # the first ribbon at the root of the ponytail (bow loops)
        S += [ell('head', (0.9, 1.1, 0.7), 'red', at=(-3.9, 2.8, -2.6), R=G.Rz(35), part='ribbon'),
              ell('head', (0.8, 1.0, 0.6), 'red', at=(-4.5, 1.6, -2.2), R=G.Rz(-20), part='ribbon')]
        return S

    def tail_shapes(self, ctx):
        S = []
        rr = [1.55, 1.7, 1.75, 1.6, 1.45, 1.6, 1.3]
        for j in range(6):
            bands = []
            if j == 0:
                bands = [(1, -1.8, 0.2, 'red')]
            if j == 4:
                bands = [(1, -2.9, -1.5, 'red')]
            S += [rcone(f'tail{j}', (0, 0, 0), (0, -2.8, 0), rr[j], rr[j + 1], 'hair', part='tail', group='tail', k=0.6,
                        bands=[(4, 0, 22, 'hairln', 0, 0, 0, 120)] + bands)]
        # the loose ends flare a little under the lower tie
        S += [ell('tail5', (1.8, 1.9, 1.3), 'hair', at=(0, -2.2, 0), part='tail', group='tail', k=0.6)]
        return S

    def shapes(self, ctx):
        bw = ctx['bones']
        S = self.head_shapes(ctx) + self.tail_shapes(ctx)
        # neck, kimono top with a plum collar
        S += [rcone('neck', (0, -0.4, 0), (0, 1.8, 0), 1.05, 1.0, 'skin', part='neck'),
              ell('spine', (2.7, 2.4, 2.0), 'white', at=(0, 0.8, 0.05), part='torso', group='torso', k=1.0),
              ell('chest', (3.0, 2.7, 2.15), 'white', at=(0, 0.3, 0.1), part='torso', group='torso', k=1.0),
              ell('chest', (0.9, 1.4, 0.5), 'plum', at=(0, 1.9, 1.85), R=G.Rx(-18), part='collar')]
        # sash: red, wide, a bow in front, two long tails
        S += [cyl('spine', 1.1, 2.95, 'red', round_=0.45, at=(0, 0.6, 0), part='sash'),
              ell('spine', (1.25, 0.9, 0.6), 'red', at=(-0.9, 1.0, 2.7), R=G.Rz(25), part='bow'),
              ell('spine', (1.15, 0.85, 0.6), 'red', at=(0.9, 1.0, 2.7), R=G.Rz(-25), part='bow'),
              ell('spine', (0.55, 0.55, 0.55), 'red', at=(0, 0.8, 2.95), part='bow')]
        for nm in ('stl', 'str'):
            for j in range(4):
                S += [box(f'{nm}{j}', (0.6, 0.95, 0.14), 'red', round_=0.1, at=(0, -0.85, 0), part='stail')]
        # hakama: plum, pleated, to the ankles; a narrow front slit shows the pink inner layer
        L = ctx.get('hem_len', 1.0)
        if ctx.get('pooled'):
            # kneeling / sitting: the hakama pools round her hips down to the ground
            p = bw['pelvis'][:3, 3]
            top = p[1] + 1.6
            bw['hem0'] = G.M4(np.eye(3), (p[0], top, p[2] + 0.6))
            L = top / 14.4
        hz = 7.2 * L
        hem_r = 5.6 + (1.0 - L) * 6.0
        hk = dict(part='hakama', group='hakama', k=0.0)
        for cut in ((-1, -0.05 / L, 0, -0.75), (1, -0.05 / L, 0, -0.75), (0, 0, 1, 0.3)):
            S += [skirt('hem0', hz, hem_r, 3.1, 'plum', sx=1.0, sz=0.8, wave=(0.35, 7, 0.2), flare=(0.28, 13, 0.0),
                        round_=0.4, at=(0, -hz, 0), cut=cut, bands=[(4, 0, 6, 'plumln', 0, 0, 0, 30)], **hk)]
        S += [skirt('hem0', hz - 0.2, hem_r - 1.0, 2.7, 'pink', sx=1.0, sz=0.82, wave=(0.2, 5, 0.0), round_=0.3,
                    at=(0, -hz - 0.1, 0), part='inner')]
        # legs (hidden by the hakama, but they shape the hem) and boots
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('thigh' + s, (0, 0, 0), (0, -6.6, 0), 1.75, 1.5, 'plum', part='leg' + s),
                  rcone('shin' + s, (0, 0.2, 0), (0, -6.2, 0.1), 1.45, 1.15, 'plum', part='leg' + s),
                  box('foot' + s, (1.05, 0.95, 1.65), 'white', round_=0.7, at=(0, -0.38, 0.45), part='boot' + s,
                      bands=[(1, -1.0, -0.62, 'sole')]),
                  cyl('foot' + s, 0.6, 1.1, 'white', round_=0.3, at=(0, 0.55, 0.05), part='boot' + s)]
        # arms: white sleeves edged plum and lined pink, hanging bags, hands
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('uarm' + s, (0, 0.3, 0), (0, -3.9, 0), 1.45, 1.75, 'white', part='arm' + s),
                  cone('farm' + s, 1.75, 2.7, 1.75, 'white', round_=0.3, at=(0, -1.65, 0.0), part='arm' + s,
                       bands=[(1, -1.8, -1.35, 'plum'), (1, -1.35, -1.0, 'pink')]),
                  box(f'slv{s}0', (0.75, 2.3, 1.95), 'white', round_=0.7, at=(0, -1.5, 0.0), part='slv' + s,
                      bands=[(1, -2.4, -1.85, 'plum'), (1, -1.85, -1.45, 'pink')]),
                  ell('hand' + s, (0.78, 0.9, 0.78), 'skin', at=(0, -0.4, 0.15), part='hand' + s)]
        return S

    # ------------------------------------------------------------------ face
    def features(self, ctx):
        def on_face(x, y):
            cx, cy, cz, rx, ry, rz = 0, 4.9, 0.3, 4.7, 4.8, 4.3
            t = 1 - (x / rx) ** 2 - ((y - cy) / ry) ** 2
            z = cz + rz * math.sqrt(max(t, 0))
            n = (x / rx ** 2, (y - cy) / ry ** 2, (z - cz) / rz ** 2)
            return (x, y, z), n
        f = {}
        for nm, (x, y) in {'eyeL': (2.5, 4.15), 'eyeR': (-2.5, 4.15), 'mouth': (0.0, 1.75),
                           'blushL': (3.2, 2.8), 'blushR': (-3.2, 2.8), 'marks': (-2.5, 2.3)}.items():
            p, n = on_face(x, y)
            f[nm] = ('head', p, n)
        return f

    def decals(self, img, px, feats, ctx):
        cmap = {k: St.hexrgb(v) for k, v in C.items()}
        skin = {self.pal.ids['skin']}

        def marks(img, px, feats):
            # two short red strokes under her right eye (1 px each, a pixel apart)
            f = feats.get('marks')
            if f is None or Face.view_class(f[3][2]) is None:
                return
            vc = Face.view_class(f[3][2])
            if Face.hi_res():
                # a finer grid (build.py --ppm): the strokes stay a pixel, the gap between them grows
                grid = ['k..k'] if vc == 'front' else (['k.k'] if vc == 'three' else ['k'])
            else:
                grid = ['k.k'] if vc == 'front' else (['kk'] if vc == 'three' else ['k'])
            stamp(img, px, f[0], f[1], grid, cmap, (len(grid[0]) / 2, 0.5), depth=f[2], only_on=skin)
        Face.paint_face(img, px, feats, cmap, expr=ctx.get('expr', 'open'), mouth=ctx.get('mouth', 'closed'),
                        blush=False, skin_ids=skin, extra=marks)

    def anchors(self, ctx):
        return {'hand': ('handR', (0, -0.6, 0)), 'head': ('head', (0, 11.5, 0))}


# =============================================================================================
# Sheet description (tools/art/sprite3d/build.py)

import anims as A  # noqa: E402

D8, D4 = ('front', 'front_right', 'right', 'back_right', 'back', 'back_left', 'left', 'front_left'), ('front', 'right', 'back', 'left')
SHEETS = {'main': None}
_ALL = tuple(SHEETS)
_M = Shione()
import shione_acts as T  # noqa: E402

F4 = ('front', 'right', 'back', 'left')


def _a(fn, fps, loop, views, sheets=_ALL):
    return {'make': fn, 'fps': fps, 'loop': loop, 'views': views, 'sheets': sheets}


ANIMS = {
    'idle': A.idle_spec(6, D8, _ALL),
    'walk': A.with_speed(A.loco_spec('walk', 8, 12, D8, _ALL, wind=0.10), _M),
    'run': dict(A.with_speed(A.loco_spec('run', 8, 15, D8, _ALL, wind=0.22), _M), **{'from': 3.9}),
    'sit': _a(T.sit, 3, True, F4),
    'kneel': _a(T.kneel, 3, True, F4),
    'bow': _a(T.bow, 6, False, F4),
}
