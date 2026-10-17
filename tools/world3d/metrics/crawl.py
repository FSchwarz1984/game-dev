#!/usr/bin/env python3
"""crawl.py <base> <D> [tol...] -- how much of the picture changes when the camera steps one pixel.
<base>_a.png: the frame; <base>_e.png: the camera one focus-plane pixel east; <base>_n.png: one up;
<base>_d.png: depth map (cm = R*256 + G, class = B / 40, white = no post: characters, particles).
On the focus plane e(x, y) == a(x + 1, y) and n(x, y) == a(x, y - 1) exactly. Counts the pixels that
differ by more than tol code values (any channel), by depth band: near (d < D - 1.5 m), focus
(|d - D| <= 1.5 m), far (d > D + 1.5 m). Writes <base>_crawl.png (a, with the changed pixels red)."""
import sys
from PIL import Image
import numpy as np

base = sys.argv[1]
D = float(sys.argv[2])
tols = [int(t) for t in sys.argv[3:]] or [0, 3]
a = np.asarray(Image.open(base + '_a.png').convert('RGB')).astype(np.int16)
e = np.asarray(Image.open(base + '_e.png').convert('RGB')).astype(np.int16)
n = np.asarray(Image.open(base + '_n.png').convert('RGB')).astype(np.int16)
dm = np.asarray(Image.open(base + '_d.png').convert('RGB')).astype(np.int32)
H, W, _ = a.shape
coded = ~((dm[..., 0] == 255) & (dm[..., 1] == 255) & (dm[..., 2] == 255))
depth = (dm[..., 0] * 256 + dm[..., 1]) / 100.0
band = np.full((H, W), -1, np.int8)
band[coded & (depth < D - 1.5)] = 0
band[coded & (np.abs(depth - D) <= 1.5)] = 1
band[coded & (depth > D + 1.5)] = 2
names = ['near', 'focus', 'far']
out = {}
# east: e[:, x] vs a[:, x + 1]; the source band is a's
de = np.abs(e[:, :W - 1] - a[:, 1:]).max(axis=2)
be = band[:, 1:]
# up: n[y] vs a[y - 1]
dn = np.abs(n[1:, :] - a[:H - 1, :]).max(axis=2)
bn = band[:H - 1, :]
line = []
for tol in tols:
    for nm, dd, bb in (('E', de, be), ('N', dn, bn)):
        parts = []
        for k in range(3):
            m = bb == k
            tot = int(m.sum())
            ch = int(((dd > tol) & m).sum())
            parts.append('%s %5.1f%% (%d/%d)' % (names[k], 100.0 * ch / max(tot, 1), ch, tot))
        line.append('tol %d %s: %s' % (tol, nm, '  '.join(parts)))
print(base.split('/')[-1], 'D=%.1f' % D, 'depth %.1f..%.1f' % (depth[coded].min(), depth[coded].max()))
for l in line:
    print('  ' + l)
# picture: a, changed (east, tol 3) in red, uncoded in blue tint
vis = a.astype(np.uint8).copy()
mask = np.zeros((H, W), bool)
mask[:, 1:] = (de > 3)
vis[mask] = (vis[mask] * 0.3 + np.array([255, 30, 30]) * 0.7).astype(np.uint8)
vis[~coded] = (vis[~coded] * 0.6 + np.array([40, 80, 255]) * 0.4).astype(np.uint8)
Image.fromarray(vis).save(base + '_crawl.png')
