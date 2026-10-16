"""百々かさゝぎ, round 6: body and clothes, built to the model sheet (design.py: the blueprint frame and
every measured number; the clothes sheet for details).

  * a navy kosode with a white and a red collar showing in its V;
  * the cream outer coat, open in front, flaring to uneven pointed hems at the knees, with very wide
    sleeves hanging to the knees from the A-posed arms, navy lining showing at the cuffs;
  * a white obi with a red band, a big red bow a little to her left, one short tail and one long one
    running down past her left knee;
  * navy lantern trousers gathered under the knee, white leg wraps, navy tabi on cream-soled zori with
    a white thong.

Coordinates: Blender, metres, Z up, she faces -Y, her left is +X.
"""
import math
from mathutils import Vector

from c3d.surf import Part, grid, sweep, cap, Path, interp, smooth, lerp, M_SKIN, M_CLOTH, M_TIE
from kasasagi import body as B
from kasasagi import palette as C
from kasasagi.design import D

TAU = 2 * math.pi


def _tab(table, h, k):
    return interp([(p[0], p[k]) for p in table], h)


# =================================================================================================
# the kosode (navy): the torso from the hips to the neck, the shoulders sloping
TORSO = [
    # h      W       F       K
    (0.62, 0.150, 0.120, 0.120),
    (0.80, 0.150, 0.120, 0.120),
    (0.95, 0.152, 0.125, 0.118),
    (1.05, 0.160, 0.128, 0.112),
    (1.10, 0.168, 0.118, 0.105),
    (1.13, 0.170, 0.105, 0.098),
    (1.155, 0.142, 0.088, 0.082),
    (1.185, 0.085, 0.064, 0.060),
    (1.21, 0.056, 0.052, 0.050),
    (1.235, 0.050, 0.048, 0.046),
]


def torso_point(h, a, grow=0.0):
    """a: angle from her front, + toward her left."""
    W = _tab(TORSO, h, 1) + grow
    F = _tab(TORSO, h, 2) + grow
    K = _tab(TORSO, h, 3) + grow
    s, c = math.sin(a), math.cos(a)
    e = 2.0 / 2.6
    x = W * math.copysign(abs(s) ** e, s)
    y = -F * (abs(c) ** e) if c >= 0 else K * (abs(c) ** e)
    return Vector((x, y + 0.004, h))


def _collar_col(p):
    """The V: skin at the throat, a red band, a white band, then the navy kosode."""
    # sheet front: at h 1.21 the throat |x| < 0.037, red to 0.055, white to 0.095; the V's point at
    # h 1.036
    if p.y > -0.02 or p.z < D['collar_v']:
        return C.NAVY
    d = abs(p.x) - 0.316 * (p.z - D['collar_v'])
    return C.SKIN if d < 0.0 else C.NAVY


def torso():
    part = Part('torso', M_CLOTH)
    h0, h1 = 0.62, 1.235

    def pos(u, v):
        return torso_point(lerp(h0, h1, u), v * TAU - math.pi / 2)

    grid(part, 20, 40, pos, close_v=True, col=lambda u, v: _collar_col(pos(u, v)),
         auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'torso', 'h': lerp(h0, h1, u)}, flip=True)
    return part


def collar():
    """The V of the collars on the kosode's front: a red band inside a white one each side, from the
    neck's sides down to the V's point (sheet front: at h 1.21 the throat |x| < 0.037, red to 0.055,
    white to 0.095; the point at h 1.036). Strips lying on the torso, a little proud of it."""
    part = Part('collar', M_CLOTH)
    z0, z1 = D['collar_v'], 1.235
    k = 0.300

    def on_torso(x, z, lift):
        # the torso's front surface at (x, z): search the angle whose x matches
        lo, hi = 0.0, math.pi / 2
        sgn = 1 if x >= 0 else -1
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if abs(torso_point(z, sgn * mid).x) < abs(x):
                lo = mid
            else:
                hi = mid
        p = torso_point(z, sgn * 0.5 * (lo + hi))
        return p + Vector((0, -lift, 0))

    for side in (1, -1):
        for (d0, d1, col, lift) in ((-0.018, 0.0, C.RED, 0.006), (0.0, 0.040, C.WHITE, 0.008)):
            def pos(u, v, d0=d0, d1=d1, lift=lift, side=side):
                z = lerp(z0, z1, u)
                x = side * (k * (z - z0) + lerp(d0, d1, v))
                if side * x < 0:
                    x = 0.0
                return on_torso(x, min(z, 1.232), lift + 0.004 * smooth((z - 1.16) / 0.05))
            grid(part, 8, 2, pos, col=lambda u, v, col=col: col, auxf=lambda u, v: (M_CLOTH, 0.0),
                 tagf=lambda u, v: {'seg': 'torso', 'h': 1.1}, flip=(side < 0))
    return part


# =================================================================================================
# the outer coat (cream), open in front

COAT = [
    # h      W       F       K       gap: x of the front edge (sheet front: the lapels at x +-0.20 by the
    #                                chest, the kosode's navy between them and the white collar)
    (0.225, 0.420, 0.335, 0.240, 0.150),
    (0.40, 0.400, 0.330, 0.232, 0.150),
    (0.60, 0.350, 0.272, 0.205, 0.145),
    (0.80, 0.270, 0.205, 0.172, 0.160),
    (0.92, 0.205, 0.162, 0.152, 0.185),
    (1.02, 0.205, 0.152, 0.140, 0.198),
    (1.10, 0.200, 0.138, 0.126, 0.192),
    (1.15, 0.188, 0.112, 0.105, 0.172),
    (1.185, 0.150, 0.080, 0.078, 0.140),
]
COAT_TOP = 1.185


def coat_slice(h):
    return (_tab(COAT, h, 1), _tab(COAT, h, 2), _tab(COAT, h, 3), _tab(COAT, h, 4))


def coat_hem(a):
    """Hem height by the angle from the front edge round her side to the back (radians from the
    front, absolute): the front panels' corners by the opening, the lowest points at the sides, a
    second corner behind and the back's middle a little higher (sheet: front, side and back views)."""
    deg = math.degrees(abs(a))
    # front view: the lowest corners at x +-0.37 (60 deg round from the front); side view: the side
    # seam high (0.39), the corners front and back lower; back view: points at the back's sides
    tab = [(0.0, D['coat_hem_mid']), (28.0, D['coat_hem_mid']), (60.0, D['coat_hem']),
           (92.0, 0.395), (125.0, 0.300), (155.0, 0.255), (180.0, 0.340)]
    for i in range(len(tab) - 1):
        if tab[i][0] <= deg <= tab[i + 1][0]:
            t = (deg - tab[i][0]) / (tab[i + 1][0] - tab[i][0])
            return lerp(tab[i][1], tab[i + 1][1], t)
    return tab[-1][1]


def coat_point(h, a, grow=0.0):
    W, F, K, g = coat_slice(h)
    s, c = math.sin(a), math.cos(a)
    e = 2.0 / 2.4
    x = (W + grow) * math.copysign(abs(s) ** e, s)
    y = -(F + grow) * (abs(c) ** e) if c >= 0 else (K + grow) * (abs(c) ** e)
    return Vector((x, y, h))


def _edge_angle(h, side):
    """The angle (from the front) where the coat's front edge is: x = gap."""
    W, F, K, g = coat_slice(h)
    r = min(0.999, g / max(W, 1e-3))
    # invert x = W |s|^e for s
    e = 2.0 / 2.4
    s = r ** (1.0 / e)
    return side * math.asin(s)


def coat():
    part = Part('coat', M_CLOTH)
    nu, nv = 26, 96

    def a_of(u, v):
        h = lerp(COAT_TOP, 0.2, u)
        a0 = _edge_angle(h, 1)
        return lerp(a0, TAU - a0, v)

    def pos(u, v):
        a = a_of(u, v)
        aa = a if a <= math.pi else a - TAU
        hem = coat_hem(aa)
        h = lerp(COAT_TOP, hem, u)
        return coat_point(h, a)

    def col(u, v):
        k = (v * 16.0) % 1.0
        return C.CREAM_DEEP if (k < 0.06 and u > 0.35) else C.CREAM

    grid(part, nu, nv, pos, col=col, auxf=lambda u, v: (M_CLOTH, 0.0),
         tagf=lambda u, v: {'seg': 'coat', 'u': u, 'a': a_of(u, v)}, flip=False)
    # the inside (a step deeper), so the open front shows the coat's inner face
    def pos_in(u, v):
        p = pos(u, v)
        return Vector((p.x * 0.985, p.y * 0.985, p.z))
    grid(part, nu, nv, pos_in, col=lambda u, v: C.CREAM_DEEP, auxf=lambda u, v: (M_CLOTH, 0.0),
         tagf=lambda u, v: {'seg': 'coat', 'u': u, 'a': a_of(u, v)}, flip=True)
    return part


# =================================================================================================
# sleeves: the coat's wide sleeves hanging from the A-posed arms. Sections in planes across her
# side (x constant) from the shoulder out to the cuff; each section a tall loop from just over the arm
# down to the bag's bottom. Front view: the cuff's edge from (x 0.484, h 0.877) to the lowest point
# (0.403, 0.518); side view: the bag 0.26 m front to back, the navy opening in its middle.

def arm_z(x):
    """Height of the arm's line at |x| (the A pose)."""
    S, W = B.SHOULDER, B.WRIST
    t = (x - S.x) / (W.x - S.x)
    return lerp(S.z, W.z, t)


SLEEVE_X0 = 0.195                # the coat's shoulder seam (sheet front: the sleeves begin at x 0.20)
SLEEVE_X1 = 0.500                # the cuff's outer corner (sheet front: the navy diamond's outer point)


def sleeve_bottom(x):
    tab = [(0.195, 0.92), (0.24, 0.80), (0.30, 0.66), (0.36, 0.56), (0.405, 0.518), (0.45, 0.545),
           (0.50, 0.600)]
    return interp(tab, x)


def sleeve_top(x):
    return arm_z(x) + 0.065


def sleeve_depth(x, z):
    """Half depth (front to back) of the bag at x, height z."""
    w = lerp(0.10, D['sleeve_depth'], smooth((x - 0.195) / 0.12))
    zt, zb = sleeve_top(x), sleeve_bottom(x)
    t = (z - zb) / max(zt - zb, 1e-3)
    # narrow over the arm, full lower down, rounded at the bottom
    return w * (math.sin(math.pi * min(1.0, max(0.0, t)) ** 0.8) ** 0.7) + 0.02


def sleeve_point(side, x, phi, inset=0.0):
    zt, zb = sleeve_top(x), sleeve_bottom(x)
    zc = 0.5 * (zt + zb)
    hz = 0.5 * (zt - zb) - inset
    z = zc + hz * math.cos(phi)
    w = sleeve_depth(x, z) - inset
    y = -w * math.sin(phi) + 0.01
    return Vector((side * x, y, z))


CUFF_DIAMOND = [(0.48, 0.89), (0.34, 0.72), (0.40, 0.53), (0.52, 0.75)]


def in_cuff_diamond(x, z):
    """The navy lining the sheet shows at each cuff (front and back views): a diamond in (|x|, z)."""
    pts = CUFF_DIAMOND
    inside = False
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        if (z1 > z) != (z2 > z):
            xi = x1 + (z - z1) * (x2 - x1) / (z2 - z1)
            if x < xi:
                inside = not inside
    return inside


def sleeves():
    parts = []
    for side in (1, -1):
        part = Part('sleeve', M_CLOTH)
        nu, nv = 40, 44

        def pos(u, v, side=side):
            x = lerp(SLEEVE_X0, SLEEVE_X1, u)
            return sleeve_point(side, x, v * TAU)

        def col(u, v, side=side):
            p = pos(u, v)
            return C.NAVY_LINING if in_cuff_diamond(abs(p.x), p.z) else C.CREAM

        grid(part, nu, nv, pos, close_v=True, col=col, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, side=side: {'seg': 'sleeve', 'side': side, 'u': u, 'phi': v},
             flip=(side < 0))
        # the lining inside, navy
        def pos_in(u, v, side=side):
            x = lerp(SLEEVE_X0, SLEEVE_X1, u)
            return sleeve_point(side, x, v * TAU, inset=0.012)
        rows = grid(part, nu, nv, pos_in, close_v=True, col=lambda u, v: C.NAVY_LINING,
                    auxf=lambda u, v: (M_CLOTH, 0.0),
                    tagf=lambda u, v, side=side: {'seg': 'sleeve', 'side': side, 'u': u, 'phi': v},
                    flip=(side > 0))
        x0 = SLEEVE_X0 + 0.004
        cz = 0.5 * (sleeve_top(x0) + sleeve_bottom(x0))
        cap(part, rows[0], Vector((side * x0, 0.01, cz)), col=C.NAVY_LINING, aux=(M_CLOTH, 0.0),
            flip=(side > 0))
        parts.append(part)
    return parts


def hands():
    """The hands out of the cuffs, open, fingers down (the sheet's A pose); a navy kosode cuff round
    the wrist inside the sleeve's opening."""
    parts = []
    for side in (1, -1):
        part = Part('hand', M_SKIN)
        Wr = Vector((side * B.WRIST.x, B.WRIST.y, B.WRIST.z))
        d = Vector((side * B.ARM_DIR.x, B.ARM_DIR.y, B.ARM_DIR.z))
        dd = (d + Vector((0, 0, -0.35))).normalized()
        tip = Wr + dd * 0.135 + Vector((0, -0.01, 0))
        path = Path([Wr - d * 0.02, Wr + dd * 0.05, tip], up=(0, -1, 0))

        def section(u, a):
            w = lerp(0.030, 0.040, smooth(u * 2)) * (1.0 - 0.40 * smooth((u - 0.7) / 0.3))
            t = lerp(0.022, 0.014, u)
            return (t * math.cos(a), w * math.sin(a))
        sweep(part, path, 8, 12, section, pole1=True, col=lambda u, v: C.SKIN,
              auxf=lambda u, v: (M_SKIN, 0.0), tagf=lambda u, v, side=side: {'seg': 'hand', 'side': side, 'u': u})
        # the kosode's cuff round the wrist
        cpath = Path([Wr - d * 0.10, Wr - d * 0.01], up=(0, -1, 0))

        def csec(u, a):
            return (0.040 * math.cos(a), 0.044 * math.sin(a))
        sweep(part, cpath, 3, 12, csec, col=lambda u, v: C.NAVY, auxf=lambda u, v: (M_CLOTH, 0.0),
              tagf=lambda u, v, side=side: {'seg': 'forearm', 'side': side, 'u': u})
        parts.append(part)
    return parts


# =================================================================================================
# the obi, the red band, the bow and its tails

def obi():
    part = Part('obi', M_CLOTH)
    z0, z1 = D['obi_z']
    b0, b1 = D['band_z']
    W, Dp = D['obi_w'], D['obi_d']

    def pos(u, v, grow=0.0):
        z = lerp(z0, z1, u)
        a = v * TAU
        s, c = math.sin(a), math.cos(a)
        e = 2.0 / 2.5
        return Vector(((W + grow) * math.copysign(abs(s) ** e, s), -(Dp + 0.01 + grow) * math.copysign(abs(c) ** e, c) + 0.004, z))

    grid(part, 6, 44, pos, close_v=True, col=lambda u, v: C.WHITE, auxf=lambda u, v: (M_CLOTH, 0.0),
         tagf=lambda u, v: {'seg': 'obi'}, flip=True)
    # tops and bottoms closed against the coat
    band = Part('band', M_CLOTH)

    def pos_b(u, v):
        z = lerp(b0, b1, u)
        return pos((z - z0) / (z1 - z0), v, grow=0.008)
    grid(band, 3, 44, pos_b, close_v=True, col=lambda u, v: C.RED, auxf=lambda u, v: (M_CLOTH, 0.0),
         tagf=lambda u, v: {'seg': 'obi'}, flip=True)
    return [part, band]


def _front_y(x, z):
    """The obi band's front surface y at x (to place the bow on it)."""
    W, Dp = D['obi_w'], D['obi_d']
    r = min(0.999, abs(x) / (W + 0.008))
    e = 2.0 / 2.5
    s = r ** (1.0 / e)
    c = math.sqrt(max(0.0, 1 - s * s))
    return -(Dp + 0.018) * c ** e + 0.004


def bow():
    part = Part('bow', M_CLOTH)
    kx, kz = D['bow_x'], D['bow_z']
    ky = _front_y(kx, kz) - 0.012
    knot = Vector((kx, ky, kz))
    # two loops: flattened ellipsoids either side of the knot
    for side in (1, -1):
        # each loop: a filled, flattened ellipsoid tilted up and out (front view: 0.107 wide each side,
        # 0.115 tall in all)
        c = knot + Vector((side * D['bow_w'] * 0.50, 0.010, 0.012))

        def pos(u, v, c=c, side=side):
            a = v * TAU
            b = u * math.pi
            rx, rz, ry = D['bow_w'] * 0.52, D['bow_h'] * 0.46, 0.028
            p = Vector((rx * math.sin(b) * math.cos(a), -ry * math.cos(b), rz * math.sin(b) * math.sin(a)))
            p.z += side * p.x * 0.30
            return c + p
        grid(part, 8, 20, pos, close_v=True, pole0=True, pole1=True, col=lambda u, v: C.RED,
             auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'bow'})
    # the knot
    def posk(u, v):
        a = v * TAU
        b = u * math.pi
        return knot + Vector((0.030 * math.sin(b) * math.cos(a), -0.028 * math.cos(b) - 0.008,
                              0.034 * math.sin(b) * math.sin(a)))
    grid(part, 6, 14, posk, close_v=True, pole0=True, pole1=True, col=lambda u, v: C.RED_DEEP,
         auxf=lambda u, v: (M_CLOTH, 0.0), tagf=lambda u, v: {'seg': 'bow'})
    return part, knot


def sash_paths():
    """The two tails' centre lines (the short one, the long one)."""
    kx, kz = D['bow_x'], D['bow_z']
    ky = _front_y(kx, kz) - 0.02
    sx, sz = D['tail_short_end']
    lx, lz = D['tail_long_end']
    short = [Vector((kx + 0.01, ky, kz - 0.02)), Vector((kx + 0.05, ky - 0.03, kz - 0.10)),
             Vector((sx, ky - 0.04, sz))]
    long_ = [Vector((kx + 0.02, ky, kz - 0.02)), Vector((kx + 0.12, ky - 0.05, 0.72)),
             Vector((0.30, -0.30, 0.42)), Vector((lx - 0.04, -0.27, 0.22)), Vector((lx, -0.22, lz))]
    return short, long_


def sash_tails():
    part = Part('sash', M_CLOTH)
    short, long_ = sash_paths()
    for pts, w, name in ((short, D['tail_w'] * 0.85, 'sashA'), (long_, D['tail_w'], 'sashB')):
        path = Path(pts, up=(0, -1, 0))

        def pos(u, v, path=path, w=w, name=name):
            p, t, n, b = path.at(u)
            # the ribbon faces forward by the bow; the long tail turns to face her left lower down
            # (front view: broad by the bow; side view: broad over her knee)
            k = smooth((u - 0.30) / 0.40) if name == 'sashB' else 0.0
            face = Vector((0, -1, 0)).lerp(Vector((0.87, -0.50, 0)).normalized(), k).normalized()
            across = t.cross(face)
            if across.length < 1e-4:
                across = Vector((1, 0, 0))
            across.normalize()
            ww = w * 0.5 * (1.0 + 0.15 * math.sin(u * 5.0))
            return p + across * ((v - 0.5) * 2 * ww)
        grid(part, 22, 3, pos, col=lambda u, v: C.RED, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, name=name: {'seg': name, 'u': u})
    return part


# =================================================================================================
# legs: lantern trousers, leg wraps, tabi on zori

def trousers():
    parts = []
    for side in (1, -1):
        part = Part('trousers', M_CLOTH)
        x0 = side * B.LX

        def radius(z):
            tab = [(0.253, 0.064), (0.27, 0.112), (0.31, 0.138), (0.38, 0.135), (0.50, 0.118),
                   (0.62, 0.106), (0.72, 0.100)]
            return interp(tab, z)

        def pos(u, v, x0=x0, side=side):
            z = lerp(0.74, D['cuff_z'], u)
            a = v * TAU
            r = radius(z)
            # the leg's centre drifts in toward the crotch at the top
            xc = lerp(x0, x0 * 0.55, smooth((z - 0.55) / 0.2))
            return Vector((xc + r * math.cos(a), r * 0.95 * math.sin(a) - 0.01, z))

        def col(u, v):
            return C.TROUSERS_DEEP if u > 0.94 else C.TROUSERS

        grid(part, 14, 24, pos, close_v=True, col=col, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, side=side: {'seg': 'leg', 'side': side, 'z': lerp(0.74, D['cuff_z'], u)}, flip=True)
        # the leg wrap (white) under the cuff
        z0, z1 = D['wrap_z']

        def posw(u, v, x0=x0):
            z = lerp(z1 + 0.02, z0, u)
            a = v * TAU
            r = 0.056 - 0.006 * u
            return Vector((x0 + r * math.cos(a), r * math.sin(a), z))
        grid(part, 3, 16, posw, close_v=True, col=lambda u, v: C.WHITE, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, side=side: {'seg': 'leg', 'side': side, 'z': 0.2}, flip=True)
        parts.append(part)
    return parts


def feet():
    parts = []
    L, Wd = D['foot_len'], D['foot_w']
    for side in (1, -1):
        part = Part('foot', M_CLOTH)
        x0 = side * B.LX
        yc = -D['foot_f']
        top = D['wrap_z'][0]

        # the tabi: a rounded box from the ankle down, the toe in front
        def pos(u, v, x0=x0):
            # u: 0 the ankle's top .. 1 the sole; v round
            a = v * TAU
            z = lerp(top + 0.005, 0.03, u)
            k = smooth(u * 1.6)                 # the foot widens and lengthens toward the sole
            rx = lerp(0.052, Wd * 0.47, k)
            ry_f = lerp(0.052, L * 0.62, k)
            ry_b = lerp(0.050, L * 0.36, k)
            s, c = math.sin(a), math.cos(a)
            x = x0 + rx * c
            y = (yc * k) + (-ry_f * s if s > 0 else -ry_b * s)
            return Vector((x, y, z))

        grid(part, 10, 28, pos, close_v=True, col=lambda u, v: C.BOOTS, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, side=side: {'seg': 'foot', 'side': side}, flip=False)
        # the zori's sole (cream), a little larger, flat
        def poss(u, v, x0=x0):
            a = v * TAU
            z = lerp(0.032, 0.0, u)
            rx = Wd * 0.50
            s, c = math.sin(a), math.cos(a)
            x = x0 + rx * c
            y = yc + (-(L * 0.64) * s if s > 0 else -(L * 0.38) * s)
            return Vector((x, y, z))
        grid(part, 2, 28, poss, close_v=True, col=lambda u, v: C.SOLE, auxf=lambda u, v: (M_CLOTH, 0.0),
             tagf=lambda u, v, side=side: {'seg': 'foot', 'side': side}, flip=False)
        # the thong: a white strap over the toes
        tp = Path([Vector((x0 - 0.07, yc - 0.05, 0.035)), Vector((x0, yc - 0.12, 0.07)),
                   Vector((x0 + 0.07, yc - 0.05, 0.035))], up=(0, -1, 0))

        def tsec(u, a):
            return (0.008 * math.cos(a), 0.016 * math.sin(a))
        sweep(part, tp, 8, 8, tsec, col=lambda u, v: C.WHITE, auxf=lambda u, v: (M_CLOTH, 0.0),
              tagf=lambda u, v, side=side: {'seg': 'foot', 'side': side})
        parts.append(part)
    return parts


def body_parts():
    parts = [torso(), collar(), coat()]
    parts += sleeves()
    parts += hands()
    parts += obi()
    b, knot = bow()
    parts.append(b)
    parts.append(sash_tails())
    parts += trousers()
    parts += feet()
    return parts
