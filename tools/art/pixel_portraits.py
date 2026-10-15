"""Pixel-art dialogue portraits (busts) from the owner's illustration packs.

    python3 -I tools/art/pixel_portraits.py crops --packs DIR    # 1. cut the work crops (needs the extracted packs)
    python3 -I tools/art/pixel_portraits.py build                # 2. pixelate assets/portraits/src -> assets/portraits/pixel
    python3 -I tools/art/pixel_portraits.py sheets --out DIR     # before/after contact sheets at x4

Dependencies: numpy, Pillow, opencv-python-headless, scipy, scikit-image.

Input packs: 12 zips of 1024x1536 RGBA PNGs (transparent background), A_01..A_36 = Tsuzumi, B_01..B_36 = Shione,
C_01..C_36 = Saji, extracted as DIR/Character_<L>_<nn-nn>/<L>_<nn>.png (one directory per zip). The packs stay out
of the repo; `crops` keeps one 320x320 work crop per selected expression in assets/portraits/src/<char>/<expr>.webp
(lossy WebP, alpha lossless) and `build` reads only those, so the PNGs are reproducible from the repo.

Output: assets/portraits/pixel_v1/<char>/<expr>.png (v1, kept for reference; the current portraits are v4,
tools/art/portraits4), SIZE x SIZE (80 x 80) native pixels, binary alpha, every colour
from the character's palette below; portraits.json lists the expressions, the eye line and the palettes.

Method (notes and reasons: docs/knowledge/13-pixel-portraits.md):
 1. Crop. A square window, SIZE native px. Both eyes were measured on every source (SELECTION, source px); the eye
    midpoint lands at EYE_POS of the window, and every expression of a character uses the same source scale
    (EYE_DIST native px between the eyes of the reference image), so swapping expressions does not move the head.
    Sampled at WORK x the native size with a premultiplied-alpha prefilter.
 2. Flatten. L0 gradient minimisation (L0_LAMBDA) turns soft painting into flat regions with sharp edges.
 3. Classify. Each work pixel goes to its nearest source-colour prototype (32 per character, measured once on
    the whole selection with k-means in Lab); CLUT maps each prototype to a palette key, with separate keys inside
    the eyes and the mouth. 'mix' prototypes (anti-aliased seams between two materials) take the label of their
    neighbours instead of inventing a colour.
 4. Lines. Dark strokes (black-hat of L*) on line-capable keys win a native pixel when they cover LINE_FRAC of its
    block (eyes and mouth / rest of the face / elsewhere); 2-px-thick runs are thinned to 1 px.
 5. Downsample. Majority vote of each WORK x WORK block, iris keys weighted up inside the eyes.
 6. Features, redrawn from measurements rather than voted: eyes (lash, 3-step iris ramp, one highlight, stray iris
    pixels removed), a closed mouth as a continuous 1-px stroke along its centre line (2-6 px, soft ends), a small
    open mouth as that stroke plus one pink pixel, blush on interior cheek skin, and Shione's two red marks as two
    parallel 2-3 px strokes with a 1-px gap.
 7. Cleanup. Components of <= 2 px (hair: <= 3) merge into their surroundings, except the eyes, the drawn mouth,
    the marks and face lines (line runs of >= 3 px touching skin); hair pixels with at most one like neighbour
    follow the majority around them (no speckle, no checkerboard).
 8. Sel-out. Silhouette pixels take their material's outline colour (the sprite outlines), never pure black; the
    window cut (frame edges) gets no outline.
Palettes are the in-game sprite ramps (tools/art/tsu_base.py, saji.py, shione.py) plus a few portrait-only steps
(marked * below; each one says why).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage.morphology import thin

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC_DIR = os.path.join(ROOT, 'assets', 'portraits', 'src')
OUT_DIR = os.path.join(ROOT, 'assets', 'portraits', 'pixel_v1')   # v1 (superseded by v4, tools/art/portraits4)

# ------------------------------------------------------------------------------------------------ parameters

SIZE = 80                 # native px, square bust window (chosen in layout mock-ups; see the knowledge note)
WORK = 4                  # supersampling of the work image
EYE_POS = (0.50, 0.52)    # eye midpoint in the window (fractions of SIZE)
EYE_DIST = 17.0           # native px between the eyes of each character's reference image
REF_EYE_DIST = {'tsuzumi': 64.5, 'shione': 66.0, 'saji': 73.0}  # source px between the eyes, reference images
L0_LAMBDA = 0.010         # flattening strength
LINE_BH = (7.0, 9.0, 16.0)        # black-hat threshold (L*): eyes and mouth / face / elsewhere
LINE_FRAC = (0.19, 0.25, 0.31)    # share of a block a line must cover to win it: eyes and mouth / face / elsewhere
SKIN_STROKE = (11.0, 24.0)        # strokes on skin in the face: soft line above the first, skin line above the second
BLUSH_DA = {'tsuzumi': 7.0, 'shione': 7.0, 'saji': 4.5}  # a* above the skin median = blush (cheeks only);
                          # Saji's rosy cheeks are part of her design, so her threshold is lower
IRIS_WEIGHT = 1.6         # vote weight of iris keys inside the eyes
EYE_COVER = (0.25, 0.30)  # lash / iris share of a native pixel (inside an eye) that makes it lash / iris
MOUTH_BH = 5.0            # black-hat threshold of a closed mouth stroke
MOUTH_MAX_W = 6           # widest closed mouth, native px
CLEAN_MAX = (2, 3)        # largest component merged away: other keys / hair keys
WEBP_QUALITY = 92         # work crops

# ------------------------------------------------------------------------------------------------ selection
# expression: (source image, left eye, right eye, mouth centre (all source px), mouth state)
# mouth state: 'open' (voted like any region), 'small' (stroke + one pink pixel), 'closed' (stroke), 'hidden'
# (a hand over the mouth; supported, but no expression uses it: at 80 px the fingers smear or vanish, see the note).
SELECTION = {
    'tsuzumi': {
        'neutral': ('A_35', (532, 209), (593, 237), (555.4, 273.2), 'closed'),
        'smile': ('A_01', (497, 207), (558, 235), (518.6, 265.3), 'closed'),
        'grin': ('A_28', (487, 205), (548, 234), (511.8, 265.5), 'open'),
        'laugh': ('A_22', (496, 201), (553, 238), (512.4, 258.2), 'open'),
        'surprise': ('A_13', (490, 209), (546, 238), (507.7, 271.7), 'open'),
        'shout': ('A_12', (569, 216), (625, 241), (588.7, 277.8), 'open'),
        'sad': ('A_23', (510, 219), (562, 241), (505.7, 268.4), 'closed'),
        'cry': ('A_24', (491, 207), (551, 235), (505.2, 264.3), 'closed'),
        'pout': ('A_04', (495, 208), (562, 234), (510.6, 256.9), 'closed'),
        'doubt': ('A_09', (491, 203), (551, 235), (515.7, 267.5), 'closed'),
        'think': ('A_34', (506, 214), (565, 244), (521.7, 274.4), 'small'),
        'embarrassed': ('A_03', (537, 213), (591, 239), (544.4, 266.9), 'closed'),
        'serious': ('A_25', (490, 205), (549, 230), (511.5, 262.5), 'closed'),
        'determined': ('A_10', (531, 197), (587, 226), (550.0, 254.1), 'closed'),
        'tired': ('A_19', (510, 228), (560, 257), (527.6, 282.3), 'small'),
        'calm': ('A_29', (498, 208), (553, 236), (510.9, 264.7), 'closed'),
    },
    'shione': {
        'neutral': ('B_10', (524, 167), (581, 192), (545.0, 222.1), 'closed'),
        'smile': ('B_01', (519, 167), (582, 192), (543.0, 219.3), 'closed'),
        'grin': ('B_02', (537, 154), (601, 181), (560.6, 210.0), 'open'),
        'laugh': ('B_22', (537, 152), (616, 191), (565.3, 214.8), 'open'),
        'surprise': ('B_13', (530, 182), (588, 210), (546.5, 242.1), 'open'),
        'shout': ('B_12', (644, 194), (705, 215), (670.6, 255.4), 'open'),
        'sad': ('B_23', (535, 191), (593, 211), (556.6, 246.6), 'closed'),
        'cry': ('B_24', (528, 166), (589, 195), (539.5, 219.0), 'closed'),
        'pout': ('B_04', (531, 166), (594, 191), (551.9, 214.3), 'closed'),
        'doubt': ('B_09', (521, 172), (577, 199), (539.8, 219.5), 'closed'),
        'think': ('B_34', (523, 172), (582, 201), (539.0, 230.8), 'small'),
        'embarrassed': ('B_03', (539, 170), (594, 200), (560.4, 230.8), 'closed'),
        'serious': ('B_25', (520, 169), (581, 192), (536.9, 215.2), 'closed'),
        'tired': ('B_19', (541, 181), (592, 207), (551.0, 231.8), 'small'),
        'calm': ('B_29', (525, 168), (586, 186), (543.3, 220.7), 'closed'),
        'blank': ('B_35', (543, 186), (607, 205), (569.0, 243.2), 'small'),
    },
    'saji': {
        'neutral': ('C_10', (526, 169), (585, 203), (547.8, 236.6), 'closed'),
        'smile': ('C_01', (495, 184), (559, 218), (523.9, 249.5), 'closed'),
        'grin': ('C_28', (497, 177), (562, 216), (506.3, 234.4), 'open'),
        'laugh': ('C_22', (514, 177), (580, 218), (528.0, 245.6), 'open'),
        'surprise': ('C_13', (524, 188), (587, 220), (548.8, 258.3), 'open'),
        'shout': ('C_12', (602, 196), (668, 224), (625.2, 267.9), 'open'),
        'sad': ('C_23', (525, 213), (578, 243), (538.3, 272.3), 'closed'),
        'cry': ('C_24', (513, 182), (576, 218), (520.8, 237.3), 'closed'),
        'pout': ('C_04', (495, 184), (562, 218), (527.5, 251.9), 'closed'),
        'doubt': ('C_09', (500, 189), (561, 224), (521.0, 255.4), 'closed'),
        'think': ('C_34', (495, 188), (560, 225), (514.1, 257.1), 'small'),
        'embarrassed': ('C_03', (525, 183), (574, 216), (522.5, 241.1), 'closed'),
        'serious': ('C_25', (492, 183), (559, 213), (512.9, 245.2), 'closed'),
        'tired': ('C_19', (506, 205), (561, 242), (522.8, 267.3), 'closed'),
        'calm': ('C_29', (498, 183), (564, 215), (519.6, 245.6), 'closed'),
    },
}

# ------------------------------------------------------------------------------------------------ palettes
# key: hex. Sprite ramps first (same hex as tools/art/*.py), then portrait-only steps (marked *).

PALETTE = {
    'tsuzumi': {
        'ink': '#16122a',
        # hair, warmed one step from the sprite ramp (#231c37 #342a4f #4d406f #76689e): large areas of the
        # cool sprite ramp read blue at bust size (*)
        'K': '#241a2e', 'k': '#33263e', 'j': '#4b3a58', 'H': '#6f5c80',
        'n': '#2f305c', 'i': '#42487d',                                   # indigo
        'W': '#fbf7ef', 'w': '#ebe3d6', 'v': '#cbc0cd', 'V': '#9d90aa',   # white: hat straw, collar
        'r': '#c03e5a', 'd': '#8c2b45', 'ro': '#3e1424',                  # red band, collar edge, red outline
        's': '#fde7d8', 'z': '#efbca8', 'Z': '#d4907f', 'so': '#6a3438', 'b': '#f5a0a2',  # skin, skin line, blush
        # iris dark / mid / light (*): the owner's reference draws a muted grey-blue; the sprite's #6f84b3 is
        # one or two pixels in game but a whole iris here, where it read as saturated blue
        'E': '#2a2444', 'e': '#707c97', 'el': '#a5aec2',
    },
    'shione': {
        'ink': '#2a0f1a', 'ho': '#3b3150',                                # outline, hair outline
        # hair (*): the sprite ramp's lightness steps (#706485 #9a8daf #c1b3d1 #ded4e7) moved to the warm,
        # pinkish silver of the owner's reference (Lab b* ~0); the sprite ramp reads periwinkle at bust size
        'Q': '#73647c', 'K': '#a08ea1', 'k': '#c6b3c1', 'h': '#e3d3da',
        'W': '#fcf9f6', 'w': '#ede5e3', 'v': '#cdbfcc',                   # white kimono
        'P': '#73526b', 'p': '#563b50', 'u': '#3f2a3b',                   # plum: horn, collar
        'R': '#cc4b5d', 'r': '#9e3548', 'd': '#6d2333',                   # red: eyes, marks, ribbon
        's': '#fde7d8', 'z': '#efbca8', 'Z': '#d4907f', 'so': '#6a3438', 'b': '#f5a0a2',
        'el': '#ec9a96',                                                  # iris light (*)
    },
    'saji': {
        'ink': '#36101c',
        'R': '#f0533f', 'r': '#cf3439', 'd': '#9b2434', 'D': '#691a2b',   # hair
        'Q': '#4fa8a0', 'q': '#2f7d7a', 'c': '#215a5d', 'C': '#13282c',   # teal: eyes, headband, outline
        'M': '#e3f1dc', 'm': '#c2dfc4', 'x': '#94c0a6',                   # mint cape
        'p': '#702e5e', 'u': '#4e2045',                                   # plum collar
        'Y': '#ffe58c', 'y': '#e2ae3c', 'g': '#a5702a',                   # gold bell
        'W': '#fcf8ef', 's': '#fde7d8', 'z': '#efbca8', 'Z': '#d4907f', 'so': '#6a3438', 'b': '#f5a0a2',
    },
}

MATERIAL = {
    'tsuzumi': {'ink': 'ink', 'K': 'hair', 'k': 'hair', 'j': 'hair', 'H': 'hair', 'n': 'indigo', 'i': 'indigo',
                'W': 'white', 'w': 'white', 'v': 'white', 'V': 'white', 'r': 'red', 'd': 'red', 'ro': 'red',
                's': 'skin', 'z': 'skin', 'Z': 'skin', 'so': 'skin', 'b': 'skin', 'E': 'eye', 'e': 'eye', 'el': 'eye'},
    'shione': {'ink': 'ink', 'ho': 'hair', 'Q': 'hair', 'K': 'hair', 'k': 'hair', 'h': 'hair', 'W': 'white',
               'w': 'white', 'v': 'white', 'P': 'plum', 'p': 'plum', 'u': 'plum', 'R': 'red', 'r': 'red', 'd': 'red',
               's': 'skin', 'z': 'skin', 'Z': 'skin', 'so': 'skin', 'b': 'skin', 'el': 'eye'},
    'saji': {'ink': 'ink', 'R': 'hair', 'r': 'hair', 'd': 'hair', 'D': 'hair', 'Q': 'teal', 'q': 'teal', 'c': 'teal',
             'C': 'teal', 'M': 'mint', 'm': 'mint', 'x': 'mint', 'p': 'plum', 'u': 'plum', 'Y': 'gold', 'y': 'gold',
             'g': 'gold', 'W': 'white', 's': 'skin', 'z': 'skin', 'Z': 'skin', 'so': 'skin', 'b': 'skin'},
}

# silhouette outline (sel-out): material -> key
SELOUT = {
    'tsuzumi': {'hair': 'ink', 'indigo': 'ink', 'eye': 'ink', 'ink': 'ink', 'white': 'k', 'red': 'ro', 'skin': 'so'},
    'shione': {'hair': 'ho', 'white': 'ho', 'plum': 'ink', 'red': 'ink', 'ink': 'ink', 'eye': 'ink', 'skin': 'so'},
    'saji': {'hair': 'ink', 'plum': 'ink', 'gold': 'ink', 'ink': 'ink', 'teal': 'C', 'mint': 'C', 'white': 'u',
             'skin': 'so'},
}

LINE_KEYS = {'tsuzumi': ('ink', 'so', 'ro', 'E'), 'shione': ('ink', 'ho', 'so', 'd', 'R'), 'saji': ('ink', 'so', 'C', 'D')}
IRIS = {'tsuzumi': ('E', 'e', 'el'), 'shione': ('r', 'R', 'el', 'd'), 'saji': ('q', 'Q', 'c', 'C')}
IRIS_RAMP = {'tsuzumi': ('E', 'e', 'el'), 'shione': ('d', 'R', 'el'), 'saji': ('c', 'q', 'Q')}  # top -> bottom
LASH = {'tsuzumi': 'ink', 'shione': 'ink', 'saji': 'ink'}
# face marks redrawn as 1-px strokes: Shione's two red marks under the eye on the viewer's left
MARKS = {'shione': {'eye': 'eye_l', 'key': 'R', 'clear': ('R', 'r', 'd', 'p', 'u', 'ink', 'so', 'Z')}}

# Source-colour prototypes (k-means, 32 per character, Lab, measured on the selection) -> palette key:
# (default, inside an eye, inside the mouth). Assigned by hand from where each prototype occurs.
CLUT = {
    'tsuzumi': [
        ('#211519', 'ink', 'ink', 'so'), ('#271e29', 'K', 'ink', 'so'), ('#282537', 'K', 'ink', 'so'),
        ('#312632', 'K', 'E', 'so'), ('#491d25', 'ro', 'ink', 'ro'), ('#3f2b2e', 'mix', 'ink', 'so'),
        ('#2f2f47', 'n', 'E', 'mix'), ('#3a2e3e', 'k', 'E', 'so'), ('#44374a', 'k', 'E', 'so'),
        ('#383957', 'i', 'E', 'mix'), ('#493745', 'k', 'E', 'so'), ('#6b2938', 'd', 'so', 'd'),
        ('#504156', 'j', 'E', 'so'), ('#584551', 'j', 'E', 'so'), ('#644545', 'mix', 'E', 'so'),
        ('#8a3248', 'd', 'so', 'd'), ('#65546b', 'H', 'e', 'so'), ('#aa3f59', 'r', 'so', 'r'),
        ('#766162', 'mix', 'e', 'so'), ('#90635d', 'mix', 'Z', 'so'), ('#928082', 'V', 'e', 'Z'),
        ('#b1847a', 'Z', 'Z', 'Z'), ('#b99e96', 'v', 'z', 'Z'), ('#baadb1', 'v', 'el', 'z'),
        ('#daa596', 'Z', 'z', 'b'), ('#e8b9a8', 'z', 'z', 'b'), ('#d3c0ba', 'v', 's', 'z'),
        ('#f2d0bf', 's', 's', 's'), ('#e5d6cd', 'w', 's', 's'), ('#fae2d3', 's', 's', 's'),
        ('#f4e8dc', 'W', 's', 's'), ('#f8eee4', 'W', 's', 's'),
    ],
    'shione': [
        ('#361b23', 'ink', 'ink', 'so'), ('#4d1f28', 'd', 'ink', 'd'), ('#4e2d3d', 'u', 'ink', 'so'),
        ('#62222f', 'd', 'd', 'd'), ('#5b3e41', 'mix', 'ink', 'so'), ('#64384a', 'p', 'ink', 'so'),
        ('#853140', 'r', 'r', 'd'), ('#61495d', 'ho', 'ink', 'so'), ('#884a4f', 'r', 'R', 'so'),
        ('#7b5a5c', 'mix', 'r', 'so'), ('#755d73', 'Q', 'Q', 'so'), ('#846d86', 'Q', 'Q', 'so'),
        ('#93767b', 'mix', 'r', 'Z'), ('#927b92', 'K', 'K', 'Z'), ('#ac7972', 'Z', 'Z', 'so'),
        ('#cf6e6f', 'R', 'R', 'R'), ('#a1899f', 'K', 'K', 'Z'), ('#b19192', 'mix', 'mix', 'Z'),
        ('#b199ad', 'k', 'k', 'z'), ('#cc9f95', 'Z', 'Z', 'Z'), ('#c1a9bb', 'k', 'k', 'z'),
        ('#c8abaa', 'v', 'mix', 'z'), ('#e7a194', 'z', 'el', 'b'), ('#ceb7c6', 'k', 'k', 'z'),
        ('#e8b9aa', 'z', 'z', 'z'), ('#dbc1bd', 'mix', 's', 's'), ('#d9c3cf', 'h', 'h', 's'),
        ('#e2ccd5', 'h', 'h', 's'), ('#f2d2c3', 's', 's', 's'), ('#e9d8d4', 'w', 's', 's'),
        ('#fbe7da', 's', 's', 's'), ('#f7eee6', 'W', 's', 's'),
    ],
    'saji': [
        ('#221616', 'ink', 'ink', 'so'), ('#3d1818', 'ink', 'ink', 'D'), ('#242f36', 'C', 'C', 'so'),
        ('#5d1c1e', 'D', 'ink', 'D'), ('#532732', 'u', 'ink', 'so'), ('#26464f', 'c', 'c', 'so'),
        ('#772429', 'D', 'ink', 'D'), ('#703142', 'p', 'ink', 'd'), ('#87272b', 'd', 'D', 'd'),
        ('#574742', 'mix', 'ink', 'so'), ('#94272b', 'd', 'd', 'd'), ('#31636d', 'q', 'q', 'so'),
        ('#a92f31', 'd', 'd', 'd'), ('#90594a', 'mix', 'mix', 'so'), ('#bd3636', 'r', 'r', 'd'),
        ('#cc3e3d', 'r', 'r', 'r'), ('#d53a39', 'r', 'r', 'r'), ('#767871', 'x', 'C', 'so'),
        ('#d84642', 'r', 'r', 'r'), ('#bd6055', 'mix', 'mix', 'R'), ('#dc5952', 'R', 'R', 'R'),
        ('#ba907f', 'Z', 'Z', 'Z'), ('#969f94', 'x', 'q', 'Z'), ('#6fa6a3', 'Q', 'Q', 'Z'),
        ('#d88f7a', 'Z', 'Z', 'b'), ('#d69e4d', 'y', 'mix', 'Z'), ('#b7bcad', 'm', 's', 'z'),
        ('#ecb298', 'z', 'z', 'b'), ('#d0d6c0', 'M', 's', 's'), ('#fbd3bb', 's', 's', 's'),
        ('#fcdcc6', 's', 's', 's'), ('#f7eadf', 'W', 's', 's'),
    ],
}
MIX = -1

# ------------------------------------------------------------------------------------------------ colour helpers


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def to_lab(c):
    c = np.asarray(c, np.float32)
    return cv2.cvtColor(c.reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(c.shape)


# ------------------------------------------------------------------------------------------------ crops


def pack_path(packs, name):
    letter, n = name[0], int(name[2:])
    rng = ['01-09', '10-18', '19-27', '28-36'][(n - 1) // 9]
    return os.path.join(packs, f'Character_{letter}_{rng}', f'{name}.png')


def scale_of(char):
    """Source px per native px."""
    return REF_EYE_DIST[char] / EYE_DIST


def window_origin(char, eye_l, eye_r):
    s = scale_of(char)
    mid = (np.asarray(eye_l, float) + np.asarray(eye_r, float)) / 2
    return mid[0] - EYE_POS[0] * SIZE * s, mid[1] - EYE_POS[1] * SIZE * s


def to_work(char, eye_l, eye_r, p):
    """Source px -> work px."""
    x0, y0 = window_origin(char, eye_l, eye_r)
    sk = scale_of(char) / WORK
    return np.array([(p[0] - x0) / sk, (p[1] - y0) / sk])


def cut_crop(packs, char, expr):
    name, eye_l, eye_r, _, _ = SELECTION[char][expr]
    rgba = np.asarray(Image.open(pack_path(packs, name)).convert('RGBA')).astype(np.float32) / 255.0
    alpha = np.clip((rgba[..., 3] - 0.03) / 0.93, 0, 1)        # the packs top out at alpha 253
    pm = np.dstack([rgba[..., :3] * alpha[..., None], alpha])   # premultiplied
    sk = scale_of(char) / WORK
    sig = max(0.0, 0.5 * sk - 0.25)
    if sig > 0.2:
        pm = cv2.GaussianBlur(pm, (0, 0), sig)
    x0, y0 = window_origin(char, eye_l, eye_r)
    m = np.array([[sk, 0, x0], [0, sk, y0]], np.float32)
    n = SIZE * WORK
    w = cv2.warpAffine(pm, m, (n, n), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT,
                       borderValue=0)
    a = w[..., 3:]
    c = np.where(a > 1e-3, w[..., :3] / np.maximum(a, 1e-3), 0)
    return (np.clip(np.dstack([c, a]), 0, 1) * 255).round().astype(np.uint8)


# ------------------------------------------------------------------------------------------------ pixelation


def fill_transparent(c, a):
    m = a < 0.5
    if not m.any() or m.all():
        return c
    _, (iy, ix) = ndi.distance_transform_edt(m, return_indices=True)
    return c[iy, ix]


def l0_smooth(img, lam, kappa=2.0, beta_max=1e5):
    """L0 gradient minimisation (Xu, Lu, Xu, Jia 2011)."""
    s = img.astype(np.float64).copy()
    h, w = s.shape[:2]

    def otf(psf):
        pad = np.zeros((h, w))
        pad[:psf.shape[0], :psf.shape[1]] = psf
        for ax, n in enumerate(psf.shape):
            pad = np.roll(pad, -(n // 2), axis=ax)
        return np.fft.fft2(pad)

    d2 = np.abs(otf(np.array([[1, -1]], float))) ** 2 + np.abs(otf(np.array([[1], [-1]], float))) ** 2
    n1 = np.fft.fft2(s, axes=(0, 1))
    beta = 2 * lam
    while beta < beta_max:
        gh = np.roll(s, -1, axis=1) - s
        gv = np.roll(s, -1, axis=0) - s
        t = (gh ** 2 + gv ** 2).sum(-1) < lam / beta
        gh[t] = 0
        gv[t] = 0
        n2 = (np.roll(gh, 1, axis=1) - gh) + (np.roll(gv, 1, axis=0) - gv)
        s = np.real(np.fft.ifft2((n1 + beta * np.fft.fft2(n2, axes=(0, 1))) / (1 + beta * d2)[..., None], axes=(0, 1)))
        beta *= kappa
    return np.clip(s, 0, 1).astype(np.float32)


def blackhat(lum, r=3):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.morphologyEx(lum, cv2.MORPH_CLOSE, k) - lum


def blocks(a):
    n = a.shape[0] // WORK
    return a.reshape(n, WORK, n, WORK, *a.shape[2:]).swapaxes(1, 2).reshape(n, n, WORK * WORK, *a.shape[2:])


class Character:
    """Palette, lookup tables and per-key flags of one character."""

    def __init__(self, char):
        self.char = char
        self.keys = list(PALETTE[char])
        self.ki = {k: i for i, k in enumerate(self.keys)}
        self.rgb = np.array([hexrgb(PALETTE[char][k]) for k in self.keys], np.float32)
        self.lab = to_lab(self.rgb)
        self.mat = [MATERIAL[char][k] for k in self.keys]
        self.proto = to_lab(np.array([hexrgb(h) for h, *_ in CLUT[char]], np.float32))
        self.lut = np.array([[self.ki.get(t, MIX) for t in row[1:]] for row in CLUT[char]])
        self.is_line = np.array([k in LINE_KEYS[char] for k in self.keys])
        self.is_skin = np.array([m == 'skin' for m in self.mat])
        self.is_hair = np.array([m == 'hair' for m in self.mat])
        self.is_iris = np.array([k in IRIS[char] for k in self.keys])
        self.selout = {m: self.ki[k] for m, k in SELOUT[char].items()}

    def classify(self, lab, eyes, mouth):
        d = ((lab[..., None, :] - self.proto[None, None]) ** 2).sum(-1)
        col = np.where(eyes, 1, np.where(mouth, 2, 0))
        return self.lut[d.argmin(-1), col]


def regions(char, eye_l, eye_r, mouth_c):
    """Work-resolution masks: each eye, the mouth, the face, the cheeks."""
    n = SIZE * WORK
    el, er = to_work(char, eye_l, eye_r, eye_l), to_work(char, eye_l, eye_r, eye_r)
    e = np.linalg.norm(er - el)
    d = (er - el) / e
    perp = np.array([-d[1], d[0]])
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)

    def ell(c, rx, ry):
        px, py = xx - c[0], yy - c[1]
        u = (px * d[0] + py * d[1]) / rx
        v = (px * perp[0] + py * perp[1]) / ry
        return u * u + v * v <= 1

    mid = (el + er) / 2
    mc = to_work(char, eye_l, eye_r, mouth_c)
    return {
        'eye_l': ell(el, 0.40 * e, 0.36 * e), 'eye_r': ell(er, 0.40 * e, 0.36 * e),
        'eye_l_c': el, 'eye_r_c': er, 'd': d, 'perp': perp,
        'mouth': ell(mc, 0.36 * e, 0.26 * e), 'mouth_core': ell(mc, 0.30 * e, 0.17 * e),
        'hand': ell(mc, 0.75 * e, 0.60 * e),
        'face': ell(mid + perp * 0.40 * e, 1.15 * e, 1.20 * e),
        'cheeks': ell(el + perp * 0.62 * e - d * 0.05 * e, 0.34 * e, 0.20 * e) |
        ell(er + perp * 0.62 * e + d * 0.05 * e, 0.30 * e, 0.20 * e),
        'mouth_c': mc, 'e': e,
    }


def fill_mix(idx, valid):
    """'mix' pixels take the most common real label in their 5x5 neighbourhood (repeated until none is left)."""
    idx = idx.copy()
    for _ in range(12):
        m = (idx == MIX) & valid
        if not m.any():
            break
        best = np.full(idx.shape, MIX)
        bestc = np.zeros(idx.shape)
        for v in np.unique(idx[valid & (idx != MIX)]):
            c = cv2.boxFilter(((idx == v) & valid).astype(np.float32), -1, (5, 5), normalize=False)
            upd = m & (c > bestc)
            best[upd] = v
            bestc[upd] = c[upd]
        idx[m] = best[m]
    idx[idx == MIX] = 0
    return idx


def thin_lines(ch, out, msk, keep):
    """2-px-thick runs of line keys become 1 px (outside `keep`); the shaved pixels take their non-line neighbours."""
    res = out.copy()
    for k in LINE_KEYS[ch.char]:
        m = (out == ch.ki[k]) & msk & ~keep
        comp, n = ndi.label(m, structure=np.ones((3, 3)))
        for ci in range(1, n + 1):
            cm = comp == ci
            area = cm.sum()
            if area < 4:
                continue
            sk = thin(cm)
            if sk.sum() >= 3 and area > 1.5 * sk.sum():
                for y, x in zip(*np.nonzero(cm & ~sk)):
                    win = out[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
                    wm = msk[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
                    nb = win[wm & ~ch.is_line[win]]
                    if len(nb):
                        vals, cnts = np.unique(nb, return_counts=True)
                        res[y, x] = vals[cnts.argmax()]
    return res


def render_eyes(ch, out, idx, reg):
    """Redraw each eye from coverage: lash, iris (3-step ramp, top to bottom), one highlight."""
    lash_k = ch.ki[LASH[ch.char]]
    ramp = [ch.ki[k] for k in IRIS_RAMP[ch.char]]
    for name in ('eye_l', 'eye_r'):
        em = reg[name]
        bl = blocks(em & (idx == lash_k)).mean(-1)
        bi = blocks(em & ch.is_iris[idx]).mean(-1)
        be = blocks(em).mean(-1) > 0.35
        is_lash = be & (bl >= EYE_COVER[0])
        is_iris = be & ~is_lash & (bi >= EYE_COVER[1])
        comp, n = ndi.label(is_iris, structure=np.ones((3, 3)))
        if n > 1:  # stray iris pixels (a lower-lid sparkle cut off by a lash) are not an eye
            sizes = ndi.sum(is_iris, comp, range(1, n + 1))
            is_iris = comp == (int(np.argmax(sizes)) + 1)
            stray = (comp > 0) & ~is_iris & ch.is_iris[out]
            for y, x in zip(*np.nonzero(stray)):
                win = out[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
                nb = win[~ch.is_iris[win] & (win != lash_k)]
                if len(nb):
                    vals, cnts = np.unique(nb, return_counts=True)
                    out[y, x] = vals[cnts.argmax()]
        out = np.where(is_lash, lash_k, out)
        ys, xs = np.nonzero(is_iris)
        if len(ys) >= 3:
            top, h = ys.min(), max(1, ys.max() - ys.min() + 1)
            for y, x in zip(ys, xs):
                f = (y - top) / h
                out[y, x] = ramp[0] if f < 0.30 else (ramp[1] if f < 0.62 else ramp[2])
            left, right = xs.min(), xs.max()
            j = int(np.argmin((ys - (top + 0.25 * h)) ** 2 + (xs - (left + 0.30 * (right - left + 1))) ** 2))
            if h >= 3 and right - left + 1 >= 2:
                out[ys[j], xs[j]] = ch.ki['W'] if 'W' in ch.ki else ramp[2]
        elif len(ys):
            out[ys, xs] = ramp[1]
    return out


def render_mouth(ch, out, msk, bh, reg, state):
    """A closed mouth becomes a 1-px stroke along its centre line; a small open one gets one pink pixel under it."""
    core = reg['mouth_core']
    st = (bh > MOUTH_BH) & reg['mouth']
    comp, n = ndi.label(st, structure=np.ones((3, 3)))
    keep = np.zeros_like(st)
    for ci in range(1, n + 1):
        cm = comp == ci
        if (cm & core).any() and cm.sum() >= 6:
            keep |= cm
    if not keep.any():
        return out, np.zeros_like(msk)
    w = np.where(keep, bh, 0.0)
    ny = w.shape[0] // WORK
    colmass = w.reshape(w.shape[0], ny, WORK).sum((0, 2))
    ys = np.arange(w.shape[0])[:, None]
    coly = (w * ys).reshape(w.shape[0], ny, WORK).sum((0, 2)) / np.maximum(colmass, 1e-6)
    cols = np.nonzero(colmass >= 0.30 * colmass.max())[0]
    cols = np.arange(cols.min(), cols.max() + 1)          # continuous: no gaps inside a mouth
    while len(cols) > MOUTH_MAX_W:                       # trim the weaker end
        cols = cols[1:] if colmass[cols[0]] < colmass[cols[-1]] else cols[:-1]
    strong = colmass >= 0.30 * colmass.max()
    for c in cols:                                       # interpolate the row where a column is faint
        if not strong[c]:
            left = [k for k in cols if k < c and strong[k]]
            right = [k for k in cols if k > c and strong[k]]
            if left and right:
                coly[c] = (coly[left[-1]] + coly[right[0]]) / 2
            else:
                coly[c] = coly[(left or right)[-1 if left else 0]]
    if len(cols) == 1:  # never a dot: take the stronger neighbour column too
        c0 = cols[0]
        nb = [c for c in (c0 - 1, c0 + 1) if 0 <= c < ny]
        cols = np.sort(np.append(cols, max(nb, key=lambda c: colmass[c])))
        coly[cols] = coly[c0]
    # clear the old marks inside the mouth (native), keep skin
    mn = blocks(reg['mouth']).mean(-1) > 0.25
    old = mn & msk & (ch.is_line[out] | (out == ch.ki['Z']) | (out == ch.ki['b']))
    for y, x in zip(*np.nonzero(old)):
        win = out[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        nb = win[ch.is_skin[win] & ~ch.is_line[win] & (win != ch.ki['b']) & (win != ch.ki['Z'])]
        if len(nb):
            vals, cnts = np.unique(nb, return_counts=True)
            out[y, x] = vals[cnts.argmax()]
        else:
            out[y, x] = ch.ki['s']
    drawn = np.zeros_like(msk)
    peak = colmass[cols].max()
    for i, c in enumerate(cols):
        y = int(coly[c] // WORK)
        end = i in (0, len(cols) - 1) and len(cols) > 2
        if 0 <= y < out.shape[0] and msk[y, c]:
            out[y, c] = ch.ki['Z'] if end and colmass[c] < 0.55 * peak else ch.ki['so']
            drawn[y, c] = True
    if state == 'small':
        cx = int(round(cols.mean()))
        y = int(coly[cx] // WORK) + 1 if cx in cols else int(coly[cols].mean() // WORK) + 1
        if 0 <= y < out.shape[0] and msk[y, cx] and ch.is_skin[out[y, cx]]:
            out[y, cx] = ch.ki['b']
            drawn[y, cx] = True
    return out, drawn


def majority(values, default):
    if not len(values):
        return default
    vals, cnts = np.unique(values, return_counts=True)
    return vals[cnts.argmax()]


def render_marks(ch, out, msk, lab_c, valid, reg, eb):
    """Re-draw face marks (red strokes under one eye) as up to two 1-px strokes following the source."""
    spec = MARKS.get(ch.char)
    if not spec:
        return out, np.zeros_like(msk)
    el = reg['eye_l_c'] if spec['eye'] == 'eye_l' else reg['eye_r_c']
    e, d, perp = reg['e'], reg['d'], reg['perp']
    n = SIZE * WORK
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx, cy = el + perp * 0.62 * e
    u = ((xx - cx) * d[0] + (yy - cy) * d[1]) / (0.34 * e)
    v = ((xx - cx) * perp[0] + (yy - cy) * perp[1]) / (0.34 * e)
    area = (u * u + v * v <= 1) & ~reg[spec['eye']]
    red = area & valid & (lab_c[..., 1] > 25) & (lab_c[..., 0] < 80)
    drawn = np.zeros_like(msk)
    if red.sum() < 8:
        return out, drawn
    ry, rx = np.nonzero(red)
    # clear the old mark pixels (outside the eye itself)
    an = (blocks(area).mean(-1) > 0.3) & msk & ~eb
    clear = np.isin(out, [ch.ki[k] for k in spec['clear'] if k in ch.ki]) & an
    for y, x in zip(*np.nonzero(clear)):
        win = out[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        out[y, x] = majority(win[ch.is_skin[win] & ~ch.is_line[win] & (win != ch.ki['Z'])], ch.ki['s'])
    # two marks when the red spreads over >= 1.5 native px: split at the widest gap in x (else one mark)
    lo, hi = np.percentile(rx, 5), np.percentile(rx, 95)
    if hi - lo >= 1.5 * WORK:
        xs_sorted = np.sort(rx[(rx >= lo) & (rx <= hi)])
        cut = xs_sorted[int(np.argmax(np.diff(xs_sorted)))] + 0.5 if len(xs_sorted) > 1 else (lo + hi) / 2
        if not (lo + 0.25 * (hi - lo) <= cut <= hi - 0.25 * (hi - lo)):
            cut = (lo + hi) / 2
        groups = [rx < cut, rx >= cut]
    else:
        groups = [np.ones_like(rx, bool)]
    strokes = [(ry[g], rx[g]) for g in groups]
    strokes = [(sy, sx) for sy, sx in strokes if len(sy) >= 4]
    if not strokes:
        return out, drawn
    # the marks are parallel and equally long: draw every stroke over the same 2-3 rows
    top = min(int(np.percentile(sy, 8)) // WORK for sy, _ in strokes)
    bot = max(int(np.percentile(sy, 92)) // WORK for sy, _ in strokes)
    rows = range(top, top + max(2, min(3, bot - top + 1)))
    xs = sorted(int(sx.mean()) // WORK for _, sx in strokes)
    if len(xs) == 2 and xs[1] - xs[0] < 2:  # keep a 1-px gap so the pair never fuses into a block
        xs[1] = xs[0] + 2
    for x in xs:  # vertical strokes: at 2-3 px a slant reads as a smudge
        for r in rows:
            if 0 <= r < SIZE and 0 <= x < SIZE and msk[r, x]:
                out[r, x] = ch.ki[spec['key']]
                drawn[r, x] = True
    return out, drawn


def merge_small(ch, out, msk, protect):
    for _ in range(2):
        for v in np.unique(out[msk]):
            comp, n = ndi.label((out == v) & msk)
            if n == 0:
                continue
            sizes = ndi.sum(np.ones_like(comp), comp, range(1, n + 1))
            lim = CLEAN_MAX[1] if ch.is_hair[v] else CLEAN_MAX[0]
            for ci in np.nonzero(sizes <= lim)[0]:
                m = comp == ci + 1
                if (m & protect).any():
                    continue
                ring = ndi.binary_dilation(m) & ~m & msk
                if ring.any():
                    vals, cnts = np.unique(out[ring], return_counts=True)
                    out[m] = vals[cnts.argmax()]
    return out


def smooth_hair(ch, out, msk, protect, passes=2):
    """A hair pixel with at most one like neighbour (8-conn) follows the hair key that holds >= 4 of its neighbours."""
    for _ in range(passes):
        res = out.copy()
        for y, x in zip(*np.nonzero(msk & ch.is_hair[out] & ~protect)):
            win = out[max(0, y - 1):y + 2, max(0, x - 1):x + 2]
            wm = msk[max(0, y - 1):y + 2, max(0, x - 1):x + 2].copy()
            wm[min(y, 1), min(x, 1)] = False
            nb = win[wm]
            if (nb == out[y, x]).sum() > 1:
                continue
            nb = nb[ch.is_hair[nb]]
            if len(nb):
                vals, cnts = np.unique(nb, return_counts=True)
                if cnts.max() >= 4:
                    res[y, x] = vals[cnts.argmax()]
        out = res
    return out


def pixelate(char, expr, crop_rgba):
    ch = Character(char)
    _, eye_l, eye_r, mouth_c, state = SELECTION[char][expr]
    a = crop_rgba[..., 3].astype(np.float32) / 255
    c = crop_rgba[..., :3].astype(np.float32) / 255
    valid = a > 0.5
    cf = fill_transparent(c, a)
    flat = l0_smooth(cf, L0_LAMBDA)
    reg = regions(char, eye_l, eye_r, mouth_c)
    eyes = reg['eye_l'] | reg['eye_r']
    mouth = reg['mouth'] if state != 'hidden' else np.zeros_like(valid)
    face = reg['face']
    lab_f, lab_c = to_lab(flat), to_lab(cf)
    # 3. classify (unsmoothed colours inside eyes and mouth keep their detail)
    idx = ch.classify(lab_f, eyes, mouth)
    idx = np.where(eyes | mouth, ch.classify(lab_c, eyes, mouth), idx)
    idx = fill_mix(idx, valid)
    # 4. strokes
    bh = blackhat(lab_c[..., 0])
    idx = np.where(mouth & (bh > 6.0) & valid & ch.is_skin[idx], ch.ki['so'], idx)
    sstroke = face & ~eyes & ~mouth & valid & ch.is_skin[idx] & (bh > SKIN_STROKE[0])
    if state == 'hidden':  # fingers over the mouth: keep only the strong finger lines, soft
        sstroke &= ~reg['hand'] | (bh > SKIN_STROKE[1])
        idx = np.where(sstroke, ch.ki['Z'], idx)
    else:
        idx = np.where(sstroke, np.where(bh > SKIN_STROKE[1], ch.ki['so'], ch.ki['Z']), idx)
    skin_now = ch.is_skin[idx] & valid & face & ~eyes & ~mouth
    if skin_now.sum() > 50:
        blush_w = reg['cheeks'] & skin_now & (lab_c[..., 1] > np.median(lab_c[..., 1][skin_now]) + BLUSH_DA[char])
    else:
        blush_w = np.zeros_like(valid)
    thr = np.where(eyes | mouth, LINE_BH[0], np.where(face, LINE_BH[1], LINE_BH[2]))
    line = ((bh > thr) & valid & ch.is_line[idx]) | sstroke
    # 5. downsample
    ib, lb, ab = blocks(idx), blocks(line), blocks(valid)
    eb = blocks(eyes).mean(-1) > 0.3
    mb = blocks(mouth).mean(-1) > 0.3
    fb = blocks(face).mean(-1) > 0.3
    nk = len(ch.keys)
    votes = np.stack([((ib == v) & ab).sum(-1) for v in range(nk)], -1).astype(np.float32)
    for k in IRIS[char]:
        votes[..., ch.ki[k]] *= np.where(eb, IRIS_WEIGHT, 1.0)
    out = votes.argmax(-1)
    lfrac = (lb & ab).mean(-1)
    need = np.where(eb | mb, LINE_FRAC[0], np.where(fb, LINE_FRAC[1], LINE_FRAC[2]))
    lv = np.stack([((ib == v) & lb & ab).sum(-1) for v in range(nk)], -1)
    pick = np.where(lv > 0, 1000 - ch.lab[:, 0][None, None], -1).argmax(-1)
    line_won = (lfrac >= need) & (lv.sum(-1) > 0)
    out = np.where(line_won, pick, out)
    msk = ab.mean(-1) >= 0.5
    skin_n = msk & ch.is_skin[out] & (out != ch.ki['so'])
    inner = ndi.binary_erosion(skin_n, structure=np.ones((3, 3)))
    bb = (blocks(blush_w).mean(-1) >= 0.5) & inner & ~eb
    comp, n = ndi.label(bb)
    if n:
        sizes = ndi.sum(bb, comp, range(1, n + 1))
        bb = np.isin(comp, np.nonzero(sizes >= 2)[0] + 1)
    out = np.where(bb, ch.ki['b'], out)
    out = thin_lines(ch, out, msk, eb)
    # 6. features
    out = render_eyes(ch, out, idx, reg)
    drawn = np.zeros_like(msk)
    if state in ('closed', 'small'):
        out, drawn = render_mouth(ch, out, msk, bh, reg, state)
    skin_px = msk & ch.is_skin[out] & ~ch.is_line[out]
    touch = ndi.binary_dilation(skin_px, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    out, marks = render_marks(ch, out, msk, lab_c, valid, reg, eb)
    face_lines = line_won & fb & ch.is_line[out] & touch
    comp, n = ndi.label(msk & ch.is_line[out], structure=np.ones((3, 3)))
    if n:  # a protected face line is a run of >= 3 px; lone dots on the hair edge are strand ends, not lines
        sizes = ndi.sum(np.ones_like(comp), comp, range(1, n + 1))
        face_lines &= np.isin(comp, np.nonzero(sizes >= 3)[0] + 1)
    # 7. cleanup
    protect = eb | (mb if state == 'open' else drawn) | face_lines | marks
    out = merge_small(ch, out, msk, protect)
    out = smooth_hair(ch, out, msk, eb | face_lines)
    # 8. sel-out (not on the window cut)
    edge = msk & ~ndi.binary_erosion(msk, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]), border_value=1)
    edge[-1, :] = edge[:, 0] = edge[:, -1] = edge[0, :] = False
    for y, x in zip(*np.nonzero(edge)):
        out[y, x] = ch.selout.get(ch.mat[out[y, x]], out[y, x])
    img = np.zeros((SIZE, SIZE, 4), np.uint8)
    img[..., :3] = (ch.rgb[out] * 255).round().astype(np.uint8)
    img[..., 3] = msk * 255
    return img


def area_downscale(crop_rgba):
    """The plain 'before' image: premultiplied box filter to native size (no palette)."""
    f = crop_rgba.astype(np.float32) / 255
    pm = np.dstack([f[..., :3] * f[..., 3:], f[..., 3:]])
    d = pm.reshape(SIZE, WORK, SIZE, WORK, 4).mean((1, 3))
    a = d[..., 3:]
    c = np.where(a > 1e-3, d[..., :3] / np.maximum(a, 1e-3), 0)
    return (np.clip(np.dstack([c, a]), 0, 1) * 255).round().astype(np.uint8)


# ------------------------------------------------------------------------------------------------ commands


def crop_path(char, expr):
    return os.path.join(SRC_DIR, char, f'{expr}.webp')


def load_crop(char, expr):
    return np.asarray(Image.open(crop_path(char, expr)).convert('RGBA'))


def cmd_crops(args):
    for char, exprs in SELECTION.items():
        os.makedirs(os.path.join(SRC_DIR, char), exist_ok=True)
        for expr in exprs:
            if args.only and f'{char}/{expr}' not in args.only:
                continue
            im = Image.fromarray(cut_crop(args.packs, char, expr), 'RGBA')
            im.save(crop_path(char, expr), 'WEBP', quality=WEBP_QUALITY, alpha_quality=100, method=6)
            print('crop', char, expr)


def cmd_build(args):
    manifest = {'size': SIZE, 'eye_line': [EYE_POS[0] * SIZE, EYE_POS[1] * SIZE], 'characters': {}}
    for char, exprs in SELECTION.items():
        os.makedirs(os.path.join(OUT_DIR, char), exist_ok=True)
        for expr in exprs:
            if args.only and f'{char}/{expr}' not in args.only:
                continue
            img = pixelate(char, expr, load_crop(char, expr))
            Image.fromarray(img, 'RGBA').save(os.path.join(OUT_DIR, char, f'{expr}.png'), optimize=True)
            print('build', char, expr)
        manifest['characters'][char] = {'expressions': list(exprs), 'palette': list(PALETTE[char].values()),
                                        'sources': {e: v[0] for e, v in exprs.items()}}
    with open(os.path.join(OUT_DIR, 'portraits.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=True)
        fh.write('\n')


def cmd_sheets(args):
    """Per character: before (plain area downscale) and after (pixel portrait), x4, labelled."""
    os.makedirs(args.out, exist_ok=True)
    font = ImageFont.load_default()
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',):
        if os.path.exists(p):
            font = ImageFont.truetype(p, 14)
    z, cols, bg = 4, 6, (92, 84, 96, 255)
    t = SIZE * z
    for char, exprs in SELECTION.items():
        for tag in ('before', 'after'):
            rows = (len(exprs) + cols - 1) // cols
            sheet = Image.new('RGB', (cols * (t + 6) + 6, rows * (t + 26) + 6), (30, 30, 34))
            for i, expr in enumerate(exprs):
                if tag == 'before':
                    im = area_downscale(load_crop(char, expr))
                else:
                    im = np.asarray(Image.open(os.path.join(OUT_DIR, char, f'{expr}.png')).convert('RGBA'))
                tile = Image.new('RGBA', (SIZE, SIZE), bg)
                tile.alpha_composite(Image.fromarray(im, 'RGBA'))
                x, y = 6 + (i % cols) * (t + 6), 6 + (i // cols) * (t + 26)
                sheet.paste(tile.resize((t, t), Image.NEAREST).convert('RGB'), (x, y + 20))
                ImageDraw.Draw(sheet).text((x, y + 2), f'{expr} ({exprs[expr][0]})', fill=(255, 236, 170), font=font)
            sheet.save(os.path.join(args.out, f'{char}_{tag}_x4.png'))
            print(char, tag)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('crops')
    a.add_argument('--packs', required=True, help='directory with the extracted Character_<L>_<nn-nn> folders')
    a.add_argument('--only', nargs='*', help='char/expr ...')
    b = sub.add_parser('build')
    b.add_argument('--only', nargs='*', help='char/expr ...')
    c = sub.add_parser('sheets')
    c.add_argument('--out', required=True)
    args = ap.parse_args()
    {'crops': cmd_crops, 'build': cmd_build, 'sheets': cmd_sheets}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
