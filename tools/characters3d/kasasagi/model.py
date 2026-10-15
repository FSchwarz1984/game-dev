"""百々かさゝぎ: the model, built from parametric surfaces (c3d.surf). Reference: the user's 12 packs
(A_01..A_36): hime cut with blunt bangs, side locks tied with white-red-white tubes, very long
dark violet-black hair; a wide sugegasa (cream top, navy underside, a red band across); a navy
kosode with a white and red collar; a long cream haori with very wide sleeves lined in navy and
navy front bands; a white obi with a red cord bowed at her front left whose long tail hangs to
the knee; navy balloon trousers gathered at the ankle with cream bands; navy tabi and sandals.

Every function returns Parts whose vertices carry tags for the rigger:
  tag['seg']   which region (head, face, hair_bang, hair_side, hair_back, hat, torso, coat, ...)
  tag['side']  -1 right / +1 left / 0 centre, where it matters
  tag['u']     position along a strand / chain (0 root .. 1 tip)
  tag['k']     strand or panel index
"""
import math
from mathutils import Vector

from c3d.surf import (Part, grid, sweep, cap, Path, interp, superellipse, smooth, lerp, mix_col,
                      M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_WOOD, M_ROPE, M_TIE)
from kasasagi import body as B
from kasasagi import palette as C

TAU = 2 * math.pi

# =================================================================================================
# head
# h = height above the chin; per slice: half width W, front y, back y, y of the widest point
HEAD_PROFILE = [
    # h      W      yf      yb      yc
    (0.000, 0.046, -0.146, -0.120, -0.133),
    (0.014, 0.104, -0.162, -0.076, -0.108),
    (0.036, 0.150, -0.176, -0.010, -0.064),
    (0.072, 0.184, -0.188, 0.066, -0.026),
    (0.122, 0.203, -0.195, 0.132, -0.006),
    (0.186, 0.214, -0.199, 0.186, 0.002),
    (0.256, 0.220, -0.198, 0.220, 0.006),
    (0.330, 0.222, -0.190, 0.232, 0.010),
    (0.395, 0.213, -0.170, 0.226, 0.012),
    (0.445, 0.187, -0.136, 0.196, 0.016),
    (0.478, 0.140, -0.096, 0.150, 0.020),
    (0.495, 0.080, -0.050, 0.092, 0.022),
    (0.500, 0.000, 0.022, 0.022, 0.022),
]


def head_slice(h):
    W = interp([(p[0], p[1]) for p in HEAD_PROFILE], h)
    yf = interp([(p[0], p[2]) for p in HEAD_PROFILE], h)
    yb = interp([(p[0], p[3]) for p in HEAD_PROFILE], h)
    yc = interp([(p[0], p[4]) for p in HEAD_PROFILE], h)
    return W, yf, yb, yc


def head_point(h, t, grow=0.0, grow_front=None):
    """Point on the head surface at height h above the chin and angle t (0 = her left, pi/2 = front,
    pi = right, 3pi/2 = back), pushed out by `grow` metres (hair layers)."""
    W, yf, yb, yc = head_slice(h)
    gf = grow if grow_front is None else grow_front
    n_front = 2.35 if h < 0.36 else 2.1
    cx, sy = superellipse(t, 1.0, 1.0, n_front if math.sin(t) > 0 else 2.0)
    x = (W + grow) * cx
    if sy > 0:
        y = yc - (yc - yf + gf) * sy
    else:
        y = yc - (yb - yc + grow) * sy
    return Vector((x, y, B.CHIN_Z + h))


HEAD_C = Vector((0.0, 0.012, B.CHIN_Z + 0.25))     # centre of the ellipsoid that lends its normals
HEAD_R = Vector((0.215, 0.215, 0.262))


def ellipsoid_normal(p, c=HEAD_C, r=HEAD_R):
    d = p - c
    return Vector((d.x / (r.x * r.x), d.y / (r.y * r.y), d.z / (r.z * r.z))).normalized()


def head():
    part = Part('head', M_FACE)
    nu, nv = 26, 36
    # rows bunch up around the face (u -> h)
    def h_of(u):
        return B.HEAD_H * (u ** 1.0)

    def pos(u, v):
        if u <= 0.0:
            W, yf, yb, yc = head_slice(0.0)
            return Vector((0.0, yf + 0.006, B.CHIN_Z - 0.002))
        if u >= 1.0:
            return Vector((0.0, 0.022, B.CHIN_Z + B.HEAD_H))
        return head_point(h_of(u), v * TAU)

    def col(u, v):
        h = h_of(u)
        t = v * TAU
        # the underside of the jaw and the throat side take a deeper skin tone (painted, not lit)
        under = smooth((0.05 - h) / 0.05) * smooth((-math.sin(t) + 0.2) / 0.6)
        return mix_col(C.SKIN, C.SKIN_DEEP, 0.5 * under)

    grid(part, nu, nv, pos, close_v=True, pole0=True, pole1=True, col=col,
         uvf=lambda u, v: (u, v), auxf=lambda u, v: (M_FACE, 0.0),
         tagf=lambda u, v: {'seg': 'head'}, flip=True)
    # the shading of an anime face is a clean, round gradient: normals from an ellipsoid, a little of
    # the real surface kept so the chin and cheeks still turn
    for i, p in enumerate(part.v):
        n_e = ellipsoid_normal(p)
        part.nrm[i] = n_e
    return [part, neck()]


def face_point(h, x, grow=0.0):
    """The point of the head's front surface (or a layer `grow` above it) at height h and x."""
    lo, hi = (0.0, math.pi / 2) if x > 0 else (math.pi / 2, math.pi)
    for _ in range(40):
        mid = (lo + hi) / 2
        px = head_point(h, mid, grow).x
        # x falls from + to - as t runs from 0 to pi
        if px > x:
            lo = mid
        else:
            hi = mid
    return head_point(h, (lo + hi) / 2, grow)


def landmarks():
    """Face landmarks (Blender coordinates, bind pose) and the surface normal at each: the game projects
    them every frame and draws the face's pixel stamps there (characters/character3d.gd)."""
    L = {}
    def put(name, p, n=None):
        L[name] = (p, n if n is not None else ellipsoid_normal(p))
    put('face', face_point(B.EYE_H, 0.0))
    put('eye_R', face_point(B.EYE_H, -B.EYE_X))
    put('eye_L', face_point(B.EYE_H, B.EYE_X))
    # the brows ride on the bangs (drawn over the hair, the anime way)
    put('brow_R', face_point(B.BROW_H, -B.EYE_X * 0.95))
    put('brow_L', face_point(B.BROW_H, B.EYE_X * 0.95))
    put('mouth', face_point(B.MOUTH_H, 0.0))
    put('cheek_R', face_point(0.118, -0.135))
    put('cheek_L', face_point(0.118, 0.135))
    put('mark', head_point(0.40, math.pi / 2 - 0.75, grow=0.04))
    put('sweat', head_point(0.27, math.pi / 2 + 1.15, grow=0.03))
    # eye normals turn outward a little more than the face's (each eye looks its own way round)
    return L


def neck():
    part = Part('neck', M_SKIN)
    path = Path([B.NECK_BASE + Vector((0, 0, -0.05)), B.NECK_BASE, B.NECK_TOP, B.NECK_TOP + Vector((0, -0.01, 0.05))],
                up=(0, -1, 0))

    def section(u, a):
        r = 0.043 - 0.004 * u
        return (r * math.cos(a), r * 0.95 * math.sin(a))
    sweep(part, path, 6, 12, section, col=lambda u, v: C.SKIN_DEEP,
          auxf=lambda u, v: (M_SKIN, 0.0), tagf=lambda u, v: {'seg': 'neck', 'u': u})
    return part


# =================================================================================================
# hair

def _strand(part, pts, width, thick, nu, nv=10, tip='point', up=None, col=None, tagf=None,
            shape=None, aux_extra=0.0):
    """One anime hair clump: a flattened tube along a path (lens-shaped section: width across, thick
    outward). width(u), thick(u) are callables. tip: 'point' (closes to a point), 'blunt' (flat cut)."""
    path = Path(pts, up=up or (0, -1, 0))

    def section(u, a):
        w = width(u)
        th = thick(u)
        ca, sa = math.cos(a), math.sin(a)
        # lens: the outer face is rounder than the inner one
        out = th * (sa if sa > 0 else sa * 0.55)
        across = w * math.copysign(abs(ca) ** 0.85, ca)
        if shape:
            out, across = shape(u, a, out, across)
        return (out, across)

    rows = sweep(part, path, nu, nv, section, close_v=True, pole1=(tip == 'point'),
                 col=col or (lambda u, v: C.HAIR), auxf=lambda u, v: (M_HAIR, aux_extra), tagf=tagf,
                 flip=True)
    if tip == 'blunt':
        p, t, n, b = path.at(1.0)
        cap(part, rows[-1], p + t * 0.004, col=(col(1.0, 0.5) if col else C.HAIR), aux=(M_HAIR, aux_extra))
    return path


def hair_cap():
    """The hair over the skull: the head shape grown outward, from a hairline that runs low at the back
    and the sides and high at the front (the bangs come down from there)."""
    part = Part('hair_cap', M_HAIR)
    nu, nv = 14, 40

    def h_low(t):
        # phi: the angle from the front. Over the bangs the hairline is high (0.435); round the temples
        # it stays above the brows (0.335) until just in front of the ear, then drops behind it (the
        # side of the face is skin, so her profile shows a cheek and an eye, not a wall of hair), and
        # runs low round the back
        phi = abs(((t - math.pi / 2 + math.pi) % TAU) - math.pi)
        h = 0.435 - 0.10 * smooth(phi / 1.2)
        h -= 0.20 * smooth((phi - 1.45) / 0.35)
        h -= 0.03 * smooth((phi - 2.2) / 0.6)
        return h

    def pos(u, v):
        t = v * TAU
        if u >= 1.0:
            return Vector((0, 0.022, B.CHIN_Z + B.HEAD_H + 0.028))
        hl = h_low(t)
        h = lerp(hl, B.HEAD_H, u ** 0.9)
        g = 0.024 + 0.008 * smooth((h - 0.25) / 0.2)
        return head_point(min(h, 0.499), t, grow=g)

    def col(u, v):
        return mix_col(C.HAIR_DEEP, C.HAIR, smooth(u * 3.0))

    grid(part, nu, nv, pos, close_v=True, pole1=True, col=col, auxf=lambda u, v: (M_HAIR, 0.0),
         tagf=lambda u, v: {'seg': 'hair_cap', 'u': 0.0}, flip=True)
    for i, p in enumerate(part.v):
        part.nrm[i] = ellipsoid_normal(p, HEAD_C + Vector((0, 0.01, 0.02)), HEAD_R * 1.12)
    return part


def bangs():
    """Hime-cut bangs: a row of flat clumps over the forehead, cut straight just above the eyes, a touch
    longer toward the temples so they frame the face."""
    part = Part('bangs', M_HAIR)
    n = 9
    spread = 1.02                     # half the arc covered (radians either side of the front)
    for k in range(n):
        f = (k + 0.5) / n * 2 - 1     # -1 .. 1, her right .. left
        t = math.pi / 2 - f * spread
        side = abs(f)
        cut = B.BANG_CUT_H - 0.022 * side ** 2 - (0.004 if k % 2 else 0.0)
        hs = [0.488, 0.474, 0.46, 0.445, cut + 0.01, cut]
        grows = [0.028, 0.030, 0.032, 0.034, 0.037, 0.039]
        pts = [head_point(h, t, grow=g) for h, g in zip(hs, grows)]
        w_tip = 0.044 if side < 0.8 else 0.038
        out = (pts[0] - HEAD_C).normalized()

        def width(u, w_tip=w_tip):
            return lerp(0.030, w_tip, smooth(u * 1.4)) * (1.0 - 0.18 * smooth((u - 0.92) / 0.08))

        def thick(u):
            return lerp(0.012, 0.016, u)

        def tag(u, v, k=k, f=f):
            return {'seg': 'hair_bang', 'u': u, 'k': k, 'side': f}

        _strand(part, pts, width, thick, nu=8, nv=10, tip='blunt', up=out,
                col=lambda u, v: mix_col(C.HAIR, C.HAIR_DEEP, 0.35 * smooth((u - 0.85) / 0.15)), tagf=tag)
    for i, p in enumerate(part.v):
        part.nrm[i] = (ellipsoid_normal(p, HEAD_C + Vector((0, 0.0, 0.03)), HEAD_R * 1.15) * 0.75 +
                       Vector((0, -1, 0.15)).normalized() * 0.25).normalized()
    return part


SIDE_TIE_Z = 1.005


def side_locks():
    """The hime side locks: from the temples down past the jaw to the chest, cut blunt, each through a
    white-red-white tie a little below the chin."""
    parts = []
    for side in (1, -1):
        part = Part('side_lock', M_HAIR)
        # at the sides of the head, just in front of the ears: further forward they hung over her
        # cheek and hid the whole face in profile
        t = math.pi / 2 - side * 1.50
        p0 = head_point(0.42, t, grow=0.026)
        p1 = head_point(0.30, t + side * 0.02, grow=0.040)
        p2 = head_point(0.14, t + side * 0.07, grow=0.050)
        # hanging a little out from the head, so from behind they show beside the long hair
        p3 = Vector((side * 0.232, -0.040, SIDE_TIE_Z + 0.01))
        p4 = Vector((side * 0.236, -0.048, 0.93))
        p5 = Vector((side * 0.230, -0.056, 0.865))
        pts = [p0, p1, p2, p3, p4, p5]

        def width(u):
            # pinched by the tie, a little fuller below it
            w = lerp(0.036, 0.046, smooth(u * 2))
            tie_u = 0.60
            w *= 1.0 - 0.28 * math.exp(-((u - tie_u) / 0.05) ** 2)
            return w

        def thick(u):
            return 0.022 * (1.0 - 0.25 * math.exp(-((u - 0.60) / 0.05) ** 2))

        def tag(u, v, side=side):
            return {'seg': 'hair_side', 'u': u, 'side': side}

        outward = Vector((side * 1.0, -0.4, 0.0)).normalized()
        n0 = len(part.v)
        _strand(part, pts, width, thick, nu=14, nv=10, tip='blunt', up=outward,
                col=lambda u, v: C.HAIR, tagf=tag)
        for i in range(n0, len(part.v)):
            part.nrm[i] = Vector((side * 0.85, -0.5, 0.15)).normalized()
        # the tie: a short tube around the lock, white - red - white
        path = Path([Vector((side * 0.233, -0.042, SIDE_TIE_Z + 0.045)),
                     Vector((side * 0.234, -0.044, SIDE_TIE_Z - 0.035))], up=outward)

        def section(u, a):
            r = 0.034
            return (r * math.cos(a) * 1.05, r * math.sin(a) * 1.15)

        def tcol(u, v):
            return C.RED if 0.36 < u < 0.64 else C.WHITE

        sweep(part, path, 6, 12, section, col=tcol, auxf=lambda u, v: (M_TIE, 0.0),
              tagf=lambda u, v, side=side: {'seg': 'hair_side', 'u': 0.60, 'side': side})
        parts.append(part)
    return parts


BACK_CHAINS_X = [-0.17, -0.085, 0.0, 0.085, 0.17]


def coat_back_y(z):
    """y of the haori's back surface at height z (the long hair lies on it)."""
    from kasasagi.clothes import coat_slice
    X, Yd, yc, g = coat_slice(min(max(z, 0.2), 0.982))
    return yc + Yd


# The long hair in three bunches (the lead, 2026-10-15: from behind she was one dark purple column):
# left, middle and right, each shaded as its own rounded mass with the darker inner layer showing
# in the gaps; the middle one ends at the waist, the two outer ones go on to mid-thigh as two tails
# that swing apart when she walks. (centre f, half width in f, clumps, tip height, tip x)
HAIR_BUNCHES = [(-0.70, 0.24, 4, 0.30, -0.185), (0.0, 0.17, 3, 0.58, 0.0), (0.70, 0.24, 4, 0.30, 0.185)]


def _bunch_path(cf, f, l, z_end, x_end, off):
    """Points of one clump: from its root on the head, behind the shoulders, then gathered toward its
    bunch's centre line and down to the bunch's tip."""
    t = 3 * math.pi / 2 + f * 1.78
    side = abs(f)
    p0 = head_point(0.40 + 0.04 * side, t, grow=0.024)
    p1 = head_point(0.22 + 0.06 * side, t, grow=0.054 + 0.012 * (1 - side))
    z2 = B.CHIN_Z - 0.04
    x2 = f * 0.205
    y2 = max(head_point(0.05, t, grow=0.0).y + 0.05, coat_back_y(z2) * (1 - 0.55 * f * f) + off + 0.03)
    z3 = 0.80
    x3 = f * 0.232
    y3 = coat_back_y(z3) * (1 - 0.45 * f * f) + off + 0.02
    if z_end < 0.5:
        # the outer bunches: gathered below the waist into a tail
        z4 = 0.56
        x4 = x_end * 1.02 + l * 0.050
        z5 = z_end
        x5 = x_end + l * 0.010
    else:
        z4 = (z3 + z_end) / 2
        x4 = cf * 0.2 + l * 0.055
        z5 = z_end
        x5 = cf * 0.2 + l * 0.020
    y4 = coat_back_y(z4) * (1 - 0.40 * f * f) + off + 0.025
    y5 = coat_back_y(max(z5, 0.2)) * (1 - 0.40 * f * f) + off + 0.03
    return [p0, p1, Vector((x2, y2, z2)), Vector((x3, y3, z3)), Vector((x4, y4, z4)), Vector((x5, y5, z5))], t


def _bunch_centre(cf, z, x_end, z_end):
    """x of a bunch's centre line at height z (for its shading)."""
    if z_end < 0.5:
        table = [(0.30, x_end), (0.56, x_end * 1.02), (0.80, cf * 0.232), (1.02, cf * 0.205), (1.4, cf * 0.15)]
    else:
        table = [(0.40, cf * 0.2), (0.80, cf * 0.232), (1.02, cf * 0.205), (1.4, cf * 0.15)]
    return interp(table, z)


def back_hair():
    """The long hair: three bunches of clumps from the back and sides of the head, behind the
    shoulders and down her back; the middle bunch ends at the waist, the outer two hang on as two tails
    to mid-thigh. A darker inner layer behind them fills the gaps (and shows in them: the parting
    between the bunches)."""
    part = Part('back_hair', M_HAIR)
    import random
    rnd = random.Random(11)
    # the inner layer: one dark sheet of clumps, a little shorter than the tails
    for k in range(7):
        f = (k + 0.5) / 7 * 2 - 1
        cf = -0.68 if f < -0.34 else (0.68 if f > 0.34 else 0.0)
        # only behind the head and the shoulders: lower down the white robe shows between the bunches
        z_end = 0.80
        x_end = 0.17 * (1 if cf > 0 else -1) if cf else 0.0
        pts, t = _bunch_path(cf, f * 0.95, (f - cf) * 0.5, z_end, x_end, 0.012)
        pts[0] = head_point(0.30 + 0.04 * abs(f), t, grow=0.020)
        w0 = 0.074

        def width(u, w0=w0):
            return w0 * (0.82 + 0.38 * smooth(u * 2.2)) * (1.0 - 0.75 * smooth((u - 0.80) / 0.20) ** 1.3)

        def thick(u):
            return 0.030 * (1.0 - 0.45 * smooth((u - 0.78) / 0.22))

        out = Vector((math.cos(t), -math.sin(t), 0.0)).normalized()
        _strand(part, pts, width, thick, nu=18, nv=10, tip='point', up=out, col=lambda u, v: C.HAIR_DEEP,
                tagf=lambda u, v, f=f: {'seg': 'hair_back', 'u': u, 'x': f, 'inner': True}, aux_extra=0.5)
    n_inner = len(part.v)
    owners = []
    for bi, (cf, hw, n, z_end, x_end) in enumerate(HAIR_BUNCHES):
        for k in range(n):
            l = (k + 0.5) / n * 2 - 1                       # -1 .. 1 across the bunch
            f = cf + l * hw
            pts, t = _bunch_path(cf, f, l, z_end + rnd.uniform(-0.012, 0.012), x_end, 0.040)
            w0 = 0.064

            def width(u, w0=w0):
                return w0 * (0.82 + 0.38 * smooth(u * 2.2)) * (1.0 - 0.75 * smooth((u - 0.80) / 0.20) ** 1.3)

            def thick(u):
                return 0.034 * (1.0 - 0.45 * smooth((u - 0.78) / 0.22))

            out = Vector((math.cos(t), -math.sin(t), 0.0)).normalized()
            n0 = len(part.v)
            _strand(part, pts, width, thick, nu=18, nv=10, tip='point', up=out, col=lambda u, v: C.HAIR,
                    tagf=lambda u, v, f=f: {'seg': 'hair_back', 'u': u, 'x': f, 'inner': False},
                    aux_extra=0.2)
            owners.append((n0, len(part.v), cf, z_end, x_end))
    # shading: each bunch as one rounded mass round its own centre line (the bunches part in light and
    # shade like three strands); the inner layer as one sheet
    for i in range(n_inner):
        p = part.v[i]
        part.nrm[i] = Vector((p.x * 0.6, 1.0, 0.10)).normalized()
    for (i0, i1, cf, z_end, x_end) in owners:
        for i in range(i0, i1):
            p = part.v[i]
            xc = _bunch_centre(cf, p.z, x_end, z_end)
            yc = coat_back_y(min(max(p.z, 0.2), 0.982)) + 0.02
            d = Vector(((p.x - xc) * 2.4, max(p.y - yc, 0.02) * 1.0, 0.18 if p.z > 0.95 else 0.06))
            part.nrm[i] = d.normalized()
    return part


def hair():
    return [hair_cap(), bangs(), back_hair()] + side_locks()


CORD_KNOT = None


def chin_cords():
    """The hat's cords (系绳): from the head ring down behind the side locks, tied under her chin in a
    small knot; two short tails hang from it and swing (spring chain 'cord'). Crimson, a shade deeper
    than the sash, so the knot reads as a ribbon on the white collar, not as a mouth."""
    part = Part('cords', M_CLOTH)
    col = C.RED_DEEP
    knot = Vector((0.0, -0.150, B.CHIN_Z - 0.028))
    for side in (1, -1):
        # behind the side lock and the jaw's corner, then under the jaw: from above only the knot
        # and the tails show
        pts = [head_point(0.36, math.pi / 2 - side * 1.62, grow=0.03),
               head_point(0.16, math.pi / 2 - side * 1.58, grow=0.02),
               head_point(0.02, math.pi / 2 - side * 1.45, grow=0.004) + Vector((0, 0, -0.02)),
               Vector((side * 0.06, -0.09, B.CHIN_Z - 0.035)),
               knot + Vector((side * 0.02, 0.006, 0.0))]
        path = Path(pts, up=(side, 0, 0))
        sweep(part, path, 10, 6, lambda u, a: (0.012 * math.cos(a), 0.016 * math.sin(a)), col=lambda u, v: col,
              auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'head'})
    # the knot
    kp = Path([knot + Vector((-0.024, 0, 0)), knot, knot + Vector((0.024, 0, 0))], up=(0, -1, 0))
    sweep(part, kp, 4, 8, lambda u, a: (0.018 * math.cos(a), 0.017 * math.sin(a)), pole0=True, pole1=True,
          col=lambda u, v: col, auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'head'})
    # two tails
    for side in (1, -1):
        tp = Path([knot + Vector((side * 0.008, -0.004, -0.006)), knot + Vector((side * 0.022, -0.016, -0.05)),
                   knot + Vector((side * 0.03, -0.02, -0.095))], up=(0, -1, 0))
        sweep(part, tp, 6, 6, lambda u, a: (0.011 * math.cos(a), 0.016 * math.sin(a)), pole1=True,
              col=lambda u, v: col, auxf=lambda u, v: (M_CLOTH, 0.0),
              tagf=lambda u, v: {'seg': 'cord', 'u': u})
    return part


# =================================================================================================
# hat (sugegasa): built level at the seat; the hat bone carries it (and tilts it toward the camera
# in the game, docs/knowledge/24)

def hat(tilt_deg=0.0, roll_deg=0.0):
    part = Part('hat', M_HAT_TOP)
    R, Hh = B.HAT_R, B.HAT_H
    seat = B.HAT_SEAT
    # the cone sits ON the head ring (atama-wa) at the crown, so the brim comes down to the brow
    # like a real sugegasa (not a lid on top of the head)
    base_z = seat.z - 0.105

    def profile(s):
        # height of the top surface at radius fraction s (0 apex .. 1 rim): a shallow cone, the apex
        # rounded, the rim turned down a touch
        cone = (1.0 - s) ** 0.92
        apex = 0.06 * math.exp(-(s / 0.06) ** 2)
        droop = -0.025 * smooth((s - 0.85) / 0.15)
        return Hh * cone + apex * 0.3 + droop

    thick = 0.016
    nu, nv = 12, 48

    def top_pos(u, v):
        s = u
        a = v * TAU
        r = R * s
        return Vector((seat.x + r * math.cos(a), seat.y + r * math.sin(a), base_z + profile(s) + thick))

    def under_pos(u, v):
        s = 1.0 - u
        a = v * TAU
        r = R * s
        return Vector((seat.x + r * math.cos(a), seat.y + r * math.sin(a), base_z + profile(s) - 0.004))

    top = grid(part, nu, nv, top_pos, close_v=True, pole0=True,
               col=lambda u, v: C.HAT, uvf=lambda u, v: (u, v), auxf=lambda u, v: (M_HAT_TOP, 0.0),
               tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # rim edge band between the top and the underside
    rim_top = top[-1]
    under_rows = grid(part, nu, nv, under_pos, close_v=True, pole1=True,
                      col=lambda u, v: C.NAVY, uvf=lambda u, v: (1.0 - u, v),
                      auxf=lambda u, v: (M_HAT_UNDER, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    rim_under = under_rows[0]
    for j in range(nv):
        j1 = (j + 1) % nv
        part.f.append((rim_top[j], rim_top[j1], rim_under[j1], rim_under[j]))
    # the rim edge reads as the cream edge (top colour), its vertices are shared
    # the head ring under the hat
    ring = Part('hat_ring', M_HAT_UNDER)
    path = Path([seat + Vector((0, 0, 0.035)), seat + Vector((0, 0, -0.035))], up=(0, -1, 0))

    def section(u, a):
        r = 0.120 - 0.012 * u
        return (r * math.cos(a), r * math.sin(a))

    sweep(ring, path, 2, 20, section, col=lambda u, v: C.NAVY, auxf=lambda u, v: (M_HAT_UNDER, 0.0),
          tagf=lambda u, v: {'seg': 'hat'})
    part.extend(ring)
    if tilt_deg or roll_deg:
        # previews only (the game tilts the hat bone toward the camera, HatTiltModifier): the top
        # turned back by -tilt_deg (Blender X; negative = away from a front camera) and to the
        # screen's right by roll_deg
        T, r = math.radians(-tilt_deg), math.radians(roll_deg)
        up = Vector((math.sin(r), math.cos(r) * math.sin(T), math.cos(r) * math.cos(T)))
        rot = Vector((0, 0, 1)).rotation_difference(up).to_matrix().to_4x4()
        part.transform(lambda p: seat + (rot @ (p - seat)))
    return part
