"""Parametric surfaces for the character builder (pure Python + mathutils; no bpy here).

A Part is a list of vertices with per-vertex attributes and quad / triangle faces. Every part of a
character is built from parametric grids (u along, v around), so the topology is clean quads that
shade smoothly, and every vertex knows its (u, v) for colour rules and skin weights.

Coordinates: Blender's, metres. Z up, the character faces -Y, her left is +X.
"""
import math
from mathutils import Vector

# per-vertex attributes carried to the glTF:
#   col   sRGB albedo (r, g, b) and a = ambient occlusion (1 open .. 0 enclosed)  -> COLOR_0
#   uv    part-specific parametric coordinates                                   -> TEXCOORD_0
#   aux   (material id, extra)                                                    -> TEXCOORD_1
# material ids (godot/characters/shaders/char_common.gdshaderinc must agree):
M_SKIN, M_FACE, M_HAIR, M_CLOTH, M_HAT_TOP, M_HAT_UNDER, M_STRAW, M_WOOD, M_ROPE, M_TIE = range(10)


class Part:
    def __init__(self, name, mat=M_CLOTH):
        self.name = name
        self.mat = mat
        self.v = []          # Vector
        self.f = []          # tuples of local indices
        self.col = []        # (r, g, b, a)
        self.uv = []         # (u, v)
        self.aux = []        # (mat, extra)
        self.nrm = {}        # local index -> custom normal (Vector), optional
        self.w = None        # list of {bone: weight}, filled by the rigger
        self.tag = []        # free per-vertex data for the rigger (dict)

    def add(self, p, col=(1, 1, 1, 1), uv=(0, 0), aux=None, tag=None):
        self.v.append(Vector(p))
        self.col.append(tuple(col) if len(col) == 4 else (col[0], col[1], col[2], 1.0))
        self.uv.append(tuple(uv))
        self.aux.append(aux if aux is not None else (self.mat, 0.0))
        self.tag.append(tag if tag is not None else {})
        return len(self.v) - 1

    def extend(self, other):
        base = len(self.v)
        self.v += [Vector(p) for p in other.v]
        self.col += other.col
        self.uv += other.uv
        self.aux += other.aux
        self.tag += other.tag
        self.f += [tuple(i + base for i in face) for face in other.f]
        for k, n in other.nrm.items():
            self.nrm[k + base] = n
        return self

    def transform(self, fn):
        """fn(Vector) -> Vector applied to every vertex (normals are recomputed by Blender)."""
        self.v = [Vector(fn(p)) for p in self.v]
        return self


def grid(part, nu, nv, pos, close_v=False, pole0=False, pole1=False, col=None, uvf=None, auxf=None,
         tagf=None, flip=False):
    """A (nu + 1) x (nv or nv + 1) grid of vertices pos(u, v), u in [0, 1] along, v in [0, 1] around.
    close_v: the v direction wraps (nv columns, no seam duplicate).
    pole0 / pole1: the row u = 0 / u = 1 is a single vertex (fan of triangles).
    col(u, v) -> rgba; uvf(u, v) -> uv (default (u, v)); auxf(u, v) -> (mat, extra); tagf(u, v) -> dict.
    flip: reverse the winding (normals point the other way).
    Returns the index rows (list of lists of part indices)."""
    cols = nv if close_v else nv + 1
    rows = []
    for i in range(nu + 1):
        u = i / nu
        row = []
        single = (i == 0 and pole0) or (i == nu and pole1)
        for j in range(cols):
            v = j / nv
            if single and j > 0:
                row.append(row[0])
                continue
            vv = 0.0 if single else v
            idx = part.add(pos(u, vv),
                           col(u, vv) if col else (1, 1, 1, 1),
                           uvf(u, vv) if uvf else (u, vv),
                           auxf(u, vv) if auxf else None,
                           tagf(u, vv) if tagf else None)
            row.append(idx)
        rows.append(row)
    for i in range(nu):
        a_row, b_row = rows[i], rows[i + 1]
        for j in range(nv):
            j1 = (j + 1) % cols if close_v else j + 1
            a, b, c, d = a_row[j], a_row[j1], b_row[j1], b_row[j]
            quad = [a, b, c, d]
            # drop repeated pole vertices -> triangles
            uniq = []
            for q in quad:
                if q not in uniq:
                    uniq.append(q)
            if len(uniq) < 3:
                continue
            if flip:
                uniq.reverse()
            part.f.append(tuple(uniq))
    return rows


def cap(part, ring, centre, col=(1, 1, 1, 1), uv=(0.5, 0.5), aux=None, flip=False):
    """Close a ring of indices with a fan around a new centre vertex."""
    c = part.add(centre, col, uv, aux)
    n = len(ring)
    for j in range(n):
        a, b = ring[j], ring[(j + 1) % n]
        part.f.append((c, b, a) if not flip else (c, a, b))
    return c


# ------------------------------------------------------------------------------------------------
# curves and frames

def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def smoother(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def interp(table, x):
    """Piecewise smooth (Catmull-Rom) interpolation of [(x, y), ...] sorted by x; y may be a float or a
    tuple / Vector."""
    xs = [p[0] for p in table]
    if x <= xs[0]:
        return _val(table[0][1])
    if x >= xs[-1]:
        return _val(table[-1][1])
    for i in range(len(table) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            p0 = _val(table[max(0, i - 1)][1])
            p1 = _val(table[i][1])
            p2 = _val(table[i + 1][1])
            p3 = _val(table[min(len(table) - 1, i + 2)][1])
            # non-uniform spacing: scale tangents by the neighbouring intervals
            h0 = xs[i] - xs[max(0, i - 1)] or (xs[i + 1] - xs[i])
            h1 = xs[i + 1] - xs[i]
            h2 = xs[min(len(table) - 1, i + 2)] - xs[i + 1] or h1
            m1 = (p2 - p0) * (h1 / (h0 + h1))
            m2 = (p3 - p1) * (h1 / (h1 + h2))
            t2, t3 = t * t, t * t * t
            return (2 * t3 - 3 * t2 + 1) * p1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2 + (t3 - t2) * m2
    return _val(table[-1][1])


def _val(y):
    if isinstance(y, (tuple, list)):
        return Vector(y)
    return y


def bezier(p0, p1, p2, p3, t):
    s = 1 - t
    return p0 * (s * s * s) + p1 * (3 * s * s * t) + p2 * (3 * s * t * t) + p3 * (t * t * t)


class Path:
    """A smooth 3D curve through control points (Catmull-Rom), sampled by arc length, with rotation-
    minimising frames (tangent T, normal N, binormal B). `up` seeds the first normal."""

    def __init__(self, pts, up=(0, -1, 0), samples=200):
        pts = [Vector(p) for p in pts]
        n = len(pts)
        raw = []
        for k in range(samples + 1):
            t = k / samples * (n - 1)
            i = min(n - 2, int(t))
            f = t - i
            p0 = pts[max(0, i - 1)]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[min(n - 1, i + 2)]
            f2, f3 = f * f, f * f * f
            raw.append(0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * f3))
        self.p = raw
        self.s = [0.0]
        for k in range(1, len(raw)):
            self.s.append(self.s[-1] + (raw[k] - raw[k - 1]).length)
        self.length = self.s[-1]
        # tangents
        self.t = []
        for k in range(len(raw)):
            a = raw[max(0, k - 1)]
            b = raw[min(len(raw) - 1, k + 1)]
            self.t.append((b - a).normalized())
        # rotation-minimising frames (double reflection, Wang et al. 2008)
        up = Vector(up)
        t0 = self.t[0]
        n0 = (up - t0 * up.dot(t0))
        if n0.length < 1e-6:
            n0 = t0.orthogonal()
        n0.normalize()
        self.n = [n0]
        for k in range(len(raw) - 1):
            v1 = raw[k + 1] - raw[k]
            c1 = v1.dot(v1)
            if c1 < 1e-12:
                self.n.append(self.n[-1].copy())
                continue
            rL = self.n[-1] - (2 / c1) * v1.dot(self.n[-1]) * v1
            tL = self.t[k] - (2 / c1) * v1.dot(self.t[k]) * v1
            v2 = self.t[k + 1] - tL
            c2 = v2.dot(v2)
            nn = rL - (2 / c2) * v2.dot(rL) * v2 if c2 > 1e-12 else rL
            self.n.append(nn.normalized())
        self.b = [self.t[k].cross(self.n[k]).normalized() for k in range(len(raw))]

    def at(self, u):
        """Position, tangent, normal, binormal at arc-length fraction u in [0, 1]."""
        target = min(1.0, max(0.0, u)) * self.length
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.s[mid] < target:
                lo = mid
            else:
                hi = mid
        seg = self.s[hi] - self.s[lo]
        f = 0.0 if seg < 1e-12 else (target - self.s[lo]) / seg
        p = self.p[lo].lerp(self.p[hi], f)
        t = self.t[lo].lerp(self.t[hi], f).normalized()
        n = self.n[lo].lerp(self.n[hi], f)
        n = (n - t * n.dot(t)).normalized()
        b = t.cross(n).normalized()
        return p, t, n, b


def sweep(part, path, nu, nv, section, close_v=True, pole0=False, pole1=False, col=None, uvf=None,
          auxf=None, tagf=None, flip=False):
    """A tube along `path`: section(u, angle) -> (a, b) offsets along the frame's normal N and binormal
    B (angle = v * 2 pi). The tube's cross-section can be any closed (or open) shape."""
    def pos(u, v):
        p, t, n, b = path.at(u)
        a, bb = section(u, v * 2 * math.pi)
        return p + n * a + b * bb
    return grid(part, nu, nv, pos, close_v=close_v, pole0=pole0, pole1=pole1, col=col, uvf=uvf,
                auxf=auxf, tagf=tagf, flip=flip)


def superellipse(angle, rx, ry, n=2.0):
    """Point on a superellipse of semi-axes rx, ry and exponent n (2 = ellipse, > 2 squarer)."""
    c, s = math.cos(angle), math.sin(angle)
    e = 2.0 / n
    return (rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s))


def hex_to_rgb(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix_col(c1, c2, t):
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(4))
