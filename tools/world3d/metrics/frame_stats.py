# Whole-frame colour statistics for comparing looks (python3 -I frame_stats.py <frame.png> [...]):
# per frame: L* median / p10 / p90, C* mean, and the share, L*, C* and hue of the pixel families that
# carry a look: greens (hue 95-170), warm earth (hue 40-95, C* 4-30), cool shade (hue 170-280).
import sys

import numpy as np
from PIL import Image


def lab(a):
    a = a.astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return 116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])


def stats(path):
    L, A, B = lab(np.asarray(Image.open(path).convert('RGB')))
    C = np.hypot(A, B)
    H = (np.degrees(np.arctan2(B, A)) + 360) % 360
    out = {'L50': np.median(L), 'L10': np.percentile(L, 10), 'L90': np.percentile(L, 90), 'C': C.mean()}
    fams = {'green': (H > 95) & (H < 170) & (C > 5), 'earth': (H > 40) & (H <= 95) & (C > 4) & (C < 30),
            'cool': (H >= 170) & (H < 280) & (C > 3)}
    for k, m in fams.items():
        if m.any():
            hm = np.degrees(np.arctan2(np.sin(np.radians(H[m])).mean(), np.cos(np.radians(H[m])).mean())) % 360
            out[k] = (m.mean() * 100, np.median(L[m]), np.median(C[m]), hm)
        else:
            out[k] = (0, 0, 0, 0)
    return out


if __name__ == '__main__':
    print('%-34s %5s %5s %5s %5s | %-22s | %-22s | %-22s' % ('frame', 'L50', 'L10', 'L90', 'C*', 'green %/L*/C*/h', 'earth %/L*/C*/h', 'cool %/L*/C*/h'))
    for p in sys.argv[1:]:
        s = stats(p)
        f = lambda t: '%4.0f%% %4.1f %4.1f %4.0f' % t
        print('%-34s %5.1f %5.1f %5.1f %5.1f | %-22s | %-22s | %-22s' % (p.split('/')[-2][-12:] + '/' + p.split('/')[-1][:20], s['L50'], s['L10'], s['L90'], s['C'], f(s['green']), f(s['earth']), f(s['cool'])))
