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

Round 4b (lead, 12:45: "the shrubs on the right read as noise by day"): the cover is laid out in
clumps with bare ground between them (成団、留白), not as single sprites strewn evenly. A clump is
one species (a few companions at its rim), 3-18 cards on a disc 0.2-0.9 m across, the tall tiles in
its middle and the short ones at the rim; its light normals bulge out of the clump (the top catches
the light, the rim turns away), its front and low cards are a little darker and bluer, and its tint
jitter is per clump, not per card. The tiles' own contrast is compressed (vegetation reads below
characters and interactables: knowledge/25). Weeds grow where people do not tread: along the feet of
walls and fences, around posts, troughs and stones (the layout's yard.weeds lines and rings, and every
walled pad's edge).

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
    # the feet of walls, fences and posts in the yard: what survives where nobody treads
    "wallfoot": {"short": 1.0, "plantain": 0.75, "clover": 0.55, "horsetail": 0.5, "tsuyukusa": 0.5, "mid": 0.4, "fern": 0.25,
                 "moss": 0.3, "tanpopo": 0.2, "nadeshiko": 0.08},
}

# clump size (radius range, m) per species: big plants make big clumps
CLUMP_R = {"fern": (0.35, 0.8), "sasa": (0.45, 0.95), "susuki": (0.3, 0.6), "long": (0.3, 0.7), "moss": (0.18, 0.45),
           "clover": (0.2, 0.5), "plantain": (0.15, 0.35), "horsetail": (0.15, 0.35)}
CLUMP_R_DEFAULT = (0.22, 0.6)
CARDS_PER_M2 = {"fern": 7.0, "sasa": 8.0, "susuki": 5.0, "long": 9.0, "moss": 12.0}
CARDS_PER_M2_DEFAULT = 13.0


calm = LV.calm


FLOWER_SPECIES = ("kikyo", "ominaeshi", "hagi", "nadeshiko", "tsuyukusa", "tanpopo")


def make_atlas(seed=5100):
    tiles = []
    table = {}
    for name, (fn, variants, layer) in SPECIES.items():
        table[name] = []
        for i, kw in enumerate(variants):
            t = LV.trim(fn(seed=seed + len(tiles) * 7 + i, **kw))
            # the flowers keep their colour (small spots of it are the point), the greens calm down
            t = calm(t, 0.82, 0.97) if name in FLOWER_SPECIES else calm(t)
            table[name].append(len(tiles))
            tiles.append(t)
    atlas, rects = LV.pack_tiles(tiles, width=256, max_h=256)
    return atlas, rects, table, tiles


def _sunflower(n, R):
    """n points on the unit disc, evenly spread (golden angle), jittered a little; centre first."""
    k = np.arange(n) + 0.5
    r = np.sqrt(k / n)
    a = k * 2.399963 + R.uniform(0, 2 * math.pi)
    pts = np.stack([np.cos(a) * r, np.sin(a) * r], 1)
    return pts + R.normal(0, 0.07, pts.shape)


def edge_lines(L, F, Xs, Zs, cs):
    """Where weeds grow along things people built: every walled pad's inner edge (the foot of its
    walls), and the layout's yard.weeds lines and rings (fences, house walls, posts, troughs)."""
    from skimage import measure
    out = []          # (points (n, 2), band width (m), density 0..1)
    for p in L.get("pads", []):
        if not p.get("wall"):
            continue
        key = "pad_sdf_" + p["id"]
        if key not in F:
            continue
        for c in measure.find_contours(F[key], -0.22):
            if len(c) < 4:
                continue
            pts = np.stack([Xs[0, 0] + c[:, 1] * cs, Zs[0, 0] + c[:, 0] * cs], -1)
            out.append((pts, 0.22, 0.85))
    Y = L.get("yard", {})
    for ln in Y.get("weeds", []):
        out.append((np.asarray(ln["pts"], np.float64), float(ln.get("w", 0.25)), float(ln.get("density", 0.8))))
    for rg in Y.get("rings", []):
        c = np.asarray(rg["c"], np.float64)
        r = float(rg.get("r", 0.4))
        a = np.linspace(0, 2 * math.pi, max(8, int(2 * math.pi * r / 0.15)))
        out.append((np.stack([c[0] + np.cos(a) * r, c[1] + np.sin(a) * r], 1), float(rg.get("w", 0.16)), float(rg.get("density", 0.9))))
    return out


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
    names = list(SPECIES)
    gz, gx = np.gradient(Hs, cs)
    slope_g = np.degrees(np.arctan(np.hypot(gx, gz)))
    south_g = np.clip(-gz / np.sqrt(1 + gx * gx + gz * gz) * 2.5, 0, 1)
    yard_g = geom.smoothstep(0.4, -0.2, F["yard_sdf"])
    zero = np.zeros_like(Hs)

    def sampler(CX, CZ):
        si = np.clip(((CX - Xs[0, 0]) / cs).astype(int), 0, Xs.shape[1] - 1)
        sj = np.clip(((CZ - Zs[0, 0]) / cs).astype(int), 0, Xs.shape[0] - 1)
        return lambda a: np.asarray(a)[sj, si] if np.ndim(a) == 2 else np.full(len(CX), float(a))

    def fields(CX, CZ):
        S = sampler(CX, CZ)
        d = dict(grass=S(W["grass"]), moss=S(W["moss"]), litter=S(W["litter"]), rock=S(W["rock"]), dirt=S(W["dirt"]),
                 gravel=S(W["gravel"]), bank=S(W["bank"]), paddy=S(W["paddy"]), canopy=S(F["canopy"]), water_d=S(F["water_d"]),
                 sanct=S(F.get("sanctum", zero)), oku=S(F.get("oku", zero)), trail=S(F.get("trail_k", zero)),
                 pave=S(F.get("pave_k", zero)), stone=S(F.get("stone_k", zero)), yard=S(yard_g), slope=S(slope_g),
                 south=S(south_g), wear=S(F.get("yard_wear", zero)), drip=S(F.get("drip_k", zero)))
        d["ground_ok"] = ((d["dirt"] < 0.5) & (d["rock"] < 0.5) & (d["gravel"] < 0.6) & (d["paddy"] < 0.5) & (d["pave"] < 0.2)
                          & (d["yard"] < 0.4) & (d["water_d"] > 0.35))
        n_lo = noise.fbm(CX / 9.0, CZ / 9.0, 3, seed + 5110)
        shade_k = geom.smoothstep(0.25, 0.65, d["canopy"] + d["litter"] * 0.4)
        wet_k = geom.smoothstep(3.5, 1.0, d["water_d"])
        dry_k = geom.smoothstep(22.0, 32.0, d["slope"]) * d["south"] * (1 - shade_k) * (1 - d["sanct"])
        edge_k = geom.smoothstep(0.08, 0.3, d["canopy"]) * (1 - geom.smoothstep(0.45, 0.75, d["canopy"]))
        near_trail = geom.smoothstep(0.0, 0.5, d["trail"]) * (1 - geom.smoothstep(0.75, 1.0, d["trail"]))
        d["shade_k"], d["wet_k"] = shade_k, wet_k
        d["comm"] = {
            "meadow": (1 - shade_k) * (1 - wet_k) * (1 - dry_k) * (1 - d["sanct"] * 0.6) * (0.6 + 0.4 * n_lo),
            "edge": edge_k * (1 - wet_k) * 0.9,
            "shade": shade_k * (1 - d["oku"]) * (1 - wet_k * 0.5),
            "wet": wet_k,
            "trodden": near_trail * 1.4 + d["stone"] * 0.6,
            "sanctum": d["sanct"] * (1 - d["oku"]) * (1 - shade_k * 0.5) * (1 - wet_k) * 0.95,
            "oku": d["oku"] * 1.2,
            "dry": dry_k * 1.2,
            "wallfoot": np.zeros(len(CX)),
        }
        return d

    def species_scores(CX, CZ, comm, salt):
        score = np.zeros((len(names), len(CX)))
        for k, name in enumerate(names):
            w = np.zeros(len(CX))
            for cname, ck in comm.items():
                w = w + ck * COMMUNITIES[cname].get(name, 0.0)
            sc = 6.0 if name in ("short", "mid", "blue", "clover", "moss") else (4.0 if name in ("fern", "sasa", "long", "sedge") else 3.0)
            clump = noise.fbm(CX / sc + k * 13.1, CZ / sc - k * 7.7, 2, seed + 5200 + k)
            score[k] = w * (0.35 + 1.3 * geom.smoothstep(0.38, 0.72, clump)) * R.uniform(0.8, 1.2, len(CX))
        return score

    clumps = []        # (cx, cz, species index, radius, n cards, companion index or -1, kind)

    # ---- 1. plant clumps on a jittered lattice; big open areas between groups of clumps
    SP = 0.95
    xs = np.arange(Xs[0, 0] + SP / 2, Xs[0, -1], SP)
    zs = np.arange(Zs[0, 0] + SP / 2, Zs[-1, 0], SP)
    CX, CZ = np.meshgrid(xs, zs)
    CX = (CX + R.uniform(-0.42, 0.42, CX.shape) * SP).ravel()
    CZ = (CZ + R.uniform(-0.42, 0.42, CZ.shape) * SP).ravel()
    fd = fields(CX, CZ)
    score = species_scores(CX, CZ, fd["comm"], 0)
    order = np.argsort(-score, axis=0)
    best, second = order[0], order[1]
    best_s = score[best, np.arange(len(CX))]
    # groups of clumps with open ground between (the 3-6 m pattern), finer gaps inside a group
    mass = geom.smoothstep(0.4, 0.6, noise.fbm(CX / 3.4, CZ / 3.4, 2, seed + 5120) + (noise.fbm(CX / 1.1, CZ / 1.1, 1, seed + 5121) - 0.5) * 0.3)
    room = np.clip(fd["grass"] + fd["moss"] * 0.9 + fd["litter"] * 0.45 + fd["bank"] * 0.35, 0, 1)
    p_clump = room * (0.06 + 0.94 * mass) * np.clip(best_s * 1.4, 0, 1.0) * (1 - geom.smoothstep(0.55, 0.9, fd["trail"]))
    p_clump *= 0.62 * (0.85 + 0.25 * fd["sanct"])
    keep = fd["ground_ok"] & (R.uniform(size=len(CX)) < p_clump)
    for i in np.nonzero(keep)[0]:
        name = names[best[i]]
        r0, r1 = CLUMP_R.get(name, CLUMP_R_DEFAULT)
        r = R.uniform(r0, r1) * (0.75 + 0.5 * float(mass[i]))
        dens = CARDS_PER_M2.get(name, CARDS_PER_M2_DEFAULT)
        n = int(np.clip(round(math.pi * r * r * dens * R.uniform(0.8, 1.2)), 2, 18))
        comp = int(second[i]) if R.uniform() < 0.45 and score[second[i], i] > 0.25 * best_s[i] else -1
        clumps.append((float(CX[i]), float(CZ[i]), int(best[i]), r, n, comp, "plant"))

    # ---- 2. flowers: small clumps of one species, in patches (meadows, edges, thickest in the barrier)
    FLOWERS = list(FLOWER_SPECIES)
    SPf = 0.8
    xs = np.arange(Xs[0, 0] + SPf / 2, Xs[0, -1], SPf)
    zs = np.arange(Zs[0, 0] + SPf / 2, Zs[-1, 0], SPf)
    FX, FZ = np.meshgrid(xs, zs)
    FX = (FX + R.uniform(-0.45, 0.45, FX.shape) * SPf).ravel()
    FZ = (FZ + R.uniform(-0.45, 0.45, FZ.shape) * SPf).ravel()
    ff = fields(FX, FZ)
    fpatch = geom.smoothstep(0.58, 0.76, noise.fbm(FX / 3.2, FZ / 3.2, 2, seed + 5130))
    fkind = (noise.fbm(FX / 7.0, FZ / 7.0, 2, seed + 5131) * len(FLOWERS) * 1.6).astype(int) % len(FLOWERS)
    froom = np.clip(ff["grass"] + ff["moss"] * 0.9 + ff["litter"] * 0.45, 0, 1)
    fk = fpatch * (ff["comm"]["meadow"] * 0.7 + ff["comm"]["edge"] * 0.5 + ff["comm"]["sanctum"] * 1.3 + ff["comm"]["dry"] * 0.4) * froom
    for i in np.nonzero(ff["ground_ok"] & (R.uniform(size=len(FX)) < fk * 0.55))[0]:
        sp = FLOWERS[fkind[i]]
        if sp == "tsuyukusa" and ff["shade_k"][i] < 0.2 and ff["wet_k"][i] < 0.2 and R.uniform() < 0.6:
            sp = "nadeshiko"
        r = R.uniform(0.14, 0.34)
        clumps.append((float(FX[i]), float(FZ[i]), names.index(sp), r, int(R.integers(2, 6)), names.index("short") if R.uniform() < 0.5 else -1,
                       "flower"))

    # ---- 3. weeds at the feet of walls, fences, posts and troughs (in the yard too)
    lines = edge_lines(L, F, Xs, Zs, cs)
    wcomm = dict(COMMUNITIES["wallfoot"])
    for pts, band, dens in lines:
        seg = np.diff(pts, axis=0)
        sl = np.hypot(seg[:, 0], seg[:, 1])
        tot = float(sl.sum())
        if tot < 0.2:
            continue
        cum = np.concatenate([[0.0], np.cumsum(sl)])
        s_ = R.uniform(0, 0.4)
        while s_ < tot:
            k = min(int(np.searchsorted(cum, s_, side="right")) - 1, len(seg) - 1)
            t = (s_ - cum[k]) / max(sl[k], 1e-6)
            q = pts[k] + seg[k] * t
            nrm = np.array([-seg[k][1], seg[k][0]]) / max(sl[k], 1e-6)
            c = q + nrm * R.normal(0, band * 0.5)
            # clumps along the line with gaps between: a patchy band, not a hedge
            patch = float(noise.fbm(np.array([c[0] / 1.6]), np.array([c[1] / 1.6]), 2, seed + 5140)[0])
            if R.uniform() < dens * geom.smoothstep(0.36, 0.6, patch):
                fx = fields(np.array([c[0]]), np.array([c[1]]))
                if fx["rock"][0] < 0.5 and fx["water_d"][0] > 0.3 and fx["wear"][0] < 0.3 and fx["pave"][0] < 0.3:
                    ws = np.array([wcomm.get(nm, 0.0) for nm in names]) * R.uniform(0.6, 1.4, len(names))
                    if fx["shade_k"][0] > 0.4:
                        ws[names.index("fern")] *= 3.0
                        ws[names.index("moss")] *= 2.5
                    bi = int(np.argmax(ws))
                    r = R.uniform(0.12, 0.3)
                    clumps.append((float(c[0]), float(c[1]), bi, r, int(R.integers(2, 6)), int(np.argsort(-ws)[1]) if R.uniform() < 0.5 else -1,
                                   "weed"))
            s_ += R.uniform(0.25, 0.55)

    # ---- 4. cards
    cellsz = 0.45
    seen = {}
    cards = {"low": {}, "tall": {}}
    counts = {}
    hx = lambda x, z: (int(math.floor(x / cellsz)), int(math.floor(z / cellsz)))
    clumps.sort(key=lambda c: c[1])
    up = np.array([0.0, 1.0, 0.0])
    for (cx, cz, si, r, n, comp, kind) in clumps:
        pts = _sunflower(n, R) * r * np.array([1.0, 0.8])
        CXc = cx + pts[:, 0]
        CZc = cz + pts[:, 1]
        fc = fields(CXc, CZc)
        ok = fc["ground_ok"] if kind != "weed" else ((fc["rock"] < 0.5) & (fc["water_d"] > 0.3) & (fc["wear"] < 0.35)
                                                       & (fc["pave"] < 0.3) & (fc["gravel"] < 0.7))
        hue = R.normal(0, 1)                                   # one hue nudge and one value per clump
        val = 1.0 + R.normal(0, 0.04)
        for j in np.argsort(CZc):
            if not ok[j]:
                continue
            x, z = float(CXc[j]), float(CZc[j])
            rr = float(np.hypot(pts[j, 0], pts[j, 1] / 0.8)) / max(r, 1e-6)       # 0 centre .. 1 rim
            name = names[comp] if (comp >= 0 and rr > 0.55 and R.uniform() < 0.5) else names[si]
            opts = table[name]
            # tall variants in the middle of the clump, short ones at the rim
            by_h = sorted(opts, key=lambda t: rects[t][3])
            pick = by_h[min(len(by_h) - 1, int((1.0 - rr) * len(by_h) + R.uniform(-0.6, 0.6)))] if len(by_h) > 1 else by_h[0]
            t = pick
            key = hx(x, z)
            clash = False
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for (ox, oz, ot) in seen.get((key[0] + dx, key[1] + dz), ()):
                        if ot == t and (ox - x) ** 2 + (oz - z) ** 2 < (cellsz * 0.6) ** 2:
                            clash = True
            if clash:
                alt = [o for o in opts if o != t]
                if alt:
                    t = alt[int(R.integers(0, len(alt)))]
            seen.setdefault(key, []).append((x, z, t))
            layer = SPECIES[name][2]
            y = float(_height(h, x0, z0, cell, x, z))
            nrm = _normal(h, x0, z0, cell, x, z)
            rx, ry, rw, rh = rects[t]
            mirror = R.uniform() < 0.5
            # light: the clump bulges, its top catches the light and its rim turns away
            out = np.array([pts[j, 0], 0.0, pts[j, 1] / 0.8]) / max(r, 1e-6)
            ln = nrm * 0.55 + up * 0.55 + out * 0.35 + np.array([0.0, 0.0, 0.25])
            ln /= np.linalg.norm(ln)
            front = float(np.clip(out[2], 0, 1))
            if name in FLOWER_SPECIES:
                tint = np.array([1.0, 1.0, 1.0]) * (1.0 + R.normal(0, 0.025))
            else:
                v = val * (1.0 - 0.07 * rr - 0.05 * front) * (1.0 + R.normal(0, 0.015))
                # rim and front a little bluer (the shade side of the clump), the middle a little warmer
                tint = np.array([1.0 + 0.03 * hue - 0.03 * rr, 1.0, 1.0 - 0.035 * hue + 0.05 * rr]) * v
            ao = float(np.clip(1.0 - 0.32 * float(fc["canopy"][j]) - 0.14 * float(fc["shade_k"][j]) - 0.12 * rr, 0.5, 1.0))
            flex = float(np.clip(0.35 + rh / 30.0 + R.normal(0, 0.08), 0.2, 1.0))
            ck = (int(math.floor(x / CHUNK)), int(math.floor(z / CHUNK)))
            cards[layer].setdefault(ck, []).append((x, y, z, rx, ry, rw, rh, mirror, np.clip(tint, 0, 1.2), ao, flex, ln))
            counts[name] = counts.get(name, 0) + 1
    counts["_clumps"] = len(clumps)
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
    import gzip
    (out / "cover.bin").write_bytes(gzip.compress(bytes(blob), compresslevel=9, mtime=0))
    return {"file": "cover.bin", "compression": "gzip", "atlas": "res://world3d/terrain/common/cover.png",
            "layout": "per chunk: pos f32x3, normal f32x3, uv f32x2, uv2 f32x2 (px offset), colour f32x4 (tint + AO), custom0 f32x4 "
                      "(anchor + flex), index u32x3", "chunks": chunks}
