"""The oblique projection: world rasters -> screen rasters.

Projection (knowledge/15 §0): screen x = world x; screen y = world z - h.
1 m = 20 px on every axis. Horizontal surfaces keep their plan shape;
south-facing vertical faces appear at full height (h px per metre);
east/west faces collapse to a line and get a 1-2 px side strip; north
faces are hidden behind the surface in front of them.

Every world pixel contributes one *top* candidate; every place where the
height drops going south contributes the column of *face* candidates
between the two tops. Candidates are resolved per screen pixel by depth
D = z + h (closer to the camera wins), which is the exact painter's order
of the oblique view.
"""
import numpy as np

from .geom import PPM
from .layout import FACE

KIND_NONE, KIND_TOP, KIND_FACE, KIND_SIDE = 0, 1, 2, 3


class Screen:
    """Screen-space buffers for a region (row-major, shape (Hs, W))."""
    pass


def project(world, min_drop_px=1):
    H, W = world.H, world.W
    valid = ~np.isnan(world.h)
    hp = np.where(valid, np.round(world.h * PPM), np.round(world.void_h * PPM)).astype(np.int32)
    zi, xi = np.nonzero(valid)
    # ---- tops
    t_row = zi - hp[zi, xi]
    t_depth = (zi + hp[zi, xi]).astype(np.float32)
    t_src = (zi * W + xi).astype(np.int64)
    # ---- faces: drops going south between row z-1 (upper) and row z (lower)
    up_h = hp[:-1, :]
    dn_h = hp[1:, :]
    up_valid = valid[:-1, :]
    drop = np.where(up_valid, up_h - dn_h, 0)
    fz, fx = np.nonzero(drop >= min_drop_px)
    d = drop[fz, fx]
    fz_lower = fz + 1                          # the lower cell's row
    counts = d.astype(np.int64)
    F = int(counts.sum())
    rep = np.repeat(np.arange(len(d)), counts)
    k = np.arange(F) - np.repeat(np.cumsum(counts) - counts, counts) + 1     # 1..d
    hu = up_h[fz, fx][rep]
    f_row = (fz[rep]) - hu + k                 # rows just below the upper top's row
    f_hpx = hu - k + 0.5                       # pixel height (px) on the face
    f_depth = (fz_lower[rep] - 0.5 + f_hpx).astype(np.float32)
    f_up = (fz[rep] * W + fx[rep]).astype(np.int64)
    f_dn = (fz_lower[rep] * W + fx[rep]).astype(np.int64)
    f_k = k.astype(np.int32)
    f_d = d[rep].astype(np.int32)
    f_col = fx[rep]
    # ---- screen extent
    rmin = int(min(t_row.min(), f_row.min() if F else t_row.min())) - 2
    rmax = int(max(t_row.max(), f_row.max() if F else t_row.max())) + 2
    Hs = rmax - rmin + 1
    # ---- resolve: concat candidates, keep the max depth per screen pixel
    n_t = len(t_row)
    rows = np.concatenate([t_row - rmin, f_row - rmin])
    cols = np.concatenate([xi, f_col])
    depth = np.concatenate([t_depth, f_depth])
    is_face = np.concatenate([np.zeros(n_t, bool), np.ones(F, bool)])
    cand = np.arange(n_t + F)
    pix = rows.astype(np.int64) * W + cols
    order = np.lexsort((depth, pix))           # by pixel, then depth ascending
    pix_s = pix[order]
    last = np.ones(len(pix_s), bool)
    last[:-1] = pix_s[1:] != pix_s[:-1]
    win = order[last]
    S = Screen()
    S.W, S.H, S.rmin = W, Hs, rmin
    S.kind = np.zeros(Hs * W, np.uint8)
    S.src = np.full(Hs * W, -1, np.int64)       # world index of the top (or the face's upper cell)
    S.src_dn = np.full(Hs * W, -1, np.int64)    # face: world index of the lower cell
    S.depth = np.full(Hs * W, -1e9, np.float32)
    S.hpx = np.zeros(Hs * W, np.float32)        # world height of the pixel (px)
    S.fk = np.zeros(Hs * W, np.int32)           # face: px below the face top (1 = top row)
    S.fd = np.zeros(Hs * W, np.int32)           # face: total face height (px)
    wp = pix[win]
    wface = is_face[win]
    S.depth[wp] = depth[win]
    S.kind[wp] = np.where(wface, KIND_FACE, KIND_TOP)
    ti = win[~wface]
    S.src[wp[~wface]] = t_src[ti]
    S.hpx[wp[~wface]] = hp.ravel()[t_src[ti]]
    fi = win[wface] - n_t
    S.src[wp[wface]] = f_up[fi]
    S.src_dn[wp[wface]] = f_dn[fi]
    S.hpx[wp[wface]] = f_hpx[fi]
    S.fk[wp[wface]] = f_k[fi]
    S.fd[wp[wface]] = f_d[fi]
    # reshape
    for a in ('kind', 'src', 'src_dn', 'depth', 'hpx', 'fk', 'fd'):
        setattr(S, a, getattr(S, a).reshape(Hs, W))
    S.face_style = np.zeros((Hs, W), np.uint8)
    m = S.kind == KIND_FACE
    S.face_style[m] = world.face.ravel()[S.src[m]]
    # ramps: the 1 px "faces" between rows of a gentle slope are slope surface, not walls
    if hasattr(world, 'ramp_mask'):
        rm = world.ramp_mask.ravel()
        small = m & (S.fd <= 2)
        both = small.copy()
        both[small] = rm[S.src[small]] | rm[S.src_dn[small]]
        S.face_style[both] = FACE['rampfill']
    _side_strips(S, world)
    return S


def _side_strips(S, world):
    """East/west-facing walls are a line in the oblique view: give them 1-2 px.

    A top pixel whose west neighbour on screen is clearly lower ground is the
    west edge of a raised surface: its wall faces west (toward the sun's side)
    and reads as a lit strip. The east edge's wall faces away: a dark strip."""
    H, W = S.kind.shape
    top = S.kind == KIND_TOP
    hp = S.hpx
    S.side = np.zeros((H, W), np.int8)          # -1 west-facing strip, +1 east-facing strip
    S.side_d = np.zeros((H, W), np.float32)     # the height of that wall (px)
    for direction, sgn in ((1, -1), (-1, 1)):
        # direction=1: compare with the west neighbour (x-1)
        nb_h = np.roll(hp, direction, axis=1)
        nb_k = np.roll(S.kind, direction, axis=1)
        if direction == 1:
            nb_k[:, 0] = 0
        else:
            nb_k[:, -1] = 0
        dh = hp - nb_h
        edge = top & (nb_k != KIND_NONE) & (dh >= 6)
        # 2 px for tall walls (>1 m), else 1 px
        S.side[edge] = sgn
        S.side_d[edge] = dh[edge]
        tall = edge & (dh > 20)
        nxt = np.roll(tall, direction, axis=1)
        if direction == 1:
            nxt[:, 0] = False
        else:
            nxt[:, -1] = False
        nxt &= top & (S.side == 0)
        S.side[nxt] = sgn
        S.side_d[nxt] = np.roll(S.side_d, direction, axis=1)[nxt]
    S.kind[S.side != 0] = KIND_SIDE
