"""百々かさゝぎ, round 6: head, hair and hat, built to the model sheet (design.py has the blueprint
frame and every measured number).

The sheet's head: a big round chibi head (the crown about 0.54 m above the chin, 3.3 heads tall in
all), a round face wider than tall (0.34 m at the cheeks), big grey eyes under thick hime bangs that
hide the brows, small ears showing between the face and the hair; hair falling round the face to the
shoulders and on down the back to the thighs, two locks in front of the shoulders tied white-red-
white under the chin. The hat: a wide shallow cone (1.24 m across, 0.32 m high, navy underneath, a
cream rim), worn tipped back and a little to her left, a red band round the crown and down one side
to a knot, its tail hanging behind her on her left.

Parts carry tags for the rigger: tag['seg'] (head, hair_cap, hair_bang, hair_side, hair_back, hat ...),
tag['side'] (-1 her right / +1 her left), tag['u'] (0 root .. 1 tip along a chain).
"""
import math
from mathutils import Vector

from c3d.surf import (Part, grid, sweep, cap, Path, interp, smooth, lerp,
                      M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_TIE)
from kasasagi import body as B
from kasasagi import palette as C
from kasasagi.design import D

TAU = 2 * math.pi

# =================================================================================================
# head: per height h above the chin, the half width W, the front F and the back K of the slice,
# measured from the head's axis (forward is -Y). Front view: the face 0.168 half wide at the cheeks,
# round to a soft chin; side view: the face's front 0.235 ahead of the body axis, the chin 0.178.
HEAD_TABLE = [
    # h      W       F       K
    (0.000, 0.040, 0.158, -0.050),
    (0.020, 0.092, 0.180, -0.035),
    (0.050, 0.130, 0.200, 0.040),
    (0.090, 0.156, 0.212, 0.120),
    (0.130, 0.168, 0.215, 0.180),
    (0.180, 0.176, 0.215, 0.215),
    (0.240, 0.205, 0.210, 0.235),
    (0.300, 0.228, 0.198, 0.240),
    (0.360, 0.235, 0.178, 0.236),
    (0.420, 0.222, 0.148, 0.216),
    (0.470, 0.186, 0.110, 0.172),
    (0.510, 0.122, 0.066, 0.104),
    (0.538, 0.000, 0.000, 0.000),
]


def head_slice(h):
    W = interp([(p[0], p[1]) for p in HEAD_TABLE], h)
    F = interp([(p[0], p[2]) for p in HEAD_TABLE], h)
    K = interp([(p[0], p[3]) for p in HEAD_TABLE], h)
    return max(W, 0.0), F, K


def head_point(h, t, grow=0.0):
    """The head's surface at height h above the chin and angle t (0 her left, pi/2 front, pi her
    right, 3pi/2 back), pushed out by `grow`."""
    h = min(max(h, 0.0), B.HEAD_H)
    W, F, K = head_slice(h)
    c, s = math.cos(t), math.sin(t)
    if s >= 0:
        e = 2.0 / 2.3                       # the face: round, a little full at the cheeks
        x = (W + grow) * math.copysign(abs(c) ** e, c)
        y = B.HEAD_YC - (F + grow) * (s ** e)
    else:
        e = 2.0 / 2.05
        x = (W + grow) * math.copysign(abs(c) ** e, c)
        y = B.HEAD_YC + (K + grow) * ((-s) ** e)
    return Vector((x, y, B.CHIN_Z + h))


HEAD_C = Vector((0.0, B.HEAD_YC + 0.01, B.CHIN_Z + 0.27))
HEAD_R = Vector((0.24, 0.24, 0.29))


def ellipsoid_normal(p, c=HEAD_C, r=HEAD_R):
    d = p - c
    return Vector((d.x / (r.x * r.x), d.y / (r.y * r.y), d.z / (r.z * r.z))).normalized()


def face_normal(p):
    """Smooth, mostly forward normals on the face (a clean one-tone face; the stamps' facing tests
    read the same field)."""
    h = p.z - B.CHIN_Z
    W, F, K = head_slice(min(max(h, 0.0), B.HEAD_H))
    xs = p.x / max(W, 1e-3)
    n = Vector((0.9 * xs, -1.0, 0.2 * (h - 0.15) / 0.15))
    return n.normalized()


def head():
    part = Part('head', M_FACE)
    nu, nv = 32, 44

    def pos(u, v):
        if u <= 0.0:
            return Vector((0.0, B.HEAD_YC - head_slice(0.0)[1] + 0.004, B.CHIN_Z - 0.002))
        if u >= 1.0:
            return Vector((0.0, B.HEAD_YC, B.CHIN_Z + B.HEAD_H))
        return head_point(B.HEAD_H * u, v * TAU)

    def col(u, v):
        h = B.HEAD_H * u
        t = v * TAU
        # the jaw's underside a step deeper
        if h < 0.03 and math.sin(t) < 0.6:
            return C.SKIN_DEEP
        return C.SKIN

    grid(part, nu, nv, pos, close_v=True, pole0=True, pole1=True, col=col,
         auxf=lambda u, v: (M_FACE, 0.0), tagf=lambda u, v: {'seg': 'head'}, flip=True)
    for i, p in enumerate(part.v):
        if p.y < B.HEAD_YC - 0.05:
            part.nrm[i] = face_normal(p)
    return [part, ears(), neck()]


def ears():
    """Small ears beside the face (they show between the face and the hair in the sheet)."""
    part = Part('ears', M_SKIN)
    hz = D['ear_h'] - B.CHIN_Z
    for side in (1, -1):
        W, F, K = head_slice(hz)
        c = Vector((side * (W - 0.004), B.HEAD_YC + 0.035, D['ear_h']))
        path = Path([c + Vector((0, 0.0, 0.040)), c, c + Vector((0, -0.004, -0.035))],
                    up=(side, 0, 0))

        def section(u, a):
            r = 0.022 * math.sin(math.pi * min(1.0, max(0.0, u)) * 0.9 + 0.15)
            return (r * 0.9 * math.cos(a), r * 0.55 * math.sin(a))
        sweep(part, path, 6, 10, section, col=lambda u, v: C.SKIN, auxf=lambda u, v: (M_SKIN, 0.0),
              tagf=lambda u, v: {'seg': 'head'}, pole0=True, pole1=True)
    return part


def neck():
    part = Part('neck', M_SKIN)
    path = Path([B.NECK_BASE + Vector((0, 0, -0.06)), B.NECK_BASE, B.NECK_TOP, B.NECK_TOP + Vector((0, -0.01, 0.05))],
                up=(0, -1, 0))

    def section(u, a):
        r = 0.040 - 0.004 * u
        return (r * math.cos(a), r * 0.95 * math.sin(a))
    sweep(part, path, 6, 12, section, col=lambda u, v: C.SKIN_DEEP,
          auxf=lambda u, v: (M_SKIN, 0.0), tagf=lambda u, v: {'seg': 'neck', 'u': u})
    return part


# =================================================================================================
# hair

def _strand(part, pts, width, thick, nu, nv=10, tip='point', up=None, col=None, tagf=None, aux_extra=0.0,
            uvf=None, mat=M_HAIR):
    """One clump: a flattened tube along a path (lens section: `width` across, `thick` outward)."""
    path = Path(pts, up=up or (0, -1, 0))

    def section(u, a):
        w = width(u)
        th = thick(u)
        ca, sa = math.cos(a), math.sin(a)
        out = th * (sa if sa > 0 else sa * 0.55)
        across = w * math.copysign(abs(ca) ** 0.85, ca)
        return (out, across)

    rows = sweep(part, path, nu, nv, section, close_v=True, pole1=(tip == 'point'),
                 col=col or (lambda u, v: C.HAIR), auxf=lambda u, v: (mat, aux_extra), tagf=tagf,
                 uvf=uvf, flip=True)
    if tip == 'blunt':
        p, t, n, b = path.at(1.0)
        cap(part, rows[-1], p + t * 0.004, col=(col(1.0, 0.5) if col else C.HAIR), aux=(mat, aux_extra))
    return path


def _hairline(t):
    """Height (above the chin) where the hair cap ends, by angle round the head: over the forehead the
    bangs hang from it; down over the temples to the ears; low at the nape."""
    phi = abs(((t - math.pi / 2 + math.pi) % TAU) - math.pi)      # 0 front .. pi back
    h = 0.30
    h -= 0.13 * smooth((phi - 1.0) / 0.45)        # the sides: down to the ears' tops
    h -= 0.14 * smooth((phi - 1.9) / 0.7)         # the back: to the nape
    return h


def hair_cap():
    part = Part('hair_cap', M_HAIR)
    nu, nv = 18, 52

    def pos(u, v):
        t = v * TAU
        if u >= 1.0:
            return Vector((0, B.HEAD_YC, B.CHIN_Z + B.HEAD_H + 0.05))
        hl = _hairline(t)
        h = lerp(hl, B.HEAD_H, u ** 0.9)
        g = 0.040 + 0.030 * smooth((h - 0.20) / 0.20)
        return head_point(min(h, B.HEAD_H - 0.001), t, grow=g)

    grid(part, nu, nv, pos, close_v=True, pole1=True, col=lambda u, v: C.HAIR,
         auxf=lambda u, v: (M_HAIR, 0.0), tagf=lambda u, v: {'seg': 'hair_cap', 'u': 0.0}, flip=True)
    for i, p in enumerate(part.v):
        part.nrm[i] = ellipsoid_normal(p, HEAD_C + Vector((0, 0.0, 0.04)), HEAD_R * 1.15)
    return part


def bangs():
    """Thick hime bangs cut straight across at the eyes' top (they hide the brows, G5R3-8)."""
    part = Part('bangs', M_HAIR)
    n = 15
    spread = 1.10
    cut = B.BANG_CUT_H - B.CHIN_Z
    for k in range(n):
        f = (k + 0.5) / n * 2 - 1           # -1 her right .. 1 her left
        t = math.pi / 2 - f * spread
        side = abs(f)
        c = cut - 0.02 * smooth((side - 0.75) / 0.25)
        hs = [B.HEAD_H - 0.06, B.HEAD_H - 0.16, 0.5 * (B.HEAD_H - 0.16 + c + 0.04), c + 0.04, c]
        grows = [0.062, 0.060, 0.046, 0.034, 0.032]
        pts = [head_point(h, t, grow=g) for h, g in zip(hs, grows)]
        out = (pts[-2] - HEAD_C).normalized()

        def width(u):
            return lerp(0.030, 0.042, smooth(u * 1.3))

        def thick(u):
            return lerp(0.012, 0.016, u)

        def tag(u, v, k=k, f=f):
            return {'seg': 'hair_bang', 'u': u, 'k': k, 'side': f}

        _strand(part, pts, width, thick, nu=10, nv=10, tip='blunt', up=out,
                col=lambda u, v: C.HAIR, tagf=tag)
    for i, p in enumerate(part.v):
        part.nrm[i] = (ellipsoid_normal(p, HEAD_C + Vector((0, 0.0, 0.05)), HEAD_R * 1.15) * 0.6 +
                       Vector((0, -1, 0.25)).normalized() * 0.4).normalized()
    return part


# ---- the mantle: the hair round the sides and back, from the crown down -----------------------
# per height (absolute): half width A (front and back views), the back's distance behind the body
# axis (side view), and how far round toward the front the hair reaches (angle from the front:
# beside the face at the head, behind the shoulders lower down)
MANTLE = [
    # h      A      back   front-edge angle (deg from the front)
    (1.70, 0.236, 0.270, 80.0),
    (1.62, 0.292, 0.315, 81.0),
    (1.55, 0.318, 0.335, 82.0),
    (1.45, 0.320, 0.345, 84.0),
    (1.30, 0.300, 0.365, 86.0),
    (1.20, 0.300, 0.385, 88.0),
    (1.10, 0.320, 0.400, 92.0),
    (1.00, 0.340, 0.410, 100.0),
    (0.85, 0.310, 0.405, 112.0),
    (0.70, 0.250, 0.385, 120.0),
    (0.58, 0.200, 0.360, 128.0),
    (D['back_hair_end'], 0.140, 0.330, 135.0),
]
MANTLE_TOP = MANTLE[0][0]


def mantle_slice(h):
    A = interp([(p[0], p[1]) for p in reversed(MANTLE)], h)
    Bk = interp([(p[0], p[2]) for p in reversed(MANTLE)], h)
    ang = interp([(p[0], p[3]) for p in reversed(MANTLE)], h)
    return A, Bk, math.radians(ang)


def mantle_point(h, a, inner=False):
    """A point on the mantle at height h, angle a from the front (+ toward her left)."""
    A, Bk, a0 = mantle_slice(h)
    th = 0.028 if not inner else 0.0
    # front of the mantle at the head: just outside the head's own slice
    fr = 0.06
    s, c = math.sin(a), math.cos(a)
    x = (A - (0 if not inner else 0.025)) * s
    if c >= 0:
        y = B.HEAD_YC - fr * c
    else:
        y = 0.0 + (Bk - (0 if not inner else 0.025)) * (-c) ** 0.9
    return Vector((x, y, h))


def mantle():
    """One sheet round the back and sides: the outside (the hair) and a thin inside facing in."""
    part = Part('hair_mantle', M_HAIR)
    nu, nv = 30, 40
    hb = D['back_hair_end']

    def pos_out(u, v):
        h = lerp(MANTLE_TOP, hb, u)
        A, Bk, a0 = mantle_slice(h)
        a = lerp(-(math.pi * 2 - a0), -a0, v)          # from her right front edge round the back
        a = -a                                          # (+ toward her left)
        # the bottom: a soft point at the back middle
        p = mantle_point(h, a)
        return p

    def col(u, v):
        # strands: darker between, the GPT highlight down the middle of each
        k = (v * 18.0) % 1.0
        if k < 0.12:
            return C.HAIR_DEEP
        return C.HAIR

    grid(part, nu, nv, pos_out, close_v=False, col=col, auxf=lambda u, v: (M_HAIR, 0.2),
         uvf=lambda u, v: (v, u), tagf=lambda u, v: {'seg': 'hair_back', 'u': u, 'x': 2 * v - 1},
         flip=False)
    # the inside, a little inward, facing in (so the sheet has two sides)
    n0 = len(part.v)

    def pos_in(u, v):
        h = lerp(MANTLE_TOP, hb, u)
        A, Bk, a0 = mantle_slice(h)
        a = -lerp(-(math.pi * 2 - a0), -a0, v)
        p = mantle_point(h, a)
        c = Vector((0, 0.0, h))
        return p + (c - p).normalized() * 0.03
    grid(part, nu, nv, pos_in, close_v=False, col=lambda u, v: C.HAIR_DEEP,
         auxf=lambda u, v: (M_HAIR, 0.2), uvf=lambda u, v: (v, u),
         tagf=lambda u, v: {'seg': 'hair_back', 'u': u, 'x': 2 * v - 1}, flip=True)
    # the bottom edge: a point at the back middle
    for i in range(len(part.v)):
        p = part.v[i]
        tg = part.tag[i]
        if tg.get('u', 0) > 0.6:
            x = tg.get('x', 0.0)
            drop = 0.06 * (1.0 - abs(x)) * smooth((tg['u'] - 0.6) / 0.4)
            part.v[i] = Vector((p.x, p.y, p.z - drop))
    return part


def side_pieces():
    """The hime cut's side pieces: a clump each side from the temple down beside the cheek to the jaw
    (sheet front: u 145..160 and 278..295 down to v 200), just outside the face."""
    part = Part('side_pieces', M_HAIR)
    for side in (1, -1):
        pts = [head_point(0.36, math.pi / 2 - side * 1.05, grow=0.055),
               head_point(0.26, math.pi / 2 - side * 1.12, grow=0.045),
               Vector((side * 0.192, B.HEAD_YC - 0.075, B.CHIN_Z + 0.16)),
               Vector((side * 0.196, B.HEAD_YC - 0.070, B.CHIN_Z + 0.085))]

        def width(u):
            return lerp(0.030, 0.026, u)

        def thick(u):
            return 0.016

        def tag(u, v, side=side):
            return {'seg': 'hair_bang', 'u': u, 'k': 0, 'side': side}
        _strand(part, pts, width, thick, nu=10, nv=8, tip='blunt', up=(side * 0.6, -1.0, 0.0),
                col=lambda u, v: C.HAIR, tagf=tag)
    return part


def side_lock_points(side):
    x = D['lock_x'] * side
    tie, end = D['lock_tie_h'], D['lock_end_h']
    # from the temple, down behind the cheek (the face's full width shows in front of it), forward
    # under the jaw to hang in front of the shoulder, through the tie to the blunt end
    return [head_point(0.30, math.pi / 2 - side * 1.25, grow=0.045),
            Vector((x * 0.98, B.HEAD_YC - 0.01, B.CHIN_Z + 0.16)),
            Vector((x, -0.05, B.CHIN_Z + 0.03)),
            Vector((x, -0.10, tie + 0.03)),
            Vector((x, -0.10, tie)),
            Vector((x * 1.01, -0.095, end))]


def side_locks():
    parts = []
    W = D['lock_w'] / 2.0
    for side in (1, -1):
        part = Part('side_lock', M_HAIR)
        pts = side_lock_points(side)
        L = Path(pts).length
        tie_u = Path(pts[:5]).length / L

        def width(u, tie_u=tie_u):
            w = lerp(W * 0.75, W, smooth(u * 3.0))
            w *= 1.0 - 0.30 * math.exp(-((u - tie_u) / 0.05) ** 2)
            return w

        def thick(u, tie_u=tie_u):
            return 0.030 * (1.0 - 0.25 * math.exp(-((u - tie_u) / 0.05) ** 2))

        def tag(u, v, side=side):
            return {'seg': 'hair_side', 'u': u, 'side': side}

        outward = Vector((side * 0.25, -1.0, 0.0)).normalized()
        _strand(part, pts, width, thick, nu=18, nv=10, tip='blunt', up=outward,
                col=lambda u, v: C.HAIR, tagf=tag)
        # the tie: white - red - white (sheet: 30 px tall, the red a third)
        p4 = pts[4]
        tc = p4 + Vector((0, 0, 0.0))
        path = Path([tc + Vector((0, 0, 0.044)), tc + Vector((0, 0, -0.044))], up=outward)

        def section(u, a):
            return (0.036 * math.cos(a), W * 1.02 * math.sin(a))

        def tcol(u, v):
            return C.RED if 0.36 < u < 0.64 else C.WHITE
        sweep(part, path, 6, 14, section, col=tcol, auxf=lambda u, v: (M_TIE, 0.0),
              tagf=lambda u, v, side=side, tie_u=tie_u: {'seg': 'hair_side', 'u': tie_u, 'side': side})
        parts.append(part)
    return parts


def outer_strands():
    """Long strands slipping off the shoulders and falling outside the sleeves (front view: dark
    strands from the shoulders down to v 470, out to x 0.50, behind the cuffs)."""
    part = Part('hair_outer', M_HAIR)
    specs = [  # (x at the shoulder, x at the end, end height, width)
        (0.31, 0.53, 0.58, 0.030), (0.31, 0.50, 0.66, 0.026), (0.30, 0.44, 0.56, 0.028)]
    for side in (1, -1):
        for k, (x0, x1, zend, w) in enumerate(specs):
            pts = [Vector((side * (x0 - 0.04), 0.05, 1.30)),
                   Vector((side * x0, 0.08, 1.12)),
                   Vector((side * lerp(x0, x1, 0.6), 0.14, 0.86)),
                   Vector((side * x1, 0.16, zend))]

            def width(u, w=w):
                return w * (1.0 - 0.7 * smooth((u - 0.6) / 0.4))

            def thick(u):
                return 0.012

            def tag(u, v, side=side):
                return {'seg': 'hair_back', 'u': u, 'x': side * 1.0}
            _strand(part, pts, width, thick, nu=12, nv=8, tip='point', up=(side, 0, 0),
                    col=lambda u, v: C.HAIR, tagf=tag)
    return part


def hair():
    return [hair_cap(), bangs(), side_pieces(), mantle(), outer_strands()] + side_locks()


# =================================================================================================
# the hat

def _hat_profile(rho):
    """Height above the brim plane at radius fraction rho (0 apex .. 1 brim): a straight cone with a
    rounded tip (hat sheet)."""
    H = B.HAT_H
    z = H * (1.0 - rho)
    tip = 0.06
    if rho < tip:
        z -= H * 0.25 * tip * (1.0 - rho / tip) ** 2
    return z


def hat_point(rho, th, lift=0.0):
    """On the hat's top: radius fraction rho, angle th (0 her front, + toward her left), lifted off
    the surface by `lift` along the cone's normal."""
    Cc, U, Fw, L = B.hat_frame()
    R = B.HAT_R
    r = rho * R
    z = _hat_profile(rho)
    radial = Fw * math.cos(th) + L * math.sin(th)
    p = Cc + radial * r + U * z
    if lift:
        slope = B.HAT_H / R
        n = (U + radial * slope).normalized()
        p = p + n * lift
    return p


def hat():
    part = Part('hat', M_HAT_TOP)
    Cc, U, Fw, L = B.hat_frame()
    R = B.HAT_R
    nu, nv = 14, 72
    # the top (ivory): faint radial ribs every 15 deg (the sheet's straw panels)

    def col_top(u, v):
        k = (v * 24.0) % 1.0
        return C.HAT_DEEP if k < 0.05 else C.HAT

    # (UV: the radius fraction and the angle fraction, for the shader's sedge; the normals face up and
    # out, so the camera sees the top's front faces: a back face with UV2.y in 0.5..1.5 is painted as
    # the navy lining)
    grid(part, nu, nv, lambda u, v: hat_point(max(u, 0.0), v * TAU), close_v=True, pole0=True,
         col=col_top, auxf=lambda u, v: (M_HAT_TOP, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # the rim: a thin rolled edge (cream)
    rim = 0.012

    def pos_rim(u, v):
        th = v * TAU
        radial = Fw * math.cos(th) + L * math.sin(th)
        a = u * math.pi
        return Cc + radial * (R + rim * math.sin(a) * 0.6) + U * (rim * math.cos(a) - rim)

    grid(part, 4, nv, pos_rim, close_v=True, col=lambda u, v: C.HAT,
         auxf=lambda u, v: (M_HAT_TOP, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # the underside (navy), from the rim in to the head ring
    under_off = 2 * rim
    r_in = 0.235

    def pos_under(u, v):
        th = v * TAU
        rho = lerp(1.0, r_in / R, u)
        radial = Fw * math.cos(th) + L * math.sin(th)
        return Cc + radial * (rho * R) + U * (_hat_profile(rho) - under_off - 0.004 * (1 - u))

    grid(part, 8, nv, pos_under, close_v=True, col=lambda u, v: C.NAVY_LINING,
         auxf=lambda u, v: (M_HAT_UNDER, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # the head ring (straw), under the crown
    def pos_ring(u, v):
        th = v * TAU
        radial = Fw * math.cos(th) + L * math.sin(th)
        rho = r_in / R
        return Cc + radial * r_in + U * (_hat_profile(rho) - under_off - 0.06 * u)

    grid(part, 2, 36, pos_ring, close_v=True, col=lambda u, v: C.STRAW,
         auxf=lambda u, v: (M_STRAW, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    return [part] + hat_band()


def hat_band():
    """The red band: a ring round the crown, a strap down to the brim behind her left, a knot and the
    tail hanging to her back."""
    part = Part('hat_band', M_CLOTH)
    R = B.HAT_R
    ring = D['hat_ring_r']
    wfrac = D['hat_band_w'] / R
    nv = 56
    # the ring: rho from ring - w/2 .. ring + w/2, lifted a little

    def pos_ring(u, v):
        return hat_point(ring + (u - 0.5) * wfrac, v * TAU, lift=0.010 + 0.004 * math.sin(u * math.pi))
    grid(part, 3, nv, pos_ring, close_v=True, col=lambda u, v: C.RED,
         auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # two straps down the cone: one over her front-left (the front view), one to the knot behind her left
    th_t = math.radians(D['hat_tail_angle'])
    half = D['hat_band_w'] / 2.0
    for th_s in (math.radians(D['hat_strap_angle']), th_t):
        def pos_strap(u, v, th_s=th_s):
            rho = lerp(ring, 1.0, u)
            r = max(rho * R, 0.05)
            dth = (v - 0.5) * 2 * half / r
            return hat_point(rho, th_s + dth, lift=0.011 + 0.003 * math.sin(v * math.pi))
        grid(part, 10, 3, pos_strap, col=lambda u, v: C.RED, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # the knot at the brim edge, and the tail down her back
    Cc, U, Fw, L = B.hat_frame()
    radial = Fw * math.cos(th_t) + L * math.sin(th_t)
    knot = Cc + radial * (R + 0.01) + U * 0.0
    path = Path([knot + U * 0.02, knot, knot + Vector((0, 0, -0.05))], up=radial)

    def ksec(u, a):
        r = 0.035 * math.sin(math.pi * min(1.0, max(0.0, u)) * 0.85 + 0.25)
        return (r * math.cos(a), r * 1.3 * math.sin(a))
    sweep(part, path, 5, 10, ksec, col=lambda u, v: C.RED_DEEP, auxf=lambda u, v: (M_CLOTH, 0.0),
          tagf=lambda u, v: {'seg': 'hat'}, pole0=True, pole1=True)
    end_h = D['hat_tail_end']
    tw = D['hat_tail_w'] / 2.0
    out = Vector((radial.x, radial.y, 0)).normalized()
    pts = [knot + Vector((0, 0, -0.02)),
           knot + out * 0.02 + Vector((0, 0, -0.18)),
           knot + out * 0.015 + Vector((0, 0.01, -0.36)),
           Vector((knot.x + out.x * 0.03, knot.y + out.y * 0.03 + 0.02, end_h))]
    tpath = Path(pts, up=out)
    side = out.cross(Vector((0, 0, 1))).normalized()

    def pos_tail(u, v):
        p, t, n, b = tpath.at(u)
        w = tw * (0.85 + 0.15 * u)
        tw_ang = 0.5 * math.sin(u * math.pi * 1.2)
        across = (side * math.cos(tw_ang) + out * math.sin(tw_ang))
        return p + across * ((v - 0.5) * 2 * w)

    grid(part, 12, 3, pos_tail, col=lambda u, v: C.RED, auxf=lambda u, v: (M_CLOTH, 0.0),
         tagf=lambda u, v: {'seg': 'hat_tail', 'u': u})
    # the tail's cut end: a shallow V
    return [part]


# =================================================================================================
# face landmarks for the game's pixel stamps (characters/character3d.gd)
#
# The face on screen (30 px per metre): 0.336 m wide at the cheeks, so 10 px; the sheet's eyes are
# 0.109 m wide, 0.095 m tall, their centres 0.19 m apart: 3 x 3 px each, laid out
# [skin][eye eye eye][gap gap][eye eye eye][skin], the face's centre on a pixel edge (head_snap x 0).
# A landmark is where the stamp's pivot lands: an eye's outer column, middle row.
EYE_PIVOT_X = 3.5 / 30.0
CHEEK_X = 3.5 / 30.0
CHEEK_H = D['eye_h'] - 2.0 / 30.0


def face_point(z, x):
    """The head's front surface at height z (absolute) and her-left x."""
    h = z - B.CHIN_Z
    sgn = 1.0 if x >= 0 else -1.0
    lo, hi = 0.0, math.pi / 2
    # t from pi/2 (front) toward 0 (her left) or pi (her right)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        t = math.pi / 2 - sgn * mid
        if abs(head_point(h, t).x) < abs(x):
            lo = mid
        else:
            hi = mid
    return head_point(h, math.pi / 2 - sgn * 0.5 * (lo + hi))


def landmarks():
    """Face landmarks (Blender coordinates, bind pose) with a normal each."""
    L = {}

    def put(name, p, n=None):
        L[name] = (p, n if n is not None else face_normal(p))
    put('face', face_point(B.EYE_H, 0.0))
    put('eye_R', face_point(B.EYE_H, -EYE_PIVOT_X))
    put('eye_L', face_point(B.EYE_H, EYE_PIVOT_X))
    put('mouth', face_point(B.MOUTH_H, 0.0))
    put('cheek_R', face_point(CHEEK_H, -CHEEK_X))
    put('cheek_L', face_point(CHEEK_H, CHEEK_X))
    put('mark', head_point(B.HEAD_H * 0.62, math.pi / 2 - 0.85, grow=0.07), ellipsoid_normal(
        head_point(B.HEAD_H * 0.62, math.pi / 2 - 0.85)))
    put('sweat', head_point(0.26, math.pi / 2 + 1.05, grow=0.06), ellipsoid_normal(
        head_point(0.26, math.pi / 2 + 1.05)))
    return L
