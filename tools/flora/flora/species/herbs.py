"""Herbs and grasses: 芒 susuki, ferns, 彼岸花 higanbana, 露草 tsuyukusa, 女郎花 ominaeshi.
All single-layer bodies sorted at their foot; blades and flower parts sway in small groups."""
import math

import numpy as np

from .. import raster as R
from ..core import Rng, normalize
from ..palette import PAL
from ..plant import Plant


def _arc(base, a_horiz, length, rise, droop, n=10, wobble=0.0, rng=None):
    """A blade that rises and arches over: base point, horizontal heading, length (m)."""
    pts = []
    d = np.array([math.cos(a_horiz), 0.0, math.sin(a_horiz)])
    for i in range(n + 1):
        t = i / n
        h = rise * math.sin(min(1.0, t * 1.15) * math.pi * 0.5) - droop * t ** 2.2
        r = length * t
        w = (rng.range(-1, 1) * wobble * t) if rng is not None else 0.0
        pts.append(base + d * r + np.array([0, h, 0]) + np.array([-d[2], 0, d[0]]) * w)
    return np.array(pts)


def susuki(name, seed):
    """Susuki: a fountain of long arching blades, and above them a few plumes of thin silky
    threads hanging to the lee (late summer: the first plumes, still tinged pink)."""
    rng = Rng(seed)
    Hh = rng.range(1.3, 1.8)
    p = Plant(name, 96, int(Hh * 20 + 50), 48, int(Hh * 20 + 50) - 10, seed, kind='herb')
    p.meta['species'] = 'susuki'
    blade = p.material('susukiLeaf', PAL['susukiLeaf'])
    plume = p.material('plume', PAL['plume'])
    stem = p.material('susuki', PAL['susuki'])
    lean = rng.range(-0.7, 0.7)              # the whole tuft is combed one way by the wind
    groups = [p.group(np.array([math.cos(a) * 0.3, 0.6, math.sin(a) * 0.3]), 0.40 + 0.08 * k)
              for k, a in enumerate(np.linspace(0, 2 * math.pi, 4, endpoint=False))]
    for k in range(rng.int(16, 22)):
        a = rng.range(0, 2 * math.pi)
        base = np.array([rng.range(-0.10, 0.10), 0.0, rng.range(-0.06, 0.06)])
        L = rng.range(0.8, 1.4)
        a2 = math.atan2(math.sin(a) * 0.5, math.cos(a) * 0.5 + lean * 0.6)
        pts = _arc(base, a2, L * rng.range(0.30, 0.6), L * rng.range(0.60, 0.95), L * rng.range(0.35, 0.8), n=12)
        g = groups[int(((a % (2 * math.pi)) / (2 * math.pi)) * 4) % 4]
        w = np.concatenate([np.full(4, 1.2), np.full(len(pts) - 4, 0.5)])
        p.blade(pts, w, blade, group=g, face=(math.cos(a) * 0.5, 0.8, math.sin(a) * 0.5), tone=rng.range(-0.16, 0.02))
    for k in range(rng.int(3, 6)):
        a = rng.range(-0.6, 0.6) + (0 if lean > 0 else math.pi)
        base = np.array([rng.range(-0.06, 0.06), 0.0, rng.range(-0.04, 0.04)])
        top_h = Hh * rng.range(0.85, 1.05)
        g = p.group(np.array([0, top_h, 0]), 0.95)
        stalk = np.array([base + np.array([math.cos(a) * 0.14 * t * t, top_h * t, 0]) for t in np.linspace(0, 1, 10)])
        p.blade(stalk, np.full(len(stalk), 0.85), stem, group=g, face=(0, 0, 1), fold=0.2, tone=0.05)
        tip = stalk[-1]
        d = np.array([math.cos(a), 0, 0])
        for j in range(rng.int(3, 5)):
            t = j / 4.0
            st = tip - np.array([0, 0.22 * t, 0]) + d * 0.03 * t
            L = rng.range(0.18, 0.30)
            spread = (j - 2) * 0.05
            th = np.array([st, st + d * (L * 0.45 + spread) + [0, -L * 0.30, 0], st + d * (L * 0.70 + spread * 1.6) + [0, -L * 0.85, 0]])
            p.blade(th, np.array([0.5, 0.5, 0.5]), plume, group=g, face=(d[0], 0.6, 0.4), tone=rng.range(-0.02, 0.14),
                    fold=0.2)
    p.leaf_opts.update(dict(blade_base=0.12, blade_tip=0.22, blade_jitter=0.22))
    return p


def fern(name, seed):
    """A shield fern: a loose fountain of fronds, the leaflets in clear pairs with gaps between."""
    rng = Rng(seed)
    Hh = rng.range(0.45, 0.65)
    p = Plant(name, 74, 50, 37, 40, seed, kind='herb')
    p.meta['species'] = 'fern'
    fm = p.material('fern', PAL['fern'])
    rach_m = p.material('stem', PAL['stem'])
    n_fr = rng.int(5, 7)
    angs = np.linspace(0, 2 * math.pi, n_fr, endpoint=False) + rng.range(0, 1)
    for k, a in enumerate(angs):
        a += rng.range(-0.25, 0.25)
        L = rng.range(0.55, 0.85)
        g = p.group(np.array([math.cos(a) * L * 0.5, Hh * 0.6, math.sin(a) * L * 0.5]), 0.35)
        rach = _arc(np.array([0, 0.02, 0]), a, L, Hh * rng.range(0.8, 1.1), Hh * rng.range(0.5, 0.9), n=14)
        face = (math.cos(a) * 0.3, 0.9, math.sin(a) * 0.3)
        p.blade(rach, np.linspace(1.0, 0.5, len(rach)), rach_m, group=g, face=face, tone=-0.04, fold=0.2)
        for i in range(2, len(rach) - 1, 2):
            t = i / (len(rach) - 1)
            P0 = rach[i]
            d = normalize(rach[i + 1] - rach[i - 1])
            side = normalize(np.cross(d, [0, 1, 0]))
            ln = 0.15 * (1 - t) ** 0.7 + 0.03
            for sd in (-1, 1):
                tip = P0 + side * sd * ln + d * ln * 0.55 + np.array([0, -ln * 0.3, 0])
                p.blade(np.array([P0, (P0 + tip) / 2 + [0, 0.01, 0], tip]), np.array([1.2, 1.3, 0.6]), fm, group=g, face=face,
                        tone=0.08 if sd < 0 else -0.06, fold=0.4)
    p.leaf_opts.update(dict(blade_base=0.18, blade_tip=0.18, blade_jitter=0.14))
    return p


def higanbana(name, seed):
    """Red spider lilies: bare stems, umbels of narrow recurved petals and long upswept stamens."""
    rng = Rng(seed)
    p = Plant(name, 60, 44, 30, 38, seed, kind='herb')
    p.meta['species'] = 'higanbana'
    stem = p.material('stem', PAL['stem'])
    red = p.material('higan', PAL['higan'])
    for k in range(rng.int(2, 5)):
        base = np.array([rng.range(-0.25, 0.25), 0, rng.range(-0.12, 0.12)])
        h = rng.range(0.34, 0.52)
        lean = np.array([rng.range(-0.05, 0.05), 0, rng.range(-0.03, 0.03)])
        g = p.group(base + np.array([0, h, 0]), 0.55)
        st = np.array([base + lean * t + np.array([0, h * t, 0]) for t in np.linspace(0, 1, 7)])
        p.blade(st, np.full(len(st), 0.5), stem, group=g, face=(0, 0, 1), fold=0.2)
        c = st[-1]
        m = rng.int(5, 7)
        for j in range(m):
            a = 2 * math.pi * j / m + rng.range(-0.3, 0.3)
            d = np.array([math.cos(a), 0, math.sin(a)])
            pet = np.array([c, c + d * 0.05 + [0, 0.02, 0], c + d * 0.08 - [0, 0.02, 0]])
            p.blade(pet, np.array([0.9, 0.8, 0.5]), red, group=g, face=(d[0] * 0.5, 0.8, d[2] * 0.5 + 0.2), tone=0.0, fold=0.5)
            stm = np.array([c + [0, 0.01, 0], c + d * 0.11 + [0, 0.08, 0], c + d * 0.20 + [0, 0.12, 0]])
            p.blade(stm, np.array([0.5, 0.5, 0.5]), red, group=g, face=(d[0] * 0.3, 0.9, 0.3), tone=0.20, fold=0.1)
    p.leaf_opts.update(dict(blade_base=0.30, blade_tip=0.10, blade_jitter=0.12))
    return p


def tsuyukusa(name, seed):
    """Asiatic dayflower: a low sprawl of pointed leaves, a few small blue two-petal flowers."""
    rng = Rng(seed)
    p = Plant(name, 44, 24, 22, 18, seed, kind='herb')
    p.meta['species'] = 'tsuyukusa'
    leaf = p.material('fern', PAL['fern'])
    blue = p.material('tsuyu', PAL['tsuyu'])
    yel = p.material('omina', PAL['omina'])
    g = p.group(np.array([0, 0.1, 0]), 0.25)
    for k in range(rng.int(9, 14)):
        a = rng.range(0, 2 * math.pi)
        b = np.array([rng.range(-0.3, 0.3), 0.01, rng.range(-0.15, 0.15)])
        d = np.array([math.cos(a), 0, math.sin(a)])
        pts = np.array([b, b + d * 0.06 + [0, 0.04, 0], b + d * 0.12 + [0, 0.05, 0]])
        p.blade(pts, np.array([1.3, 1.8, 0.6]), leaf, group=g, face=(d[0] * 0.3, 0.9, d[2] * 0.3 + 0.2), tone=rng.range(-0.1, 0.05))
    for k in range(rng.int(3, 6)):
        c = np.array([rng.range(-0.25, 0.25), rng.range(0.07, 0.12), rng.range(-0.1, 0.12)])
        for sd in (-1, 1):
            q = c + np.array([sd * 0.025, 0.01, 0])
            p.blade(np.array([q, q + [sd * 0.02, 0.02, 0]]), np.array([2.0, 1.8]), blue, group=g, face=(0, 0.7, 0.7), tone=0.1, fold=0.3)
        p.blade(np.array([c - [0, 0.012, 0], c - [0, 0.02, 0]]), np.array([1.0, 0.8]), yel, group=g, face=(0, 0.7, 0.7), tone=0.2)
    p.leaf_opts.update(dict(blade_base=0.28, blade_tip=0.1, blade_jitter=0.2))
    return p


def ominaeshi(name, seed):
    """Patrinia: tall thin stems topped with flat clusters of tiny yellow flowers."""
    rng = Rng(seed)
    Hh = rng.range(0.8, 1.15)
    p = Plant(name, 50, int(Hh * 20 + 30), 25, int(Hh * 20 + 30) - 8, seed, kind='herb')
    p.meta['species'] = 'ominaeshi'
    stem = p.material('stem', PAL['stem'])
    leaf = p.material('fern', PAL['fern'])
    yel = p.material('omina', PAL['omina'])
    for k in range(rng.int(2, 4)):
        base = np.array([rng.range(-0.12, 0.12), 0, rng.range(-0.06, 0.06)])
        h = Hh * rng.range(0.8, 1.0)
        lean = np.array([rng.range(-0.12, 0.12), 0, 0])
        g = p.group(base + np.array([0, h, 0]), 0.7)
        st = np.array([base + lean * t * t + np.array([0, h * t, 0]) for t in np.linspace(0, 1, 9)])
        p.blade(st, np.full(len(st), 1.0), stem, group=g, face=(0, 0, 1), fold=0.2)
        for i in (2, 4):
            for sd in (-1, 1):
                q = st[i]
                p.blade(np.array([q, q + [sd * 0.10, 0.03, 0.02], q + [sd * 0.16, 0.0, 0.03]]), np.array([1.4, 1.6, 0.6]),
                        leaf, group=g, face=(sd * 0.3, 0.9, 0.3), tone=-0.05)
        top = st[-1]
        # a flat-topped corymb: a few short branches, a dense cap of tiny flowers
        for j in range(rng.int(9, 14)):
            a = rng.range(0, 2 * math.pi)
            r = rng.range(0.0, 0.10)
            q = top + np.array([math.cos(a) * r, rng.range(-0.01, 0.03), math.sin(a) * r * 0.6])
            p.blade(np.array([q, q + [0.012, 0.006, 0]]), np.array([1.6, 1.4]), yel, group=g, face=(0, 0.8, 0.6),
                    tone=rng.range(-0.05, 0.15), fold=0.2)
    p.leaf_opts.update(dict(blade_base=0.28, blade_tip=0.1, blade_jitter=0.2))
    return p
