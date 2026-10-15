# Colour statistics of a native frame (python3 -I measure.py <frame.png> [<same frame, no shadows>.png]):
# CIELAB L* mean / p10 / p90, C* mean, grass hue and chroma, large-area chroma (8x8 block means),
# and, given the shadowless twin, the L* drop of the same surfaces in cast shadow and the warm/cool
# split (b* of lit vs shaded pixels, hue of each).
import sys

import numpy as np
from PIL import Image


def lab(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    A = 500 * (f[..., 0] - f[..., 1])
    B = 200 * (f[..., 1] - f[..., 2])
    return L, A, B


L, A, B = lab(sys.argv[1])
C = np.hypot(A, B)
H = (np.degrees(np.arctan2(B, A)) + 360) % 360
print('L* mean %.1f  p10 %.1f  p90 %.1f   C* mean %.1f' % (L.mean(), np.percentile(L, 10), np.percentile(L, 90), C.mean()))
grass = (H > 95) & (H < 165) & (C > 8)
if grass.any():
    print('grass-like px %.0f %%: hue mean %.0f (p10 %.0f, p90 %.0f), C* mean %.1f, L* mean %.1f' % (
        grass.mean() * 100, H[grass].mean(), np.percentile(H[grass], 10), np.percentile(H[grass], 90), C[grass].mean(), L[grass].mean()))
h, w = L.shape
bh, bw = h // 8, w // 8
blk = lambda X: X[:bh * 8, :bw * 8].reshape(bh, 8, bw, 8).mean(axis=(1, 3))
Cb = np.hypot(blk(A), blk(B))
Hb = (np.degrees(np.arctan2(blk(B), blk(A))) + 360) % 360
gb = (Hb > 95) & (Hb < 165)
print('8x8 block chroma: all p95 %.1f max %.1f | grass-hued blocks (%.0f %%): p95 %.1f, share > 24: %.1f %%' % (
    np.percentile(Cb, 95), Cb.max(), gb.mean() * 100, np.percentile(Cb[gb], 95) if gb.any() else 0,
    (Cb[gb] > 24).mean() * 100 if gb.any() else 0))
if len(sys.argv) > 2:
    L2, A2, B2 = lab(sys.argv[2])
    shade = (L2 - L) > 3.0
    print('in cast shadow: %.0f %% of px; L* lit %.1f vs shaded %.1f: drop median %.1f, mean %.1f' % (
        shade.mean() * 100, L2[shade].mean(), L[shade].mean(), np.median((L2 - L)[shade]), (L2 - L)[shade].mean()))
    lit = ~shade
    hs = (np.degrees(np.arctan2(B[shade], A[shade])) + 360) % 360
    print('b* (yellow+) of sunlit px %.1f, of the same surfaces in shadow %.1f (lit version %.1f); a* lit %.1f shade %.1f' % (
        B[lit].mean(), B[shade].mean(), B2[shade].mean(), A[lit].mean(), A[shade].mean()))
