"""Broadleaf trees: ブナ beech (the moss forest), 柿 persimmon, イロハモミジ maple (green, turning,
red). One architecture: a trunk that forks into a few main limbs, each carrying foliage masses at
its end, sub-branches to the masses in between, a dark crown interior behind the gaps."""
import math

import numpy as np

from .. import arch
from .. import raster as R
from ..core import KZ, PPM, Rng, hash01, normalize, smoothstep, vnoise2
from ..palette import PAL
from ..plant import Plant


def _crown(p, rng, tp, Ht, fork_t, crown_c, crown_r, n_masses, mass_r, leaf, lit, bark, cell_r, bumps,
           flat_y=0.72, n_limbs=3, limb_r=0.2, layered=0, under=None, sway_base=0.4):
    """Main limbs from the fork to the crown's rim; masses on a dome (or in flat layers)."""
    env = p.envelope(crown_c, crown_r)
    top = tp[-1]
    limb_ends = []
    paths = []
    for k in range(n_limbs):
        a = 2 * math.pi * k / n_limbs + rng.range(-0.5, 0.5)
        up = rng.range(0.25, 0.75)
        d = np.array([math.cos(a) * (1 - up * 0.6), up, math.sin(a) * (1 - up * 0.6)])
        end = crown_c + d * crown_r * rng.range(0.55, 0.75)
        start = arch.point_on(tp, rng.range(fork_t, 1.0))
        path = arch.limb_to(start, end, rise=0.45, seed=int(rng.range(0, 1e6)), n=22)
        p.tube(path, arch.collar(np.linspace(limb_r, limb_r * 0.40, len(path)), k=1.35), bark, R.PART_LIMB, dens=2.6)
        paths.append((path, np.linspace(limb_r, limb_r * 0.40, len(path))))
        limb_ends.append(end)
    centres = []
    if layered:
        # tiers of flat masses (maple): each tier a loose ring, wider in the middle tiers
        for L in range(layered):
            tt = L / max(1, layered - 1)
            y = crown_c[1] - crown_r[1] * 0.75 + tt * crown_r[1] * 1.55
            ring = crown_r[0] * (1.0 - abs(tt - 0.35) * 0.9) * rng.range(0.85, 1.0)
            n = max(2, int(ring * 1.25))
            ph = rng.range(0, 2 * math.pi)
            for j in range(n):
                a = ph + 2 * math.pi * j / n + rng.range(-0.4, 0.4)
                rr = ring * rng.range(0.45, 0.85)
                c = np.array([crown_c[0] + math.cos(a) * rr, y + rng.range(-0.25, 0.25),
                              crown_c[2] + math.sin(a) * rr * 0.85])
                centres.append((c, mass_r * rng.range(0.8, 1.15) * (1.1 - tt * 0.35)))
            if L == layered - 1:
                centres.append((np.array([crown_c[0], y + 0.2, crown_c[2]]), mass_r * 0.8))
    else:
        pts, outer = arch.dome_layout(crown_c, crown_r * 0.70, n_masses, rng, shell=0.45, top_bias=0.35, min_sep=1.3)
        for c in pts:
            centres.append((c, mass_r * rng.range(0.85, 1.15)))
    for c, rm in centres:
        # carry each mass on a branch from the nearest limb
        best = None
        for path, rr in paths:
            d = np.linalg.norm(path - c, axis=1)
            j = int(np.argmin(d))
            if best is None or d[j] < best[0]:
                best = (d[j], path[j], rr[j])
        dist, a, ra = best
        if dist > 0.6:
            sp = arch.limb_to(a, c, rise=0.3, seed=int(abs(c[0] * 131 + c[2] * 17)) + p.seed, n=12)
            rb = max(0.05, min(ra * 0.7, 0.12))
            p.tube(sp, np.linspace(rb, rb * 0.5, len(sp)), bark, R.PART_LIMB, dens=2.8)
        ry = rm * (flat_y if not layered else 0.42)
        sway = np.clip(sway_base + 0.12 * math.hypot(c[0] - top[0], c[2] - top[2]), 0.3, 1.0)
        p.mass(c, np.array([rm, ry, rm]), leaf, env, cell_r=cell_r, lit_mat=lit, bumps=bumps,
               flat=0.62, sway=sway, under=under)
    return env, paths


def beech(name, seed, moss_forest=True):
    rng = Rng(seed)
    Ht = rng.range(6.5, 8.0)              # trunk to the top of the fork
    crown_w = rng.range(9.0, 11.0)
    crown_h = rng.range(6.0, 7.5)
    W = int(crown_w * 20 + 110)
    Hc = int((Ht + crown_h + 2.0) * 20 + 60)
    p = Plant(name, W, Hc, W // 2, Hc - 30, seed)
    p.meta['species'] = 'beech'
    leaf = p.material('beech', PAL['beech'])
    bark = p.material('barkBeech', PAL['barkBeech'])
    moss = p.material('moss', PAL['moss'])
    lichen = p.material('lichen', PAL['lichen'])
    p.bark_fx[bark] = arch.bark_smooth(seed, streak=0.06, lichen_mat=lichen, lichen_p=0.18,
                                       moss_mat=moss if moss_forest else None, moss_h=1.2 if moss_forest else 0.4)
    lean = (rng.range(-0.6, 0.6), rng.range(-0.3, 0.3))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.18, seed=seed, n=40)
    r0 = rng.range(0.36, 0.46)
    p.tube(tp, lambda t: r0 * (1 + 0.55 * math.exp(-t * 16)) * (1 - 0.30 * t), bark, R.PART_TRUNK, dens=2.6, cap=False)
    p.trunk_top = tp[-1]
    crown_c = tp[-1] + np.array([0, crown_h * 0.42, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.9])
    _crown(p, rng, tp, Ht, 0.62, crown_c, crown_r, rng.int(11, 14), rng.range(1.9, 2.3), leaf, None, bark,
           cell_r=0.24, bumps=(4, 7, 0.10, 0.24), n_limbs=rng.int(3, 4), limb_r=r0 * 0.55)
    deep = p.material('beechDeep', PAL['camphorDeep'])
    p.interior(crown_c + np.array([0, -crown_h * 0.15, 0]), crown_r * np.array([0.62, 0.45, 0.6]), deep)
    p.leaf_opts.update(dict(w_env=0.52, inset=0.10, hl_p=0.40, inner_margin=6))
    return p


def persimmon(name, seed):
    rng = Rng(seed)
    Ht = rng.range(2.0, 2.8)              # a low, crooked fork
    crown_w = rng.range(6.0, 7.4)
    crown_h = rng.range(4.2, 5.2)
    W = int(crown_w * 20 + 100)
    Hc = int((Ht + crown_h + 2.6) * 20 + 50)
    p = Plant(name, W, Hc, W // 2, Hc - 26, seed)
    p.meta['species'] = 'persimmon'
    leaf = p.material('kaki', PAL['kaki'])
    bark = p.material('barkKaki', PAL['barkKaki'])
    fruit_g = p.material('kakiGreen', PAL['kakiGreen'])
    fruit_o = p.material('kakiFruit', PAL['kakiFruit'])
    p.bark_fx[bark] = arch.bark_blocky(seed)
    lean = (rng.range(-0.7, 0.7), rng.range(-0.3, 0.3))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.25, seed=seed, n=30)
    r0 = rng.range(0.20, 0.25)
    p.tube(tp, lambda t: r0 * (1 + 0.45 * math.exp(-t * 14)) * (1 - 0.2 * t), bark, R.PART_TRUNK, dens=2.6, cap=False)
    p.trunk_top = tp[-1]
    crown_c = tp[-1] + np.array([lean[0] * 0.3, crown_h * 0.55, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.9])
    _crown(p, rng, tp, Ht, 0.75, crown_c, crown_r, rng.int(8, 10), rng.range(1.45, 1.75), leaf, None, bark,
           cell_r=0.27, bumps=(3, 5, 0.12, 0.26), n_limbs=rng.int(3, 4), limb_r=r0 * 0.75)
    deep = p.material('kakiDeep', PAL['camphorDeep'])
    p.interior(crown_c + np.array([0, -crown_h * 0.15, 0]), crown_r * np.array([0.6, 0.45, 0.6]), deep)
    p.leaf_opts.update(dict(w_env=0.50, inset=0.10, hl_p=0.55, inner_margin=5))

    # fruit: on the outer, lower clumps; most still green-yellow in late summer, a few turning
    def fruit(pl, cv):
        frng = Rng(seed * 3 + 1)
        n = frng.int(10, 16)
        cand = np.nonzero(pl.c_pos[:, 1] < crown_c[1] + crown_r[1] * 0.3)[0]
        if len(cand) == 0:
            return
        for _ in range(n):
            i = int(frng.pick(cand))
            c = pl.c_pos[i]
            d = normalize(c - pl.masses[pl.c_mass[i]]['c'])
            P = c + d * 0.18 + np.array([0, -0.12, 0])
            mat = fruit_o if frng() < 0.35 else fruit_g
            R.ellipsoids(cv, pl.D([P]), [[0.085, 0.08, 0.085 * pl.kz]], R.PART_DETAIL, mat,
                         mass=pl.c_mass[i], nkz=pl.kz)
    p.details.append(fruit)
    return p


def maple(name, seed, variant='green'):
    """variant: 'green' | 'turn' (the outermost, sunniest leaves already orange-red) | 'red'."""
    rng = Rng(seed)
    Ht = rng.range(1.6, 2.4)
    crown_w = rng.range(6.0, 7.6)
    crown_h = rng.range(3.4, 4.4)
    W = int(crown_w * 20 + 100)
    Hc = int((Ht + crown_h + 2.6) * 20 + 50)
    p = Plant(name, W, Hc, W // 2, Hc - 26, seed)
    p.meta['species'] = 'maple_' + variant
    base = {'green': 'maple', 'turn': 'maple', 'red': 'mapleRed'}[variant]
    leaf = p.material(base, PAL[base])
    bark = p.material('barkGrey', PAL['barkGrey'])
    p.bark_fx[bark] = arch.bark_smooth(seed, streak=0.08)
    # two or three stems from the foot, leaning apart (irohamomiji grow like that)
    n_st = rng.int(1, 3)
    stems = []
    for k in range(n_st):
        a = rng.range(0, 2 * math.pi)
        lean = (math.cos(a) * rng.range(0.4, 1.0) * (1 if n_st > 1 else 0.4), math.sin(a) * 0.3)
        tp = arch.trunk_path(Ht + rng.range(0, 0.6), lean=lean, wobble=0.2, seed=seed * 7 + k, n=26, bend=0.3)
        r0 = rng.range(0.12, 0.17) * (1.25 if k == 0 else 1.0)
        p.tube(tp, lambda t, r0=r0: r0 * (1 + 0.4 * math.exp(-t * 12)) * (1 - 0.3 * t), bark, R.PART_TRUNK, dens=2.8,
               cap=False)
        stems.append((tp, r0))
    tp = stems[0][0]
    p.trunk_top = tp[-1]
    crown_c = tp[-1] + np.array([0, crown_h * 0.5, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.9])
    env, paths = _crown(p, rng, tp, Ht, 0.7, crown_c, crown_r, 0, rng.range(1.15, 1.4), leaf, None, bark,
                        cell_r=0.15, bumps=(5, 6, 0.30, 0.42, 2.2), n_limbs=rng.int(4, 5), limb_r=0.09,
                        layered=rng.int(3, 4))
    for tp2, r2 in stems[1:]:
        e2 = tp2[-1]
        p.tube(arch.limb_to(e2, crown_c + (e2 - tp[-1]) * 1.4 + np.array([0, 0.6, 0]), rise=0.4, seed=seed + 5, n=14),
               np.linspace(r2 * 0.8, r2 * 0.35, 14), bark, R.PART_LIMB, dens=2.8)
    if variant == 'turn':
        turn = p.material('mapleTurn', PAL['mapleTurn'])
        red = p.material('mapleRed', PAL['mapleRed'])

        def fn(pl, pos, mass_ids, mats):
            # the outermost and highest clumps turn first; patches, not salt and pepper
            d = (pos - crown_c) / crown_r
            outer = np.linalg.norm(d * np.array([1, 0.8, 1]), axis=1) + d[:, 1] * 0.35
            patch = vnoise2(pos[:, 0] * 0.9, pos[:, 2] * 0.9 + pos[:, 1] * 0.6, seed + 9)
            k = outer * 0.65 + patch * 0.55
            out = mats.copy()
            out[k > 0.92] = turn
            out[k > 1.05] = red
            return out
        p.clump_mat_fn = fn
    p.leaf_opts.update(dict(w_env=0.50, inset=0.14, hl_p=0.55, crest_p=0.5, inner_margin=4,
                            self_shadow=0.50, shadow_floor=0.35))
    deep = p.material('mapleDeep', PAL['camphorDeep'] if variant != 'red' else PAL['mapleRed'])
    p.interior(crown_c, crown_r * np.array([0.55, 0.35, 0.5]), deep)
    return p
