"""Sheet crop next to the model render (white background), same box, nearest zoom.
usage: zoomcmp.py RENDERDIR VIEW u0 v0 u1 v1 ZOOM OUT"""
import os
import sys
from PIL import Image
C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
rd, v = sys.argv[1], sys.argv[2]
u0, v0, u1, v1, z = map(int, sys.argv[3:8])
out = sys.argv[8]
b = Image.open('%s/model_%s.png' % (rd, v)).convert('RGBA')
bg = Image.new('RGBA', b.size, (255, 255, 255, 255)); bg.alpha_composite(b)
box = (u0, v0, u1, v1)
W, H = (u1 - u0) * z, (v1 - v0) * z
b = bg.convert('RGB').crop(box).resize((W, H), Image.NEAREST)
a = Image.open('%s/ref/crop_%s.png' % (C6, v)).convert('RGB').crop(box).resize((W, H), Image.NEAREST)
s = Image.new('RGB', (W * 2 + 10, H), (90, 90, 90)); s.paste(a, (0, 0)); s.paste(b, (W + 10, 0)); s.save(out)
print(out, s.size)
