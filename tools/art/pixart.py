"""Pixel-art kit for the character sheets (deterministic, Python 3 + Pillow + numpy).

Sprites are authored by hand as character grids: every character is one pixel and names a palette
entry; '.' (or ' ') is transparent. A palette entry carries a colour, a material and a tone
(-2 deep shadow .. +2 highlight). The outline character 'o' is resolved after composition into a
dark, hue-shifted colour picked from the material it borders (selective outline, "sel-out").

Frames are composed from layered parts (head, torso, arms, legs, hair, props) pasted at integer
offsets, so an animation reuses the same hand-drawn pixels instead of redrawing them.

Normal maps are derived per pixel from (a) the depth of the layer that painted it, (b) a bevel
from the distance to the edge of its material region and (c) the painted tone (lighter pixels
lean toward the top-left key light, darker ones away), so the dynamic light agrees with the
shading drawn into the albedo. Convention: RGB = normal * 0.5 + 0.5 with x right, y up (screen),
z toward the viewer; alpha = coverage (same silhouette as the albedo).
"""

from __future__ import annotations

import colorsys
import numpy as np
from PIL import Image, ImageDraw

TRANSPARENT = '.'
OUTLINE = 'o'


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ---------------------------------------------------------------------------------------------
# Palettes


class Palette:
    """char -> colour, material, tone. outlines: material -> outline colour (sel-out)."""

    def __init__(self, entries: dict, outlines: dict, default_outline: str, bevel: dict | None = None):
        self.entries = {}
        for ch, spec in entries.items():
            col, mat, tone = spec
            self.entries[ch] = {'rgb': hex_rgb(col), 'mat': mat, 'tone': tone}
        self.outlines = {m: hex_rgb(c) for m, c in outlines.items()}
        self.default_outline = hex_rgb(default_outline)
        self.bevel = bevel or {}

    def colours(self) -> list[tuple[int, int, int]]:
        cols = {e['rgb'] for e in self.entries.values()}
        cols |= set(self.outlines.values())
        cols.add(self.default_outline)
        return sorted(cols)


# ---------------------------------------------------------------------------------------------
# Grids


def G(text: str) -> np.ndarray:
    """Parse a grid. Leading/trailing blank lines are dropped; rows are padded with '.'."""
    rows = text.split('\n')
    while rows and not rows[0].strip():
        rows.pop(0)
    while rows and not rows[-1].strip():
        rows.pop()
    # strip a common indentation made of spaces only (grids use '.' for transparency)
    indent = min((len(r) - len(r.lstrip(' ')) for r in rows if r.strip()), default=0)
    rows = [r[indent:].rstrip() for r in rows]
    w = max(len(r) for r in rows)
    a = np.full((len(rows), w), TRANSPARENT, dtype='<U1')
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            a[y, x] = TRANSPARENT if c == ' ' else c
    return a


def flip(grid: np.ndarray) -> np.ndarray:
    return grid[:, ::-1].copy()


def sub(grid: np.ndarray, mapping: dict) -> np.ndarray:
    """Replace characters (e.g. recolour a part, swap a face)."""
    out = grid.copy()
    for a, b in mapping.items():
        out[grid == a] = b
    return out


class Part:
    """A grid with an anchor (the pixel that attaches to the skeleton point)."""

    def __init__(self, grid, anchor=(0, 0), z=0.0, name=''):
        self.grid = G(grid) if isinstance(grid, str) else grid
        self.anchor = anchor
        self.z = z
        self.name = name

    @property
    def w(self):
        return self.grid.shape[1]

    @property
    def h(self):
        return self.grid.shape[0]

    def flipped(self) -> 'Part':
        ax, ay = self.anchor
        return Part(flip(self.grid), (self.w - 1 - ax, ay), self.z, self.name + '~')

    def subbed(self, mapping: dict) -> 'Part':
        return Part(sub(self.grid, mapping), self.anchor, self.z, self.name)


# ---------------------------------------------------------------------------------------------
# Canvas


class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.ch = np.full((h, w), TRANSPARENT, dtype='<U1')
        self.z = np.zeros((h, w), np.float32)
        self.layer = np.zeros((h, w), np.int16)
        self._next = 1

    def copy(self) -> 'Canvas':
        c = Canvas(self.w, self.h)
        c.ch = self.ch.copy(); c.z = self.z.copy(); c.layer = self.layer.copy(); c._next = self._next
        return c

    def put(self, part, x: int, y: int, z: float | None = None, only=None, under=None, skip=None):
        """Paste a Part (anchored at x, y) or a raw grid (top-left at x, y).

        only:  paint only over canvas pixels whose char is in this set (e.g. straps on cloth)
        under: paint only where the canvas is transparent or its char is in this set
        skip:  chars of the part that are not pasted
        """
        if isinstance(part, Part):
            grid, (ax, ay) = part.grid, part.anchor
            zz = part.z if z is None else z
        else:
            grid, ax, ay = part, 0, 0
            zz = 0.0 if z is None else z
        lid = self._next
        self._next += 1
        x0, y0 = x - ax, y - ay
        gh, gw = grid.shape
        for j in range(gh):
            ty = y0 + j
            if ty < 0 or ty >= self.h:
                continue
            for i in range(gw):
                c = grid[j, i]
                if c == TRANSPARENT:
                    continue
                if skip and c in skip:
                    continue
                tx = x0 + i
                if tx < 0 or tx >= self.w:
                    continue
                cur = self.ch[ty, tx]
                if only is not None and cur not in only:
                    continue
                if under is not None and cur != TRANSPARENT and cur not in under:
                    continue
                self.ch[ty, tx] = c
                self.z[ty, tx] = zz
                self.layer[ty, tx] = lid
        return lid

    def set(self, x, y, c, z=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.ch[y, x] = c
            if z is not None:
                self.z[y, x] = z

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.ch[y, x]
        return TRANSPARENT

    def shifted(self, dx: int, dy: int) -> 'Canvas':
        c = Canvas(self.w, self.h)
        ys, xs = np.nonzero(self.ch != TRANSPARENT)
        ty, tx = ys + dy, xs + dx
        ok = (ty >= 0) & (ty < self.h) & (tx >= 0) & (tx < self.w)
        c.ch[ty[ok], tx[ok]] = self.ch[ys[ok], xs[ok]]
        c.z[ty[ok], tx[ok]] = self.z[ys[ok], xs[ok]]
        c.layer[ty[ok], tx[ok]] = self.layer[ys[ok], xs[ok]]
        return c

    def mask(self) -> np.ndarray:
        return self.ch != TRANSPARENT

    def bbox(self):
        ys, xs = np.nonzero(self.mask())
        if len(xs) == 0:
            return None
        return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


# ---------------------------------------------------------------------------------------------
# Finishing: outline safety net, sel-out recolour, albedo


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def close_outline(cv: Canvas, pal: Palette) -> int:
    """Safety net: any opaque non-outline pixel touching transparency gets an outline pixel
    outside it. Returns how many were added (0 when the hand-drawn outline is complete)."""
    m = cv.mask()
    add = []
    for y in range(cv.h):
        for x in range(cv.w):
            if m[y, x]:
                continue
            for dx, dy in N4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < cv.w and 0 <= ny < cv.h and m[ny, nx] and cv.ch[ny, nx] != OUTLINE:
                    add.append((x, y, cv.z[ny, nx]))
                    break
    for x, y, z in add:
        cv.ch[y, x] = OUTLINE
        cv.z[y, x] = z
    return len(add)


def outline_colours(cv: Canvas, pal: Palette) -> np.ndarray:
    """Per pixel RGB for outline pixels: the outline colour of the bordering material that
    occurs most often among the 4- (then 8-) neighbours; the default outline otherwise."""
    out = np.zeros((cv.h, cv.w, 3), np.uint8)
    for y in range(cv.h):
        for x in range(cv.w):
            if cv.ch[y, x] != OUTLINE:
                continue
            col = None
            for hood in (N4, N8):
                counts = {}
                for dx, dy in hood:
                    c = cv.get(x + dx, y + dy)
                    if c in (TRANSPARENT, OUTLINE):
                        continue
                    e = pal.entries.get(c)
                    if not e:
                        continue
                    m = e['mat']
                    if m in pal.outlines:
                        counts[m] = counts.get(m, 0) + 1
                if counts:
                    best = max(counts.items(), key=lambda kv: (kv[1], -sum(pal.outlines[kv[0]])))
                    col = pal.outlines[best[0]]
                    break
            out[y, x] = col if col is not None else pal.default_outline
    return out


def albedo(cv: Canvas, pal: Palette) -> np.ndarray:
    """RGBA uint8 image of the canvas."""
    img = np.zeros((cv.h, cv.w, 4), np.uint8)
    oc = outline_colours(cv, pal)
    for y in range(cv.h):
        for x in range(cv.w):
            c = cv.ch[y, x]
            if c == TRANSPARENT:
                continue
            if c == OUTLINE:
                img[y, x, :3] = oc[y, x]
            else:
                e = pal.entries.get(c)
                if e is None:
                    raise KeyError(f'palette has no entry for {c!r} at {x},{y}')
                img[y, x, :3] = e['rgb']
            img[y, x, 3] = 255
    return img


# ---------------------------------------------------------------------------------------------
# Normal maps


def _erode(m: np.ndarray) -> np.ndarray:
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    e[0, :] = e[-1, :] = False
    e[:, 0] = e[:, -1] = False
    return e


def normal_map(cv: Canvas, pal: Palette, key=(-0.55, 0.62), tone_tilt=0.16, z_scale=0.9, smooth=True) -> np.ndarray:
    """RGBA uint8 normal map (see module docstring)."""
    h, w = cv.h, cv.w
    opaque = cv.mask()
    mats = np.full((h, w), '', dtype=object)
    tones = np.zeros((h, w), np.float32)
    for y in range(h):
        for x in range(w):
            c = cv.ch[y, x]
            if c == TRANSPARENT:
                continue
            if c == OUTLINE:
                # an outline pixel belongs to the material it borders (for the bevel)
                best = None
                for dx, dy in N4:
                    cc = cv.get(x + dx, y + dy)
                    if cc not in (TRANSPARENT, OUTLINE) and cc in pal.entries:
                        best = pal.entries[cc]['mat']
                        if cv.layer[y + dy, x + dx] == cv.layer[y, x]:
                            break
                mats[y, x] = best or '_line'
                tones[y, x] = -1.0
            else:
                e = pal.entries[c]
                mats[y, x] = e['mat']
                tones[y, x] = e['tone']

    # bevel: distance (in erosion steps) from the edge of each material region of each layer
    dist = np.zeros((h, w), np.float32)
    keys = {}
    for y in range(h):
        for x in range(w):
            if opaque[y, x]:
                keys.setdefault((mats[y, x], int(cv.layer[y, x])), []).append((y, x))
    for (mat, lid), pts in keys.items():
        m = np.zeros((h, w), bool)
        ys, xs = zip(*pts)
        m[list(ys), list(xs)] = True
        cur = m
        for step in range(1, 5):
            cur = _erode(cur)
            if not cur.any():
                break
            dist[cur] = step
    profile = np.array([0.0, 0.75, 1.25, 1.55, 1.7], np.float32)
    bev = profile[np.clip(dist.astype(int), 0, 4)]
    scale = np.ones((h, w), np.float32)
    for y in range(h):
        for x in range(w):
            if opaque[y, x]:
                scale[y, x] = pal.bevel.get(mats[y, x], 1.0)
    height = np.where(opaque, cv.z * z_scale + bev * scale, 0.0).astype(np.float32)

    if smooth:
        p = np.pad(height, 1, mode='edge')
        hs = (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:] + 2 * p[1:-1, :-2] + 4 * p[1:-1, 1:-1]
              + 2 * p[1:-1, 2:] + p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) / 16.0
        height = np.where(opaque, 0.5 * height + 0.5 * hs, 0.0)

    p = np.pad(height, 1, mode='constant')
    # Sobel; image y grows downward, normal y points up
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:] - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]) / 8.0
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:] - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]) / 8.0
    nx = -gx
    ny = gy
    kx, ky = key
    kl = (kx * kx + ky * ky) ** 0.5
    nx = nx + tones * tone_tilt * kx / kl
    ny = ny + tones * tone_tilt * ky / kl
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0] = np.clip(np.round((nx * 0.5 + 0.5) * 255), 0, 255)
    img[..., 1] = np.clip(np.round((ny * 0.5 + 0.5) * 255), 0, 255)
    img[..., 2] = np.clip(np.round((nz * 0.5 + 0.5) * 255), 0, 255)
    img[..., 3] = np.where(opaque, 255, 0)
    img[~opaque, :3] = (128, 128, 255)
    img[~opaque, 3] = 0
    return img


# ---------------------------------------------------------------------------------------------
# Viewing helpers (for iteration and contact sheets)


def checker(w, h, k, a=(58, 62, 70), b=(66, 70, 79)):
    img = Image.new('RGB', (w, h), a)
    d = ImageDraw.Draw(img)
    for y in range(0, h, k):
        for x in range(0, w, k):
            if ((x // k) + (y // k)) % 2:
                d.rectangle([x, y, x + k - 1, y + k - 1], fill=b)
    return img


def zoom(rgba: np.ndarray, k: int, bg=None, grid=False) -> Image.Image:
    im = Image.fromarray(rgba, 'RGBA')
    big = im.resize((im.width * k, im.height * k), Image.NEAREST)
    base = checker(big.width, big.height, max(4, k * 2)) if bg is None else Image.new('RGB', big.size, bg)
    base.paste(big, (0, 0), big)
    if grid and k >= 6:
        d = ImageDraw.Draw(base)
        for x in range(0, big.width, k):
            d.line([(x, 0), (x, big.height)], fill=(0, 0, 0) if x % (k * 8) == 0 else (40, 44, 50))
        for y in range(0, big.height, k):
            d.line([(0, y), (big.width, y)], fill=(0, 0, 0) if y % (k * 8) == 0 else (40, 44, 50))
    return base


def lit_preview(rgba: np.ndarray, nrm: np.ndarray, light=(-0.6, 0.5, 0.65), ambient=0.55, strength=0.75) -> np.ndarray:
    """Quick CPU relight to sanity-check a normal map: albedo * (ambient + strength * N.L)."""
    n = nrm[..., :3].astype(np.float32) / 255.0 * 2 - 1
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    d = np.clip((n * L).sum(-1), 0, 1)
    k = ambient + strength * d
    out = rgba.copy().astype(np.float32)
    out[..., :3] = np.clip(out[..., :3] * k[..., None], 0, 255)
    return out.astype(np.uint8)
