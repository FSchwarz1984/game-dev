"""Quick composites of baked props on a flat ground for iteration and contact sheets (CPU, approximate
run-time lighting from preview.py). The Godot bench makes the definitive sheets."""
import numpy as np
from PIL import Image, ImageDraw

from . import preview as PV
from .core import PPM

GROUND = np.array([84.0, 96.0, 70.0])      # the terrain's meadow albedo (measured)


def compose(baked, tod='noon', far=0.0, ground=GROUND, pad=24, lit=False, glow=1.0, state_layers=None,
            linear=False):
    """Render a baked prop over a ground patch; returns (rgb uint8, anchor)."""
    fr = baked['frame']
    sh = baked.get('shadow')
    W, H = fr.W, fr.H
    # canvas big enough for the shadow too
    x0, y0, x1, y1 = 0, 0, W, H
    if sh is not None:
        ox, oz = sh['offset']
        h, w = sh['img'].shape[:2]
        x0 = min(x0, fr.ax + ox)
        y0 = min(y0, fr.ay + oz)
        x1 = max(x1, fr.ax + ox + w)
        y1 = max(y1, fr.ay + oz + h)
    x0 -= pad
    y0 -= pad
    x1 += pad
    y1 += pad
    CW, CH = x1 - x0, y1 - y0
    ax, ay = fr.ax - x0, fr.ay - y0
    T = PV.TOD[tod]
    g = np.ones((CH, CW, 3)) * ground[None, None, :] / 255.0
    g = g * (np.asarray(T['sky']) + np.asarray(T['sun']) * 0.75) * 255.0
    if sh is not None:
        ox, oz = sh['offset']
        h, w = sh['img'].shape[:2]
        f = PV.shadow_factor(sh['img'], T['elev'], tod=tod)
        g[ay + oz:ay + oz + h, ax + ox:ax + ox + w] *= f
    img = g
    layers = sorted(baked['layers'].items(), key=lambda kv: (kv[1]['L'].z_index, kv[1]['L'].sort_px))
    for name, L in layers:
        if state_layers is not None and name not in state_layers:
            continue
        lit_rgb = PV.light(L['rgb'], L['nrgb'], tod, linear=linear)
        if far > 0:
            hit = L['hit']
            pad1 = np.pad(hit, 1)
            edge = hit & ~(pad1[:-2, 1:-1] & pad1[2:, 1:-1] & pad1[1:-1, :-2] & pad1[1:-1, 2:])
            lit_rgb = PV.far_look(lit_rgb, far, edge)
        if lit and L['emit'].any():
            lit_rgb = lit_rgb + L['emit'] * 255.0 * glow
        m = L['a'] > 0.5
        dy = -int(round(far * 3)) if far > 0 else 0
        sub = img[(-y0) + dy:(-y0) + dy + H, (-x0):(-x0) + W]
        sub[m] = lit_rgb[m]
    out = np.clip(img, 0, 255).astype(np.uint8)
    # crop to what differs from the bare ground (the prop and the part of its shadow cast now)
    gref = np.clip(ground[None, None, :] / 255.0 * (np.asarray(T['sky']) + np.asarray(T['sun']) * 0.75) * 255.0, 0, 255)
    diff = np.abs(out.astype(np.float64) - gref).max(-1) > 2.5
    ys, xs = np.nonzero(diff)
    if ys.size:
        cy0, cy1 = max(0, ys.min() - pad), min(out.shape[0], ys.max() + 1 + pad)
        cx0, cx1 = max(0, xs.min() - pad), min(out.shape[1], xs.max() + 1 + pad)
        out = out[cy0:cy1, cx0:cx1]
        ax -= cx0
        ay -= cy0
    return out, (ax, ay)


def sheet(items, scale=3, cols=None, bg=(24, 24, 28), label=True, maxw=1800):
    """items: list of (label, rgb uint8). Shelf layout, scaled by an integer."""
    pad = 8
    x = pad
    y = pad + 12
    rowh = 0
    pos = []
    for lab, im in items:
        h, w = im.shape[:2]
        if x + w + pad > maxw // scale and x > pad:
            x = pad
            y += rowh + pad + 12
            rowh = 0
        pos.append((x, y))
        x += w + pad
        rowh = max(rowh, h)
    W = maxw // scale
    H = y + rowh + pad
    canvas = np.zeros((H, W, 3), np.uint8) + np.array(bg, np.uint8)
    for (lab, im), (px, py) in zip(items, pos):
        h, w = im.shape[:2]
        canvas[py:py + h, px:px + w] = im[:, :, :3]
    out = Image.fromarray(canvas).resize((W * scale, H * scale), Image.NEAREST)
    if label:
        d = ImageDraw.Draw(out)
        for (lab, im), (px, py) in zip(items, pos):
            d.text((px * scale, (py - 11) * scale), lab, fill=(210, 210, 210))
    return out
