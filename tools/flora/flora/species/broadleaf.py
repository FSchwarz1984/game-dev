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
    """Buna: a short trunk that forks low into two or three smooth grey stems climbing into a broad,
    layered crown; lichen patches on the bark; in the moss forest, moss up the foot and roots."""
    rng = Rng(seed)
    Ht = rng.range(2.4, 3.4)              # the fork
    crown_w = rng.range(10.0, 12.0)
    crown_h = rng.range(6.0, 7.0)
    stem_h = rng.range(5.5, 7.0)          # stems climb this far above the fork
    W = int(crown_w * 20 + 110)
    Hc = int((Ht + stem_h + crown_h * 0.6 + 2.0) * 20 + 60)
    p = Plant(name, W, Hc, W // 2, Hc - 30, seed)
    p.meta['species'] = 'beech'
    leaf = p.material('beech', PAL['beech'])
    bark = p.material('barkBeech', PAL['barkBeech'])
    moss = p.material('moss', PAL['moss'])
    lichen = p.material('lichen', PAL['lichen'])
    fx = arch.bark_smooth(seed, streak=0.05, lichen_mat=lichen, lichen_p=0.22,
                          moss_mat=moss if moss_forest else None, moss_h=1.3 if moss_forest else 0.35)
    p.bark_fx[bark] = fx
    lean = (rng.range(-0.4, 0.4), rng.range(-0.2, 0.2))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.10, seed=seed, n=24)
    r0 = rng.range(0.42, 0.52)
    p.tube(tp, lambda t: r0 * (1 + 0.6 * math.exp(-t * 9)) * (1 - 0.12 * t), bark, R.PART_TRUNK, dens=2.6, cap=False)
    top = tp[-1]
    p.trunk_top = top + np.array([0, stem_h * 0.6, 0])
    crown_c = top + np.array([lean[0] * 0.5 + rng.range(-0.8, 0.8), stem_h + crown_h * 0.25, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.9])
    env = p.envelope(crown_c, crown_r)
    # the stems: ascending, spreading apart, each ending inside a big mass
    n_st = rng.int(2, 3)
    paths = []
    limb_tips = []
    for k in range(n_st):
        a = (k / n_st) * 2 * math.pi + rng.range(-0.4, 0.4) + 0.4
        out = rng.range(3.0, 4.4)
        end = top + np.array([math.cos(a) * out, stem_h * rng.range(0.85, 1.05), math.sin(a) * out * 0.7])
        path = arch.limb_to(top - np.array([0, 0.3, 0]), end, rise=0.35, seed=seed * 5 + k, n=26)
        rs = r0 * rng.range(0.55, 0.68)
        p.tube(path, arch.collar(np.linspace(rs, rs * 0.45, len(path)), k=1.25), bark, R.PART_LIMB, dens=2.6)
        paths.append((path, np.linspace(rs, rs * 0.45, len(path))))
        # side limbs off each stem, out to the crown's rim
        for j in range(rng.int(2, 4)):
            t0 = rng.range(0.30, 0.85)
            a2 = a + rng.range(-1.3, 1.3)
            st = arch.point_on(path, t0)
            en = st + np.array([math.cos(a2) * rng.range(2.2, 3.6), rng.range(0.4, 1.4), math.sin(a2) * rng.range(1.6, 2.8)])
            sp = arch.limb_to(st, en, rise=0.4, seed=seed * 9 + k * 3 + j, n=16)
            rb = rs * 0.42
            p.tube(sp, arch.collar(np.linspace(rb, rb * 0.4, len(sp)), k=1.25), bark, R.PART_LIMB, dens=2.6)
            paths.append((sp, np.linspace(rb, rb * 0.4, len(sp))))
            limb_tips.append(en)
        limb_tips.append(end)
    # masses: one at every limb's tip (no bare stick ends), then an upper tier to close the crown
    centres = [(c + np.array([0, 0.35, 0]), rng.range(1.6, 2.1)) for c in limb_tips]
    for tier, (yy, ring, n, rm) in enumerate([(0.15, 0.62, 5, 2.0), (0.60, 0.35, 3, 1.9)]):
        ph = rng.range(0, 2 * math.pi)
        for j in range(n):
            a = ph + 2 * math.pi * j / n + rng.range(-0.3, 0.3)
            rr = ring * rng.range(0.8, 1.05)
            c = crown_c + np.array([math.cos(a) * rr * crown_r[0], yy * crown_r[1] + rng.range(-0.3, 0.3),
                                    math.sin(a) * rr * crown_r[2]])
            centres.append((c, rm * rng.range(0.85, 1.15)))
    for c, rm in centres:
        best = None
        for path, rr in paths:
            d = np.linalg.norm(path - c, axis=1)
            j = int(np.argmin(d))
            if best is None or d[j] < best[0]:
                best = (d[j], path[j], rr[j])
        dist, a, ra = best
        if dist > 0.7:
            sp = arch.limb_to(a, c, rise=0.3, seed=int(abs(c[0] * 131 + c[2] * 17)) + seed, n=12)
            rb = max(0.05, min(ra * 0.7, 0.11))
            p.tube(sp, np.linspace(rb, rb * 0.5, len(sp)), bark, R.PART_LIMB, dens=2.8)
        sway = float(np.clip(0.4 + 0.1 * math.hypot(c[0] - top[0], c[2] - top[2]), 0.3, 1.0))
        p.mass(c, np.array([rm, rm * 0.62, rm]), leaf, env, cell_r=0.22 * rng.range(0.9, 1.1),
               bumps=(4, 7, 0.10, 0.24), sway=sway, fringe=0.4 if c[1] < crown_c[1] else 0.0)
    deep = p.material('beechDeep', PAL['camphorDeep'])
    p.interior(crown_c + np.array([0, -crown_h * 0.12, 0]), crown_r * np.array([0.55, 0.32, 0.5]), deep)
    p.leaf_opts.update(dict(w_env=0.50, inset=0.10, hl_p=0.40, inner_margin=6))
    return p


def persimmon(name, seed):
    """Kaki: a dark blocky trunk forking low into crooked limbs that spread like a vase; an open
    crown of glossy leaf clumps at the limb ends with gaps between; fruit along the outer clumps
    (late summer: most still green-yellow, some already orange)."""
    rng = Rng(seed)
    Ht = rng.range(1.6, 2.2)
    crown_w = rng.range(6.6, 7.8)
    crown_h = rng.range(4.0, 4.8)
    W = int(crown_w * 20 + 110)
    Hc = int((Ht + crown_h + 3.0) * 20 + 50)
    p = Plant(name, W, Hc, W // 2, Hc - 26, seed)
    p.meta['species'] = 'persimmon'
    leaf = p.material('kaki', PAL['kaki'])
    bark = p.material('barkKaki', PAL['barkKaki'])
    fruit_g = p.material('kakiGreen', PAL['kakiGreen'])
    fruit_o = p.material('kakiFruit', PAL['kakiFruit'])
    p.bark_fx[bark] = arch.bark_blocky(seed)
    lean = (rng.range(-0.6, 0.6), rng.range(-0.2, 0.2))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.22, seed=seed, n=24)
    r0 = rng.range(0.20, 0.25)
    p.tube(tp, lambda t: r0 * (1 + 0.45 * math.exp(-t * 12)) * (1 - 0.15 * t), bark, R.PART_TRUNK, dens=2.6, cap=False)
    top = tp[-1]
    p.trunk_top = top + np.array([0, 1.5, 0])
    crown_c = top + np.array([lean[0] * 0.3, crown_h * 0.62, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.85])
    env = p.envelope(crown_c, crown_r)
    tips = []
    paths = []
    n_l = rng.int(3, 4)
    for k in range(n_l):
        a = 2 * math.pi * k / n_l + rng.range(-0.4, 0.4)
        out = rng.range(1.6, 2.4)
        end = top + np.array([math.cos(a) * out, rng.range(1.6, 2.4), math.sin(a) * out * 0.8])
        path = arch.limb_to(top - np.array([0, 0.2, 0]), end, rise=0.3, seed=seed * 11 + k, n=18)
        # crooked: a kink or two
        path[:, 0] += 0.25 * np.sin(np.linspace(0, 3.1, len(path)) * 2 + k) * np.linspace(0, 1, len(path))
        rl = r0 * rng.range(0.6, 0.75)
        p.tube(path, arch.collar(np.linspace(rl, rl * 0.45, len(path)), k=1.3), bark, R.PART_LIMB, dens=2.6)
        paths.append(path)
        for j in range(2):
            a2 = a + (j - 0.5) * rng.range(0.8, 1.4)
            st = arch.point_on(path, rng.range(0.6, 0.95))
            en = st + np.array([math.cos(a2) * rng.range(1.0, 1.7), rng.range(0.6, 1.3), math.sin(a2) * rng.range(0.8, 1.4)])
            sp = arch.limb_to(st, en, rise=0.35, seed=seed * 13 + k * 2 + j, n=12)
            rb = rl * 0.45
            p.tube(sp, np.linspace(rb, rb * 0.45, len(sp)), bark, R.PART_LIMB, dens=2.8)
            tips.append(en)
        tips.append(end)
    tips.append(crown_c + np.array([0, crown_r[1] * 0.4, 0]))
    for c in tips:
        rm = rng.range(1.15, 1.5)
        c = c + np.array([0, rm * 0.25, 0])
        p.mass(c, np.array([rm, rm * 0.70, rm]), leaf, env, cell_r=0.26 * rng.range(0.9, 1.1),
               bumps=(3, 5, 0.12, 0.26), sway=float(np.clip(0.4 + 0.12 * math.hypot(c[0] - top[0], c[2] - top[2]), 0.3, 1.0)),
               fringe=0.3)
    deep = p.material('kakiDeep', PAL['camphorDeep'])
    p.interior(crown_c + np.array([0, -crown_h * 0.1, 0]), crown_r * np.array([0.45, 0.30, 0.45]), deep)
    p.leaf_opts.update(dict(w_env=0.45, inset=0.10, hl_p=0.65, inner_margin=5))

    def fruit(pl, cv):
        frng = Rng(seed * 3 + 1)
        n = frng.int(12, 18)
        cand = np.nonzero(pl.c_pos[:, 1] < crown_c[1] + crown_r[1] * 0.2)[0]
        if len(cand) == 0:
            return
        for _ in range(n):
            i = int(frng.pick(cand))
            c = pl.c_pos[i]
            d = normalize(c - pl.masses[pl.c_mass[i]]['c'])
            P = c + d * 0.26 + np.array([0, -0.10, 0.25])
            mat = fruit_o if frng() < 0.5 else fruit_g
            R.ellipsoids(cv, pl.D([P]), [[0.13, 0.125, 0.13 * pl.kz]], R.PART_DETAIL, mat,
                         mass=pl.c_mass[i], nkz=pl.kz)
    p.details.append(fruit)
    return p


def maple(name, seed, variant='green'):
    """Irohamomiji: one to three slim stems leaning apart, branches spreading out flat in tiers,
    each tier a thin layer of fine-leaved sprays with sky between the layers.
    variant: 'green' | 'turn' (the outermost, sunniest sprays already orange-red) | 'red'."""
    rng = Rng(seed)
    Ht = rng.range(1.2, 1.9)
    crown_w = rng.range(7.0, 8.6)
    crown_h = rng.range(3.6, 4.6)
    W = int(crown_w * 20 + 110)
    Hc = int((Ht + crown_h + 2.6) * 20 + 50)
    p = Plant(name, W, Hc, W // 2, Hc - 26, seed)
    p.meta['species'] = 'maple_' + variant
    base = {'green': 'maple', 'turn': 'maple', 'red': 'mapleRed'}[variant]
    leaf = p.material(base, PAL[base])
    bark = p.material('barkGrey', PAL['barkGrey'])
    p.bark_fx[bark] = arch.bark_smooth(seed, streak=0.08)
    n_st = rng.int(1, 3)
    stems = []
    for k in range(n_st):
        a = rng.range(0, 2 * math.pi)
        lean = (math.cos(a) * rng.range(0.4, 1.0) * (1 if n_st > 1 else 0.4), math.sin(a) * 0.3)
        tp = arch.trunk_path(Ht + rng.range(0, 0.5), lean=lean, wobble=0.2, seed=seed * 7 + k, n=20, bend=0.3)
        r0 = rng.range(0.12, 0.16) * (1.25 if k == 0 else 1.0)
        p.tube(tp, lambda t, r0=r0: r0 * (1 + 0.4 * math.exp(-t * 12)) * (1 - 0.3 * t), bark, R.PART_TRUNK, dens=2.8,
               cap=False)
        stems.append((tp, r0))
    tp = stems[0][0]
    p.trunk_top = tp[-1] + np.array([0, 1.5, 0])
    crown_c = tp[-1] + np.array([0, crown_h * 0.5, 0])
    crown_r = np.array([crown_w / 2, crown_h / 2, crown_w / 2 * 0.85])
    env = p.envelope(crown_c, crown_r)
    # tiers: branches fan out flat from the stems at a few heights; each ends in a thin layer of
    # fine leaves. Layers are thin and spaced apart, so sky shows between them (v0.1's layered maple)
    n_tiers = rng.int(3, 4)
    gap = crown_h / (n_tiers + 0.3)
    for L in range(n_tiers):
        tt = L / max(1, n_tiers - 1)
        y = crown_c[1] - crown_h * 0.42 + L * gap
        reach = crown_r[0] * (1.0 - abs(tt - 0.3) * 0.8)
        n_b = rng.int(3, 4) if tt < 0.9 else 2
        ph = rng.range(0, 2 * math.pi)
        for j in range(n_b):
            stp, sr = stems[j % len(stems)]
            st = arch.point_on(stp, 1.0) + np.array([0, (y - stp[-1][1]) * 0.35, 0])
            a = ph + 2 * math.pi * j / n_b + rng.range(-0.35, 0.35)
            rr = reach * rng.range(0.55, 0.9)
            end = np.array([crown_c[0] + math.cos(a) * rr, y + rng.range(-0.12, 0.12), crown_c[2] + math.sin(a) * rr * 0.55])
            path = arch.limb_to(st, end, rise=0.15, seed=seed * 17 + L * 7 + j, n=16)
            p.tube(path, np.linspace(sr * 0.55, sr * 0.18, len(path)), bark, R.PART_LIMB, dens=2.8)
            for tm in (0.70, 1.0):
                c = arch.point_on(path, tm) + np.array([rng.range(-0.2, 0.2), 0.10, rng.range(-0.15, 0.15)])
                rm = rng.range(0.95, 1.30) * (1.1 - tt * 0.3)
                p.mass(c, np.array([rm, rm * 0.20, rm * 0.70]), leaf, env, cell_r=0.12,
                       bumps=(5, 6, 0.30, 0.42, 2.2), flat=0.55, sway=float(np.clip(0.45 + 0.1 * rr, 0.3, 1.0)),
                       fringe=0.25)
    if variant == 'turn':
        turn = p.material('mapleTurn', PAL['mapleTurn'])
        red = p.material('mapleRed', PAL['mapleRed'])

        def fn(pl, pos, mass_ids, mats):
            # the outermost and highest sprays turn first: a warm rim, not blotches
            d = (pos - crown_c) / crown_r
            outer = np.linalg.norm(d * np.array([1, 0.6, 1]), axis=1) + d[:, 1] * 0.25 - d[:, 0] * 0.08
            jit = (vnoise2(pos[:, 0] * 2.4, pos[:, 2] * 2.4 + pos[:, 1] * 1.5, seed + 9) - 0.5) * 0.14
            k = outer + jit
            out = mats.copy()
            out[k > 0.80] = turn
            out[k > 0.93] = red
            return out
        p.clump_mat_fn = fn
    p.leaf_opts.update(dict(w_env=0.42, inset=0.16, hl_p=0.55, crest_p=0.5, inner_margin=3,
                            self_shadow=0.40, shadow_floor=0.40))
    return p
