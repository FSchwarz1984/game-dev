"""Turn the renderer's supersampled buffers into pixel art: coverage and material votes per pixel,
banded tones from a top-left key light, ambient occlusion and cast shadows, a 1-px sel-out outline
outside the silhouette, separation lines where one part overlaps another, cleanup of stray tones,
and a matching normal map. No dithering anywhere (CLAUDE.md character light protection)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

N4 = ((0, 1), (0, -1), (1, 0), (-1, 0))


def hexrgb(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass
class Mat:
    name: str
    ramp: list            # hex colours, dark -> light
    outline: str          # outline colour (sel-out) where this material meets the background
    cuts: list            # ascending light thresholds, len(ramp) - 1
    prio: float = 1.0     # weight in the per-pixel material vote
    line: int = 0         # ramp index for separation lines drawn on this material
    min_tone: int = 0     # brightness floor (ramp index)
    rim: int = -1         # ramp index for the top-left rim (-1: none)

    def rgb(self, i):
        return hexrgb(self.ramp[int(np.clip(i, 0, len(self.ramp) - 1))])


@dataclass
class Palette:
    mats: list                                   # Mat, index = material id
    light: tuple = (-0.58, 0.60, 0.55)           # toward the key light, camera space (top-left, front)
    extra: dict = field(default_factory=dict)    # named colours for decals

    def __post_init__(self):
        self.ids = {m.name: i for i, m in enumerate(self.mats)}
        L = np.array(self.light, float)
        self.L = L / np.linalg.norm(L)

    def colours(self):
        cols = set()
        for m in self.mats:
            cols |= {hexrgb(c) for c in m.ramp}
            cols.add(hexrgb(m.outline))
        cols |= {hexrgb(c) for c in self.extra.values()}
        return cols


def blocks(a, S):
    """(H*S, W*S[, c]) -> (H, W, S*S[, c])"""
    H, W = a.shape[0] // S, a.shape[1] // S
    if a.ndim == 2:
        return a.reshape(H, S, W, S).transpose(0, 2, 1, 3).reshape(H, W, S * S)
    c = a.shape[2]
    return a.reshape(H, S, W, S, c).transpose(0, 2, 1, 3, 4).reshape(H, W, S * S, c)


def stylize(buf, S, pal: Palette, cover=0.5, line_gap=2.0, keep_parts=(), shade=None):
    """Returns a dict: mat (H, W) int (-1 empty), tone (H, W), depth, part, nrm (H, W, 3), light (H, W)."""
    mats = blocks(buf['mat'], S)
    parts = blocks(buf['part'], S)
    depth = blocks(buf['depth'], S)
    nrm = blocks(buf['nrm'], S)
    ao = blocks(buf['ao'], S)
    sh = blocks(buf['sh'], S)
    H, W, n = mats.shape
    hit = mats >= 0
    hole = mats == -2
    nhit = hit.sum(-1)
    nhole = hole.sum(-1)
    opaque = (nhit >= cover * n) & (nhit > nhole)
    nm = len(pal.mats)
    votes = np.zeros((H, W, nm), np.float32)
    for m in range(nm):
        votes[..., m] = (mats == m).sum(-1) * pal.mats[m].prio
    mid = np.where(opaque, votes.argmax(-1), -1)
    sel = (mats == mid[..., None]) & opaque[..., None]
    cnt = np.maximum(sel.sum(-1), 1)
    # light per sample: wrapped lambert, cast shadow, ambient occlusion
    L = pal.L
    ndl = (nrm * L).sum(-1)
    lam = np.clip((ndl + 0.35) / 1.35, 0, 1)
    v = (0.30 + 0.70 * lam * (0.45 + 0.55 * sh)) * (0.55 + 0.45 * ao)
    if shade is not None:
        v = shade(v, nrm, ao, sh)
    light = (v * sel).sum(-1) / cnt
    d = np.where(sel, depth, 0).sum(-1) / cnt
    nn = (nrm * sel[..., None]).sum(-2) / cnt[..., None]
    ln = np.linalg.norm(nn, axis=-1, keepdims=True)
    nn = np.where(ln > 1e-6, nn / np.maximum(ln, 1e-6), np.array([0, 0, 1.0]))
    # part: the most common part among the chosen samples
    pt = np.full((H, W), -1, np.int32)
    ys, xs = np.nonzero(opaque)
    for y, x in zip(ys, xs):
        vals = parts[y, x][sel[y, x]]
        if len(vals):
            u, c = np.unique(vals, return_counts=True)
            pt[y, x] = int(u[c.argmax()])
    tone = np.zeros((H, W), np.int32)
    for m, M in enumerate(pal.mats):
        k = mid == m
        t = np.searchsorted(np.array(M.cuts, float), light[k], side='right')
        tone[k] = np.maximum(t, M.min_tone)
    hole_px = (nhole >= nhit) & (nhole > 0) & ~opaque
    return {'mat': mid, 'tone': tone, 'depth': np.where(opaque, d, -1e9), 'part': pt, 'nrm': nn, 'light': light,
            'opaque': opaque, 'hole': hole_px}


def clean_tones(px, pal: Palette, passes=2, protect=None):
    """A pixel whose tone differs from all four neighbours of the same material, which agree among
    themselves, takes their tone (removes salt-and-pepper banding)."""
    mat, tone = px['mat'], px['tone']
    H, W = mat.shape
    for _ in range(passes):
        new = tone.copy()
        for y in range(H):
            for x in range(W):
                m = mat[y, x]
                if m < 0 or (protect is not None and protect[y, x]):
                    continue
                nb = []
                for dy, dx in N4:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and mat[yy, xx] == m:
                        nb.append(tone[yy, xx])
                if len(nb) >= 3 and tone[y, x] not in nb:
                    vals, cnt = np.unique(nb, return_counts=True)
                    if cnt.max() >= len(nb) - 1:
                        new[y, x] = vals[cnt.argmax()]
        tone[:] = new
    return px


def merge_islands(px, pal: Palette, max_size=2, skip=()):
    """Tone islands of max_size pixels or fewer (4-connected, same material and tone) take the most
    common tone among their same-material neighbours. Materials in `skip` keep their small details
    (eyes, bells)."""
    from scipy import ndimage as ndi
    mat, tone = px['mat'], px['tone']
    H, W = mat.shape
    for m in np.unique(mat[mat >= 0]):
        if pal.mats[m].name in skip:
            continue
        for t in np.unique(tone[mat == m]):
            lab, n = ndi.label((mat == m) & (tone == t))
            if n == 0:
                continue
            sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
            for i, sz in enumerate(sizes, start=1):
                if sz > max_size:
                    continue
                ys, xs = np.nonzero(lab == i)
                cnt = {}
                for y, x in zip(ys, xs):
                    for dy, dx in N4:
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and mat[yy, xx] == m and lab[yy, xx] != i:
                            cnt[tone[yy, xx]] = cnt.get(tone[yy, xx], 0) + 1
                if cnt:
                    tone[ys, xs] = max(cnt.items(), key=lambda kv: kv[1])[0]
    return px


def separation_lines(px, pal: Palette, gap=2.0, parts_only=True):
    """Where a pixel sits behind a neighbouring pixel of another part by more than `gap` units, it
    takes its material's line tone: the overlap reads as a drawn line, not a merged blob."""
    mat, tone, depth, part = px['mat'], px['tone'], px['depth'], px['part']
    H, W = mat.shape
    line = np.zeros((H, W), bool)
    for y in range(H):
        for x in range(W):
            m = mat[y, x]
            if m < 0:
                continue
            for dy, dx in N4:
                yy, xx = y + dy, x + dx
                if not (0 <= yy < H and 0 <= xx < W) or mat[yy, xx] < 0:
                    continue
                if parts_only and part[yy, xx] == part[y, x] and mat[yy, xx] == m:
                    continue
                if depth[yy, xx] - depth[y, x] > gap:
                    line[y, x] = True
                    break
    for y, x in zip(*np.nonzero(line)):
        M = pal.mats[mat[y, x]]
        tone[y, x] = min(tone[y, x], M.line)
    px['line'] = line
    return px


def outline(px, pal: Palette):
    """1-px outline outside the silhouette (4-neighbourhood), coloured by the bordering material."""
    mat = px['mat']
    hole = px.get('hole')
    H, W = mat.shape
    out = np.full((H, W), -1, np.int32)
    for y in range(H):
        for x in range(W):
            if mat[y, x] >= 0 or (hole is not None and hole[y, x]):
                continue
            cnt = {}
            for dy, dx in N4:
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and mat[yy, xx] >= 0:
                    m = mat[yy, xx]
                    cnt[m] = cnt.get(m, 0) + 1
            if cnt:
                out[y, x] = max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    px['outline'] = out
    return px


def to_rgba(px, pal: Palette):
    mat, tone, out = px['mat'], px['tone'], px['outline']
    H, W = mat.shape
    img = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        for x in range(W):
            if mat[y, x] >= 0:
                img[y, x, :3] = pal.mats[mat[y, x]].rgb(tone[y, x])
                img[y, x, 3] = 255
            elif out[y, x] >= 0:
                img[y, x, :3] = hexrgb(pal.mats[out[y, x]].outline)
                img[y, x, 3] = 255
    for (y, x), c in px.get('paint', {}).items():
        img[y, x, :3] = c
        img[y, x, 3] = 255
    return img


def normal_map(px):
    """RGB = n * 0.5 + 0.5 with x right, y up (screen), z toward the viewer; alpha = coverage.
    Outline pixels lean outward from the silhouette."""
    mat, out, nn = px['mat'], px['outline'], px['nrm']
    H, W = mat.shape
    img = np.zeros((H, W, 4), np.uint8)
    img[..., :3] = (128, 128, 255)
    body = mat >= 0
    n = nn.copy()
    n[..., 1] = nn[..., 1]   # camera y is up already
    for y in range(H):
        for x in range(W):
            if body[y, x]:
                v = n[y, x]
            elif out[y, x] >= 0:
                gx = gy = 0.0
                for dy, dx in N4:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and body[yy, xx]:
                        gx -= dx; gy += dy
                v = np.array([gx, gy, 0.6])
                v = v / np.linalg.norm(v)
            else:
                continue
            img[y, x, :3] = np.clip(np.round((v * 0.5 + 0.5) * 255), 0, 255)
            img[y, x, 3] = 255
    return img
