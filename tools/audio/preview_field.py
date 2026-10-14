#!/usr/bin/env python3
"""Offline preview of the field-recording layer (src/audio/field.js), rendered with ffmpeg + numpy.

    python3 -I tools/audio/preview_field.py OUT_DIR [--ccby DIR]

  dusk-night.wav   60 s, game clock 17:30 -> 21:00, wind 0.3, waterfall 35 m away
  morning.wav      30 s, 07:00, nearness 1
  morning-far.wav  30 s, 07:00, nearness 0.35 (the engine's far rule: ~3.4 kHz low-pass, -4 dB, fewer calls)
  --ccby DIR       also dusk-night-ccby.wav, with the CC BY higurashi layers built by
                   `build_field.py --preview DIR --ccby dusk higu` (not shipped; for the licence decision)

field.js's behaviour (time windows, gains, distances, event rules) is mirrored here; MIX and META are
parsed from field.js, so levels and loop points cannot drift. Downstream it applies what the engine does
to the ambience bus: nearness low-pass and gain, the room reverb send (a synthetic 2.8 s forest IR like
the engine's), bus x master x compressor makeup x output (0.85 x 0.85 x +3.6 dB x 0.55). Checked against a
headless-Chromium capture of the real engine: within about 1 dB at night. Not modelled: compression
above the compressor's threshold (the ambience sits below it) and every synthesized layer still playing
(music, the synthesized higurashi at dusk until the CC BY layer is approved, kajika, bamboo, rain).
"""
import json, math, os, re, subprocess, sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SR, CR = 44100, 100  # audio rate, control rate (Hz)

def field_js():
    js = open(os.path.join(ROOT, "src", "audio", "field.js"), encoding="utf-8").read()
    meta = json.loads(re.search(r"const META = (\{.*?\});\n// META:END", js, flags=re.S).group(1))
    block = js[js.index("const MIX = {"): js.index("};", js.index("const MIX = {"))]
    mix = {k: {kk: float(vv) for kk, vv in re.findall(r"(\w+):\s*(-?[\d.]+)", body)} for k, body in re.findall(r"(\w+):\s*\{([^}]*)\}", block)}
    return meta, mix

def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)

def ff(x, af):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af, "-f", "f64le", "-"],
                         input=x.astype(np.float64).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float64)[: len(x)]

def lp_fft(x, fc):  # zero-phase 2nd-order low-pass magnitude (preview only)
    n = 1 << int(math.ceil(math.log2(len(x) + 1)))
    X = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), n)[: len(x)]

def pan_lr(p):
    a = (min(1, max(-1, p)) + 1) * math.pi / 4
    return math.cos(a), math.sin(a)

def win(h, a, b, f):
    h %= 24
    inside = (a <= h <= b) if a <= b else (h >= a or h <= b)
    if not inside: return 0.0
    t = min((h - a) % 24, (b - h) % 24) / f
    return 1.0 if t >= 1 else t * t * (3 - 2 * t)

def ss(a, b, x):
    t = min(1, max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

def forest_ir(sec=2.8, seed=7):
    rng = np.random.default_rng(seed); n = int(sec * SR); pre = int(0.012 * SR)
    t = np.arange(n - pre) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n - pre) * np.exp(-6.9 * t / sec)
        k = np.exp(-2 * math.pi * 3500 / SR); y = np.zeros_like(noise); acc = 0.0
        for i in range(len(noise)):  # one-pole low-pass ~3.5 kHz (the engine's IR darkens 9 -> 2.2 kHz)
            acc = noise[i] + k * (acc - noise[i]); y[i] = acc
        ir[pre:, c] = y / np.sqrt((y ** 2).sum())
    return ir

def convolve(x, ir):  # stereo in, stereo IR: L*irL, R*irR (what a 2-channel ConvolverNode does)
    n = 1 << int(math.ceil(math.log2(len(x) + len(ir))))
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c], n) * np.fft.rfft(ir[:, c], n), n)[: len(x)] for c in range(2)], 1)

class Layer:
    def __init__(self, name, buf, meta): self.name, self.buf, self.meta = name, buf, meta

def render(scene, layers, meta, mix, seed=11):
    """scene: dict(dur, tod0, tod1, near, wind, waterDist). Returns stereo output (N, 2)."""
    rng = np.random.default_rng(seed)
    N = int(scene["dur"] * SR); K = int(scene["dur"] * CR) + 1
    dry = np.zeros((N, 2)); wet = np.zeros((N, 2))
    near, wind, d_fall = scene["near"], scene["wind"], scene["waterDist"]
    act = ss(0.04, 0.6, near)
    hours = np.linspace(scene["tod0"], scene["tod1"], K)
    # ---- beds: target gains at control rate, smoothed like setTargetAtTime
    def bed_targets(name):
        g = np.zeros(K)
        mixA, next_mix, gust, next_gust = 0.7, 0.0, 1.0, 0.0
        for k in range(K):
            t, h = k / CR, hours[k]
            if t > next_mix: mixA = rng.uniform(0.45, 1); next_mix = t + rng.uniform(20, 45)
            if t > next_gust: gust = min(1.4, max(0.6, 1 + (rng.random() - 0.5) * (0.35 + 0.7 * wind))); next_gust = t + rng.uniform(0.8, 3)
            duskW = (win(h, 16.8, 19.4, 0.6) + 0.7 * win(h, 4.3, 5.9, 0.4)) * act
            nightW = win(h, 18.6, 4.8, 0.8) * act
            m = mix[name]; db = 10 ** (m["db"] / 20)
            g[k] = {"dusk": db * duskW, "night": db * nightW * mixA, "night2": db * nightW * (1.45 - mixA),
                    "wind": db * (0.3 + 2.3 * wind) * gust,
                    "fall": db * min(1.8, m.get("ref", 20) / max(1, d_fall)),
                    "stream": db * min(1.8, m.get("ref", 6) / max(1, d_fall))}[name]
        return g
    tcs = {"dusk": 3, "night": 4, "night2": 4, "wind": 1.2, "fall": 0.8, "stream": 0.8}
    for name in ("dusk", "night", "night2", "wind", "fall", "stream"):
        if name not in layers: continue
        L = layers[name]; m = mix[name]; mm = L.meta
        i0, i1 = int(round(mm["loopStart"] * SR)), int(round(mm["loopEnd"] * SR)); loop = L.buf[i0:i1]; n = len(loop)
        tgt = bed_targets(name); g = np.zeros(K); a = 1 - math.exp(-1 / (CR * tcs[name]))
        for k in range(1, K): g[k] = g[k - 1] + a * (tgt[k] - g[k - 1])
        env = np.interp(np.arange(N) / SR, np.arange(K) / CR, g)
        off = int(rng.uniform(0, n))
        if name in ("fall", "stream"):
            ref = m["ref"]; fc = min(18000, max(900, 15000 * ((ref * 0.5) / max(1, d_fall)) ** 0.75))
            send = min(0.6, max(m["wet"], m["wet"] + 0.45 * (1 - ref / max(1, d_fall))))
        elif name == "wind": fc, send = 6000 + 14000 * wind, m["wet"]
        else: fc, send = 20000, m["wet"]
        for i, p in enumerate((-m["spread"], m["spread"])):
            v = loop[(off + int(i * n * 0.382) + np.arange(N)) % n] * math.sqrt(0.5)
            if fc < 19000: v = ff(v, f"lowpass=f={fc:.0f}:p=2")
            l, r = pan_lr(p)
            s = v * env
            dry[:, 0] += s * l; dry[:, 1] += s * r; wet[:, 0] += s * l * send; wet[:, 1] += s * r * send
    # ---- events
    live = []
    def place(d, db):
        return dict(gain=10 ** (db / 20) * min(1.5, max(0.05, 15 / d)), lp=min(16000, max(1500, 16000 * (15 / d) ** 0.8)),
                    wet=min(0.65, max(0.1, 0.15 + 0.5 * (1 - 15 / d))))
    def play(name, slice_, t, o, sub=False):
        L = layers.get(name)
        if not L or slice_ not in L.meta["segs"]: return 0
        s0, d0 = L.meta["segs"][slice_]; lead, tail = (0, 0) if sub else (0.06, 0.1)
        a, b = int(max(0, s0 - lead) * SR), int((s0 + d0 + tail) * SR)
        x = L.buf[a:b]; rate = o["rate"]
        x = np.interp(np.arange(0, len(x) - 1, rate), np.arange(len(x)), x)
        x = lp_fft(x, o["lp"])
        n = len(x); e = np.ones(n); fi, fo = int((0.012 if sub else 0.004) * SR), int((0.05 if sub else 0.02) * SR)
        e[:fi] = np.linspace(0, 1, fi); e[-fo:] = np.linspace(1, 0, fo)
        x = x * e * o["gain"]; i0 = int((t + 0.03) * SR); i1 = min(N, i0 + n); x = x[: i1 - i0]
        l, r = pan_lr(o["pan"])
        dry[i0:i1, 0] += x * l; dry[i0:i1, 1] += x * r; wet[i0:i1, 0] += x * l * o["wet"]; wet[i0:i1, 1] += x * r * o["wet"]
        live.append((name, t + n / SR)); return n / SR
    busy = lambda kind, t: sum(1 for k, e in live if k == kind and e > t)
    pending, cool = [], {}
    CROWS = ["crow_a", "crow_b", "crow_a", "crow_b", "crow_a1", "crow_a3", "crow_b1", "crow_b2"]
    BIRDS = [("bulbul_a", 3, 14), ("bulbul_b", 2, 14), ("tit_a", 2, 10), ("tit_b", 2, 10), ("ugu_a", 1.2, 20), ("ugu_b", 1.2, 20), ("ugu_c", 1.2, 20)]
    def crow(t, answer=None):
        sl = CROWS[rng.integers(len(CROWS))]; p = place(rng.uniform(40, 160) if answer else rng.uniform(25, 120), mix["crow"]["db"] + rng.uniform(-3, 2))
        pan = min(1, max(-1, -answer + rng.uniform(-0.4, 0.4))) if answer is not None else rng.uniform(-0.95, 0.95)
        d = play("crow", sl, t, dict(p, gain=p["gain"] * act, pan=pan, rate=rng.uniform(0.96, 1.04)), sub=sl[-1].isdigit())
        if d and answer is None and rng.random() < 0.35: pending.append((t + d + rng.uniform(0.8, 3.5), lambda tt, pan=pan: crow(tt, pan)))
    def bird(t):
        ok = [b for b in BIRDS if "birds" in layers and b[0] in layers["birds"].meta["segs"] and not cool.get(b[0], -1) > t]
        if not ok: return
        r = rng.random() * sum(b[1] for b in ok); pick = ok[0]
        for b in ok:
            r -= b[1]
            if r <= 0: pick = b; break
        cool[pick[0]] = t + pick[2] * rng.uniform(0.8, 1.6)
        p = place(rng.uniform(12, 70), mix["birds"]["db"] + rng.uniform(-3, 2))
        play("birds", pick[0], t, dict(p, gain=p["gain"] * act, pan=rng.uniform(-0.9, 0.9), rate=rng.uniform(0.97, 1.03)))
    def higu(t, chain=0):
        segs = list(layers["higu"].meta["segs"]) if "higu" in layers else []
        if not segs: return
        p = place(rng.uniform(15, 60), mix["higu"]["db"] + rng.uniform(-3, 1))
        d = play("higu", segs[rng.integers(len(segs))], t, dict(p, gain=p["gain"] * act, pan=rng.uniform(-0.95, 0.95), rate=rng.uniform(0.98, 1.02)))
        if d and chain < 3 and rng.random() < 0.55: pending.append((t + d + rng.uniform(-1, 1.5), lambda tt, c=chain: higu(tt, c + 1)))
    dt = 1 / CR
    for k in range(K):
        t, h = k / CR, hours[k]
        if act > 0.02:
            crowW = win(h, 4.7, 19.2, 0.5) * (0.35 + win(h, 4.7, 7.5, 0.6) + win(h, 16.2, 19.2, 0.6))
            if "crow" in layers and busy("crow", t) < 2 and rng.random() < crowW * act * 0.02 * dt: crow(t)
            birdW = win(h, 4.8, 10.5, 0.8) + 0.3 * win(h, 10.5, 17.2, 0.8)
            if "birds" in layers and busy("birds", t) < 2 and rng.random() < birdW * act * 0.11 * dt: bird(t)
            duskW = (win(h, 16.8, 19.4, 0.6) + 0.7 * win(h, 4.3, 5.9, 0.4)) * act
            if "higu" in layers and busy("higu", t) < 3 and rng.random() < duskW * 0.08 * dt: higu(t)
        for item in [p for p in pending if p[0] <= t]:
            pending.remove(item); item[1](max(t, item[0]))
    # ---- engine ambience path
    nearG = (0.03 + 0.97 * ss(0, 0.6, near))
    lpF = 18000 if near >= 0.6 else 320 * (18000 / 320) ** min(1, near / 0.6)
    if lpF < 17000:
        dry = np.stack([ff(dry[:, c], f"lowpass=f={lpF:.0f}:p=2") for c in range(2)], 1)
        wet = np.stack([ff(wet[:, c], f"lowpass=f={lpF:.0f}:p=2") for c in range(2)], 1)
    dry_out = dry * nearG * 0.85
    room_in = wet * nearG * 0.85 + dry_out * 0.08
    ir = forest_ir()
    room = convolve(room_in, ir)
    # master 0.85, then Chrome's DynamicsCompressor (below threshold it still adds its automatic makeup,
    # about +3.6 dB at the engine's settings; see audio.js), then the engine's output trim 0.55.
    return (dry_out + room * 0.7) * 0.85 * 10 ** (3.6 / 20) * 0.55

def write(out, y, name):
    path = os.path.join(out, name)
    pk = np.abs(y).max()
    if pk > 0.99: y = y * (0.99 / pk)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s16le", path],
                   input=y.astype(np.float64).tobytes(), check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-c:a", "libmp3lame", "-q:a", "2", path[:-4] + ".mp3"], check=True)
    e = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-filter_complex", "ebur128", "-f", "null", "-"], capture_output=True).stderr.decode()
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", e[e.rfind("Summary"):]).group(1)
    print(f"{name}: {len(y) / SR:.0f} s, {I} LUFS integrated, peak {20 * math.log10(np.abs(y).max() + 1e-12):.1f} dBFS")

def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    meta, mix = field_js()
    layers = {k: Layer(k, decode(os.path.join(ROOT, "assets", "audio", f"{k}.mp3")), v) for k, v in meta.items()}
    dn = dict(dur=60, tod0=17.5, tod1=21.0, near=1.0, wind=0.3, waterDist=35)
    write(out, render(dn, layers, meta, mix), "dusk-night.wav")
    write(out, render(dict(dur=30, tod0=7, tod1=7, near=1.0, wind=0.3, waterDist=35), layers, meta, mix, seed=5), "morning.wav")
    write(out, render(dict(dur=30, tod0=7, tod1=7, near=0.35, wind=0.3, waterDist=35), layers, meta, mix, seed=5), "morning-far.wav")
    if "--ccby" in sys.argv:
        d = sys.argv[sys.argv.index("--ccby") + 1]
        cmeta = json.load(open(os.path.join(d, "meta.json")))
        more = dict(layers); more.update({k: Layer(k, decode(os.path.join(d, f"{k}.mp3")), v) for k, v in cmeta.items()})
        write(out, render(dn, more, meta, mix), "dusk-night-ccby.wav")

if __name__ == "__main__":
    main()
