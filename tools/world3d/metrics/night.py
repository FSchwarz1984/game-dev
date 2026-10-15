# Night lamp metrics (python3 -I night.py <frame with lamps>.png <same frame, lamps off>.png):
# where the lamps add light, the L* they add (the rings), the jump across the outermost seam (the lit
# pixel at the pool's edge against its unlit neighbour, both in the lamp frame), and the value
# levels of the night outside the lamps.
import sys

import numpy as np
from PIL import Image


def lab_L(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    f = np.where(y > 0.008856, np.cbrt(y), 7.787 * y + 16 / 116)
    return 116 * f - 16


L = lab_L(sys.argv[1])
L0 = lab_L(sys.argv[2])
add = L - L0
lit = add > 1.0
print('lamp-lit px %.1f %%' % (lit.mean() * 100))
if lit.any():
    v = add[lit]
    hist, edges = np.histogram(v, bins=[1, 3, 6, 10, 15, 20, 30, 40, 60, 100])
    print('L* added by the lamps: ' + ', '.join('%d-%d: %.0f%%' % (edges[i], edges[i + 1], hist[i] * 100.0 / v.size) for i in range(len(hist))))
# the outermost seam: lit pixels with an unlit 4-neighbour (both read in the lamp frame)
jumps = []
H, W = L.shape
for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    nb_lit = np.roll(np.roll(lit, dy, axis=0), dx, axis=1)
    nb_L = np.roll(np.roll(L, dy, axis=0), dx, axis=1)
    m = lit & ~nb_lit
    m[:1, :] = m[-1:, :] = False
    m[:, :1] = m[:, -1:] = False
    jumps.append((L - nb_L)[m])
j = np.concatenate(jumps)
if j.size:
    print('outermost seam (lit edge vs unlit neighbour): L* jump median %.1f, p75 %.1f, p90 %.1f (n=%d)' % (
        np.median(j), np.percentile(j, 75), np.percentile(j, 90), j.size))
out = L0[~lit]
print('outside the lamps: L* p10 %.1f, p25 %.1f, p50 %.1f, p75 %.1f, p90 %.1f, p97 %.1f' % tuple(np.percentile(out, [10, 25, 50, 75, 90, 97])))
h2, e2 = np.histogram(out, bins=np.arange(0, 60, 4))
print('  histogram (4 L* bins): ' + ' '.join('%d:%.0f%%' % (e2[i], h2[i] * 100.0 / out.size) for i in range(len(h2)) if h2[i] > 0))
