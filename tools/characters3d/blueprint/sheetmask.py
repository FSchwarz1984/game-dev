"""Main-figure masks of the turnaround views (images only). The full sheet is 2048x832; each view is
cut by its x range; touching neighbours (hat brims) are cut off by the main connected component,
with a forced split column where two figures touch. Writes ref/mask_<view>.npy (bool) and the
view's class map restricted to the figure. Coordinates stay in full-sheet pixels (x0 offset saved)."""
import os
import json, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetclass as SC

C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
im = Image.open(os.environ['C3D_SHEET']).convert('RGB')   # the ChatGPT turnaround png (images only)
A = np.asarray(im)
fg = A.min(axis=2) <= 238
# the two figures that touch (side, three-quarter back): split at the emptiest column between them
cols = fg[:, 1150:1200].sum(axis=0)
split = 1150 + int(cols.argmin())
fg[:, split] = False
lab, n = ndi.label(fg)
views = {'front': (45, 482), 'q_front': (456, 880), 'side': (844, split - 1), 'q_back': (split + 1, 1586),
         'back': (1575, 2002)}
info = {'split': split}
for v, (x0, x1) in views.items():
    # the component with the most pixels in the view's central columns
    cx = (x0 + x1) // 2
    ids, counts = np.unique(lab[:, cx - 40:cx + 40][fg[:, cx - 40:cx + 40]], return_counts=True)
    main = ids[counts.argmax()]
    m = lab == main
    # small holes inside the figure (white details) are part of it
    m = ndi.binary_fill_holes(m)
    ys, xs = np.where(m)
    bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
    sub = m[by0:by1 + 1, bx0:bx1 + 1]
    cls = SC.classify(A[by0:by1 + 1, bx0:bx1 + 1])
    cls[~sub] = 0
    np.save('%s/ref/mask_%s.npy' % (C6, v), sub)
    np.save('%s/ref/cls_%s.npy' % (C6, v), cls.astype(np.uint8))
    pv = np.zeros(sub.shape + (3,), np.uint8)
    for i, nme in enumerate(SC.CLASSES):
        pv[cls == i] = SC.PREVIEW[nme]
    Image.fromarray(pv).save('%s/ref/cls_%s.png' % (C6, v))
    Image.fromarray(A[by0:by1 + 1, bx0:bx1 + 1]).save('%s/ref/crop_%s.png' % (C6, v))
    info[v] = {'x0': int(bx0), 'x1': int(bx1), 'y0': int(by0), 'y1': int(by1), 'area': int(sub.sum())}
    print(v, info[v])
json.dump(info, open(C6 + '/ref/views.json', 'w'), indent=1)
