"""百々つゞみ (Tsuzumi Momo): the porter of the pass, under a very wide sedge hat.

Reference: assets/reference/illustrations/tsuzumi.png and pack A. A wide sugegasa (cream straw, red
band, navy underside) worn tilted back; long straight dark violet hair to the knees with a blunt
hime fringe and cheek locks tied in white and red; indigo kimono under a long white haori with
pointed panels and very wide sleeves; a white obi with a red cord and bow and a long red tail on
her left; very baggy indigo trousers gathered at the ankle with white wraps; black tabi boots.

Variants (sheets): 'plain', 'frame' (the old back-frame, empty: day 1, Saji rides on its top
rail), 'load' (the frame with the wicker box). The hat is its own layer (hat_shapes) so that the
pending damage / burn states (her body material, pending decision) only swap that layer.

Proportions: 33.3 px to the crown (3.2 heads, head 10.5 px), the hat apex ~37 px; shoulders 8 px."""

from __future__ import annotations

import math

import numpy as np

import geom as G
from geom import ell, halfell, rcone, box, cone, cyl, skirt, torus
import style as St
from model import Model, ChainSpec
import face as Face
import humanoid as Hu

C = {
    'E': '#16122a', 'e': '#707c97', 'q': '#a5aec2', 'l': '#ffffff',
    'm': '#b06a62', 'M': '#7a2e3a', 'b': '#f5a0a2',
}

HAT_TILT = 13.0          # degrees the hat is tipped back on her head (front brim up)


class Tsuzumi(Model):
    NAME = 'tsuzumi'
    FRAME = (64, 64)
    PIVOT = (32, 58)

    def props(self):
        return {
            'hip': 14.4, 'spine': 2.2, 'chest': 2.5, 'neck': 2.6, 'neck2': 1.2,
            'sh_w': 3.1, 'sh_h': 1.5, 'uarm': 4.0, 'farm': 3.6,
            'hip_w': 1.55, 'hip_d': 0.6, 'thigh': 6.2, 'shin': 6.3, 'ankle': 1.3,
            'ao': 2.4, 'shadow_k': 8.0, 'line_gap': 1.6,
            'cycles': {
                'walk': {'stride': 11.5, 'lift': 1.9, 'bob': Hu.bob_walk, 'arm': 18.0, 'arm_out': 8.0, 'elbow': 14.0,
                         'elbow_swing': 8.0, 'lean': 2.5, 'lean2': 1.0, 'twist': 3.0, 'toe_off': 20.0, 'heel': 8.0},
                'run': {'stride': 14.0, 'lift': 3.4, 'bob': Hu.bob_run, 'arm': 30.0, 'arm_out': 10.0, 'elbow': 60.0,
                        'elbow_swing': 16.0, 'lean': 8.0, 'lean2': 3.0, 'twist': 5.0, 'toe_off': 28.0, 'heel': 4.0,
                        'stance': 0.38},
            },
        }

    def rest_pose(self):
        return {'uarmL': (0, 0, 7), 'uarmR': (0, 0, -7), 'farmL': (-16, 0, 0), 'farmR': (-16, 0, 0),
                'thighL': (0, 0, 1.5), 'thighR': (0, 0, -1.5)}

    def palette(self):
        return St.Palette([
            St.Mat('hair', ['#160f1e', '#241a2e', '#33263e', '#4b3a58'], '#0f0a16', [0.30, 0.50, 0.76], line=0),
            St.Mat('hairhi', ['#33263e', '#4b3a58', '#6f5c80'], '#0f0a16', [0.42, 0.66], line=0),
            St.Mat('white', ['#9d90aa', '#cbc0cd', '#ebe3d6', '#fbf7ef'], '#3b3150', [0.32, 0.52, 0.80], line=1),
            St.Mat('straw', ['#9d90aa', '#cbc0cd', '#ebe3d6', '#fbf7ef'], '#3b3150', [0.30, 0.50, 0.80], line=1),
            St.Mat('indigo', ['#201e3f', '#2f305c', '#42487d', '#5f679f'], '#16122a', [0.30, 0.50, 0.80], line=0),
            St.Mat('red', ['#8c2b45', '#c03e5a', '#e3647c'], '#3e1424', [0.42, 0.72], prio=2.0, line=0),
            St.Mat('skin', ['#d4907f', '#efbca8', '#fde7d8'], '#6a3438', [0.42, 0.62], line=1, min_tone=1),
            St.Mat('boot', ['#120f1c', '#1e1a2d', '#2c2740', '#3e3756'], '#0b0812', [0.30, 0.50, 0.80], line=0),
            St.Mat('wood', ['#5e4130', '#8b6443', '#b58c5f'], '#2f1e12', [0.45, 0.72], line=0),
            St.Mat('wicker', ['#644728', '#8f6a3c', '#bf9558', '#e1c084'], '#2f1e12', [0.30, 0.50, 0.78], line=1),
            St.Mat('rope', ['#8f6a3c', '#bf9558', '#e1c084'], '#2f1e12', [0.45, 0.72], prio=1.5),
            St.Mat('navy', ['#16122a', '#201e3f', '#2f305c'], '#16122a', [0.45, 0.72], prio=1.5),
        ], extra=C)

    def chain_specs(self):
        sp = {
            'hairb': ChainSpec('head', (0, 3.6, -3.2), 6, 3.05, rest=(0, -1, -0.08), damping=0.20, stiff=0.12,
                               gravity=0.35, wind=1.0, collide=self._hair_collide),
            'sash': ChainSpec('spine', (1.7, -0.3, 2.5), 5, 1.55, damping=0.16, stiff=0.08, gravity=0.30, wind=1.2),
            'coat': ChainSpec('chest', (0, 0.6, 0), 1, 11.2, damping=0.28, stiff=0.35, gravity=0.30, wind=0.5),
            'slvL': ChainSpec('farmL', (0, -1.2, -0.3), 1, 3.0, damping=0.22, stiff=0.18, gravity=0.35, wind=0.8),
            'slvR': ChainSpec('farmR', (0, -1.2, -0.3), 1, 3.0, damping=0.22, stiff=0.18, gravity=0.35, wind=0.8),
        }
        return sp

    def head_chain_prefixes(self):
        return ()

    def _hair_collide(self, pts, bw):
        """Keep the long back hair behind her back and the coat (in the chest bone frame)."""
        m = bw['chest']
        inv = np.linalg.inv(m)
        out = pts.copy()
        for i in range(1, len(pts)):
            p = inv @ np.array([pts[i][0], pts[i][1], pts[i][2], 1.0])
            y = p[1]
            # back profile of torso + haori in chest coordinates: wider toward the hem
            back = 2.6 + max(0.0, -y) * 0.20
            if p[2] > -back:
                p[2] = -back
            q = m @ p
            out[i] = q[:3]
        return out

    # ------------------------------------------------------------------ the hat (own layer)
    def hat_shapes(self, ctx, variant='intact'):
        """The sugegasa in its own frame: y up along the cone, brim radius 14.5, 4 px tall; the red
        band runs from the crown down to the brim on her left-front; the underside is navy.
        variant: 'intact' only for now (damage and burn states wait for the body-material
        decision; they would add cut planes and char bands here)."""
        hat = dict(part='hat')
        S = [cone('hat', 1.9, 14.5, 0.9, 'straw', round_=0.45, at=(0, 1.9, 0),
                  bands=[(4, 30, 50, 'red'), (1, -1.95, -1.55, 'navy')], **hat),
             ell('hat', (1.3, 0.9, 1.3), 'straw', at=(0, 3.9, 0), **hat)]
        return S

    def hat_frame(self, bw, yaw):
        """On her head, tipped back toward the camera in every view: a round hat then keeps the same
        outline from any side at this pitch (only the band turns with her), and the face shows
        under the front brim. Bows and falls still carry the head's own rotation."""
        head = bw['head']
        seat = head @ np.array([0, 8.6, -0.4, 1.0])
        tilt = G.Ry(-yaw) @ G.Rx(-HAT_TILT) @ G.Ry(yaw)
        return G.M4(tilt @ head[:3, :3], seat[:3])

    # ------------------------------------------------------------------ shapes
    def head_shapes(self, ctx):
        S = []
        S += [ell('head', (4.7, 4.8, 4.3), 'skin', at=(0, 4.9, 0.3), part='face', group='face', k=1.2),
              ell('head', (3.6, 2.7, 3.1), 'skin', at=(0, 2.6, 1.2), part='face', group='face', k=1.4)]
        hair = dict(group='hair', k=0.8)
        S += [ell('head', (5.05, 5.1, 4.85), 'hair', at=(0, 5.3, -0.3), cut=(0, -1.0, 0.30, -4.4), part='hair',
                  bands=[(1, 2.0, 2.8, 'hairhi')], **hair)]
        # blunt hime fringe, cut straight at the brow
        S += [ell('head', (4.55, 2.2, 1.5), 'hair', at=(0, 7.3, 3.3), cut=(0, -1.0, 0, -5.75), part='bangs', **hair)]
        # cheek locks (hime cut) with white and red ties
        for sx, nm in ((1, 'lockL'), (-1, 'lockR')):
            S += [rcone('head', (sx * 4.5, 6.6, 0.4), (sx * 4.4, -2.2, 1.0), 1.25, 0.9, 'hair', part=nm,
                        bands=[(1, 2.2, 3.4, 'white'), (1, 1.6, 2.2, 'red')], **hair)]
        # back of the head (the long sheet itself is the 'hairb' chain)
        S += [ell('head', (4.9, 4.2, 3.0), 'hair', at=(0, 4.0, -2.2), part='hair', **hair)]
        return S

    def hair_sheet(self, ctx):
        S = []
        bw = ctx['bones']
        for j in range(6):
            w = 4.3 - j * 0.28
            S += [box(f'hairb{j}', (w, 1.75, 0.95), 'hair', round_=0.85, at=(0, -1.4, 0), part='hairb',
                      group='hairb', k=0.9)]
        return S

    def shapes(self, ctx):
        bw = ctx['bones']
        var = ctx.get('variant', 'plain')
        S = self.head_shapes(ctx) + self.hair_sheet(ctx)
        # the hat, in its own frame
        bw['hat'] = self.hat_frame(bw, ctx.get('yaw', 0.0))
        S += self.hat_shapes(ctx, ctx.get('hat', 'intact'))
        # neck, kimono top, collar
        S += [rcone('neck', (0, -0.4, 0), (0, 1.8, 0), 1.05, 1.0, 'skin', part='neck'),
              ell('spine', (2.7, 2.4, 2.0), 'indigo', at=(0, 0.8, 0.05), part='torso', group='torso', k=1.0),
              ell('chest', (3.0, 2.7, 2.15), 'indigo', at=(0, 0.3, 0.1), part='torso', group='torso', k=1.0),
              ell('chest', (1.0, 1.2, 0.6), 'white', at=(0, 2.0, 1.75), R=G.Rx(-20), part='collar'),
              ell('chest', (0.55, 0.9, 0.5), 'red', at=(0, 1.6, 2.0), R=G.Rx(-20), part='collar')]
        # obi: white, a red cord around it, the bow on her left-front, the long tail (chain)
        S += [cyl('spine', 1.0, 2.95, 'white', round_=0.4, at=(0, 0.3, 0), part='obi'),
              torus('spine', 2.98, 0.32, 'red', at=(0, 0.25, 0), part='obi'),
              ell('spine', (0.9, 0.75, 0.5), 'red', at=(1.15, 0.65, 2.75), R=G.Rz(-30), part='bow'),
              ell('spine', (0.8, 0.7, 0.5), 'red', at=(2.1, 0.2, 2.45), R=G.Rz(25), part='bow')]
        for j in range(5):
            S += [box(f'sash{j}', (0.62, 0.86, 0.14), 'red', round_=0.1, at=(0, -0.75, 0), part='sash')]
        # haori: an open coat on the coat chain; left, right and back pieces leave the front open
        coat = dict(part='coat', group='coat', k=0.0)
        hz = 5.6
        for cut in ((-1, -0.107, 0, -1.6), (1, -0.107, 0, -1.6), (0, 0, 1, 0.2)):
            S += [skirt('coat0', hz, 5.4, 3.3, 'white', sx=1.0, sz=0.78, wave=(1.0, -6, 0.3), flare=(0.25, 7, 0.0),
                        round_=0.4, at=(0, -hz, 0), cut=cut, **coat)]
        # trousers and boots
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('thigh' + s, (0, 0, 0), (0, -6.2, 0), 1.95, 1.75, 'indigo', part='leg' + s),
                  rcone('shin' + s, (0, 0.2, 0), (0, -6.0, 0.1), 1.8, 1.15, 'indigo', part='leg' + s,
                        bands=[(1, -6.4, -4.9, 'white')]),
                  box('foot' + s, (1.1, 0.85, 1.7), 'boot', round_=0.7, at=(0, -0.45, 0.5), part='boot' + s,
                      bands=[(1, -0.9, -0.55, 'white')])]
        # arms: haori sleeves (white, indigo lining at the opening), the hanging sleeve bags, hands
        for s, sx in (('L', 1), ('R', -1)):
            S += [rcone('uarm' + s, (0, 0.3, 0), (0, -3.8, 0), 1.45, 1.75, 'white', part='arm' + s),
                  cone('farm' + s, 1.7, 2.7, 1.75, 'white', round_=0.3, at=(0, -1.6, 0.0), part='arm' + s,
                       bands=[(1, -1.75, -1.25, 'indigo')]),
                  box(f'slv{s}0', (0.75, 2.1, 1.9), 'white', round_=0.7, at=(0, -1.3, 0.0), part='slv' + s,
                      bands=[(1, -2.2, -1.7, 'indigo')]),
                  ell('hand' + s, (0.78, 0.9, 0.78), 'skin', at=(0, -0.4, 0.15), part='hand' + s)]
        if var in ('frame', 'load'):
            S += self.frame_shapes(ctx, var == 'load')
        return S

    def frame_shapes(self, ctx, box_on):
        """The back-frame (背負子) on her back, rigid with the chest: two posts from the hips to above
        the hat (their tips show beside it, so the frame reads from the front too), four rails and a
        shelf; straw straps over the shoulders and down the coat; the wicker box (load) on the shelf
        with a cloth bundle tied on top."""
        S = []
        w = dict(part='frame')
        for sx in (1, -1):
            S += [box('chest', (0.55, 12.2, 0.55), 'wood', round_=0.25, at=(sx * 3.1, 5.9, -3.9), **w),
                  ell('chest', (0.62, 0.5, 0.62), 'wood', at=(sx * 3.1, 18.2, -3.9), **w)]
            # straps: behind the shoulder, over it, down the front of the coat to the armpit
            S += [rcone('chest', (sx * 2.0, 2.2, -2.6), (sx * 2.3, 3.2, 0.6), 0.45, 0.45, 'rope', part='strap'),
                  rcone('chest', (sx * 2.3, 3.2, 0.6), (sx * 2.8, -1.4, 2.95), 0.45, 0.42, 'rope', part='strap')]
        for y in (-5.4, 3.0, 10.6, 16.9):
            S += [box('chest', (3.5, 0.42, 0.45), 'wood', round_=0.2, at=(0, y, -3.9), **w)]
        S += [box('chest', (3.5, 0.4, 2.5), 'wood', round_=0.2, at=(0, -5.8, -6.0), **w)]
        if box_on:
            S += [box('chest', (3.9, 4.9, 2.4), 'wicker', round_=0.8, at=(0, -0.6, -6.4), part='box',
                      bands=[(1, 3.6, 4.9, 'wood'), (0, -0.35, 0.35, 'rope')]),
                  ell('chest', (3.4, 2.0, 2.2), 'indigo', at=(0, 5.6, -6.1), part='bundle',
                      bands=[(0, -0.45, 0.35, 'rope')])]
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
                           'blushL': (3.2, 2.8), 'blushR': (-3.2, 2.8)}.items():
            p, n = on_face(x, y)
            f[nm] = ('head', p, n)
        return f

    def decals(self, img, px, feats, ctx):
        cmap = {k: St.hexrgb(v) for k, v in C.items()}
        Face.paint_face(img, px, feats, cmap, expr=ctx.get('expr', 'open'), mouth=ctx.get('mouth', 'closed'),
                        blush=False, skin_ids={self.pal.ids['skin']})

    def anchors(self, ctx):
        a = {'hand': ('handL', (0, -0.6, 0)), 'head': ('head', (0, 12.0, 0))}
        if ctx.get('variant') in ('frame', 'load'):
            a['loadTop'] = ('chest', (0, 17.4, -3.9))
            a['hook'] = ('chest', (-3.1, 18.6, -3.9))
        return a


# =============================================================================================
# Sheet description (tools/art/sprite3d/build.py)

import anims as A  # noqa: E402

D8, D4 = ('front', 'front_right', 'right', 'back_right', 'back', 'back_left', 'left', 'front_left'), ('front', 'right', 'back', 'left')
SHEETS = {'load': 'load', 'frame': 'frame', 'plain': 'plain'}
_ALL = tuple(SHEETS)
_M = Tsuzumi()
ANIMS = {
    'idle': A.idle_spec(6, D8, _ALL),
    'walk': A.with_speed(A.loco_spec('walk', 8, 12, D8, _ALL, wind=0.10), _M),
    'run': dict(A.with_speed(A.loco_spec('run', 8, 15, D8, _ALL, wind=0.22), _M), **{'from': 3.9}),
}
