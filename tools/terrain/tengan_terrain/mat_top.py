"""World-space painting of horizontal surfaces (tops), as indexed (ramp, tone).

Shapes first, then sparse glyphs (v0.1's lesson, knowledge/08 §2):
large calm patches with dithered borders -> grass clumps of a few pixels lit
on the upper left -> sparse tufts, flowers, pebbles where the masks ask for
them (edges, verges, wild stretches). Busy texture is kept away from where
characters stand (the clearing, road centres) so they read first."""
import numpy as np
from scipy import ndimage as ndi

from . import noise, stamps, rocks
from .geom import PPM, smoothstep
from .layout import TOP
from .palette import RAMP_ID as R, N_TONES


class TopPaint:
    def __init__(self, H, W):
        self.ramp = np.zeros((H, W), np.uint8)
        self.tone = np.zeros((H, W), np.float32)
        self.tx = np.zeros((H, W), np.float32)      # normal tilt toward +x (east)
        self.tz = np.zeros((H, W), np.float32)      # normal tilt toward +z (south)
        self.prio = np.full((H, W), -1e9, np.float32)
        self.flags = np.zeros((H, W), np.uint8)     # bit0 plant detail (tuft/flower), bit1 stone, bit2 wet


def edge_fields(world):
    """Distances (px) on each surface to its own edges.
    lip:  to the nearest edge where this surface drops away (south lip or side)
    slip: to the south-facing lip only (where a face hangs below)
    foot: to the nearest place where higher ground rises from this surface
    sfoot: to the foot of a south-facing face above (the visible cliff foot)"""
    h = np.nan_to_num(world.h, nan=world.void_h)
    th = 0.3
    H, W = h.shape
    up_side = np.zeros((H, W), bool)
    dn_side = np.zeros((H, W), bool)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = np.roll(h, (-dy, -dx), (0, 1))
        up_side |= (h - nb) >= th          # this cell is higher than a neighbour: a lip
        dn_side |= (nb - h) >= th          # a neighbour is higher: a foot
    slip = np.zeros((H, W), bool)
    slip[:-1] = (h[:-1] - h[1:]) >= th     # the face hangs south of this cell
    sfoot = np.zeros((H, W), bool)
    sfoot[1:] = (h[:-1] - h[1:]) >= th     # this cell is at the foot of a south-facing face

    def dist_same(seed_mask):
        d, (ii, jj) = ndi.distance_transform_edt(~seed_mask, return_indices=True)
        same = np.abs(h[ii, jj] - h) < 0.05
        return np.where(same, d, 1e4).astype(np.float32)
    return {'lip': dist_same(up_side), 'slip': dist_same(slip), 'foot': dist_same(dn_side), 'sfoot': dist_same(sfoot)}


def _dither_round(v, X, Y, amp=0.5, seed=977):
    """Round a continuous tone; where it sits between two steps, a small clustered
    noise (2-3 px blobs) decides, so borders break into irregular clusters rather
    than a checkerboard (knowledge/08 §2.1: no screen-wide ordered dither)."""
    b = noise.vnoise(X / 2.3, Y / 2.3, seed) - 0.5
    return np.floor(v + 0.5 + b * amp)


def _clumps(X, Y, dens, cw=10, ch=6, flat=0.0, seed=0, blade=0.5, dens_fn=None):
    """Grass clumps on a jittered grid: each pixel takes the front-most (lowest
    anchored) mound covering it. Returns offset tone (+1 tops, +2 tips,
    -1 gaps), tilt x/z and a 'tip' flag."""
    N = X.shape[0]
    Xi = np.floor(X).astype(np.int64)
    Yi = np.floor(Y).astype(np.int64)
    cx0 = np.floor_divide(Xi, cw)
    cy0 = np.floor_divide(Yi, ch)
    best_ay = np.full(N, -10 ** 9, np.int64)
    b_u = np.zeros(N, np.float32)
    b_rel = np.zeros(N, np.float32)
    b_bl = np.zeros(N, np.float32)
    b_h = np.zeros(N, np.uint32)
    for j in (0, 1):
        for i in (-1, 0, 1):
            qx = cx0 + i
            qy = cy0 + j
            hh = noise.hash2(qx, qy, seed)
            ay = qy * ch + ((hh >> np.uint32(12)) % np.uint32(ch)).astype(np.int64)
            ax = qx * cw + ((hh >> np.uint32(8)) % np.uint32(cw)).astype(np.int64) + (qy & 1) * (cw // 2)
            # a clump exists or not as a whole: density is read at its anchor
            dcell = dens if dens_fn is None else dens_fn(ax.astype(np.float32), ay.astype(np.float32))
            has = ((hh & np.uint32(255)).astype(np.float32) / 255.0) < dcell
            rx = 2 + ((hh >> np.uint32(16)) % np.uint32(4)).astype(np.int64)
            hg = np.maximum(1, 2 + ((hh >> np.uint32(19)) % np.uint32(3)).astype(np.int64) - int(flat))
            dx = Xi - ax
            u = dx / (rx + 0.5)
            inside = has & (np.abs(dx) <= rx) & (Yi <= ay) & (ay > best_ay)
            bt = (noise.hash2(Xi, ay, seed + 3) & np.uint32(15)).astype(np.int64)
            bl = np.where(bt < 2, 2, np.where(bt < 5, 1, 0))
            bl = (bl * blade).round().astype(np.int64)
            top = ay - np.round(hg * np.sqrt(np.clip(1 - u * u, 0, 1))).astype(np.int64) - bl
            cov = inside & (Yi >= top)
            best_ay = np.where(cov, ay, best_ay)
            b_u = np.where(cov, u, b_u)
            b_rel = np.where(cov, Yi - top, b_rel)
            b_bl = np.where(cov, bl, b_bl)
            b_h = np.where(cov, hh, b_h)
    covered = best_ay > -10 ** 9
    off = np.where(covered, 0.0, -1.0).astype(np.float32)
    tip = covered & (b_rel < b_bl)
    topband = covered & (b_rel >= b_bl) & (b_rel <= b_bl + 1)
    off = np.where(topband & (b_u < 0.35), 1.0, off)
    off = np.where(tip, np.where((b_rel == 0) & (b_u < 0.2), 2.0, 1.0), off)
    foot = covered & (Yi == best_ay) & (b_rel > 1) & (((b_h >> np.uint32(22)) & np.uint32(1)) == 1)
    off = np.where(foot, -1.0, off)
    tx = np.where(covered, b_u * 0.45, 0.0).astype(np.float32)
    tz = np.where(covered, np.where(b_rel <= 1, -0.35, np.where(Yi == best_ay, 0.3, 0.0)), 0.05).astype(np.float32)
    return off, tx, tz, tip


def paint_grass(P, idx, X, Y, calm, wild, lipd, footd, seed):
    """Meadow (calm 0) to lawn (calm 1).

    Big shapes first: stretches of damp-cool, olive and sun-bleached grass
    (2-8 m, borders broken into clusters); inside them a few value patches;
    then grass clumps that gather in masses with open, calm ground between
    (never an even carpet); sparse lit blades only on the clumps."""
    hf = noise.fbm(X / 300.0, Y / 300.0, seed + 1, 3) * 0.7 + noise.fbm(X / 90.0, Y / 90.0, seed + 2, 2) * 0.3
    damp = smoothstep(16.0, 0.0, footd)          # at the foot of walls: damp, cool
    hv = hf - damp * 0.3 + (noise.vnoise(X / 2.6, Y / 2.6, seed + 3) - 0.5) * 0.05
    rp = np.where(hv < 0.42, R['grass_cool'], np.where(hv < 0.67, R['grass'], R['grass_dry'])).astype(np.uint8)
    lawn = calm > 0.5
    rp = np.where(lawn & (rp == R['grass']), R['lawn'], rp)
    # value patches (2-6 m), dithered into clusters at their borders
    pv = noise.fbm(X / 80.0, Y / 80.0, seed + 5, 3)
    base = 3.6 + (pv - 0.5) * 1.8 * (1.0 - 0.3 * calm) - damp * 0.5
    tb = _dither_round(base, X, Y, 0.4, seed + 6)
    # where clumps gather: masses ~1-3 m across with open ground between them
    extra = (wild - 0.5) * 0.35 - calm * 0.18

    def dens_fn(ax, ay):
        return np.clip((noise.fbm(ax / 34.0, ay / 34.0, seed + 8, 3) + extra - 0.40) * 2.6, 0.0, 0.92)
    dens = dens_fn(X, Y)
    off, tx, tz, tip = _clumps(X, Y, dens, cw=10, ch=6, seed=seed + 11, blade=0.5 + 0.6 * wild - 0.3 * calm, dens_fn=dens_fn)
    # in the open between masses there is no 'gap' shading: flat ground
    open_ground = dens < 0.08
    off = np.where(open_ground, 0.0, off)
    # lawn: half the gaps are not shaded, the highlight tips rarer -> calmer
    gap = off < 0
    soft = gap & (noise.vnoise(X / 1.7 + 3, Y / 1.7, seed + 12) < 0.55 * calm + 0.1)
    off = np.where(soft, 0.0, off)
    off = np.where((off > 1) & lawn, 1.0, off)
    tone = tb + off
    # sparse lit blades on the clumps of light patches
    r = noise.hash01(X.astype(np.int64), (Y.astype(np.int64)) // 2, seed + 9)
    tone = np.where((tb >= 3) & (off > 0) & (r > 0.9 + 0.06 * calm), tone + 1, tone)
    P.ramp.flat[idx] = rp
    P.tone.flat[idx] = np.clip(tone, 0, N_TONES - 1)
    P.tx.flat[idx] = tx * (1 - open_ground)
    P.tz.flat[idx] = tz * (1 - open_ground)


def paint_moss(P, idx, X, Y, seed):
    """Moss: flat damp ground with cushion clusters. Cushions are irregular
    (noise-bent distances, three sizes picked by a slow field), lit on a
    thin upper-left crescent, a dark crevice only where two cushions press
    together; between clusters the moss is flat and calm."""
    sz = noise.fbm(X / 55.0, Y / 55.0, seed + 3, 2)
    cw = np.where(sz < 0.4, 5.0, np.where(sz < 0.62, 8.0, 12.0))
    chh = cw * 0.68
    # bend the lattice so cells are not a visible grid
    wx, wy = noise.warp(X, Y, 18.0, 4.0, seed + 4, 2)
    gx = wx / cw
    gy = wy / chh
    cx = np.floor(gx)
    cy = np.floor(gy)
    d1 = np.full(X.shape, 1e9, np.float32)
    d2 = np.full(X.shape, 1e9, np.float32)
    bx = np.zeros(X.shape, np.float32)
    by = np.zeros(X.shape, np.float32)
    bh = np.zeros(X.shape, np.uint32)
    for j in (-1, 0, 1):
        for i in (-1, 0, 1):
            qx = (cx + i).astype(np.int64)
            qy = (cy + j).astype(np.int64)
            hh = noise.hash2(qx * 3 + (cw > 6).astype(np.int64), qy, seed + 17)
            px = qx + 0.1 + (hh & np.uint32(255)).astype(np.float32) / 255.0 * 0.8
            py = qy + 0.1 + ((hh >> np.uint32(8)) & np.uint32(255)).astype(np.float32) / 255.0 * 0.8
            ex = (gx - px) * cw / 1.2
            ey = (gy - py) * chh
            dd = ex * ex + ey * ey
            closer = dd < d1
            d2 = np.where(closer, d1, np.minimum(d2, dd))
            d1 = np.where(closer, dd, d1)
            bx = np.where(closer, ex, bx)
            by = np.where(closer, ey, by)
            bh = np.where(closer, hh, bh)
    crev = np.sqrt(d2) - np.sqrt(d1)
    # clusters: cushions only where the cluster field is high; many cells skipped
    clus = noise.fbm(X / 26.0 + 9.0, Y / 26.0, seed + 5, 3)
    alive = (clus > 0.47) & (((bh >> np.uint32(18)) & np.uint32(3)) != 0)
    pv = noise.fbm(X / 60.0, Y / 60.0, seed + 6, 2)
    base = _dither_round(2.7 + (pv - 0.5) * 1.4, X, Y, 0.6, seed + 7)
    r_cell = np.sqrt(d1) / (cw * 0.55)
    side = (bx + by * 1.3) / (cw * 0.5)
    off = np.zeros(X.shape, np.float32)
    off = np.where(alive & (side < -0.55) & (r_cell > 0.35), 1.0, off)         # lit crescent
    off = np.where(alive & (side > 0.7), -1.0, off)                             # shaded flank
    press = alive & (crev < 0.9) & (((bh >> np.uint32(9)) & np.uint32(3)) == 0)
    off = np.where(press, -1.0, off)
    r = noise.hash01(X.astype(np.int64), Y.astype(np.int64), seed + 23)
    off = np.where(alive & (r > 0.994), 2.0, off)                              # fruiting specks
    P.ramp.flat[idx] = R['moss']
    P.tone.flat[idx] = np.clip(base + off, 0, N_TONES - 1)
    P.tx.flat[idx] = np.where(alive, np.clip(bx / cw * 0.6, -0.4, 0.4), 0)
    P.tz.flat[idx] = np.where(alive, np.clip(by / chh * 0.6, -0.4, 0.4), 0)


def paint_forest(P, idx, X, Y, seed):
    """Forest floor (mostly under tree shade in the game).

    One crumbly texture (small low mounds: humus, moss pads, leaf mould),
    tinted by a slow damp/dry field: damp hollows lean to moss green, drier
    stretches to brown leaf litter, the two meeting in clusters, never in
    hard-edged blobs. A few loose leaves and twigs on top."""
    damp = noise.fbm(X / 140.0, Y / 140.0, seed + 1, 3) + (noise.vnoise(X / 2.4, Y / 2.4, seed + 2) - 0.5) * 0.12
    pv = noise.fbm(X / 50.0, Y / 50.0, seed + 3, 2)
    def dens_fn(ax, ay):      # masses of humus mounds with open soil between them
        return np.clip((noise.fbm(ax / 28.0, ay / 28.0, seed + 9, 3) - 0.38) * 2.4, 0.0, 0.9)
    off, tx, tz, tip = _clumps(X, Y, 0.0, cw=7, ch=4, seed=seed + 4, blade=0.0, dens_fn=dens_fn)
    open_ground = dens_fn(X, Y) < 0.1
    off = np.where(open_ground, 0.0, np.clip(off, -1, 1))
    green = damp > 0.56
    base = np.where(green, 2.6, 2.9) + (pv - 0.5) * 1.2
    tone = _dither_round(base, X, Y, 0.4, seed + 5) + off
    rp = np.where(green, R['moss'], R['forest']).astype(np.uint8)
    # leaf litter in drifts on the drier ground: flecks close to the soil's value
    drift = noise.fbm(X / 30.0 + 21, Y / 30.0, seed + 6, 3)
    lh = noise.hash01(np.floor(X / 2).astype(np.int64), Y.astype(np.int64), seed + 7)
    leaf = (~green) & (drift > 0.5) & (lh < (drift - 0.5) * 1.3) & (off >= 0)
    rp = np.where(leaf, R['litter'], rp)
    tone = np.where(leaf, 2 + np.floor(noise.hash01(np.floor(X / 2).astype(np.int64), Y.astype(np.int64), seed + 8) * 2.5), tone)
    P.ramp.flat[idx] = rp
    P.tone.flat[idx] = np.clip(tone, 0, N_TONES - 1)
    P.tx.flat[idx] = tx * 0.7
    P.tz.flat[idx] = tz * 0.7


def paint_dirt(P, idx, X, Y, u, along, side, hw, wear, seed, ramp='dirt'):
    """The old road: trodden earth in three tones, two worn ruts with a crown,
    a darker line where the verge grass leans over the edge."""
    pv = noise.fbm(X / 26.0, Y / 26.0, seed + 1, 3)
    fine = noise.fbm(X / 4.0, Y / 4.0, seed + 2, 2)
    base = 3.4 + (pv - 0.5) * 1.5 + (fine - 0.5) * 0.7
    # ruts: two bands about 40% out from the centre line, wandering a little
    off = side * u
    wob = (noise.fbm(along / 60.0, side * 3.0 + seed, seed + 4, 2) - 0.5) * 0.16
    for c in (-0.44, 0.44):
        band = np.exp(-((off - c - wob) / 0.11) ** 2)
        base = base - band * 0.9 * wear
    base = base + np.exp(-(off / 0.18) ** 2) * 0.35 * wear     # the crown between the ruts
    # the edge: a darker line under the leaning grass, a little lighter dust just inside
    base = base - smoothstep(0.86, 0.98, u) * 1.1 + smoothstep(0.62, 0.8, u) * smoothstep(0.92, 0.8, u) * 0.35
    tone = _dither_round(base, X, Y, 0.6)
    P.ramp.flat[idx] = R[ramp]
    P.tone.flat[idx] = np.clip(tone, 0, N_TONES - 1)
    P.tx.flat[idx] = (fine - 0.5) * 0.25
    P.tz.flat[idx] = 0.0


def paint_earth(P, idx, X, Y, seed):
    pv = noise.fbm(X / 30.0, Y / 30.0, seed + 1, 3)
    fine = noise.fbm(X / 5.0, Y / 5.0, seed + 2, 2)
    tone = _dither_round(3.7 + (pv - 0.5) * 1.3 + (fine - 0.5) * 0.6, X, Y, 0.6)
    P.ramp.flat[idx] = R['earth']
    P.tone.flat[idx] = np.clip(tone, 0, N_TONES - 1)
    P.tx.flat[idx] = (fine - 0.5) * 0.2


def paint_atlas_top(P, idx, X, Y, atlas, ramp_a, ramp_b, seed, scale=1.0, base_tone=2.6, spread=2.6, gap_tone=0.6,
                    moss_k=0.0, lichen_k=0.0, rim_k=1.0):
    """Plates/stones from a photoscan atlas laid flat (rock tops, gravel, scree).
    scale > 1 enlarges the plates; rim_k scales the bevel contrast."""
    ah, aw = atlas['plate'].shape
    ax = (np.floor(X / scale).astype(np.int64)) % aw
    ay = (np.floor(Y / scale).astype(np.int64)) % ah
    plate = atlas['plate'][ay, ax]
    base = atlas['base'][ay, ax]
    rim = atlas['rim'][ay, ax]
    # vary each repetition of the tile so the period never reads
    rep = noise.hash01(np.floor_divide(np.floor(X / scale).astype(np.int64), aw) * 131 + plate,
                       np.floor_divide(np.floor(Y / scale).astype(np.int64), ah) * 71 + plate, seed + 3)
    t = base_tone + (base - 0.5) * spread + (rep - 0.5) * 0.9
    t = t + rim_k * (np.where(rim == 2, 1.0, 0) + np.where(rim == 1, 0.4, 0) + np.where(rim == -1, -0.8, 0))
    t = np.where(plate == 0, gap_tone, t)
    rp = np.where(rep < 0.5, ramp_a, ramp_b).astype(np.uint8)
    if moss_k > 0:
        mz = noise.fbm(X / 30.0, Y / 30.0, seed + 5, 2)
        mm = ((plate == 0) & (mz > 0.5 - moss_k * 0.3)) | ((mz > 1.0 - moss_k * 0.35) & (rim != -2))
        rp = np.where(mm, R['moss'], rp)
        t = np.where(mm, np.clip(t - 0.5, 1, 5), t)
    if lichen_k > 0:
        # lichen grows in rosettes and patches on the exposed tops, not as scattered dots
        lz = noise.fbm(X / 11.0 + 5, Y / 11.0, seed + 7, 2)
        lr = noise.vnoise(X / 1.6, Y / 1.6, seed + 8)
        lm = (plate > 0) & (rim >= 0) & (lz > 0.68 - 0.05 * lichen_k) & (lr > 0.35)
        rp = np.where(lm, R['lichen'], rp)
        t = np.where(lm, np.where(lz > 0.74, 4, 3), t)
    P.ramp.flat[idx] = rp
    P.tone.flat[idx] = np.clip(np.round(t), 0, N_TONES - 1)
    P.tx.flat[idx] = atlas['nx'][ay, ax] * 0.6 * rim_k
    P.tz.flat[idx] = -atlas['ny'][ay, ax] * 0.6 * rim_k
    P.flags.flat[idx] |= 2


def paint_tread(P, world, idx, X, Y, seed):
    """Stone treads: 1-3 slabs per step, joints, the nosing catching the light,
    a crease at the back, worn lighter in the middle, moss in joints and corners."""
    k = world.stair_k.flat[idx].astype(np.int64)
    u = world.stair_u.flat[idx]
    v = world.stair_v.flat[idx]
    sid = world.sid.flat[idx].astype(np.int64)
    hk = noise.hash2(k, sid, seed + 1)
    off = (hk & np.uint32(31)).astype(np.float32)
    seg_w = 15.0 + ((hk >> np.uint32(5)) & np.uint32(15)).astype(np.float32)
    seg = np.floor((u + off) / seg_w).astype(np.int64)
    fu = (u + off) - seg * seg_w
    hs = noise.hash2(seg, k * 7 + sid, seed + 2)
    stone_tone = 3.0 + ((hs & np.uint32(255)).astype(np.float32) / 255.0) * 1.0
    rp = np.where((hs >> np.uint32(9)) & np.uint32(1), R['stone_warm'], R['stone']).astype(np.uint8)
    fine = noise.fbm(X / 5.0, Y / 5.0, seed + 3, 2)
    t = stone_tone + (fine - 0.5) * 0.9
    tread_d = np.maximum(world.stair_v.max(), 1)
    t = np.where(v < 1.2, t + 0.8, np.where(v < 2.2, t + 0.3, t))          # nosing
    t = np.where(v > 6.4, t - 0.7, t)                                        # crease at the back
    t = np.where(fu < 1.0, t - 1.8, np.where(fu < 2.0, t + 0.4, t))           # joint, then its lit lip
    w = np.abs(u - np.median(u)) if len(u) else u
    t = t + smoothstep(18.0, 4.0, np.abs(u - 22.0)) * 0.3                    # worn middle
    # chipped corners: a pixel or two of the nosing missing at random
    chip = (v < 1.2) & (noise.hash01(np.floor(u / 3).astype(np.int64), k + sid * 13, seed + 4) < 0.18)
    t = np.where(chip, t - 1.6, t)
    mz = noise.fbm(X / 14.0, Y / 14.0, seed + 5, 2)
    mossy = ((fu < 1.6) | (v > 6.0) | (u < 3.0) | (u > 41.0)) & (mz > 0.48) & (noise.hash01(X.astype(np.int64), Y.astype(np.int64), seed + 6) < 0.6)
    rp = np.where(mossy, R['moss'], rp)
    t = np.where(mossy, 2.0 + (mz > 0.6), t)
    P.ramp.flat[idx] = rp
    P.tone.flat[idx] = np.clip(np.round(t), 0, N_TONES - 1)
    P.tx.flat[idx] = 0.0
    P.tz.flat[idx] = np.where(v < 1.5, 0.35, 0.0)
    P.flags.flat[idx] |= 2


def paint_cheek(P, world, idx, X, Y, seed):
    """Tops of the cheek stones: rough blocks, rounded and lit on the upper left."""
    k = world.stair_k.flat[idx].astype(np.int64)
    u = world.stair_u.flat[idx]
    v = world.stair_v.flat[idx]
    hb = noise.hash2(k, np.sign(u).astype(np.int64) + world.sid.flat[idx].astype(np.int64) * 3, seed + 1)
    t = 2.9 + ((hb & np.uint32(255)).astype(np.float32) / 255.0) * 0.8
    fine = noise.fbm(X / 4.0, Y / 4.0, seed + 2, 2)
    t = t + (fine - 0.5) * 0.9 + np.where(v < 1.5, 0.6, 0.0)
    mz = noise.fbm(X / 10.0, Y / 10.0, seed + 3, 2)
    mossy = mz > 0.56
    rp = np.where(mossy, R['moss'], np.where((hb >> np.uint32(8)) & np.uint32(1), R['stone'], R['stone_warm'])).astype(np.uint8)
    t = np.where(mossy, 2.5 + (fine > 0.5), t)
    P.ramp.flat[idx] = rp
    P.tone.flat[idx] = np.clip(np.round(t), 0, N_TONES - 1)
    P.tz.flat[idx] = np.where(v < 1.5, 0.3, 0.0)
    P.flags.flat[idx] |= 2


def paint_water(P, world, idx, X, Y, seed):
    """A still spring pool: darker with depth, a darker band in the bank's
    reflection along the north shore, a few slow glints."""
    dep = world.wdepth.flat[idx]
    fine = noise.fbm(X / 18.0, Y / 6.0, seed + 1, 2)
    t = 4.6 - np.clip(dep / 0.7, 0, 1) * 2.4 + (fine - 0.5) * 0.6
    tone = _dither_round(t, X, Y, 0.7)
    # glints: short horizontal strokes
    g = noise.hash01(np.floor(X / 4).astype(np.int64), Y.astype(np.int64), seed + 2) > 0.985
    tone = np.where(g, 6.0, tone)
    P.ramp.flat[idx] = R['water']
    P.tone.flat[idx] = np.clip(tone, 0, N_TONES - 1)
    P.flags.flat[idx] |= 4


def paint_tops(world, atlases, seed=0):
    H, W = world.H, world.W
    P = TopPaint(H, W)
    E = edge_fields(world)
    world.edges = E
    Xg, Yg = world.frame.grid()
    top = world.top
    calm_map = {TOP['lawn']: 1.0, TOP['meadow']: 0.0}
    # ---- grass (meadow + lawn) -------------------------------------------------
    for tm in (TOP['meadow'], TOP['lawn']):
        m = top == tm
        if not m.any():
            continue
        idx = np.flatnonzero(m)
        calm = np.full(len(idx), calm_map[tm], np.float32)
        paint_grass(P, idx, Xg.flat[idx], Yg.flat[idx], calm, world.wild.flat[idx], E['lip'].flat[idx], E['foot'].flat[idx], seed + 100)
    for tm, fn in ((TOP['moss'], paint_moss),):
        idx = np.flatnonzero(top == tm)
        if len(idx):
            fn(P, idx, Xg.flat[idx], Yg.flat[idx], seed + 200)
    idx = np.flatnonzero(top == TOP['forest'])
    if len(idx):
        paint_forest(P, idx, Xg.flat[idx], Yg.flat[idx], seed + 300)
    # ---- roads ----------------------------------------------------------------
    for tm, rname in ((TOP['dirt'], 'dirt'),):
        idx = np.flatnonzero(top == tm)
        if len(idx):
            u = np.clip(world.road_d.flat[idx] / np.maximum(world.road_hw.flat[idx], 1), 0, 1)
            paint_dirt(P, idx, Xg.flat[idx], Yg.flat[idx], u, world.road_along.flat[idx], world.road_side.flat[idx],
                       world.road_hw.flat[idx], world.road_wear.flat[idx], seed + 400, rname)
    idx = np.flatnonzero((top == TOP['earth']) | (top == TOP['wetbank']))
    if len(idx):
        paint_earth(P, idx, Xg.flat[idx], Yg.flat[idx], seed + 500)
        wet = top.flat[idx] == TOP['wetbank']
        P.ramp.flat[idx[wet]] = R['wetsoil']
        P.tone.flat[idx[wet]] = np.clip(P.tone.flat[idx[wet]] - 0.5, 0, 7)
    # ---- stone ----------------------------------------------------------------
    idx = np.flatnonzero(top == TOP['rock'])
    if len(idx):
        paint_atlas_top(P, idx, Xg.flat[idx], Yg.flat[idx], atlases['cliff'], R['rock'], R['rock_warm'], seed + 600,
                        scale=2.2, base_tone=3.6, spread=1.8, gap_tone=1.4, moss_k=0.45, lichen_k=1.0, rim_k=0.75)
    idx = np.flatnonzero(top == TOP['scree'])
    if len(idx):
        paint_atlas_top(P, idx, Xg.flat[idx], Yg.flat[idx], atlases['pebbles'], R['rock'], R['rock_warm'], seed + 650,
                        scale=1.3, base_tone=3.2, spread=2.0, gap_tone=1.2, moss_k=0.2, rim_k=0.8)
    idx = np.flatnonzero(top == TOP['gravel'])
    if len(idx):
        paint_atlas_top(P, idx, Xg.flat[idx], Yg.flat[idx], atlases['pebbles'], R['gravel'], R['gravel'], seed + 660,
                        scale=0.6, base_tone=3.2, spread=2.0, gap_tone=1.5)
    idx = np.flatnonzero(top == TOP['tread'])
    if len(idx):
        paint_tread(P, world, idx, Xg.flat[idx], Yg.flat[idx], seed + 700)
    idx = np.flatnonzero(top == TOP['cheek'])
    if len(idx):
        paint_cheek(P, world, idx, Xg.flat[idx], Yg.flat[idx], seed + 750)
    idx = np.flatnonzero(top == TOP['water'])
    if len(idx):
        paint_water(P, world, idx, Xg.flat[idx], Yg.flat[idx], seed + 800)
    _verges(P, world, E, Xg, Yg, seed + 900)
    _details(P, world, E, Xg, Yg, seed + 1000)
    return P


def _verges(P, world, E, Xg, Yg, seed):
    """Road verges: grass tongues bite into the dirt edge (in the neighbouring
    grass colour); just outside, in patches, the grass is trodden short (flat,
    no clumps, a step lighter) with bare specks. Never a continuous band."""
    top = world.top
    u = world.road_d / np.maximum(world.road_hw, 1)
    near = (u < 1.7) & (world.road_hw > 0)
    tongue = noise.fbm(Xg / 7.0, Yg / 7.0, seed + 1, 2)
    grassy = np.isin(top, [TOP['meadow'], TOP['lawn']])
    dirt = top == TOP['dirt']
    to_grass = dirt & near & (u > 0.86 + (0.5 - tongue) * 0.32)
    # borrow the ramp of the grass just outside: grow the grass ramp inward
    gr = np.where(grassy, P.ramp, 0).astype(np.uint8)
    for _ in range(6):
        gr = np.where(gr == 0, np.maximum.reduce([np.roll(gr, 1, 0), np.roll(gr, -1, 0), np.roll(gr, 1, 1), np.roll(gr, -1, 1)]), gr)
    P.ramp[to_grass] = np.where(gr[to_grass] > 0, gr[to_grass], R['grass'])
    P.tone[to_grass] = 3 + (tongue[to_grass] > 0.58)
    patch = noise.fbm(Xg / 22.0, Yg / 22.0, seed + 2, 2) > 0.48
    verge = grassy & near & (u < 1.3 + (tongue - 0.5) * 0.4) & patch
    P.tone[verge] = np.clip(np.round(P.tone[verge] * 0.4 + 2.1), 2, 4)
    P.tx[verge] = 0
    P.tz[verge] = 0
    speck = verge & (noise.hash01(Xg.astype(np.int64), Yg.astype(np.int64), seed + 3) < 0.05)
    P.ramp[speck] = R['dirt']
    P.tone[speck] = 3
    P.flags[near & (u < 1.15)] |= 8     # no tufts on the trodden edge


def _details(P, world, E, Xg, Yg, seed):
    """Glyph passes: tufts, weeds and flowers on grass; pebbles on earth;
    rubble at cliff feet; leaves and twigs under the great tree."""
    H, W = world.H, world.W
    top = world.top
    grass = np.isin(top, [TOP['meadow'], TOP['lawn']]) & ((P.flags & 8) == 0)
    wild = world.wild
    lip = E['lip']
    foot = E['foot']
    lawn = top == TOP['lawn']
    # tuft density: wild stretches and along lips and feet; sparse in the lawn
    dens = (0.10 + 0.55 * wild) * np.where(lawn, 0.35, 1.0)
    dens = dens + smoothstep(26.0, 2.0, lip) * 0.45 + smoothstep(22.0, 2.0, foot) * 0.5
    dens = np.clip(dens * (0.6 + 0.8 * noise.fbm(Xg / 90.0, Yg / 90.0, seed + 2, 2)), 0, 1).astype(np.float32)
    ys, xs, hh = stamps.jitter_points(grass, 7, 6, dens, seed + 3)
    which = ((hh >> np.uint32(3)) % np.uint32(len(stamps.TUFTS))).astype(np.int64)
    stamps.stamp(P.prio, P.tone, P.ramp, ys, xs, stamps.TUFTS, which, allow=grass)
    P.flags.ravel()[ys * W + xs] |= 1
    # small weeds in the lawn (calmer than tufts)
    ys, xs, hh = stamps.jitter_points(grass & lawn, 13, 9, np.float32(0.18), seed + 5)
    which = ((hh >> np.uint32(3)) % np.uint32(len(stamps.WEEDS))).astype(np.int64)
    stamps.stamp(P.prio, P.tone, P.ramp, ys, xs, stamps.WEEDS, which, allow=grass)
    # wildflowers: clustered in patches of the meadow
    fz = noise.fbm(Xg / 70.0 + 40, Yg / 70.0, seed + 7, 3)
    spot = noise.fbm(Xg / 14.0 - 7, Yg / 14.0, seed + 8, 2)
    fdens = np.clip((fz - 0.58) * 3.0, 0, 1) * np.clip((spot - 0.55) * 5.0, 0, 1) * np.where(lawn, 0.3, 1.0) * (0.4 + wild)
    meadow_ok = grass & (fdens > 0)
    ys, xs, hh = stamps.jitter_points(meadow_ok, 4, 3, (fdens * 0.8).astype(np.float32), seed + 9)
    kind = (hh >> np.uint32(5)) % np.uint32(16)
    # the colour follows the patch, not each flower: patches of one kind with a few others
    patch_kind = (noise.fbm(xs / 120.0, ys / 120.0, seed + 11, 2) * 4).astype(np.int64)
    fr = np.array([R['flower_w'], R['flower_y'], R['flower_v'], R['flower_p']], np.int16)
    ramp_ids = np.where(kind < 11, fr[np.clip(patch_kind, 0, 3)], fr[(kind % 4).astype(np.int64)]).astype(np.int16)
    which = ((hh >> np.uint32(9)) % np.uint32(len(stamps.FLOWERS))).astype(np.int64)
    stamps.stamp(P.prio, P.tone, P.ramp, ys, xs, stamps.FLOWERS, which, ramp_ids=ramp_ids, allow=grass)
    P.flags.ravel()[ys * W + xs] |= 1
    # pebbles on earth and dirt, more toward the edges and in the ruts
    ground = np.isin(top, [TOP['dirt'], TOP['earth'], TOP['wetbank']])
    u = world.road_d / np.maximum(world.road_hw, 1)
    pd = np.where(top == TOP['dirt'], 0.10 + 0.35 * smoothstep(0.55, 0.95, u), 0.12).astype(np.float32)
    ys, xs, hh = stamps.jitter_points(ground, 7, 5, pd, seed + 13)
    which = ((hh >> np.uint32(3)) % np.uint32(len(stamps.PEBBLES))).astype(np.int64)
    stamps.stamp(P.prio, P.tone, P.ramp, ys, xs, stamps.PEBBLES, which, allow=ground)
    # rock fall at the foot of every cliff: stones on the lower ground, densest at the foot
    rub = (E['sfoot'] < 28) & ~np.isin(top, [TOP['water'], TOP['tread'], TOP['cheek'], TOP['void']])
    rd = (smoothstep(28.0, 1.0, E['sfoot']) * 0.55).astype(np.float32)
    ys, xs, hh = stamps.jitter_points(rub, 6, 5, rd, seed + 15)
    which = ((hh >> np.uint32(3)) % np.uint32(len(stamps.PEBBLES))).astype(np.int64)
    rid = np.where((hh >> np.uint32(7)) & np.uint32(1), R['rock'], R['rock_warm']).astype(np.int16)
    # rubble stones are drawn in rock colours: give them an absolute base by re-ramping
    before_r = P.ramp.copy()
    t = stamps.stamp(P.prio, P.tone, P.ramp, ys, xs, stamps.PEBBLES, which, allow=rub)
    newly = t & (before_r != R['rock'])
    # stone pixels: rock ramp, tone around 3-5 from the glyph offset
    P.ramp[newly] = R['rock_warm']
    P.tone[newly] = np.clip(P.tone[newly] - P.tone[newly] + 3.6 + (P.tone[newly] - np.round(P.tone[newly])), 1, 6)
    P.flags[newly] |= 2
