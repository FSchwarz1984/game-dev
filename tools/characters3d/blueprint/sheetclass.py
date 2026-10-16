"""Coarse colour classes of the ChatGPT turnaround (images only): background, outline, cream/white,
navy, hair, skin, red, iris. Writes a class map (.npy) and a false-colour preview per view.
usage: sheetclass.py OUTDIR view.png ..."""
import sys, os
import numpy as np
from PIL import Image

CLASSES = ['bg', 'line', 'cream', 'navy', 'hair', 'skin', 'red', 'iris', 'sole']
# representative colours (main / shadow / highlight of the colour sheet) per class
REF = {
    'cream': ['#F7EADC', '#DDD1C7', '#F8EDDF', '#F8EFE5', '#D9D1CD', '#F9EFE6', '#DFD5D3', '#F9F0E7'],
    'navy': ['#252C4B', '#242A4B', '#33395B', '#232741', '#343B5D', '#332D3B', '#22202B', '#3E3846'],
    'hair': ['#3E344A', '#231A28', '#5F5071', '#38344B', '#1E1C2A', '#454464'],
    'skin': ['#FCE4D2', '#ECC0AB', '#FCE6D5'],
    'red': ['#9B324E', '#75253D', '#AE3754'],
    'iris': ['#6F7887', '#AAAFB8'],
    'sole': ['#D5C8C0', '#C4A89A', '#F1E5D7'],
}
PREVIEW = {'bg': (255, 255, 255), 'line': (0, 0, 0), 'cream': (235, 225, 200), 'navy': (40, 50, 140),
           'hair': (110, 60, 140), 'skin': (255, 190, 160), 'red': (220, 30, 60), 'iris': (90, 160, 160),
           'sole': (200, 160, 110)}


def hexrgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def classify(a):
    a = a.astype(np.float32)
    H, W, _ = a.shape
    names, refs = [], []
    for k, hs in REF.items():
        for h in hs:
            names.append(k)
            refs.append(hexrgb(h))
    refs = np.array(refs, np.float32)
    d = ((a[:, :, None, :] - refs[None, None, :, :]) ** 2).sum(-1)
    idx = d.argmin(-1)
    dmin = d.min(-1)
    cls = np.array([CLASSES.index(n) for n in names])[idx]
    mn = a.min(-1)
    lum = a.mean(-1)
    cls[mn > 238] = 0                                   # paper
    cls[(lum < 45) & (dmin > 300)] = 1                  # ink lines
    return cls


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for p in sys.argv[2:]:
        a = np.asarray(Image.open(p).convert('RGB'))
        c = classify(a)
        base = os.path.splitext(os.path.basename(p))[0]
        np.save(os.path.join(out, base + '_cls.npy'), c.astype(np.uint8))
        pv = np.zeros(a.shape, np.uint8)
        for i, n in enumerate(CLASSES):
            pv[c == i] = PREVIEW[n]
        Image.fromarray(pv).save(os.path.join(out, base + '_cls.png'))
        print(base, a.shape, {n: int((c == i).sum()) for i, n in enumerate(CLASSES)})
