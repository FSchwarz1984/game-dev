"""A zoomed crop of a view with a labelled pixel grid (view-local coordinates).
usage: gridcrop.py VIEW u0 v0 u1 v1 ZOOM STEP OUT"""
import os
import sys
from PIL import Image, ImageDraw
C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
v, u0, v0, u1, v1, z, step, out = sys.argv[1], *map(int, sys.argv[2:8]), sys.argv[8]
im = Image.open('%s/ref/crop_%s.png' % (C6, v)).convert('RGB')
c = im.crop((u0, v0, u1, v1)).resize(((u1 - u0) * z, (v1 - v0) * z), Image.NEAREST)
d = ImageDraw.Draw(c)
for u in range((u0 // step + 1) * step, u1, step):
    X = (u - u0) * z
    d.line([(X, 0), (X, c.height)], fill=(0, 200, 255) if u % (step * 5) else (255, 0, 255), width=1)
    d.text((X + 2, 2), str(u), fill=(0, 120, 255))
for vv in range((v0 // step + 1) * step, v1, step):
    Y = (vv - v0) * z
    d.line([(0, Y), (c.width, Y)], fill=(0, 200, 255) if vv % (step * 5) else (255, 0, 255), width=1)
    d.text((2, Y + 2), str(vv), fill=(255, 0, 0))
c.save(out)
print(out, c.size)
