"""ctypes wrapper around sdf_render.c (compiled on demand into a user cache directory, never into
the repository). See sdf_render.c for the primitive layout."""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sdf_render.c')
STRIDE = 76
_lib = None


def _cache_dir() -> str:
    base = os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
    d = os.path.join(base, 'tengan-sprite3d')
    os.makedirs(d, exist_ok=True)
    return d


def lib():
    global _lib
    if _lib is not None:
        return _lib
    src = open(SRC, 'rb').read()
    tag = hashlib.sha256(src).hexdigest()[:16]
    so = os.path.join(_cache_dir(), f'sdf_render_{tag}.so')
    if not os.path.exists(so):
        tmp = so + '.tmp'
        subprocess.check_call(['gcc', '-O2', '-ffp-contract=off', '-shared', '-fPIC', '-o', tmp, SRC, '-lm'])
        os.replace(tmp, so)
    L = ctypes.CDLL(so)
    f = ctypes.POINTER(ctypes.c_float)
    s16 = ctypes.POINTER(ctypes.c_int16)
    L.render.argtypes = [f, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float,
                         ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, f, ctypes.c_float,
                         ctypes.c_float, ctypes.c_int, f, s16, s16, f, f, f, f]
    L.render.restype = ctypes.c_int
    _lib = L
    return L


def _p(a, t):
    return a.ctypes.data_as(ctypes.POINTER(t))


def render(prims: np.ndarray, W: int, H: int, x0: float, y0: float, dx: float, dy: float, zmax: float, zmin: float,
           light, ao_dist: float = 3.0, shadow_k: float = 6.0, block: int = 1) -> dict:
    """prims: (n, STRIDE) float32 in camera space. Returns per-ray buffers (H, W[, 3])."""
    L = lib()
    prims = np.ascontiguousarray(prims, np.float32)
    n = prims.shape[0]
    light = np.ascontiguousarray(np.asarray(light, np.float32))
    depth = np.empty((H, W), np.float32)
    mat = np.empty((H, W), np.int16)
    part = np.empty((H, W), np.int16)
    nrm = np.empty((H, W, 3), np.float32)
    ao = np.empty((H, W), np.float32)
    sh = np.empty((H, W), np.float32)
    loc = np.empty((H, W, 3), np.float32)
    F = ctypes.c_float
    L.render(_p(prims, F), n, W, H, x0, y0, dx, dy, zmax, zmin, _p(light, F), ao_dist, shadow_k, int(block),
             _p(depth, F), _p(mat, ctypes.c_int16), _p(part, ctypes.c_int16), _p(nrm, F), _p(ao, F), _p(sh, F), _p(loc, F))
    return {'depth': depth, 'mat': mat, 'part': part, 'nrm': nrm, 'ao': ao, 'sh': sh, 'loc': loc}
