"""What made v0.1's "stream in strong wind" sound strange (G5R3-65, decision 2.3's added item).

Reads the renders of tools/audio/v01/streamwind_jobs (the original v0.1 engine, legacy/v0.1/src/audio.js,
by the brook at noon, same seed in every variant so the gusts and the noise are identical) and measures,
instead of guessing:
  1. pumping: the master compressor's gain over time (compressed mix / uncompressed mix), how far it
     swings, and how it follows the wind's gusts (the engine's own gust log);
  2. the creak events (the only wind-driven tonal source): how many, how loud against the beds, at what
     pitch, how tonal;
  3. the brook's own resonances: narrow peaks standing above the spectrum, how many and how they move;
  4. masking and beating between the brook's resonances and the wind: how much of the brook's tonal
     energy lies under the wind's spectrum, and the envelope fluctuation (roughness band) of the mix
     against the brook alone.
Usage: python3 -I tools/audio/v01/streamwind_probe.py <render_dir> [tag ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100


def load(p):
    sr, x = wavfile.read(p)
    assert sr == SR
    x = x.astype(np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def rms_track(x, win=0.05, hop=0.025):
    w, h = int(win * SR), int(hop * SR)
    n = 1 + (len(x) - w) // h
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    r = np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-20)
    t = (np.arange(n) * h + w / 2) / SR
    return t, r


def db(v):
    return 20 * np.log10(np.maximum(v, 1e-12))


def gust_curve(logs, t):
    # the engine sets W.gust with setTargetAtTime(g, t0, tc): an exponential approach from wherever it was
    ev = sorted([(r[1], r[2], r[3]) for r in logs if r and r[0] == "gust"])
    out = np.zeros_like(t)
    if not ev:
        return out
    cur, j = 0.6, 0
    last_t, tgt, tc = 0.0, 0.6, 1.0
    for i, tt in enumerate(t):
        while j < len(ev) and ev[j][0] <= tt:
            # advance the current value to the new event's start, then retarget
            cur = tgt + (cur - tgt) * np.exp(-(ev[j][0] - last_t) / tc)
            last_t, tgt, tc = ev[j]
            j += 1
        out[i] = tgt + (cur - tgt) * np.exp(-(tt - last_t) / tc)
    return out


def peaks_track(x, fmin=150, fmax=4500, prom_db=10.0):
    f, tt, Z = signal.stft(x, SR, nperseg=4096, noverlap=3072, window="hann")
    P = db(np.abs(Z) + 1e-12)
    band = (f >= fmin) & (f <= fmax)
    fb = f[band]
    counts, freqs = [], []
    for k in range(P.shape[1]):
        s = P[band, k]
        # smooth spectrum: median over ~1/3 octave (in bins, at the peak's own frequency)
        base = signal.medfilt(s, 41)
        pk, props = signal.find_peaks(s - base, height=prom_db)
        counts.append(len(pk))
        freqs.append(fb[pk])
    return np.array(counts), freqs, tt


def main(d, tags):
    d = Path(d)
    logs = {}
    for line in open(d / "render_log.jsonl", encoding="utf-8"):
        r = json.loads(line)
        logs[r["name"]] = r
    report = {}
    for tag in tags:
        R = {}
        full_c, full_n = load(d / f"{tag}_full_comp.f32.wav"), load(d / f"{tag}_full_nocomp.f32.wav")
        beds_c, beds_n = load(d / f"{tag}_beds_comp.f32.wav"), load(d / f"{tag}_beds_nocomp.f32.wav")
        stream, air = load(d / f"{tag}_stream_nocomp.f32.wav"), load(d / f"{tag}_air_nocomp.f32.wav")
        creak, events = load(d / f"{tag}_creak_nocomp.f32.wav"), load(d / f"{tag}_events_nocomp.f32.wav")
        skip = int(3 * SR)            # beds fade in over the first seconds
        t, rc = rms_track(full_c[skip:])
        _, rn = rms_track(full_n[skip:])
        gr = db(rc) - db(0.55 * rn)  # the compressor's net gain (its makeup included), dB
        t2, bc = rms_track(beds_c[skip:])
        _, bn = rms_track(beds_n[skip:])
        grb = db(bc) - db(0.55 * bn)
        g = gust_curve(logs[f"{tag}_beds_comp"]["logs"], t2 + 3.0)
        R["level_full_nocomp_dbfs_median"] = round(float(np.median(db(rn))), 1)
        R["level_full_nocomp_dbfs_p95"] = round(float(np.percentile(db(rn), 95)), 1)
        R["comp_gain_full_db"] = {"median": round(float(np.median(gr)), 2), "p5": round(float(np.percentile(gr, 5)), 2),
                                  "p95": round(float(np.percentile(gr, 95)), 2), "swing_p95_p5": round(float(np.percentile(gr, 95) - np.percentile(gr, 5)), 2)}
        R["comp_gain_beds_db"] = {"median": round(float(np.median(grb)), 2), "swing_p95_p5": round(float(np.percentile(grb, 95) - np.percentile(grb, 5)), 2)}
        # how the gain follows the gusts (negative: the gusts push everything else down, i.e. pumping)
        if np.std(g) > 1e-6:
            R["corr_comp_gain_vs_gust"] = round(float(np.corrcoef(grb, g)[0, 1]), 3)
            # the brook's level in the mix rides on the compressor: its envelope against its own envelope alone
        _, rs = rms_track(stream[skip:])
        _, ra = rms_track(air[skip:])
        R["stream_dbfs_median"] = round(float(np.median(db(rs))), 1)
        R["air_dbfs_median"] = round(float(np.median(db(ra))), 1)
        R["air_dbfs_p95"] = round(float(np.percentile(db(ra), 95)), 1)
        R["corr_air_level_vs_gust"] = round(float(np.corrcoef(db(ra), g)[0, 1]), 3) if np.std(g) > 1e-6 else None
        # 2. creak events
        tcr, rcr = rms_track(creak[skip:])
        on = db(rcr) > -70
        n_ev = int(np.sum(np.diff(on.astype(int)) == 1))
        ev_logs = [r for r in logs[f"{tag}_creak_nocomp"]["logs"] if r and r[0] == "event" and r[2] == "creak"]
        R["creak_events_per_min"] = round(len(ev_logs) / ((len(creak) / SR) / 60), 2)
        if on.any():
            lvl_cr = db(rcr[on])
            lvl_beds = db(bn[: len(rcr)][on]) if len(bn) >= len(rcr) else db(bn[on[: len(bn)]])
            R["creak_level_vs_beds_db_median"] = round(float(np.median(lvl_cr - lvl_beds)), 1)
            R["creak_level_vs_beds_db_max"] = round(float(np.max(lvl_cr - lvl_beds)), 1)
            # spectrum of the creak sections
            seg = creak[skip:][np.repeat(on, int(0.025 * SR))[: len(creak) - skip]] if False else None
            f, Pc = signal.welch(creak[skip:], SR, nperseg=8192)
            f2, Pb = signal.welch(beds_n[skip:], SR, nperseg=8192)
            band = (f > 60) & (f < 2000)
            pk = f[band][np.argmax(Pc[band])]
            R["creak_spectral_peak_hz"] = round(float(pk), 1)
            # tonality of the creak: peak over its 1/3-octave neighbourhood
            sm = signal.medfilt(10 * np.log10(Pc + 1e-20), 61)
            R["creak_peak_prominence_db"] = round(float(np.max((10 * np.log10(Pc + 1e-20) - sm)[band])), 1)
            # how far the creak's energy stands above the beds in its own band (150-400 Hz)
            b2 = (f > 150) & (f < 400)
            R["creak_vs_beds_150_400hz_db"] = round(float(10 * np.log10(np.sum(Pc[b2]) / np.sum(Pb[b2]))), 1)
        R["creak_onsets_counted"] = n_ev
        # 3. the brook's resonances
        cnt, fr, tt = peaks_track(stream[skip:])
        R["stream_peaks_per_frame_mean"] = round(float(cnt.mean()), 2)
        R["stream_frames_with_peaks_pct"] = round(float(100 * np.mean(cnt > 0)), 1)
        cnt_a, _, _ = peaks_track(air[skip:])
        R["air_peaks_per_frame_mean"] = round(float(cnt_a.mean()), 2)
        cnt_m, _, _ = peaks_track(beds_n[skip:])
        R["mix_peaks_per_frame_mean"] = round(float(cnt_m.mean()), 2)
        # 4. masking: share of the brook's energy (by band) at or below the air's level (third octaves)
        f, Ps = signal.welch(stream[skip:], SR, nperseg=8192)
        _, Pa = signal.welch(air[skip:], SR, nperseg=8192)
        edges = 125 * 2 ** (np.arange(0, 22) / 3)
        rows = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (f >= lo) & (f < hi)
            if not m.any():
                continue
            es, ea = np.sum(Ps[m]), np.sum(Pa[m])
            rows.append([round(float(np.sqrt(lo * hi))), round(float(10 * np.log10(es + 1e-30)), 1), round(float(10 * np.log10(ea + 1e-30)), 1)])
        R["third_octaves_hz_stream_db_air_db"] = rows
        tot = sum(10 ** (r[1] / 10) for r in rows)
        under = sum(10 ** (r[1] / 10) for r in rows if r[2] > r[1] - 3)
        R["stream_energy_within_3db_of_air_pct"] = round(100 * under / tot, 1)
        # envelope fluctuation 20-150 Hz (roughness) in 200-800 Hz: mix vs brook alone vs air alone
        def rough(x):
            b, a = signal.butter(4, [200 / (SR / 2), 800 / (SR / 2)], "band")
            y = signal.filtfilt(b, a, x)
            env = np.abs(signal.hilbert(y))
            f3, Pe = signal.welch(env - env.mean(), SR, nperseg=16384)
            m = (f3 >= 20) & (f3 <= 150)
            return float(np.sum(Pe[m]) / (np.mean(env) ** 2 + 1e-20))
        R["roughness_200_800hz"] = {"stream": round(rough(stream[skip:]), 5), "air": round(rough(air[skip:]), 5),
                                    "mix": round(rough(beds_n[skip:]), 5), "mix_comp": round(rough(beds_c[skip:]), 5)}
        report[tag] = R
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["f06", "f09", "b09", "f025"])
