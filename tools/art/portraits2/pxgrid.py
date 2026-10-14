"""Pixel grids: read the authored text data, compose a portrait, render, check.

Data layout (tools/art/portraits2/data/<char>/):
  base.txt   the bust without a face: SIZE lines of SIZE keys (palettes.py), '.' = transparent
  parts.txt  named parts:   == name @ x,y   followed by the part's rows ('.' = keep what is below)
  faces.txt  one expression per line:   name: part part part@x,y ...   (layered in order; @x,y moves a part)
Lines starting with '#' are comments. Every row of a grid is written out pixel by pixel; nothing is generated.
"""

import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from palettes import PALETTES, rgb

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
SIZE = 80


def _rows(lines):
    out = []
    for ln in lines:
        s = ln.rstrip('\n')
        if s.strip() == '' or s.lstrip().startswith('#'):
            continue
        out.append(s.rstrip())
    return out


def read_base(char):
    with open(os.path.join(DATA, char, 'base.txt'), encoding='utf-8') as f:
        rows = _rows(f.readlines())
    if len(rows) != SIZE:
        raise ValueError(f'{char} base: {len(rows)} rows, expected {SIZE}')
    for y, r in enumerate(rows):
        if len(r) != SIZE:
            raise ValueError(f'{char} base row {y}: {len(r)} keys, expected {SIZE}')
    return [list(r) for r in rows]


PART_HEAD = re.compile(r'^==\s*([\w.-]+)\s*@\s*(-?\d+)\s*,\s*(-?\d+)\s*$')


def read_parts(path):
    parts = {}
    if not os.path.exists(path):
        return parts
    name = None
    with open(path, encoding='utf-8') as f:
        for ln in f:
            s = ln.rstrip('\n')
            m = PART_HEAD.match(s.strip())
            if m:
                name = m.group(1)
                if name in parts:
                    raise ValueError(f'{path}: part {name} defined twice')
                parts[name] = {'x': int(m.group(2)), 'y': int(m.group(3)), 'rows': []}
                continue
            if s.strip() == '' or s.lstrip().startswith('#'):
                continue
            if name is None:
                raise ValueError(f'{path}: rows before the first part header: {s!r}')
            parts[name]['rows'].append(s.rstrip())
    return parts


def read_faces(char):
    faces = {}
    with open(os.path.join(DATA, char, 'faces.txt'), encoding='utf-8') as f:
        for ln in f:
            s = ln.split('#', 1)[0].strip()
            if not s:
                continue
            name, rest = s.split(':', 1)
            faces[name.strip()] = rest.split()
    return faces


def load(char):
    parts = read_parts(os.path.join(DATA, 'common', 'parts.txt'))
    for k, v in read_parts(os.path.join(DATA, char, 'parts.txt')).items():
        parts[k] = v  # a character's own part overrides a common one of the same name
    return read_base(char), parts, read_faces(char)


def compose(base, parts, recipe):
    """Layer the recipe's parts over a copy of the base; returns the key grid."""
    g = [row[:] for row in base]
    for ref in recipe:
        name, x, y = ref, None, None
        if '@' in ref:
            name, at = ref.split('@')
            x, y = (int(v) for v in at.split(','))
        if name not in parts:
            raise KeyError(f'unknown part {name}')
        p = parts[name]
        x = p['x'] if x is None else x
        y = p['y'] if y is None else y
        for j, row in enumerate(p['rows']):
            for i, k in enumerate(row):
                if k == '.' or k == ' ':
                    continue
                yy, xx = y + j, x + i
                if 0 <= yy < SIZE and 0 <= xx < SIZE:
                    g[yy][xx] = '.' if k == '_' else k  # '_' erases to transparent
    return g


def to_image(grid, char):
    pal = PALETTES[char]
    h, w = len(grid), len(grid[0])
    a = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(grid):
        for x, k in enumerate(row):
            if k == '.':
                continue
            if k not in pal:
                raise KeyError(f'{char}: key {k!r} at ({x},{y}) not in palette')
            a[y, x, :3] = rgb(pal[k])
            a[y, x, 3] = 255
    return Image.fromarray(a, 'RGBA')


def orphans(grid, keys=None):
    """Pixels with no 8-neighbour of the same key (the classic 'stray pixel'); returns [(x, y, key)]."""
    h, w = len(grid), len(grid[0])
    out = []
    for y in range(h):
        for x in range(w):
            k = grid[y][x]
            if k == '.' or (keys and k not in keys):
                continue
            alone = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (dx or dy) and 0 <= y + dy < h and 0 <= x + dx < w and grid[y + dy][x + dx] == k:
                        alone = False
            if alone:
                out.append((x, y, k))
    return out


# ------------------------------------------------------------------------------------------------- previews

def _font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def zoom(img, k=8, grid=True, bg=(78, 70, 86), label=True):
    """Nearest-neighbour zoom with a pixel grid and coordinates every 5 px (for pixel-by-pixel editing)."""
    w, h = img.size
    m = 18 if label else 0
    out = Image.new('RGB', (w * k + m, h * k + m), (30, 28, 34))
    base = Image.new('RGBA', img.size, bg + (255,))
    base.alpha_composite(img)
    out.paste(base.convert('RGB').resize((w * k, h * k), Image.NEAREST), (m, m))
    d = ImageDraw.Draw(out)
    if grid:
        for x in range(w + 1):
            c = (255, 255, 255) if x % 10 == 0 else ((150, 150, 160) if x % 5 == 0 else (60, 58, 66))
            if x % 5 == 0 or k >= 8:
                d.line([(m + x * k, m), (m + x * k, m + h * k)], fill=c if x % 5 == 0 else (0, 0, 0), width=1)
        for y in range(h + 1):
            c = (255, 255, 255) if y % 10 == 0 else ((150, 150, 160) if y % 5 == 0 else (60, 58, 66))
            if y % 5 == 0 or k >= 8:
                d.line([(m, m + y * k), (m + w * k, m + y * k)], fill=c if y % 5 == 0 else (0, 0, 0), width=1)
    if label:
        f = _font(10)
        for x in range(0, w, 5):
            d.text((m + x * k + 1, 2), str(x), fill=(255, 220, 140), font=f)
        for y in range(0, h, 5):
            d.text((1, m + y * k + 1), str(y), fill=(255, 220, 140), font=f)
    return out


def sheet(tiles, k=1, cols=6, bg=(78, 70, 86), gap=None, labels=None, pad_label=14):
    """Tiles (RGBA, same size) at integer scale k on a mid-tone card, optional labels under each tile."""
    w, h = tiles[0].size
    gap = gap if gap is not None else max(4, 2 * k)
    lh = pad_label if labels else 0
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new('RGB', (cols * (w * k + gap) + gap, rows * (h * k + gap + lh) + gap), (34, 31, 38))
    d = ImageDraw.Draw(out)
    f = _font(11)
    for n, t in enumerate(tiles):
        x = gap + (n % cols) * (w * k + gap)
        y = gap + (n // cols) * (h * k + gap + lh)
        card = Image.new('RGBA', t.size, bg + (255,))
        card.alpha_composite(t)
        out.paste(card.convert('RGB').resize((w * k, h * k), Image.NEAREST), (x, y))
        if labels:
            d.text((x, y + h * k + 1), labels[n], fill=(240, 230, 210), font=f)
    return out
