"""百々かさゝぎ, round 5: body and clothes. Big clean shapes first (the lead's diagnosis of round 4: thin
body, rectangular sleeves, stiff): a short round torso, two wide white sleeves that hang as bells from
the shoulders with the hands just showing (v0.2), the white robe open over the trousers, a red bow.
Colour regions that must stay crisp at 30 px per metre are separate geometry laid on top (collar,
cord, hem bands), never vertex-colour gradients; every band is at least ~1 native px wide."""
import math
from mathutils import Vector

from c3d.surf import (Part, grid, sweep, cap, Path, interp, superellipse, smooth, lerp, mix_col,
                      M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_WOOD, M_ROPE, M_TIE)
from kasasagi import body as B
from kasasagi import palette as C
from kasasagi.design import D

TAU = 2 * math.pi
LINED = 1.0           # aux extra: the back faces show the navy lining (the shader flips them)
LINED_CREAM = 2.0     # back faces a deeper cream


def ring_point(t, X, Yd, yc, n=2.3):
    cx, sy = superellipse(t, 1.0, 1.0, n)
    return X * cx, yc - Yd * sy


# =================================================================================================
# torso (the navy kosode)

def _torso_table():
    hz, (o0, o1), sz, nb = D['hip_z'], D['obi_z'], B.SHOULDER_Z, D['neck_base']
    return [
        # z            X      Yd     yc
        (hz - 0.07,    0.124, 0.094, 0.000),
        (hz,           0.122, 0.092, 0.000),
        (o0,           0.116, 0.088, 0.000),
        (o1,           0.120, 0.088, -0.002),
        (o1 + 0.07,    0.128, 0.090, -0.004),
        (sz - 0.03,    0.136, 0.086, 0.000),
        (sz,           0.122, 0.074, 0.006),
        (sz + 0.022,   0.082, 0.058, 0.010),
        (nb + 0.012,   0.048, 0.044, 0.012),
    ]


TORSO = _torso_table()


def torso_slice(z):
    X = interp([(p[0], p[1]) for p in TORSO], z)
    Yd = interp([(p[0], p[2]) for p in TORSO], z)
    yc = interp([(p[0], p[3]) for p in TORSO], z)
    return X, Yd, yc


def torso():
    part = Part('torso', M_CLOTH)
    z0, z1 = TORSO[0][0], TORSO[-1][0]

    def pos(u, v):
        z = lerp(z0, z1, u)
        X, Yd, yc = torso_slice(z)
        x, y = ring_point(v * TAU, X, Yd, yc)
        return Vector((x, y, z))

    grid(part, 14, 32, pos, close_v=True, col=lambda u, v: C.NAVY, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': lerp(z0, z1, u)})
    return part


def torso_normal(p):
    X, Yd, yc = torso_slice(min(max(p.z, TORSO[0][0]), TORSO[-1][0]))
    n = Vector((p.x / max(X, 1e-3) ** 2, (p.y - yc) / max(Yd, 1e-3) ** 2, 0.0))
    if n.length < 1e-6:
        return Vector((0, -1, 0))
    return n.normalized()


def _band_on(part, path_pts, width, lift, base_fn, col, aux=(M_CLOTH, 0.0), tag=None, nu=12, up=None,
             thick=0.006):
    """A flat band laid along a path over a surface (`base_fn(p)`: the surface's outward normal near p)."""
    path = Path(path_pts, up=up or (0, -1, 0))
    idx = []
    for i in range(nu + 1):
        u = i / nu
        p, t, n, b = path.at(u)
        out = base_fn(p)
        side = t.cross(out).normalized()
        w = width(u) if callable(width) else width
        top = [part.add(p + out * (lift + thick) + side * (w * 0.5 * s), col(u, (s + 1) / 2) if callable(col) else col,
                        (u, (s + 1) / 2), aux, dict(tag or {}, u=u)) for s in (-1, 0, 1)]
        lo = [part.add(p + out * lift + side * (w * 0.5 * s), col(u, (s + 1) / 2) if callable(col) else col,
                       (u, (s + 1) / 2), aux, dict(tag or {}, u=u)) for s in (-1, 1)]
        idx.append((top, lo))
    for i in range(nu):
        (r0, l0), (r1, l1) = idx[i], idx[i + 1]
        for k in range(2):
            part.f.append((r0[k], r0[k + 1], r1[k + 1], r1[k]))
        part.f.append((l0[0], r0[0], r1[0], l1[0]))
        part.f.append((r0[2], l0[1], l1[1], r1[2]))
    return part


def collar():
    """The kosode's V (her left panel over her right): a white band with the red under-collar inside."""
    part = Part('collar', M_CLOTH)
    nb = D['neck_base']
    o1 = D['obi_z'][1]
    for side, z_end, over in ((1, o1 - 0.01, True), (-1, o1 + 0.05, False)):
        pts = [Vector((0.0, 0.048, nb + 0.012)), Vector((side * 0.044, 0.016, nb + 0.010)),
               Vector((side * 0.050, -0.040, nb - 0.004)),
               Vector((side * 0.010, -0.082, nb - 0.075)),
               Vector((-side * 0.032, -0.086, z_end + 0.02))]
        if not over:
            pts = pts[:4] + [Vector((-side * 0.006, -0.086, z_end))]
        _band_on(part, pts, lambda u: 0.042, 0.004 if over else 0.002, torso_normal, C.WHITE,
                 tag={'seg': 'torso'}, nu=12)
        # the red under-collar, a band inside the V
        rp = [p + Vector((-side * 0.016, -0.001, 0.0)) for p in pts[1:]]
        _band_on(part, rp, lambda u: 0.026, 0.0035 if over else 0.0015, torso_normal, C.RED,
                 tag={'seg': 'torso'}, nu=10, thick=0.004)
    return part


# =================================================================================================
# obi, cord, bow, the sash's tails

def obi():
    part = Part('obi', M_CLOTH)
    o0, o1 = D['obi_z']

    def pos(u, v):
        z = lerp(o0, o1, u)
        X, Yd, yc = torso_slice(z)
        bulge = 0.016 + 0.004 * math.sin(math.pi * u)
        x, y = ring_point(v * TAU, X + bulge, Yd + bulge, yc)
        return Vector((x, y, z))

    grid(part, 4, 32, pos, close_v=True, col=lambda u, v: C.WHITE, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': lerp(o0, o1, u)})
    cord = Part('cord', M_CLOTH)
    zc = (o0 + o1) / 2

    def cpos(u, v):
        z = lerp(zc - 0.022, zc + 0.022, u)
        X, Yd, yc = torso_slice(z)
        bulge = 0.026 + 0.003 * math.sin(math.pi * u)
        x, y = ring_point(v * TAU, X + bulge, Yd + bulge, yc)
        return Vector((x, y, z))

    grid(cord, 2, 32, cpos, close_v=True, col=lambda u, v: C.RED, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': zc})
    part.extend(cord)
    return part


def bow_at():
    o0, o1 = D['obi_z']
    zc = (o0 + o1) / 2
    if D['bow'] == 'left':
        return Vector((0.072, -0.118, zc + 0.004))
    return Vector((0.010, -0.124, zc + 0.004))


def bow():
    """The red bow: a knot and two loops (the butterfly)."""
    part = Part('bow', M_CLOTH)
    k = bow_at()
    path = Path([k + Vector((0, 0.010, 0.022)), k + Vector((0, -0.010, 0.0)), k + Vector((0, 0.010, -0.022))],
                up=(0, -1, 0))
    sweep(part, path, 4, 10, lambda u, a: (0.024 * math.cos(a), 0.022 * math.sin(a)), pole0=True, pole1=True,
          col=lambda u, v: C.RED, tagf=lambda u, v: {'seg': 'bow'})
    for ang, size, h in ((math.radians(18), 0.115, 0.074), (math.radians(162), 0.115, 0.074)):
        d = Vector((math.cos(ang), 0.0, math.sin(ang)))
        upv = Vector((-d.z, 0, d.x))
        c = k + d * size * 0.5 + Vector((0, 0.010, 0))
        lp = []
        for j in range(12):
            a = j / 12 * TAU
            r = 0.5 * (1.0 - 0.35 * math.cos(a))
            lp.append(c + d * (size * 0.5 * math.cos(a)) + upv * (h * r * math.sin(a)))
        lpath = Path(lp + [lp[0], lp[1]], up=(0, -1, 0))
        sweep(part, lpath, 24, 6, lambda u, a: (0.010 * math.cos(a), 0.026 * math.sin(a)), col=lambda u, v: C.RED,
              tagf=lambda u, v: {'seg': 'bow'})
    return part


def sash_paths():
    """The two tails from the bow (rest pose): A long one down the front to the knee, a shorter one beside it."""
    k = bow_at()
    hem = D['coat_hem']
    if D['bow'] == 'left':
        A = [k + Vector((0.012, -0.010, -0.020)), k + Vector((0.040, -0.024, -0.14)),
             k + Vector((0.070, -0.020, -0.28)), Vector((k.x + 0.092, k.y + 0.002, hem - 0.06)),
             Vector((k.x + 0.104, k.y + 0.016, hem - 0.15))]
        Bp = [k + Vector((0.004, -0.008, -0.020)), k + Vector((0.004, -0.020, -0.12)),
              k + Vector((0.016, -0.018, -0.22)), Vector((k.x + 0.024, k.y - 0.006, hem + 0.02))]
    else:
        A = [k + Vector((0.016, -0.010, -0.020)), k + Vector((0.050, -0.026, -0.16)),
             k + Vector((0.100, -0.026, -0.32)), Vector((k.x + 0.150, k.y - 0.006, hem - 0.04)),
             Vector((k.x + 0.180, k.y + 0.010, hem - 0.18))]
        Bp = [k + Vector((-0.008, -0.008, -0.020)), k + Vector((-0.010, -0.022, -0.13)),
              k + Vector((0.004, -0.022, -0.25)), Vector((k.x + 0.020, k.y - 0.010, hem + 0.04))]
    return A, Bp


def _tail(part, pts, width, chain, col):
    path = Path(pts, up=(0, -1, 0))

    def section(u, a):
        w = lerp(width * 0.55, width, smooth(u * 3.0))
        return (0.007 * math.sin(a), w * math.cos(a))

    rows = sweep(part, path, 20, 8, section, col=lambda u, v: col, auxf=lambda u, v: (M_CLOTH, 0.0),
                 tagf=lambda u, v: {'seg': 'sash', 'u': u, 'chain': chain}, flip=True)
    p, t, n, b = path.at(1.0)
    tip = part.add(p - t * 0.022, col, (1, 0.5), (M_CLOTH, 0.0), {'seg': 'sash', 'u': 1.0, 'chain': chain})
    ring = rows[-1]
    for j in range(len(ring)):
        part.f.append((tip, ring[j], ring[(j + 1) % len(ring)]))


def sash_tail():
    part = Part('sash', M_CLOTH)
    A, Bp = sash_paths()
    _tail(part, A, 0.050, 'A', C.RED)
    _tail(part, Bp, 0.044, 'B', C.RED_DEEP)
    return part


# =================================================================================================
# the white robe below the obi (haori): open at the front over the trousers, flaring to the hem

def _coat_table():
    o0 = D['obi_z'][0]
    hem = D['coat_hem']
    fl = D['coat_flare']
    hz = D['hip_z']
    return [
        # z                    X                 Yd             yc     half gap at the front (rad)
        (o0 + 0.012,           0.136,            0.104,         0.000, 0.30),
        (hz,                   0.150,            0.112,         0.004, 0.34),
        (lerp(hz, hem, 0.5),   lerp(0.15, fl, 0.62), lerp(0.112, fl * 0.66, 0.62), 0.010, 0.40),
        (hem,                  fl,               fl * 0.66,     0.016, 0.46),
    ]


COAT = _coat_table()


def coat_slice(z):
    tab = COAT[::-1]
    X = interp([(p[0], p[1]) for p in tab], z)
    Yd = interp([(p[0], p[2]) for p in tab], z)
    yc = interp([(p[0], p[3]) for p in tab], z)
    g = interp([(p[0], p[4]) for p in tab], z)
    return X, Yd, yc, g


def _peak(v, c, w):
    d = abs(v - c)
    return max(0.0, 1.0 - d / w) ** 1.3


def hem_z(v):
    """The hem along v (0 her right front edge .. 1 her left front edge). A: the ChatGPT sheet's pointed
    hems (the front corners lowest, a point at each side and at the back); B: a plain round hem."""
    hem = D['coat_hem']
    if D['hem_style'] == 'points':
        w = hem + 0.12
        w -= 0.12 * (_peak(v, 0.0, 0.08) + _peak(v, 1.0, 0.08))
        w -= 0.08 * (_peak(v, 0.24, 0.08) + _peak(v, 0.76, 0.08))
        w -= 0.10 * _peak(v, 0.5, 0.12)
        return w
    return hem + 0.02 - 0.03 * (_peak(v, 0.0, 0.1) + _peak(v, 1.0, 0.1)) + 0.012 * math.sin(math.pi * v) ** 2


def coat_point(z, v, grow=0.0):
    X, Yd, yc, g = coat_slice(z)
    t = (math.pi / 2 + g) + v * (TAU - 2 * g)
    x, y = ring_point(t, X + grow, Yd + grow, yc, n=2.2)
    return Vector((x, y, z))


def coat():
    part = Part('coat', M_CLOTH)
    z_top = COAT[0][0]
    nu, nv = 18, 64

    def pos(u, v):
        return coat_point(lerp(z_top, hem_z(v), u), v)

    def col(u, v):
        return mix_col(C.CREAM, C.CREAM_DEEP, 0.30 * smooth((u - 0.88) / 0.12))

    def tag(u, v):
        z = lerp(z_top, hem_z(v), u)
        return {'seg': 'coat', 'u': u, 'v': v, 'z': z}

    grid(part, nu, nv, pos, close_v=False, col=col, auxf=lambda u, v: (M_CLOTH, LINED_CREAM), tagf=tag)
    return part


def back_y(z):
    """The body's back surface (y, at x = 0) at height z, for the long hair to lie on."""
    best = 0.0
    if TORSO[0][0] <= z <= TORSO[-1][0]:
        X, Yd, yc = torso_slice(z)
        best = max(best, yc + Yd)
    o0, o1 = D['obi_z']
    if o0 - 0.01 <= z <= o1 + 0.01:
        X, Yd, yc = torso_slice(z)
        best = max(best, yc + Yd + 0.022)
    if D['coat_hem'] - 0.05 <= z <= COAT[0][0] + 0.01:
        X, Yd, yc, g = coat_slice(z)
        best = max(best, yc + Yd)
    if z > TORSO[-1][0]:
        best = max(best, 0.06)
    return best + 0.012


# =================================================================================================
# sleeves: wide white bells hanging from the shoulders round the hanging arms; the hands show at the
# hem (B) or at the cuff over the hanging bag (A); a navy band round the hem (the lining's edge)

def sleeve_frame(side):
    sh = Vector((B.SHOULDER.x * side, B.SHOULDER.y, B.SHOULDER.z))
    hem = D['sleeve_hem']
    out = D['sleeve_w']
    inner = 0.112
    cx = (out + inner) / 2
    rx = (out - inner) / 2
    ry = rx * 0.78
    return sh, hem, cx * side, rx, ry


def sleeve(side):
    part = Part('sleeve', M_CLOTH)
    sh, hem, cx, rx, ry = sleeve_frame(side)
    top_c = sh + Vector((side * 0.010, 0.0, 0.010))
    hem_c = Vector((cx, 0.006, hem))
    nu, nv = 18, 36
    slant = D['sleeve_slant']                          # A: the hem lower on the outside

    def pos(u, v):
        a = v * TAU
        # the bell's profile: round over the shoulder, flaring down to the hem
        f = smooth(u) ** 0.8
        c = top_c.lerp(hem_c, u)
        c.z = lerp(top_c.z, hem_c.z, u)
        r_x = lerp(0.074, rx, f ** 0.9)
        r_y = lerp(0.070, ry, f ** 0.9)
        x = c.x + r_x * math.cos(a)
        y = c.y - r_y * math.sin(a)
        z = c.z
        # the hem: slanted (A), and a little lower at the front and back than at the sides
        if u > 0.5:
            k = smooth((u - 0.5) / 0.5)
            z -= k * (slant * (0.5 + 0.5 * math.cos(a) * side))
            z -= k * 0.015 * abs(math.sin(a))
        # the top closes over the shoulder: pull the inner side in toward the body
        if u < 0.25:
            pull = (1.0 - u / 0.25)
            z += 0.03 * pull * (0.5 + 0.5 * math.cos(a) * side)
        return Vector((x, y, z))

    def col(u, v):
        return mix_col(C.CREAM, C.CREAM_DEEP, 0.0)

    def tag(u, v):
        return {'seg': 'sleeve', 'side': side, 'u': u, 'a': v * TAU}

    rows = grid(part, nu, nv, pos, close_v=True, col=col, auxf=lambda u, v: (M_CLOTH, LINED), tagf=tag, flip=side < 0)
    # the hem's navy band: a ring just inside the edge, on the outside
    band = Part('sleeve_band', M_CLOTH)

    def bpos(u, v):
        uu = lerp(0.955, 1.0, u)
        q = pos(uu, v)
        c = top_c.lerp(hem_c, uu)
        d = Vector((q.x - c.x, q.y - c.y, 0.0))
        return q + d.normalized() * 0.006

    grid(band, 2, nv, bpos, close_v=True, col=lambda u, v: C.NAVY_LINING, auxf=lambda u, v: (M_CLOTH, LINED),
         tagf=lambda u, v: tag(1.0, v), flip=side < 0)
    part.extend(band)
    # custom normals: a smooth cone (clean cel tones: lit outside, the inner side in shade)
    for i, p in enumerate(part.v):
        u = part.tag[i].get('u', 0.5)
        c = top_c.lerp(hem_c, u)
        d = Vector((p.x - c.x, p.y - c.y, 0.0))
        if d.length < 1e-5:
            d = Vector((side, 0, 0))
        part.nrm[i] = (d.normalized() + Vector((0, 0, 0.35 - 0.25 * u))).normalized()
    return part


def hand(side):
    part = Part('hand', M_SKIN)

    def m(v):
        return Vector((v.x * side, v.y, v.z))
    w = m(B.WRIST)
    tip = m(B.HAND_TIP)
    axis = (tip - w).normalized()
    path = Path([w - axis * 0.01, w + axis * 0.03, tip + axis * 0.004], up=(side, 0, 0))

    def section(u, a):
        r = 0.030 * math.sin(math.pi * min(1.0, 0.18 + u * 0.9)) + 0.006
        return (r * 0.70 * math.cos(a), r * math.sin(a))

    sweep(part, path, 8, 12, section, pole0=True, pole1=True, col=lambda u, v: C.SKIN,
          auxf=lambda u, v: (M_SKIN, 0.0), tagf=lambda u, v: {'seg': 'hand', 'side': side, 'u': u})
    return part


def arm_inner(side):
    """The arm inside the sleeve (navy kosode sleeve, seen only through the bell's opening)."""
    part = Part('arm', M_CLOTH)

    def m(v):
        return Vector((v.x * side, v.y, v.z))
    path = Path([m(B.SHOULDER), m(B.ELBOW), m(B.WRIST) + Vector((0, 0, 0.01))], up=(0, -1, 0))
    sweep(part, path, 10, 10, lambda u, a: (0.040 * math.cos(a), 0.040 * math.sin(a)),
          col=lambda u, v: C.NAVY, auxf=lambda u, v: (M_CLOTH, 0.0),
          tagf=lambda u, v: {'seg': 'arm', 'side': side, 'u': u}, flip=True)
    return part


# =================================================================================================
# trousers (lantern monpe), ankle bands, boots

def leg_points(side):
    def m(v):
        return Vector((v.x * side, v.y, v.z))
    return m(B.HIP_JOINT), m(B.KNEE), m(B.ANKLE)


def trouser(side):
    part = Part('trouser', M_CLOTH)
    hip, knee, ankle = leg_points(side)
    top = hip + Vector((-side * 0.012, 0.0, 0.08))
    a_top = ankle + Vector((0, 0, 0.045))
    path = Path([top, hip, knee, a_top + Vector((0, 0, 0.05)), a_top], up=(0, -1, 0))
    pf = D['trouser_puff']

    def section(u, a):
        r = interp([(0.0, 0.098), (0.25, 0.104), (0.55, pf * 0.94), (0.78, pf), (0.90, pf * 0.86),
                    (0.97, 0.062), (1.0, 0.048)], u)
        return (r * 0.86 * math.cos(a), r * math.sin(a))

    sweep(part, path, 20, 20, section, col=lambda u, v: C.TROUSERS,
          tagf=lambda u, v: {'seg': 'leg', 'side': side, 'u': u})
    band = Part('ankle_band', M_CLOTH)
    bpath = Path([a_top + Vector((0, 0, 0.014)), a_top + Vector((0, 0, -0.026))], up=(0, -1, 0))
    sweep(band, bpath, 2, 16, lambda u, a: (0.052 * math.cos(a), 0.052 * math.sin(a)),
          col=lambda u, v: C.WHITE, tagf=lambda u, v: {'seg': 'leg', 'side': side, 'u': 0.97})
    part.extend(band)
    return part


def foot(side):
    part = Part('foot', M_CLOTH)

    def m(v):
        return Vector((v.x * side, v.y, v.z))
    ank, ball, toe = m(B.ANKLE), m(B.BALL), m(B.TOE)
    path = Path([ank + Vector((0, 0.014, 0.05)), ank + Vector((0, 0.024, 0.0)), ank + Vector((0, 0.012, -0.05)),
                 ball + Vector((0, 0.0, 0.010)), toe + Vector((0, 0.004, 0.012))], up=(0, -1, 0))

    def section(u, a):
        w = interp([(0.0, 0.048), (0.3, 0.047), (0.55, 0.044), (0.8, 0.040), (1.0, 0.030)], u)
        h = interp([(0.0, 0.048), (0.3, 0.048), (0.55, 0.040), (0.8, 0.028), (1.0, 0.018)], u)
        return (h * math.cos(a), w * math.sin(a))

    sweep(part, path, 12, 14, section, pole1=True, col=lambda u, v: C.BOOTS,
          tagf=lambda u, v: {'seg': 'foot', 'side': side, 'u': max(0.0, (u - 0.3) / 0.7)})
    sole = Part('sole', M_CLOTH)
    cx = ank.x
    y0, y1 = ank.y + 0.055, toe.y - 0.016

    def spos(u, v):
        a = v * TAU
        cxs, sys_ = superellipse(a, 1.0, 1.0, 2.6)
        hw = 0.040 if sys_ < 0 else 0.044
        yy = (y0 + y1) / 2 - sys_ * (y0 - y1) / 2
        z = 0.020 * (1 - u)
        return Vector((cx + cxs * hw, yy, z))

    rows = grid(sole, 1, 24, spos, close_v=True, col=lambda u, v: C.SOLE,
                tagf=lambda u, v: {'seg': 'foot', 'side': side, 'u': 0.6})
    cap(sole, rows[0], Vector((cx, (y0 + y1) / 2, 0.020)), col=C.SOLE, aux=(M_CLOTH, 0.0))
    cap(sole, rows[-1], Vector((cx, (y0 + y1) / 2, 0.0)), col=C.SOLE, aux=(M_CLOTH, 0.0), flip=True)
    for i in range(len(sole.tag)):
        sole.tag[i] = {'seg': 'foot', 'side': side, 'u': 0.6}
    part.extend(sole)
    return part


def body_parts():
    parts = [torso(), collar(), coat(), obi(), bow(), sash_tail()]
    for side in (1, -1):
        parts += [sleeve(side), arm_inner(side), hand(side), trouser(side), foot(side)]
    return parts
