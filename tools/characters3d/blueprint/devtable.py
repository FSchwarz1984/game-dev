"""The keypoint deviation table: the sheet's keypoints (read by hand on the gridded crops, ref/
g_*.png; silhouette points also measured automatically on the sheet's mask) against the model's,
measured exactly on the per-part ID renders (bp_ids.py). Sheet-local pixels of each view's crop.
usage: devtable.py IDSDIR OUT.md"""
import os
import json, sys
import numpy as np
from PIL import Image
C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = 1.90 / 660.0
NAT = 30.0 * S
idd, out = sys.argv[1], sys.argv[2]
meta = json.load(open(idd + '/ids.json'))
IDS, PAD = meta['ids'], meta['pad']
frames = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames.json')))


def part_mask(view, names):
    a = np.asarray(Image.open('%s/ids_%s.png' % (idd, view)).convert('RGBA')).astype(int)
    m = np.zeros(a.shape[:2], bool)
    for n in names:
        c = IDS[n]
        m |= (np.abs(a[:, :, :3] - np.array(c)).sum(-1) < 6) & (a[:, :, 3] > 128)
    return m


def pts(m):
    ys, xs = np.where(m)
    return xs - PAD, ys - PAD


def sheet_mask(view):
    return np.load('%s/ref/mask_%s.npy' % (C6, view))


rows = []


def add(view, name, sheet, model, how):
    rows.append((view, name, sheet, model, how))


# ---------------------------------------------------------------- front
ax = frames['front']['axis']
hat = part_mask('front', ['hat', 'hat_band'])
xs, ys = pts(hat)
sm = sheet_mask('front')
sy, sx = np.where(sm[:170])
il, ir = xs.argmin(), xs.argmax()
add('front', 'hat: width', int(sx.max() - sx.min()), int(xs.max() - xs.min()), 'mask')
add('front', 'hat: left tip, row', int(sy[sx.argmin()]), int(ys[il]), 'mask')
add('front', 'hat: right tip, row', int(sy[sx.argmax()]), int(ys[ir]), 'mask')
add('front', 'hat: apex, row', int(np.where(sm.any(axis=1))[0].min()), int(ys.min()), 'mask')
add('front', 'hat: height (apex to the tips\' mean row)', round((sy[sx.argmin()] + sy[sx.argmax()]) / 2.0 - np.where(sm.any(axis=1))[0].min(), 1),
    round((ys[il] + ys[ir]) / 2.0 - ys.min(), 1), 'mask')
head = part_mask('front', ['head'])
xs, ys = pts(head)
add('front', 'chin, row', 232, int(ys.max()), 'sheet by hand')
add('front', 'face: width at the cheeks', 117, int(xs[(ys > 190) & (ys < 200)].max() - xs[(ys > 190) & (ys < 200)].min()), 'sheet by hand')
from kasasagi.design import D, hf
add('front', 'eye line (centre), row', 172, round(660 - D['eye_h'] / S, 1), 'model: landmark')
add('front', 'eye centres, half spacing', 33, round(3.5 / 30 / S - 1.0 / 30 / S * 1.0, 1), 'model: stamp columns')
bangs = part_mask('front', ['bangs'])
xs, ys = pts(bangs)
c = (xs > -40 + ax) & (xs < 40 + ax)
add('front', 'bangs cut (centre), row', 150, int(ys[c].max()), 'sheet by hand')
collar = part_mask('front', ['collar'])
xs, ys = pts(collar)
add('front', 'collar V point, row', 300, int(ys.max()), 'sheet by hand')
obi = part_mask('front', ['obi', 'band'])
xs, ys = pts(obi)
c = np.abs(xs - (ax - 40)) < 3
add('front', 'obi top, row', 323, int(ys[c].min()), 'sheet by hand')
add('front', 'obi bottom, row', 357, int(ys[c].max()), 'sheet by hand')
bow = part_mask('front', ['bow'])
xs, ys = pts(bow)
add('front', 'bow knot, column from the axis', 25, round(float(xs.mean() - ax), 1), 'sheet by hand')
add('front', 'bow knot, row', 345, round(float(ys.mean()), 1), 'sheet by hand')
add('front', 'shoulder joint (the kosode\'s shoulder point), row', 262, round(660 - D['shoulder_z'] / S, 1), 'model: design')
sl = part_mask('front', ['sleeve'])
xs, ys = pts(sl)
left = xs < ax
cuff = xs < ax - 160
add('front', 'left cuff: top (where the hand comes out), row', 355, int(ys[cuff].min()), 'sheet by hand')
add('front', 'left sleeve: lowest row', 480, int(ys[left].max()), 'sheet by hand')
add('front', 'left sleeve: outermost column from the axis', 45 - ax, int(xs[left].min() - ax), 'sheet by hand')
add('front', 'right sleeve: lowest row', 470, int(ys[~left].max()), 'sheet by hand')
hand = part_mask('front', ['hand'])
xs, ys = pts(hand)
lm = sm[340:430]
hy, hx = np.where(lm)
add('front', 'left hand tip, column from the axis', int(hx.min() - ax), int(xs.min() - ax), 'mask')
add('front', 'right hand tip, column from the axis', int(hx.max() - ax), int(xs.max() - ax), 'mask')
coat = part_mask('front', ['coat'])
xs, ys = pts(coat)
lc = xs < ax
add('front', 'coat hem: lowest left corner, row', 582, int(ys[lc].max()), 'sheet by hand')
add('front', 'coat hem: lowest left corner, column from the axis', 90 - ax, int(xs[lc][ys[lc] == ys[lc].max()].mean() - ax), 'sheet by hand')
add('front', 'trouser cuff, row', 572, round(660 - D['cuff_z'] / S, 1), 'model: design')
foot = part_mask('front', ['foot'])
xs, ys = pts(foot)
add('front', 'ankle (top of the tabi), row', 600, int(ys.min()), 'sheet by hand')
add('front', 'sole, row', int(np.where(sm.any(axis=1))[0].max()), int(ys.max()), 'mask')
fl = xs < ax
add('front', 'left foot centre, column from the axis', 152 - ax, round(float(xs[fl].mean() - ax), 1), 'sheet by hand')
add('front', 'foot width', 65, int(xs[fl].max() - xs[fl].min()), 'sheet by hand')
# ---------------------------------------------------------------- side
ax = frames['side']['axis']
hat = part_mask('side', ['hat'])
xs, ys = pts(hat)
add('side', 'hat: front tip, column from the axis', 5 - ax, int(xs.min() - ax), 'sheet by hand (front view wins: 1.24 m)')
add('side', 'hat: front tip, row', 62, int(ys[xs.argmin()]), 'sheet by hand')
add('side', 'hat: back tip, column from the axis', 355 - ax, int(xs.max() - ax), 'sheet by hand (clipped by the next figure)')
add('side', 'hat: back tip, row', 165, int(ys[xs.argmax()]), 'sheet by hand')
add('side', 'hat: apex, column from the axis', 255 - ax, int(xs[ys.argmin()] - ax), 'sheet by hand')
head = part_mask('side', ['head'])
xs, ys = pts(head)
band = (ys > 150) & (ys < 245)
add('side', 'face front (nose), column from the axis', 105 - ax, int(xs[band].min() - ax), 'sheet by hand')
add('side', 'chin, row', 230, int(ys.max()), 'sheet by hand')
mant = part_mask('side', ['hair_mantle'])
xs, ys = pts(mant)
add('side', 'back of the hair (shoulders), column from the axis', 335 - ax, int(xs[(ys > 250) & (ys < 400)].max() - ax), 'sheet by hand')
add('side', 'hair end, row', 485, int(ys.max()), 'sheet by hand')
coat = part_mask('side', ['coat'])
xs, ys = pts(coat)
b = (ys > 420) & (ys < 560)
add('side', 'coat front, column from the axis', 75 - ax, int(xs[b].min() - ax), 'sheet by hand')
add('side', 'coat back, column from the axis', 272 - ax, int(xs[b].max() - ax), 'sheet by hand')
foot = part_mask('side', ['foot'])
xs, ys = pts(foot)
add('side', 'toe, column from the axis', 112 - ax, int(xs.min() - ax), 'sheet by hand')
add('side', 'heel, column from the axis', 215 - ax, int(xs.max() - ax), 'sheet by hand')
sl = part_mask('side', ['sleeve'])
xs, ys = pts(sl)
add('side', 'sleeve: lowest row', 488, int(ys.max()), 'sheet by hand')
# ---------------------------------------------------------------- back
ax = frames['back']['axis']
mant = part_mask('back', ['hair_mantle'])
xs, ys = pts(mant)
add('back', 'hair end, row', 490, int(ys.max()), 'sheet by hand')
r300 = ys == 300
add('back', 'hair width at row 300', 215, int(xs[r300].max() - xs[r300].min()) if r300.any() else None, 'sheet by hand')
with open(out, 'w') as f:
    f.write('| view | keypoint | sheet | model | model - sheet (sheet px) | (m) | (game native px) | how the sheet value was read |\n')
    f.write('|---|---|---|---|---|---|---|---|\n')
    for v, k, a, b, how in rows:
        if a is None or b is None:
            f.write('| %s | %s | %s | %s | - | - | - | %s |\n' % (v, k, a, b, how))
        else:
            d = b - a
            f.write('| %s | %s | %s | %s | %+.0f | %+.3f | %+.1f | %s |\n' % (v, k, a, b, d, d * S, d * NAT, how))
print(open(out).read())
