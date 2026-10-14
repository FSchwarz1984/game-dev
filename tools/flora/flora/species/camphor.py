"""大楠 the great camphor (御神木) at the shrine clearing: one organism.

Buttress fins flare out of the trunk and run on as surface roots over the ground; the trunk carries
a shimenawa with shide; eight main limbs (two long low ones reaching west over the hut and east over
the shrine) leave the trunk and end inside the foliage masses they carry, so the crown is held by
its limbs instead of floating above a stump. ~22 m crown, ~3.2 m trunk, buttresses ~6 m across.
Modelled in natural metres (plant.py): the canopy's cast shade covers the clearing.
"""
import math

import numpy as np

from .. import arch
from .. import raster as R
from ..core import PPM, Rng, normalize, vnoise2
from ..palette import PAL
from ..plant import Plant


def _rope_fx(seed):
    def fx(u, v, n, P, base, T):
        tw = ((u * 7.5 + v * 1.0 / math.pi) % 1.0)
        dv = np.where(tw < 0.45, 0.12, -0.06) + np.where(tw > 0.86, -0.16, 0.0)
        return dv, None
    return fx


def _camphor_bark(seed, moss, lichen, hollow=None):
    base_fx = arch.bark_furrowed(seed, depth=0.24, lichen_mat=lichen)

    def fx(u, v, n, P, base, T):
        dv, mat = base_fx(u, v, n, P, base, T)
        if hollow is not None:
            # 洞: an old cavity at the foot; dark inside, a rolled lip around it
            th = np.arctan2(P[:, 0] - hollow['x'], P[:, 2] - hollow['z'])
            dth = (th - hollow['th'] + np.pi) % (2 * np.pi) - np.pi
            yy = (P[:, 1] - hollow['y']) / hollow['h']
            # a pointed arch: narrower toward the top, as old cavities split upward along the grain
            wth = hollow['wth'] * (1.0 - np.clip(yy, 0, 1) * 0.55)
            e = (dth / wth) ** 2 + yy ** 2
            e = e + (vnoise2(dth * 9, P[:, 1] * 6, seed + 41) - 0.5) * 0.18
            inside = e < 1.0
            lip = (e >= 1.0) & (e < 1.5)
            deep = inside & ((dth / wth) - yy * 0.6 < 0.15)
            dv = np.where(inside, np.where(deep, -1.0, -0.62), dv)
            dv = np.where(lip & ((dth < 0.0) | (yy < -0.6)), dv + 0.18, np.where(lip, dv - 0.06, dv))
            mat = np.where(inside, 0, mat) if mat is not None else mat
        # moss: cushions on the buttresses and lower trunk, more on the shaded north-west side,
        # and along the top of the big limbs
        q = vnoise2(P[:, 0] * 1.1 + P[:, 2] * 0.7, P[:, 1] * 0.9, seed + 21) * 0.72 + \
            vnoise2(P[:, 0] * 3.5, P[:, 1] * 3.5 + P[:, 2], seed + 22) * 0.28
        low = np.clip(1.0 - P[:, 1] / 2.6, 0, 1) * np.clip(P[:, 1] / 0.35, 0, 1)   # not on the roots' flanks
        side = np.clip(-P[:, 0] * 0.2 - P[:, 2] * 0.25, -0.3, 0.3)
        up = np.clip(n[:, 1], 0, 1)
        k = 0.72 - low * 0.18 - side * 0.30 - up * 0.10
        mm = (q > k) & (dv > -0.15)
        mat = np.where(mm & (mat == 0), moss, mat)
        dv = np.where(mm, dv * 0.25 + (q - k) * 0.7 - 0.05, dv)
        return dv, mat
    return fx


def _limb_bark(seed, moss):
    base_fx = arch.bark_furrowed(seed + 3, depth=0.10, n_furrows=9)

    def fx(u, v, n, P, base, T):
        dv, mat = base_fx(u, v, n, P, base, T)
        q = vnoise2(P[:, 0] * 1.4, P[:, 2] * 1.4 + P[:, 1], seed + 31)
        mm = (n[:, 1] > 0.35) & (q > 0.45)          # moss along the top of the limbs
        mat = np.where(mm, moss, mat)
        dv = np.where(mm, -0.06, dv)
        return dv, mat
    return fx


def camphor(name='camphor_a', seed=1):
    rng = Rng(seed)
    W, H = 640, 600
    ax, ay = 320, 500
    p = Plant(name, W, H, ax, ay, seed)
    p.meta['species'] = 'camphor'
    p.meta['trunk_occluder'] = True
    leaf = p.material('camphor', PAL['camphor'])
    new = p.material('camphorNew', PAL['camphorNew'])
    bark = p.material('barkCamphor', PAL['barkCamphor'])
    moss = p.material('moss', PAL['moss'])
    lichen = p.material('lichen', PAL['lichen'])
    rope = p.material('rope', PAL['rope'])
    paper = p.material('paper', PAL['paper'])
    p.bark_fx[bark] = _camphor_bark(seed, moss, None,
                                    hollow=dict(x=0.0, z=0.0, th=rng.range(-0.70, -0.50), wth=0.20, y=0.85, h=0.72))
    limb_bark = p.material('barkCamphorLimb', PAL['barkCamphor'])
    p.bark_fx[limb_bark] = _limb_bark(seed, moss)
    p.bark_fx[rope] = _rope_fx(seed)

    # ---------------- trunk with buttress fins (natural metres)
    Ht = 7.4
    lean = (rng.range(-0.4, 0.4), rng.range(0.0, 0.4))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.22, seed=seed, n=48)
    r_at = lambda t: 1.95 - 0.55 * t + 0.08 * math.sin(t * 6.0 + seed)
    nf = 7
    angs = np.linspace(-2.7, 2.5, nf) + np.array([rng.range(-0.15, 0.15) for _ in range(nf)])
    fins = [dict(th=float(a), A=rng.range(1.2, 2.0) * (1.0 if abs(a) < 2.0 else 0.75),
                 Hs=rng.range(0.9, 1.5), p=rng.range(4.0, 7.0)) for a in angs]

    def rfun(s, th, R0):
        out = R0.copy()
        for f in fins:
            c = np.cos(th - f['th'])
            out = out + f['A'] * np.exp(-s / f['Hs']) * np.maximum(0, c) ** f['p']
        out = out + 0.09 * np.sin(th * 5 + s * 0.35 + seed) * np.exp(-s / 3.0) + 0.05 * np.sin(th * 3 - s * 0.5)
        return out

    p.tube(tp, r_at, bark, R.PART_TRUNK, rfun=rfun, dens=2.4, cap=False)
    p.trunk_top = tp[-1]

    # ---------------- surface roots: the fins run on over the ground as long, thick, half-buried
    # roots that snake away and sink into the soil (never tapering to a claw); a side root or two
    def fdir(th):
        return np.array([math.sin(th), 0.0, math.cos(th)])   # 0 = south (toward the camera)

    p.root_ends = []
    for k, f in enumerate(fins):
        if abs(f['th']) > 2.25:           # behind the trunk: hidden anyway
            continue
        if abs(f['th']) < 0.45:           # straight at the camera a root foreshortens to a stub: skip
            continue
        d = fdir(f['th'])
        r_tip = r_at(0) + f['A']
        start = d * r_tip * 0.80
        front = max(0.0, math.cos(f['th']))
        L = rng.range(3.4, 5.6) * (1 - 0.35 * front)
        ang = math.atan2(d[2], d[0])
        pts = [start.copy()]
        cur = start.copy()
        n = 24
        bend = rng.range(-0.06, 0.06)
        for i in range(1, n + 1):
            ang += bend + rng.range(-0.10, 0.10)
            cur = cur + np.array([math.cos(ang), 0, math.sin(ang)]) * (L / n)
            pts.append(cur.copy())
        pts = np.array(pts)
        t = np.linspace(0, 1, len(pts))
        rr = (0.58 * (1 - t) ** 0.55 + 0.16) * (1 - 0.25 * front)
        dive = np.clip((t - 0.58) / 0.42, 0, 1) ** 1.3
        pts[:, 1] = rr * 0.42 - dive * rr * 1.5 + 0.06 * np.sin(t * 9 + k) * (1 - dive)
        p.tube(pts, rr, bark, R.PART_ROOT, cast=False, dens=2.2, cap=False)
        p.root_ends.append(pts[int(len(pts) * 0.8)])
        if L > 3.6 and rng() < 0.8:
            j = int(len(pts) * rng.range(0.30, 0.45))
            a2 = ang + rng.sign() * rng.range(0.7, 1.1)
            sp = [pts[j]]
            cur = pts[j].copy()
            for i in range(14):
                a2 += rng.range(-0.15, 0.15)
                cur = cur + np.array([math.cos(a2), 0, math.sin(a2)]) * 0.16
                sp.append(cur.copy())
            sp = np.array(sp)
            t2 = np.linspace(0, 1, len(sp))
            r2 = 0.24 * (1 - t2) ** 0.6 + 0.08
            sp[:, 1] = r2 * 0.35 - np.clip((t2 - 0.5) / 0.5, 0, 1) * r2 * 1.5
            p.tube(sp, r2, bark, R.PART_ROOT, cast=False, dens=2.2, cap=False)

    # ---------------- shimenawa at ~2.4 m, following the bark, a little lower at the front
    s_r = 2.4
    c_r = arch.point_on(tp, s_r / Ht)
    th = np.linspace(-math.pi, math.pi, 241)
    Rr = rfun(np.full_like(th, s_r), th, np.full_like(th, r_at(s_r / Ht))) - 0.02
    ring = np.stack([c_r[0] + np.sin(th) * Rr, c_r[1] - 0.12 * (1 + np.cos(th)) / 2,
                     c_r[2] + np.cos(th) * Rr], axis=-1)
    p.tube(ring, 0.22, rope, R.PART_DETAIL, cast=False, cap=False, dens=3.0)
    shide_at = [-0.95, -0.36, 0.24, 0.84]

    def draw_shide(pl, cv):
        # 紙垂: a paper strip folded down in four zigzag steps, 2 px wide, hung from the rope
        ringd = pl.D(ring)
        for a in shide_at:
            i = int(np.argmin(np.abs(th - a)))
            P0 = ringd[i]
            sx = int(round(cv.ax + P0[0] * PPM)) - 2
            sy = int(round(cv.ay + (P0[2] - P0[1]) * PPM)) + 4
            D = P0[1] + P0[2] + 0.4
            cells = []
            for k, (dx, y0, y1) in enumerate([(0, 0, 4), (2, 3, 7), (0, 6, 10), (2, 9, 13)]):
                for y in range(y0, y1):
                    for w in range(3):
                        cells.append((sx + dx + w, sy + y, 0.30 if w == 0 else (0.18 if w == 1 else 0.02)))
            for x, y, tone in cells:
                if 0 <= x < cv.W and 0 <= y < cv.H:
                    cv.depth[y, x] = D
                    cv.part[y, x] = R.PART_DETAIL
                    cv.mat[y, x] = paper
                    cv.mass[y, x] = -1
                    cv.n[y, x] = (-0.2 if tone > 0.25 else 0.25, 0.1, 0.95)
                    cv.wpos[y, x] = P0
                    cv.tone[y, x] = tone
    p.wood_details = [draw_shide]

    # ---------------- limbs (natural metres). The trunk forks at its top into three that climb
    # (left, right, back) and sends two big side limbs out lower down; all rise at 25-60 deg, curve
    # out, and taper into the masses they carry. None is a horizontal bar.
    top = tp[-1].copy()
    limbs = [
        # start: ('trunk', metres up) or ('top',), end point, base radius
        (('trunk', 4.8), (-8.6, 10.4, 1.2), 0.74),
        (('trunk', 5.5), (9.0, 11.2, -0.4), 0.72),
        (('top',), (-3.8, 14.8, 2.4), 0.78),
        (('top',), (4.0, 15.2, 1.6), 0.76),
        (('top',), (0.6, 16.6, -4.2), 0.70),
        (('trunk', 6.4), (0.2, 13.2, 6.0), 0.56),
        (('trunk', 6.0), (-6.4, 13.8, -4.8), 0.56),
        (('trunk', 6.2), (6.8, 14.2, -4.4), 0.56),
    ]
    paths = []
    for k, (st, end, r0) in enumerate(limbs):
        end = np.array(end) + np.array([rng.range(-0.6, 0.6), rng.range(-0.4, 0.4), rng.range(-0.6, 0.6)])
        if st[0] == 'top':
            start = top - np.array([0, 0.5, 0])
            r0 = r_at(1.0) * 0.62
            kc = 1.25
        else:
            start = arch.point_on(tp, min(1.0, st[1] / Ht))
            kc = 1.55
        path = arch.limb_to(start, end, rise=0.42, seed=seed * 17 + k, n=30)
        rr = arch.collar(np.linspace(r0, r0 * 0.32, len(path)) ** 1.0, k=kc, length=0.12)
        p.tube(path, rr, limb_bark, R.PART_LIMB, dens=2.4)
        paths.append((path, rr))

    # ---------------- masses: a designed crown (a hero tree is composed, not scattered): broad side
    # lobes at the base of the crown, a middle tier, an upper tier and the top, jittered per seed.
    env_c = np.array([0.0, 13.0, 0.0])
    env_r = np.array([12.4, 5.8, 9.0])
    env = p.envelope(env_c, env_r)
    layout = [
        # x, y, z, radius
        (-9.6, 9.2, 0.6, 2.6), (9.9, 9.8, 0.0, 2.6), (-7.0, 9.6, 3.0, 2.2), (7.4, 10.0, 2.6, 2.2),
        (-3.5, 10.6, 3.8, 2.1), (3.7, 11.0, 3.4, 2.1), (-0.2, 11.4, 5.0, 1.9),
        (-6.6, 12.0, -1.0, 3.0), (6.7, 12.4, -1.2, 3.0), (-2.6, 12.8, 3.6, 2.8), (2.9, 13.0, 3.2, 2.8),
        (0.0, 12.2, -4.2, 3.0), (-10.4, 11.6, -2.0, 2.4), (10.6, 12.0, -2.4, 2.4),
        (-4.8, 15.2, 0.6, 3.2), (4.7, 15.4, 0.2, 3.2), (0.0, 14.8, 4.4, 2.8), (-8.4, 14.0, -2.8, 2.6),
        (8.8, 14.2, -3.0, 2.6), (0.0, 15.6, -5.2, 3.0),
        (-1.8, 17.8, -1.0, 3.1), (2.8, 17.6, -1.6, 3.0), (0.2, 18.8, -3.6, 2.6), (-5.2, 17.0, -3.4, 2.4),
        (5.4, 17.0, -3.6, 2.4),
    ]
    centres = []
    for (x, y, z, rm) in layout:
        c = np.array([x, y, z]) + np.array([rng.range(-0.7, 0.7), rng.range(-0.4, 0.4), rng.range(-0.7, 0.7)])
        centres.append((c, rm * rng.range(0.92, 1.08), None))
    # small rim masses break the outline (a sprig sticking out here and there)
    for k in range(9):
        a = rng.range(0, 2 * math.pi)
        yv = rng.range(-0.15, 0.85)
        rad = math.sqrt(1 - yv * yv)
        c = env_c + np.array([math.cos(a) * rad, yv, math.sin(a) * rad]) * env_r * rng.range(0.90, 0.98)
        centres.append((c, rng.range(1.3, 1.8), 'rim'))
    # attach every mass that is not on a low limb to the nearest point of the limb system
    for c, rm, e_own in centres:
        if e_own is None:            # rim sprigs grow out of their neighbours: no branch of their own
            best = None
            for path, rr in paths:
                d = np.linalg.norm(path - c, axis=1)
                j = int(np.argmin(d + np.linspace(0, 1.5, len(path))[::-1] * 0.3))
                if best is None or d[j] < best[0]:
                    best = (d[j], path[j], rr[j])
            dist, a, ra = best
            if dist > 1.2:
                sp = arch.limb_to(a, c, rise=0.35, seed=int(abs(c[0] * 97 + c[2] * 31)) + seed, n=14)
                r_b = min(0.24, max(0.12, ra * 0.45))
                p.tube(sp, arch.collar(np.linspace(r_b, 0.08, len(sp)), k=1.3), limb_bark, R.PART_LIMB, dens=2.4)
        p.mass(c, np.array([rm, rm * 0.74, rm]), leaf, env if e_own in (None, 'rim') else e_own,
               cell_r=0.27 * rng.range(0.88, 1.15), lit_mat=new, fringe=0.55 if c[1] < 12.5 else 0.0)
    # the crown's dark inside, around the fork and along its belly
    deep = p.material('camphorDeep', PAL['camphorDeep'])
    p.interior(np.array([0.0, 12.0, -1.0]), np.array([6.5, 2.4, 4.5]), deep)
    p.leaf_opts.update(dict(w_env=0.55, inset=0.10, hl_p=0.40))
    # collision footprint: trunk and buttresses as drawn on the ground, px from the anchor
    poly = []
    for a in np.linspace(-math.pi, math.pi, 24, endpoint=False):
        rr = float(rfun(np.array([0.3]), np.array([a]), np.array([r_at(0.04)]))[0]) * 0.85
        poly.append([round(math.sin(a) * rr * PPM, 1), round(math.cos(a) * rr * p.kz * PPM, 1)])
    p.collision = poly
    return p
