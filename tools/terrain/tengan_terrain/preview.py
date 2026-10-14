"""CPU preview of the run-time lighting, for fast iteration and contact sheets.

The model is the one the Godot shader implements (see godot/terrain.gdshader
in the preview project and docs/knowledge/17):
  ambient  = sky * (0.75 + 0.25 N.y) * (0.5 + 0.5 AO) + bounce * (0.5 - 0.5 N.y)
  sun      = sun_col * max(N.L, 0) * vis        (DirectionalLight2D, light())
  vis      = smoothstep(horizon - soft, horizon + soft, sun_elevation)
  colour   = albedo * (ambient + sun)            (sRGB space, like Godot 2D)
"""
import numpy as np

TOD = {
    # elevation (deg), sun colour*energy (DirectionalLight2D), sky = ambient (CanvasModulate),
    # bounce = light thrown back from the ground onto walls, sat = grade saturation
    'morning': dict(elev=24.0, sun=(0.66, 0.60, 0.50), sky=(0.52, 0.55, 0.62), bounce=(0.20, 0.19, 0.15), sat=0.92),
    'noon': dict(elev=58.0, sun=(0.64, 0.61, 0.53), sky=(0.53, 0.56, 0.60), bounce=(0.24, 0.23, 0.17), sat=0.95),
    'dusk': dict(elev=12.0, sun=(0.95, 0.58, 0.33), sky=(0.33, 0.30, 0.42), bounce=(0.16, 0.10, 0.08), sat=0.95),
    'night': dict(elev=40.0, sun=(0.17, 0.21, 0.34), sky=(0.15, 0.18, 0.30), bounce=(0.03, 0.03, 0.05), sat=0.75),
}


def sun_vector(elev_deg, toward_xz=(-0.92, 0.38)):
    e = np.radians(elev_deg)
    d = np.asarray(toward_xz, np.float64)
    d = d / np.linalg.norm(d)
    return np.array([d[0] * np.cos(e), np.sin(e), d[1] * np.cos(e)], np.float32)


def lit(albedo, normal, horizon, sky, mask, tod, toward_xz=(-0.92, 0.38), soft=2.5, elev=None):
    """albedo uint8 (H,W,3) sRGB; normal float (H,W,3) world; horizon deg; sky 0..1."""
    T = TOD[tod] if isinstance(tod, str) else tod
    e = T['elev'] if elev is None else elev
    L = sun_vector(e, toward_xz)
    a = albedo.astype(np.float32) / 255.0
    ndl = np.clip(np.einsum('hwc,c->hw', normal, L), 0, 1)
    t = np.clip((e - (horizon - soft)) / (2 * soft), 0, 1)
    vis = t * t * (3 - 2 * t)
    ny = np.clip(normal[..., 1], -1, 1)
    amb = np.asarray(T['sky'], np.float32)[None, None, :] * ((0.75 + 0.25 * ny) * (0.5 + 0.5 * sky))[..., None]
    amb = amb + np.asarray(T['bounce'], np.float32)[None, None, :] * (0.5 - 0.5 * ny)[..., None]
    sun = np.asarray(T['sun'], np.float32)[None, None, :] * (ndl * vis)[..., None]
    c = a * (amb + sun)
    # gentle grade: saturation
    lum = (c * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    c = lum + (c - lum) * T['sat']
    out = np.clip(c * 255.0, 0, 255).astype(np.uint8)
    out[~mask] = (14, 16, 22)
    return out
