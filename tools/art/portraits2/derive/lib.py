"""Helpers for derive.py (the v3 base derivation). Pure image maths on the tilted reference crop and its PixelOE
version; nothing here reads the owner's packs (derive.py opens them, as images only)."""

import math

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.filters import sato
from skimage.morphology import skeletonize

CARD = (78, 70, 86)
N4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
N8 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]


# ------------------------------------------------------------------------------------------------- grids, colour

def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lab(rgb):
    """uint8 RGB (..., 3) -> float Lab, L in 0..100, a/b signed."""
    a = cv2.cvtColor(rgb.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32).reshape(rgb.shape)
    a[..., 0] *= 100.0 / 255.0
    a[..., 1:] -= 128.0
    return a


def read_grid(path):
    return [list(l.rstrip('\n')) for l in open(path, encoding='utf-8') if l.strip() and not l.startswith('#')]


def write_grid(path, g, header=''):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + '\n'.join(''.join(r) for r in g) + '\n')


def render(g, pal, k=1, bg=CARD):
    h, w = len(g), len(g[0])
    a = np.zeros((h, w, 3), np.uint8)
    a[:] = bg
    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c != '.':
                a[y, x] = hexrgb(pal[c])
    im = Image.fromarray(a, 'RGB')
    return im.resize((w * k, h * k), Image.NEAREST) if k != 1 else im


# ------------------------------------------------------------------------------------------------- reference maths

def cells(hi, n=96):
    """Area-average the hi crop down to n x n (premultiplied, so the background does not bleed)."""
    f = hi.astype(np.float32) / 255.0
    rgb, a = f[..., :3], f[..., 3:4]
    pm = rgb * a
    s = hi.shape[0] // n
    pm = pm.reshape(n, s, n, s, 3).mean(axis=(1, 3))
    aa = a.reshape(n, s, n, s, 1).mean(axis=(1, 3))
    rgb_small = np.where(aa > 1e-4, pm / np.maximum(aa, 1e-4), 0)
    return (rgb_small * 255).clip(0, 255).astype(np.uint8), aa[..., 0]


def refclass(hi):
    """Per-cell classes of the reference: '#' very dark, '+' dark, 'r' red, 'w' white, 's' skin, 'g' grey, 'h' other,
    '.' background. Returns (classes, L, cell colours)."""
    c, a = cells(hi)
    L = lab(c)
    l, aa, bb = L[..., 0], L[..., 1], L[..., 2]
    C = np.hypot(aa, bb)
    h = np.degrees(np.arctan2(bb, aa))
    cls = np.full(l.shape, 'h', dtype='<U1')
    cls[(h > 30) & (C >= 7)] = 's'
    cls[(C < 9) & (l < 88)] = 'g'
    cls[(l > 88) & (C < 6)] = 'w'
    cls[(C > 22) & (h < 45)] = 'r'
    cls[l < 45] = '+'
    cls[l < 25] = '#'
    cls[a < 0.5] = '.'
    return cls, l, c


def orientation(hi, n=96, sig_d=2.0, sig_t=28.0):
    """Hair-flow direction per cell (structure tensor of the hi crop; the minor eigenvector runs along the strands)."""
    g = cv2.cvtColor(hi[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    g = cv2.GaussianBlur(g, (0, 0), sig_d)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    jxx = cv2.resize(cv2.GaussianBlur(gx * gx, (0, 0), sig_t), (n, n), interpolation=cv2.INTER_AREA)
    jyy = cv2.resize(cv2.GaussianBlur(gy * gy, (0, 0), sig_t), (n, n), interpolation=cv2.INTER_AREA)
    jxy = cv2.resize(cv2.GaussianBlur(gx * gy, (0, 0), sig_t), (n, n), interpolation=cv2.INTER_AREA)
    return 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2


def flow_smooth(v, mask, theta, L=3.0, sigma=1.6, step=0.5):
    """Average v along the flow direction (both ways), only over mask pixels; bilinear sampling."""
    n_h, n_w = v.shape
    out = v.copy()
    ts = np.arange(-L, L + 1e-6, step)
    wts = np.exp(-0.5 * (ts / sigma) ** 2)
    vm = np.where(mask, v, 0).astype(np.float32)
    mm = mask.astype(np.float32)
    for y, x in zip(*np.nonzero(mask)):
        c, s = math.cos(theta[y, x]), math.sin(theta[y, x])
        acc = wsum = 0.0
        for t, w in zip(ts, wts):
            px, py = x + t * c, y + t * s
            x0, y0 = int(math.floor(px)), int(math.floor(py))
            fx, fy = px - x0, py - y0
            for (xx, yy, ww) in ((x0, y0, (1 - fx) * (1 - fy)), (x0 + 1, y0, fx * (1 - fy)),
                                 (x0, y0 + 1, (1 - fx) * fy), (x0 + 1, y0 + 1, fx * fy)):
                if 0 <= xx < n_w and 0 <= yy < n_h and mm[yy, xx] > 0:
                    acc += w * ww * vm[yy, xx]
                    wsum += w * ww
        if wsum > 0:
            out[y, x] = acc / wsum
    return out


def norm_blur(v, mask, sigma):
    m = mask.astype(np.float32)
    num = cv2.GaussianBlur((v * m).astype(np.float32), (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma)
    return np.where(den > 1e-3, num / np.maximum(den, 1e-3), v)


def ridges(hi, mask96, sigmas=(2, 3, 4), black=True, n=96):
    """Line strength of the reference (Sato), max-pooled to n x n inside mask96."""
    g = cv2.cvtColor(hi[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    r = sato(g, sigmas=sigmas, black_ridges=black)
    s = hi.shape[0] // n
    rp = r.reshape(n, s, n, s).max(axis=(1, 3))
    rp[~mask96] = 0
    return rp


def thin_lines(strength, thr, minlen=4):
    """Skeleton of strength > thr, components shorter than minlen dropped, L-corners removed (pixel-perfect)."""
    sk = skeletonize(strength > thr)
    lab_, nlab = ndi.label(sk, structure=np.ones((3, 3)))
    sizes = ndi.sum(sk, lab_, range(1, nlab + 1))
    keep = np.zeros_like(sk)
    for i, sz in enumerate(sizes, 1):
        if sz >= minlen:
            keep |= lab_ == i
    k = keep.copy()
    H, W = k.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if not k[y, x]:
                continue
            n4 = [(k[y - 1, x], k[y, x + 1], k[y - 1, x + 1]), (k[y, x + 1], k[y + 1, x], k[y + 1, x + 1]),
                  (k[y + 1, x], k[y, x - 1], k[y + 1, x - 1]), (k[y, x - 1], k[y - 1, x], k[y - 1, x - 1])]
            if int(k[y - 1, x]) + int(k[y + 1, x]) + int(k[y, x - 1]) + int(k[y, x + 1]) == 2:
                for a, b, diag in n4:
                    if a and b and not diag:
                        k[y, x] = False
                        break
    return k


# ------------------------------------------------------------------------------------------------- cleanup

def components(g, keyset=None):
    """4-connected components of equal keys: [(key, [(x, y), ...]), ...]."""
    h, w = len(g), len(g[0])
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                continue
            k = g[y][x]
            stack, pts = [(x, y)], []
            seen[y][x] = True
            while stack:
                cx, cy = stack.pop()
                pts.append((cx, cy))
                for dx, dy in N4:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and g[ny][nx] == k:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if keyset is None or k in keyset:
                comps.append((k, pts))
    return comps


def orphan_fix(g, mask, keep=(), passes=2):
    """Lone pixels (no same-key 4-neighbour, at most one same-key 8-neighbour) inside mask take the most common key of
    their in-mask 8-neighbours."""
    from collections import Counter
    n_h, n_w = len(g), len(g[0])
    for _ in range(passes):
        snap = [r[:] for r in g]
        ch = 0
        for y in range(n_h):
            for x in range(n_w):
                if not mask[y, x]:
                    continue
                k = snap[y][x]
                same8 = sum(1 for dx, dy in N8 if 0 <= x + dx < n_w and 0 <= y + dy < n_h and snap[y + dy][x + dx] == k)
                same4 = sum(1 for dx, dy in N4 if 0 <= x + dx < n_w and 0 <= y + dy < n_h and snap[y + dy][x + dx] == k)
                if k in keep and same8 >= 1:
                    continue
                if same4 == 0 and same8 <= 1:
                    cnt = Counter(snap[y + dy][x + dx] for dx, dy in N8
                                  if 0 <= x + dx < n_w and 0 <= y + dy < n_h and mask[y + dy, x + dx]
                                  and snap[y + dy][x + dx] != k)
                    if cnt:
                        g[y][x] = cnt.most_common(1)[0][0]
                        ch += 1
        if not ch:
            break
    return g


def prune_keys(g, mask, keys, minsize=3, passes=3):
    """Clusters of keys smaller than minsize (inside mask) take the most common in-mask neighbouring key."""
    from collections import Counter
    n_h, n_w = len(g), len(g[0])
    for _ in range(passes):
        ch = 0
        for k, pts in components(g, set(keys)):
            if len(pts) >= minsize or not mask[pts[0][1], pts[0][0]]:
                continue
            ptset = set(pts)
            cnt = Counter()
            for x, y in pts:
                for dx, dy in N4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < n_w and 0 <= ny < n_h and (nx, ny) not in ptset and mask[ny, nx]:
                        cnt[g[ny][nx]] += 1
            if cnt:
                nk = cnt.most_common(1)[0][0]
                for x, y in pts:
                    g[y][x] = nk
                ch += 1
        if not ch:
            break
    return g


def shade(mat, oe, pal, spec):
    """Tone each material from the PixelOE luminance: explicit cuts (descending L thresholds) or the nearest ramp
    step; optional blur inside the material first."""
    n = mat.shape[0]
    Lsrc = lab(oe[..., :3])[..., 0]
    g = [['.'] * n for _ in range(n)]
    for mk, sp in spec.items():
        mask = mat == mk
        if not mask.any():
            continue
        keys = sp['ramp']
        v = Lsrc.copy()
        if sp.get('blur'):
            v = norm_blur(v, mask, sp['blur'])
        if 'cuts' in sp:
            cuts = sp['cuts']
            for y, x in zip(*np.nonzero(mask)):
                i = 0
                while i < len(cuts) and v[y, x] < cuts[i]:
                    i += 1
                g[y][x] = keys[i]
        else:
            rl = lab(np.array([hexrgb(pal[k]) for k in keys], np.uint8)[None])[0][:, 0]
            for y, x in zip(*np.nonzero(mask)):
                g[y][x] = keys[int(np.abs(rl - v[y, x]).argmin())]
    return g


# ------------------------------------------------------------------------------------------------- material maps

def classify(c, a, rules):
    """rules: [(key, numpy expression over l, a, b, C, h, fig)] evaluated in order on the cell colours."""
    L = lab(c)
    l, aa, bb = L[..., 0], L[..., 1], L[..., 2]
    fig = a > 0.5
    m = np.full(l.shape, '.', dtype='<U1')
    env = dict(l=l, a=aa, b=bb, C=np.hypot(aa, bb), h=np.degrees(np.arctan2(bb, aa)), fig=fig, np=np)
    for key, expr in rules:
        m[eval(expr, {}, env) & fig] = key
    return m


def box(m, x0, y0, x1, y1, key, only=None):
    sub = m[y0:y1 + 1, x0:x1 + 1]
    if only is None:
        sub[sub != '.'] = key
    else:
        sub[np.isin(sub, list(only))] = key


def mpoly(m, pts, key, only=None):
    """Fill a polygon on a material map (pixel centres inside), skipping the background."""
    n_h, n_w = m.shape
    ys = [p[1] for p in pts]
    for y in range(max(0, int(min(ys))), min(n_h, int(max(ys)) + 1)):
        yc = y + 0.5
        xs = []
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for a_, b_ in zip(xs[0::2], xs[1::2]):
            for x in range(max(0, math.ceil(a_ - 0.5)), min(n_w, math.floor(b_ - 0.5) + 1)):
                if m[y, x] != '.' and (only is None or m[y, x] in only):
                    m[y, x] = key


def resolve(m, dark='d', passes=6):
    """Line pixels (dark) take the most common other material among their 8-neighbours."""
    from collections import Counter
    n_h, n_w = m.shape
    for _ in range(passes):
        snap = m.copy()
        left = 0
        for y in range(n_h):
            for x in range(n_w):
                if snap[y, x] != dark:
                    continue
                cnt = Counter()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if (dx or dy) and 0 <= yy < n_h and 0 <= xx < n_w and snap[yy, xx] not in (dark, '.'):
                            cnt[snap[yy, xx]] += 1
                if cnt:
                    m[y, x] = cnt.most_common(1)[0][0]
                else:
                    left += 1
        if not left:
            break
    return m


# ------------------------------------------------------------------------------------------------- paint edits

class Canvas:
    def __init__(self, w=96, h=96, bg='.'):
        self.w, self.h = w, h
        self.g = [[bg] * w for _ in range(h)]

    def poly(self, pts, k):
        ys = [p[1] for p in pts]
        for y in range(max(0, int(min(ys))), min(self.h, int(max(ys)) + 1)):
            yc = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                for x in range(max(0, math.ceil(a - 0.5)), min(self.w, math.floor(b - 0.5) + 1)):
                    self.g[y][x] = k

    def line(self, pts, k):
        """Pixel-perfect polyline through integer points (no L-shaped doubles)."""
        path = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0), 1)
            for i in range(n + 1):
                p = (round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n))
                if not path or path[-1] != p:
                    path.append(p)
        out = []
        for p in path:
            out.append(p)
            if len(out) >= 3:
                a, b, c = out[-3], out[-2], out[-1]
                if abs(a[0] - c[0]) == 1 and abs(a[1] - c[1]) == 1 and (b[0] == a[0] or b[1] == a[1]):
                    out.pop(-2)
        for x, y in out:
            if 0 <= x < self.w and 0 <= y < self.h:
                self.g[y][x] = k


def _opts(tokens):
    o, rest = {}, []
    for t in tokens:
        if '=' in t:
            k, v = t.split('=', 1)
            o[k] = v
        else:
            rest.append(t)
    return o, rest


def _pts(s):
    return [tuple(float(v) for v in p.split(',')) for p in s.split()]


def paint(g, lines):
    """Apply hand paint commands in order (one per line, '#' comments):
      poly K [only=KEYS] [not=KEYS] : x,y x,y ...     fill polygon (pixel centres inside)
      line K [only=KEYS] [not=KEYS] : x,y x,y ...     pixel-perfect polyline through integer points
      px K : x,y x,y ...                              single pixels
      rect K [only=KEYS] [not=KEYS] : x0,y0,x1,y1     inclusive rectangle
      span K [only=KEYS] Y : x0-x1 x ...              pixels of one row (Y may be y0-y1)
      repl FROM TO [x0,y0,x1,y1]                      replace keys (FROM is a set) inside the rectangle
      below K FROM OVER [n=1] [x0,y0,x1,y1]           FROM pixels with an OVER pixel within n rows above -> K
      edge K FROM NB [dirs=udlr] [x0,y0,x1,y1]        FROM pixels with a 4-neighbour (dirs) in NB -> K"""
    H, W = len(g), len(g[0])
    for raw in lines:
        ln = raw.split('#', 1)[0].rstrip()
        if not ln.strip():
            continue
        head, body = ln.split(':', 1) if ':' in ln else (ln, '')
        tok = head.split()
        cmd = tok[0]
        if cmd == 'span':
            K = tok[1]
            o2, rest2 = _opts(tok[2:])
            only2 = set(o2['only']) if 'only' in o2 else None
            ys = rest2[0]
            for yy in range(int(ys.split('-')[0]), int(ys.split('-')[-1]) + 1):
                for item in body.split():
                    a_, b_ = item.split('-') if '-' in item else (item, item)
                    for xx in range(int(a_), int(b_) + 1):
                        if 0 <= xx < W and 0 <= yy < H and (only2 is None or g[yy][xx] in only2):
                            g[yy][xx] = K
            continue
        o, rest = _opts(tok[1:])
        only = set(o['only']) if 'only' in o else None
        notk = set(o['not']) if 'not' in o else set()

        def ok(x, y):
            k = g[y][x]
            return (only is None or k in only) and k not in notk

        def rect_arg(i):
            return tuple(int(v) for v in rest[i].split(',')) if len(rest) > i else (0, 0, W - 1, H - 1)

        if cmd in ('poly', 'line'):
            sel = Canvas(W, H, '0')
            if cmd == 'poly':
                sel.poly(_pts(body), '1')
            else:
                sel.line([(int(round(x)), int(round(y))) for x, y in _pts(body)], '1')
            for y in range(H):
                for x in range(W):
                    if sel.g[y][x] == '1' and ok(x, y):
                        g[y][x] = rest[0]
        elif cmd == 'px':
            for x, y in _pts(body):
                g[int(y)][int(x)] = rest[0]
        elif cmd == 'rect':
            x0, y0, x1, y1 = (int(v) for v in body.strip().split(','))
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    if ok(x, y):
                        g[y][x] = rest[0]
        elif cmd == 'repl':
            frm, to = rest[0], rest[1]
            bx = rect_arg(2)
            for y in range(bx[1], bx[3] + 1):
                for x in range(bx[0], bx[2] + 1):
                    if g[y][x] in frm:
                        g[y][x] = to
        elif cmd == 'below':
            K, frm, over = rest[0], set(rest[1]), set(rest[2])
            n = int(o.get('n', 1))
            bx = rect_arg(3)
            snap = [r[:] for r in g]
            for y in range(bx[1], bx[3] + 1):
                for x in range(bx[0], bx[2] + 1):
                    if snap[y][x] in frm and any(0 <= y - j < H and snap[y - j][x] in over for j in range(1, n + 1)):
                        g[y][x] = K
        elif cmd == 'edge':
            K, frm, nb = rest[0], set(rest[1]), set(rest[2])
            D = {'u': (0, -1), 'd': (0, 1), 'l': (-1, 0), 'r': (1, 0)}
            bx = rect_arg(3)
            snap = [r[:] for r in g]
            for y in range(bx[1], bx[3] + 1):
                for x in range(bx[0], bx[2] + 1):
                    if snap[y][x] not in frm:
                        continue
                    for dn in o.get('dirs', 'udlr'):
                        dx, dy = D[dn]
                        if 0 <= x + dx < W and 0 <= y + dy < H and snap[y + dy][x + dx] in nb:
                            g[y][x] = K
                            break
        else:
            raise SystemExit(f'unknown paint command {cmd!r} in {raw!r}')
    return g
