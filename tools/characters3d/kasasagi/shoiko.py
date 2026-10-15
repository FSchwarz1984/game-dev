"""The carrying frame (背負子, shoiko) she wears from the first morning (the old porter's frame; さぢ
later sits on its top bar). A separate prop: the game hangs it on her chest bone (BoneAttachment3D)
and can also stand it on the ground on its own. Weathered wood, rope straps; every member at least
~1.2 native px thick (4 cm) so it never breaks into dots.
"""
import math
from mathutils import Vector

from c3d.surf import Part, sweep, Path, M_WOOD, M_ROPE, mix_col
from kasasagi import palette as C

BACK_Y = 0.235          # the frame stands this far behind her (over the long hair)
RAIL_X = 0.135


def _beam(part, a, b, w, h, col, mat=M_WOOD, up=(0, 0, 1), segs=2):
    """A member between a and b with a rounded-rectangle section (w across, h the other way)."""
    path = Path([a, a.lerp(b, 0.5), b], up=up)

    def section(u, ang):
        c, s = math.cos(ang), math.sin(ang)
        e = 2.0 / 4.0          # rounded box
        return (h * 0.5 * math.copysign(abs(c) ** e, c), w * 0.5 * math.copysign(abs(s) ** e, s))

    rows = sweep(part, path, segs, 8, section, col=lambda u, v: col, auxf=lambda u, v: (mat, 0.0),
                 tagf=lambda u, v: {'seg': 'pack'})
    # caps
    from c3d.surf import cap
    p0, t0, _, _ = path.at(0.0)
    p1, t1, _, _ = path.at(1.0)
    cap(part, rows[0], p0, col=col, aux=(mat, 0.0), flip=True)
    cap(part, rows[-1], p1, col=col, aux=(mat, 0.0))
    return part


def shoiko():
    part = Part('shoiko', M_WOOD)
    y = BACK_Y
    wood = C.WOOD
    deep = C.WOOD_DEEP
    # two rails, a little splayed at the foot, their tops worn round
    for sx in (1, -1):
        _beam(part, Vector((sx * RAIL_X * 1.08, y + 0.02, 0.47)), Vector((sx * RAIL_X, y, 1.20)), 0.042, 0.036, wood,
              up=(0, -1, 0), segs=3)
    # cross bars
    for z, wcol in ((0.64, deep), (0.88, wood), (1.12, wood)):
        _beam(part, Vector((-RAIL_X - 0.012, y, z)), Vector((RAIL_X + 0.012, y, z)), 0.04, 0.034, wcol, up=(0, -1, 0))
    # the shelf at the foot: two arms back, a slatted platform
    for sx in (1, -1):
        _beam(part, Vector((sx * RAIL_X * 1.06, y + 0.01, 0.52)), Vector((sx * RAIL_X * 1.06, y + 0.20, 0.53)),
              0.036, 0.034, deep, up=(0, 0, 1))
    for k in range(3):
        yy = y + 0.05 + k * 0.06
        _beam(part, Vector((-RAIL_X * 1.1, yy, 0.55)), Vector((RAIL_X * 1.1, yy, 0.55)), 0.04, 0.03, wood,
              up=(0, 1, 0))
    # rope straps over her shoulders and back under her arms
    for sx in (1, -1):
        pts = [Vector((sx * 0.10, y, 1.08)), Vector((sx * 0.11, 0.08, 1.02)), Vector((sx * 0.125, -0.02, 0.985)),
               Vector((sx * 0.13, -0.085, 0.90)), Vector((sx * 0.15, -0.06, 0.80)), Vector((sx * 0.165, 0.06, 0.74)),
               Vector((sx * RAIL_X, y, 0.70))]
        path = Path(pts, up=(sx, 0, 0))
        sweep(part, path, 14, 6, lambda u, a: (0.018 * math.cos(a), 0.022 * math.sin(a)),
              col=lambda u, v: C.ROPE, auxf=lambda u, v: (M_ROPE, 0.0), tagf=lambda u, v: {'seg': 'pack'})
    return part
