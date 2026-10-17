"""Shared helpers for the sound pipeline (tools/audio): reading the renders, loops and one-shots, loudness
(ITU-R BS.1770-4 / EBU R128), true peak, writing WAV and Ogg Vorbis. numpy + scipy only; ffmpeg for Ogg.
"""
import hashlib
import subprocess
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100


# ------------------------------------------------------------------------------------------- files
def read(path):
    """-> float64 array (n, ch) in -1..1 (any WAV the pipeline writes or Godot's Movie Maker records)."""
    sr, x = wavfile.read(str(path))
    if x.dtype == np.int16:
        x = x.astype(np.float64) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float64) / 2147483648.0
    else:
        x = x.astype(np.float64)
    if x.ndim == 1:
        x = x[:, None]
    return sr, x


def write_wav16(path, x, dither_seed=0):
    """16-bit PCM WAV with TPDF dither (seeded: the same input always gives the same file)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2 and x.shape[1] == 1:
        x = x[:, 0]
    rng = np.random.default_rng(dither_seed)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
    y = np.clip(np.round((x + d) * 32767.0), -32768, 32767).astype(np.int16)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), SR, y)


def write_ogg(path, x, quality=6, tmp_dir=None):
    """Ogg Vorbis through ffmpeg/libvorbis from a 32-bit float intermediate (no dither, no clipping in
    the intermediate; the encoder sees the same samples). Metadata stripped."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tmp_dir or path.parent) / (path.stem + ".tmp.f32.wav")
    x = np.asarray(x, dtype=np.float32)
    wavfile.write(str(tmp), SR, x)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-map_metadata", "-1", "-c:a", "libvorbis",
                    "-q:a", str(quality), "-fflags", "+bitexact", "-flags:a", "+bitexact", str(path)], check=True)
    tmp.unlink()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def decode(path):
    """Decode any audio file with ffmpeg to float32 stereo/mono at its own rate -> (sr, array (n, ch))."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-acodec", "pcm_f32le", "-"],
                       capture_output=True, check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "stream=sample_rate,channels", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    sr, ch = [int(v) for v in probe.stdout.strip().split(",")[:2]]
    x = np.frombuffer(p.stdout, dtype=np.float32).astype(np.float64)
    return sr, x.reshape(-1, ch)


# ------------------------------------------------------------------------------------------- shaping
def mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def fade(x, fin=0.0, fout=0.0, curve="sine"):
    """Fade in / out in seconds (sine or linear), in place on a copy."""
    y = np.array(x, dtype=np.float64, copy=True)
    for n, rev in ((int(fin * SR), False), (int(fout * SR), True)):
        if n <= 0:
            continue
        n = min(n, len(y))
        t = (np.arange(n) + 0.5) / n
        g = np.sin(0.5 * np.pi * t) if curve == "sine" else t
        if y.ndim == 2:
            g = g[:, None]
        if rev:
            y[-n:] *= g[::-1]
        else:
            y[:n] *= g
    return y


def trim_tail(x, floor_db=-80.0, hold=0.15, min_len=0.05):
    """Cut a one-shot after its last sample above floor_db (relative to full scale) plus hold seconds."""
    m = np.max(np.abs(x), axis=1) if x.ndim == 2 else np.abs(x)
    above = np.nonzero(m > 10 ** (floor_db / 20))[0]
    if len(above) == 0:
        return x[: int(min_len * SR)]
    end = min(len(x), above[-1] + int(hold * SR))
    return x[: max(end, int(min_len * SR))]


def onset(x, floor_db=-70.0):
    m = np.max(np.abs(x), axis=1) if x.ndim == 2 else np.abs(x)
    i = np.nonzero(m > 10 ** (floor_db / 20))[0]
    return int(i[0]) if len(i) else 0


def make_loop(x, start_s, period_s, xfade_s, power=True):
    """A seamless loop of period_s seconds taken from x at start_s: the last xfade_s seconds are crossfaded
    with the xfade_s seconds that come just before start_s (which flow into x[start] the way the loop's
    end must), so the wrap from the loop's end to its start is continuous. power: equal-power fade
    (uncorrelated material: noise beds); else equal-gain (correlated material at the same musical
    position). Returns the loop (exactly round(period_s * SR) samples)."""
    s, p, f = int(round(start_s * SR)), int(round(period_s * SR)), int(round(xfade_s * SR))
    assert s - f >= 0 and s + p <= len(x), (s, p, f, len(x))
    loop = np.array(x[s: s + p], copy=True)
    pre = x[s - f: s]
    t = (np.arange(f) + 0.5) / f
    if power:
        gin, gout = np.sin(0.5 * np.pi * t), np.cos(0.5 * np.pi * t)
    else:
        gin, gout = t, 1.0 - t
    if loop.ndim == 2:
        gin, gout = gin[:, None], gout[:, None]
    loop[p - f:] = loop[p - f:] * gout + pre * gin
    return loop


# ------------------------------------------------------------------------------------------- measures
def _k_filter(sr):
    # BS.1770-4 K-weighting for any rate (high shelf +4 dB at ~1682 Hz, then the RLB high-pass ~38 Hz),
    # from the analogue prototypes (as pyloudnorm derives them)
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    K = np.tan(np.pi * fc / sr)
    Vh, Vb = 10 ** (G / 20), 10 ** (G / 20) ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    Q2, fc2 = 0.5003270373238773, 38.13547087602444
    K = np.tan(np.pi * fc2 / sr)
    b2 = [1, -2, 1]
    a2 = [1, 2 * (K * K - 1) / (1 + K / Q2 + K * K), (1 - K / Q2 + K * K) / (1 + K / Q2 + K * K)]
    return (b1, a1), (b2, a2)


def loudness(x, sr=SR):
    """Integrated loudness (LUFS, gated), short-term loudness track (3 s windows, 1 s hop) and LRA-ish
    spread. Silence -> -inf."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    (b1, a1), (b2, a2) = _k_filter(sr)
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        return {"integrated": float("-inf"), "short_term": [], "max_short_term": float("-inf")}
    n = 1 + (len(y) - blk) // hop
    z = np.array([np.mean(y[i * hop: i * hop + blk] ** 2, axis=0).sum() for i in range(n)])
    lk = -0.691 + 10 * np.log10(z + 1e-20)
    g1 = z[lk > -70]
    if len(g1) == 0:
        integ = float("-inf")
    else:
        rel = -0.691 + 10 * np.log10(np.mean(g1)) - 10
        g2 = z[(lk > -70) & (lk > rel)]
        integ = float(-0.691 + 10 * np.log10(np.mean(g2))) if len(g2) else float("-inf")
    st_blk, st_hop = int(3 * sr), int(1 * sr)
    st = []
    for i in range(0, max(0, len(y) - st_blk) + 1, st_hop):
        e = np.mean(y[i: i + st_blk] ** 2, axis=0).sum()
        st.append(float(-0.691 + 10 * np.log10(e + 1e-20)))
    return {"integrated": integ, "short_term": st, "max_short_term": max(st) if st else float("-inf")}


def true_peak_db(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-20))


def peak_db(x):
    return float(20 * np.log10(np.max(np.abs(x)) + 1e-20))
