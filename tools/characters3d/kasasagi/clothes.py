"""百々かさゝぎ's body and clothes. Colour regions that must stay crisp at 30 px per metre (collar,
front bands, cuffs, the obi's cord, ankle bands) are separate pieces of geometry laid on top, like
sewn bands, never vertex-colour gradients; every band is at least ~1.1 native px (3.5 cm) wide."""
import math
from mathutils import Vector

from c3d.surf import (Part, grid, sweep, cap, Path, interp, superellipse, smooth, lerp, mix_col,
                      M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_WOOD, M_ROPE, M_TIE)
from kasasagi import body as B
from kasasagi import palette as C

TAU = 2 * math.pi
LINED = 1.0           # aux extra: the back faces show the navy lining (the shader flips them)
LINED_CREAM = 2.0     # back faces a deeper cream


def ring_point(t, X, Yd, yc, n=2.3):
    cx, sy = superellipse(t, 1.0, 1.0, n)
    return X * cx, yc - Yd * sy


# =================================================================================================
# torso (the navy kosode) and its collar

TORSO = [
    # z      X      Yd     yc
    (0.585, 0.122, 0.088, 0.000),
    (0.660, 0.112, 0.081, 0.000),
    (0.740, 0.104, 0.077, 0.000),
    (0.820, 0.113, 0.080, -0.004),
    (0.885, 0.126, 0.081, -0.002),
    (0.925, 0.131, 0.076, 0.004),
    (0.950, 0.112, 0.062, 0.010),
    (0.968, 0.072, 0.052, 0.012),
    (0.978, 0.050, 0.046, 0.013),
]


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

    grid(part, 12, 28, pos, close_v=True, col=lambda u, v: C.NAVY, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': lerp(z0, z1, u)})
    return part


def _band_on(part, path_pts, width, lift, base_fn, col, aux=(M_CLOTH, 0.0), tag=None, nu=12, up=None,
             thick=0.006):
    """A flat band laid along a path over a surface: `base_fn(p)` returns the surface normal near p
    (the band's outward side); the band is `width` wide, raised by `lift`, a little thick."""
    path = Path(path_pts, up=up or (0, -1, 0))
    rows_out, rows_in = [], []
    pts_out, pts_in = [], []
    for i in range(nu + 1):
        u = i / nu
        p, t, n, b = path.at(u)
        out = base_fn(p)
        side = t.cross(out).normalized()
        w = width(u) if callable(width) else width
        for s in (-1, 1):
            pass
        pts_out.append([p + out * (lift + thick) + side * (w * 0.5 * s) for s in (-1, 0, 1)])
        pts_in.append([p + out * lift + side * (w * 0.5 * s) for s in (-1, 1)])
    # top surface (3 across, so the band is slightly domed) + two side walls
    idx = []
    for i in range(nu + 1):
        u = i / nu
        row = [part.add(pts_out[i][k], col(u, k / 2) if callable(col) else col, (u, k / 2), aux,
                        dict(tag or {}, u=u)) for k in range(3)]
        lo = [part.add(pts_in[i][k], col(u, k) if callable(col) else col, (u, k), aux,
                       dict(tag or {}, u=u)) for k in range(2)]
        idx.append((row, lo))
    for i in range(nu):
        (r0, l0), (r1, l1) = idx[i], idx[i + 1]
        for k in range(2):
            part.f.append((r0[k], r0[k + 1], r1[k + 1], r1[k]))
        part.f.append((l0[0], r0[0], r1[0], l1[0]))
        part.f.append((r0[2], l0[1], l1[1], r1[2]))
    return part


def torso_normal(p):
    X, Yd, yc = torso_slice(min(max(p.z, TORSO[0][0]), TORSO[-1][0]))
    d = Vector((p.x / max(X, 1e-3), (p.y - yc) / max(Yd, 1e-3), 0.0))
    if d.length < 1e-6:
        return Vector((0, -1, 0))
    n = Vector((d.x / max(X, 1e-3), d.y / max(Yd, 1e-3), 0.0)).normalized()
    return n


def collar():
    """The kosode's V: her left panel over her right (the living way). White band with a red under-
    collar showing inside the V."""
    part = Part('collar', M_CLOTH)
    for side, z_end, over in ((1, 0.79, True), (-1, 0.875, False)):
        pts = [Vector((0.0, 0.050, 0.982)), Vector((side * 0.046, 0.018, 0.982)),
               Vector((side * 0.052, -0.040, 0.968)),
               Vector((side * 0.012, -0.082, 0.905)),
               Vector((-side * 0.030, -0.084, z_end + 0.02))]
        if not over:
            pts = pts[:4] + [Vector((-side * 0.008, -0.084, z_end))]

        def wfn(u):
            return 0.040
        _band_on(part, pts, wfn, 0.004 if over else 0.002, torso_normal, C.WHITE,
                 tag={'seg': 'torso'}, nu=12)
        # the red under-collar, a step inward toward the V
        red_pts = [p + Vector((-side * 0.0, 0.0, 0.0)) for p in pts]
        _band_on(part, [p + torso_normal(p) * 0.0 + (Vector((0, 0, 0))) for p in red_pts],
                 lambda u: 0.032, 0.001, torso_normal, C.RED_DEEP, tag={'seg': 'torso'}, nu=12,
                 thick=0.003)
    # shift the red bands toward the inside of the V (they were laid on the same line)
    return part


# =================================================================================================
# haori (cream coat): open front, flaring to the shins, navy front bands

COAT = [
    # z      X      Yd     yc     half gap at the front (rad): the panels part below the obi and the
    #                             navy trousers show between them
    (0.982, 0.064, 0.056, 0.012, 0.42),
    (0.962, 0.124, 0.072, 0.010, 0.30),
    (0.935, 0.156, 0.094, 0.006, 0.24),
    (0.870, 0.152, 0.099, 0.000, 0.26),
    (0.790, 0.142, 0.101, 0.000, 0.32),
    (0.700, 0.156, 0.110, 0.000, 0.40),
    (0.600, 0.180, 0.127, 0.004, 0.24),
    (0.450, 0.212, 0.150, 0.010, 0.31),
    (0.300, 0.238, 0.170, 0.016, 0.38),
    (0.200, 0.252, 0.180, 0.020, 0.42),
]


def coat_slice(z):
    keys = [(p[0], p) for p in COAT[::-1]]
    X = interp([(p[0], p[1]) for p in COAT[::-1]], z)
    Yd = interp([(p[0], p[2]) for p in COAT[::-1]], z)
    yc = interp([(p[0], p[3]) for p in COAT[::-1]], z)
    g = interp([(p[0], p[4]) for p in COAT[::-1]], z)
    return X, Yd, yc, g


def _peak(v, c, w):
    d = abs(v - c)
    return max(0.0, 1.0 - d / w) ** 1.3


def hem_z(v):
    """The haori's hem along v (0 her right front edge .. 1 her left front edge): cut in points like the
    art's (the front corners hang lowest, a second point at each side, one at the back), so the white
    hangs in layers over the trousers instead of closing like a skirt."""
    w = 0.36
    w -= 0.10 * (_peak(v, 0.0, 0.07) + _peak(v, 1.0, 0.07))
    w -= 0.075 * (_peak(v, 0.21, 0.07) + _peak(v, 0.79, 0.07))
    w -= 0.10 * _peak(v, 0.5, 0.14)
    w -= 0.03 * math.sin(math.pi * v) ** 2
    return w


def coat_point(z, v, grow=0.0):
    X, Yd, yc, g = coat_slice(z)
    t = (math.pi / 2 + g) + v * (TAU - 2 * g)
    x, y = ring_point(t, X + grow, Yd + grow, yc, n=2.2)
    return Vector((x, y, z))


OBI_MID = 0.745


def coat():
    part = Part('coat', M_CLOTH)
    z_top = COAT[0][0]
    nu, nv = 20, 64

    def pos(u, v):
        hz = hem_z(v)
        z = lerp(z_top, hz, u)
        p = coat_point(z, v)
        return p

    def col(u, v):
        # above the obi the navy kosode (the white robe is worn off the shoulders: only its collar
        # shows there); below it the white panels, a whisper of shade toward the hem's inside folds
        z = lerp(z_top, hem_z(v), u)
        if z > OBI_MID:
            return C.NAVY
        return mix_col(C.CREAM, C.CREAM_EDGE, 0.25 * smooth((u - 0.85) / 0.15))

    def tag(u, v):
        hz = hem_z(v)
        z = lerp(z_top, hz, u)
        X, Yd, yc, g = coat_slice(z)
        t = (math.pi / 2 + g) + v * (TAU - 2 * g)
        return {'seg': 'coat', 'u': u, 'v': v, 'z': z, 't': t}

    grid(part, nu, nv, pos, close_v=False, col=col, auxf=lambda u, v: (M_CLOTH, LINED_CREAM),
         tagf=tag)
    # (no navy bands on the front edges: the art's panels are white to the edge; navy there joined
    # the trousers into one dark column down her middle)
    return part


# =================================================================================================
# sleeves (furisode-like, hanging bags lined in navy), hands

def tamoto_corners(side):
    """The tamoto's four corners in the rest pose (top outer under the elbow, top inner under the wrist,
    and the bottom ones at mid-thigh, well outside the body: the two white flags of the art)."""
    def m(v):
        return Vector((v.x * side, v.y, v.z))
    el, wr = m(B.ELBOW), m(B.WRIST)
    # wider than real sleeves (the lead: at native size they must read as two white flags from any
    # side, beyond the long hair from behind): the outer edge 0.40 m from her middle
    top_o = el + Vector((side * 0.070, 0.016, -0.010))
    top_i = wr + Vector((side * 0.004, -0.006, -0.040))
    # the lower corners flare: the outer one out, the inner one forward past the robe's front (the
    # lead, round 3: in profile the sleeve's mouth must stand out of the hem, a flag, not a panel of it)
    bot_o = Vector((side * 0.415, 0.030, 0.385))
    bot_i = Vector((side * 0.140, -0.235, 0.425))
    return top_o, top_i, bot_o, bot_i


def sleeve(side):
    """The white robe's sleeve as the art draws it: worn off the shoulder (the navy kosode shows on the
    shoulder cap), a wide tube round the arm open at the wrist (navy cuff), and below the forearm the
    tamoto, a big flat bag hanging to mid-thigh, its opening edge lined in navy. With the elbows out
    and the forearms across the front (the rest pose), the two bags face front like two white flags,
    the widest shapes on her after the hat; they swing on the sleeve chains (rig.json springs)."""
    part = Part('sleeve', M_CLOTH)

    def m(v):
        return Vector((v.x * side, v.y, v.z))
    sh, el, wr = m(B.SHOULDER), m(B.ELBOW), m(B.WRIST)
    fa = (wr - el).normalized()
    pts = [sh + Vector((side * 0.004, 0.0, 0.014)), el, wr + fa * 0.014]
    path = Path(pts, up=(0, 0, 1))
    nu, nv = 18, 24

    def pos(u, v):
        p, t, n, b = path.at(u)
        a = v * TAU
        rn = interp([(0.0, 0.058), (0.45, 0.074), (1.0, 0.084)], u)
        rb = interp([(0.0, 0.062), (0.45, 0.078), (1.0, 0.090)], u)
        ca, sa = math.cos(a), math.sin(a)
        e = 2.0 / 2.4
        return p + n * (rn * math.copysign(abs(ca) ** e, ca)) + b * (rb * math.copysign(abs(sa) ** e, sa))

    def tag(u, v):
        return {'seg': 'sleeve', 'side': side, 'u': u, 'hang': 0.0}

    def col(u, v):
        # the navy kosode's shoulder cap, then the white robe
        return C.NAVY if u < 0.2 else C.CREAM

    grid(part, nu, nv, pos, close_v=True, col=col, auxf=lambda u, v: (M_CLOTH, LINED), tagf=tag)
    # navy cuff edge round the opening
    cuff = Part('cuff', M_CLOTH)

    def cpos(u, v):
        uu = lerp(0.93, 1.0, u)
        p0, t, n, b = path.at(uu)
        q = pos(uu, v)
        return q + (q - p0).normalized() * 0.005

    grid(cuff, 2, nv, cpos, close_v=True, col=lambda u, v: C.NAVY, auxf=lambda u, v: (M_CLOTH, LINED),
         tagf=lambda u, v: tag(1.0, v))
    part.extend(cuff)
    # the tamoto: a flat bag from under the forearm down to mid-thigh, rounded lower corners
    flag = Part('tamoto', M_CLOTH)
    top_o, top_i, bot_o, bot_i = tamoto_corners(side)
    across = (top_o - top_i).normalized()
    out_dir = across.cross(Vector((0, 0, 1))).normalized()
    if out_dir.y > 0:                        # the bag's faces look front-outward and back-inward
        out_dir = -out_dir
    thick = 0.026

    def bag(u, x, face):
        top = top_i.lerp(top_o, x)
        bot = bot_i.lerp(bot_o, x)
        # rounded bottom corners: the bottom rises toward both edges
        rise = 0.05 * (abs(2 * x - 1) ** 4)
        q = top.lerp(bot, u) + Vector((0, 0, rise * smooth((u - 0.6) / 0.4)))
        # the bag bellies out a little in the middle
        belly = 0.018 * math.sin(math.pi * u) * math.sin(math.pi * x)
        return q + out_dir * (face * thick * (0.35 + 0.65 * math.sin(math.pi * x) ** 0.5) + belly)

    def fpos(u, v):
        # u: down the bag (0 top .. 1 bottom); v: round the bag's edge loop (both faces and the rim)
        a = v * TAU
        # the mirrored corners flip the grid's handedness: the face sign follows the side so both bags
        # wind outward
        return bag(u, 0.5 - 0.5 * math.cos(a), -side * math.sin(a))

    def ftag(u, v):
        a = v * TAU
        x = 0.5 - 0.5 * math.cos(a)
        return {'seg': 'tamoto', 'side': side, 'u': u, 'x': x}

    rows = grid(flag, 14, 28, fpos, close_v=True, col=lambda u, v: C.CREAM,
                auxf=lambda u, v: (M_CLOTH, LINED), tagf=ftag)
    # close the bag's bottom
    bc = sum((flag.v[i] for i in rows[-1]), Vector()) / len(rows[-1])
    cap(flag, rows[-1], bc, col=C.CREAM_EDGE, aux=(M_CLOTH, LINED), flip=False)
    flag.tag[-1] = {'seg': 'tamoto', 'side': side, 'u': 1.0, 'x': 0.5}
    # the opening's navy lining: a band down the inner edge of the front face
    lpts = [bag(k / 8 * 0.97, 0.10, 1.0) for k in range(9)]
    lining = Part('tamoto_lining', M_CLOTH)
    _band_on(lining, lpts, 0.042, 0.003, lambda q: out_dir, C.NAVY, aux=(M_CLOTH, LINED),
             tag={'seg': 'tamoto', 'side': side, 'x': 0.10}, nu=10, thick=0.004)
    for i, tg in enumerate(lining.tag):
        lining.tag[i] = dict(tg, u=tg.get('u', 0.0) * 0.97)
    flag.extend(lining)
    part.extend(flag)
    return part


def hand(side):
    part = Part('hand', M_SKIN)
    def m(v):
        return Vector((v.x * side, v.y, v.z))
    w = m(B.WRIST)
    tip = m(B.HAND_TIP)
    axis = (tip - w).normalized()
    path = Path([w - axis * 0.01, w + axis * 0.03, tip + axis * 0.012], up=(side, 0, 0))

    def section(u, a):
        r = 0.030 * math.sin(math.pi * min(1.0, 0.18 + u * 0.9)) + 0.005
        return (r * 0.68 * math.cos(a), r * math.sin(a))

    sweep(part, path, 8, 12, section, pole0=True, pole1=True, col=lambda u, v: C.SKIN,
          auxf=lambda u, v: (M_SKIN, 0.0), tagf=lambda u, v: {'seg': 'hand', 'side': side, 'u': u})
    # thumb
    tb = w + axis * 0.022 + Vector((-side * 0.012, -0.018, 0.0))
    tpath = Path([tb, tb + Vector((-side * 0.006, -0.016, -0.018))], up=(side, 0, 0))
    sweep(part, tpath, 4, 8, lambda u, a: (0.011 * math.cos(a), 0.011 * math.sin(a)), pole0=True, pole1=True,
          col=lambda u, v: C.SKIN, auxf=lambda u, v: (M_SKIN, 0.0),
          tagf=lambda u, v: {'seg': 'hand', 'side': side, 'u': 1.0})
    return part


# =================================================================================================
# obi, cord, bow and the long tail

OBI_Z = (0.698, 0.792)
CORD_Z = (0.728, 0.762)


def obi():
    part = Part('obi', M_CLOTH)

    def pos(u, v):
        z = lerp(OBI_Z[0], OBI_Z[1], u)
        X, Yd, yc = torso_slice(z)
        bulge = 0.012 + 0.004 * math.sin(math.pi * u)
        x, y = ring_point(v * TAU, X + bulge, Yd + bulge, yc)
        return Vector((x, y, z))

    grid(part, 4, 28, pos, close_v=True, col=lambda u, v: C.WHITE, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': lerp(OBI_Z[0], OBI_Z[1], u)})
    cord = Part('cord', M_CLOTH)

    def cpos(u, v):
        z = lerp(CORD_Z[0], CORD_Z[1], u)
        X, Yd, yc = torso_slice(z)
        bulge = 0.022 + 0.004 * math.sin(math.pi * u)
        x, y = ring_point(v * TAU, X + bulge, Yd + bulge, yc)
        return Vector((x, y, z))

    grid(cord, 2, 28, cpos, close_v=True, col=lambda u, v: C.RED, flip=True,
         tagf=lambda u, v: {'seg': 'torso', 'z': 0.745})
    part.extend(cord)
    return part


BOW_AT = Vector((0.120, -0.126, 0.800))
# the two tails (Blender coordinates, rest pose): from the bow at her left hip, over the forearm's
# sleeve, the long one out and down past her knee, the shorter one out and back, so they show beside
# her from the front, the side and from behind (the lead: the sash is one of her three big shapes;
# longer than real, it reads)
TAIL_A = [Vector((0.136, -0.140, 0.776)), Vector((0.205, -0.150, 0.62)), Vector((0.268, -0.118, 0.47)),
          Vector((0.318, -0.075, 0.32)), Vector((0.355, -0.035, 0.17))]
# the shorter one is thrown back over her left hip and hangs behind her, between the long hair's two
# tails: from behind it is the red that shows (and it is the one that flies when she walks)
TAIL_B = [Vector((0.134, -0.132, 0.776)), Vector((0.222, -0.040, 0.715)), Vector((0.200, 0.120, 0.620)),
          Vector((0.095, 0.215, 0.500)), Vector((0.050, 0.240, 0.360))]


def bow():
    """The red bow at her front left: a knot and two big loops (the art's butterfly), over the obi."""
    part = Part('bow', M_CLOTH)
    k = BOW_AT
    path = Path([k + Vector((0, 0.012, 0.024)), k + Vector((0, -0.008, 0.0)), k + Vector((0, 0.012, -0.024))],
                up=(0, -1, 0))
    sweep(part, path, 4, 10, lambda u, a: (0.026 * math.cos(a), 0.024 * math.sin(a)), pole0=True, pole1=True,
          col=lambda u, v: C.RED, tagf=lambda u, v: {'seg': 'bow'})
    # loops: teardrops pinched at the knot, one out to her left and up, one to her right and down
    for ang, size, h in ((math.radians(24), 0.140, 0.086), (math.radians(150), 0.126, 0.078)):
        d = Vector((math.cos(ang), 0.0, math.sin(ang)))
        up = Vector((-d.z, 0, d.x))
        c = k + d * size * 0.5 + Vector((0, 0.01, 0))
        lp = []
        for j in range(12):
            a = j / 12 * TAU
            r = 0.5 * (1.0 - 0.35 * math.cos(a))
            lp.append(c + d * (size * 0.5 * math.cos(a)) + up * (h * r * math.sin(a)))
        lpath = Path(lp + [lp[0], lp[1]], up=(0, -1, 0))

        def section(u, a):
            return (0.010 * math.cos(a), 0.030 * math.sin(a))
        sweep(part, lpath, 24, 6, section, col=lambda u, v: C.RED, tagf=lambda u, v: {'seg': 'bow'})
    return part


def _tail(part, pts, width, chain, col):
    path = Path(pts, up=(0, -1, 0))

    def section(u, a):
        w = lerp(width * 0.6, width, smooth(u * 3.0))
        return (0.007 * math.sin(a), w * math.cos(a))

    rows = sweep(part, path, 20, 8, section, col=lambda u, v: col, auxf=lambda u, v: (M_CLOTH, 0.0),
                 tagf=lambda u, v: {'seg': 'sash', 'u': u, 'chain': chain}, flip=True)
    p, t, n, b = path.at(1.0)
    # a swallow-tail cut: the end's middle sits a little up
    tip = part.add(p - t * 0.024, col, (1, 0.5), (M_CLOTH, 0.0), {'seg': 'sash', 'u': 1.0, 'chain': chain})
    ring = rows[-1]
    for j in range(len(ring)):
        part.f.append((tip, ring[j], ring[(j + 1) % len(ring)]))


def sash_tail():
    """Two long red tails from the bow: the long one to her knee, a shorter one beside it. They fly on
    their spring chains (sashA, sashB) whenever she walks, turns or stops."""
    part = Part('sash', M_CLOTH)
    _tail(part, TAIL_A, 0.080, 'A', C.RED)
    _tail(part, TAIL_B, 0.068, 'B', C.RED_DEEP)
    return part


# =================================================================================================
# trousers (navy balloon monpe), ankle bands, tabi, sandals

def leg_points(side):
    def m(v):
        return Vector((v.x * side, v.y, v.z))
    return m(B.HIP_JOINT), m(B.KNEE), m(B.ANKLE)


def trouser(side):
    """Navy lantern trousers (monpe): full from the knee down, gathered at the ankle under a white band
    (the band sits on the top of the boot)."""
    part = Part('trouser', M_CLOTH)
    hip, knee, ankle = leg_points(side)
    top = hip + Vector((-side * 0.01, 0.0, 0.06))
    a_top = ankle + Vector((0, 0, 0.05))
    path = Path([top, hip, knee, a_top + Vector((0, 0, 0.05)), a_top], up=(0, -1, 0))

    def section(u, a):
        r = interp([(0.0, 0.098), (0.25, 0.108), (0.5, 0.118), (0.72, 0.126), (0.86, 0.112),
                    (0.95, 0.075), (1.0, 0.052)], u)
        return (r * 0.84 * math.cos(a), r * math.sin(a))

    sweep(part, path, 20, 20, section, col=lambda u, v: C.NAVY,
          tagf=lambda u, v: {'seg': 'leg', 'side': side, 'u': u})
    band = Part('ankle_band', M_CLOTH)
    bpath = Path([a_top + Vector((0, 0, 0.012)), a_top + Vector((0, 0, -0.028))], up=(0, -1, 0))
    sweep(band, bpath, 2, 16, lambda u, a: (0.054 * math.cos(a), 0.054 * math.sin(a)),
          col=lambda u, v: C.WHITE, tagf=lambda u, v: {'seg': 'leg', 'side': side, 'u': 0.97})
    part.extend(band)
    return part


def foot(side):
    """Jika-tabi: near-black indigo split-toe work boots to above the ankle, a thin pale rubber sole."""
    part = Part('foot', M_CLOTH)

    def m(v):
        return Vector((v.x * side, v.y, v.z))
    ank, ball, toe = m(B.ANKLE), m(B.BALL), m(B.TOE)
    path = Path([ank + Vector((0, 0.012, 0.06)), ank + Vector((0, 0.022, 0.0)), ank + Vector((0, 0.012, -0.05)),
                 ball + Vector((0, 0.0, 0.006)), toe + Vector((0, 0.004, 0.008))], up=(0, -1, 0))

    def section(u, a):
        w = interp([(0.0, 0.046), (0.3, 0.044), (0.55, 0.040), (0.8, 0.036), (1.0, 0.026)], u)
        h = interp([(0.0, 0.046), (0.3, 0.046), (0.55, 0.036), (0.8, 0.024), (1.0, 0.016)], u)
        return (h * math.cos(a), w * math.sin(a))

    sweep(part, path, 12, 14, section, pole1=True, col=lambda u, v: C.NAVY_DEEP,
          tagf=lambda u, v: {'seg': 'foot', 'side': side, 'u': max(0.0, (u - 0.3) / 0.7)})
    sole = Part('sole', M_CLOTH)
    cx = ank.x
    y0, y1 = ank.y + 0.05, toe.y - 0.012

    def spos(u, v):
        a = v * TAU
        cxs, sys_ = superellipse(a, 1.0, 1.0, 2.6)
        hw = 0.038 if sys_ < 0 else 0.042
        yy = (y0 + y1) / 2 - sys_ * (y0 - y1) / 2
        z = 0.016 * (1 - u)
        return Vector((cx + cxs * hw, yy, z))

    rows = grid(sole, 1, 24, spos, close_v=True, col=lambda u, v: C.SOLE,
                tagf=lambda u, v: {'seg': 'foot', 'side': side, 'u': 0.6})
    cap(sole, rows[0], Vector((cx, (y0 + y1) / 2, 0.016)), col=C.SOLE, aux=(M_CLOTH, 0.0))
    cap(sole, rows[-1], Vector((cx, (y0 + y1) / 2, 0.0)), col=C.SOLE, aux=(M_CLOTH, 0.0), flip=True)
    for i in range(len(sole.tag)):
        sole.tag[i] = {'seg': 'foot', 'side': side, 'u': 0.6}
    part.extend(sole)
    return part


def body_parts():
    parts = [torso(), collar(), coat(), obi(), bow(), sash_tail()]
    for side in (1, -1):
        parts += [sleeve(side), hand(side), trouser(side), foot(side)]
    return parts
