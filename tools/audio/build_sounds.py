"""Builds the game's sounds from their recipes (tools/audio/sound_spec.py): renders the v0.1 synthesizer
offline (tools/audio/v01/render.mjs, headless Chromium), cuts the renders into one-shots, loops and pieces,
and writes them under godot/audio/ with two manifests:
  godot/audio/sounds.json   what the game loads (ids, files, loops, levels, jitter)
  godot/audio/SOURCES.json  where every file came from (generator, engine and renderer hashes, the job with
                            its seed and parameters, the cutting steps, the file's hash and measurements)
No recording and no sample is involved anywhere (G5R3-53, G5R3-65).

  python3 -I tools/audio/build_sounds.py --scratch DIR [--only id,id] [--no-render] [--clean]
Renders are cached in DIR by a key of (job, engine source, renderer source): only changed jobs render again.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import audiolib as AL  # noqa: E402
import sound_spec  # noqa: E402

GODOT_AUDIO = ROOT / "godot" / "audio"
ENGINE = ROOT / "src" / "audio" / "audio.js"
RENDERER = HERE / "v01" / "render.mjs"
SR = AL.SR
# the shortest and most frequent one-shots stay PCM (Godot compresses them to QOA on import; no codec smear on
# their attacks); the longer ones (creatures, verbs, stingers, the story's moments, weather) are Ogg Vorbis
WAV_GROUPS = {"step", "ui", "voice", "saji", "body"}


def job_key(job, eng_sha, ren_sha):
    return AL.hashlib.sha256((json.dumps(job, sort_keys=True) + eng_sha + ren_sha).encode()).hexdigest()[:24]


def render_all(assets, scratch, only):
    eng_sha, ren_sha = AL.sha256(ENGINE), AL.sha256(RENDERER)
    pending = []
    for a in assets:
        if only and a["id"] not in only:
            continue
        for i, j in enumerate(a["jobs"]):
            name = f"{a['id']}__{i:02d}"
            job = dict(j, name=name)
            key = job_key({k: v for k, v in job.items() if k != "name"}, eng_sha, ren_sha)
            kf = scratch / (name + ".key")
            if (scratch / (name + ".f32.wav")).exists() and kf.exists() and kf.read_text() == key:
                continue
            pending.append((job, key))
    if pending:
        jf = scratch / "pending_jobs.json"
        jf.write_text(json.dumps([j for j, _ in pending]))
        print(f"rendering {len(pending)} jobs ...", flush=True)
        subprocess.run(["node", str(RENDERER), str(jf), str(scratch)], check=True)
        for job, key in pending:
            if (scratch / (job["name"] + ".f32.wav")).exists():
                (scratch / (job["name"] + ".key")).write_text(key)
    return eng_sha, ren_sha


def render_logs(scratch):
    logs = {}
    p = scratch / "render_log.jsonl"
    if p.exists():
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            logs[r["name"]] = r          # the last render of a name wins
    return logs


def pink_noise(seconds, seed):
    """v0.1's pink noise (Paul Kellet's economy filter, makeNoise 'pink'), independent per channel."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = np.zeros((n, 2))
    for c in range(2):
        w = rng.random(n) * 2 - 1
        b0 = b1 = b2 = 0.0
        y = np.empty(n)
        # vectorised as three one-pole filters (same coefficients as makeNoise)
        from scipy.signal import lfilter
        p0 = lfilter([0.099046], [1, -0.99765], w)
        p1 = lfilter([0.2965164], [1, -0.963], w)
        p2 = lfilter([1.0526913], [1, -0.57], w)
        y = (p0 + p1 + p2 + w * 0.1848) * 0.2
        out[:, c] = y
    return out


def highpass(x, hz=25.0):
    """Zero-phase 2nd-order high-pass: no DC, no infrasonic drift (the pink noise's one-pole filters wander)."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(2, hz / (SR / 2), "highpass", output="sos")
    return sosfiltfilt(sos, x, axis=0)


def vary(x, seed, amount, tilt_db):
    """One variant made a little different from its siblings (for sounds v0.1 made the same each time): played a
    little faster or slower (pitch and length together, like a different strike, +-amount) and a gentle tilt of
    its colour (+-tilt_db above 2 kHz). Seeded: the same recipe always gives the same file."""
    from scipy.signal import resample, lfilter
    rng = np.random.default_rng(seed)
    r = 1.0 + amount * (2 * rng.random() - 1)
    n = max(8, int(round(len(x) / r)))
    y = resample(x, n, axis=0)
    g = 10 ** ((tilt_db * (2 * rng.random() - 1)) / 20)
    # first-order high shelf at 2 kHz: y + (g - 1) * HP(y)
    k = np.exp(-2 * np.pi * 2000 / SR)
    hp = lfilter([(1 + k) / 2, -(1 + k) / 2], [1, -k], y, axis=0)
    return y + (g - 1) * hp, r, 20 * np.log10(g)


def level_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-12))


def post(asset, scratch, logs, eng_sha, ren_sha, sources, sounds):
    aid, kind, group = asset["id"], asset["kind"], asset.get("group", "")
    mono = asset.get("mono", False)
    files = []
    base_src = {"generator": "v0.1 synthesizer, src/audio/audio.js (ported from legacy/v0.1/src/audio.js), rendered offline by tools/audio/v01/render.mjs in headless Chromium",
                "engine_sha256": eng_sha, "renderer_sha256": ren_sha}
    if kind == "noise":
        nz = asset["noise"]
        x = pink_noise(nz["seconds"] + 4.0, nz["seed"])
        x = highpass(x)
        x = AL.make_loop(x, 2.0, nz["seconds"], 1.0, power=True)
        x -= np.mean(x, axis=0)
        x *= 0.125 / np.sqrt(np.mean(x ** 2))  # -18 dBFS RMS (the bus filters and gains set the level)
        out = GODOT_AUDIO / "amb" / f"{aid}.ogg"
        AL.write_ogg(out, x, quality=6, tmp_dir=scratch)
        files.append(out)
        sources[str(out.relative_to(ROOT / "godot"))] = dict(generator="numpy: v0.1's pink-noise filter (makeNoise 'pink') on seeded white noise, tools/audio/build_sounds.py pink_noise",
                                                             recipe=nz, post=["high-pass 25 Hz", "seamless loop: 1.0 s equal-power cross-fade", "DC removed", "RMS -18 dBFS", "Ogg Vorbis q6"])
    for i, job in enumerate(asset["jobs"]):
        name = f"{aid}__{i:02d}"
        src = scratch / (name + ".f32.wav")
        if not src.exists():
            raise SystemExit(f"missing render {src}")
        _, x = AL.read(src)
        x = highpass(x)
        steps = ["high-pass 25 Hz (no DC or infrasonic)"]
        lg = logs.get(name, {})
        if kind == "oneshot":
            s0 = max(0, int((job.get("at", 0.05)) * SR) - int(0.004 * SR))
            if job.get("type") == "event":
                s0 = max(0, AL.onset(x, -75) - int(0.004 * SR))
            x = x[s0:]
            floor = max(-80.0, AL.peak_db(x) - 60.0)
            x = AL.trim_tail(x, floor, 0.12)
            steps += [f"cut at {s0 / SR:.3f} s", f"tail trimmed below {floor:.1f} dBFS (60 dB under its peak, at most -80; +0.12 s)"]
            V = asset.get("vary")
            if V:
                x, r, tdb = vary(x, job["seed"] + 17, V[0], V[1])
                steps.append(f"variant: played at {r:.4f}x (pitch and length), colour {tdb:+.2f} dB above 2 kHz")
            x = AL.fade(x, 0.002, 0.02)
            steps.append("fades 2 ms in, 20 ms out")
        elif kind == "loop":
            L = asset["loop"]
            s_i, n_ = int(round(L["start"] * SR)), int(0.05 * SR)
            seam_orig = level_db(x[s_i: s_i + n_]) - level_db(x[s_i - n_: s_i])
            x = AL.make_loop(x, L["start"], L["period"], L["xfade"], power=L.get("power", True))
            seam_loop = level_db(x[:n_]) - level_db(x[-n_:])
            steps += [f"loop {L['start']:.3f} s + {L['period']:.4f} s, {L['xfade']} s {'equal-power' if L.get('power', True) else 'equal-gain'} cross-fade from the pre-roll"]
        elif kind == "piece":
            P = asset["piece"]
            segs = [r for r in lg.get("logs", []) if r and r[0] == "seg"]
            if P.get("oneshot"):
                t0 = segs[0][3] if segs else 0.15
                s0 = max(0, int(t0 * SR) - int(0.01 * SR))
                x = x[s0:]
                x = AL.trim_tail(x, -78.0, 0.2)
                x = AL.fade(x, 0.005, 0.15)
                steps += [f"from the first section ({t0:.3f} s)", "tail trimmed below -78 dBFS", "fades 5 ms in, 150 ms out"]
            else:
                a, b = P["loop_sections"]
                starts = {int(r[2]): float(r[3]) for r in segs}
                if b not in starts:                     # the section after the loop never started: its start = last + beats
                    last = max(starts)
                    lr = [r for r in segs if int(r[2]) == last][-1]
                    starts[b] = float(lr[3]) + float(lr[4]) * 60.0 / float(lr[5])
                ts, te = starts[a], starts[b]
                s_i, n_ = int(round(ts * SR)), int(0.05 * SR)
                seam_orig = level_db(x[s_i: s_i + n_]) - level_db(x[s_i - n_: s_i])
                x = AL.make_loop(x, ts, te - ts, P.get("xfade", 0.25), power=False)
                seam_loop = level_db(x[:n_]) - level_db(x[-n_:])
                bpm = float([r for r in segs if int(r[2]) == a][0][5])
                beats = round((te - ts) * bpm / 60.0, 3)
                asset.setdefault("meta", {}).update({"bpm": bpm, "beats": beats})
                steps += [f"loop sections {a}..{b - 1}: {ts:.4f} s + {te - ts:.4f} s ({beats} beats at {bpm} bpm), equal-gain cross-fade {P.get('xfade', 0.25)} s"]
        if mono and x.shape[1] == 2:
            x = x.mean(axis=1, keepdims=True)
            steps.append("mixed to mono (placed in 3D by the game)")
        tp = AL.true_peak_db(x)
        gain = 0.0
        if tp > -1.0:
            gain = -1.0 - tp
            x = x * 10 ** (gain / 20)
            steps.append(f"gain {gain:+.2f} dB (true peak to -1 dBTP; the game adds it back as volume)")
        if kind == "oneshot" and group in WAV_GROUPS:
            out = GODOT_AUDIO / "sfx" / group / (f"{aid}_{i + 1:02d}.wav")
            AL.write_wav16(out, x, dither_seed=job["seed"])
            steps.append("16-bit PCM WAV, TPDF dither (Godot imports it as QOA)")
        elif kind == "oneshot":
            out = GODOT_AUDIO / "sfx" / group / (f"{aid}_{i + 1:02d}.ogg")
            AL.write_ogg(out, x, quality=6, tmp_dir=scratch)
            steps.append("Ogg Vorbis q6")
        else:
            sub = "music" if group == "music" else ("amb" if group == "bed" else "festival")
            nm = f"{aid}_{i + 1:02d}.ogg" if (kind == "piece" and asset["piece"].get("phrase")) else f"{aid}.ogg"
            out = GODOT_AUDIO / sub / nm
            AL.write_ogg(out, x, quality=6, tmp_dir=scratch)
            steps.append("Ogg Vorbis q6")
        files.append(out)
        rel = str(out.relative_to(ROOT / "godot"))
        sources[rel] = dict(base_src, id=aid, job={k: v for k, v in job.items() if k != "name"}, post=steps,
                            seconds=round(len(x) / SR, 3), gain_db=round(gain, 2), sha256=AL.sha256(out))
        if kind == "loop" or (kind == "piece" and not asset["piece"].get("oneshot")):
            # the wrap must sound like the music did at that point of the render (a downbeat after a rest is a
            # jump in level there too): the 50 ms level step across the seam, in the render and in the loop
            sources[rel]["seam_db"] = {"render": round(seam_orig, 2), "loop": round(seam_loop, 2)}
        if gain:
            asset.setdefault("gains", {})[rel] = round(gain, 2)
    entry = {"kind": kind, "group": group, "mono": mono, "files": ["res://" + str(f.relative_to(ROOT / "godot")) for f in files]}
    if asset.get("measure_f0"):
        # each variant's pitch (the bell cricket's trill): the game never runs two within 60 Hz at once (rule 4)
        lo, hi = asset["measure_f0"]
        f0s = []
        for f in files:
            _, y = AL.read(f) if f.suffix == ".wav" else AL.decode(f)
            m = AL.mono(y)
            spec = np.abs(np.fft.rfft(m * np.hanning(len(m))))
            fr = np.fft.rfftfreq(len(m), 1 / SR)
            band = (fr >= lo) & (fr <= hi)
            f0s.append(round(float(fr[band][np.argmax(spec[band])]), 1))
        entry["f0"] = f0s
    if asset.get("loop") or (kind == "piece" and not asset["piece"].get("oneshot")) or kind == "noise":
        entry["loop"] = True
    entry.update(asset.get("meta", {}))
    if asset.get("gains"):
        entry["gain_db"] = {("res://" + k): v for k, v in asset["gains"].items()}
    sounds[aid] = entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--clean", action="store_true", help="remove godot/audio/{sfx,amb,music,festival} first")
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    assets = sound_spec.assets()
    if a.clean and not only:
        for d in ["sfx", "amb", "music", "festival"]:
            shutil.rmtree(GODOT_AUDIO / d, ignore_errors=True)
    if a.no_render:
        eng_sha, ren_sha = AL.sha256(ENGINE), AL.sha256(RENDERER)
    else:
        eng_sha, ren_sha = render_all(assets, scratch, only)
    logs = render_logs(scratch)
    src_path, snd_path = GODOT_AUDIO / "SOURCES.json", GODOT_AUDIO / "sounds.json"
    sources = json.loads(src_path.read_text()).get("files", {}) if (only and src_path.exists()) else {}
    sounds = json.loads(snd_path.read_text()).get("sounds", {}) if (only and snd_path.exists()) else {}
    for asset in assets:
        if only and asset["id"] not in only:
            continue
        post(asset, scratch, logs, eng_sha, ren_sha, sources, sounds)
        print("built", asset["id"], flush=True)
    about = ("Every sound and every piece of music here is synthesized: the v0.1 synthesizer (pure WebAudio, no "
             "samples) rendered offline, cut and encoded by tools/audio/build_sounds.py. No recording and no "
             "instrument sample is used (G5R3-53, G5R3-65). Rebuild: python3 -I tools/audio/build_sounds.py --scratch DIR")
    src_path.write_text(json.dumps({"_about": about, "files": dict(sorted(sources.items()))}, ensure_ascii=False, indent=1) + "\n")
    snd_path.write_text(json.dumps({"_about": "Loaded by godot/core/audio.gd. Built by tools/audio/build_sounds.py from tools/audio/sound_spec.py.",
                                    "version": 1, "sounds": dict(sorted(sounds.items()))}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(sounds)} sounds, {len(sources)} files")


if __name__ == "__main__":
    main()
