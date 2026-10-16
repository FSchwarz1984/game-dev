"""The grass field (round 5, decision-log G5R3-2): a continuous sward of small blade tufts in the
manner of Breath of the Wild / Genshin, drawn as pixel art.

The user: "草的表現…太雜亂了，顏色深一塊淺一塊…能不能做類似曠野之息或者原神那種比較自然柔順和地面塗色相協調
相同一相一致但又明顯不同，而且有一定物理效果的狀態". So:
* the colour is the ground's: every tuft takes the terrain's own palette row and macro tone at its
  root (the shader computes them exactly as toon_terrain does), its blades go one tone lighter (the
  ramp's lighter tones lean warm) toward the tips; there is no per-clump or per-tuft tint at all;
* the light is the ground's: the tuft is lit with the ground normal at its root and the terrain's
  wrap, AO, shade and sun flecks, so the sward never breaks into light and dark blobs;
* variation is large and slow: the height of the sward follows a field a few metres across (taller
  in the open, trodden short along the paths, thin and short in the shade and on moss), no clumps;
* the blades are 1 px strokes in two tones (root, tip): the per-pixel contrast stays one palette step;
* physics in the shader (godot/world3d/grass_field.gdshader): whole-pixel sway, gust fronts that run
  across the field with the wind, and a bend map (godot/world3d/grass.gd) that pushes the blades
  aside where she, Saji and the small creatures walk and lets them stand up again over a few seconds.

The tufts are placed in the shader (a lattice per 16 m chunk, jittered by hashes; godot/world3d/
grass.gd draws one shared MultiMesh per chunk), from the fields written here into m4.png on the
splat grid: r = sward density, g = sward height, b = flower patches, a = thin (moss and forest floor).
So there is no per-tuft data on disk and the sward always agrees with the ground's materials.
Output: m4.png (terrain/<name>), grass_blades.png (terrain/common: 8 x 4 cells of 16 x 16; R = tone
offset + 4, G = accent index + 1, A = coverage) and the list of chunks that have grass.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from . import geom, noise

CHUNK = 16.0
LATTICE = 50              # tufts per chunk side: 0.32 m apart (a tuft is 5-14 px tall, 0.2-0.5 m across)
CELL = 16
COLS = 8
# cell index ranges by height class (the shader picks among them)
SHORT = range(0, 4)
MID = range(4, 8)
TALL = range(8, 12)
TALLER = range(12, 16)
FLOWER = range(16, 24)
THIN = range(24, 28)      # sparse, short, for moss and the forest floor

# accents (pixelart.ACCENT_ORDER "WYBPRLOEKGS"): white, yellow, blue-violet, pink
ACC = {"W": 0, "Y": 1, "B": 2, "P": 3}


def fields(L, W, F, Xs, Zs, Hs, cs, seed):
    """m4 on the splat grid: (density, height, flower patches, thin), each 0..1."""
    zero = np.zeros_like(Hs)
    grass, moss, litter = W["grass"], W["moss"], W["litter"]
    canopy = F["canopy"]
    trail = F.get("trail_k", zero)
    pave = F.get("pave_k", zero)
    stone = F.get("stone_k", zero)
    wear = np.maximum(F.get("path_wear", zero), F.get("yard_wear", zero))
    yard = geom.smoothstep(0.4, -0.2, F["yard_sdf"])
    sanct = F.get("sanctum", zero)
    gz, gx = np.gradient(Hs, cs)
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    near_trail = geom.smoothstep(0.0, 0.45, trail) * (1 - geom.smoothstep(0.8, 1.0, trail))
    # where the sward grows: the grass material (and a little into moss and the forest floor); never
    # on the paths, the paving, the stepping stones and steps, the yard's packed earth or in water
    dens = geom.smoothstep(0.3, 0.62, grass) + geom.smoothstep(0.4, 0.8, moss) * 0.22 + geom.smoothstep(0.4, 0.8, litter) * 0.12
    dens *= 1.0 - geom.smoothstep(0.35, 0.75, np.maximum(wear, trail * 0.9))
    # (round 5, the paths' iron rule) short sparse tufts on a trail's untrodden margins: its edge is
    # not a line where the sward stops
    edge = F.get("edge_k", zero)
    tread = F.get("tread_k", zero)
    dens = np.maximum(dens, 0.42 * edge * (1.0 - tread) * (1.0 - 0.6 * geom.smoothstep(0.3, 0.9, canopy)) * (1.0 - geom.smoothstep(0.15, 0.6, pave)))
    dens *= 1.0 - geom.smoothstep(0.15, 0.6, pave)
    dens *= 1.0 - geom.smoothstep(0.2, 0.6, stone)
    dens *= 1.0 - yard * 0.97
    dens *= geom.smoothstep(0.15, 0.5, F["water_d"])
    dens *= 1.0 - 0.55 * geom.smoothstep(0.3, 0.9, canopy)
    dens *= 1.0 - geom.smoothstep(38.0, 48.0, slope)
    # the height: one slow field, trodden short along the paths, short in the shade and on moss
    big = noise.fbm(Xs / 7.0, Zs / 7.0, 3, seed + 7310)
    H = 0.28 + 0.62 * geom.smoothstep(0.25, 0.75, big)
    H += 0.08 * sanct
    H -= 0.42 * near_trail
    H -= 0.32 * geom.smoothstep(0.3, 0.9, canopy)
    H -= 0.35 * geom.smoothstep(0.4, 0.8, np.maximum(moss, litter)) * (1 - geom.smoothstep(0.4, 0.7, grass))
    H -= 0.15 * geom.smoothstep(25.0, 40.0, slope)
    # a few flowers in loose patches, out in the light, not on the trodden edges
    fpatch = geom.smoothstep(0.55, 0.8, noise.fbm(Xs / 4.0, Zs / 4.0, 2, seed + 7320))
    fpatch *= (1 - geom.smoothstep(0.2, 0.6, canopy)) * (1 - near_trail) * geom.smoothstep(0.5, 0.8, grass)
    thin = ((np.maximum(moss, litter) > 0.5) & (grass < 0.45)).astype(np.float64)
    m4 = np.stack([np.clip(dens, 0, 1), np.clip(H, 0, 1), np.clip(fpatch, 0, 1), thin], -1)
    return m4


def _blade(img, x0, h, lean, curve, tip_from, root_y=15):
    """One 1 px blade from the root row up, in three tones: the ground's at the root, one lighter from
    a little below its middle, two lighter at the tip (the ramp's lights lean warm)."""
    mid_from = tip_from * 0.75
    for k in range(h):
        t = k / max(h - 1, 1)
        x = x0 + lean * t * h * 0.5 + curve * (t ** 2) * h * 0.5
        xi = int(round(x))
        y = root_y - k
        if 0 <= xi < CELL and 0 <= y < CELL:
            tone = 2 if t >= tip_from else (1 if t >= mid_from else 0)
            img[y, xi] = (4 + tone, 0, 0, 255)


def _tuft(rng, H, n, spread, tip_from=0.5, arch=0.0):
    img = np.zeros((CELL, CELL, 4), np.uint8)
    order = sorted(range(n), key=lambda i: rng.uniform())
    for i in order:
        off = (i - (n - 1) / 2.0) * spread + rng.uniform(-0.4, 0.4)
        x0 = 7.5 + off * 0.6
        h = int(round(H * rng.uniform(0.62, 1.0)))
        lean = off * 0.18 + rng.uniform(-0.25, 0.25)
        curve = np.sign(lean if abs(lean) > 0.05 else rng.uniform(-1, 1)) * arch * rng.uniform(0.3, 1.0)
        _blade(img, x0, max(h, 2), lean, curve, tip_from + rng.uniform(-0.08, 0.08))
    return img


def _flower(rng, kind):
    img = _tuft(rng, int(rng.integers(6, 9)), int(rng.integers(3, 5)), 1.1)
    a = ACC[kind]
    # one to three heads on stems a little above the blades
    for _ in range(int(rng.integers(1, 4))):
        x = int(np.clip(round(7.5 + rng.uniform(-3.0, 3.0)), 1, 14))
        top = int(rng.integers(3, 6))
        for y in range(top + 1, 15):
            if img[y, x, 3] == 0:
                img[y, x] = (4, 0, 0, 255)
        img[top, x] = (4, a + 1, 0, 255)
        if kind in ("B", "P") and rng.uniform() < 0.6:
            img[top, min(x + 1, 15)] = (4, a + 1, 0, 255)
        if kind == "Y":                       # ominaeshi: a flat little umbel
            for dx in (-1, 1):
                if 0 <= x + dx < 16:
                    img[top, x + dx] = (4, a + 1, 0, 255)
    return img


def make_atlas(seed=7300):
    rng = np.random.default_rng(seed)
    cells = []
    for _ in SHORT:
        cells.append(_tuft(rng, int(rng.integers(4, 7)), int(rng.integers(3, 6)), 1.3, 0.62))
    for _ in MID:
        cells.append(_tuft(rng, int(rng.integers(7, 10)), int(rng.integers(4, 7)), 1.2, 0.66))
    for _ in TALL:
        cells.append(_tuft(rng, int(rng.integers(10, 13)), int(rng.integers(5, 8)), 1.15, 0.68, arch=0.25))
    for _ in TALLER:
        cells.append(_tuft(rng, int(rng.integers(12, 15)), int(rng.integers(5, 8)), 1.1, 0.7, arch=0.4))
    for k in "BYPWBYPW":
        cells.append(_flower(rng, k))
    for _ in THIN:
        cells.append(_tuft(rng, int(rng.integers(3, 6)), 2, 1.6, 0.5))
    rows = (len(cells) + COLS - 1) // COLS
    atlas = np.zeros((rows * CELL, COLS * CELL, 4), np.uint8)
    for k, c in enumerate(cells):
        atlas[(k // COLS) * CELL:(k // COLS + 1) * CELL, (k % COLS) * CELL:(k % COLS + 1) * CELL] = c
    return atlas


def write(m4, Xs, Zs, Hs, out: Path, out_common: Path, seed):
    """m4.png, the atlas, and the chunks (16 m, on the splat grid's origin) that have any sward."""
    atlas = make_atlas(seed + 7300)
    out_common.mkdir(parents=True, exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(out_common / "grass_blades.png")
    imp = out_common / "grass_blades.png.import"
    if not imp.exists():
        imp.write_text('[remap]\n\nimporter="image"\ntype="Image"\n')
    Image.fromarray((np.clip(m4, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(out / "m4.png")
    imp = out / "m4.png.import"
    if not imp.exists():
        imp.write_text('[remap]\n\nimporter="image"\ntype="Image"\n')
    x0, z0 = float(Xs[0, 0]), float(Zs[0, 0])
    cs = float(Xs[0, 1] - Xs[0, 0])
    n = int(round(CHUNK / cs))
    chunks = []
    total = 0.0
    for j in range(0, Hs.shape[0] - 1, n):
        for i in range(0, Hs.shape[1] - 1, n):
            d = m4[j:j + n + 1, i:i + n + 1, 0]
            if d.max() < 0.05:
                continue
            hh = Hs[j:j + n + 1, i:i + n + 1]
            chunks.append({"origin": [round(x0 + i * cs, 3), round(z0 + j * cs, 3)],
                           "y": [round(float(hh.min()) - 0.2, 3), round(float(hh.max()) + 0.8, 3)]})
            total += float(d.sum()) * cs * cs
    tufts = int(total * (LATTICE / CHUNK) ** 2)
    return {"map": "m4.png", "channels": ["density", "height", "flowers", "thin"], "atlas": "res://world3d/terrain/common/grass_blades.png",
            "cell": CELL, "cols": COLS, "chunk": CHUNK, "lattice": LATTICE, "chunks": chunks,
            "stats": {"tufts": tufts, "chunks": len(chunks)}}
