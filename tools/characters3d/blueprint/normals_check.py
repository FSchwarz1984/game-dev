"""Blender: per part, the share of faces whose normal points away from the part's own centre (outward)
- a quick check of the windings (closed parts should be near 1, inner linings near 0)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mathutils import Vector
from c3d import scene as SC
SC.reset_scene(fps=30)
from kasasagi import build as KB
parts = KB.all_parts()
for part in parts:
    if not part.f:
        continue
    c = Vector((0, 0, 0))
    for p in part.v:
        c += p
    c /= len(part.v)
    out = 0
    n = 0
    for f in part.f:
        a, b, cc = part.v[f[0]], part.v[f[1]], part.v[f[2]]
        nrm = (b - a).cross(cc - a)
        if nrm.length < 1e-12:
            continue
        fc = (a + b + cc) / 3
        out += 1 if nrm.dot(fc - c) > 0 else 0
        n += 1
    # halves (two-layer parts: the outer grid first)
    h = len(part.f) // 2
    def frac(fs):
        o = m = 0
        for f in fs:
            a, b, cc = part.v[f[0]], part.v[f[1]], part.v[f[2]]
            nrm = (b - a).cross(cc - a)
            if nrm.length < 1e-12:
                continue
            fc = (a + b + cc) / 3
            o += 1 if nrm.dot(fc - c) > 0 else 0
            m += 1
        return o / max(m, 1)
    print('%-14s faces %6d outward %.2f   first half %.2f second half %.2f' % (part.name, n, out / max(n, 1), frac(part.f[:h]), frac(part.f[h:])))
