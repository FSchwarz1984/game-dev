#!/usr/bin/env python3
"""Build the field-recording ambience assets (assets/audio/*.mp3) from CC0 / public-domain sources.

    python3 -I tools/audio/build_field.py                 # download missing sources, rebuild every asset
    python3 -I tools/audio/build_field.py night wind      # rebuild a subset
    python3 -I tools/audio/build_field.py --preview DIR   # build into DIR; the repo is not touched
    python3 -I tools/audio/build_field.py --ccby          # ALSO build the CC BY higurashi layers (dusk,
                                                          # higu): only after the user approves crediting
                                                          # the recordists (CC BY 4.0 needs attribution)

Every source in SRC is CC0 or public domain; CCBY_SRC (used only with --ccby) is CC BY 4.0. See
docs/knowledge/07-audio-sources.md for the search, the rejected candidates and the licence decision. The script records the exact edits in
assets/audio/manifest.json and rewrites the generated META block in src/audio/field.js, so the loop
points and sprite offsets the engine uses always match the files.

Method (per asset):
  beds    decode -> channel choice -> filters (ffmpeg) -> seamless loop: the last X seconds of the
          segment are crossfaded (equal power) into its head, so sample L-1 runs straight into sample 0
          -> padded with P seconds of periodic extension on both sides (so a decoder that keeps or drops
          the ~25 ms MP3 encoder delay still loops cleanly between loopStart=P and loopEnd=P+L)
          -> loudness normalised (EBU R128 integrated) -> mono MP3, CBR, 44.1 kHz.
  events  decode -> filters, light FFT denoise -> fades -> loudness normalised -> packed into one
          sprite file per family with silent gaps; field.js plays [start, dur] slices.

Needs: ffmpeg (with libmp3lame, libsoxr), numpy. Downloads use the proxy CA bundle when present.
"""
import json, os, re, ssl, subprocess, sys, time, urllib.request

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "audio")
FIELD_JS = os.path.join(ROOT, "src", "audio", "field.js")
CACHE = os.environ.get("AUDIO_CACHE", "/tmp/field-audio-cache")
SR = 44100
PAD = 0.25  # seconds of periodic extension on each side of a loop
UA = "TenganAmbienceBuild/1.0 (CC0 field-recording asset build)"

# --------------------------------------------------------------------------------------------------
# Sources. 'file' is the cache path (relative to CACHE), 'url' the direct download, 'page' the human
# page that states the licence. Licence strings are copied from those pages.
# --------------------------------------------------------------------------------------------------
SRC = {
    "akiyoshidai": dict(
        file="ia/aporee_65285_75402/akiyioshidai.flac",
        url="https://archive.org/download/aporee_65285_75402/akiyioshidai.flac",
        page="https://archive.org/details/aporee_65285_75402",
        title="773V+27 Mine, Yamaguchi, Japan - Night in Akiyoshidai (radio aporee ::: maps)",
        author="thomasmartinnutt", licence="Public Domain Mark 1.0",
        licence_url="https://creativecommons.org/publicdomain/mark/1.0/",
        recorded="2018-10-18 01:00 JST, forest near Akiyoshidai, Mine, Yamaguchi, Japan"),
    "miuda": dict(
        file="ia/aporee_65627_75795/Miudainsectnightlifelonggrassaporee.mp3",
        url="https://archive.org/download/aporee_65627_75795/Miudainsectnightlifelonggrassaporee.mp3",
        page="https://archive.org/details/aporee_65627_75795",
        title="Miuda insect nightlife_long grass (radio aporee ::: maps)",
        author="abyssence", licence="Public Domain Mark 1.0",
        licence_url="https://creativecommons.org/publicdomain/mark/1.0/",
        recorded="2024-09-30 23:20 JST, long grass at Miuda, Tsushima, Nagasaki, Japan"),
    "bsb0659": dict(
        file="bsb/0659/0659.mp3", url="https://bigsoundbank.com/UPLOAD/mp3/0659.mp3",
        page="https://bigsoundbank.com/wind-in-a-tree-s0659.html",
        title="Wind in a Tree (BigSoundBank #0659)", author="Joseph SARDIN", licence="CC0 1.0",
        licence_url="https://creativecommons.org/publicdomain/zero/1.0/", recorded="France"),
    "bsb1354": dict(
        file="bsb/1354/1354.ogg", url="https://bigsoundbank.com/UPLOAD/ogg/1354.ogg",
        page="https://bigsoundbank.com/small-stream-4-s1354.html",
        title="Small Stream #4 (BigSoundBank #1354)", author="Joseph SARDIN", licence="CC0 1.0",
        licence_url="https://creativecommons.org/publicdomain/zero/1.0/", recorded="France, a small mountain stream"),
    "bsb0219": dict(
        file="bsb/0219/0219.ogg", url="https://bigsoundbank.com/UPLOAD/ogg/0219.ogg",
        page="https://bigsoundbank.com/small-waterfall-2-s0219.html",
        title="Small waterfall #2 (BigSoundBank #0219)", author="gamin", licence="CC0 1.0",
        licence_url="https://creativecommons.org/publicdomain/zero/1.0/",
        recorded="France, a few metres above a small mountain waterfall"),
}

def inat(key, taxon, sid, ext, obs, user, place, date, species):
    SRC[key] = dict(
        file=f"inat/{taxon}/{sid}.{ext}", url=f"https://static.inaturalist.org/sounds/{sid}.{ext}",
        page=f"https://www.inaturalist.org/observations/{obs}",
        title=f"{species}, iNaturalist observation {obs} (sound {sid})", author=user,
        licence="CC0 1.0", licence_url="https://creativecommons.org/publicdomain/zero/1.0/",
        recorded=f"{date}, {place}")

inat("crow_kyoto", "Corvus_macrorhynchos", 1247228, "wav", 250986351, "funnieanimals", "Kyoto, Japan", "2024-11-09", "Large-billed crow (Corvus macrorhynchos)")
inat("crow_okinawa", "Corvus_macrorhynchos", 1718844, "m4a", 331178834, "islander_iskander", "Okinawa, Japan", "2025-12-18", "Large-billed crow (Corvus macrorhynchos)")
inat("bul_ueda", "Hypsipetes_amaurotis", 394003, "mp3", 111523106, "konoda", "Ueda, Nagano, Japan", "2022-04-15", "Brown-eared bulbul (Hypsipetes amaurotis)")
inat("bul_ota", "Hypsipetes_amaurotis", 836234, "wav", 188787166, "kalvinchan", "Ota City, Tokyo, Japan", "2023-10-24", "Brown-eared bulbul (Hypsipetes amaurotis)")
inat("tit_setagaya", "Parus_minor", 1915066, "wav", 356867013, "quercus_e", "Setagaya, Tokyo, Japan", "2026-04-18", "Japanese tit (Parus minor)")
inat("tit_sagamihara", "Parus_minor", 1998102, "mp3", 367885458, "bko98212", "Sagamihara, Kanagawa, Japan", "2026-05-10", "Japanese tit (Parus minor)")
inat("ugu_kyoto", "Horornis_diphone", 964225, "m4a", 206776175, "ahikar", "Nakagyo Ward, Kyoto, Japan", "2024-04-12", "Japanese bush warbler (Horornis diphone)")
inat("ugu_fujisawa", "Horornis_diphone", 1998112, "mp3", 367885761, "bko98212", "Fujisawa, Kanagawa, Japan", "2026-05-12", "Japanese bush warbler (Horornis diphone)")

# --------------------------------------------------------------------------------------------------
# Assets. Beds: src, chan (mix|L|R|diff), start, L (loop length), X (crossfade), af (ffmpeg filters),
# lufs (integrated target), kbps. Events: segs = (name, src, t0, t1, af, fade_in, fade_out).
# --------------------------------------------------------------------------------------------------
HP = lambda f: f"highpass=f={f}:p=2,highpass=f={f}:p=2"  # 4th-order (24 dB/oct) high-pass
LP = lambda f: f"lowpass=f={f}:p=2,lowpass=f={f}:p=2"     # 4th-order low-pass
BEDS = {
    # Night insects, Japan, October: a 4 kHz trilling chorus plus chirps at 2.6 and 4.5-5 kHz.
    # The two channels are anti-correlated (r = -0.55; summing cancels 5-11 dB), so the mono is (L-R)/2.
    "night": dict(src="akiyoshidai", chan="diff", start=95.0, L=30.0, X=3.0, af=HP(150), lufs=-23, kbps=64),
    # Night insects, Japan, late September: denser katydid band at 7.5-9 kHz and pulsed 5 kHz calls.
    "night2": dict(src="miuda", chan="mix", start=300.0, L=20.0, X=2.5, af=HP(300), lufs=-23, kbps=64),
    # Wind gusts through the leaves of one large tree (lulls and swells about every 8-10 s).
    "wind": dict(src="bsb0659", chan="mix", start=85.0, L=27.5, X=2.5, af=HP(70), lufs=-23, kbps=64, detonal=True),
    # A small mountain stream, close: bubbles and droplets up to 16 kHz over a body below 2.5 kHz.
    "stream": dict(src="bsb1354", chan="L", start=47.6, L=20.0, X=2.0, af=HP(80), lufs=-23, kbps=80),
    # A small waterfall, recorded close; field.js adds the distance (low-pass, level, room).
    # Pre-filtered to 8 kHz: it is never heard close, and the encoder spends the bits below.
    "fall": dict(src="bsb0219", chan="mix", start=2.0, L=16.0, X=2.0, af=HP(60) + ",lowpass=f=8000:p=2", lufs=-23, kbps=64),
}
NR = "afftdn=nr=10:nf=-50:tn=1"
EVENTS = {
    "crow": dict(lufs=-18, kbps=64, segs=[
        ("crow_a", "crow_kyoto", 0.05, 2.32, HP(250) + "," + LP(8000) + "," + NR, 0.02, 0.12),
        ("crow_b", "crow_okinawa", 0.40, 2.02, HP(300) + "," + LP(8000) + "," + NR, 0.02, 0.12),
    ]),
    "birds": dict(lufs=-18, kbps=64, segs=[
        ("bulbul_a", "bul_ueda", 0.15, 2.78, HP(1200) + "," + NR, 0.02, 0.15),
        ("bulbul_b", "bul_ota", 7.85, 9.70, HP(1500) + "," + NR, 0.02, 0.15),
        ("tit_a", "tit_setagaya", 2.95, 5.78, HP(2500) + "," + NR, 0.02, 0.12),
        ("tit_b", "tit_sagamihara", 0.12, 2.88, HP(3000) + "," + NR, 0.02, 0.12),
        ("ugu_a", "ugu_kyoto", 7.60, 9.62, HP(800) + "," + NR, 0.03, 0.15),
        ("ugu_b", "ugu_fujisawa", 7.10, 9.30, HP(1000) + "," + NR, 0.03, 0.15),
        ("ugu_c", "ugu_fujisawa", 17.40, 20.00, HP(900) + "," + NR, 0.03, 0.15),
    ]),
}
# --------------------------------------------------------------------------------------------------
# CC BY 4.0 layers (higurashi, the evening cicada). No CC0 / public-domain recording of Tanna japonensis
# was found (docs/knowledge/07-audio-sources.md). Built only with --ccby; the credit line is in
# manifest.json ("attribution"). Without them the engine keeps its synthesized higurashi.
# --------------------------------------------------------------------------------------------------
CCBY_SRC = {
    "higu_nasu": dict(
        file="inat/Tanna_japonensis/1590381.m4a", url="https://static.inaturalist.org/sounds/1590381.m4a",
        page="https://www.inaturalist.org/observations/303075754",
        title="Higurashi (Tanna japonensis), iNaturalist observation 303075754 (sound 1590381)",
        author="Yoshihiro Tokue (tokue)", licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
        recorded="2025-08-02 18:12 JST, Nasu, Tochigi, Japan"),
    "higu_sendai": dict(
        file="inat/Tanna_japonensis/782217.m4a", url="https://static.inaturalist.org/sounds/782217.m4a",
        page="https://www.inaturalist.org/observations/175909347",
        title="Higurashi (Tanna japonensis), iNaturalist observation 175909347 (sound 782217)",
        author="Timur Kalininsky (timur_kalininsky)", licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
        recorded="2023-07-29 16:43 JST, Aoba Ward, Sendai, Miyagi, Japan"),
}
CCBY_BEDS = {
    # A higurashi chorus: overlapping "kana-kana-kana" phrases (4.3 kHz with harmonics), several individuals.
    "dusk": dict(src="higu_nasu", chan="mix", start=0.5, L=30.0, X=3.0, af=HP(1200), lufs=-23, kbps=64),
}
CCBY_EVENTS = {
    "higu": dict(lufs=-18, kbps=64, segs=[
        ("higu_a", "higu_sendai", 10.55, 13.65, HP(1500) + "," + NR, 0.15, 0.6),
        ("higu_b", "higu_sendai", 15.55, 19.40, HP(1500) + "," + NR, 0.3, 0.8),
    ]),
}

# Sub-slices of a sprite segment that field.js may also play alone: (name, parent, t0, t1) in seconds
# relative to the parent's start (single caws out of a three-caw call).
SUBS = {
    "crow": [("crow_a1", "crow_a", 0.0, 0.80), ("crow_a3", "crow_a", 1.58, 2.27),
             ("crow_b1", "crow_b", 0.0, 0.45), ("crow_b2", "crow_b", 0.58, 1.02)],
}
GAP = 0.45      # silence between sprite segments
MARGIN = 0.15   # silence before the first and after the last segment

# --------------------------------------------------------------------------------------------------
def fetch(key):
    s = SRC.get(key) or CCBY_SRC[key]; path = os.path.join(CACHE, s["file"])
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ca = "/root/.ccr/ca-bundle.crt"
    ctx = ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()
    print(f"  downloading {s['url']}")
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(s["url"], headers={"User-Agent": UA}), context=ctx, timeout=600) as r:
                data = r.read()
            open(path, "wb").write(data); return path
        except Exception as e:  # noqa: BLE001 - retry any transport error
            print(f"  retry {i + 1}: {e}"); time.sleep(3 * (i + 1))
    raise SystemExit(f"cannot download {s['url']}")

def decode(path, start, dur, af, chan):
    """Decode [start, start+dur) as float32 mono at 44.1 kHz. Filters run with 1 s of pre-roll."""
    pre = min(1.0, start)
    chain = f"aresample={SR}:resampler=soxr,{af}" if af else f"aresample={SR}:resampler=soxr"
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start - pre:.6f}", "-t", f"{dur + pre + 0.5:.6f}", "-i", path,
           "-af", chain, "-ac", "2", "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).astype(np.float64)
    x = {"mix": x.mean(1), "L": x[:, 0], "R": x[:, 1], "diff": (x[:, 0] - x[:, 1]) / 2}[chan]
    i0 = int(round(pre * SR)); n = int(round(dur * SR))
    if len(x) < i0 + n:
        raise SystemExit(f"{path}: segment {start}+{dur}s runs past the end")
    return x[i0:i0 + n]

def ffmpeg_filter_mono(x, af):
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af, "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, input=x.astype(np.float32).tobytes(), capture_output=True, check=True).stdout, np.float32).astype(np.float64)

def lufs(x):
    """EBU R128 integrated loudness and true peak (ffmpeg ebur128)."""
    cmd = ["ffmpeg", "-nostats", "-v", "info", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]
    err = subprocess.run(cmd, input=x.astype(np.float32).tobytes(), capture_output=True).stderr.decode()
    summ = err[err.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    tp = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", summ)
    return I, (float(tp.group(1)) if tp else None)

def detonal(x, f0=1500.0, f1=10000.0, thr_db=6.0, n=1024, hop=256):
    """Spectral repair for noise-like beds: in [f0, f1] any time-frequency cell more than thr_db above
    the local median (separable: +-8 frames, then +-4 bins) is pulled down to that limit, phase kept.
    Removes faint bird chips and ticks from wind; on plain noise it touches about 1-2 % of cells."""
    w = np.hanning(n + 1)[:n]
    padn = n
    xp = np.concatenate([np.zeros(padn), x, np.zeros(padn)])
    idx = np.arange(n)[None, :] + hop * np.arange((len(xp) - n) // hop + 1)[:, None]
    X = np.fft.rfft(xp[idx] * w, axis=1)
    f = np.fft.rfftfreq(n, 1 / SR); band = (f >= f0) & (f <= f1)
    M = np.abs(X[:, band])
    def med(a, k, axis):
        pad = [(0, 0), (0, 0)]; pad[axis] = (k, k)
        v = np.lib.stride_tricks.sliding_window_view(np.pad(a, pad, mode="edge"), 2 * k + 1, axis=axis)
        return np.median(v, axis=-1)
    ref = med(med(M, 8, 0), 4, 1)
    lim = ref * 10 ** (thr_db / 20)
    g = np.minimum(1.0, lim / np.maximum(M, 1e-12))
    X[:, band] *= g
    y = np.fft.irfft(X, n, axis=1) * w
    out = np.zeros(len(xp)); norm = np.zeros(len(xp))
    for i, r in enumerate(idx[:, 0]):
        out[r:r + n] += y[i]; norm[r:r + n] += w ** 2
    out = out / np.maximum(norm, 1e-9)
    touched = float((g < 0.999).mean() * 100)
    return out[padn:padn + len(x)], touched

def make_loop(seg, L, X):
    """seg has L+X seconds. Returns L seconds whose end flows into its start (equal-power crossfade)."""
    n, x = int(round(L * SR)), int(round(X * SR))
    assert len(seg) >= n + x
    t = (np.arange(x) + 0.5) / x
    y = seg[:n].copy()
    y[:x] = seg[:x] * np.sin(0.5 * np.pi * t) + seg[n:n + x] * np.cos(0.5 * np.pi * t)
    return y

def encode(x, path, kbps):
    tmp = path + ".tmp.mp3"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
           "-c:a", "libmp3lame", "-b:a", f"{kbps}k", "-compression_level", "0", "-ar", str(SR), "-ac", "1",
           "-map_metadata", "-1", "-id3v2_version", "0", "-write_id3v1", "0", tmp]
    subprocess.run(cmd, input=np.clip(x, -1, 1).astype(np.float32).tobytes(), check=True)
    os.replace(tmp, path)

def norm(x, target):
    I, _ = lufs(np.tile(x, 2) if len(x) < 20 * SR else x)
    g = 10 ** ((target - I) / 20)
    y = x * g
    pk = np.abs(y).max()
    if pk > 0.89:  # keep sample peaks under -1 dBFS; never clip
        y *= 0.89 / pk
    return y, I, 20 * np.log10(g)

def build_bed(name, b, manifest, meta):
    src = SRC.get(b["src"]) or CCBY_SRC[b["src"]]; path = fetch(b["src"])
    seg = decode(path, b["start"], b["L"] + b["X"], b["af"], b["chan"])
    extra = []
    if b.get("detonal"):
        seg, touched = detonal(seg)
        extra.append(f"spectral repair 1.5-10 kHz: cells more than 6 dB above the local time-frequency median pulled down to it ({touched:.1f} % of cells); removes faint bird chips")
    loop = make_loop(seg, b["L"], b["X"])
    loop, I0, gdb = norm(loop, b["lufs"])
    p = int(round(PAD * SR))
    body = np.concatenate([loop[-p:], loop, loop[:p]])
    out = os.path.join(OUT, f"{name}.mp3"); encode(body, out, b["kbps"])
    I1, tp = lufs(np.tile(loop, 2))
    meta[name] = dict(kind="loop", loopStart=PAD, loopEnd=round(PAD + len(loop) / SR, 6), dur=round(len(body) / SR, 6))
    manifest[name] = dict(
        file=f"assets/audio/{name}.mp3", kind="loop", bytes=os.path.getsize(out), seconds=round(len(body) / SR, 3),
        source={k: src[k] for k in ("title", "author", "licence", "licence_url", "page", "url", "recorded")},
        edits=[f"segment {b['start']:.2f}-{b['start'] + b['L'] + b['X']:.2f} s of the source",
               {"mix": "mono = (L+R)/2", "L": "mono = left channel only (the pair is decorrelated; a sum would comb-filter)",
                "R": "mono = right channel only", "diff": "mono = (L-R)/2 (channels are polarity-inverted against each other)"}[b["chan"]],
               "resampled to 44.1 kHz (soxr)", f"filters: {b['af']}", *extra,
               f"seamless loop: last {b['X']} s crossfaded (equal power, sin/cos) into the head; loop length {b['L']} s",
               f"loudness {I0:.1f} -> {I1:.1f} LUFS integrated (gain {gdb:+.1f} dB), true peak {tp} dBFS",
               f"padded {PAD} s of periodic extension each side; loopStart={PAD}, loopEnd={meta[name]['loopEnd']}",
               f"MP3 CBR {b['kbps']} kbps mono 44.1 kHz (LAME q0), tags stripped"])
    print(f"{name:8} {os.path.getsize(out) / 1024:6.1f} KB  {len(body) / SR:5.1f} s  {I0:6.1f} -> {I1:6.1f} LUFS  tp {tp}")

def fade(x, fi, fo):
    a, b = int(fi * SR), int(fo * SR)
    if a: x[:a] *= np.sin(0.5 * np.pi * (np.arange(a) + 0.5) / a) ** 2
    if b: x[-b:] *= np.cos(0.5 * np.pi * (np.arange(b) + 0.5) / b) ** 2
    return x

def build_events(name, e, manifest, meta):
    parts, segs, notes, used = [np.zeros(int(MARGIN * SR))], {}, [], {}
    t = MARGIN
    for k, (seg, srck, t0, t1, af, fi, fo) in enumerate(e["segs"]):
        path = fetch(srck)
        x = decode(path, t0, t1 - t0, af, "mix")
        x = fade(x, fi, fo)
        x, I0, gdb = norm(x, e["lufs"])
        I1, tp = lufs(np.concatenate([np.zeros(SR // 2), x, np.zeros(SR // 2)]))
        segs[seg] = [round(t, 4), round(len(x) / SR, 4)]
        parts.append(x); t += len(x) / SR
        notes.append(f"{seg}: {srck} {t0:.2f}-{t1:.2f} s, filters {af}, fades {fi}/{fo} s, {I0:.1f} -> {I1:.1f} LUFS ({gdb:+.1f} dB), tp {tp}")
        used[srck] = SRC.get(srck) or CCBY_SRC[srck]
        if k < len(e["segs"]) - 1:
            parts.append(np.zeros(int(GAP * SR))); t += GAP
    parts.append(np.zeros(int(MARGIN * SR)))
    body = np.concatenate(parts)
    out = os.path.join(OUT, f"{name}.mp3"); encode(body, out, e["kbps"])
    for sub, parent, a, b in SUBS.get(name, []):
        s0, d0 = segs[parent]; segs[sub] = [round(s0 + a, 4), round(min(b, d0) - a, 4)]
    meta[name] = dict(kind="sprite", segs=segs, dur=round(len(body) / SR, 4))
    manifest[name] = dict(
        file=f"assets/audio/{name}.mp3", kind="sprite", bytes=os.path.getsize(out), seconds=round(len(body) / SR, 3),
        sources={k: {kk: v[kk] for kk in ("title", "author", "licence", "licence_url", "page", "url", "recorded")} for k, v in used.items()},
        edits=notes + [f"segments packed with {GAP} s silence between them; MP3 CBR {e['kbps']} kbps mono 44.1 kHz (LAME q0)"],
        segments=segs)
    print(f"{name:8} {os.path.getsize(out) / 1024:6.1f} KB  {len(body) / SR:5.1f} s  {len(segs)} slices")

def write_meta(meta):
    js = open(FIELD_JS, encoding="utf-8").read()
    block = "const META = " + json.dumps(meta, separators=(",", ":")) + ";"
    new, n = re.subn(r"(// META:BEGIN[^\n]*\n).*?(\n// META:END)", lambda m: m.group(1) + block + m.group(2), js, flags=re.S)
    if n != 1:
        raise SystemExit("META markers not found in src/audio/field.js")
    open(FIELD_JS, "w", encoding="utf-8").write(new)

def main():
    global OUT
    args = sys.argv[1:]
    ccby = "--ccby" in args
    preview = None
    if "--preview" in args:
        preview = os.path.abspath(args[args.index("--preview") + 1]); OUT = preview
        args = [a for a in args if a not in ("--preview", preview) and os.path.abspath(a) != preview]
    want = {a for a in args if not a.startswith("--")}
    beds, events = dict(BEDS), dict(EVENTS)
    if ccby:
        beds.update(CCBY_BEDS); events.update(CCBY_EVENTS)
    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    manifest.pop("_about", None)
    meta = {k: v.get("_meta") for k, v in manifest.items() if isinstance(v, dict) and v.get("_meta")}
    for name, b in beds.items():
        if not want or name in want:
            build_bed(name, b, manifest, meta)
    for name, e in events.items():
        if not want or name in want:
            build_events(name, e, manifest, meta)
    for k in list(manifest):
        if k not in beds and k not in events:  # e.g. CC BY layers after a build without --ccby
            manifest.pop(k)
            f = os.path.join(OUT, f"{k}.mp3")
            if os.path.exists(f): os.remove(f)
    for k, v in manifest.items():
        lic = {x["licence"] for x in ([v["source"]] if "source" in v else v["sources"].values())}
        if any("BY" in l for l in lic):
            srcs = [v["source"]] if "source" in v else list(v["sources"].values())
            v["attribution"] = "; ".join(f'{x["title"]} by {x["author"]}, {x["licence"]} ({x["licence_url"]}), edited: looped/trimmed, filtered, level-normalised' for x in srcs)
    for k in manifest:
        manifest[k]["_meta"] = meta[k]
    total = sum(v["bytes"] for v in manifest.values())
    out = {"_about": dict(
        built_by="tools/audio/build_field.py", licence_policy="CC0 or public domain only",
        total_bytes=total, note="Public Domain Mark items are radio aporee uploads the recordists marked as public domain.")}
    out.update(manifest)
    json.dump(out, open(mpath, "w"), ensure_ascii=False, indent=1)
    if preview:
        json.dump({k: v["_meta"] for k, v in manifest.items()}, open(os.path.join(OUT, "meta.json"), "w"))
    else:
        write_meta({k: v["_meta"] for k, v in manifest.items()})
    print(f"total {total / 1024:.1f} KB in {len(manifest)} files")

if __name__ == "__main__":
    main()
