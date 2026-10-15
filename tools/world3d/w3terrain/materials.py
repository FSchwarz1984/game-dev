"""Material weights on the splat grid (0.25 m): grass, worn dirt, gravel, rock, moss, leaf litter,
bank earth, paddy; plus ambient occlusion, puddles, path wear, flowers, litter kind, grass dryness
and tuft density. The shader picks the dominant material per screen texel with a jittered lookup,
so these meet along ragged pixel-scale borders."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import geom, noise

ORDER = ["grass", "dirt", "gravel", "rock", "moss", "litter", "bank", "paddy"]


def compute(L, F, Xs, Zs, Hs, cell_s, placements):
    """F: feature fields sampled on the splat grid (dicts of arrays); Hs: heights on the splat grid."""
    seed = int(L["seed"])
    gz, gx = np.gradient(Hs, cell_s)
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    nrm_z = gz / np.sqrt(1 + gx * gx + gz * gz)      # > 0: the slope faces north? (height rises to the south)
    faces_north = np.clip(nrm_z * 2.5, 0.0, 1.0)     # ground rising to the south faces north (away from the camera)

    W = {k: np.zeros_like(Hs) for k in ORDER}
    n1 = noise.fbm(Xs / 2.3, Zs / 2.3, 3, seed + 101)
    n2 = noise.fbm(Xs / 6.0, Zs / 6.0, 3, seed + 102)
    n3 = noise.fbm(Xs / 15.0, Zs / 15.0, 3, seed + 103)

    # --- rock: steep ground, the spur, the ravine, the spring face; outcrops on rough slopes
    # (soil holds on slopes up to about 40 degrees here; bare rock only where it is steeper, or where
    # the spur's bedrock breaks through in patches, never as a continuous band)
    rock = geom.smoothstep(41.0, 50.0, slope + (n1 - 0.5) * 8.0)
    rock = np.maximum(rock, F["spur_rock"] * geom.smoothstep(30.0, 40.0, slope + (n1 - 0.5) * 10) * geom.smoothstep(0.45, 0.6, n2))
    rock = np.maximum(rock, F["lookout_top"])
    rock = np.maximum(rock, F["spring_face"])
    rough = noise.ridged(Xs / 11.0, Zs / 11.0, 3, seed + 104)
    rock = np.maximum(rock, geom.smoothstep(0.62, 0.72, rough) * geom.smoothstep(24.0, 32.0, slope))
    W["rock"] = rock

    # --- bank earth: steep but not rock, cut and fill banks of the road, terrace risers
    bank = geom.smoothstep(26.0, 34.0, slope + (n1 - 0.5) * 6.0) * (1.0 - rock)
    bank = np.maximum(bank, F["road_bank"] * geom.smoothstep(14.0, 24.0, slope) * (1.0 - rock))
    bank = np.maximum(bank, F["terrace_bank"])
    W["bank"] = bank

    # --- worn dirt: the trails and the earth stretches of the road, the yard. Crisp edges (round 4:
    # the soft noisy edge read as a band painted on the ground); only a low-frequency wobble along
    # the way and the shader's per-texel jitter break them
    sanct = F.get("sanctum", np.zeros_like(Hs))
    road = F["trail_k"]
    paths = np.zeros_like(Hs)
    yard = geom.smoothstep(0.22, -0.3, F["yard_sdf"] + (n1 - 0.5) * 0.4) * (0.78 + 0.22 * geom.smoothstep(0.35, 0.65, n2))
    dirt = np.maximum(road, yard)
    W["dirt"] = dirt * (1.0 - rock * 0.8)

    # --- gravel: the shrine terrace, the dosojin, the stream bed, the paved road's gutter
    gravel = np.maximum(F["shrine_sdf_k"] * 0.85, F["dosojin_k"])
    gravel = np.maximum(gravel, F["stream_bed"] * 0.9)
    gravel = np.maximum(gravel, F["graves_k"] * geom.smoothstep(0.3, 0.6, n1))
    gravel = np.maximum(gravel, F.get("gutter_k", 0.0) * 0.95)
    W["gravel"] = gravel * (1.0 - rock * 0.7)

    # --- moss: wet and shaded ground; in the joints of the paving and between stepping stones; and
    # inside the barrier (zones.sanctum) the moss is thick, around the great tree and the shrine (oku)
    # a carpet
    wet = geom.smoothstep(5.0, 0.8, F["water_d"])
    moss = np.maximum(wet * (0.55 + 0.45 * n2), faces_north * geom.smoothstep(0.42, 0.62, n2) * 0.8)
    moss = np.maximum(moss, F["cedar"] * geom.smoothstep(0.42, 0.6, n2) * 0.75)
    moss = np.maximum(moss, F["graves_k"] * geom.smoothstep(0.55, 0.7, n2))
    moss = np.maximum(moss, rock * faces_north * geom.smoothstep(0.5, 0.65, n1) * 0.7)
    moss = np.maximum(moss, F["camphor_roots"] * geom.smoothstep(0.38, 0.55, n2) * 0.8)
    moss = np.maximum(moss, sanct * geom.smoothstep(0.5, 0.66, n2 + (n1 - 0.5) * 0.3) * 0.75)
    moss = np.maximum(moss, F.get("oku", 0.0) * geom.smoothstep(0.3, 0.5, n2 + (n0x := noise.fbm(Xs / 1.6, Zs / 1.6, 2, seed + 109) - 0.5) * 0.4) * 0.9)
    moss = np.maximum(moss, F.get("pave_k", 0.0) * 0.95)
    moss = np.maximum(moss, F.get("stone_k", 0.0) * (0.55 + 0.4 * geom.smoothstep(0.4, 0.6, n1)))
    W["moss"] = moss * (1.0 - dirt * 0.85) * (1.0 - W["gravel"] * 0.6)

    # --- leaf litter under the canopies (camphor leaves, cedar needles, bamboo leaves)
    canopy = F["canopy"]
    n0 = noise.fbm(Xs / 0.9, Zs / 0.9, 2, seed + 100)
    litter = geom.smoothstep(0.42, 1.1, canopy + (n1 - 0.5) * 0.7 + (n0 - 0.5) * 0.45 + (n2 - 0.5) * 0.35)
    W["litter"] = 0.66 * litter * (1.0 - dirt * 0.5) * (1.0 - rock * 0.8) * (1.0 - W["moss"] * 0.45) * (1.0 - F.get("pave_k", 0.0))
    # under the canopy the grass thins and moss creeps in among the leaves
    W["moss"] = np.maximum(W["moss"], canopy * geom.smoothstep(0.5, 0.68, n1) * 0.55 * (1.0 - dirt))

    # the paddies, and the packed earth of the yard's trodden paths (same row of the palette: dark earth,
    # smooth, no pebbles: the feet pushed them aside)
    W["paddy"] = np.maximum(F["paddy"], F.get("yard_wear", 0.0) * 0.97)
    # the yard: gravel in the drip channels, leaves blown against the walls, scratched earth by the hens,
    # a little moss where the trough spills
    yard_in = geom.smoothstep(0.3, -0.2, F["yard_sdf"])
    W["gravel"] = np.maximum(W["gravel"], F.get("drip_k", 0.0) * 0.97)
    W["litter"] = np.maximum(W["litter"], F.get("drift_k", 0.0) * 1.0)
    W["bank"] = np.maximum(W["bank"], F.get("scratch_k", 0.0) * 0.9 * yard_in)
    feat = np.maximum.reduce([np.broadcast_to(np.asarray(F.get(k, 0.0), np.float64), Hs.shape)
                              for k in ("yard_wear", "drift_k", "drip_k")] + [F.get("scratch_k", np.zeros_like(Hs)) * yard_in])
    W["dirt"] = W["dirt"] * (1.0 - 0.8 * feat)

    # --- grass: whatever is left, and it is everywhere else
    other = np.maximum.reduce([W[k] for k in ORDER if k != "grass"])
    W["grass"] = np.clip(1.0 - other, 0.0, 1.0) * (1.0 - F["water_core"]) * (1.0 - F.get("pave_k", 0.0))

    # normalise
    S = sum(W[k] for k in ORDER) + 1e-6
    for k in ORDER:
        W[k] = W[k] / S

    # --- extras
    hb = ndimage.gaussian_filter(Hs, 4.0 / cell_s)
    concave = np.clip((hb - Hs) * 0.9, 0.0, 0.45)
    ao = 1.0 - concave - 0.25 * F["trunk_k"]
    # contact shadows: the ground darkens where rocks sit on it
    for p in placements:
        if p["kind"] not in ("outcrop", "boulder", "rock_slab"):
            continue
        r = 0.5 * max(float(p.get("sx", 1.0)), float(p.get("sz", 1.0))) if "sx" in p else 0.45 * float(p.get("scale", 1.0))
        cx, cz = p["x"], p["z"]
        i0 = max(int((cx - r - 1.5 - Xs[0, 0]) / cell_s), 0); i1 = min(int((cx + r + 1.5 - Xs[0, 0]) / cell_s) + 1, Hs.shape[1])
        j0 = max(int((cz - r - 1.5 - Zs[0, 0]) / cell_s), 0); j1 = min(int((cz + r + 1.5 - Zs[0, 0]) / cell_s) + 1, Hs.shape[0])
        if i1 <= i0 or j1 <= j0:
            continue
        d = np.hypot(Xs[j0:j1, i0:i1] - cx, Zs[j0:j1, i0:i1] - cz)
        ao[j0:j1, i0:i1] *= 1.0 - 0.42 * geom.smoothstep(r + 0.9, r * 0.7, d)
    ao = np.clip(ao, 0.45, 1.0)
    hb2 = ndimage.gaussian_filter(Hs, 1.2 / cell_s)
    puddle = geom.smoothstep(0.015, 0.06, hb2 - Hs) * np.maximum(W["dirt"], W["gravel"]) * geom.smoothstep(12.0, 6.0, slope)
    puddle = np.maximum(puddle, F["paddy"] * 0.0)
    wear = geom.smoothstep(0.3, 0.9, F["trail_k"]) * np.maximum(W["dirt"], 0.0) * (0.5 + 0.5 * n1)
    # the yard: swept a little in the open middle (fewer pebbles), pebbles gather toward the edges
    yard_mid = geom.smoothstep(-0.6, -2.4, F["yard_sdf"]) * geom.smoothstep(0.45, 0.6, n2)
    wear = np.maximum(wear, 0.3 * yard_mid * W["dirt"])
    open_meadow = W["grass"] * (1.0 - geom.smoothstep(0.1, 0.4, canopy)) * geom.smoothstep(26.0, 14.0, slope)
    flowers = open_meadow * geom.smoothstep(0.5 - 0.12 * sanct, 0.75 - 0.12 * sanct, noise.fbm(Xs / 5.5, Zs / 5.5, 3, seed + 105))
    litter_kind = F["litter_kind"]
    # dry grass only where the sun bakes a steep south face or the soil is thin by the rock; never a
    # broad yellow field (round 4: the "withered yellow" of round 3 came from here)
    dryness = np.clip(geom.smoothstep(0.58, 0.85, n3) * 0.45 + (1.0 - faces_north) * 0.08 - wet * 0.6
                      + geom.smoothstep(22, 34, slope) * 0.35 + rock * 0.3 - sanct * 0.7, 0, 1)
    tufts = W["grass"] * (0.35 + 0.65 * geom.smoothstep(0.3, 0.7, n2)) * (1.0 - geom.smoothstep(0.3, 0.7, canopy) * 0.6)
    tufts *= 1.0 - np.maximum(np.maximum(road, F.get("pave_k", 0.0)), F.get("stone_k", 0.0)) * 0.9

    m0 = np.stack([W["grass"], W["dirt"], W["gravel"], W["rock"]], -1)
    m1 = np.stack([W["moss"], W["litter"], W["bank"], W["paddy"]], -1)
    m2 = np.stack([ao, puddle, wear, flowers], -1)
    m3 = np.stack([litter_kind, dryness, tufts, np.clip(canopy, 0.0, 1.0)], -1)
    return {"m0": m0, "m1": m1, "m2": m2, "m3": m3, "slope": slope, "W": W}
