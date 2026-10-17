"""Every sound the game ships, as a recipe: which v0.1 synthesizer call renders it (tools/audio/v01/render.mjs),
with which seed and parameters, and how the build cuts it (one-shot, loop, piece). build_sounds.py turns
this into the files under godot/audio/ and into godot/audio/sounds.json (what the game loads) and
godot/audio/SOURCES.json (where each file came from). No recordings: everything here is synthesized
(G5R3-53, G5R3-65).

An asset: {id, group, kind, out, jobs, post, meta}
  kind  oneshot   a sound effect or creature call (variants share an id: id_01, id_02, ...)
        loop      a seamless bed or loop (period, cross-fade)
        piece     a sequencer piece cut on its section boundaries (loop or one-shot)
        noise     a long noise loop made here in numpy (the real-time wind's source)
  mono  True for sounds Godot places in 3D (mixed to one channel); 2D sounds keep their stereo.
"""
import zlib


def h(x):
    """A stable small number for a name (Python's hash() changes between runs)."""
    return zlib.crc32(repr(x).encode("utf-8")) % 997


BEDS_STATE = {"tod": 12, "near": 1, "rain": 0, "fall": 0, "water": 0, "wind": 0.3,
              "biome": {"forest": 0, "bamboo": 0, "stream": 0, "meadow": 0, "shrine": 0}}
FEST_CYCLE = 256 * 60 / 108 / 4          # one turn of the 16-bar festival: 35.556 s
FEST_T0 = 0.08                           # its first step (festStart: FEST.t = t + 0.08)


def _st(**kw):
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in BEDS_STATE.items()}
    for k, v in kw.items():
        if k in s["biome"]:
            s["biome"][k] = v
        else:
            s[k] = v
    return s


def variants(base_id, n, job_fn, seed0, **asset):
    """n variants of one sound: job_fn(i) -> job dict (without name and seed)."""
    out = []
    for i in range(n):
        j = job_fn(i)
        j.setdefault("dur", 2.0)
        j["seed"] = seed0 + i * 7919
        out.append(j)
    a = {"id": base_id, "kind": "oneshot", "jobs": out}
    a.update(asset)
    return a


def assets():
    A = []
    sfx = lambda name, opts=None, dur=2.0: (lambda i: {"type": "sfx", "sfx": name, "opts": dict(opts or {}), "dur": dur, "at": 0.05})
    code = lambda src, dur=2.0: (lambda i: {"type": "code", "code": src, "dur": dur, "at": 0.05})

    # ------------------------------------------------------------ her body: footsteps (v0.1 SFX.step)
    for mat in ["grass", "soil", "stone", "wood", "water", "leaves", "sand", "moss"]:
        for gait in ["walk", "run"]:
            A.append(variants(f"step_{mat}_{gait}", 12, sfx("step", {"mat": mat, "weight": 0, "run": gait == "run"}, 0.9),
                              1000 + h((mat, gait)), group="step", mono=True,
                              meta={"pitch_jitter": 0.5, "vol_jitter_db": 2.0}))
    # body layers that ride on a step (v0.1 put the weight's thump inside SFX.step; here a layer of its own)
    A.append(variants("step_heavy", 8, code(
        "play('sfx', (v) => { const o = out(v, 'sfx', 1, 0.04); I.thump(v, o, t, 85 * (0.95 + 0.1 * Math.random()), 42, 0.3, 0.12); "
        "I.noiseHit(v, o, 'brown', t, 'lowpass', 300, 0, 0.12, 0.08); });", 0.6), 2100, group="step", mono=True,
        meta={"pitch_jitter": 0.4, "vol_jitter_db": 1.5}))
    # 「音」 in her body: each step rings like a drum (the 2D core's step_sound "drum")
    A.append(variants("step_drum", 8, code(
        "play('sfx', (v) => { const o = out(v, 'sfx', 1, 0.18); I.bufTo(v, 'taiko', t, 0.9 + 0.12 * Math.random(), 0.32, o); "
        "I.bufTo(v, 'wood', t + 0.004, 0.55 + 0.1 * Math.random(), 0.12, o); });", 1.8), 2200, group="step", mono=True,
        meta={"pitch_jitter": 0.3, "vol_jitter_db": 1.5}))
    # さぢ's bell (8.1, G5R3-65: the bell is hers, not Kasasagi's): v0.1's suzu on her steps, barely there
    A.append(variants("bell_saji", 10, code(
        "play('sfx', (v) => { const o = out(v, 'sfx', 1, 0.04); I.bufTo(v, 'suzu', t, 0.96 + 0.08 * Math.random(), 0.05, o); });", 0.8),
        2300, group="saji", mono=True, meta={"pitch_jitter": 0.0, "vol_jitter_db": 2.0}))
    # さぢ's bare feet: v0.1's soil and grass steps, lighter (a child, barefoot)
    for mat in ["soil", "grass", "wood", "stone"]:
        A.append(variants(f"saji_step_{mat}", 8, sfx("step", {"mat": mat, "weight": 0}, 0.8), 2400 + h(mat),
                          group="saji", mono=True, meta={"pitch_jitter": 0.6, "vol_jitter_db": 2.0}))
    for name, opts, n in [("land", {"h": 0.3}, 6), ("rustle", {}, 10), ("branch", {}, 6), ("splash", {"size": 0.4}, 6)]:
        A.append(variants(name, n, sfx(name, opts, 2.5), 2600 + h(name), group="body", mono=True,
                          meta={"pitch_jitter": 0.4, "vol_jitter_db": 2.0}))

    # ------------------------------------------------------------ 「移」: verbs (8.2: take rises, give falls)
    for name in ["take", "give", "release", "deny"]:
        A.append(variants(name, 4, sfx(name, {}, 1.6), 3000 + h(name), group="verb", mono=False,
                          meta={"pitch_jitter": 0.0, "vol_jitter_db": 1.0}))
    for k in ["w", "h", "l", "s", "v"]:
        for verb in ["take", "give", "release"]:
            A.append(variants(f"qual_{k}_{verb}", 4, sfx("qual", {"k": k, "verb": verb, "n": 3}, 2.0),
                              3400 + h((k, verb)), group="verb", mono=False, meta={"pitch_jitter": 0.0, "vol_jitter_db": 1.0}))
    # ------------------------------------------------------------ things in the world (v0.1)
    for name, opts in [("pickup", {"size": 0.4}), ("drop", {"size": 0.4}), ("place", {}), ("build", {}), ("fall", {"size": 0.6})]:
        A.append(variants(name, 4, sfx(name, opts, 2.5), 3800 + h(name), group="thing", mono=True,
                          meta={"pitch_jitter": 0.3, "vol_jitter_db": 1.5}))
    A.append(variants("build_done", 2, sfx("build_done", {}, 5.0), 3900, group="thing", mono=False, meta={}))
    for n in range(1, 10):
        A.append(variants(f"stack_{n}", 2, sfx("stack", {"n": n}, 2.0), 4000 + n * 13, group="thing", mono=True, meta={}))
    # ------------------------------------------------------------ menus and the dialogue (v0.1)
    for name in ["ui_move", "ui_ok", "ui_back", "ui_open", "ui_close"]:
        A.append(variants(name, 4, sfx(name, {}, 1.4), 4300 + h(name), group="ui", mono=False,
                          meta={"pitch_jitter": 0.0, "vol_jitter_db": 1.0}))
    for voice in ["tsuzumi", "saji", "shione", "old", "radio", "crow", "kago", "tsuzura"]:
        A.append({"id": f"blip_{voice}", "kind": "oneshot", "group": "voice", "mono": False,
                  "jobs": [{"type": "sfx", "sfx": "blip", "opts": {"voice": voice, "i": i}, "dur": 0.5, "at": 0.05,
                            "seed": 4700 + h(voice) + i} for i in range(12)],
                  "meta": {"pitch_jitter": 0.0, "vol_jitter_db": 0.8}})
    # ------------------------------------------------------------ creatures and weather (v0.1's scheduler events)
    ev = lambda name, dur, args=None: (lambda i: {"type": "event", "ev": name, "evargs": list(args or []), "dur": dur, "at": 2.0,
                                                  "mask": {}, "events": False})
    for name, fn, n, dur in [("minmin", "evMinmin", 10, 10), ("higu", "evHigurashi", 12, 8), ("ugu", "evUguisu", 8, 5),
                             ("tit", "evTit", 10, 5), ("suzumushi", "evSuzumushi", 16, 5), ("kajika", "evKajika", 10, 6),
                             ("clack", "evClack", 10, 3), ("drip", "evDrip", 16, 2.6)]:
        A.append(variants(f"ev_{name}", n, ev(fn, dur), 5000 + h(name), group="creature", mono=True,
                          meta={"pitch_jitter": 0.0, "vol_jitter_db": 2.0}))
        if name == "suzumushi":
            A[-1]["measure_f0"] = [3500, 6000]
    # one caw at a time (the crows on the camphor open their beaks one caw at a time, W3Life's "caw" pose)
    A.append(variants("caw", 12, code(
        "play('sfx', (v) => { I.caw(v, out(v, 'sfx', 1, 0.25), t, 1, 470 + 90 * Math.random()); });", 2.4),
        5600, group="creature", mono=True, meta={"pitch_jitter": 0.0, "vol_jitter_db": 2.0}))
    A.append(variants("wings", 6, sfx("wings", {}, 2.5), 5700, group="creature", mono=True, meta={"pitch_jitter": 0.3, "vol_jitter_db": 2.0}))
    A.append(variants("thunder", 4, sfx("thunder", {"dist": 0.85}, 12.0), 5800, group="weather", mono=False, meta={"vol_jitter_db": 2.0}))
    # ------------------------------------------------------------ the far (遠化) and the prologue's moments (v0.1)
    for name, n, dur in [("far_pulse", 2, 9.0), ("far_touch", 2, 6.0), ("far_wave", 1, 14.0), ("heartbeat", 2, 2.0), ("offering", 3, 5.0),
                         ("awaken", 2, 4.0), ("sleep", 2, 5.0), ("bell_big", 2, 12.0)]:
        A.append(variants(name, n, sfx(name, {}, dur), 6000 + h(name), group="story", mono=False, meta={}))
    for name in ["discover", "offering", "build", "complete", "awaken", "far", "title_hit", "night", "dawn", "hum", "echo"]:
        A.append(variants(f"sting_{name}", 2, lambda i, nm=name: {"type": "stinger", "stinger": nm, "dur": 12.0, "at": 0.05},
                          6600 + h(name), group="stinger", mono=False, meta={}))

    # ------------------------------------------------------------ beds (loops): leaves, bamboo, brook, rain
    for w in [0.25, 0.55, 0.9]:
        A.append({"id": f"bed_leaves_{int(w * 100):02d}", "kind": "loop", "group": "bed", "mono": False,
                  "jobs": [{"type": "amb", "state": _st(wind=w, forest=1), "mask": {"leaves": 1}, "events": False, "seed": 7100 + int(w * 100), "dur": 68}],
                  "loop": {"start": 6.0, "period": 60.0, "xfade": 2.0, "power": True}, "meta": {"wind": w}})
    for w in [0.3, 0.85]:
        A.append({"id": f"bed_sasa_{int(w * 100):02d}", "kind": "loop", "group": "bed", "mono": False,
                  "jobs": [{"type": "amb", "state": _st(wind=w, bamboo=1), "mask": {"sasa": 1}, "events": False, "seed": 7200 + int(w * 100), "dur": 53}],
                  "loop": {"start": 6.0, "period": 45.0, "xfade": 2.0, "power": True}, "meta": {"wind": w}})
    for v, sd in [("a", 7301), ("b", 7302), ("c", 7303)]:
        A.append({"id": f"bed_stream_{v}", "kind": "loop", "group": "bed", "mono": True,
                  "jobs": [{"type": "amb", "state": _st(water=1, stream=1), "mask": {"stream": 1}, "events": False, "seed": sd, "dur": 83}],
                  "loop": {"start": 6.0, "period": 75.0, "xfade": 2.0, "power": True}, "meta": {}})
    for r in [0.3, 0.6, 0.95]:
        A.append({"id": f"bed_rain_{int(r * 100):02d}", "kind": "loop", "group": "bed", "mono": False,
                  "jobs": [{"type": "amb", "state": _st(rain=r, forest=1), "mask": {"rain": 1}, "events": False, "seed": 7400 + int(r * 100), "dur": 68}],
                  "loop": {"start": 6.0, "period": 60.0, "xfade": 2.0, "power": True}, "meta": {"rain": r}})
    # the wind's source: long pink noise (v0.1's pink filter), filtered and gusted in real time by Godot
    A.append({"id": "noise_pink", "kind": "noise", "group": "bed", "mono": False, "jobs": [],
              "noise": {"kind": "pink", "seconds": 61.0, "seed": 7501}, "meta": {}})

    # ------------------------------------------------------------ the far festival (遠囃子), in tune (A-phase fix 2)
    fest_jobs = []
    for a, near in [(0.4, 0.8), (0.25, 0.6), (0.1, 0.3), (0.55, 1.0), (0.35, 0.5)]:
        A.append({"id": f"fest_{int(a * 100):02d}_{int(near * 100):03d}", "kind": "loop", "group": "festival", "mono": False,
                  "jobs": [{"type": "festival", "fest": {"a": a, "near": near}, "seed": 7600, "dur": FEST_T0 + 2 * FEST_CYCLE + 0.6}],
                  "loop": {"start": FEST_T0 + FEST_CYCLE, "period": FEST_CYCLE, "xfade": 0.35, "power": False},
                  "meta": {"a": a, "near": near, "bpm": 108, "beats": 64}})
    # the radio on the engawa post (the 遠囃子 through its little speaker, static, the dial)
    A.append({"id": "radio_fest", "kind": "loop", "group": "festival", "mono": True,
              "jobs": [{"type": "festival", "radio": {"signal": 0.6}, "seed": 7700, "dur": FEST_T0 + 3 * FEST_CYCLE + 0.6}],
              "loop": {"start": FEST_T0 + FEST_CYCLE, "period": 2 * FEST_CYCLE, "xfade": 0.35, "power": False},
              "meta": {"bpm": 108, "beats": 128}})

    # ------------------------------------------------------------ the music (v0.1's sequencer pieces)
    A.append({"id": "mus_title", "kind": "piece", "group": "music", "mono": False,
              "jobs": [{"type": "music", "piece": "title", "ks": list(range(24)), "seed": 8100, "dur": 300}],
              "piece": {"loop_sections": [12, 24], "xfade": 0.25}, "meta": {}})
    A.append({"id": "mus_home", "kind": "piece", "group": "music", "mono": False,
              "jobs": [{"type": "music", "piece": "home", "ks": list(range(8)), "seed": 8200, "dur": 140}],
              "piece": {"loop_sections": [4, 8], "xfade": 0.25}, "meta": {}})
    A.append({"id": "mus_prologue", "kind": "piece", "group": "music", "mono": False,
              "jobs": [{"type": "music", "piece": "prologue", "ks": list(range(8)), "seed": 8300, "dur": 110}],
              "piece": {"oneshot": True}, "meta": {}})
    A.append({"id": "mus_wonder", "kind": "piece", "group": "music", "mono": False,
              "jobs": [{"type": "music", "piece": "wonder", "seed": 8400, "dur": 36}],
              "piece": {"oneshot": True}, "meta": {}})
    A.append({"id": "mus_tension", "kind": "piece", "group": "music", "mono": False,
              "jobs": [{"type": "music", "piece": "tension", "ks": [0, 1, 2], "seed": 8500, "dur": 64}],
              "piece": {"oneshot": True}, "meta": {}})
    # the explore piece: v0.1 plays a phrase every 25-70 s, coloured by the hour; the phrases are cut one
    # by one and the silences are kept by the game (Godot's music director)
    for mode, tod in [("morning", 8.0), ("noon", 13.0), ("dusk", 18.0), ("night", 22.0)]:
        A.append({"id": f"mus_explore_{mode}", "kind": "piece", "group": "music", "mono": False,
                  "jobs": [{"type": "music", "piece": "explore", "ks": [1], "tod": tod, "seed": 8600 + 101 * i + int(tod), "dur": 48}
                           for i in range(8)],
                  "piece": {"oneshot": True, "phrase": True}, "meta": {"mode": mode}})
    # v0.1 made these the same every time (fixed partials, a tone and a little noise): their variants are played a
    # little faster or slower and coloured a little differently (build_sounds.vary: [pitch range, tilt dB])
    VARY = {"deny": [0.025, 1.5], "step_heavy": [0.04, 1.5], "step_drum": [0.03, 1.5], "land": [0.04, 1.5],
            "take": [0.012, 1.2], "give": [0.012, 1.2], "release": [0.015, 1.2], "ui_open": [0.008, 1.0],
            "ui_close": [0.008, 1.0], "ui_move": [0.008, 1.0], "ui_ok": [0.006, 1.0], "ui_back": [0.006, 1.0],
            "pickup": [0.03, 1.5], "drop": [0.03, 1.5], "place": [0.03, 1.5], "build": [0.02, 1.5],
            "fall": [0.03, 1.5], "heartbeat": [0.03, 1.0], "sleep": [0.01, 1.0]}
    for a in A:
        if a["id"] in VARY:
            a["vary"] = VARY[a["id"]]
        elif a["id"].startswith("qual_"):
            a["vary"] = [0.007, 1.2]          # tonal on the yo scale: within about 12 cents
        elif a["id"].startswith("stack_"):
            a["vary"] = [0.006, 1.2]
    return A
