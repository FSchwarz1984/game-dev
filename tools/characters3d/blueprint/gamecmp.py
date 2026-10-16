"""Game-camera views next to the sheet's matching views at the same pixel height.
For each view: the sheet's crop (white paper) scaled down to the figure's native height in the game
render (LANCZOS), then everything blown up by nearest neighbour xN. Columns: sheet | each render dir.
usage: gamecmp.py OUT SCALE LABEL1=DIR1 [LABEL2=DIR2 ...]"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw
C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
out, sc = sys.argv[1], int(sys.argv[2])
dirs = [a.split('=', 1) for a in sys.argv[3:]]
VIEWS = [('front', '0'), ('q_front', '-45'), ('side', '-90'), ('q_back', '-135'), ('back', '180')]
BG = np.array([219, 211, 201])


def figure_box(im):
    """The figure's box in the frame's central window: pixels that differ from the stage grey right
    round them (the stage has a vignette), the cast shadow's blue-grey excluded."""
    a = np.asarray(im.convert('RGB')).astype(int)
    X0, Y0, X1, Y1 = 240, 60, 400, 250
    w = a[Y0:Y1, X0:X1]
    bg = np.median(np.concatenate([w[:, :8].reshape(-1, 3), w[:, -8:].reshape(-1, 3), w[:8].reshape(-1, 3)]), axis=0)
    d = np.abs(w - bg).sum(-1)
    # the cast shadow: the stage's own grey darkened and cooled (#8a8e99 at noon); anything within
    # reach of that colour, or between it and the stage grey, is ground, not her
    sh = np.array([138, 142, 153])
    t = np.clip(((w - sh) * (bg - sh)).sum(-1) / max(((bg - sh) ** 2).sum(), 1), 0, 1)
    proj = sh + t[..., None] * (bg - sh)
    ground = np.abs(w - proj).sum(-1) < 22
    m = (d > 24) & ~ground
    ys, xs = np.where(m)
    return xs.min() + X0, ys.min() + Y0, xs.max() + X0, ys.max() + Y0


cells = []
for v, yaw in VIEWS:
    row = []
    boxes = []
    for lab, d in dirs:
        im = Image.open('%s/%s_10p5.png' % (d, yaw)).convert('RGB')
        boxes.append((im, figure_box(im)))
    # common frame: the union box (with a margin) of all renders, same for every column of the row
    x0 = min(b[0] for _, b in boxes) - 3
    y0 = min(b[1] for _, b in boxes) - 3
    x1 = max(b[2] for _, b in boxes) + 4
    y1 = max(b[3] for _, b in boxes) + 6
    sheet = Image.open('%s/ref/crop_%s.png' % (C6, v)).convert('RGB')
    for (lab, d), (im, b) in zip(dirs, boxes):
        # the sheet's view at this render's figure height, then the render
        H = b[3] - b[1] + 1
        w = max(1, round(sheet.width * H / sheet.height))
        small = sheet.resize((w, H), Image.LANCZOS)
        canvas = Image.new('RGB', (max(w + 6, x1 - x0), y1 - y0), (255, 255, 255))
        canvas.paste(small, ((canvas.width - w) // 2, b[3] - y0 - H + 1))
        row.append(('sheet %s at %d px' % (v, H), canvas))
        row.append((lab, im.crop((x0, y0, x1, y1))))
    cells.append(row)
pad, lab_h = 6, 16
cols = len(cells[0])
cw = [max(r[c][1].width for r in cells) * sc for c in range(cols)]
rh = [max(im.height for _, im in r) * sc for r in cells]
W = sum(cw) + pad * (cols + 1)
Ht = sum(h + lab_h + pad for h in rh) + pad
s = Image.new('RGB', (W, Ht), (30, 30, 34))
dr = ImageDraw.Draw(s)
y = pad
for r, h in zip(cells, rh):
    x = pad
    for (lab, im), w in zip(r, cw):
        big = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
        s.paste(big, (x, y))
        dr.text((x + 2, y + h + 2), lab, fill=(230, 230, 230))
        x += w + pad
    y += h + lab_h + pad
s.save(out)
print(out, s.size)
