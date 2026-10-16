"""百々かさゝぎ, round 5: head, face plate, hair and hat, from parametric surfaces (c3d.surf).

Design (docs/knowledge/24 §3, design.py): a big round cranium under the hat and a small face plate
low on the head, wider than tall (about 11 x 6 native px on screen); thick hime-cut bangs that end on
the eyes' top row (the brows never show, decision-log G5R3-8); side locks framing the cheeks, tied
white-red-white; the long hair as one sheet down her back; a wide sugegasa worn tipped back so its
white top frames the face from above (the game tips it: hat_tilt_modifier.gd).

Every function returns Parts whose vertices carry tags for the rigger:
  tag['seg']   region (head, hair_cap, hair_bang, hair_side, hair_back, hat, ...)
  tag['side']  -1 her right / +1 her left / 0 centre
  tag['u']     position along a strand / chain (0 root .. 1 tip)
"""
import math
from mathutils import Vector

from c3d.surf import (Part, grid, sweep, cap, Path, interp, superellipse, smooth, lerp, mix_col,
                      M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_WOOD, M_ROPE, M_TIE)
from kasasagi import body as B
from kasasagi import palette as C
from kasasagi.design import D

TAU = 2 * math.pi

# =================================================================================================
# head: per height h above the chin, a slice with half width W, front distance F and back distance K
# from the head's axis (y = HEAD_YC); F, K > 0 forward / backward. The face's half (front) is a
# squarer superellipse: a near-vertical plate, so the face keeps its height on screen.


def _head_table():
    fw, fy = B.FACE_W, B.FACE_Y
    cw, cb, hh = D['cranium_w'], D['cranium_back'], B.HEAD_H
    t = [
        # h      W              F              K
        (0.000, 0.040,         fy - 0.044,    -0.100),
        (0.016, 0.092,         fy - 0.020,    -0.040),
        (0.042, 0.136,         fy - 0.007,     0.020),
        (0.080, fw - 0.016,    fy,             0.085),
        (0.130, fw - 0.003,    fy,             0.135),
        (0.190, fw,            fy,             0.172),
        (0.250, fw + 0.010,    fy - 0.002,     0.198),
    ]
    h0 = 0.25
    for s, w, f, k in ((0.22, 0.5 * (fw + cw) + 0.014, fy - 0.010, cb - 0.006),
                       (0.46, cw, fy - 0.026, cb),
                       (0.66, cw - 0.006, fy - 0.048, cb - 0.008),
                       (0.80, cw * 0.88, fy - 0.082, cb - 0.036),
                       (0.90, cw * 0.70, fy - 0.118, cb - 0.078),
                       (0.96, cw * 0.46, fy - 0.158, cb - 0.132),
                       (1.00, 0.0, 0.0, 0.0)):
        t.append((h0 + (hh - h0) * s, w, f, k))
    return t


HEAD_TABLE = _head_table()


def head_slice(h):
    W = interp([(p[0], p[1]) for p in HEAD_TABLE], h)
    F = interp([(p[0], p[2]) for p in HEAD_TABLE], h)
    K = interp([(p[0], p[3]) for p in HEAD_TABLE], h)
    return W, F, K


def _n_front(h):
    # the face plate (flat front, rounded corners) blends into the round cranium
    return lerp(3.2, 2.15, smooth((h - 0.24) / 0.12))


def head_point(h, t, grow=0.0, grow_front=None):
    """The head's surface at height h above the chin and angle t (0 her left, pi/2 front, pi her right,
    3pi/2 back), pushed out by `grow` (hair layers; `grow_front` for the front half)."""
    h = min(max(h, 0.0), B.HEAD_H)
    W, F, K = head_slice(h)
    gf = grow if grow_front is None else grow_front
    c, s = math.cos(t), math.sin(t)
    if s >= 0:
        e = 2.0 / _n_front(h)
        x = (W + gf) * math.copysign(abs(c) ** e, c)
        y = B.HEAD_YC - (F + gf) * (s ** e)
    else:
        e = 2.0 / 2.05
        x = (W + grow) * math.copysign(abs(c) ** e, c)
        y = B.HEAD_YC + (K + grow) * ((-s) ** e)
    return Vector((x, y, B.CHIN_Z + h))


HEAD_C = Vector((0.0, B.HEAD_YC + 0.01, B.CHIN_Z + 0.24))
HEAD_R = Vector((0.20, 0.20, 0.27))


def ellipsoid_normal(p, c=HEAD_C, r=HEAD_R):
    d = p - c
    return Vector((d.x / (r.x * r.x), d.y / (r.y * r.y), d.z / (r.z * r.z))).normalized()


def face_normal(p):
    """The face's normals: mostly forward, turning toward the cheeks (clean, one-tone face; the stamps'
    facing tests read the same field)."""
    h = p.z - B.CHIN_Z
    W, F, K = head_slice(min(max(h, 0.0), B.HEAD_H))
    xs = p.x / max(W, 1e-3)
    n = Vector((0.85 * xs, -1.0, 0.25 * (h - 0.13) / 0.13))
    return n.normalized()


def head():
    part = Part('head', M_FACE)
    nu, nv = 30, 40

    def h_of(u):
        return B.HEAD_H * u

    def pos(u, v):
        if u <= 0.0:
            return Vector((0.0, B.HEAD_YC - head_slice(0.0)[1] + 0.004, B.CHIN_Z - 0.002))
        if u >= 1.0:
            return Vector((0.0, B.HEAD_YC, B.CHIN_Z + B.HEAD_H))
        return head_point(h_of(u), v * TAU)

    def col(u, v):
        h = h_of(u)
        t = v * TAU
        # the jaw's underside and the throat side: a deeper skin, painted
        under = smooth((0.03 - h) / 0.03) * smooth((-math.sin(t) + 0.35) / 0.6)
        return mix_col(C.SKIN, C.SKIN_DEEP, 0.85 * under)

    grid(part, nu, nv, pos, close_v=True, pole0=True, pole1=True, col=col,
         uvf=lambda u, v: (u, v), auxf=lambda u, v: (M_FACE, 0.0),
         tagf=lambda u, v: {'seg': 'head'}, flip=True)
    for i, p in enumerate(part.v):
        h = p.z - B.CHIN_Z
        if h < 0.30 and p.y < B.HEAD_YC - 0.05:
            part.nrm[i] = face_normal(p)
        else:
            part.nrm[i] = ellipsoid_normal(p)
    return [part, neck()]


def face_point(h, x, grow=0.0):
    """The point of the front surface (or a layer `grow` above it) at height h and lateral x."""
    lo, hi = (0.0, math.pi / 2) if x > 0 else (math.pi / 2, math.pi)
    for _ in range(48):
        mid = (lo + hi) / 2
        px = head_point(h, mid, grow).x
        if px > x:
            lo = mid
        else:
            hi = mid
    return head_point(h, (lo + hi) / 2, grow)


# the eyes' landmarks are their OUTER columns (the stamp's pivot): 3 px from the face's centre column,
# so with 2 px eyes there are 3 px between them (the head sits on a pixel centre: head_snap_modifier.gd)
EYE_PIVOT_X = 3.0 / 30.0


def landmarks():
    """Face landmarks (Blender coordinates, bind pose) with a normal each: the game projects them every
    frame and draws the face's pixel stamps there (characters/character3d.gd)."""
    L = {}

    def put(name, p, n=None):
        L[name] = (p, n if n is not None else face_normal(p))
    put('face', face_point(B.EYE_H, 0.0))
    put('eye_R', face_point(B.EYE_H, -EYE_PIVOT_X))
    put('eye_L', face_point(B.EYE_H, EYE_PIVOT_X))
    put('mouth', face_point(B.MOUTH_H, 0.0))
    put('cheek_R', face_point(D['cheek_h'], -D['cheek_x']))
    put('cheek_L', face_point(D['cheek_h'], D['cheek_x']))
    # marks drawn over the hair or the hat: the anger vein up on her right temple, the sweat drop
    put('mark', head_point(B.HEAD_H * 0.62, math.pi / 2 - 0.85, grow=0.06), ellipsoid_normal(
        head_point(B.HEAD_H * 0.62, math.pi / 2 - 0.85)))
    put('sweat', head_point(0.26, math.pi / 2 + 1.05, grow=0.05), ellipsoid_normal(
        head_point(0.26, math.pi / 2 + 1.05)))
    return L


def neck():
    part = Part('neck', M_SKIN)
    path = Path([B.NECK_BASE + Vector((0, 0, -0.05)), B.NECK_BASE, B.NECK_TOP, B.NECK_TOP + Vector((0, -0.01, 0.05))],
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
            uvf=None):
    """One hair clump: a flattened tube along a path (lens section: `width` across, `thick` outward)."""
    path = Path(pts, up=up or (0, -1, 0))

    def section(u, a):
        w = width(u)
        th = thick(u)
        ca, sa = math.cos(a), math.sin(a)
        out = th * (sa if sa > 0 else sa * 0.55)
        across = w * math.copysign(abs(ca) ** 0.85, ca)
        return (out, across)

    rows = sweep(part, path, nu, nv, section, close_v=True, pole1=(tip == 'point'),
                 col=col or (lambda u, v: C.HAIR), auxf=lambda u, v: (M_HAIR, aux_extra), tagf=tagf,
                 uvf=uvf, flip=True)
    if tip == 'blunt':
        p, t, n, b = path.at(1.0)
        cap(part, rows[-1], p + t * 0.004, col=(col(1.0, 0.5) if col else C.HAIR), aux=(M_HAIR, aux_extra))
    return path


def _hairline(t):
    """Height (above the chin) where the hair cap ends, by angle round the head: high over the face
    (the bangs hang from there), down over the temples and ears to the jaw, low at the nape."""
    phi = abs(((t - math.pi / 2 + math.pi) % TAU) - math.pi)      # 0 front .. pi back
    h = B.BANG_CUT_H + 0.07
    h -= (B.BANG_CUT_H + 0.07 - 0.10) * smooth((phi - 0.95) / 0.45)   # the sides: down to the jaw
    h -= 0.10 * smooth((phi - 1.9) / 0.6)                              # the back: to the nape
    return h


def hair_cap():
    """The hair over the cranium, grown out a little; the bangs, side locks and the long sheet hang from it."""
    part = Part('hair_cap', M_HAIR)
    nu, nv = 16, 48

    def pos(u, v):
        t = v * TAU
        if u >= 1.0:
            return Vector((0, B.HEAD_YC, B.CHIN_Z + B.HEAD_H + 0.026))
        hl = _hairline(t)
        h = lerp(hl, B.HEAD_H, u ** 0.85)
        g = 0.022 + 0.006 * smooth((h - 0.25) / 0.2)
        return head_point(min(h, B.HEAD_H - 0.001), t, grow=g)

    grid(part, nu, nv, pos, close_v=True, pole1=True, col=lambda u, v: C.HAIR,
         auxf=lambda u, v: (M_HAIR, 0.0), tagf=lambda u, v: {'seg': 'hair_cap', 'u': 0.0}, flip=True)
    for i, p in enumerate(part.v):
        part.nrm[i] = ellipsoid_normal(p, HEAD_C + Vector((0, 0.0, 0.04)), HEAD_R * 1.1)
    return part


def bangs():
    """Thick hime-cut bangs: a curtain of flat clumps over the forehead, cut straight across on the eyes'
    top row (G5R3-8: the brows never show); the outer clumps a little longer, rounding the face's top
    corners into the side locks."""
    part = Part('bangs', M_HAIR)
    n = 11
    spread = 1.12
    for k in range(n):
        f = (k + 0.5) / n * 2 - 1           # -1 her right .. 1 her left
        t = math.pi / 2 - f * spread
        side = abs(f)
        cut = B.BANG_CUT_H - 0.030 * smooth((side - 0.62) / 0.38)
        hs = [B.HEAD_H - 0.07, B.HEAD_H - 0.14, 0.36, 0.30, cut + 0.03, cut]
        grows = [0.030, 0.032, 0.030, 0.026, 0.024, 0.024]
        pts = [head_point(h, t, grow=g) for h, g in zip(hs, grows)]
        w_tip = 0.050 if side < 0.8 else 0.044
        out = (pts[-2] - HEAD_C).normalized()

        def width(u, w_tip=w_tip):
            return lerp(0.034, w_tip, smooth(u * 1.3))

        def thick(u):
            return lerp(0.010, 0.016, u)

        def tag(u, v, k=k, f=f):
            return {'seg': 'hair_bang', 'u': u, 'k': k, 'side': f}

        _strand(part, pts, width, thick, nu=10, nv=10, tip='blunt', up=out,
                col=lambda u, v: C.HAIR, tagf=tag)
    for i, p in enumerate(part.v):
        part.nrm[i] = (ellipsoid_normal(p, HEAD_C + Vector((0, 0.0, 0.05)), HEAD_R * 1.15) * 0.6 +
                       Vector((0, -1, 0.25)).normalized() * 0.4).normalized()
    return part


def side_lock_points(side):
    fw = B.FACE_W
    tie_h, end_h = D['lock_tie_h'], D['lock_end_h']
    t = math.pi / 2 - side * 1.28
    return [head_point(0.34, t, grow=0.024),
            Vector((side * (fw + 0.032), B.HEAD_YC - 0.118, B.CHIN_Z + 0.20)),
            Vector((side * (fw + 0.030), B.HEAD_YC - 0.112, B.CHIN_Z + 0.06)),
            Vector((side * (fw + 0.024), -0.094, B.CHIN_Z + tie_h + 0.05)),
            Vector((side * (fw + 0.020), -0.090, B.CHIN_Z + tie_h)),
            Vector((side * (fw + 0.018), -0.086, B.CHIN_Z + end_h))]


def side_locks():
    """The hime side locks: from the temples down past the cheeks (just outside the face's outline, so
    the round cheeks show against them) to the tie, white-red-white, and a short blunt end."""
    parts = []
    fw = B.FACE_W
    tie_h, end_h = D['lock_tie_h'], D['lock_end_h']
    for side in (1, -1):
        part = Part('side_lock', M_HAIR)
        pts = side_lock_points(side)
        p0, p1, p2, p3, p4, p5 = pts
        L = Path(pts).length
        tie_u = (Path(pts[:5]).length) / L

        def width(u, tie_u=tie_u):
            w = lerp(0.040, 0.034, smooth(u))
            w *= 1.0 - 0.25 * math.exp(-((u - tie_u) / 0.05) ** 2)
            return w

        def thick(u, tie_u=tie_u):
            return 0.024 * (1.0 - 0.25 * math.exp(-((u - tie_u) / 0.05) ** 2))

        def tag(u, v, side=side):
            return {'seg': 'hair_side', 'u': u, 'side': side}

        outward = Vector((side * 1.0, -0.35, 0.0)).normalized()
        n0 = len(part.v)
        _strand(part, pts, width, thick, nu=16, nv=10, tip='blunt', up=outward,
                col=lambda u, v: C.HAIR, tagf=tag)
        for i in range(n0, len(part.v)):
            part.nrm[i] = Vector((side * 0.8, -0.55, 0.12)).normalized()
        # the tie: white - red - white, three native rows
        tc = p4 + Vector((0, 0, 0.012))
        path = Path([tc + Vector((0, -0.002, 0.050)), tc + Vector((0, 0.002, -0.050))], up=outward)

        def section(u, a):
            r = 0.031
            return (r * math.cos(a) * 1.05, r * math.sin(a) * 1.10)

        def tcol(u, v):
            return C.RED if 0.34 < u < 0.66 else C.WHITE

        sweep(part, path, 9, 12, section, col=tcol, auxf=lambda u, v: (M_TIE, 0.0),
              tagf=lambda u, v, side=side, tie_u=tie_u: {'seg': 'hair_side', 'u': tie_u, 'side': side})
        parts.append(part)
    return parts


SHEET_TOP_H = 0.36          # where the long hair's sheet leaves the cranium (above the chin)
SHEET_THICK = 0.034


def _back_y(z):
    from kasasagi.clothes import back_y
    return back_y(z)


def sheet_frame(u):
    """The long hair's sheet at u (0 where it leaves the cranium .. 1 its end): height z, the arc's centre
    y, half width, wrap angle and depth. Round the head it follows the cranium; down the back it lies
    on the body (clothes.back_y)."""
    z_top = B.CHIN_Z + SHEET_TOP_H
    z_end = D['back_hair_end']
    W0 = D['back_hair_w']
    z = lerp(z_top, z_end, u)
    h = z - B.CHIN_Z
    W, F, K = head_slice(min(max(h, 0.0), B.HEAD_H))
    K = max(K, 0.10)
    hf = (B.HEAD_YC + K * 0.35, max(W, 0.20) + 0.026, lerp(1.28, 1.08, smooth((SHEET_TOP_H - h) / SHEET_TOP_H)),
          K * 0.65 + 0.03)
    by = _back_y(z)
    bf = (by - 0.04, W0 * (1.0 - 0.10 * smooth((-h - 0.05) / 0.5)), 0.95, 0.07)
    k = smooth((h + 0.14) / 0.18)                 # 1 round the head, 0 down the back
    yc, hw, wrap, depth = (lerp(bf[i], hf[i], k) for i in range(4))
    return z, yc, hw, wrap, depth


def sheet_point(u, x, outer=True):
    """A point of the sheet: x in [-1, 1] across (her right .. her left); outer: the visible face."""
    z, yc, hw, wrap, depth = sheet_frame(u)
    a = x * wrap
    px = hw * math.sin(a) / math.sin(wrap)
    py = yc + depth * math.cos(a) + (SHEET_THICK if outer else 0.0) * (0.6 + 0.4 * math.cos(a))
    return Vector((px, py, z))


def sheet_bottom_u(x):
    """The end is rounded: the sides finish higher than the middle."""
    return 1.0 - 0.13 * (abs(x) ** 2.2) * (1.0 if D['back_hair_end'] > 0.5 else 0.6)


def back_hair():
    """The long hair as one sheet down her back (the v0.2 sprite's back view): from the back of the
    cranium over the shoulders and down, wrapping round her back, its end rounded.
    UV: x across the sheet (0 her right .. 1 her left), y down it (the shader paints strand highlights
    in vertical lines across x)."""
    part = Part('back_hair', M_HAIR)
    nu, nv = 34, 26
    rows_out, rows_in = [], []
    for i in range(nu + 1):
        r_o, r_i = [], []
        for j in range(nv + 1):
            x = j / nv * 2 - 1
            u = i / nu * sheet_bottom_u(x)
            uu = (x + 1) / 2
            tag = {'seg': 'hair_back', 'u': u, 'x': x}
            r_o.append(part.add(sheet_point(u, x, True), C.HAIR, (uu, u), (M_HAIR, 0.2), tag))
            r_i.append(part.add(sheet_point(u, x, False), C.HAIR_DEEP, (uu, u), (M_HAIR, 0.5), dict(tag)))
        rows_out.append(r_o)
        rows_in.append(r_i)
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = rows_out[i][j], rows_out[i][j + 1], rows_out[i + 1][j + 1], rows_out[i + 1][j]
            part.f.append((a, b, c, d))                        # the outer face looks back (+y)
            a, b, c, d = rows_in[i][j], rows_in[i][j + 1], rows_in[i + 1][j + 1], rows_in[i + 1][j]
            part.f.append((a, d, c, b))
    # close the edges (sides and the end): a strip between the outer and inner faces
    for i in range(nu):
        for j in (0, nv):
            o0, o1, i0, i1 = rows_out[i][j], rows_out[i + 1][j], rows_in[i][j], rows_in[i + 1][j]
            part.f.append((o0, o1, i1, i0) if j == 0 else (o0, i0, i1, o1))
    for j in range(nv):
        o0, o1, i0, i1 = rows_out[nu][j], rows_out[nu][j + 1], rows_in[nu][j], rows_in[nu][j + 1]
        part.f.append((o0, o1, i1, i0))
    # shading: one rounded mass (normals from the arc's centre, up a little toward the head)
    z_top = B.CHIN_Z + SHEET_TOP_H
    z_end = D['back_hair_end']
    for i, p in enumerate(part.v):
        u = min(max((z_top - p.z) / max(z_top - z_end, 1e-3), 0.0), 1.0)
        zz, yc, hw, wrap, depth = sheet_frame(u)
        d = Vector((p.x / max(hw, 0.05) * 0.9, 1.0, 0.25 * smooth((p.z - B.CHIN_Z + 0.05) / 0.3)))
        part.nrm[i] = d.normalized()
    return part


def hair():
    return [hair_cap(), bangs(), back_hair()] + side_locks()


# =================================================================================================
# hat (sugegasa): built level, its seat on the crown; the hat bone carries it, the game tips it
# (hat_tilt_modifier.gd: back, away from the camera, so the white top frames the face)

def hat_top_z(s):
    """Height of the top surface above the brim plane at radius fraction s (0 apex .. 1 rim): a shallow
    cone, the apex rounded, the rim turned down a touch."""
    Hh = B.HAT_H
    cone = (1.0 - s) ** 0.95
    apex = -0.10 * Hh * math.exp(-(s / 0.07) ** 2)
    droop = -0.018 * smooth((s - 0.86) / 0.14)
    return Hh * cone + apex + droop


def hat(tilt_deg=0.0, roll_deg=0.0):
    part = Part('hat', M_HAT_TOP)
    R = B.HAT_R
    seat = B.HAT_SEAT
    base_z = seat.z - B.HAT_SINK
    thick = 0.016
    rim = 0.026                      # the rim's edge band: the navy line under the white (v0.2)
    nu, nv = 14, 64

    def top_pos(u, v):
        a = v * TAU
        r = R * u
        return Vector((seat.x + r * math.cos(a), seat.y + r * math.sin(a), base_z + hat_top_z(u) + thick))

    def under_pos(u, v):
        s = 1.0 - u
        a = v * TAU
        r = R * s * 0.995
        return Vector((seat.x + r * math.cos(a), seat.y + r * math.sin(a), base_z + hat_top_z(s) - rim + 0.004))

    top = grid(part, nu, nv, top_pos, close_v=True, pole0=True,
               col=lambda u, v: C.HAT, uvf=lambda u, v: (u, v), auxf=lambda u, v: (M_HAT_TOP, 0.0),
               tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    under_rows = grid(part, nu, nv, under_pos, close_v=True, pole1=True,
                      col=lambda u, v: C.NAVY_LINING, uvf=lambda u, v: (1.0 - u, v),
                      auxf=lambda u, v: (M_HAT_UNDER, 0.0), tagf=lambda u, v: {'seg': 'hat'}, flip=True)
    # the rim band: its own vertices (navy), from the top's edge down to the underside's edge
    rim_top_ring = top[-1]
    rim_under_ring = under_rows[0]
    ra = [part.add(part.v[rim_top_ring[j]].copy(), C.NAVY_LINING, (1.0, j / nv),
                   (M_HAT_UNDER, 0.0), {'seg': 'hat'}) for j in range(nv)]
    rb = [part.add(part.v[rim_under_ring[j]].copy(), C.NAVY_LINING, (1.0, j / nv), (M_HAT_UNDER, 0.0), {'seg': 'hat'})
          for j in range(nv)]
    for j in range(nv):
        j1 = (j + 1) % nv
        part.f.append((ra[j], rb[j], rb[j1], ra[j1]))          # facing out
    for i, p in enumerate(part.v):
        if part.aux[i][0] == M_HAT_UNDER and abs((p - seat).to_2d().length - R) < 0.02:
            part.nrm[i] = Vector(((p - seat).x, (p - seat).y, 0.0)).normalized()
    # the head ring inside (atama-wa): the hat stands on it
    ring = Part('hat_ring', M_HAT_UNDER)
    path = Path([seat + Vector((0, 0, -0.012)), seat + Vector((0, 0, -0.07))], up=(0, -1, 0))

    def section(u, a):
        r = 0.105 + 0.025 * u
        return (r * math.cos(a), r * math.sin(a))

    sweep(ring, path, 2, 20, section, col=lambda u, v: C.NAVY_LINING, auxf=lambda u, v: (M_HAT_UNDER, 0.0),
          tagf=lambda u, v: {'seg': 'hat'})
    part.extend(ring)
    part.extend(hat_band())
    if tilt_deg or roll_deg:
        # previews only (the game tilts the hat bone): the top turned back by tilt_deg
        T, r = math.radians(-tilt_deg), math.radians(roll_deg)
        up = Vector((math.sin(r), math.cos(r) * math.sin(T), math.cos(r) * math.cos(T)))
        rot = Vector((0, 0, 1)).rotation_difference(up).to_matrix().to_4x4()
        part.transform(lambda p: seat + (rot @ (p - seat)))
    return part


def _on_top(s, a, lift):
    """A point on the hat's top surface at radius fraction s and angle a (0 her left, pi/2 front),
    lifted off it by `lift` along the surface normal (roughly up)."""
    seat = B.HAT_SEAT
    base_z = seat.z - B.HAT_SINK
    R = B.HAT_R
    r = R * s
    p = Vector((seat.x + r * math.cos(a), seat.y - r * math.sin(a), base_z + hat_top_z(s) + 0.016))
    slope = (hat_top_z(max(s - 0.01, 0.0)) - hat_top_z(min(s + 0.01, 1.0))) / (0.02 * R)
    n = Vector((math.cos(a) * slope, -math.sin(a) * slope, 1.0)).normalized()
    return p + n * lift


def hat_band():
    """The red on the hat. B: a stripe from the apex down to the brim, on its front left (the sprite's
    right-hand stripe). A: the ChatGPT sheet's ribbon round the crown and a band across the top."""
    part = Part('hat_band', M_CLOTH)
    style = D['hat_band']
    lift = 0.006
    if style == 'stripe':
        a0 = math.pi / 2 - 0.62                 # front, toward her left (the screen's right)
        w = 0.070
        n = 18
        rows = []
        for i in range(n + 1):
            s = lerp(0.10, 0.995, i / n)
            p = _on_top(s, a0, lift)
            # across: perpendicular to the radial line, in the surface
            across = Vector((-math.sin(a0), -math.cos(a0), 0.0))
            ww = w * lerp(0.55, 1.0, smooth(s / 0.5))
            rows.append([part.add(p + across * (ww * (k - 1)), C.RED, (s, k / 2), (M_CLOTH, 0.0),
                                  {'seg': 'hat'}) for k in range(3)])
        for i in range(n):
            for k in range(2):
                part.f.append((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
    else:
        # the ribbon round the crown (s 0.26..0.36), and a band across the top through the apex
        n = 48
        s0, s1 = 0.24, 0.35
        r0 = [part.add(_on_top(s0, j / n * TAU, lift), C.RED, (0, j / n), (M_CLOTH, 0.0), {'seg': 'hat'}) for j in range(n)]
        r1 = [part.add(_on_top(s1, j / n * TAU, lift), C.RED, (1, j / n), (M_CLOTH, 0.0), {'seg': 'hat'}) for j in range(n)]
        for j in range(n):
            j1 = (j + 1) % n
            part.f.append((r0[j], r0[j1], r1[j1], r1[j]))
        a0 = math.pi / 2 - 0.70
        w = 0.062
        for sgn in (1, -1):
            a = a0 if sgn > 0 else a0 + math.pi
            rows = []
            m = 12
            for i in range(m + 1):
                s = lerp(0.35, 0.995, i / m)
                p = _on_top(s, a, lift * 0.8)
                across = Vector((-math.sin(a), -math.cos(a), 0.0))
                rows.append([part.add(p + across * (w * (k - 1)), C.RED_DEEP if sgn < 0 else C.RED, (s, k / 2),
                                      (M_CLOTH, 0.0), {'seg': 'hat'}) for k in range(3)])
            for i in range(m):
                for k in range(2):
                    part.f.append((rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]))
    for i in range(len(part.v)):
        part.nrm[i] = Vector((0, 0, 1))
    return part
