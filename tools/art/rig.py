"""Frame composition shared by the character modules.

A character module defines layers (pixart grids placed in its model space) and animations. An
animation frame is a list of placements (layer, dx, dy) drawn back to front, plus anchors in model
space. compose() turns it into a Canvas the size of the character's frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pixart import Canvas, G


class L:
    """A layer: a grid placed in model space at (col, row). z feeds the normal map (depth)."""

    def __init__(self, row, text, col=0, z=0.0, only=None):
        self.grid = G(text) if isinstance(text, str) else text
        self.row, self.col, self.z = row, col, z
        self.only = only  # paint only over these canvas chars (e.g. straps on cloth)

    def flipped(self, axis_col):
        """Mirror around a model column (for left/right swaps of symmetric parts)."""
        w = self.grid.shape[1]
        g = self.grid[:, ::-1].copy()
        # the right edge maps to 2*axis - col
        new_col = 2 * axis_col - (self.col + w - 1)
        return L(self.row, g, new_col, self.z, self.only)

    def shifted(self, dc=0, dr=0):
        return L(self.row + dr, self.grid, self.col + dc, self.z, self.only)


@dataclass
class Frame:
    layers: list                       # [(L, dx, dy) | L | None]
    anchors: dict = field(default_factory=dict)   # name -> (model col, model row)
    flags: dict = field(default_factory=dict)


def compose(frame: Frame, size, origin) -> Canvas:
    fw, fh = size
    mx, my = origin
    cv = Canvas(fw, fh)
    for item in frame.layers:
        if item is None:
            continue
        if isinstance(item, L):
            lay, dx, dy = item, 0, 0
        else:
            lay, dx, dy = item
        cv.put(lay.grid, mx + lay.col + dx, my + lay.row + dy, z=lay.z,
               only=set(lay.only) if lay.only else None)
    return cv


def at(layer, dx=0, dy=0):
    return (layer, dx, dy) if layer is not None else None


def shear_h(layer: L, k: float, pivot_row: int) -> L:
    """Lean: shift each row right by round(k * (pivot_row - row)); rows above the pivot move
    forward (k > 0 leans to the right). Returns a new layer (grid widened as needed)."""
    import numpy as np
    g = layer.grid
    h, w = g.shape
    shifts = [int(round(k * (pivot_row - (layer.row + j)))) for j in range(h)]
    lo, hi = min(shifts), max(shifts)
    out = np.full((h, w + hi - lo), '.', dtype='<U1')
    for j in range(h):
        s = shifts[j] - lo
        out[j, s:s + w] = g[j]
    return L(layer.row, out, layer.col + lo, layer.z, layer.only)


def shear_v(layer: L, k: float, pivot_col: int) -> L:
    """Tilt: shift each column down by round(k * (col - pivot_col)) (k > 0 tips the right side down)."""
    import numpy as np
    g = layer.grid
    h, w = g.shape
    shifts = [int(round(k * ((layer.col + i) - pivot_col))) for i in range(w)]
    lo, hi = min(shifts), max(shifts)
    out = np.full((h + hi - lo, w), '.', dtype='<U1')
    for i in range(w):
        s = shifts[i] - lo
        out[s:s + h, i] = g[:, i]
    return L(layer.row + lo, out, layer.col, layer.z, layer.only)


def crop_rows(layer: L, r0: int, r1: int) -> L:
    """Keep model rows r0..r1 (inclusive) of a layer."""
    a = max(r0 - layer.row, 0)
    b = min(r1 - layer.row + 1, layer.grid.shape[0])
    return L(layer.row + a, layer.grid[a:b].copy(), layer.col, layer.z, layer.only)


def merge(*items) -> L:
    """Flatten several placed layers [(L, dx, dy)] into one layer (later items on top)."""
    import numpy as np
    items = [(i, 0, 0) if isinstance(i, L) else i for i in items if i is not None]
    c0 = min(l.col + dx for l, dx, dy in items)
    r0 = min(l.row + dy for l, dx, dy in items)
    c1 = max(l.col + dx + l.grid.shape[1] for l, dx, dy in items)
    r1 = max(l.row + dy + l.grid.shape[0] for l, dx, dy in items)
    out = np.full((r1 - r0, c1 - c0), '.', dtype='<U1')
    z = 0
    for l, dx, dy in items:
        y, x = l.row + dy - r0, l.col + dx - c0
        m = l.grid != '.'
        sub = out[y:y + l.grid.shape[0], x:x + l.grid.shape[1]]
        sub[m] = l.grid[m]
        z = max(z, l.z)
    return L(r0, out, c0, z)
