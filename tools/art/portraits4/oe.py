"""Contrast-aware pixelisation: a numpy port of PixelOE 0.0.10 (KohakuBlueleaf, Apache-2.0,
https://github.com/KohakuBlueleaf/PixelOE; see docs/knowledge/11). Same maths as the package's
`pixelize(mode='contrast', thickness=t, no_upscale=True)`, without torch: outline expansion (dark and light
strokes thickened by a local-brightness-weighted erode/dilate), colour matching back to the original, then a
downscale that picks, per output pixel, the block's minimum, maximum or middle lightness (a*, b* by median).
Checked against the package on one portrait crop: mean |difference| 2.2 (sum of RGB, 0..765), 1.9 % of pixels
off by more than 12 (padding at block edges)."""

import cv2
import numpy as np


def _chunk(data, k, s, func):
    """PixelOE's apply_chunk: every s x s block gets func(the k x k window around it)."""
    h, w = data.shape
    sh = max(k - s, 0)
    p0, p1 = sh // 2, sh // 2 + sh % 2
    d = np.pad(data, ((p0, p1), (p0, p1)), mode='edge')
    nby, nbx = (d.shape[0] - k) // s + 1, (d.shape[1] - k) // s + 1
    win = np.lib.stride_tricks.sliding_window_view(d, (k, k))[::s, ::s][:nby, :nbx]
    v = func(win.reshape(nby, nbx, k * k))
    out = np.repeat(np.repeat(v, s, 0), s, 1)
    res = np.zeros_like(data)
    hh, ww = min(h, out.shape[0]), min(w, out.shape[1])
    res[:hh, :ww] = out[:hh, :ww]
    return res


def _sig(x):
    return 1 / (1 + np.exp(-x))


def _expansion_weight(img, k, stride, avg_scale, dist_scale):
    y = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32) / 255
    avg = _chunk(y, k * 2, stride, lambda w: np.median(w, -1))
    mx = _chunk(y, k, stride, lambda w: w.max(-1))
    mn = _chunk(y, k, stride, lambda w: w.min(-1))
    weight = (avg - 0.5) * avg_scale - ((mx - avg) - (avg - mn)) * dist_scale
    out = _sig(weight)
    out = cv2.resize(out, (img.shape[1] // stride, img.shape[0] // stride), interpolation=cv2.INTER_LINEAR)
    out = cv2.resize(out, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    return (out - out.min()) / out.max()


_K3 = np.ones((3, 3), np.uint8)
_KX = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)


def outline_expansion(img, erode=1, dilate=1, k=4, avg_scale=9, dist_scale=4):
    wgt = _expansion_weight(img, k, (k // 4) * 2, avg_scale, dist_scale)[..., None]
    ow = _sig((wgt - 0.5) * 5) * 0.25
    e = cv2.erode(img, _K3, iterations=erode).astype(np.float32)
    d = cv2.dilate(img, _K3, iterations=dilate).astype(np.float32)
    out = e * wgt + d * (1 - wgt)
    out = out * (1 - ow) + img.astype(np.float32) * ow
    out = out.astype(np.uint8)
    out = cv2.erode(out, _KX, iterations=erode)
    out = cv2.dilate(out, _KX, iterations=dilate * 2)
    out = cv2.erode(out, _KX, iterations=erode)
    return out


def _wdec(x, levels=5):
    high = np.zeros_like(x)
    for i in range(1, levels + 1):
        r = 2 ** i
        low = cv2.GaussianBlur(x, (2 * r + 1, 2 * r + 1), 0)
        high = high + (x - low)
        x = low
    return high, x


def match_color(src, tgt):
    s = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32) / 255
    t = cv2.cvtColor(tgt, cv2.COLOR_BGR2LAB).astype(np.float32) / 255
    r = (s - s.mean()) / s.std() * t.std() + t.mean()
    out = cv2.cvtColor((r * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
    for c in range(3):
        hi, _ = _wdec(out[:, :, c])
        _, lo = _wdec(tgt[:, :, c].astype(np.float32))
        out[:, :, c] = hi + lo
    return out.clip(0, 255).astype(np.uint8)


def _find_pixel(w):
    mid = w[..., w.shape[-1] // 2]
    med = np.median(w, -1)
    mu = w.mean(-1)
    mx = w.max(-1)
    mn = w.min(-1)
    out = mid.copy()
    lo = (med < mu) & (mx - med > med - mn)
    hi = (med > mu) & (mx - med < med - mn)
    out[lo] = mn[lo]
    out[hi] = mx[hi]
    return out


def contrast_downscale(img, p):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    n, m = h // p, w // p
    blk = lab[:n * p, :m * p].reshape(n, p, m, p, 3).swapaxes(1, 2).reshape(n, m, p * p, 3)
    out = np.dstack([_find_pixel(blk[..., 0]), np.median(blk[..., 1], -1), np.median(blk[..., 2], -1)])
    return cv2.cvtColor(out.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def pixelize(bgr, p, thickness=1):
    """uint8 BGR image (p x the target size) -> uint8 BGR at the target size."""
    img = outline_expansion(bgr, thickness, thickness, p, 9, 4) if thickness else bgr
    img = match_color(img, bgr)
    return contrast_downscale(img, p)
