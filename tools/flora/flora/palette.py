"""Colour ramps for vegetation, dark -> light, built with the same hue-shifting ramp() as the game
palette (src/env/palette.js) so the plants sit with the rest of the art.

Readability (CLAUDE.md, art-direction): vegetation is the lowest layer of the read order. Its
values stay inside a narrower band than characters and interactables: the darkest foliage tone is
never black and the brightest highlight stays below the characters' lights (cream, skin, paper).
Late summer on a mountain pass: olive and moss greens, blue-green shadow, honey light.
"""
import numpy as np

from .core import ramp


def R(base, n, lo, hi, hs=0.06, ss=0.1):
    return ramp(base, n, lo=lo, hi=hi, hue_shift=hs, sat_shift=ss)


def blend(a, b, t):
    return np.clip(np.round(np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t), 0, 255).astype(np.uint8)


PAL = {
    # ---- broadleaf foliage, 6 tones: gap, shadow, mid-dark, mid, light, highlight
    'camphor': R('#557a38', 6, 0.62, 0.34, 0.08),
    'camphorNew': R('#76944a', 6, 0.55, 0.30, 0.07),
    'camphorDeep': R('#2f4d36', 6, 0.55, 0.45, 0.06),
    'beech': R('#5a803c', 6, 0.60, 0.34, 0.08),
    'maple': R('#5a833a', 6, 0.60, 0.34, 0.07),
    'mapleTurn': R('#b0633a', 6, 0.58, 0.40, 0.04, 0.05),
    'mapleRed': R('#a3392c', 6, 0.58, 0.40, 0.04, 0.0),
    'kaki': R('#3f6a33', 6, 0.60, 0.50, 0.07),
    'broad': R('#3f6634', 6, 0.58, 0.48, 0.07),
    'azalea': R('#456c35', 6, 0.58, 0.46, 0.07),
    'hydLeaf': R('#4b7838', 6, 0.58, 0.46, 0.07),
    # ---- conifers
    'cedar': R('#2f4f3d', 6, 0.66, 0.46, 0.08),
    'pine': R('#36573a', 6, 0.60, 0.52, 0.08),
    # ---- grasses and herbs
    'bambooLeaf': R('#55853d', 6, 0.55, 0.48, 0.07),
    'bamboo': R('#78a04f', 6, 0.55, 0.45, 0.06),
    'bambooOld': R('#a29c58', 5, 0.50, 0.40, 0.05),
    'fern': R('#4f7d39', 6, 0.58, 0.48, 0.07),
    'susuki': R('#8a985a', 6, 0.55, 0.42, 0.06),
    'susukiLeaf': R('#6a8646', 6, 0.58, 0.40, 0.07),
    'plume': R('#cfc3a6', 5, 0.40, 0.30, 0.04),
    'stem': R('#5f7f3c', 5, 0.50, 0.40, 0.06),
    # ---- flowers
    'higan': R('#c43a2c', 5, 0.50, 0.32, 0.03, 0.0),
    'tsuyu': R('#4f6fd0', 5, 0.45, 0.35, 0.03, 0.0),
    'omina': R('#d9b93a', 5, 0.45, 0.32, 0.03, 0.0),
    'hydBlue': R('#7486c4', 5, 0.45, 0.32, 0.04),
    'hydViolet': R('#9a82bd', 5, 0.45, 0.32, 0.04),
    'hydDusty': R('#a69aa8', 5, 0.42, 0.30, 0.04),
    'kakiFruit': R('#d9822e', 5, 0.45, 0.32, 0.03, 0.0),
    'kakiGreen': R('#9aa84a', 5, 0.45, 0.32, 0.04),
    # ---- bark and wood, 6 tones
    'barkCamphor': R('#6c6556', 6, 0.60, 0.40, 0.05),
    'barkCedar': R('#6e4532', 6, 0.58, 0.45, 0.04),
    'barkPine': R('#6a4a3a', 6, 0.58, 0.45, 0.04),
    'barkPineRed': R('#a35a3c', 6, 0.55, 0.40, 0.03),
    'barkGrey': R('#6f675d', 6, 0.60, 0.45, 0.05),
    'barkBeech': R('#8a8a80', 6, 0.55, 0.38, 0.05),
    'barkKaki': R('#4f453c', 6, 0.58, 0.42, 0.05),
    'moss': R('#55783a', 6, 0.55, 0.45, 0.06),
    'lichen': R('#a7a578', 5, 0.40, 0.30, 0.04),
    'soil': R('#6e523b', 6, 0.50, 0.45, 0.05),
    # ---- made things on the camphor
    'rope': R('#c2a868', 6, 0.50, 0.32, 0.04),
    'paper': R('#ece4d2', 5, 0.30, 0.18, 0.03),
}
