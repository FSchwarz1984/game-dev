"""家守さぢ (Saji Yamori): the zashiki-warashi who rides on Tsuzumi's back-frame.

Reference: assets/reference/illustrations/saji.png and pack C. Red messy bob with a teal alice band
and a curled ahoge (her right), teal eyes, a pale-green capelet with a teal edge and a gold bell at
the throat, plum kimono top, wide white sleeves with red lining, a teal obi with the bow on her
left, a red bell skirt with a cream wavy stripe, bare knees, white socks tied with red ribbons,
maroon boots.

Proportions (R-4: she read as "a fat, short, bloated dwarf"): 31 px to the crown, head 10.3 px
(3 heads, like the other two), shoulders 7 px, waist 5 px, the skirt hem 12 px wide at the knee,
legs visible below it. The youngest and shortest of the three, slim."""

from __future__ import annotations

import math

import numpy as np

import geom as G
from geom import ell, halfell, rcone, box, cone, cyl, skirt
import style as St
from model import Model, ChainSpec
import face as Face
import humanoid as Hu

C = {
    'E': '#1b3a3f', 'e': '#2f7d7a', 'q': '#4fa8a0', 'l': '#ffffff',
    'm': '#a8564f', 'M': '#7a2b33', 'b': '#f5a0a2',
}


class Saji(Model):
    NAME = 'saji'
    FRAME = (48, 48)
    PIVOT = (24, 44)

    def props(self):
        return {
            'hip': 12.6, 'spine': 2.0, 'chest': 2.2, 'neck': 2.4, 'neck2': 1.0,
            'sh_w': 2.9, 'sh_h': 1.4, 'uarm': 3.6, 'farm': 3.2,
            'hip_w': 1.35, 'hip_d': 0.6, 'thigh': 5.6, 'shin': 5.2, 'ankle': 1.2,
            'ao': 2.2, 'shadow_k': 8.0, 'line_gap': 1.6,
            'cycles': {
                'walk': {'stride': 6.4, 'lift': 1.6, 'bob': Hu.bob_walk, 'arm': 20.0, 'arm_out': 9.0, 'elbow': 16.0,
                         'elbow_swing': 10.0, 'lean': 3.0, 'lean2': 1.0, 'twist': 4.0, 'toe_off': 22.0, 'heel': 8.0},
                'run': {'stride': 8.6, 'lift': 3.0, 'bob': Hu.bob_run, 'arm': 34.0, 'arm_out': 12.0, 'elbow': 62.0,
                        'elbow_swing': 18.0, 'lean': 9.0, 'lean2': 3.0, 'twist': 6.0, 'toe_off': 30.0, 'heel': 4.0,
                        'stance': 0.38},
            },
        }

    def rest_pose(self):
        return {'uarmL': (0, 0, 8), 'uarmR': (0, 0, -8), 'farmL': (-14, 0, 0), 'farmR': (-14, 0, 0),
                'thighL': (0, 0, 1.5), 'thighR': (0, 0, -1.5)}

    def palette(self):
        return St.Palette([
            St.Mat('hair', ['#691a2b', '#9b2434', '#cf3439', '#f0533f'], '#36101c', [0.30, 0.48, 0.74], line=1),
            St.Mat('hairhi', ['#9b2434', '#cf3439', '#f0533f', '#ff8a62'], '#36101c', [0.30, 0.48, 0.66], line=1),
            St.Mat('skirt', ['#691a2b', '#9b2434', '#cf3439', '#f0533f'], '#36101c', [0.32, 0.50, 0.80], line=1),
            St.Mat('teal', ['#163b42', '#215a5d', '#2f7d7a', '#4fa8a0'], '#13282c', [0.30, 0.50, 0.80], prio=1.6, line=1),
            St.Mat('mint', ['#94c0a6', '#c2dfc4', '#e3f1dc'], '#13282c', [0.45, 0.76], line=0),
            St.Mat('plum', ['#34152f', '#4e2045', '#702e5e', '#93437a'], '#36101c', [0.30, 0.50, 0.80], line=1),
            St.Mat('white', ['#9d90aa', '#cdc2cd', '#ede5d8', '#fcf8ef'], '#3b3150', [0.32, 0.52, 0.80], line=1),
            St.Mat('gold', ['#a5702a', '#e2ae3c', '#ffe58c'], '#36101c', [0.45, 0.72], prio=6.0),
            St.Mat('skin', ['#d4907f', '#efbca8', '#fde7d8'], '#6a3438', [0.42, 0.62], line=1, min_tone=1),
            St.Mat('boot', ['#2e1220', '#4a1d30', '#6a2a3e', '#8a3c52'], '#36101c', [0.30, 0.50, 0.80], line=1),
            St.Mat('ribbon', ['#9b2434', '#cf3439', '#f0533f'], '#36101c', [0.45, 0.75], prio=2.5),
        ], extra=C)

    def chain_specs(self):
        return {
            'hem': ChainSpec('spine', (0, 0.4, 0), 1, 6.5, damping=0.25, stiff=0.30, gravity=0.30, wind=0.6),
            'bowt': ChainSpec('spine', (2.5, 0.0, 1.05), 3, 1.5, damping=0.18, stiff=0.10, gravity=0.30, wind=1.0),
            'slvL': ChainSpec('farmL', (0, -1.4, -0.2), 1, 2.0, damping=0.22, stiff=0.20, gravity=0.35, wind=0.8),
            'slvR': ChainSpec('farmR', (0, -1.4, -0.2), 1, 2.0, damping=0.22, stiff=0.20, gravity=0.35, wind=0.8),
        }

    def head_bones(self):
        return ('head',)

    # ------------------------------------------------------------------ shapes
    def head_shapes(self, ctx):
        S = []
        S += [ell('head', (4.6, 4.6, 4.2), 'skin', at=(0, 4.6, 0.3), part='face', group='face', k=1.2),
              ell('head', (3.5, 2.6, 3.0), 'skin', at=(0, 2.5, 1.1), part='face', group='face', k=1.4)]
        hair = dict(group='hair', k=0.8)
        # cap: the hairline is high at the forehead, at the temples beside the eyes, low at the nape;
        # the alice band crosses it ahead of the crown, the highlight ring sits on its upper slope
        S += [ell('head', (4.95, 4.95, 4.75), 'hair', at=(0, 5.1, -0.3), cut=(0, -1.0, 0.36, -4.0), part='hair',
                  bands=[(1, 2.2, 2.9, 'hairhi'), (2, 1.6, 2.6, 'teal')], **hair)]
        # fringe: a slab over the forehead whose lower edge is cut into locks, with a parted gap
        S += [ell('head', (4.2, 1.4, 1.3), 'hair', at=(0, 7.5, 3.5), part='bangs', bands=[(1, 0.7, 1.4, 'hairhi')], **hair)]
        for i, (x, y, r) in enumerate(((-3.4, 5.8, 0.85), (-1.7, 5.6, 0.95), (0.8, 6.1, 0.75), (2.5, 5.7, 0.9), (3.9, 6.0, 0.7))):
            S += [rcone('head', (x * 0.9, 7.5, 3.7), (x, y, 4.3), 1.1, 0.35, 'hair', part='bangs', **hair)]
        # side locks behind the cheeks, flicking out at the jaw
        for sx, nm in ((1, 'lockL'), (-1, 'lockR')):
            S += [rcone('head', (sx * 4.6, 6.8, -1.2), (sx * 4.8, 2.3, -0.4), 1.3, 0.9, 'hair', part=nm, **hair),
                  rcone('head', (sx * 4.75, 2.7, -0.6), (sx * 5.6, 1.6, -1.0), 0.85, 0.35, 'hair', part=nm, **hair)]
        # back of the bob with flicks at the nape
        S += [ell('head', (4.8, 3.4, 2.8), 'hair', at=(0, 3.4, -2.5), part='hair', **hair),
              rcone('head', (3.3, 2.4, -2.8), (5.0, 1.1, -2.2), 1.1, 0.45, 'hair', part='nape', **hair),
              rcone('head', (-3.3, 2.4, -2.8), (-5.0, 1.1, -2.2), 1.1, 0.45, 'hair', part='nape', **hair),
              rcone('head', (0.0, 2.0, -3.6), (0.4, 0.7, -3.9), 1.1, 0.45, 'hair', part='nape', **hair)]
        # ahoge: a curl rising from her right side of the crown and bending back over
        S += [rcone('head', (-1.2, 9.4, 1.2), (-1.9, 10.9, 1.0), 0.42, 0.3, 'hair', part='ahoge'),
              rcone('head', (-1.9, 10.9, 1.0), (-1.0, 11.6, 0.8), 0.3, 0.26, 'hair', part='ahoge'),
              rcone('head', (-1.0, 11.6, 0.8), (-0.3, 11.0, 0.7), 0.26, 0.22, 'hair', part='ahoge')]
        return S

    def shapes(self, ctx):
        bw = ctx['bones']
        S = self.head_shapes(ctx)
        # neck, kimono top, capelet, bell
        S += [rcone('neck', (0, -0.4, 0), (0, 1.6, 0), 0.95, 0.9, 'skin', part='neck'),
              ell('spine', (2.45, 2.2, 1.85), 'plum', at=(0, 0.7, 0.05), part='torso', group='torso', k=1.0),
              ell('chest', (2.75, 2.4, 1.95), 'plum', at=(0, 0.2, 0.1), part='torso', group='torso', k=1.0),
              cone('chest', 1.5, 4.6, 1.6, 'mint', round_=0.5, sx=1.0, sz=0.8, at=(0, 1.3, 0.0), part='cape',
                   bands=[(1, -1.55, -0.95, 'teal')]),
              ell('chest', (0.85, 0.85, 0.75), 'gold', at=(0, 2.0, 2.25), part='bell')]
        # obi and the bow on her left
        S += [cyl('spine', 0.75, 2.62, 'teal', round_=0.35, at=(0, 0.25, 0), part='obi'),
              ell('spine', (1.05, 0.85, 0.55), 'teal', at=(2.35, 0.95, 1.25), R=G.Rz(-25), part='bow'),
              ell('spine', (0.95, 0.8, 0.55), 'teal', at=(2.75, -0.15, 1.2), R=G.Rz(30), part='bow'),
              ell('spine', (0.55, 0.55, 0.5), 'teal', at=(2.35, 0.4, 1.55), part='bow')]
        for j in range(3):
            S += [box(f'bowt{j}', (0.42, 0.78, 0.16), 'teal', round_=0.12, at=(0, -0.7, 0), part='bowt')]
        # skirt: hangs from the waist along the hem chain; the knees push its front
        hem = bw.get('hem0')
        S += [skirt('hem0', 3.25, 5.8, 2.6, 'skirt', sx=1.0, sz=0.82, wave=(0.32, 5, 0.4), flare=(0.30, 9, 0.0),
                    round_=0.35, at=(0, -3.25, 0), part='skirt',
                    bands=[(1, -2.65, -2.0, 'white', 0.32, 5, 0.4)])]
        # legs
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('thigh' + s, (0, 0, 0), (0, -5.6, 0), 1.35, 1.1, 'skin', part='leg' + s),
                  rcone('shin' + s, (0, 0.2, 0), (0, -5.2, 0), 1.0, 0.82, 'white', part='leg' + s,
                        bands=[(1, -1.3, 0.9, 'skin'), (1, -1.85, -1.3, 'ribbon')]),
                  ell('shin' + s, (0.45, 0.4, 0.3), 'ribbon', at=(sx * 0.95, -1.55, 0.2), part='leg' + s),
                  box('foot' + s, (1.0, 0.8, 1.55), 'boot', round_=0.75, at=(0, -0.42, 0.5), part='boot' + s),
                  cyl('foot' + s, 0.55, 1.05, 'boot', round_=0.3, at=(0, 0.45, 0.05), part='boot' + s)]
        # arms: sleeves (white, red lining at the cuff), the hanging sleeve bags, hands
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('uarm' + s, (0, 0.3, 0), (0, -3.4, 0), 1.3, 1.6, 'white', part='arm' + s),
                  cone('farm' + s, 1.6, 2.6, 1.6, 'white', round_=0.25, at=(0, -1.5, 0.0), part='arm' + s,
                       bands=[(1, -1.65, -1.2, 'ribbon')]),
                  ell(f'slv{s}0', (0.9, 1.7, 1.6), 'white', at=(0, -1.0, 0.0), part='slv' + s),
                  ell('hand' + s, (0.72, 0.85, 0.72), 'skin', at=(0, -0.35, 0.15), part='hand' + s)]
        return S

    # ------------------------------------------------------------------ face
    def features(self, ctx):
        def on_face(x, y):
            cx, cy, cz, rx, ry, rz = 0, 4.6, 0.3, 4.6, 4.6, 4.2
            t = 1 - (x / rx) ** 2 - ((y - cy) / ry) ** 2
            z = cz + rz * math.sqrt(max(t, 0))
            n = (x / rx ** 2, (y - cy) / ry ** 2, (z - cz) / rz ** 2)
            return (x, y, z), n
        f = {}
        for nm, (x, y) in {'eyeL': (2.5, 3.9), 'eyeR': (-2.5, 3.9), 'mouth': (0.0, 1.6),
                           'blushL': (3.2, 2.6), 'blushR': (-3.2, 2.6)}.items():
            p, n = on_face(x, y)
            f[nm] = ('head', p, n)
        return f

    def decals(self, img, px, feats, ctx):
        cmap = {k: St.hexrgb(v) for k, v in C.items()}
        skin = {self.pal.ids['skin']}
        Face.paint_face(img, px, feats, cmap, expr=ctx.get('expr', 'open'), mouth=ctx.get('mouth', 'closed'),
                        blush=True, skin_ids=skin)

    def anchors(self, ctx):
        return {'hand': ('handL', (0, -0.6, 0)), 'head': ('head', (0, 11.0, 0)), 'seat': ('pelvis', (0, -0.6, -0.6))}
