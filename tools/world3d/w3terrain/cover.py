"""Ground cover (round 4, G5R2-1 ⑦: "under the great tree the grass is all the same, repeated"):
many small plants as pixel-art cards, chosen by plant community, clumped by noise, every clump its
own size, tint, mirror and wind phase.

Communities (from the terrain's materials and zones): open meadow, forest edge, shade under the
canopies, wet ground by the water, the trodden edge of paths, the barrier's lusher ground (sanctum)
and its mossy heart under the great tree and round the shrine (oku), dry steep faces. Each community
weighs its species; inside it every species has its own noise field, and the strongest species
(weight x its noise x a random draw) wins a spot, so species form patches that interpenetrate along
their edges instead of meeting in lines. Tile variants (two or three sizes per species, mirrored at
random) and a per-clump hue/value jitter keep neighbours from repeating; the same tile never stands
twice within 0.45 m.

Output: cover.png (the atlas, RGBA: albedo + coverage; terrain/common) and cover.bin (per 16 m chunk,
two layers: 'low' casts no shadow, 'tall' does), in the renderer's foliage card layout (toon_foliage
card mode: CUSTOM0 = anchor + flex, UV2 = corner offset in native px, UV = atlas uv, COLOR = tint +
AO, NORMAL = light normal). Cards stand on the ground at their root (bottom-anchored), material lean 0.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from . import geom, noise

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "world3d_assets"))
from w3a import flora as FL  # noqa: E402
from w3a import leaves as LV  # noqa: E402

CHUNK = 16.0
STEP = 0.2                 # candidate spacing (m)
PPM = 30.0

# species: (painter, [kwargs per tile variant], layer)
SPECIES = {
    "short": (FL.tuft, [dict(W=8, H=6, family="grass", tall=0.9), dict(W=10, H=7, family="grass"), dict(W=12, H=8, family="grass", spread=0.7)], "low"),
    "mid": (FL.tuft, [dict(W=12, H=10, family="grass"), dict(W=14, H=12, family="grass", spread=0.6), dict(W=16, H=12, family="grass_blue")], "low"),
    "long": (FL.tuft, [dict(W=16, H=18, family="grass", arch=1.2), dict(W=18, H=22, family="grass_olive", arch=1.3)], "tall"),
    "blue": (FL.tuft, [dict(W=10, H=8, family="grass_blue"), dict(W=14, H=12, family="grass_blue", spread=0.65)], "low"),
    "yellow": (FL.tuft, [dict(W=10, H=8, family="grass_yellow"), dict(W=12, H=10, family="grass_yellow", spread=0.7)], "low"),
    "dry": (FL.tuft, [dict(W=12, H=11, family="grass_olive"), dict(W=16, H=14, family="grass_olive", arch=1.1)], "low"),
    "sedge": (FL.sedge, [dict(W=12, H=14), dict(W=10, H=12, family="grass_blue")], "low"),
    "fern": (FL.fern, [dict(W=16, H=12), dict(W=20, H=14), dict(W=24, H=17, fronds=8)], "tall"),
    "clover": (FL.clover, [dict(W=12, H=6), dict(W=14, H=7, flowers=1), dict(W=10, H=6, flowers=2)], "low"),
    "moss": (FL.moss_cushion, [dict(W=12, H=5), dict(W=16, H=6), dict(W=9, H=4)], "low"),
    "horsetail": (FL.horsetail, [dict(W=8, H=14), dict(W=10, H=16)], "low"),
    "plantain": (FL.plantain, [dict(W=14, H=7), dict(W=16, H=8)], "low"),
    "sasa": (FL.sasa, [dict(W=18, H=14), dict(W=22, H=16)], "tall"),
    "susuki": (FL.susuki, [dict(W=22, H=40), dict(W=26, H=44)], "tall"),
    "kikyo": (FL.flower_stems, [dict(W=12, H=18, kind="kikyo"), dict(W=14, H=20, kind="kikyo")], "low"),
    "ominaeshi": (FL.flower_stems, [dict(W=12, H=24, kind="ominaeshi"), dict(W=14, H=26, kind="ominaeshi")], "tall"),
    "hagi": (FL.flower_stems, [dict(W=18, H=20, kind="hagi"), dict(W=22, H=22, kind="hagi")], "tall"),
    "nadeshiko": (FL.flower_stems, [dict(W=10, H=12, kind="nadeshiko"), dict(W=12, H=14, kind="nadeshiko")], "low"),
    "tsuyukusa": (FL.flower_stems, [dict(W=10, H=10, kind="tsuyukusa", leaves="grass_blue"), dict(W=12, H=11, kind="tsuyukusa")], "low"),
    "tanpopo": (FL.flower_stems, [dict(W=8, H=8, kind="tanpopo"), dict(W=10, H=9, kind="tanpopo")], "low"),
}

# communities: species -> weight
COMMUNITIES = {
    "meadow": {"short": 1.0, "mid": 1.2, "long": 0.45, "blue": 0.5, "yellow": 0.35, "clover": 0.35, "plantain": 0.12, "kikyo": 0.09,
               "ominaeshi": 0.07, "nadeshiko": 0.07, "tanpopo": 0.06, "susuki": 0.08, "hagi": 0.05},
    "edge": {"mid": 0.8, "long": 0.8, "fern": 0.6, "sasa": 0.35, "hagi": 0.18, "tsuyukusa": 0.15, "susuki": 0.18, "blue": 0.4, "kikyo": 0.05},
    "shade": {"fern": 1.0, "moss": 0.8, "sasa": 0.45, "blue": 0.35, "tsuyukusa": 0.2, "sedge": 0.2, "short": 0.25},
    "wet": {"sedge": 1.0, "horsetail": 0.55, "fern": 0.5, "moss": 0.5, "tsuyukusa": 0.3, "blue": 0.35},
    "trodden": {"plantain": 1.0, "clover": 0.9, "short": 0.8, "tanpopo": 0.2},
    "sanctum": {"mid": 0.7, "blue": 0.6, "short": 0.5, "clover": 0.4, "moss": 0.5, "fern": 0.5, "kikyo": 0.22, "nadeshiko": 0.18,
                "tsuyukusa": 0.22, "ominaeshi": 0.08, "hagi": 0.08},
    "oku": {"moss": 1.2, "fern": 0.9, "sasa": 0.25, "tsuyukusa": 0.25, "blue": 0.3, "sedge": 0.15},
    "dry": {"dry": 1.0, "susuki": 0.4, "yellow": 0.4, "ominaeshi": 0.12, "hagi": 0.08, "short": 0.3},
}


def make_atlas(seed=5100):
    tiles = []
    table = {}
    for name, (fn, variants, layer) in SPECIES.items():
        table[name] = []
        for i, kw in enumerate(variants):
            t = LV.trim(fn(seed=seed + len(tiles) * 7 + i, **kw))
            table[name].append(len(tiles))
            tiles.append(t)
    atlas, rects = LV.pack_tiles(tiles, width=256, max_h=256)
    return atlas, rects, table, tiles


def build(L, W, F, Xs, Zs, Hs, cs, h, x0, z0, cell, seed, out_common: Path):
    """W: material weights on the splat grid; F: feature fields on the splat grid."""
    R = np.random.default_rng(seed + 5101)
    atlas, rects, table, tiles = make_atlas(seed + 5100)
    out_common.mkdir(parents=True, exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(out_common / "cover.png")
    imp = out_common / "cover.png.import"
    if not imp.exists():
        imp.write_text('[remap]\n\nimporter="image"\ntype="Image"\n')
    AH, AW = atlas.shape[:2]

    # ---- candidates on a jittered grid
    xs = np.arange(Xs[0, 0] + STEP / 2, Xs[0, -1], STEP)
    zs = np.arange(Zs[0, 0] + STEP / 2, Zs[-1, 0], STEP)
    CX, CZ = np.meshgrid(xs, zs)
    CX = (CX + R.uniform(-0.45, 0.45, CX.shape) * STEP).ravel()
    CZ = (CZ + R.uniform(-0.45, 0.45, CZ.shape) * STEP).ravel()
    si = np.clip(((CX - Xs[0, 0]) / cs).astype(int), 0, Xs.shape[1] - 1)
    sj = np.clip(((CZ - Zs[0, 0]) / cs).astype(int), 0, Xs.shape[0] - 1)

    def S(a):
        return np.asarray(a)[sj, si] if np.ndim(a) == 2 else np.full(len(CX), float(a))
    grass = S(W["grass"])
    moss = S(W["moss"])
    litter = S(W["litter"])
    rock = S(W["rock"])
    dirt = S(W["dirt"])
    gravel = S(W["gravel"])
    bank = S(W["bank"])
    paddy = S(W["paddy"])
    canopy = S(F["canopy"])
    water_d = S(F["water_d"])
    sanct = S(F.get("sanctum", 0.0))
    oku = S(F.get("oku", 0.0))
    trail = S(F.get("trail_k", 0.0))
    pave = S(F.get("pave_k", 0.0))
    stone = S(F.get("stone_k", 0.0))
    yard = S(geom.smoothstep(0.4, -0.2, F["yard_sdf"]))
    gz, gx = np.gradient(Hs, cs)
    slope = S(np.degrees(np.arctan(np.hypot(gx, gz))))
    south = S(np.clip(-gz / np.sqrt(1 + gx * gx + gz * gz) * 2.5, 0, 1))      # ground falling to the south (sun-facing)

    # ---- where plants can grow at all (not on paths, rock, water, yards, paved strips)
    ground_ok = (dirt < 0.5) & (rock < 0.5) & (gravel < 0.6) & (paddy < 0.5) & (pave < 0.2) & (yard < 0.4) & (water_d > 0.35)
    near_trail = geom.smoothstep(0.0, 0.5, trail) * (1 - geom.smoothstep(0.75, 1.0, trail))       # the trodden fringe

    # ---- community weights per candidate
    n_lo = noise.fbm(CX / 9.0, CZ / 9.0, 3, seed + 5110)
    shade_k = geom.smoothstep(0.25, 0.65, canopy + litter * 0.4)
    wet_k = geom.smoothstep(3.5, 1.0, water_d)
    dry_k = geom.smoothstep(22.0, 32.0, slope) * south * (1 - shade_k) * (1 - sanct)
    edge_k = geom.smoothstep(0.08, 0.3, canopy) * (1 - geom.smoothstep(0.45, 0.75, canopy))
    comm = {
        "meadow": (1 - shade_k) * (1 - wet_k) * (1 - dry_k) * (1 - sanct * 0.6) * (0.6 + 0.4 * n_lo),
        "edge": edge_k * (1 - wet_k) * 0.9,
        "shade": shade_k * (1 - oku) * (1 - wet_k * 0.5),
        "wet": wet_k,
        "trodden": near_trail * 1.4 + stone * 0.6,
        "sanctum": sanct * (1 - oku) * (1 - shade_k * 0.5) * (1 - wet_k) * 0.95,
        "oku": oku * 1.2,
        "dry": dry_k * 1.2,
    }
    # each species: weight from the communities, then its own clumping noise
    names = list(SPECIES)
    score = np.zeros((len(names), len(CX)))
    for si_, name in enumerate(names):
        w = np.zeros(len(CX))
        for cname, ck in comm.items():
            w = w + ck * COMMUNITIES[cname].get(name, 0.0)
        sc = 4.5 if name in ("short", "mid", "blue", "clover", "moss") else (3.0 if name in ("fern", "sasa", "long", "sedge") else 2.2)
        clump = noise.fbm(CX / sc + si_ * 13.1, CZ / sc - si_ * 7.7, 2, seed + 5200 + si_)
        score[si_] = w * (0.35 + 1.3 * geom.smoothstep(0.38, 0.72, clump)) * R.uniform(0.75, 1.25, len(CX))
    best = np.argmax(score, axis=0)
    best_s = score[best, np.arange(len(CX))]
    # density: the material's room for plants, clumps with bare ground between (negative space)
    mass = geom.smoothstep(0.42, 0.62, noise.fbm(CX / 2.6, CZ / 2.6, 2, seed + 5120) + (noise.fbm(CX / 0.8, CZ / 0.8, 1, seed + 5121) - 0.5) * 0.25)
    room = np.clip(grass + moss * 0.9 + litter * 0.45 + bank * 0.35, 0, 1)
    dens = room * (0.04 + 0.96 * mass) * np.clip(best_s * 1.4, 0, 1.0)
    dens *= (1 - geom.smoothstep(0.55, 0.9, trail))
    dens = dens * (0.8 + 0.3 * sanct)
    keep = ground_ok & (R.uniform(size=len(CX)) < dens * 0.3)
    # flowers: their own patches, one species to a patch (spots of colour), in the meadows, at the
    # edges and thickest inside the barrier
    FLOWERS = ["kikyo", "ominaeshi", "nadeshiko", "tsuyukusa", "hagi", "tanpopo"]
    fpatch = geom.smoothstep(0.6, 0.78, noise.fbm(CX / 3.2, CZ / 3.2, 2, seed + 5130))
    fkind = (noise.fbm(CX / 7.0, CZ / 7.0, 2, seed + 5131) * len(FLOWERS) * 1.6).astype(int) % len(FLOWERS)
    fk = fpatch * (comm["meadow"] * 0.7 + comm["edge"] * 0.5 + comm["sanctum"] * 1.3 + comm["dry"] * 0.4) * room
    flower = ground_ok & ~keep & (R.uniform(size=len(CX)) < fk * 0.28)
    for i in np.nonzero(flower)[0]:
        sp = FLOWERS[fkind[i]]
        if sp == "tsuyukusa" and shade_k[i] < 0.2 and wet_k[i] < 0.2 and R.uniform() < 0.6:
            sp = "nadeshiko"
        best[i] = names.index(sp)
    idx = np.nonzero(keep | flower)[0]

    # ---- choose tiles, avoid the same tile within 0.45 m, build cards
    cellsz = 0.45
    seen = {}
    cards = {"low": {}, "tall": {}}
    counts = {}
    hx = lambda x, z: (int(math.floor(x / cellsz)), int(math.floor(z / cellsz)))
    order = idx[np.argsort(CZ[idx])]
    for i in order:
        x, z = float(CX[i]), float(CZ[i])
        name = names[best[i]]
        opts = table[name]
        t = opts[int(R.integers(0, len(opts)))]
        key = hx(x, z)
        clash = False
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (ox, oz, ot) in seen.get((key[0] + dx, key[1] + dz), ()):
                    if ot == t and (ox - x) ** 2 + (oz - z) ** 2 < cellsz * cellsz:
                        clash = True
        if clash:
            alt = [o for o in opts if o != t]
            if not alt:
                continue
            t = alt[int(R.integers(0, len(alt)))]
        seen.setdefault(key, []).append((x, z, t))
        layer = SPECIES[name][2]
        y = float(_height(h, x0, z0, cell, x, z))
        nrm = _normal(h, x0, z0, cell, x, z)
        rx, ry, rw, rh = rects[t]
        mirror = R.uniform() < 0.5
        # per-clump tint: a hue nudge (more green / more yellow / more blue) and a value jitter
        hue = R.normal(0, 1)
        val = 1.0 + R.normal(0, 0.06)
        tint = np.array([1.0 + 0.035 * hue, 1.0, 1.0 - 0.04 * hue]) * val
        if name in ("kikyo", "ominaeshi", "hagi", "nadeshiko", "tsuyukusa", "tanpopo"):
            tint = np.array([1.0, 1.0, 1.0]) * (1.0 + R.normal(0, 0.03))
        ao = float(np.clip(1.0 - 0.35 * float(canopy[i]) - 0.15 * float(shade_k[i]), 0.55, 1.0))
        flex = float(np.clip(0.35 + rh / 30.0 + R.normal(0, 0.1), 0.2, 1.0))
        ln = nrm + np.array([0.0, 0.35, 0.45])
        ln /= np.linalg.norm(ln)
        ck = (int(math.floor(x / CHUNK)), int(math.floor(z / CHUNK)))
        cards[layer].setdefault(ck, []).append((x, y, z, rx, ry, rw, rh, mirror, np.clip(tint, 0, 1.2), ao, flex, ln))
        counts[name] = counts.get(name, 0) + 1
    return cards, counts, (AW, AH)


def _height(h, x0, z0, cell, x, z):
    fx = (x - x0) / cell
    fz = (z - z0) / cell
    i = int(min(max(math.floor(fx), 0), h.shape[1] - 2))
    j = int(min(max(math.floor(fz), 0), h.shape[0] - 2))
    tx, tz = min(max(fx - i, 0), 1), min(max(fz - j, 0), 1)
    return (h[j, i] * (1 - tx) + h[j, i + 1] * tx) * (1 - tz) + (h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx) * tz


def _normal(h, x0, z0, cell, x, z, e=0.4):
    dx = (_height(h, x0, z0, cell, x + e, z) - _height(h, x0, z0, cell, x - e, z)) / (2 * e)
    dz = (_height(h, x0, z0, cell, x, z + e) - _height(h, x0, z0, cell, x, z - e)) / (2 * e)
    n = np.array([-dx, 1.0, -dz])
    return n / np.linalg.norm(n)


def write(cards, atlas_size, out: Path):
    """cover.bin: per chunk and layer, vertex arrays in the foliage card layout; returns the json part."""
    AW, AH = atlas_size
    blob = bytearray()
    chunks = []
    for layer in ("low", "tall"):
        for ck, lst in sorted(cards[layer].items()):
            n = len(lst)
            P = np.zeros((n * 4, 3), np.float32)
            N = np.zeros((n * 4, 3), np.float32)
            UV = np.zeros((n * 4, 2), np.float32)
            UV2 = np.zeros((n * 4, 2), np.float32)
            C = np.zeros((n * 4, 4), np.float32)
            C0 = np.zeros((n * 4, 4), np.float32)
            I = np.zeros((n * 2, 3), np.uint32)
            for k, (x, y, z, rx, ry, rw, rh, mirror, tint, ao, flex, ln) in enumerate(lst):
                b = k * 4
                hw = rw // 2
                # bottom-anchored: the root row one pixel into the ground
                off = np.array([[-hw, -1], [rw - hw, -1], [rw - hw, rh - 1], [-hw, rh - 1]], np.float32)
                u0, u1 = (rx + rw, rx) if mirror else (rx, rx + rw)
                uvs = np.array([[u0, ry + rh], [u1, ry + rh], [u1, ry], [u0, ry]], np.float32) / np.array([AW, AH], np.float32)
                UV[b:b + 4] = uvs
                UV2[b:b + 4] = off
                # bounds: the anchor plus the card's extent on the camera plane (rough)
                up = np.array([0.0, 0.819, -0.574])
                P[b:b + 4] = np.array([x, y, z]) + off[:, :1] / PPM * np.array([1.0, 0.0, 0.0]) + off[:, 1:] / PPM * up
                N[b:b + 4] = ln
                C[b:b + 4, :3] = tint
                C[b:b + 4, 3] = ao
                C0[b:b + 4, :3] = (x, y, z)
                C0[b:b + 4, 3] = flex
                # front-facing on screen (Godot: clockwise); BL, BR, TR is counter-clockwise with y up
                I[k * 2] = (b, b + 2, b + 1)
                I[k * 2 + 1] = (b, b + 3, b + 2)
            e = {"chunk": [ck[0], ck[1]], "layer": layer, "offset": len(blob), "vertices": int(n * 4), "triangles": int(n * 2),
                 "aabb": [[round(float(v), 3) for v in P.min(axis=0)], [round(float(v), 3) for v in (P.max(axis=0) - P.min(axis=0))]]}
            for arr in (P, N, UV, UV2, C, C0, I):
                blob += np.ascontiguousarray(arr).tobytes()
            chunks.append(e)
    (out / "cover.bin").write_bytes(bytes(blob))
    return {"file": "cover.bin", "atlas": "res://world3d/terrain/common/cover.png",
            "layout": "per chunk: pos f32x3, normal f32x3, uv f32x2, uv2 f32x2 (px offset), colour f32x4 (tint + AO), custom0 f32x4 "
                      "(anchor + flex), index u32x3", "chunks": chunks}
