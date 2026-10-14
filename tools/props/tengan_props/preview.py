"""CPU previews: the run-time lighting model (approximate) for contact sheets and quick looks.

Godot (knowledge/16, tools/flora/bench): CanvasModulate = sky (ambient); the DirectionalLight2D is
the main light with a fixed screen-space direction (LIGHT_C), its colour*energy changing with the
time of day; final = albedo * sky + albedo * sun * max(N.L, 0) (+ point lights); the glow layer adds
on top (unshaded). Shadows multiply the ground by shade_color = sky / (sky + sun * ndl_ground).
The definitive sheets are rendered in Godot (bench); these are for iteration.
"""
import math

import numpy as np

from .core import LIGHT_C, lin_to_srgb, smoothstep, srgb_to_lin

TOD = {
    'morning': {'elev': 24.0, 'sun': (0.76, 0.68, 0.55), 'sky': (0.56, 0.58, 0.65)},
    'noon': {'elev': 58.0, 'sun': (0.64, 0.61, 0.53), 'sky': (0.53, 0.56, 0.60)},
    'dusk': {'elev': 15.0, 'sun': (1.12, 0.68, 0.40), 'sky': (0.42, 0.37, 0.49)},
    'night': {'elev': 40.0, 'sun': (0.20, 0.25, 0.40), 'sky': (0.19, 0.23, 0.36)},
}
FAR_COL = np.array([0.70, 0.77, 0.88])


def decode_normal(nrgb):
    n = nrgb.astype(np.float64) / 255.0 * 2.0 - 1.0
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)


def light(rgb, nrgb, tod, linear=False, sun_vis=1.0):
    """rgb 0..255 float/uint8 (H,W,3), nrgb uint8 normal map -> lit rgb 0..255 float."""
    T = TOD[tod] if isinstance(tod, str) else tod
    n = decode_normal(nrgb)
    ndl = np.clip(n @ LIGHT_C, 0, 1)[..., None]
    sky = np.asarray(T['sky'])
    sun = np.asarray(T['sun'])
    if linear:
        a = srgb_to_lin(np.asarray(rgb, np.float64) / 255.0)
        c = a * (srgb_to_lin(sky) + srgb_to_lin(sun) * ndl * sun_vis)
        return lin_to_srgb(c) * 255.0
    a = np.asarray(rgb, np.float64) / 255.0
    c = a * (sky + sun * ndl * sun_vis)
    return np.clip(c, 0, None) * 255.0


def lum(c):
    return c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114


def far_look(rgb, F, edge=None, t=0.0, seed=0.0):
    """The 遠化 colour (same maths as prop.gdshader): paler, lifted, drained toward a cool blue-grey,
    contrast compressed but the value structure kept (30 % of the original)."""
    if F <= 0:
        return rgb
    c = np.asarray(rgb, np.float64) / 255.0
    l = lum(c)[..., None]
    pale = FAR_COL * 0.48 + (FAR_COL * 0.95 - FAR_COL * 0.48) * smoothstep(0.0, 0.8, l)
    pale = pale + ((np.repeat(l, 3, -1) * 0.7 + c * 0.3) * 0.5 + FAR_COL * 0.45 - pale) * 0.32
    out = c + (pale - c) * (F * 0.82)
    if edge is not None:
        out = np.where(edge[..., None], out + (np.array([0.86, 0.90, 0.97]) - out) * (F * 0.45), out)
    return out * 255.0


def shade_color(tod, ground_ndl=0.75):
    T = TOD[tod]
    sky = np.asarray(T['sky'])
    sun = np.asarray(T['sun'])
    return np.clip(sky / np.maximum(sky + sun * ground_ndl, 1e-4), 0, 1)


def shadow_factor(img, elev, soft=2.5, tod='noon', strength=1.0, contact_k=0.55):
    """Multiply factor (H,W,3) from a horizon shadow map at sun elevation `elev`."""
    top = img[..., 0].astype(np.float64) * 90.0 / 255.0
    bot = img[..., 1].astype(np.float64) * 90.0 / 255.0
    con = img[..., 2].astype(np.float64) / 255.0
    cast = (1.0 - smoothstep(top - soft, top + soft, elev)) * np.where(bot > 0, smoothstep(bot - soft, bot + soft, elev), 1.0)
    cast = cast * (top > 0.5) * strength
    sc = shade_color(tod)
    f = 1.0 + (sc[None, None, :] - 1.0) * cast[..., None]
    cc = np.array([0.62, 0.64, 0.70])
    f = np.minimum(f, 1.0 + (cc[None, None, :] - 1.0) * (con * contact_k)[..., None])
    return np.where((img[..., 3] > 0)[..., None], f, 1.0)
