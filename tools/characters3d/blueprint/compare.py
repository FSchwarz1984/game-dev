"""Blueprint comparison: per view, the sheet's figure mask against the model's render (same frame).
Writes overlay (sheet 50% + model 50%), silhouette difference (grey both, red sheet only, blue model
only), class difference, and prints silhouette IoU at the frame's axis and at the best horizontal shift
(+-30 px), plus per-colour-class IoU.
usage: compare.py RENDERDIR OUTDIR"""
import os
import json, sys, os
import numpy as np
from PIL import Image, ImageDraw
C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetclass as SC

rd, od = sys.argv[1], sys.argv[2]
os.makedirs(od, exist_ok=True)
frames = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames.json')))
GROUPS = {'cream': ['cream', 'sole'], 'navy': ['navy'], 'dark': ['hair'], 'red': ['red'], 'skin': ['skin']}


def iou(a, b):
    u = (a | b).sum()
    return (a & b).sum() / u if u else 1.0


def shift(m, dx):
    r = np.zeros_like(m)
    if dx > 0:
        r[:, dx:] = m[:, :-dx]
    elif dx < 0:
        r[:, :dx] = m[:, -dx:]
    else:
        r = m.copy()
    return r


res = {}
panels = []
for v in frames:
    sm = np.load('%s/ref/mask_%s.npy' % (C6, v))
    sc = np.load('%s/ref/cls_%s.npy' % (C6, v))
    crop = np.asarray(Image.open('%s/ref/crop_%s.png' % (C6, v)).convert('RGB'))
    p = '%s/model_%s.png' % (rd, v)
    if not os.path.exists(p):
        continue
    mr = np.asarray(Image.open(p).convert('RGBA'))
    mm = mr[:, :, 3] > 128
    mrgb = mr[:, :, :3]
    mc = SC.classify(mrgb)
    mc[~mm] = 0
    base = iou(sm, mm)
    best = max(((iou(sm, shift(mm, dx)), dx) for dx in range(-30, 31)), key=lambda t: t[0])
    cls = {}
    for g, names in GROUPS.items():
        ids = [SC.CLASSES.index(n) for n in names]
        a = np.isin(sc, ids) & sm
        b = np.isin(mc, ids) & mm
        cls[g] = round(float(iou(a, b)), 3)
    res[v] = {'iou': round(float(base), 4), 'best_iou': round(float(best[0]), 4), 'best_dx': best[1],
              'sheet_px': int(sm.sum()), 'model_px': int(mm.sum()), 'class_iou': cls}
    # overlay
    comp = np.full(crop.shape, 255, np.uint8)
    comp[sm] = crop[sm]
    mod = np.full(crop.shape, 255, np.uint8)
    mod[mm] = mrgb[mm]
    over = (comp.astype(np.float32) * 0.5 + mod.astype(np.float32) * 0.5).astype(np.uint8)
    diff = np.full(crop.shape, 255, np.uint8)
    diff[sm & mm] = (170, 170, 170)
    diff[sm & ~mm] = (230, 40, 40)
    diff[~sm & mm] = (40, 90, 230)
    Image.fromarray(over).save('%s/overlay_%s.png' % (od, v))
    Image.fromarray(diff).save('%s/silhouette_diff_%s.png' % (od, v))
    side = np.concatenate([comp, np.full((crop.shape[0], 8, 3), 128, np.uint8), mod], axis=1)
    Image.fromarray(side).save('%s/side_by_side_%s.png' % (od, v))
    panels.append((v, comp, mod, over, diff))
json.dump(res, open(od + '/iou.json', 'w'), indent=1)
for v, r in res.items():
    print('%-8s IoU %.3f (best %.3f at dx %+d)  sheet %d model %d  %s' % (v, r['iou'], r['best_iou'], r['best_dx'],
          r['sheet_px'], r['model_px'], ' '.join('%s %.2f' % kv for kv in r['class_iou'].items())))
# one sheet: rows = views; columns = sheet, model, overlay, difference
if panels:
    Hm = max(p[1].shape[0] for p in panels)
    rows = []
    for v, *ims in panels:
        row = []
        for im in ims:
            pad = np.full((Hm, im.shape[1], 3), 255, np.uint8)
            pad[:im.shape[0]] = im
            row.append(pad)
            row.append(np.full((Hm, 6, 3), 90, np.uint8))
        rows.append(np.concatenate(row, axis=1))
    Wm = max(r.shape[1] for r in rows)
    out = np.full((sum(r.shape[0] + 24 for r in rows), Wm, 3), 255, np.uint8)
    y = 0
    img = Image.fromarray(out)
    d = ImageDraw.Draw(img)
    for (v, *_), r in zip(panels, rows):
        img.paste(Image.fromarray(r), (0, y + 20))
        rr = res[v]
        d.text((4, y + 4), '%s   silhouette IoU %.3f (best %.3f at %+d px)   colour-class IoU: %s' % (
            v, rr['iou'], rr['best_iou'], rr['best_dx'], ', '.join('%s %.2f' % kv for kv in rr['class_iou'].items())),
            fill=(0, 0, 0))
        y += r.shape[0] + 24
    img.save(od + '/blueprint_sheet.png')
    print(od + '/blueprint_sheet.png', img.size)
