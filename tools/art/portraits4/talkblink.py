"""Talk and blink overlays for the v4 dialogue portraits (docs/knowledge/13-pixel-portraits.md section 10.9).

    python3 -I tools/art/portraits4/talkblink.py            # after build.py: write the overlays next to the portraits
    python3 -I tools/art/portraits4/talkblink.py --check    # verify them against a fresh generation
    python3 -I tools/art/portraits4/talkblink.py --out DIR  # write somewhere else (same <char>/ layout)

The approved expressions never change: each overlay holds only the pixels that differ from the portrait, everything
else transparent, and the dialogue box draws it over the portrait (godot/story/dialogue_box.gd):

  <expr>.talk1.png, <expr>.talk2.png   the mouth a little / more open while the text types; an open mouth closes
                                       part way in talk1 and stays itself in talk2 (no file when nothing changes)
  <expr>.blink1.png, <expr>.blink2.png the eyes half / fully closed, every 2.5-6 s

Talk and blink overlays never touch the same pixels, so a blink can happen mid-sentence. Made from the portrait
itself (the ChatGPT pack's talk and blink images are another face and do not fit v4):
  - closed mouth: the 1-px stroke opens below its own curve (a frown opens as a frown, a smile as a smile);
  - open mouth: the lower lip rises to 55 % of the opening (talk1);
  - blink: one dark line, two px thick in the middle, slanted with the eye and bowed slightly down, the lid one flat
    skin tone; tears, blush, Shione's red marks and the hair over the eyes stay.
A hand-drawn frame wins over the automatic one: edits/<char>/<expr>.<talk1|talk2|blink1|blink2>.txt in the edit
format of build.py, laid over the portrait (used where the mouth is too small or too faint to open by rule).
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402
import config as C  # noqa: E402

KINDS = ('talk1', 'talk2', 'blink1', 'blink2')
# eyes already closed (laugh, calm), a hand over the face (the lid would paint over the fingers), a wink
NO_BLINK = {(c, e) for c in C.SELECTION for e in ('laugh', 'calm', 'embarrassed')} | {('saji', 'mischievous')}
NO_TALK = {(c, 'embarrassed') for c in C.SELECTION}         # the hands cover the mouth
NARROW = {'pout'}                                            # a pursed mouth opens only in its middle (a small "o")


def rgb_of(h):
    return (B.hexrgb(h) * 255).round().astype(np.uint8)


def legend(char):
    return {k: rgb_of(v) for k, v in B.read_legend(os.path.join(B.EDITS, char, '_legend.txt')).items()}


def skin_mask(img):
    L = B.lab(img[..., :3].astype(np.float32) / 255)
    return B._is_skin(L) & (img[..., 3] > 0)


def fill_from(img, holes, source, radius=3):
    """holes take a smooth skin colour: the Gaussian-weighted mean of the `source` pixels around them (falling back
    to the nearest source pixel), snapped to the closest colour already used by `source` (no new colours)."""
    if not holes.any() or not source.any():
        return
    f = img[..., :3].astype(np.float32)
    w = source.astype(np.float32)
    sig = radius / 1.5
    num = np.dstack([ndi.gaussian_filter(f[..., c] * w, sig) for c in range(3)])
    den = ndi.gaussian_filter(w, sig)[..., None]
    _, (iy, ix) = ndi.distance_transform_edt(~source, return_indices=True)
    near = f[iy, ix]
    mean = np.where(den > 0.05, num / np.maximum(den, 1e-6), near)
    pal = np.unique(img[source][:, :3], axis=0).astype(np.float32)
    P = B.lab(pal / 255)
    Lm = B.lab(mean[holes] / 255)
    k = ((Lm[:, None, :] - P[None]) ** 2).sum(-1).argmin(-1)
    img[holes, :3] = pal[k].astype(np.uint8)


def _classes(char, img, region):
    """Inside the eye ellipse every colour is one of EYE_CANON (snap_eyes); in the 2-px ring around it, classify by
    the nearest of canon eye colours vs the character's skin and hair. Returns a bool mask of eye pixels."""
    canon = np.array([rgb_of(h) for h in C.EYE_CANON[char]]).astype(np.float32) / 255
    lg = legend(char)
    skin = [lg[k] for k in ('s', 't', 'u', 'U') if k in lg]
    hair = [lg[k] for k in ('h', 'H') if k in lg]
    refs = np.concatenate([canon, np.array(skin + hair, np.float32) / 255])
    is_eye = np.array([True] * 7 + [False] * (len(canon) - 7) + [False] * (len(skin) + len(hair)))
    L = B.lab(img[..., :3].astype(np.float32) / 255)
    P = B.lab(refs)
    k = ((L[..., None, :] - P[None, None]) ** 2).sum(-1).argmin(-1)
    eye = is_eye[k] | np.all(img[..., :3] == 255, -1)
    for kk in ('k', 'K', 'w', 'v', 'E', 'e', 'i', 'l'):   # hand-edited lids and glints
        if kk in lg:
            eye |= np.all(img[..., :3] == lg[kk], -1)
    return eye & region & (img[..., 3] > 0)


def eye_mask(char, img, reg):
    m = _classes(char, img, ndi.binary_dilation(reg, iterations=2))
    lab, n = ndi.label(m, np.ones((3, 3)))
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    return m


def blink(char, expr, img, amount):
    """amount 0.5 = half, 1.0 = closed. One dark line, two pixels thick in the middle, one at the ends, slanted with
    the eye, bowed slightly downward. Half: the line runs through the middle of the eye, skin above it, the lower
    half of the eye kept. Closed: skin everywhere but the line. Only eye pixels change."""
    out = img.copy()
    lash = rgb_of(C.EYE_CANON[char][0])
    skin = skin_mask(img)
    _, el, er, *_ = C.SELECTION[char][expr]
    d_eye = float(np.hypot(*(np.array(B.to_native(char, expr, er)) - np.array(B.to_native(char, expr, el)))))
    for reg in B.eye_regions(char, expr):
        E = eye_mask(char, img, reg)
        if char == 'shione':
            # her red marks hang under the near eye: never part of the eye (they would pull the lower lid down)
            Lab0 = B.lab(img[..., :3].astype(np.float32) / 255)
            cy = np.nonzero(reg)[0].mean()
            rows = np.mgrid[0:C.SIZE, 0:C.SIZE][0]
            marks = (Lab0[..., 1] > 18) & (Lab0[..., 0] < 72) & (rows > cy + 0.2 * d_eye)
            E &= ~marks
            lab1, n1 = ndi.label(E, np.ones((3, 3)))
            if n1 > 1:
                E = lab1 == (int(np.argmax(ndi.sum(E, lab1, range(1, n1 + 1)))) + 1)
        if E.sum() < 12:
            continue
        xs = np.nonzero(E.any(0))[0]
        # trim thin wisps at the ends (lash tips): keep columns with >= 2 eye pixels
        xs = np.array([x for x in xs if E[:, x].sum() >= 2])
        if len(xs) < 4:
            continue
        tops = np.array([np.nonzero(E[:, x])[0].min() for x in xs], float)
        bots = np.array([np.nonzero(E[:, x])[0].max() for x in xs], float)
        tfit = np.polyval(np.polyfit(xs, tops, 2), xs)
        bfit = np.polyval(np.polyfit(xs, bots, 2), xs)
        u = (xs - xs[0]) / max(1, xs[-1] - xs[0])
        if amount < 1:
            line = tfit + 0.5 * (bfit - tfit)
        else:
            # a straight slant from end to end (through 60 % of the height there), bowed down in the middle
            yl = tfit[0] + 0.6 * (bfit[0] - tfit[0])
            yr = tfit[-1] + 0.6 * (bfit[-1] - tfit[-1])
            bow = 1.0 if len(xs) < 12 else 1.5
            line = yl + (yr - yl) * u + bow * 4 * u * (1 - u)
        line = np.round(line).astype(int)
        # the eye zone: between the fitted lids (one row of margin), over the eye's columns (plus the wisps);
        # tears, blush and the red marks inside it stay
        keep = np.zeros(img.shape[:2], bool)
        lg = legend(char)
        for kk in ('c', 'C', 'z', 'b', 'p', 'r'):
            if kk in lg:
                keep |= np.all(img[..., :3] == lg[kk], -1)
        if char == 'shione':
            keep |= marks                               # the red marks under the near eye stay
        allx = np.nonzero(E.any(0))[0]
        zone = np.zeros_like(E)
        for x in allx:
            if x in xs:
                i = int(np.nonzero(xs == x)[0][0])
                t0, b0 = int(np.floor(tfit[i])) - 1, int(np.ceil(bfit[i])) + 1
            else:
                col = np.nonzero(E[:, x])[0]
                t0, b0 = col.min() - 1, col.max() + 1
            zone[max(0, t0):b0 + 1, x] = True
        zone &= ~keep & (img[..., 3] > 0)
        holes = zone.copy()
        if amount < 1:
            for x, y in zip(xs, line):
                holes[y:, x] = False                    # below the half-closed lid the eye stays
        # the lid is one flat tone: the commonest skin colour in a ring around the eye zone
        ring = ndi.binary_dilation(zone, iterations=3) & ~zone & skin
        if ring.any():
            vals, cnt = np.unique(img[ring][:, :3], axis=0, return_counts=True)
            out[holes, :3] = vals[cnt.argmax()]
        else:
            fill_from(out, holes, skin & ~zone)
        for x, y, uu in zip(xs, line, u):
            thick = 2 if 0.15 < uu < 0.9 else 1
            for i in range(thick):
                yy = y + i
                if 0 <= yy < C.SIZE and zone[yy, x]:
                    out[yy, x, :3] = lash
    return out


def mouth_pixels(char, expr, img):
    lg = legend(char)
    keys = [k for k in ('q', 'Q', 'm', 'n', 'y') if k in lg]
    cols = [lg[k] for k in keys] + [rgb_of(C.MOUTH[char][0]), rgb_of(C.MOUTH[char][1]), rgb_of(C.MOUTH_CAVITY[char]),
                                    rgb_of(C.MOUTH_TONGUE[char]), rgb_of(C.MOUTH_PINK[char])]
    _, el, er, mc, state, *_ = C.SELECTION[char][expr]
    m = np.array(B.to_native(char, expr, mc))
    yy, xx = np.mgrid[0:C.SIZE, 0:C.SIZE]
    box = (np.abs(xx - m[0]) <= 10) & (np.abs(yy - m[1]) <= 7)
    hit = np.zeros(img.shape[:2], bool)
    for c in cols:
        hit |= np.all(img[..., :3] == c, -1)
    hit &= box & (img[..., 3] > 0)
    if hit.sum() < 2:
        # a faint mouth (the illustration's line was too light to become a stroke): its darkest pixels near the spot
        L = B.lab(img[..., :3].astype(np.float32) / 255)[..., 0]
        near = (np.abs(xx - m[0]) <= 6) & (np.abs(yy - m[1]) <= 5) & (img[..., 3] > 0)
        if near.any():
            base = np.median(L[near])
            hit = near & (L < base - 6)
    lab, n = ndi.label(hit, np.ones((3, 3)))
    if n > 1:
        sizes = ndi.sum(hit, lab, range(1, n + 1))
        hit = lab == (int(np.argmax(sizes)) + 1)
    return hit


def talk(char, expr, img, frame):
    """frame 'half' | 'open'. A closed mouth opens below its own stroke (so a frown opens as a frown, a smile as a
    smile); an open mouth closes part way (its lower lip rises) for 'half' and stays itself for 'open'."""
    out = img.copy()
    M = mouth_pixels(char, expr, img)
    if M.sum() < 2:
        return None
    line = rgb_of(C.MOUTH[char][0])
    cav = rgb_of(C.MOUTH_CAVITY[char])
    tongue = rgb_of(C.MOUTH_TONGUE[char])
    ys, xs = np.nonzero(M)
    x0, x1 = xs.min(), xs.max()
    colx = [x for x in range(x0, x1 + 1) if M[:, x].any()]
    top = {x: np.nonzero(M[:, x])[0].min() for x in colx}
    bot = {x: np.nonzero(M[:, x])[0].max() for x in colx}
    tall = max(bot[x] - top[x] for x in colx) + 1
    skin = skin_mask(img)
    if tall <= 3 and len(colx) <= 6 and not (tall <= 2):  # a small open mouth (e.g. the crying arch)
        if frame == 'half':
            return out
        # one row wider open: the lower lip moves down a row, the row above it becomes tongue
        for x in colx:
            if bot[x] - top[x] >= 1 and bot[x] + 1 < C.SIZE:
                out[bot[x] + 1, x, :3] = img[bot[x], x, :3]
                if bot[x] - top[x] >= 2:
                    out[bot[x], x, :3] = tongue
        return out
    if tall <= 2:                                       # closed: a stroke
        if frame == 'half':
            depth = 1
        else:
            depth = 2 if len(colx) <= 5 else 3
        w = len(colx)
        narrow = expr in NARROW
        if narrow:
            depth = 1 if frame == 'half' else 2
        for i, x in enumerate(colx):
            u = (i + 0.5) / w                           # 0..1 across the mouth
            d = int(round(depth * (1 - (2 * u - 1) ** 2) ** 0.5 + 0.15))
            if i in (0, w - 1) or (narrow and abs(i - (w - 1) / 2) > 1):
                d = 0
            y = bot[x]
            for r in range(1, d + 1):
                out[y + r, x, :3] = cav if (r == 1 or frame == 'half') else tongue
            if d:
                out[y + d + 1, x, :3] = line
        return out
    if frame == 'open':
        return out
    # open mouth -> half: per column, the lower lip rises to 55 % of the opening
    region = ndi.binary_fill_holes(M)
    holes = np.zeros_like(M)
    newbot = {}
    for x in colx:
        nb = top[x] + int(round((bot[x] - top[x]) * 0.55))
        newbot[x] = nb
        holes[nb + 1:bot[x] + 1, x] = region[nb + 1:bot[x] + 1, x]
    fill_from(out, holes, skin & ~region)
    for x in colx:
        out[newbot[x], x, :3] = line                    # the risen lower lip, corner to corner
    return out


def hand_frame(char, expr, kind, base):
    """A hand-drawn frame (edits/<char>/<expr>.<kind>.txt over the portrait), or None."""
    if not os.path.exists(os.path.join(B.EDITS, char, f'{expr}.{kind}.txt')):
        return None
    img = base.copy()
    B.apply_edits(img, char, f'{expr}.{kind}')
    return img


def frames(char, expr, base):
    """-> {kind: full RGBA frame} for the kinds that apply (hand-drawn ones win)."""
    out = {}
    if (char, expr) not in NO_BLINK:
        for kind, amount in (('blink1', 0.5), ('blink2', 1.0)):
            out[kind] = blink(char, expr, base, amount)
    if (char, expr) not in NO_TALK:
        for kind, fr in (('talk1', 'half'), ('talk2', 'open')):
            t = talk(char, expr, base, fr)
            if t is not None:
                out[kind] = t
    for kind in KINDS:
        h = hand_frame(char, expr, kind, base)
        if h is not None:
            out[kind] = h
    return out


def overlay(base, frame):
    """Only the changed pixels, opaque; None when nothing changed."""
    ch = np.any(frame != base, -1)
    if not ch.any():
        return None
    ov = np.zeros_like(frame)
    ov[ch] = frame[ch]
    ov[ch, 3] = 255
    return ov


def generate(src_dir):
    """-> {(char, expr): {kind: overlay RGBA}}"""
    res = {}
    for char, exprs in C.SELECTION.items():
        for expr in exprs:
            p = os.path.join(src_dir, char, f'{expr}.png')
            if not os.path.exists(p):
                print('WARNING no portrait (run build.py first):', char, expr)
                continue
            base = np.asarray(Image.open(p).convert('RGBA')).copy()
            ovs = {}
            for kind, fr in frames(char, expr, base).items():
                o = overlay(base, fr)
                if o is not None:
                    ovs[kind] = o
            talk_ = [k for k in ('talk1', 'talk2') if k in ovs]
            blink_ = [k for k in ('blink1', 'blink2') if k in ovs]
            # check: the two never touch the same pixel (a blink can happen mid-sentence)
            if talk_ and blink_:
                t = np.logical_or.reduce([ovs[k][..., 3] > 0 for k in talk_])
                b = np.logical_or.reduce([ovs[k][..., 3] > 0 for k in blink_])
                if (t & b).any():
                    raise SystemExit(f'{char}/{expr}: talk and blink overlays overlap')
            res[(char, expr)] = ovs
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', default=B.OUT, help='the portraits (default assets/portraits/pixel)')
    ap.add_argument('--out', default=None, help='where to write the overlays (default: next to the portraits)')
    ap.add_argument('--check', action='store_true', help='verify the overlays on disk against a fresh generation')
    args = ap.parse_args()
    out_dir = args.out or args.src
    res = generate(args.src)
    bad = 0
    for (char, expr), ovs in res.items():
        d = os.path.join(out_dir, char)
        os.makedirs(d, exist_ok=True)
        for kind in KINDS:
            p = os.path.join(d, f'{expr}.{kind}.png')
            if args.check:
                cur = np.asarray(Image.open(p).convert('RGBA')) if os.path.exists(p) else None
                want = ovs.get(kind)
                same = (cur is None and want is None) or (cur is not None and want is not None and
                                                          np.array_equal(cur, want))
                if not same:
                    bad += 1
                    print('MISMATCH', char, expr, kind)
                continue
            if kind in ovs:
                Image.fromarray(ovs[kind], 'RGBA').save(p, optimize=True)
            elif os.path.exists(p):
                os.remove(p)                                   # stale: this frame no longer applies
        moves = [k for k in ('talk1', 'talk2') if k in ovs]
        if not args.check and (char, expr) not in NO_TALK and not moves:
            print('WARNING no mouth movement:', char, expr)
        if not args.check:
            print(char, expr, ' '.join(k for k in KINDS if k in ovs))
    if args.check:
        print('check:', 'OK' if not bad else f'{bad} differ')
        return 1 if bad else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
