"""Shared building of tree assets: wood (toon_solid, tiling bark texture, vertex tint / AO / moss)
and crowns (toon_foliage cards), packed into one folder per species with several variants.

A species module gives, per variant: limbs (wood.Limb), masses (cards.Mass) and the card tile sets;
this module turns them into meshes, scenes and catalog entries. Budgets (contract section 2):
a tree <= 8k triangles (wood + cards), <= 600 cards.
"""
from __future__ import annotations

import math

import numpy as np

from . import cards as CD
from . import foliage as FO
from . import leaves as LV
from . import wood as WD
from .core import PPM, hex_rgb, normalize, rng


def tint_for(hexcol, body=LV.BODY):
    """The card tint that makes a tile's BODY tone come out as hexcol."""
    c = np.array(hex_rgb(hexcol), np.float64) / 255.0
    return np.clip(c / body, 0, 1)


def default_colour(base_tint=(1, 1, 1), ground=(0.82, 0.76, 0.66), high=None):
    base_tint = np.asarray(base_tint, np.float64)

    def f(P, N, L):
        y = P[:, 1]
        col = np.tile(base_tint, (len(P), 1))
        g = np.clip((0.4 - y) / 0.5, 0, 1)[:, None]
        col = col * (1 - g) + np.asarray(ground) * g
        if high is not None:
            hi = np.clip((y - high[0]) / max(high[1] - high[0], 1e-6), 0, 1)[:, None]
            col = col * (1 - hi) + np.asarray(high[2]) * hi
        return col
    return f


def default_ao(masses, floor=0.45, n_rays=12):
    def f(P, N, L):
        ao = np.ones(len(P))
        y = P[:, 1]
        ao -= 0.25 * np.clip((0.35 - y) / 0.35, 0, 1)
        if L.kind in ('limb', 'branch'):
            ao -= 0.15 * np.clip(-N[:, 1], 0, 1)
        if masses:
            ao *= floor + (1 - floor) * CD.sky_visibility(P, N, masses, n_rays=n_rays)
        return np.clip(ao, 0.2, 1)
    return f


def build_variant(asset, key, limbs, masses, tiles, sets, crown_kw, bark_mat, leaf_mat, catalog,
                  colour_fn=None, ao_fn=None, moss_fn=None, extra_cards=(), extra_wood=(), seed=0,
                  max_tris=8000, max_cards=1100, scene_meta=None, card_post=None):
    """Make one variant: meshes <name>_<key>_wood/_leaves, scene <name>_<key>.tscn, a catalog entry.
    tiles: (atlas, rects). Returns stats."""
    atlas, rects = tiles
    for L in limbs:
        if L.spine is None:
            WD.build_limb(L)
    if ao_fn is None:
        ao_fn = default_ao(masses)
    wood = WD.wood_mesh(limbs, tex_size=256, colour_fn=colour_fn, ao_fn=ao_fn, moss_fn=moss_fn)
    surfaces = [(bark_mat, wood)] + list(extra_wood)
    cards = []
    if masses:
        kw = dict(crown_kw)
        kw.setdefault('max_cards', max_cards - len(extra_cards))
        cards = CD.crown_cards(masses, kw.pop('centre'), kw.pop('radii'), sets, seed=seed, **kw)
        if cards:
            vis = CD.sky_visibility(np.array([c.p for c in cards]), np.array([c.n for c in cards]), masses, n_rays=12)
            for c, v in zip(cards, vis):
                c.ao = float(np.clip(c.ao * (0.6 + 0.4 * v), 0.2, 1.0))
    cards = list(cards) + list(extra_cards)
    if card_post is not None:
        cards = card_post(cards)
    nodes = []
    name = f'{asset.name}_{key}'
    wood_res = asset.mesh(f'{key}_wood', surfaces)
    nodes.append({'name': 'Wood', 'type': 'mesh', 'mesh': wood_res})
    if cards:
        lo = np.min([c.p for c in cards], axis=0) - 2
        hi = np.max([c.p for c in cards], axis=0) + 2
        leaf_md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
        leaf_res = asset.mesh(f'{key}_leaves', [(leaf_mat, leaf_md)], custom_aabb=[lo.tolist(), (hi - lo + np.array([0, 4, 0])).tolist()])
        nodes.append({'name': 'Leaves', 'type': 'mesh', 'mesh': leaf_res, 'extra_cull_margin': 2.0})
    scene = asset.scene(nodes, meta=scene_meta or {}, key=key)
    e = dict(catalog)
    e['scene'] = scene
    asset.entries[name] = e
    wood_tris = sum(len(md.arrays()['idx']) for _, md in surfaces)
    tris = wood_tris + 2 * len(cards)
    assert len(cards) <= max_cards, f'{name}: {len(cards)} cards > {max_cards}'
    assert tris <= max_tris, f'{name}: {tris} triangles > {max_tris}'
    return {'cards': len(cards), 'tris': tris}


def wander(R, p0, d0, length, segs, bend=0.18, up=0.0, gravity=0.0):
    """A naturally bending path from p0 along d0: list of points."""
    pts = [np.asarray(p0, np.float64)]
    d = normalize(np.asarray(d0, np.float64))
    for i in range(segs):
        d = normalize(d + R.normal(0, bend, 3) + np.array([0, up - gravity * (i / max(segs - 1, 1)), 0]))
        pts.append(pts[-1] + d * length / segs)
    return pts
