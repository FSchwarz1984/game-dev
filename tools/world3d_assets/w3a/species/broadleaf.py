"""Deciduous broadleaf trees of the slopes, and a dead one she may cut.

  konara_*  コナラ (Quercus serrata): a crooked grey-brown trunk with furrowed bark, an open,
            irregular crown of mid-green leaves in several lobes
  buna_*    ブナ (beech): a smooth pale-grey trunk mottled with lichen, a rounded, layered crown of
            lighter fresh green
  kare_*    a dead standing konara (枯れ木): bare, grey, broken limbs (the choppable tree)
"""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import foliage as FO
from .. import leaves as LV
from .. import trees as TR
from .. import wood as WD
from ..core import normalize, rng

SPECIES = {
    'konara': dict(seed=7501, leaf=dict(size=(3.0, 4.6), wid=(1.8, 2.6), gloss=0.05), tints=('#57703c', '#6a7f42', '#43603e'),
                   variants=[('a', 12.0, 4, 4.2, 1), ('b', 9.5, 3, 3.4, 2), ('c', 14.0, 5, 4.8, 3)],
                   bark=dict(spacing=(2, 4), ridge=('#5e564c', '#6a6156', '#766c60'), lip='#80766a', fissure='#352f2a',
                             deep='#28231f', break_p=0.12, wave=(1.4, 0.6), merge_p=0.2),
                   fork=0.38, crook=0.3, species='konara', note='コナラ'),
    'buna': dict(seed=7601, leaf=dict(size=(3.4, 5.0), wid=(2.2, 3.0), gloss=0.1), tints=('#62803f', '#76904a', '#4c6c42'),
                 variants=[('a', 15.0, 4, 5.0, 1), ('b', 11.0, 3, 4.0, 2), ('c', 17.0, 5, 5.6, 3)],
                 bark=dict(spacing=(9, 15), ridge=('#8e8d86', '#9a9890', '#a5a39a'), lip='#aeaca2', fissure='#7e7d76',
                           deep='#6f6e68', lichen=('#a4a890', '#b8bba4'), lichen_p=0.02, break_p=0.005, wave=(0.6, 0.3),
                           merge_p=0.7),
                 fork=0.45, crook=0.12, species='beech', note='ブナ'),
}


def variant(sp, key, H, nl, spread, vs, R):
    fork = H * sp['fork']
    trunk = WD.Limb('trunk', TR.wander(R, [0, -0.3, 0], [R.normal(0, 0.1), 1, R.normal(0, 0.1)], fork + 0.3, 3, bend=sp['crook'] * 0.4),
                    [0.34 + 0.01 * H, 0.28, 0.25, 0.23], kind='trunk', n_around=9, step_fn=lambda f: 0.6, moss=0.25,
                    rfun=lambda th, k, f, s: s.rad[k] * (1 + 0.18 * np.exp(-max(s.pos[k, 1], 0) / 0.5) * (1 + 0.3 * np.cos(3 * th))))
    WD.build_limb(trunk)
    limbs = [trunk]
    masses = []
    top = trunk.spine.pos[-1]
    az0 = R.uniform(0, 2 * math.pi)
    for i in range(nl):
        az = az0 + i * 2 * math.pi / nl + R.normal(0, 0.3)
        d = np.array([math.cos(az) * 0.65, 1.0, math.sin(az) * 0.65])
        L = (H - fork) * R.uniform(0.8, 1.0)
        path = TR.wander(R, top - np.array([0, 0.3, 0]), d, L, 4, bend=sp['crook'], up=0.03)
        limbs.append(WD.Limb(f'l{i}', path, [0.17, 0.13, 0.09, 0.06, 0.035], kind='limb', n_around=6, step_fn=lambda f: 0.6, moss=0.2))
        for k, f in enumerate((0.5, 1.0)):
            p = path[2] if k == 0 else path[-1]
            r = spread * (0.42 if k == 0 else 0.5) * R.uniform(0.85, 1.1)
            masses.append(CD.Mass(p + np.array([0, 0.2, 0]), (r, r * 0.7, r * 0.9), seed=sp['seed'] + vs * 100 + i * 10 + k,
                                  clumps=0.35, clump_r=(0.7, 1.3), tiles='mass', interior=k == 1, flat=0.35, lump=0.16, sag=0.3))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 2.0)
    t0, t1, t2 = sp['tints']
    crown_kw = dict(centre=tuple(cc), radii=(span, H * 0.32, span), base_tint=TR.tint_for(t0), young_tint=TR.tint_for(t1),
                    old_tint=TR.tint_for(t2), overlap=1.2, fill_density=0.8, clump_overlap=1.0, interior_frac=0.3,
                    spray_rate=0.0, env_k=0.25, clump_k=0.3, up_bias=0.3, flex_r=span, max_cards=1000)
    cat = {'category': 'tree', 'species': sp['species'], 'footprint': [[0.0, 0.0, 0.45]], 'height': H,
           'crown': {'centre': [float(cc[0]), float(cc[1]), float(cc[2])], 'radius': float(span), 'base': float(fork)},
           'tags': ['tree', 'broadleaf'], 'anchors': {}, 'notes': f"{sp['note']} {H:.0f} m."}
    return limbs, masses, crown_kw, cat


def build_species(out, name):
    sp = SPECIES[name]
    a = out.asset(name, 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.9},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(sp['seed'], **sp['bark']))})
    S = sp['seed']
    specs = {'mass': [(LV.broad_leaves, dict(W=int(16 + (i % 3) * 3), H=int(13 + (i % 2) * 3), seed=S + i, **sp['leaf']))
                      for i in range(9)],
             'small': [(LV.broad_leaves, dict(W=12, H=11, seed=S + 50 + i, **sp['leaf'])) for i in range(4)],
             'interior': [(LV.broad_leaves, dict(W=18, H=15, seed=S + 80 + i, size=sp['leaf']['size'], wid=sp['leaf']['wid'],
                                                 gloss=0.0)) for i in range(2)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.2),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(S)
    stats = {}
    for key, H, nl, spread, vs in sp['variants']:
        limbs, masses, crown_kw, cat = variant(sp, key, H, nl, spread, vs, R)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=TR.default_colour(), seed=S + vs)
    return stats


def build_dead(out):
    """A dead konara: bare limbs, a broken top, grey weathered wood, bracket fungus."""
    a = out.asset('kare', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.9},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(7701, spacing=(2, 4),
                                                                                  ridge=('#77726a', '#837d74', '#8e877d'),
                                                                                  lip='#99928a', fissure='#4a4540', deep='#3a3632',
                                                                                  break_p=0.18, wave=(1.0, 0.5)))})
    R = rng(7700)
    stats = {}
    for key, H, nl, vs in (('a', 8.0, 4, 1), ('b', 6.0, 3, 2)):
        trunk = WD.Limb('trunk', TR.wander(R, [0, -0.3, 0], [0.05, 1, 0.0], H * 0.6, 3, bend=0.08), [0.3, 0.25, 0.22, 0.16],
                        kind='trunk', n_around=9, step_fn=lambda f: 0.6, moss=0.4, cap_end=True)
        WD.build_limb(trunk)
        limbs = [trunk]
        top = trunk.spine.pos[-1]
        az0 = R.uniform(0, 2 * math.pi)
        for i in range(nl):
            az = az0 + i * 2 * math.pi / nl + R.normal(0, 0.3)
            f = R.uniform(0.55, 0.95)
            p0, t0, r0 = trunk.spine.point_at(f)
            d = np.array([math.cos(az), 0.7, math.sin(az)])
            path = TR.wander(R, p0, d, H * R.uniform(0.2, 0.38), 3, bend=0.3, up=0.05)
            limbs.append(WD.Limb(f'l{i}', path, [r0 * 0.5, r0 * 0.35, r0 * 0.2, 0.03], kind='limb', n_around=5,
                                 step_fn=lambda f_: 0.5, moss=0.3))
            for j in range(2):
                q = path[int(R.integers(1, 3))]
                dd = normalize(d + R.normal(0, 0.6, 3) + np.array([0, 0.3, 0]))
                limbs.append(WD.Limb(f'l{i}t{j}', [q, q + dd * R.uniform(0.6, 1.2)], [0.03, 0.012], kind='branch', n_around=4,
                                     step_fn=lambda f_: 0.5))
        cat = {'category': 'tree', 'species': 'dead', 'footprint': [[0.0, 0.0, 0.4]], 'height': H, 'crown': {},
               'tags': ['tree', 'choppable', 'dead'], 'anchors': {'cut': [0.0, 0.6, 0.35]},
               'notes': '枯れ木: a dead konara she may cut (the stump with the axe stands by it).'}

        def col(P, N, L):
            c = np.ones((len(P), 3))
            g = np.clip((0.4 - P[:, 1]) / 0.5, 0, 1)[:, None]
            return c * (1 - g) + np.array([0.8, 0.74, 0.66]) * g
        stats[key] = TR.build_variant(a, key, limbs, [], (np.zeros((8, 8, 4), np.uint8), [(0, 0, 8, 8)]), {}, {}, m_bark,
                                      None, cat, colour_fn=col, ao_fn=TR.default_ao([]), seed=7700 + vs)
    return stats


def build(out):
    return {'konara': build_species(out, 'konara'), 'buna': build_species(out, 'buna'), 'kare': build_dead(out)}
