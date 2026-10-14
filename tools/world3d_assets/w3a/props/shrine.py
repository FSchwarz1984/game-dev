"""The shrine (祠) on its terrace below the camphor, and its offering box (賽銭箱).

A small gabled wooden shrine on a two-step stone base: a raised floor, board walls, lattice doors,
a long front roof slope (nagare) over a porch on two posts; the porch's eave beam (the beam that
falls and pins さぢ, script-02) is its own node 'EaveBeam'. Scenes: shrine (beam in place),
shrine_fallen (the beam down across the porch step, the right porch post leaning, the front eave
sagging), their faded twins; the beam alone is objects/shrine_beam. Origin: the middle of the
body at terrace level; the front (+z) faces the steps."""
from __future__ import annotations

import math

import numpy as np

from ..core import rng
from . import kit as K
from .common import export_prop

WOOD = K.col('#85796b')          # old boards, silvered
POST = K.col('#73675a')
DARK = K.col('#2b2521')
ROOF = K.col('#655b50')
STONE = K.col('#8b877d')
STRAW = K.col('#c2a868')
PAPER = K.col('#efeadc')
RIDGE_Y = 2.95


def wood(pc, c=None, pattern='planks', amount=0.3, seed=0):
    pc.pattern = K.PAT[pattern]
    pc.amount = amount
    pc.var = 0.05
    pc.seed = seed
    if c is not None:
        pc.colour = c
    return pc


def roof_slab(x0, x1, top, bottom, thick, c, seed):
    """A roof board from the ridge line `top` (y, z) down to the eave line `bottom` (y, z), x0..x1."""
    (yt, zt), (yb, zb) = top, bottom
    d = np.array([0.0, yb - yt, zb - zt])
    L = np.linalg.norm(d)
    nrm = np.array([0.0, d[2], -d[1]]) / L
    if nrm[1] < 0:
        nrm = -nrm
    pts = []
    for x in (x0, x1):
        for (y, z) in ((yt, zt), (yb, zb)):
            p = np.array([x, y, z])
            pts += [p, p - nrm * thick]
    pc = K.convex(pts, c)
    return wood(pc, c, 'tiles', 0.3, seed)


def shrine_pieces(R, fallen=False):
    P = []
    sd = lambda: int(R.integers(0, 1 << 20))
    # stone base: two steps, weathered
    def base_f(Q):
        a = K.sd_box(Q - np.array([0, 0.075, 0.45]), (1.17, 0.075, 1.42), 0.03)
        b = K.sd_box(Q - np.array([0, 0.225, 0.42]), (1.02, 0.075, 1.27), 0.03)
        return np.minimum(a, b) + K.weathered(Q, 0.01, 0.12, 8101)
    P.append(K.sdf_piece(base_f, (-1.25, -0.05, -1.05), (1.25, 0.34, 1.95), STONE, h=0.03, tris=420, pattern='stone',
                         amount=0.7, var=0.07, seed=8101))
    # floor and short posts
    P.append(wood(K.cbox((1.76, 0.08, 1.46), WOOD * 0.95, centre=(0, 0.5, 0), bevel=0.02), WOOD * 0.95, 'planks', 0.3, sd()))
    for x in (-0.75, 0.75):
        for z in (-0.6, 0.6):
            P.append(wood(K.cbox((0.1, 0.16, 0.1), POST, centre=(x, 0.38, z), bevel=0.01), POST, 'bark', 0.3, sd()))
    # corner posts
    for x in (-0.8, 0.8):
        for z in (-0.65, 0.65):
            P.append(wood(K.cbox((0.12, 1.42, 0.12), POST, centre=(x, 0.54 + 0.71, z), bevel=0.015, jitter=0.004, seed=sd()),
                          POST, 'bark', 0.3, sd()))
    # walls: sides and back (horizontal boards), a dark gap at the top (ventilation)
    for x in (-0.8, 0.8):
        P.append(wood(K.cbox((0.04, 1.22, 1.18), WOOD, centre=(x, 0.54 + 0.62, 0), bevel=0.008), WOOD, 'planks', 0.4, sd()))
    P.append(wood(K.cbox((1.48, 1.22, 0.04), WOOD, centre=(0, 0.54 + 0.62, -0.65), bevel=0.008), WOOD, 'planks', 0.4, sd()))
    # front: a dark interior behind two lattice doors
    P.append(K.cbox((1.48, 1.2, 0.02), DARK, centre=(0, 0.54 + 0.61, 0.58), bevel=0.0, var=0.0, ao=False))
    for side in (-1, 1):
        cx = side * 0.37
        fr = []
        fr.append(K.cbox((0.72, 0.05, 0.05), WOOD, centre=(cx, 0.6, 0.64), bevel=0.008))
        fr.append(K.cbox((0.72, 0.05, 0.05), WOOD, centre=(cx, 1.74, 0.64), bevel=0.008))
        fr.append(K.cbox((0.05, 1.18, 0.05), WOOD, centre=(cx - side * 0.34, 1.17, 0.64), bevel=0.008))
        fr.append(K.cbox((0.05, 1.18, 0.05), WOOD, centre=(cx + side * 0.34, 1.17, 0.64), bevel=0.008))
        for k in range(1, 4):                                   # vertical bars
            fr.append(K.cbox((0.025, 1.12, 0.025), WOOD * 0.95, centre=(cx - 0.36 + k * 0.18, 1.17, 0.645), bevel=0.0))
        for k in range(1, 5):                                   # horizontal bars
            fr.append(K.cbox((0.68, 0.025, 0.025), WOOD * 0.95, centre=(cx, 0.6 + k * 0.228, 0.645), bevel=0.0))
        P += [wood(f, None, 'planks', 0.2, sd()) for f in fr]
    # top beams (keta) and the tie beams
    for z in (-0.65, 0.65):
        P.append(wood(K.beam((-0.95, 1.98, z), (0.95, 1.98, z), 0.12, 0.14, POST), POST, 'bark', 0.3, sd()))
    for x in (-0.8, 0.8):
        P.append(wood(K.beam((x, 1.98, -0.85), (x, 1.98, 0.85), 0.1, 0.12, POST), POST, 'bark', 0.3, sd()))
    # gable walls (triangles over the side beams up to the ridge)
    for x in (-0.82, 0.82):
        tri = []
        for dx in (-0.02, 0.02):
            tri += [(x + dx, 2.05, -0.62), (x + dx, 2.05, 0.62), (x + dx, RIDGE_Y - 0.12, -0.05)]
        P.append(wood(K.convex(tri, WOOD * 0.92), WOOD * 0.92, 'planks', 0.4, sd()))
    # porch: floor step, two posts, the posts' tie at the top
    P.append(wood(K.cbox((1.4, 0.07, 0.42), WOOD * 0.9, centre=(0, 0.34, 0.92), bevel=0.015), WOOD * 0.9, 'planks', 0.3, sd()))
    P.append(wood(K.cbox((1.2, 0.07, 0.3), WOOD * 0.9, centre=(0, 0.44, 0.7 + 0.18), bevel=0.012), WOOD * 0.9, 'planks', 0.3, sd()))
    lean = 0.17 if fallen else 0.0
    for x in (-0.76, 0.76):
        Rl = K.rot_z(-lean) if (fallen and x > 0) else np.eye(3)
        post = wood(K.cbox((0.11, 1.68, 0.11), POST, centre=(0, 0.84, 0), bevel=0.014, jitter=0.004, seed=sd()), POST, 'bark', 0.3, sd())
        P.append(post.moved(Rl, (x, 0.3, 1.52)))
    # roof: long front slope over the porch, short back slope, bargeboards, a ridge box and logs
    sag = 0.12 if fallen else 0.0
    P.append(roof_slab(-1.17, 1.17, (RIDGE_Y, -0.05), (2.05 - sag, 1.98), 0.11, ROOF, sd()))
    P.append(roof_slab(-1.17, 1.17, (RIDGE_Y, -0.05), (2.02, -1.07), 0.11, ROOF, sd()))
    for x in (-1.19, 1.19):
        P.append(wood(K.beam((x, RIDGE_Y + 0.02, -0.05), (x, 2.0 - sag, 2.0), 0.05, 0.16, WOOD * 0.85), WOOD * 0.85, 'planks', 0.2, sd()))
        P.append(wood(K.beam((x, RIDGE_Y + 0.02, -0.05), (x, 1.97, -1.09), 0.05, 0.16, WOOD * 0.85), WOOD * 0.85, 'planks', 0.2, sd()))
    P.append(wood(K.cbox((2.3, 0.16, 0.22), ROOF * 0.9, centre=(0, RIDGE_Y + 0.08, -0.05), bevel=0.02), ROOF * 0.9, 'planks', 0.3, sd()))
    for x in (-0.6, 0.0, 0.6):
        logp = K.lathe([(0.0, -0.17), (0.055, -0.165), (0.06, -0.12), (0.06, 0.12), (0.055, 0.165), (0.0, 0.17)], WOOD * 0.8,
                       n=8, R=K.rot_x(math.pi / 2), base=(x, RIDGE_Y + 0.22, -0.05))
        P.append(wood(logp, WOOD * 0.8, 'bark', 0.3, sd()))
    # a small shimenawa across the porch, under the beam, with three shide
    if not fallen:
        rope = K.rod([[-0.72, 1.82, 1.58], [-0.36, 1.72, 1.6], [0.0, 1.69, 1.61], [0.36, 1.72, 1.6], [0.72, 1.82, 1.58]],
                     0.035, STRAW, n=5, cap=True, step=0.12, var=0.05, seed=8120)
        P.append(wood(rope, STRAW, 'thatch', 0.2, 8120))
        for x in (-0.36, 0.0, 0.36):
            y0 = 1.7 if x else 1.67
            pts = []
            for dz in (0.0, 0.012):
                pts += [(x - 0.05, y0, 1.62 + dz), (x + 0.05, y0, 1.62 + dz), (x + 0.05, y0 - 0.22, 1.62 + dz),
                        (x - 0.05, y0 - 0.22, 1.62 + dz)]
            P.append(K.convex(pts, PAPER, pattern='paper', amount=0.2, var=0.0, dirt=False))
    return P


def beam_piece(seed=8130):
    """The eave beam (虹梁, simplified): a squared timber 1.8 m with a slight upward arch."""
    pts = []
    L = 1.8
    for k in range(7):
        x = -L / 2 + L * k / 6
        y = 0.03 * math.sin(math.pi * k / 6)
        for dy in (-0.08, 0.08):
            for dz in (-0.06, 0.06):
                pts.append((x, y + dy, dz))
    # convex hull of an arched beam loses the arch underside: make it from three straight timbers
    out = []
    for a, b in ((-0.9, -0.3), (-0.3, 0.3), (0.3, 0.9)):
        ya = 0.03 * math.sin(math.pi * (a + 0.9) / 1.8)
        yb = 0.03 * math.sin(math.pi * (b + 0.9) / 1.8)
        out.append(wood(K.beam((a, ya, 0), (b, yb, 0), 0.12, 0.16, POST * 0.95), POST * 0.95, 'bark', 0.4, seed + len(out)))
    return out


def offering_box(out):
    """賽銭箱: a dark wooden box with a slatted, sloping top; coins inside catch the light (anchors.glint)."""
    R = rng(8140)
    W, H, D = 0.72, 0.46, 0.44
    c = K.col('#5a4a3c')
    P = []
    P.append(wood(K.cbox((W, H - 0.06, D), c, centre=(0, (H - 0.06) / 2 + 0.04, 0), bevel=0.02), c, 'planks', 0.3, 8141))
    for x in (-W / 2 + 0.05, W / 2 - 0.05):                      # feet
        P.append(wood(K.cbox((0.08, 0.05, D + 0.02), c * 0.8, centre=(x, 0.025, 0), bevel=0.01), c * 0.8, 'planks', 0.2, 8142))
    P.append(wood(K.cbox((W + 0.04, 0.04, D + 0.04), c * 1.1, centre=(0, H - 0.02, 0), bevel=0.012), c * 1.1, 'planks', 0.2, 8143))
    # the slatted top: a dark well with angled slats
    P.append(K.cbox((W - 0.1, 0.02, D - 0.1), DARK, centre=(0, H - 0.03, 0), bevel=0.0, var=0.0))
    for k in range(5):
        z = -D / 2 + 0.08 + k * (D - 0.16) / 4
        P.append(wood(K.cbox((W - 0.08, 0.025, 0.035), c * 1.15, centre=(0, H + 0.005, z), bevel=0.006, R=K.rot_x(0.5)),
                      c * 1.15, 'planks', 0.2, 8150 + k))
    # a few coins glinting in the well
    for k in range(3):
        P.append(K.lathe([(0.0, 0.0), (0.02, 0.0), (0.02, 0.005), (0.0, 0.005)], K.col('#b0894a'), n=6,
                         base=(R.uniform(-0.2, 0.2), H - 0.02, R.uniform(-0.1, 0.1)), var=0.0, ao=False, dirt=False))
    prop = K.Prop('offering_box', 8140).add(P)
    cat = {'footprint': [[0.0, 0.0, 0.42]], 'tags': ['interact'],
           'notes': 'Offering box before the shrine; anchors.glint: coins inside that catch the light.',
           'anchors': {'glint': [0.0, H - 0.01, 0.0], 'interact': [0.0, 0.0, 0.75]}}
    return export_prop(out, 'offering_box', 'props', prop, cat, porosity=0.8, budget=1200)


def build(out):
    st = {}
    R = rng(8100)
    beam = K.Prop('beam', 8130).add(beam_piece())
    body = K.Prop('shrine', 8100).add(shrine_pieces(R))
    R = rng(8100)
    body_f = K.Prop('shrine_fallen', 8100).add(shrine_pieces(R, fallen=True))
    beam_up = (0.0, 2.0, 1.52)
    cat = {'footprint': [[0.0, 0.2, 1.2], [0.0, 1.4, 0.6]], 'tags': ['interact', 'sacred', 'building'],
           'notes': 'Small gabled shrine on a stone base; the porch eave beam is the node EaveBeam (scene shrine). '
                    'shrine_fallen: the beam lies across the porch step (node EaveBeam moved), a post leans, the eave sags. '
                    'The beam alone: objects/shrine_beam.',
           'anchors': {'interact': [0.0, 0.0, 2.3], 'beam': list(beam_up), 'beam_fallen': [0.15, 0.48, 1.85]}}
    st['shrine'] = export_prop(out, 'shrine', 'buildings', body, cat, porosity=0.8, cutaway=False, budget=6000,
                               variants={'fallen': body_f},
                               extras={'EaveBeam': (beam, beam_up, {'fallen': {'pos': [0.15, 0.5, 1.85], 'rot': [0.0, 28.6, 14.3]}})})
    b = K.Prop('shrine_beam', 8130).add(beam_piece())
    st['shrine_beam'] = export_prop(out, 'shrine_beam', 'objects', b,
                                    {'footprint': [], 'tags': ['interact', 'story'],
                                     'notes': 'The shrine porch eave beam alone (1.8 m), centred; for the fallen state '
                                              'place it at shrine anchors.beam_fallen (yaw 0.5 rad, roll 0.25 rad).'},
                                    porosity=0.8, budget=600)
    st['offering_box'] = offering_box(out)
    return st
