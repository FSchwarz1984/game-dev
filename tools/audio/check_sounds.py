"""Objective checks of every sound file the game ships (decision 7, categories 1, 2, 3 and 5; category 4, the
whole mix in the game, is tools/audio/check_mix.py). Nothing here needs ears; what only ears can judge is left
to the user (decision 7). Exit code 1 if any check fails; warnings do not fail.

  python3 -I tools/audio/check_sounds.py [--json OUT.json] [--only id,id]

Per file: decodes; 44.1 kHz; sample and true peak <= -1 dBFS; no DC; no clipped samples; one-shots start and
end at silence (no click); loops: the wrap is an ordinary step (knowledge/07: the seam ranked against the
loop's own sample steps) and no loudness jump at the seam; no long digital silence inside loops; no steady
tone above 6 kHz held longer than 0.5 s (rule 6); no ultrasonic or infrasonic energy worth the name.
Beds (the brook-and-wind finding, G5R3-65 2.3): no repetition inside a bed (normalised self-correlation at
every lag from 0.25 s to half the loop < 0.15), the brook and the rain not whistling (narrow peaks >= 10 dB
over the spectrum's local median: < 1.5 per frame on average), no two beds sharing their noise (cross-
correlation < 0.1).
Variants: every pair of variants of a sound differ (max normalised cross-correlation < 0.97; reported).
Music: integrated loudness and loudness range per piece (reported), loop length in whole beats.
Content: every audio file under godot/ is listed in SOURCES.json, says which synthesizer made it, and its
SHA-256 matches; nothing from the old recordings remains.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import audiolib as AL  # noqa: E402

GODOT = ROOT / "godot"
AUDIO_EXT = {".ogg", ".wav", ".mp3", ".flac", ".opus", ".aiff", ".aif", ".m4a", ".aac", ".wma"}
SR = AL.SR


def load(rel):
    p = GODOT / rel.replace("res://", "")
    if p.suffix == ".wav":
        sr, x = AL.read(p)
    else:
        sr, x = AL.decode(p)
    return sr, x


def seam_rank(x):
    """knowledge/07: the step across the wrap against 4000 ordinary steps inside the loop (percentile)."""
    m = AL.mono(x)
    wrap = abs(m[0] - m[-1])
    rng = np.random.default_rng(7)
    idx = rng.integers(0, len(m) - 1, 4000)
    steps = np.abs(m[idx + 1] - m[idx])
    return float(np.mean(steps < wrap) * 100.0)


def seam_jump_db(x):
    """Short-time level (50 ms) just before the wrap against just after it."""
    m = AL.mono(x)
    n = int(0.05 * SR)
    a = np.sqrt(np.mean(m[-n:] ** 2) + 1e-20)
    b = np.sqrt(np.mean(m[:n] ** 2) + 1e-20)
    return float(abs(20 * np.log10(a / b)))


def longest_silence(x, floor_db=-90.0):
    m = np.max(np.abs(x), axis=1)
    q = m < 10 ** (floor_db / 20)
    best = run = 0
    for v in q:
        run = run + 1 if v else 0
        best = max(best, run)
    return best / SR


def held_tones(x, fmin, min_s, prom_db=15.0):
    """Longest time a narrow peak above fmin stays (+-1 bin), seconds."""
    m = AL.mono(x)
    if len(m) < 4096:
        return 0.0
    f, t, Z = signal.stft(m, SR, nperseg=4096, noverlap=3072)
    P = 20 * np.log10(np.abs(Z) + 1e-12)
    band = f >= fmin
    hop = 1024 / SR
    best = 0.0
    runs = {}
    for k in range(P.shape[1]):
        s = P[band, k]
        base = signal.medfilt(s, 31)
        pk = set(np.nonzero((s - base) > prom_db)[0].tolist())
        new = {}
        for b in pk:
            r = max(runs.get(b, 0), runs.get(b - 1, 0), runs.get(b + 1, 0)) + 1
            new[b] = r
            best = max(best, r * hop)
        runs = new
    return best


def band_ratio_db(x, lo=None, hi=None):
    m = AL.mono(x)
    f, P = signal.welch(m, SR, nperseg=8192)
    tot = np.sum(P) + 1e-30
    sel = np.ones_like(f, dtype=bool)
    if lo is not None:
        sel &= f >= lo
    if hi is not None:
        sel &= f < hi
    return float(10 * np.log10(np.sum(P[sel]) / tot + 1e-30))


def self_corr_max(x, period_s):
    m = AL.mono(x)
    w = int(0.5 * SR)
    lags = [l for l in [0.25, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30] if l <= period_s / 2]
    best = (0.0, 0.0)
    for L in lags:
        Ls = int(L * SR)
        v = []
        for s0 in range(0, len(m) - Ls - w, w):
            a, c = m[s0: s0 + w], m[s0 + Ls: s0 + Ls + w]
            v.append(np.dot(a, c) / np.sqrt(np.dot(a, a) * np.dot(c, c) + 1e-30))
        if v:
            med = float(np.median(v))
            if med > best[1]:
                best = (L, med)
    return best


def peaks_per_frame(x, fmin=150, fmax=4500, prom=10.0):
    m = AL.mono(x)
    f, t, Z = signal.stft(m, SR, nperseg=4096, noverlap=3072)
    P = 20 * np.log10(np.abs(Z) + 1e-12)
    band = (f >= fmin) & (f <= fmax)
    c = []
    for k in range(P.shape[1]):
        s = P[band, k]
        base = signal.medfilt(s, 41)
        pk, _ = signal.find_peaks(s - base, height=prom)
        c.append(len(pk))
    return float(np.mean(c))


def xcorr_max(a, b):
    n = min(len(a), len(b), 30 * SR)
    a, b = a[:n] - np.mean(a[:n]), b[:n] - np.mean(b[:n])
    N = 1 << int(np.ceil(np.log2(2 * n)))
    A, B = np.fft.rfft(a, N), np.fft.rfft(b, N)
    c = np.fft.irfft(A * np.conj(B), N)
    return float(np.max(np.abs(c)) / (np.sqrt(np.sum(a * a) * np.sum(b * b)) + 1e-30))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    sounds = json.loads((GODOT / "audio" / "sounds.json").read_text())["sounds"]
    sources = json.loads((GODOT / "audio" / "SOURCES.json").read_text())
    files_src = sources["files"]
    fails, warns, report = [], [], {"files": {}, "ids": {}, "beds": {}, "music": {}}

    def fail(msg):
        fails.append(msg)

    def warn(msg):
        warns.append(msg)

    # ---------------- content (5): every audio file is ours and listed
    found = sorted(p for p in GODOT.rglob("*") if p.suffix.lower() in AUDIO_EXT and ".godot" not in p.parts)
    for p in found:
        rel = str(p.relative_to(GODOT))
        if rel not in files_src:
            fail(f"content: {rel} is not listed in SOURCES.json")
            continue
        s = files_src[rel]
        gen = s.get("generator", "")
        if "synthesizer" not in gen and "numpy" not in gen:
            fail(f"content: {rel} does not say how it was synthesized")
        if s.get("sha256") and s["sha256"] != AL.sha256(p):
            fail(f"content: {rel} differs from its recorded SHA-256 (rebuilt without the manifest?)")
    for rel in files_src:
        if not (GODOT / rel).exists():
            fail(f"content: listed {rel} is missing")
    text = (GODOT / "audio" / "SOURCES.json").read_text().lower()
    for w in ["freesound", "xeno-canto", "aporee", "archive.org", "field recording"]:
        if w in text:
            fail(f"content: SOURCES.json still mentions {w}")
    report["content"] = {"audio_files": len(found), "listed": len(files_src)}

    beds = {}
    for sid, e in sounds.items():
        if only and sid not in only:
            continue
        kind, group = e["kind"], e.get("group", "")
        loop = bool(e.get("loop"))
        xs = []
        for f in e["files"]:
            rel = f.replace("res://", "")
            try:
                sr, x = load(rel)
            except Exception as ex:  # noqa: BLE001
                fail(f"{rel}: does not decode ({ex})")
                continue
            r = {"seconds": round(len(x) / sr, 3), "channels": int(x.shape[1])}
            if sr != SR:
                fail(f"{rel}: {sr} Hz, not 44100")
            pk, tp = AL.peak_db(x), AL.true_peak_db(x)
            r["peak_db"], r["true_peak_db"] = round(pk, 2), round(tp, 2)
            if tp > -1.0 + 0.05:
                fail(f"{rel}: true peak {tp:.2f} dBTP > -1")
            dc = float(np.max(np.abs(np.mean(x, axis=0))))
            r["dc"] = round(dc, 6)
            if dc > 0.001 and kind != "oneshot":
                fail(f"{rel}: DC offset {dc:.4f}")
            clip = int(np.sum(np.abs(x) >= 0.9999))
            if clip:
                fail(f"{rel}: {clip} clipped samples")
            if loop:
                rk = seam_rank(x)
                r["seam_rank_pct"] = round(rk, 1)
                if rk > 99.0:
                    fail(f"{rel}: the loop's wrap is a bigger step than {rk:.1f}% of its own steps (click)")
                # the level step across the seam against the same point of the render (music: a downbeat after a
                # rest is a jump there too; beds: should be none)
                sd = files_src.get(rel, {}).get("seam_db")
                if sd is None:
                    if group != "bed" or sid != "noise_pink":
                        fail(f"{rel}: no seam measurement in SOURCES.json")
                else:
                    r["seam_db"] = sd
                    if abs(sd["loop"] - sd["render"]) > 1.5:
                        fail(f"{rel}: the seam's level step {sd['loop']:+.1f} dB differs from the render's {sd['render']:+.1f} dB")
                    if group == "bed" and abs(sd["loop"]) > 3.0:
                        fail(f"{rel}: a bed jumps {sd['loop']:+.1f} dB at its seam")
                sil = longest_silence(x)
                r["longest_silence_s"] = round(sil, 2)
                if sil > 2.0:
                    fail(f"{rel}: {sil:.1f} s of digital silence inside a loop")
            else:
                e0, e1 = float(np.max(np.abs(x[0]))), float(np.max(np.abs(x[-1])))
                r["edges"] = [round(e0, 5), round(e1, 5)]
                if e0 > 0.002 or e1 > 0.002:
                    fail(f"{rel}: starts or ends away from silence ({e0:.4f}, {e1:.4f}): a click")
            if group not in ("music", "stinger", "festival"):
                ht = held_tones(x, 6000.0, 0.5)
                r["held_tone_above_6k_s"] = round(ht, 2)
                if ht > 0.5:
                    warn(f"{rel}: a narrow tone above 6 kHz held {ht:.2f} s (rule 6)")
            us, inf = band_ratio_db(x, lo=18000), band_ratio_db(x, hi=20)
            r["ultrasonic_db"], r["infrasonic_db"] = round(us, 1), round(inf, 1)
            if us > -40:
                warn(f"{rel}: energy above 18 kHz {us:.1f} dB of the total")
            if inf > -30:
                warn(f"{rel}: energy below 20 Hz {inf:.1f} dB of the total")
            report["files"][rel] = r
            xs.append(x)
        # ---------------- variants (3)
        if len(xs) >= 2 and kind == "oneshot":
            ms = [AL.mono(x) for x in xs]
            worst = 0.0
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    worst = max(worst, xcorr_max(ms[i], ms[j]))
            report["ids"][sid] = {"variants": len(xs), "max_pair_similarity": round(worst, 3)}
            # (voice blips are tones whose pitch is the variant, v0.1's speech melody: alike by design)
            if worst > 0.97 and group in ("step", "creature", "body", "ui", "verb", "saji", "thing"):
                fail(f"{sid}: two variants nearly identical (similarity {worst:.3f})")
        # ---------------- beds
        if group == "bed" and xs:
            beds[sid] = AL.mono(xs[0])
            period = len(xs[0]) / SR
            L, c = self_corr_max(xs[0], period)
            b = {"self_corr_max": round(c, 3), "at_lag_s": L}
            if c > 0.15:
                fail(f"{sid}: repeats itself (self-correlation {c:.2f} at {L} s)")
            if sid.startswith("bed_stream") or sid.startswith("bed_rain") or sid.startswith("bed_leaves") or sid.startswith("bed_sasa"):
                ppf = peaks_per_frame(xs[0])
                b["narrow_peaks_per_frame"] = round(ppf, 2)
                if ppf > 1.5:
                    fail(f"{sid}: whistles (narrow peaks {ppf:.2f} per frame)")
            report["beds"][sid] = b
        # ---------------- music
        if group in ("music", "festival") and xs:
            for f, x in zip(e["files"], xs):
                L = AL.loudness(x)
                st = [v for v in L["short_term"] if v > -70]
                report["music"][f.replace("res://", "")] = {"lufs": round(L["integrated"], 1),
                                                            "short_term_range_lu": round((np.percentile(st, 95) - np.percentile(st, 10)) if st else 0.0, 1)}
            if e.get("beats") is not None and abs(float(e["beats"]) - round(float(e["beats"]))) > 0.01:
                fail(f"{sid}: loop of {e['beats']} beats, not whole beats")
    # ---------------- beds share no noise
    ids = sorted(beds)
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            c = xcorr_max(beds[ids[i]], beds[ids[j]])
            pairs.append([ids[i], ids[j], round(c, 3)])
            if c > 0.1:
                fail(f"{ids[i]} and {ids[j]} share their noise (cross-correlation {c:.2f})")
    report["bed_pairs_max_xcorr"] = max((p[2] for p in pairs), default=0.0)
    report["fails"], report["warnings"] = fails, warns
    if a.json:
        Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"checked {len(report['files'])} files, {len(sounds)} sounds: {len(fails)} failures, {len(warns)} warnings")
    for m in fails[:60]:
        print("FAIL", m)
    for m in warns[:40]:
        print("warn", m)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
