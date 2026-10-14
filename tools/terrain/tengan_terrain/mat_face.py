"""Screen-space painting of the vertical faces the oblique view shows.

A face pixel knows its column x, its absolute height v (px), how far below
the face top it is (fk, 1 = top row) and the face's total height (fd).
Textures are addressed by (x, v), so strata stay level across the whole
cliff and a face of any height samples the same rock. The face style comes
from the surface above the drop (layout.FACE)."""
import numpy as np
from scipy import ndimage as ndi

from . import noise, stamps
from .geom import PPM, smoothstep
from .layout import FACE, TOP
from .painter import KIND_TOP, KIND_FACE, KIND_SIDE
from .palette import RAMP_ID as R, N_TONES

VEG_TOPS = (TOP['meadow'], TOP['lawn'], TOP['moss'], TOP['forest'])


class ScreenPaint:
    def __init__(self, Hs, W):
        self.ramp = np.zeros((Hs, W), np.uint8)
        self.tone = np.zeros((Hs, W), np.float32)
        self.n = np.zeros((Hs, W, 3), np.float32)       # world normal (x east, y up, z south)
        self.n[..., 1] = 1.0
        self.mat = np.zeros((Hs, W), np.uint8)          # top material id, or 32 + face style
        self.flags = np.zeros((Hs, W), np.uint8)
        self.prio = np.full((Hs, W), -1e9, np.float32)


def face_normals(world, sigma_m=0.9):
    """Horizontal facing of the terrain edges: -grad(h), blurred, per world cell."""
    h = np.nan_to_num(world.h, nan=world.void_h).astype(np.float32)
    hb = ndi.gaussian_filter(h, sigma_m * PPM)
    gz, gx = np.gradient(hb)
    nx, nz = -gx, -gz
    l = np.hypot(nx, nz)
    ok = l > 1e-6
    nx = np.where(ok, nx / np.maximum(l, 1e-6), 0.0)
    nz = np.where(ok, nz / np.maximum(l, 1e-6), 1.0)
    # faces we can see face south-ish; keep a minimum south component so a
    # face never turns its back on the camera
    nz = np.maximum(nz, 0.25)
    l = np.hypot(nx, nz)
    return (nx / l).astype(np.float32), (nz / l).astype(np.float32)


def _overhang_len(x, seed, upper_top, wildv):
    """Sod hanging over a cliff top: clumps a few px wide, 0-5 px long."""
    c = np.floor(x / 6.0)
    f = x / 6.0 - c
    a = noise.hash01(c.astype(np.int64), np.zeros_like(c, np.int64), seed)
    b = noise.hash01((c + 1).astype(np.int64), np.zeros_like(c, np.int64), seed)
    s = f * f * (3 - 2 * f)
    n = a + (b - a) * s
    j = noise.hash01(x.astype(np.int64), np.ones_like(x, np.int64), seed + 1)
    L = np.round(n * (3.2 + 2.0 * wildv) - 0.4 + (j < 0.2)).astype(np.int64)
    L = np.where(upper_top == TOP['lawn'], np.minimum(L, 3), L)
    L = np.where(upper_top == TOP['moss'], np.minimum(L, 2), L)
    return np.clip(L, 0, 6)


def paint_faces(S, world, top, atlases, seed=0):
    Hs, W = S.kind.shape
    SP = ScreenPaint(Hs, W)
    x0px = int(round(world.frame.x0 * PPM))
    # ---- tops: gather from the world-space paint
    tm = S.kind == KIND_TOP
    src = S.src[tm]
    SP.ramp[tm] = top.ramp.ravel()[src]
    SP.tone[tm] = top.tone.ravel()[src]
    tx = top.tx.ravel()[src]
    tz = top.tz.ravel()[src]
    nn = np.stack([tx, np.ones_like(tx), tz], -1)
    SP.n[tm] = nn / np.linalg.norm(nn, axis=-1, keepdims=True)
    SP.mat[tm] = world.top.ravel()[src]
    SP.flags[tm] = top.flags.ravel()[src]
    # ---- faces
    fm = S.kind == KIND_FACE
    fy, fx = np.nonzero(fm)
    style = S.face_style[fm]
    up = S.src[fm]
    fk = S.fk[fm].astype(np.float32)
    fd = S.fd[fm].astype(np.float32)
    v = S.hpx[fm]
    X = (fx + x0px).astype(np.float32)
    nhx_w, nhz_w = face_normals(world)
    nhx = nhx_w.ravel()[up]
    nhz = nhz_w.ravel()[up]
    upper_top = world.top.ravel()[up]
    sid_up = world.sid.ravel()[up].astype(np.int64)
    ramp = np.zeros(len(fy), np.uint8)
    tone = np.zeros(len(fy), np.float32)
    lnx = np.zeros(len(fy), np.float32)   # face-local tilt: along the face (right)
    lny = np.zeros(len(fy), np.float32)   # face-local tilt: up
    rel = fk / np.maximum(fd, 1)          # 0 at the top .. 1 at the foot
    # -- rock: photoscan plates with bedding
    for st, atl, ra, rb in ((FACE['rock'], atlases['cliff'], R['rock'], R['rock_warm']),):
        m = style == st
        if not m.any():
            continue
        a = atl
        ah, aw = a['plate'].shape
        off = (noise.hash2(sid_up[m], sid_up[m] * 7 + 3, seed + 1) % np.uint32(aw)).astype(np.int64)
        au = (X[m].astype(np.int64) + off) % aw
        av = (-np.round(v[m]).astype(np.int64) + 7) % ah
        plate = a['plate'][av, au]
        base = a['base'][av, au]
        rim = a['rim'][av, au]
        rep = noise.hash01(np.floor_divide(X[m].astype(np.int64) + off, aw) * 131 + plate,
                           np.floor_divide(-np.round(v[m]).astype(np.int64) + 7, ah) * 17 + plate, seed + 2)
        band = noise.fbm(X[m] / 140.0, v[m] / 50.0, seed + 3, 2)
        t = 3.3 + (base - 0.5) * 2.9 + (rep - 0.5) * 0.7
        t = t + np.where(rim == 2, 1.25, 0.0) + np.where(rim == 1, 0.45, 0.0) + np.where(rim == -1, -0.9, 0.0)
        t = np.where(plate == 0, 1.0 + (rep > 0.7) * 0.6, t)
        t = t + (0.35 - rel[m]) * 0.6 - smoothstep(0.75, 1.0, rel[m]) * 0.8
        rp = np.where(band + (rep - 0.5) * 0.15 > 0.52, rb, ra).astype(np.uint8)
        # moss and grass on the ledges, where it is damp
        damp = noise.fbm(X[m] / 60.0, v[m] / 25.0, seed + 4, 3)
        ledge = a['ledge'][av, au] & (plate > 0)
        mossy = ledge & (damp > 0.5) & (noise.hash01(X[m].astype(np.int64), np.round(v[m]).astype(np.int64), seed + 5) < 0.75)
        rp = np.where(mossy, R['moss'], rp)
        t = np.where(mossy, 2.6 + (damp > 0.62), t)
        # rare thin water stains below a ledge (1-2 px wide, fading downward)
        sc = noise.hash01(np.floor(X[m] / 2.0).astype(np.int64), 77, seed + 6)
        streak = (sc < 0.025) & (rel[m] > 0.2) & (rel[m] < 0.8)
        t = np.where(streak & (plate > 0), t - 0.5, t)
        ramp[m] = rp
        tone[m] = t
        lnx[m] = a['nx'][av, au]
        lny[m] = a['ny'][av, au]
    # -- dry-stone wall (野面積み): stones from the wall scan, dark chinks, moss plugs
    for st in (FACE['wall'],):
        m = style == st
        if not m.any():
            continue
        a = atlases['wall']
        ah, aw = a['plate'].shape
        off = (noise.hash2(sid_up[m], 11, seed + 7) % np.uint32(aw)).astype(np.int64)
        au = (X[m].astype(np.int64) + off) % aw
        av = (-np.round(v[m]).astype(np.int64) + 3) % ah
        plate = a['plate'][av, au]
        base = a['base'][av, au]
        rim = a['rim'][av, au]
        rep = noise.hash01(plate * 3 + np.floor_divide(X[m].astype(np.int64) + off, aw), plate, seed + 8)
        t = 3.4 + (base - 0.5) * 2.2 + (rep - 0.5) * 1.0
        t = t + np.where(rim == 2, 1.1, 0.0) + np.where(rim == 1, 0.4, 0.0) + np.where(rim == -1, -0.8, 0.0)
        t = t + (0.4 - rel[m]) * 0.5
        chink = plate == 0
        t = np.where(chink, 1.2, t)
        rp = np.where(rep < 0.35, R['stone_warm'], R['stone']).astype(np.uint8)
        mz = noise.fbm(X[m] / 40.0, v[m] / 20.0, seed + 9, 2)
        plug = chink & (mz > 0.52) & (noise.hash01(X[m].astype(np.int64), np.round(v[m]).astype(np.int64), seed + 10) < 0.5)
        rp = np.where(plug, R['moss'], rp)
        t = np.where(plug, 2.2, t)
        ledge = a['ledge'][av, au] & (plate > 0) & (mz > 0.58)
        rp = np.where(ledge, R['moss'], rp)
        t = np.where(ledge, 3.0, t)
        ramp[m] = rp
        tone[m] = t
        lnx[m] = a['nx'][av, au]
        lny[m] = a['ny'][av, au]
    # -- earth bank: layered soil, embedded stones, roots
    for st in (FACE['earth'], FACE['bank'], FACE['wetbank']):
        m = style == st
        if not m.any():
            continue
        Xm, vm = X[m], v[m]
        wob = (noise.fbm(Xm / 40.0, np.zeros(m.sum()) + 2.0, seed + 11, 2) - 0.5) * 6.0
        strata = noise.fbm(Xm / 70.0, (vm + wob) / 3.2, seed + 12, 2)
        t = 2.4 + (strata - 0.5) * 2.2 + (0.3 - rel[m]) * 0.8
        tone_m = _dither_round_s(t, fx[m], fy[m])
        rp = np.full(m.sum(), R['soil'] if st != FACE['wetbank'] else R['wetsoil'], np.uint8)
        # embedded stones: small rounded lumps lit on the upper left
        a = atlases['pebbles']
        ah, aw = a['plate'].shape
        au = (Xm.astype(np.int64) * 2 // 3) % aw
        av = (-np.round(vm).astype(np.int64) * 2 // 3) % ah
        pl = a['plate'][av, au]
        sel = noise.hash01(pl, pl * 3 + 1, seed + 13) < 0.16
        stone = (pl > 0) & sel
        rim = a['rim'][av, au]
        st_t = 3.4 + np.where(rim == 2, 1.0, 0) + np.where(rim == 1, 0.5, 0) + np.where(rim == -1, -0.8, 0)
        rp = np.where(stone, R['stone_warm'], rp)
        tone_m = np.where(stone, st_t, tone_m)
        # roots threading the bank (thin, wavy, mostly near the top)
        ry = (np.round(vm).astype(np.int64))
        rootline = np.abs(np.sin(Xm * 0.11 + np.floor(ry / 9.0) * 2.1) * 2.6 + (ry % 9) - 4.5) < 0.55
        rootsel = noise.hash01(np.floor(Xm / 19).astype(np.int64), np.floor(ry / 9.0).astype(np.int64), seed + 14) < 0.22
        root = rootline & rootsel & (rel[m] < 0.8)
        rp = np.where(root, R['bark'], rp)
        tone_m = np.where(root, 2.0, tone_m)
        if st == FACE['bank']:
            g = rel[m] < 0.6 + (noise.hash01(Xm.astype(np.int64), 3, seed + 15) - 0.5) * 0.4
            rp = np.where(g, R['grass_cool'], rp)
            tone_m = np.where(g, 2.0 + (noise.hash01(Xm.astype(np.int64), ry, seed + 16) > 0.6), tone_m)
        ramp[m] = rp
        tone[m] = tone_m
        lny[m] = np.where(stone, a['ny'][av, au], 0.0)
    # -- stair risers: dressed stone below each nosing
    m = style == FACE['riser']
    if m.any():
        u = world.stair_u.ravel()[up[m]]
        k = world.stair_k.ravel()[up[m]].astype(np.int64)
        sidm = sid_up[m]
        hk = noise.hash2(k, sidm, seed + 701)      # same slab split as the tread above (mat_top.paint_tread)
        off = (hk & np.uint32(31)).astype(np.float32)
        seg_w = 15.0 + ((hk >> np.uint32(5)) & np.uint32(15)).astype(np.float32)
        uu = np.where(k >= 0, u, X[m] % 40)
        seg = np.floor((uu + off) / seg_w)
        fu = (uu + off) - seg * seg_w
        hs = noise.hash2(seg.astype(np.int64), k * 7 + sidm, seed + 702)
        t = 3.0 + ((hs & np.uint32(255)).astype(np.float32) / 255.0) * 0.8
        t = np.where(fk[m] <= 1, t - 0.7, t)                          # under the nosing
        t = np.where(fk[m] >= fd[m], t - 0.4, t)                     # the foot
        t = np.where(fu < 1.0, t - 1.1, t)
        rp = np.where((hs >> np.uint32(9)) & np.uint32(1), R['stone_warm'], R['stone']).astype(np.uint8)
        mz = noise.fbm(X[m] / 12.0, v[m] / 6.0, seed + 703, 2)
        mossy = (fk[m] >= fd[m] - 1) & (mz > 0.55)
        rp = np.where(mossy, R['moss'], rp)
        t = np.where(mossy, 2.2, t)
        ramp[m] = rp
        tone[m] = t
        lny[m] = np.where(fk[m] <= 1, -0.4, 0.0)
    # -- cheek faces: rough blocks
    m = style == FACE['cheekface']
    if m.any():
        u = world.stair_u.ravel()[up[m]]
        k = world.stair_k.ravel()[up[m]].astype(np.int64)
        hb = noise.hash2(k, np.sign(u).astype(np.int64) + sid_up[m] * 3, seed + 751)
        t = 2.7 + ((hb & np.uint32(255)).astype(np.float32) / 255.0) * 0.8
        # bevel: lit top row and left edge, dark right edge and foot
        xl = np.zeros(m.sum(), bool)
        col = fx[m]
        rowv = fy[m]
        kk = S.kind
        left_open = (col > 0) & (S.face_style[rowv, np.maximum(col - 1, 0)] != FACE['cheekface'])
        right_open = (col < W - 1) & (S.face_style[rowv, np.minimum(col + 1, W - 1)] != FACE['cheekface'])
        t = np.where(fk[m] <= 1, t + 0.8, t)
        t = np.where(left_open, t + 0.5, t)
        t = np.where(right_open, t - 0.7, t)
        t = np.where(fk[m] >= fd[m], t - 0.5, t)
        fine = noise.fbm(X[m] / 3.0, v[m] / 3.0, seed + 752, 2)
        t = t + (fine - 0.5) * 0.8
        rp = np.where((hb >> np.uint32(8)) & np.uint32(1), R['stone'], R['stone_warm']).astype(np.uint8)
        mossy = (fk[m] >= fd[m] - 1) & (fine > 0.55)
        rp = np.where(mossy, R['moss'], rp)
        t = np.where(mossy, 2.4, t)
        ramp[m] = rp
        tone[m] = t
        lnx[m] = np.where(left_open, -0.4, np.where(right_open, 0.4, 0.0))
        lny[m] = np.where(fk[m] <= 1, 0.5, 0.0)
    # -- gentle-slope fill: the 1 px steps of a ramp are the ramp surface itself
    m = style == FACE['rampfill']
    if m.any():
        ramp[m] = top.ramp.ravel()[up[m]]
        tone[m] = top.tone.ravel()[up[m]] - 0.3
    # -- the sod lip: vegetated tops hang over the face in clumps
    veg = np.isin(upper_top, VEG_TOPS) & (style != FACE['rampfill']) & (style != FACE['riser'])
    if veg.any():
        wildv = world.wild.ravel()[up]
        L = _overhang_len(X, seed + 31, upper_top, wildv)
        L = np.minimum(L, np.maximum(fd - 2, 0))
        over = veg & (fk <= L)
        # the hanging sod in the top material's own colours, a little darker each row down
        ramp[over] = top.ramp.ravel()[up[over]]
        lip_tone = top.tone.ravel()[up[over]]
        t_o = np.clip(lip_tone, 2, 5) - (fk[over] - 1) * 0.55
        # ragged blade tips on the bottom row of each clump
        tipm = (fk[over] == L[over]) & (noise.hash01(X[over].astype(np.int64), 9, seed + 32) < 0.45)
        t_o = np.where(tipm, t_o + 0.8, t_o)
        tone[over] = t_o
        lny[over] = 0.3
        # the shadow line just under the sod
        under = veg & (fk == L + 1) & (L > 0)
        tone[under] = tone[under] - 1.3
        # the very top row where no sod hangs: the lip edge catches light
        bare_top = veg & (fk == 1) & (L == 0)
        tone[bare_top] = tone[bare_top] + 0.8
    # -- hanging roots and vines on rock and earth below vegetated lips
    hangable = np.isin(style, [FACE['rock'], FACE['earth']]) & np.isin(upper_top, (TOP['forest'], TOP['meadow'], TOP['moss']))
    if hangable.any():
        hcol = noise.hash01(X.astype(np.int64), 17, seed + 41)
        vine_len = np.floor(4 + noise.hash01(X.astype(np.int64), 19, seed + 42) * 12)
        is_vine = hangable & (hcol < 0.035) & (fk <= vine_len) & (fk > 1)
        kind_v = noise.hash01(X.astype(np.int64), 23, seed + 43) < 0.5
        ramp[is_vine] = np.where(kind_v[is_vine], R['moss'], R['bark'])
        tone[is_vine] = np.where(kind_v[is_vine], 2.6 - fk[is_vine] * 0.05, 1.6)
    SP.ramp[fy, fx] = ramp
    SP.tone[fy, fx] = np.clip(tone, 0, N_TONES - 1)
    SP.mat[fy, fx] = 32 + style
    # face normals: the edge's horizontal facing + the plate tilts in face coordinates
    tanx, tanz = nhz, -nhx      # along the face, pointing right (east-ish) for a south face
    nx = nhx + tanx * lnx
    ny = lny
    nz = nhz + tanz * lnx
    nn = np.stack([nx, ny, nz], -1)
    SP.n[fy, fx] = nn / np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-6)
    SP.flags[fy, fx] |= 16
    # ---- side strips (east/west walls collapsed to 1-2 px)
    sm = S.kind == KIND_SIDE
    sy, sx = np.nonzero(sm)
    sd = S.side[sm]
    src_t = world.top.ravel()[S.src[sm]]
    stone = np.isin(src_t, [TOP['tread'], TOP['cheek'], TOP['earth'], TOP['moss']])
    rp = np.where(stone, R['stone'], R['rock_warm']).astype(np.uint8)
    hv = noise.hash01(sx.astype(np.int64), sy.astype(np.int64), seed + 51)
    t = np.where(sd < 0, 4.2 + (hv > 0.6), 1.6 + (hv > 0.7) * 0.6)
    SP.ramp[sy, sx] = rp
    SP.tone[sy, sx] = t
    sn = np.stack([np.where(sd < 0, -0.9, 0.9), np.full(len(sd), 0.15), np.full(len(sd), 0.4)], -1)
    SP.n[sy, sx] = sn / np.linalg.norm(sn, axis=-1, keepdims=True)
    SP.mat[sy, sx] = 32 + FACE['rock']
    SP.flags[sy, sx] |= 16
    _foot_plants(SP, S, world, top, seed + 60)
    return SP


def _dither_round_s(v, x, y):
    b = noise.bayer(x, y) - 0.5
    return np.floor(v + 0.5 + b * 0.55)


def _foot_plants(SP, S, world, top, seed):
    """Grass and weeds standing on the lower ground at a cliff foot overlap the
    bottom of the face (they are closer to the camera): the foot line is
    broken plant by plant instead of being a ruler-straight seam."""
    Hs, W = S.kind.shape
    face = S.kind == KIND_FACE
    below_top = np.zeros_like(face)
    below_top[:-1] = face[:-1] & (S.kind[1:] == KIND_TOP) & (S.fk[:-1] == S.fd[:-1])
    ys, xs = np.nonzero(below_top)
    ys = ys + 1                          # the ground pixel right under the foot
    gtop = world.top.ravel()[S.src[ys, xs]]
    ok = np.isin(gtop, VEG_TOPS)
    ys, xs = ys[ok], xs[ok]
    h = noise.hash2(xs.astype(np.int64), ys.astype(np.int64), seed)
    keep = (h & np.uint32(255)) < 70
    ys, xs, h = ys[keep], xs[keep], h[keep]
    which = ((h >> np.uint32(8)) % np.uint32(len(stamps.TUFTS))).astype(np.int64)
    # stamp in screen space; relative tones use the ground ramp under the anchor
    anchor_ramp = SP.ramp[ys, xs].astype(np.int16)
    anchor_tone = SP.tone[ys, xs]
    allow = np.ones((Hs, W), bool)
    before_ramp = SP.ramp.copy()
    before_tone = SP.tone.copy()
    tmp_tone = np.zeros((Hs, W), np.float32)
    tmp_ramp = np.zeros((Hs, W), np.uint8)
    prio = np.full((Hs, W), -1e9, np.float32)
    touched = stamps.stamp(prio, tmp_tone, tmp_ramp, ys, xs, stamps.TUFTS, which, allow=allow)
    # map every touched pixel back to its anchor's ramp/tone (nearest anchor below it)
    if touched.any():
        ty, tx = np.nonzero(touched)
        # find anchor: the glyph's anchor is at most 5 px below and 3 px aside; use the
        # ground pixel straight below the touched pixel's face foot
        gy = ty.copy()
        for _ in range(8):
            step = (gy + 1 < Hs) & (S.kind[np.minimum(gy, Hs - 1), tx] != KIND_TOP)
            gy = np.where(step, gy + 1, gy)
        gy = np.minimum(gy, Hs - 1)
        is_ground = S.kind[gy, tx] == KIND_TOP
        base_r = np.where(is_ground, before_ramp[gy, tx], before_ramp[ty, tx])
        base_t = np.where(is_ground, before_tone[gy, tx], before_tone[ty, tx])
        SP.ramp[ty, tx] = base_r
        SP.tone[ty, tx] = np.clip(np.clip(base_t, 2, 5) + tmp_tone[ty, tx], 0, N_TONES - 1)
        SP.n[ty, tx] = np.array([0.0, 0.8, 0.6], np.float32)
        SP.flags[ty, tx] |= 1
