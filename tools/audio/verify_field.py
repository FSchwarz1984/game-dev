#!/usr/bin/env python3
"""Check the field-recording assets: decode, loop seams, sprite slices, spectrograms.

    python3 -I tools/audio/verify_field.py [out_dir]     # default out_dir: $AUDIO_CHECK or /tmp/field-audio-check

1. Every assets/audio/*.mp3 decodes without an ffmpeg error and is as long as META says.
2. Loops: the wrap loopEnd -> loopStart is checked twice, for a decoder that trims the MP3 encoder
   delay (ffmpeg, Chrome) and for one that keeps it (+1105 samples). The wrap is compared with 400
   ordinary cut points inside the same loop (sample step, 50 ms RMS change, high-band energy): a
   seamless wrap is just another point of the recording. Also checks that the padding repeats the
   loop head (proves the loop length survived encoding).
3. Sprites: each slice holds sound and its surroundings are quiet.
4. Writes a spectrogram PNG per file (and one around each loop's wrap) to out_dir.
"""
import json, os, re, subprocess, sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SR = 44100
DELAY = 1105  # LAME encoder delay + decoder delay, in samples, if a decoder does not trim it

def meta_from_field_js():
    js = open(os.path.join(ROOT, "src", "audio", "field.js"), encoding="utf-8").read()
    return json.loads(re.search(r"const META = (\{.*?\});\n// META:END", js, flags=re.S).group(1))

def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.float32).astype(np.float64), p.stderr.decode().strip()

def hp_energy(x, n=256):
    """Energy above ~6 kHz per n-sample frame (first difference twice as a cheap high-pass)."""
    d = np.diff(x, 2); m = len(d) // n
    return (d[: m * n].reshape(m, n) ** 2).mean(1)

def seam(b, ls, le):
    """Compare the wrap (last sample -> first sample of the loop) with 400 ordinary cut points inside
    the loop: a seamless wrap is statistically just another point of the recording. Reported values
    are percentiles of the wrap among those interior points (50 = typical, 100 = worse than all)."""
    i0, i1 = int(round(ls * SR)), int(round(le * SR))
    y = b[i0:i1]; L = len(y); n50 = int(0.05 * SR)
    ring = np.concatenate([y, y[:SR]])  # the loop as the player hears it, wrap at index L
    r = lambda s: 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-12)
    def feats(p):  # step at p, 50 ms RMS change across p, high-band energy in +-12 ms around p
        step = abs(ring[p] - ring[p - 1])
        jump = abs(r(ring[p:p + n50]) - r(ring[p - n50:p]))
        seg = ring[p - 512:p + 512]; hb = (np.diff(seg, 2) ** 2).mean()
        return step, jump, hb
    rng = np.random.default_rng(1)
    pts = rng.integers(SR, L - SR, 400)
    F = np.array([feats(p) for p in pts]); w = np.array(feats(L))
    pct = [float((F[:, k] < w[k]).mean() * 100) for k in range(3)]
    # padding repeats the head: b[i1 : i1+k] ~ b[i0 : i0+k] (proves the loop length survived encoding)
    k = int(0.15 * SR)
    a, c = b[i1:i1 + k], b[i0:i0 + k]
    corr = float(np.corrcoef(a, c)[0, 1]) if len(a) == k else float("nan")
    return dict(L=round(L / SR, 4), step_pct=round(pct[0], 1), rms_jump_pct=round(pct[1], 1), rms_jump_db=round(float(w[1]), 2),
                hiband_pct=round(pct[2], 1), pad_corr=round(corr, 3))

def spectrogram(x, out, title, width=1400, height=360, fmax=16000, marks=()):
    n = 2048; hop = max(64, len(x) // width)
    frames = max(1, (len(x) - n) // hop)
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    S = 20 * np.log10(np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1)) + 1e-9)
    k = int(fmax / (SR / n)); S = S[:, :k].T[::-1]
    v = np.clip((S - (S.max() - 80)) / 80, 0, 1)
    rgb = (np.stack([np.clip(v * 2.2 - .6, 0, 1), np.clip(v * 1.6 - .3, 0, 1), np.clip(.35 + v * .9 - v ** 2 * 1.1, 0, 1)], -1) * 255).astype(np.uint8)
    im = Image.fromarray(rgb).resize((width, height))
    W = width + 50; c = Image.new("RGB", (W, height + 60), (18, 18, 22)); c.paste(im, (45, 22)); d = ImageDraw.Draw(c)
    for f in range(0, fmax + 1, 4000):
        y = 22 + height - int(f / fmax * height); d.text((4, y - 6), f"{f // 1000}k", fill=(200, 200, 200))
    dur = len(x) / SR; step = 1 if dur <= 12 else 2 if dur <= 25 else 5
    for s in np.arange(0, dur, step):
        xx = 45 + int(s / dur * width); d.line([(xx, 22 + height), (xx, 28 + height)], fill=(200, 200, 200)); d.text((xx + 2, 28 + height), f"{s:g}", fill=(200, 200, 200))
    for t, lab in marks:
        xx = 45 + int(t / dur * width); d.line([(xx, 22), (xx, 22 + height)], fill=(255, 80, 80)); d.text((xx + 3, 24), lab, fill=(255, 120, 120))
    d.text((45, 4), title, fill=(255, 255, 255))
    c.save(out)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AUDIO_CHECK", "/tmp/field-audio-check")
    os.makedirs(out, exist_ok=True)
    meta = meta_from_field_js(); bad = 0
    for name, m in meta.items():
        path = os.path.join(ROOT, "assets", "audio", f"{name}.mp3")
        b, err = decode(path)
        dur = len(b) / SR
        ok = not err and dur >= m["dur"] - 0.05
        print(f"{name:7} decode {'ok' if ok else 'FAIL'}  {dur:6.2f} s (meta {m['dur']})  {os.path.getsize(path) / 1024:6.1f} KB {err[:80]}")
        bad += not ok
        if m["kind"] == "loop":
            for label, buf in (("trimmed", b), ("untrimmed", np.concatenate([np.zeros(DELAY), b]))):
                r = seam(buf, m["loopStart"], m["loopEnd"])
                # A click is a step at the wrap; high-band energy near an ordinary step is the recording's
                # own transient (a droplet, a chirp) that happens to sit there.
                good = r["step_pct"] < 99 and r["rms_jump_pct"] < 99 and (r["hiband_pct"] < 99 or r["step_pct"] < 50) and r["pad_corr"] > 0.8
                bad += not good
                print(f"        seam/{label:9} {'ok ' if good else 'BAD'} {r}")
            spectrogram(b, os.path.join(out, f"{name}.png"), f"{name}.mp3 (loop {m['loopStart']}-{m['loopEnd']} s)",
                        marks=[(m["loopStart"], "loopStart"), (m["loopEnd"], "loopEnd")])
            i0, i1 = int(m["loopStart"] * SR), int(m["loopEnd"] * SR)
            wrap = np.concatenate([b[i1 - SR:i1], b[i0:i0 + SR]])
            spectrogram(wrap, os.path.join(out, f"{name}-wrap.png"), f"{name}: last 1 s of the loop, then its first 1 s (wrap at 1.0 s)", width=900, marks=[(1.0, "wrap")])
        else:
            marks = []
            for s, (t0, d) in m["segs"].items():
                seg = b[int(t0 * SR): int((t0 + d) * SR)]
                pre = b[max(0, int((t0 - 0.12) * SR)): int((t0 - 0.02) * SR)]
                lvl = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12); gap = 20 * np.log10(np.sqrt((pre ** 2).mean()) + 1e-12) if len(pre) else -120
                sub = len(s.split("_")[-1]) > 1 and s.split("_")[-1][-1].isdigit()
                good = lvl > -40 and (sub or gap < lvl - 25)
                bad += not good
                print(f"        slice {s:9} {t0:6.2f}+{d:4.2f} s  rms {lvl:6.1f} dBFS  before {gap:6.1f} dBFS  {'ok' if good else 'CHECK'}")
                if not sub: marks.append((t0, s))
            spectrogram(b, os.path.join(out, f"{name}.png"), f"{name}.mp3 sprite", marks=marks)
    print("all checks passed" if not bad else f"{bad} check(s) failed")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
