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
    rock = geom.smoothstep(37.0, 47.0, slope + (n1 - 0.5) * 8.0)
    rock = np.maximum(rock, F["spur_rock"] * geom.smoothstep(24.0, 34.0, slope + (n1 - 0.5) * 10))
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

    # --- worn dirt: the road, the footpaths, the yard; grass creeps in at ragged edges
    edge_n = (n1 - 0.5) * 0.7 + (n2 - 0.5) * 0.4
    road = geom.smoothstep(0.55 + edge_n * 0.6, -0.1, F["road_d"] - F["road_hw"])
    paths = np.zeros_like(Hs)
    for d, hw in F["paths"]:
        paths = np.maximum(paths, geom.smoothstep(0.35 + edge_n * 0.5, -0.15, d - hw * (0.75 + 0.35 * n2)))
    yard = geom.smoothstep(0.6 + edge_n, -0.3, F["yard_sdf"]) * (0.55 + 0.45 * geom.smoothstep(0.35, 0.65, n2))
    dirt = np.maximum(np.maximum(road, paths), yard)
    W["dirt"] = dirt * (1.0 - rock * 0.8)

    # --- gravel: the shrine terrace and its steps, the dosojin, the stream bed, outer bends
    gravel = np.maximum(F["shrine_sdf_k"], F["dosojin_k"])
    gravel = np.maximum(gravel, F["stream_bed"] * 0.9)
    gravel = np.maximum(gravel, F["graves_k"] * geom.smoothstep(0.3, 0.6, n1))
    gravel = np.maximum(gravel, road * F["road_outer"] * geom.smoothstep(0.45, 0.6, n1))
    W["gravel"] = gravel * (1.0 - rock * 0.7)

    # --- moss: wet and shaded ground
    wet = geom.smoothstep(5.0, 0.8, F["water_d"])
    moss = np.maximum(wet * (0.55 + 0.45 * n2), faces_north * geom.smoothstep(0.42, 0.62, n2) * 0.8)
    moss = np.maximum(moss, F["cedar"] * geom.smoothstep(0.42, 0.6, n2) * 0.75)
    moss = np.maximum(moss, F["graves_k"] * geom.smoothstep(0.55, 0.7, n2))
    moss = np.maximum(moss, rock * faces_north * geom.smoothstep(0.5, 0.65, n1) * 0.7)
    moss = np.maximum(moss, F["camphor_roots"] * geom.smoothstep(0.45, 0.62, n2) * 0.6)
    W["moss"] = moss * (1.0 - dirt * 0.85) * (1.0 - W["gravel"] * 0.6)

    # --- leaf litter under the canopies (camphor leaves, cedar needles, bamboo leaves)
    canopy = F["canopy"]
    litter = geom.smoothstep(0.45, 0.95, canopy + (n1 - 0.5) * 0.6 + (n2 - 0.5) * 0.35)
    W["litter"] = 0.85 * litter * (1.0 - dirt * 0.5) * (1.0 - rock * 0.8) * (1.0 - W["moss"] * 0.4)

    W["paddy"] = F["paddy"]

    # --- grass: whatever is left, and it is everywhere else
    other = np.maximum.reduce([W[k] for k in ORDER if k != "grass"])
    W["grass"] = np.clip(1.0 - other, 0.0, 1.0) * (1.0 - F["water_core"])

    # normalise
    S = sum(W[k] for k in ORDER) + 1e-6
    for k in ORDER:
        W[k] = W[k] / S

    # --- extras
    hb = ndimage.gaussian_filter(Hs, 4.0 / cell_s)
    concave = np.clip((hb - Hs) * 0.9, 0.0, 0.45)
    ao = 1.0 - concave - 0.25 * F["trunk_k"]
    ao = np.clip(ao, 0.45, 1.0)
    hb2 = ndimage.gaussian_filter(Hs, 1.2 / cell_s)
    puddle = geom.smoothstep(0.015, 0.06, hb2 - Hs) * np.maximum(W["dirt"], W["gravel"]) * geom.smoothstep(12.0, 6.0, slope)
    puddle = np.maximum(puddle, F["paddy"] * 0.0)
    wear = np.maximum(F["road_wear"], F["path_wear"]) * np.maximum(W["dirt"], 0.0)
    open_meadow = W["grass"] * (1.0 - geom.smoothstep(0.1, 0.4, canopy)) * geom.smoothstep(26.0, 14.0, slope)
    flowers = open_meadow * geom.smoothstep(0.5, 0.75, noise.fbm(Xs / 5.5, Zs / 5.5, 3, seed + 105))
    litter_kind = F["litter_kind"]
    dryness = np.clip(geom.smoothstep(0.35, 0.75, n3) * 0.7 + (1.0 - faces_north) * 0.15 - wet * 0.5 + geom.smoothstep(18, 30, slope) * 0.2, 0, 1)
    tufts = W["grass"] * (0.35 + 0.65 * geom.smoothstep(0.3, 0.7, n2)) * (1.0 - geom.smoothstep(0.3, 0.7, canopy) * 0.6)
    tufts *= 1.0 - np.maximum(road, paths) * 0.9

    m0 = np.stack([W["grass"], W["dirt"], W["gravel"], W["rock"]], -1)
    m1 = np.stack([W["moss"], W["litter"], W["bank"], W["paddy"]], -1)
    m2 = np.stack([ao, puddle, wear, flowers], -1)
    m3 = np.stack([litter_kind, dryness, tufts, np.clip(canopy, 0.0, 1.0)], -1)
    return {"m0": m0, "m1": m1, "m2": m2, "m3": m3, "slope": slope, "W": W}
