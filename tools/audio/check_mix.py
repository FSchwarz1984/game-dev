#!/usr/bin/env python3
"""Measures the recordings of the game's own output (tools/audio/capture_mix.py; decision 7, category 4):
  every plan   integrated loudness (target -24 +-2 LUFS, IESD for consoles; no PC standard), true peak (<= -1 dBTP),
               the short-term loudness (3 s) and every jump of more than 6 LU from one second to the next, with
               its time, to be looked at against the picture
  menu         from each key press to the first sound it makes (<= 0.1 s, CLAUDE.md §3)
  gallery      the air's level before the dialogue and under it (the ducking: -4 dB)
  brook        the brook-and-wind check (G5R3-65 2.3): no repetition in the mix (self-correlation < 0.15 at every
               lag from 0.25 s to 20 s), and no pumping: the water's highs (6-10 kHz, the brook and the rain) must not
               dip when the wind (100-400 Hz) swells -- the dip per gust (slope of the fast level changes times two
               standard deviations of the wind's) must stay above -0.5 dB
  every plan   the 3D sample loads for about ten seconds (the GI bake) before its sound starts: the measures run on
               the steady part, from 2 s after the first second within 6 dB of the recording's median level
  any          with the plays log (--audio-log): no variant twice running, no variant above 2/n of its sound's plays
  python3 -I tools/audio/check_mix.py DIR [plan ...]     (exit 1 if a check fails)
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audiolib as AL  # noqa: E402


def band(x, sr, lo, hi):
    b, a = signal.butter(4, [lo / (sr / 2), min(hi, sr / 2 * 0.95) / (sr / 2)], "band")
    return signal.filtfilt(b, a, x)


def env_db(x, sr, win=0.1):
    n = int(win * sr)
    k = len(x) // n
    y = x[: k * n].reshape(k, n)
    return 20 * np.log10(np.sqrt(np.mean(y ** 2, axis=1)) + 1e-12)


def onset_after(m, sr, t, lo=1500, hi=9000):
    x = band(m, sr, lo, hi)
    e = env_db(x, sr, 0.005)
    i0 = int(t / 0.005)
    base = np.median(e[max(0, i0 - 40): i0]) if i0 > 5 else np.min(e)
    for i in range(i0, min(len(e), i0 + 200)):
        if e[i] > base + 10:
            return i * 0.005
    return None


def self_corr(m, sr, lags):
    w = int(0.5 * sr)
    out = []
    for L in lags:
        Ls = int(L * sr)
        v = []
        for s0 in range(0, len(m) - Ls - w, w):
            a, c = m[s0: s0 + w], m[s0 + Ls: s0 + Ls + w]
            v.append(np.dot(a, c) / np.sqrt(np.dot(a, a) * np.dot(c, c) + 1e-30))
        out.append((L, float(np.median(v)) if v else 0.0))
    return out


def steady_start(m, sr):
    n = sr
    k = len(m) // n
    lv = 20 * np.log10(np.sqrt(np.mean(m[: k * n].reshape(k, n) ** 2, axis=1)) + 1e-12)
    med = np.median(lv[lv > -100]) if np.any(lv > -100) else -100
    return float(int(np.argmax(lv > med - 6)) + 2)


def fast(e, n=31):
    from scipy import ndimage
    return e - ndimage.median_filter(e, n)


def main():
    d = Path(sys.argv[1])
    plans = sys.argv[2:] or sorted(p.stem for p in d.glob("*.wav"))
    fails, rep = [], {}
    for plan in plans:
        w = d / f"{plan}.wav"
        if not w.exists():
            continue
        sr, x = AL.read(w)
        keys = json.loads((d / f"{plan}_keys.json").read_text()) if (d / f"{plan}_keys.json").exists() else {"events": []}
        m = AL.mono(x)
        t0 = steady_start(m, sr) if plan not in ("menu", "gallery") else 0.0
        x, m = x[int(t0 * sr):], m[int(t0 * sr):]
        L = AL.loudness(x, sr)
        tp = AL.true_peak_db(x)
        st = L["short_term"]
        jumps = [[i + 1, round(st[i + 1] - st[i], 1)] for i in range(len(st) - 1) if st[i] > -60 and abs(st[i + 1] - st[i]) > 6.0]
        r = {"steady_from_s": t0, "seconds": round(len(x) / sr, 1), "lufs": round(L["integrated"], 1), "true_peak_db": round(tp, 2),
             "short_term_max": round(L["max_short_term"], 1), "jumps_over_6lu": jumps}
        if tp > -1.0:
            fails.append(f"{plan}: true peak {tp:.2f} dBTP")
        if plan in ("home", "brook", "vista", "lookout", "approach", "night") and not (-26.0 <= L["integrated"] <= -22.0):
            fails.append(f"{plan}: integrated {L['integrated']:.1f} LUFS outside -24 +-2")
        if plan in ("brook_rain", "rain") and not (-26.0 <= L["integrated"] <= -20.0):
            # weather may sit up to 4 LU above the reference, never more (the voices and her steps stay on top)
            fails.append(f"{plan}: integrated {L['integrated']:.1f} LUFS outside -26..-20 (weather)")
        if plan == "menu":
            lat = []
            for ev in keys["events"]:
                t = ev["frame"] / keys.get("fps", 30)
                o = onset_after(m, sr, t)
                lat.append(None if o is None else round(o - t, 3))
            r["key_to_sound_s"] = lat
            for v in lat:
                if v is None or v > 0.1:
                    fails.append(f"menu: key to sound {v} s")
        marks = {}
        plays = d / f"{plan}_plays.jsonl"
        if plays.exists():
            for l in plays.read_text().splitlines():
                if l.strip():
                    ms, sid, v = json.loads(l)
                    if str(sid).startswith("_"):
                        marks.setdefault(sid, []).append((ms, v))
        if plan == "gallery" and "_rec" in marks and "_duck" in marks:
            # the dialogue's own duck calls (StoryUI.say / _finish, logged by Audio.duck) on the recording's clock;
            # the air (the wind, 80-300 Hz) averaged in power over everything before and everything under it (its
            # gusts swing it +-3 dB over a few seconds: short windows cannot see a 4 dB duck)
            r0 = marks["_rec"][0][0]
            on = [(ms - r0) / 1000.0 for ms, v in marks["_duck"] if v > 0]
            off = [(ms - r0) / 1000.0 for ms, v in marks["_duck"] if v == 0 and on and (ms - r0) / 1000.0 > on[0]]
            t1, t2 = on[0], (off[0] if off else len(m) / sr)
            low = band(m, sr, 80, 300)
            pw = lambda a, b: 10 * np.log10(np.mean(low[int(a * sr): int(b * sr)] ** 2) + 1e-20)
            before, during = pw(2.0, t1 - 0.2), pw(t1 + 0.6, t2 - 0.2)
            r["dialogue_s"], r["air_before_db"], r["air_under_dialogue_db"] = [round(t1, 2), round(t2, 2)], round(before, 1), round(during, 1)
            r["duck_db"] = round(during - before, 1)
            if not (-6.5 <= during - before <= -1.5):
                fails.append(f"{plan}: the air ducked {during - before:.1f} dB under the dialogue (want about -4)")
        if plan.startswith("brook"):
            sc = self_corr(m, sr, [0.25, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20])
            worst = max(sc, key=lambda v: v[1])
            r["self_corr"] = [[a, round(b, 3)] for a, b in sc]
            if worst[1] > 0.15:
                fails.append(f"brook: the mix repeats (self-correlation {worst[1]:.2f} at {worst[0]} s)")
            wind = fast(env_db(band(m, sr, 100, 400), sr, 0.1))
            water = fast(env_db(band(m, sr, 6000, 10000), sr, 0.1))
            c = float(np.corrcoef(wind, water)[0, 1])
            dip = 2.0 * c * float(np.std(water))   # the slope (c sd_water / sd_wind) times two sd of the wind
            r["water_vs_wind_fast_corr"], r["water_dip_per_gust_db"] = round(c, 3), round(dip, 2)
            if dip < -0.5:
                fails.append(f"{plan}: the water dips {dip:.2f} dB when the wind swells (pumping)")
        if plays.exists():
            rows = [json.loads(l) for l in plays.read_text().splitlines() if l.strip()]
            rows = [q for q in rows if not str(q[1]).startswith("_")]
            by = {}
            for _, sid, vi in rows:
                by.setdefault(sid, []).append(vi)
            sounds = json.loads((HERE.parent.parent / "godot" / "audio" / "sounds.json").read_text())["sounds"]
            var = {}
            for sid, seq in by.items():
                n = len(sounds.get(sid, {}).get("files", [])) or 1
                nrep = sum(1 for a, b in zip(seq, seq[1:]) if a == b)
                share = max(seq.count(v) for v in set(seq)) / len(seq)
                var[sid] = {"plays": len(seq), "variants": n, "repeats": nrep, "max_share": round(share, 3)}
                if n > 1 and nrep and not sid.startswith("blip_"):
                    fails.append(f"{plan}: {sid} played the same variant twice running ({nrep} times)")
                if n > 1 and len(seq) >= 2 * n and share > 2.0 / n:
                    fails.append(f"{plan}: {sid} variant share {share:.2f} > 2/{n}")
            r["plays"] = var
        rep[plan] = r
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    for f in fails:
        print("FAIL", f)
    (d / "check_mix.json").write_text(json.dumps({"report": rep, "fails": fails}, ensure_ascii=False, indent=1))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
