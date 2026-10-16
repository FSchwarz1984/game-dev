# Colour of named zones in two frames of the same view (python3 -I zones.py <spec.json> [<out.png>]):
# for each zone (a rectangle in native pixels, the same material in both frames) the median CIELAB
# of frame A and of frame B, their L*, C*, h, and the difference (CIEDE2000, and dL*, dC*, dh).
# Used for the round-5 colour roll-back: round 3 (A, 480x270) against now (B, 640x360, whose centre
# 480x270 is the same view: b_offset = [80, 45]). Zones may differ between the frames where the
# scene moved (zones_b overrides). With <out.png>: both frames with the zones drawn, for checking.
#
# spec: {"pairs": [{"name": ..., "a": path, "b": path, "b_offset": [80, 45],
#                   "zones": {"grass": [x0, y0, x1, y1], ...}, "zones_b": {...}}]}
import json
import sys

import numpy as np
from PIL import Image, ImageDraw


def lab(a):
    a = a.astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de2000(l1, l2):
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm = (L1 + L2) / 2
    Cmp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    else:
        hm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.2 * np.cos(np.radians(4 * hm - 63))
    dth = 30 * np.exp(-((hm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    Sc = 1 + 0.045 * Cmp
    Sh = 1 + 0.015 * Cmp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def zone(img_lab, r):
    x0, y0, x1, y1 = r
    z = img_lab[y0:y1, x0:x1].reshape(-1, 3)
    return np.median(z, axis=0)


def lch(v):
    return v[0], float(np.hypot(v[1], v[2])), float(np.degrees(np.arctan2(v[2], v[1])) % 360)


def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2] if len(sys.argv) > 2 else None
    sheets = []
    print('%-22s %-14s | %5s %5s %5s | %5s %5s %5s | %5s %6s %6s %6s' % ('view', 'zone', 'L*A', 'C*A', 'hA', 'L*B', 'C*B', 'hB', 'dE00', 'dL', 'dC', 'dh'))
    for p in spec['pairs']:
        A = np.asarray(Image.open(p['a']).convert('RGB'))
        B = np.asarray(Image.open(p['b']).convert('RGB'))
        la, lb = lab(A), lab(B)
        ox, oy = p.get('b_offset', [0, 0])
        zb = p.get('zones_b', {})
        des = []
        for name, r in p['zones'].items():
            rb = zb.get(name, [r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy])
            va, vb = zone(la, r), zone(lb, rb)
            d = de2000(va, vb)
            des.append(d)
            La, Ca, ha = lch(va)
            Lb, Cb, hb = lch(vb)
            dh = (hb - ha + 180) % 360 - 180
            print('%-22s %-14s | %5.1f %5.1f %5.0f | %5.1f %5.1f %5.0f | %5.1f %+6.1f %+6.1f %+6.0f' % (p['name'], name, La, Ca, ha, Lb, Cb, hb, d, Lb - La, Cb - Ca, dh))
        print('%-22s %-14s mean dE00 %.1f, max %.1f' % (p['name'], '', float(np.mean(des)), float(np.max(des))))
        if out:
            ia = Image.fromarray(A).resize((A.shape[1] * 2, A.shape[0] * 2), Image.NEAREST)
            ib = Image.fromarray(B).resize((B.shape[1] * 2, B.shape[0] * 2), Image.NEAREST)
            for im, zs, off in ((ia, p['zones'], (0, 0)), (ib, {k: zb.get(k, None) for k in p['zones']}, (ox, oy))):
                d = ImageDraw.Draw(im)
                for name, r in p['zones'].items():
                    rr = zs.get(name) if zs is not p['zones'] else r
                    if rr is None:
                        rr = [r[0] + off[0], r[1] + off[1], r[2] + off[0], r[3] + off[1]]
                    d.rectangle([rr[0] * 2, rr[1] * 2, rr[2] * 2 - 1, rr[3] * 2 - 1], outline=(255, 0, 255))
                    d.text((rr[0] * 2 + 2, rr[1] * 2 + 1), name, fill=(255, 255, 255))
            s = Image.new('RGB', (ia.width + ib.width + 8, max(ia.height, ib.height)), (20, 20, 24))
            s.paste(ia, (0, 0))
            s.paste(ib, (ia.width + 8, 0))
            sheets.append(s)
    if out and sheets:
        w = max(s.width for s in sheets)
        h = sum(s.height for s in sheets) + 8 * (len(sheets) - 1)
        o = Image.new('RGB', (w, h), (20, 20, 24))
        y = 0
        for s in sheets:
            o.paste(s, (0, y))
            y += s.height + 8
        o.save(out)


if __name__ == '__main__':
    main()
