"""Compose sheet | model | difference for chosen views of a compare dir. usage: look.py CDIR OUT view..."""
import sys
from PIL import Image
cd, out, views = sys.argv[1], sys.argv[2], sys.argv[3:]
rows = []
for v in views:
    a = Image.open('%s/side_by_side_%s.png' % (cd, v))
    b = Image.open('%s/silhouette_diff_%s.png' % (cd, v))
    r = Image.new('RGB', (a.width + b.width + 8, max(a.height, b.height)), (90, 90, 90))
    r.paste(a, (0, 0)); r.paste(b, (a.width + 8, 0))
    rows.append(r)
W = max(r.width for r in rows); H = sum(r.height + 8 for r in rows)
s = Image.new('RGB', (W, H), (90, 90, 90)); y = 0
for r in rows:
    s.paste(r, (0, y)); y += r.height + 8
sc = float(sys.argv[0] and 1.0)
s.save(out)
print(out, s.size)
