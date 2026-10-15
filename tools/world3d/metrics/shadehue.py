# The renderer's painted shade (pixel_toon.gdshaderinc w3_shadow_hue, v1.4) for sRGB albedos, printed
# as the colour a surface of that albedo shows in the ambient only (the side away from the sun):
#   python3 -I tools/world3d/metrics/shadehue.py c8a868 8e7e5c ...
# ambient factor 0.59 = the noon sky/ground hemisphere seen by a vertical face (world_env.gd KEYS).
import math
import sys

import numpy as np


def s2l(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.round(255 * np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)).astype(int)


def lin_to_oklab(c):
    l = 0.4122214708 * c[0] + 0.5363325363 * c[1] + 0.0514459929 * c[2]
    m = 0.2119034982 * c[0] + 0.6806995451 * c[1] + 0.1073969566 * c[2]
    s = 0.0883024619 * c[0] + 0.2817188376 * c[1] + 0.6299787005 * c[2]
    l, m, s = np.cbrt([l, m, s])
    return np.array([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s])


def oklab_to_lin(L):
    l = L[0] + 0.3963377774 * L[1] + 0.2158037573 * L[2]
    m = L[0] - 0.1055613458 * L[1] - 0.0638541728 * L[2]
    s = L[0] - 0.0894841775 * L[1] - 1.2914855480 * L[2]
    l, m, s = l ** 3, m ** 3, s ** 3
    return np.array([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                     -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                     -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s])


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def shadow_hue(alb, turn=0.38):
    lab = lin_to_oklab(alb)
    C = math.hypot(lab[1], lab[2])
    h = math.atan2(lab[2], lab[1])
    T = -1.66                                   # blue-violet
    d = ((T - h + math.pi) % (2 * math.pi)) - math.pi
    turn *= smoothstep(0.025, 0.075, C)
    turn *= 1.0 - smoothstep(0.82 * math.pi, 0.97 * math.pi, abs(d))
    h += max(-turn, min(turn, d))
    ab = np.array([math.cos(h), math.sin(h)]) * (C * 1.15 + 0.006) + np.array([math.cos(T), math.sin(T)]) * 0.005
    return np.maximum(oklab_to_lin(np.array([lab[0], ab[0], ab[1]])), 0), math.degrees(math.atan2(lab[2], lab[1]))


for a in sys.argv[1:]:
    c = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    out, h = shadow_hue(s2l(c))
    print('%s  Oklab hue %3.0f  shade (x0.59): %s' % (a, h, l2s(out * 0.59)))
