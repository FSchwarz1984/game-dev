"""Indexed ramps: every terrain pixel is (ramp id, tone index), so the bake stays
on short discrete ramps like hand pixel art. Ramps are generated in OKLCh:
value from dark to light, chroma lowest at the ends, hue drifting cool in the
shadows and warm in the lights (low-saturation, v0.1's late-summer mood).
Time of day is NOT painted here: morning/dusk/night come from lighting and
grading in the engine."""
import numpy as np

N_TONES = 8


def _srgb_to_lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055) * 255.0


def srgb_to_oklab(rgb):
    r, g, b = _srgb_to_lin(rgb).T
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)


def oklab_to_srgb(lab):
    L, a, b = np.asarray(lab, np.float64).T
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return _lin_to_srgb(np.stack([r, g, bb], -1))


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)


def ramp(mid_hex, lo=0.17, hi=0.17, n=N_TONES, cool=18.0, warm=14.0, chroma_lo=0.55, chroma_hi=0.7):
    """n colours around a mid colour: lightness mid-lo .. mid+hi (OKLab L),
    hue rotated `cool` degrees toward blue at the dark end and `warm` toward
    yellow at the light end; chroma scaled down at both ends."""
    L0, a0, b0 = srgb_to_oklab(hexrgb(mid_hex)[None])[0]
    C0 = np.hypot(a0, b0)
    H0 = np.degrees(np.arctan2(b0, a0))
    out = []
    for i in range(n):
        t = i / (n - 1) * 2 - 1                  # -1 dark .. +1 light
        L = L0 + (hi if t > 0 else lo) * t
        if t < 0:
            hue = H0 + _toward(H0, 255.0, cool * -t)
            C = C0 * (1 + (chroma_lo - 1) * -t)
        else:
            hue = H0 + _toward(H0, 95.0, warm * t)
            C = C0 * (1 + (chroma_hi - 1) * t)
        a = C * np.cos(np.radians(hue))
        b = C * np.sin(np.radians(hue))
        out.append(oklab_to_srgb(np.array([[L, a, b]]))[0])
    return np.clip(np.round(np.array(out)), 0, 255).astype(np.uint8)


def _toward(h, target, deg):
    d = (target - h + 180) % 360 - 180
    return np.sign(d) * min(abs(d), deg)


# ---- CIELAB ramp generator ----------------------------------------------------
def lab_ramp(L0, L1, C, h, cool=24.0, warm=-16.0, c_end=0.55, n=N_TONES):
    """n colours from L*=L0 (dark) to L1 (light). Chroma peaks at C in the
    middle and falls to C*c_end at both ends; hue rotates `cool` degrees in the
    darks (toward cyan/blue) and `warm` in the lights (toward yellow/ochre)."""
    from skimage.color import lab2rgb
    out = []
    for i in range(n):
        t = i / (n - 1)
        s = 2 * t - 1
        L = L0 + (L1 - L0) * t
        c = C * (1 - (1 - c_end) * abs(s) ** 1.4)
        hh = h + (cool * -s if s < 0 else warm * s)
        a = c * np.cos(np.radians(hh))
        b = c * np.sin(np.radians(hh))
        out.append(lab2rgb(np.array([[[L, a, b]]], np.float64))[0, 0] * 255.0)
    return np.clip(np.round(np.array(out)), 0, 255).astype(np.uint8)


# ---- the ramps ----------------------------------------------------------------
# Targets (2026-10-14): lit noon grass should sit near v0.1's measured L* 40, C* 20
# (h about 120-140); shadows cooler and bluer, lights warmer (olive -> ochre).
# ids are stable: masks, atlases and the export refer to them.
RAMPS = {}
RAMP_ID = {}


def _add(name, colours):
    RAMP_ID[name] = len(RAMPS)
    RAMPS[name] = np.asarray(colours, np.uint8)


_add('none', np.zeros((N_TONES, 3)))
_add('grass', lab_ramp(17, 61, 19.0, 118, cool=34, warm=-20))         # meadow, olive
_add('grass_cool', lab_ramp(15, 57, 17.0, 130, cool=30, warm=-16))    # damp / shaded stretches
_add('grass_dry', lab_ramp(20, 64, 19.0, 100, cool=30, warm=-14))     # sun-bleached, ochre
_add('lawn', lab_ramp(16, 57, 16.0, 122, cool=32, warm=-18))
_add('moss', lab_ramp(16, 57, 18.0, 124, cool=28, warm=-22))
_add('forest', lab_ramp(13, 49, 10.0, 66, cool=30, warm=8))           # forest soil
_add('litter', lab_ramp(20, 58, 21.0, 62, cool=14, warm=10))          # fallen leaves
_add('needle', lab_ramp(19, 53, 17.0, 68, cool=14, warm=8))
_add('dirt', lab_ramp(25, 67, 14.0, 74, cool=28, warm=6))             # the old road
_add('earth', lab_ramp(28, 70, 13.0, 78, cool=26, warm=6))            # trodden yard
_add('gravel', lab_ramp(28, 72, 7.0, 84, cool=40, warm=0, c_end=0.6))
_add('stone', lab_ramp(20, 71, 4.5, 86, cool=120, warm=0, c_end=0.8))  # dressed stone: grey, blue-grey shade
_add('stone_warm', lab_ramp(21, 69, 8.0, 74, cool=60, warm=6, c_end=0.7))
_add('rock', lab_ramp(17, 68, 8.0, 62, cool=70, warm=10, c_end=0.7))  # cliff rock: grey-brown
_add('rock_warm', lab_ramp(19, 68, 13.0, 64, cool=30, warm=8, c_end=0.7))
_add('soil', lab_ramp(18, 58, 12.0, 70, cool=26, warm=8))             # earth banks
_add('wetsoil', lab_ramp(11, 43, 10.0, 70, cool=30, warm=6))
_add('water', lab_ramp(15, 60, 12.0, 205, cool=12, warm=-40, c_end=0.6))
_add('lichen', lab_ramp(38, 76, 21.0, 100, cool=10, warm=-6))
_add('flower_w', lab_ramp(48, 93, 6.0, 92, cool=20, warm=0))
_add('flower_y', lab_ramp(44, 86, 48.0, 88, cool=10, warm=0, c_end=0.6))
_add('flower_v', lab_ramp(32, 72, 32.0, 292, cool=6, warm=-6, c_end=0.6))
_add('flower_p', lab_ramp(44, 82, 26.0, 8, cool=6, warm=4, c_end=0.6))
_add('bark', lab_ramp(17, 53, 10.0, 66, cool=24, warm=8))

PALETTE = np.stack([RAMPS[k] for k in RAMPS])          # (n_ramps, N_TONES, 3)


def resolve(ramp_id, tone):
    """(ramp id, tone) rasters -> sRGB uint8."""
    t = np.clip(np.round(tone), 0, N_TONES - 1).astype(np.int64)
    return PALETTE[ramp_id.astype(np.int64), t]
