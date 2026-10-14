"""Per-character settings for derive.py: which illustration, how it is framed, how its regions become materials,
and how each material is toned. Coordinates are in the 96 x 96 frame."""

import numpy as np

from lib import Canvas, box, classify, lab, mpoly, resolve


def _mask(pts):
    cv = Canvas(96, 96, '0')
    cv.poly(pts, '1')
    return np.array([[cv.g[y][x] == '1' for x in range(96)] for y in range(96)])


# ------------------------------------------------------------------------------------------------- Shione

def _shione_materials(ctx):
    m = classify(ctx['c'], ctx['a'], [
        ('h', 'fig'),
        ('s', '((h > 30) & (h < 100) & (C >= 7) & (l > 60))'),
        ('k', '((l > 93) & (C < 8) & (h > 40))'),
        ('r', '((C >= 24) & (h > -30) & (h < 50))'),
        ('d', '((l < 44) & (C < 24))'),
    ])
    mpoly(m, [(30, 76), (40, 68), (58, 70), (74, 80), (96, 86), (96, 96), (28, 96)], 'k', only='hsk')
    mpoly(m, [(28, 66), (40, 64), (60, 68), (76, 82), (84, 96), (60, 96), (40, 76), (28, 78)], 'c', only='d')
    mpoly(m, [(56, 72), (66, 76), (84, 92), (84, 96), (76, 96), (60, 80)], 't', only='r')
    box(m, 42, 30, 60, 42, 'e', only='rd')
    box(m, 64, 35, 80, 47, 'e', only='rd')
    box(m, 47, 42, 53, 48, 'x', only='r')
    box(m, 0, 54, 26, 96, 'T', only='r')
    m[m == 'r'] = 'd'
    m = resolve(m)
    m[:64][m[:64] == 'k'] = 'h'
    return m


# ------------------------------------------------------------------------------------------------- Tsuzumi

_TS_FRONT = [(96, 35.5), (80, 31.5), (60, 27), (40, 22.5), (20, 18.5), (0, 13.5)]   # hat brim front edge
_TS_UNDER_L = [(0, 13.5), (20, 18.5), (26, 20), (18, 25), (13, 30), (10, 35), (7, 42), (5, 47.5), (0, 47.5)]
_TS_UNDER_R = [(75, 31), (96, 35.5), (96, 54), (78, 53.5), (78, 46), (78, 40), (76.5, 34)]
_TS_TIE_L = [(25.5, 72.5), (37, 72), (38, 82.5), (27, 83.5), (26, 78)]
_TS_TIE_R = [(68, 75), (80, 72.5), (82.5, 80.5), (72, 83.5)]
_TS_COLLAR = [(30, 96), (34, 86), (38, 80.5), (44, 79), (50, 75), (54, 74), (58, 76), (64, 80), (72, 84), (78, 88),
              (84, 96)]


def _tsuzumi_materials(ctx):
    cls, L, c = ctx['cls'], ctx['L'], ctx['cref']
    fig = cls != '.'
    m = np.where(fig, 'h', '.').astype('<U1')
    top = _mask([(0, 0), (96, 0)] + _TS_FRONT)
    m[top & fig] = 'a'
    lb = lab(c)
    C0 = np.hypot(lb[..., 1], lb[..., 2])
    h0 = np.degrees(np.arctan2(lb[..., 2], lb[..., 1]))
    m[top & fig & (C0 > 20) & (h0 > -25) & (h0 < 45)] = 'b'
    m[(_mask(_TS_UNDER_L) | _mask(_TS_UNDER_R)) & fig & ~top] = 'n'
    for pts in (_TS_TIE_L, _TS_TIE_R):
        m[_mask(pts) & fig] = 'T'
    col = _mask(_TS_COLLAR) & fig & ~(_mask(_TS_TIE_L) | _mask(_TS_TIE_R))
    m[col & (L >= 50)] = 'c'
    m[col & (cls == 'r')] = 'r'
    m[col & (L < 50) & (cls != 'r') & (h0 < -50)] = 'k'
    return m


# ------------------------------------------------------------------------------------------------- Saji

def _saji_materials(ctx):
    c, a = ctx['c'], ctx['a']
    Lb = lab(c)
    l, aa, bb = Lb[..., 0], Lb[..., 1], Lb[..., 2]
    C = np.hypot(aa, bb)
    h = np.degrees(np.arctan2(bb, aa))
    Y = np.arange(96)[:, None] * np.ones((1, 96))
    X = np.ones((96, 1)) * np.arange(96)[None, :]
    fig = a > 0.5
    m = np.where(fig, 'h', '.').astype('<U1')
    m[fig & (h > 40) & (h < 85) & (C >= 7) & (C < 35) & (l > 62)] = 's'
    m[fig & (h > 85) & (l > 55) & (Y > 64)] = 'm'
    m[fig & (aa < -3) & (bb < 4) & (l < 55) & (Y < 37)] = 'g'
    col = fig & (Y >= 68) & (X >= 20) & (X <= 70) & (m != 'm')
    m[col & (C > 15) & (h < 22) & (l < 55)] = 'c'
    m[col & (C > 40) & (h >= 22) & (h < 45)] = 'r'
    m[col & (l < 30) & (m == 'h')] = 'd'
    bell = fig & (Y >= 84) & (X >= 50) & (X <= 74)
    m[bell & (h > 50) & (h < 100) & (C > 20)] = 'G'
    return resolve(m)


# ------------------------------------------------------------------------------------------------- the table
# ident / eyes: the illustration and its eye centres (px); frame: eye distance (px in the 96 frame), eye-line tilt
# (deg, falling to the viewer's right), eye midpoint (fraction of the frame).
# zone: the face polygon where the reference's skin classes decide skin; eyebox: kept plain skin (the eyes are
# parts); jaw: where dark reference cells next to skin join the skin (they become the jaw line); face_clean: where
# the illustration's nose and mouth lines are filled with skin (they are parts too).
# skin_cuts: reference L for s / t / u (below: q if darker than ink_max, else u); hairs: (material, ramp light ->
# dark, L cuts, flow-smoothing length); strands: (dark percentile, light percentile, min length dark, light).
CHARS = {
    'shione': dict(
        ident='B_10', eyes=((524, 167), (581, 192)), frame=(21.0, 15.0, 0.66, 0.42),
        materials=_shione_materials, hair_mat='h',
        zone=[(42, 28), (60, 14), (66, 14), (82, 20), (84, 40), (80, 56), (66, 66), (60, 70), (44, 70), (42, 50)],
        skin_cell=lambda c, x, y: c in 'sr' or (c == 'w' and y >= 32),
        eyebox=((45, 33, 59, 42), (70, 37, 78, 46), (49, 42, 53, 48)), jaw=(42, 48, 80, 68),
        face_clean=(44, 45, 72, 66), wisp_passes=0,
        skin_cuts=(88, 76, 62), ink_max=42,
        hairs=[('h', 'HLMDO', [85, 76, 63, 48], 8.0)], hair_blur=0.8, hair_min=5, strands=(90, 96, 10, 9),
        spec={'k': dict(ramp=list('WVUY')), 'c': dict(ramp=list('5678')), 't': dict(ramp=list('12')),
              'T': dict(ramp=list('1234')), 'n': dict(ramp=list('JRrP'))},
        line={'h': 'K', 's': 'q', 'k': 'Y', 'c': '8', 'T': '4', 'n': 'P'},
    ),
    'tsuzumi': dict(
        ident='A_01', eyes=((497, 207), (558, 235)), frame=(21.0, 12.0, 0.52, 0.52),
        materials=_tsuzumi_materials, hair_mat='h',
        zone=[(30, 40), (66, 40), (68, 60), (60, 72), (56, 80), (40, 80), (32, 70)],
        skin_cell=lambda c, x, y: c in 'srw' and y >= 40,
        eyebox=((33, 43, 46, 53), (55, 46, 64, 55)), jaw=(30, 56, 70, 80),
        face_clean=(36, 55, 64, 74), wisp_passes=3,
        skin_cuts=(88, 76, 62), ink_max=42,
        hairs=[('h', 'hHLMDO', [36, 29, 23, 17, 11], 6.0)], hair_blur=0.8, hair_min=5, strands=(90, 96, 10, 9),
        spec={'a': dict(ramp=list('WVUY')), 'b': dict(ramp=list('RrP')), 'n': dict(ramp=list('1234'), blur=1.0),
              'T': dict(ramp=list('WVURr')), 'c': dict(ramp=list('WVU')), 'r': dict(ramp=list('Rr')),
              'k': dict(ramp=list('5678'), blur=1.4)},
        line={'h': 'K', 's': 'q', 'a': 'Y', 'b': 'P', 'n': '4', 'T': 'Y', 'c': 'Y', 'r': 'P', 'k': '8'},
    ),
    'saji': dict(
        ident='C_01', eyes=((495, 184), (559, 218)), frame=(22.0, 15.0, 0.52, 0.45),
        materials=_saji_materials, hair_mat='h',
        zone=[(28, 26), (48, 22), (70, 30), (72, 48), (64, 66), (56, 82), (40, 82), (30, 60)],
        skin_cell=lambda c, x, y: c in 'sw' and y >= 28,
        eyebox=((31, 35, 46, 47), (56, 39, 68, 50)), jaw=(28, 50, 72, 82),
        face_clean=(32, 48, 66, 68), wisp_passes=2,
        skin_cuts=(80, 70, 58), ink_max=42,
        hairs=[('h', 'hHLMDO', [58, 50, 44, 36, 26], 6.0)], hair_blur=0.8, hair_min=5, strands=(90, 96, 10, 9),
        spec={'g': dict(ramp=list('1234')), 'm': dict(ramp=list('567'), blur=2.0, cuts=[83.3, 79.6]),
              'c': dict(ramp=list('PQZ')), 'r': dict(ramp=list('Rr')), 'G': dict(ramp=list('GFAB'))},
        line={'h': 'K', 's': 'q', 'g': '4', 'm': '8', 'c': 'Z', 'r': 'Z', 'G': 'B'},
    ),
}
