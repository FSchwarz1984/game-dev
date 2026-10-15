# Shimmer / crawl check of a pixel-perfect recording (python3 -I shimmer.py <frames dir> [first last step]).
# For consecutive frames, find the whole-window-pixel shift that best aligns frame b with frame a on
# a central crop (the camera moves in whole native pixels plus a whole-window-pixel remainder), then
# count the pixels that still differ (sum of |RGB| > 24). Animated things (grass and leaves in the
# wind, water, particles, the two characters) differ too, so compare with a still camera.
import glob
import sys

import numpy as np
from PIL import Image

d = sys.argv[1]
fs = sorted(glob.glob(d + '/f*.png'))
a0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
a1 = int(sys.argv[3]) if len(sys.argv) > 3 else len(fs) - 2
st = int(sys.argv[4]) if len(sys.argv) > 4 else 30


def load(i):
    return np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)


rows = []
for i in range(a0, a1 + 1, st):
    a = load(i)
    b = load(i + 1)
    h, w, _ = a.shape
    m = 24
    # coarse search on every 2nd pixel, then exact
    ca = a[m:h - m:2, m:w - m:2]
    cand = []
    for dy in range(-16, 17):
        for dx in range(-16, 17):
            cb = b[m + dy:h - m + dy:2, m + dx:w - m + dx:2]
            cand.append(((np.abs(ca - cb).sum(axis=2) > 24).mean(), dx, dy))
    cand.sort()
    best = None
    for _, dx, dy in cand[:4]:
        ca2 = a[m:h - m, m:w - m]
        cb2 = b[m + dy:h - m + dy, m + dx:w - m + dx]
        v = (np.abs(ca2 - cb2).sum(axis=2) > 24).mean()
        if best is None or v < best[0]:
            best = (v, dx, dy)
    rows.append((i, best[1], best[2], best[0]))
    print('frame %4d -> %4d  shift (%+3d, %+3d) window px  differing after alignment %.2f %%' % (i, i + 1, best[1], best[2], best[0] * 100))
mv = [r[3] for r in rows if (r[1], r[2]) != (0, 0)]
stl = [r[3] for r in rows if (r[1], r[2]) == (0, 0)]
if mv:
    print('camera moving: %d pairs, mean %.2f %%, max %.2f %%' % (len(mv), np.mean(mv) * 100, np.max(mv) * 100))
if stl:
    print('camera still:  %d pairs, mean %.2f %%, max %.2f %%' % (len(stl), np.mean(stl) * 100, np.max(stl) * 100))
