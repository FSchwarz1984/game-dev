#!/usr/bin/env python3
"""Long exposure of the rising lights (docs/knowledge/14 §6, §7), from the frames tools/vista/record.gd
writes with --rise=DIR: each is the rising lights' own buffer (what they add to the screen, sRGB
units, a 1 px border around the view), so no base frame has to be subtracted.

  python3 tools/vista/longexp.py RISE_DIR OUT_PREFIX [--screen FRAME.png] [--thresh 40] [--t0 S --t1 S]

Writes OUT_PREFIX.png (the maximum over the frames), OUT_PREFIX-over.png (that over a darkened screen
frame, if --screen is given) and OUT_PREFIX.txt: per row, the lit columns, the span (leftmost to
rightmost lit column) and the segments (a gap of more than 2 px starts a new one), every 5 rows.
A pixel is lit when any channel of the exposure passes --thresh (0..255): the buffer holds nothing
but the rising lights, so the screen test of §6 (red up > 40 and R >= B) is not needed here (it
would also drop the lights once they turn pale jade on the second half of their way).
"""
import sys
import os
import glob
import numpy as np
from PIL import Image


def arg(name, default=None, cast=str):
    if name in sys.argv:
        return cast(sys.argv[sys.argv.index(name) + 1])
    return default


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    src, out = sys.argv[1], sys.argv[2]
    thresh = arg("--thresh", 40, int)
    t0 = arg("--t0", -1e9, float)
    t1 = arg("--t1", 1e9, float)
    times = {}
    tf = os.path.join(src, "times.txt")
    if os.path.exists(tf):
        for line in open(tf):
            p = line.split()
            if len(p) >= 2:
                times[int(p[0])] = float(p[1])
    files = sorted(glob.glob(os.path.join(src, "r*.png")))
    acc = None
    used = 0
    for f in files:
        i = int(os.path.basename(f)[1:-4])
        t = times.get(i, 0.0)
        if t < t0 or t > t1:
            continue
        a = np.asarray(Image.open(f).convert("RGB"), dtype=np.uint8)[1:-1, 1:-1]
        acc = a.copy() if acc is None else np.maximum(acc, a)
        used += 1
    if acc is None:
        print("no frames")
        sys.exit(1)
    Image.fromarray(acc).save(out + ".png")
    lit = acc.max(axis=2) > thresh
    h, w = lit.shape
    lines = ["# %d frames from %s, threshold %d; y: lit columns, span [x0..x1] width, segments" % (used, src, thresh)]
    rows = []
    for y in range(h):
        xs = np.nonzero(lit[y])[0]
        if xs.size == 0:
            continue
        seg = 1 + int(np.count_nonzero(np.diff(xs) > 2))
        rows.append((y, xs.size, int(xs[0]), int(xs[-1]), seg))
    for (y, n, x0, x1, seg) in rows:
        if y % 5 == 0:
            lines.append("%3d: %3d lit  [%3d..%3d] %3d px  %2d seg" % (y, n, x0, x1, x1 - x0 + 1, seg))
    if rows:
        top = rows[0][0]
        widest = max(rows, key=lambda r: r[3] - r[2])
        lines.append("# first lit row %d; width 10 rows below it %s; widest row %d: %d px; rows lit %d"
                     % (top, next((r[3] - r[2] + 1 for r in rows if r[0] >= top + 10), "-"), widest[0],
                        widest[3] - widest[2] + 1, len(rows)))
    open(out + ".txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[-1:]))
    scr = arg("--screen")
    if scr:
        s = np.asarray(Image.open(scr).convert("RGB"), dtype=np.float32)
        s = s[: acc.shape[0], : acc.shape[1]] * 0.45
        o = np.clip(s + acc.astype(np.float32), 0, 255).astype(np.uint8)
        Image.fromarray(o).save(out + "-over.png")


if __name__ == "__main__":
    main()
