class_name AudioAmbience
extends Node
## The air (Audio.amb): v0.1's ambience (legacy/v0.1/src/audio.js ambUpdate / ambTick) on Godot's players.
## Beds, their levels and the creatures' schedule are v0.1's rules (time-of-day windows, rates, caps, rain,
## the 遠化's nearness); what changed (A phase, docs/knowledge/30 §12):
##   * the wind is real time: long pink noise through a low-pass whose cutoff and level follow v0.1's gust
##     random walk (and the world's wind); the leaves, bamboo, brook and rain are long offline loops with
##     their own noise each (v0.1 read one 2-second noise buffer for all of them: the beds repeated every 2 s);
##   * every creature sounds from a place you can see: cicadas and birds in the trees round her, insects in
##     the grass, frogs on the brook, the bamboo knocking in the bamboo, drips under the trees (`places`);
##     where there is no such place nothing sounds (decision 3, rule 3). The crows are the ones on the camphor:
##     the showcase's driver plays a caw when one opens its beak (ShowcaseSound);
##   * no creak in the wind (rule 1), at most three bell crickets at once and never two on near pitches (rule 4).
## On a screen with no 3D world (menu, gallery, vista) preset() gives a fixed scene and the calls are panned.
##   Audio.amb.set_state({"tod": 9.5, "wind": 0.3, "rain": 0, "forest": 1, ...})   every frame, from the world
##   Audio.amb.places = obj   # tree(rng, rmin, rmax), grass(...), water(...), bamboo(...) -> Vector3 or INF;
##                            # stream_points() -> PackedVector3Array; listener() -> Vector3

const WIND_BUS := "AmbWind"
## v0.1's pink noise is -9.3 dBFS RMS; the wind's source file is -18 dBFS: this puts it back (+8.8 dB), times
## v0.1's ambience and master bus gains (0.85 * 0.85) that the offline renders carry already
const WIND_CAL := 2.75 * 0.7225
const LEAVES := [[0.25, "bed_leaves_25"], [0.55, "bed_leaves_55"], [0.9, "bed_leaves_90"]]
const SASA := [[0.3, "bed_sasa_30"], [0.85, "bed_sasa_85"]]
const RAIN := [[0.3, "bed_rain_30"], [0.6, "bed_rain_60"], [0.95, "bed_rain_95"]]
const STREAM := ["bed_stream_a", "bed_stream_b", "bed_stream_c"]
const STREAM_STEP := 5.0          # metres between the brook's emitters
const STREAM_REACH := 34.0        # emitters farther than this from her are stopped
# The mix's calibration (decision 7, in-game recordings, tools/audio/check_mix.py): v0.1's beds keep their own
# levels against each other, but its rain and brook were 6-8 LU louder than a calm walk (heavy rain by the brook
# -16 LUFS against -25). Heavy rain may stand about 3 LU above the reference (-24 LUFS), the brook beside her about
# at it; the voices and her steps stay on top.
const BED_TRIM_DB := {"bed_rain_30": -1.0, "bed_rain_60": -3.0, "bed_rain_95": -5.5}
const STREAM_DB := -10.5          # each brook emitter (they overlap every five metres): about -25.5 LUFS beside it
# v0.1's wind grew with the wind (0.1 + 0.6 w, and brighter): alone it was -20.4 LUFS at wind 0.9 by the brook,
# the loudest thing there (the "大風聲" over the brook, G5R3-65 2.3). Above 0.35 it now gives up to 5 dB of that.
const WIND_TOP_DB := -5.0

var state := {"tod": 12.0, "rain": 0.0, "wind": 0.3, "near": 1.0, "forest": 0.0, "bamboo": 0.0, "meadow": 0.0,
	"shrine": 0.0, "stream": 0.0, "indoor": false, "cinematic": false, "paused": false}
var on := false
var places: Object = null
var wet := 0.0                    # the leaves keep dripping after rain (v0.1 AMB.wet)
var gust := 0.62                  # v0.1's gust random walk (the wind's level and brightness)
var gust_front := 0.0             # the grass's gust front at her place (0..1), from the driver: the wind swells with it
var act := 1.0
var events_on := true
var rng := RandomNumberGenerator.new()
var log_events := false
var events_log: Array = []        # [msec, kind, pos] (checks)
# -- --audio-solo=wind,beds,stream,events: only these parts of the air sound (calibration recordings; the
# showcase's crows count as events, the music is muted unless "music" is listed). Empty: everything.
var solo := {}

var _wind: AudioStreamPlayer
var _wind_lp: AudioEffectLowPassFilter
var _beds := {}                   # id -> AudioStreamPlayer (leaves, sasa, rain)
var _stream_em: Array = []        # [AudioStreamPlayer3D, Vector3]
var _g_target := 0.62
var _g_tc := 1.0
var _next_gust := 0.0
var _clock := 0.0
var _active := {}                 # kind -> [[end_time, freq]]
var _pending: Array = []          # [time, callable]
var _preset := ""


func _ready() -> void:
	rng.seed = Time.get_ticks_usec() ^ 0x5bd1e995
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--audio-solo="):
			for k in a.substr(13).split(","):
				solo[k] = true
	_make_wind_bus()
	_wind = AudioStreamPlayer.new()
	_wind.bus = WIND_BUS
	_wind.volume_db = -80.0
	add_child(_wind)
	for list in [LEAVES, SASA, RAIN]:
		for pair in list:
			var p := AudioStreamPlayer.new()
			p.bus = "Ambience"
			p.volume_db = -80.0
			add_child(p)
			_beds[String(pair[1])] = p


func _make_wind_bus() -> void:
	if AudioServer.get_bus_index(WIND_BUS) >= 0:
		var bi := AudioServer.get_bus_index(WIND_BUS)
		for i in AudioServer.get_bus_effect_count(bi):
			if AudioServer.get_bus_effect(bi, i) is AudioEffectLowPassFilter:
				_wind_lp = AudioServer.get_bus_effect(bi, i)
		return
	AudioServer.add_bus()
	var b := AudioServer.bus_count - 1
	AudioServer.set_bus_name(b, WIND_BUS)
	AudioServer.set_bus_send(b, "Ambience")
	var hp := AudioEffectHighPassFilter.new()     # v0.1: highpass 50 Hz, Q 0 dB
	hp.cutoff_hz = 50.0
	hp.resonance = 1.0
	AudioServer.add_bus_effect(b, hp)
	_wind_lp = AudioEffectLowPassFilter.new()     # v0.1: lowpass 300..1200 Hz by the wind, Q 0 dB (resonance 1)
	_wind_lp.cutoff_hz = 600.0
	_wind_lp.resonance = 1.0
	AudioServer.add_bus_effect(b, _wind_lp)


## A fixed scene for screens without a 3D world: "night" (the title under the camphor), "wind" (day), [] (off).
func preset(names: Array) -> void:
	var key := ",".join(PackedStringArray(names.map(func(x): return str(x))))
	if key == _preset:
		return
	_preset = key
	if names.is_empty():
		on = false
		return
	var s := {"tod": 12.0, "rain": 0.0, "wind": 0.3, "near": 1.0, "forest": 0.6, "bamboo": 0.0, "meadow": 0.0,
		"shrine": 0.5, "stream": 0.0, "indoor": false, "cinematic": false, "paused": false}
	if "night" in names:
		s["tod"] = 21.5
		s["wind"] = 0.25 if not "wind" in names else 0.35
	elif "wind" in names:
		s["tod"] = 9.5
		s["wind"] = 0.35
	set_state(s)


func set_state(s: Dictionary) -> void:
	for k in s:
		state[k] = s[k]
	on = true
	_start_beds()


func stop_all() -> void:
	on = false
	for p in [_wind] + _beds.values():
		if p != null and is_instance_valid(p):
			(p as AudioStreamPlayer).stop()
			(p as AudioStreamPlayer).stream = null
	for e in _stream_em:
		if is_instance_valid(e[0]):
			(e[0] as AudioStreamPlayer3D).stop()
			(e[0] as AudioStreamPlayer3D).stream = null


func world_changed() -> void:
	for e in _stream_em:
		if is_instance_valid(e[0]):
			(e[0] as Node).queue_free()
	_stream_em.clear()
	_active.clear()
	_pending.clear()


func _start_beds() -> void:
	var w := Audio.stream_of(String(Audio.sounds.get("noise_pink", {}).get("files", [""])[0])) if Audio.has("noise_pink") else null
	if w and _wind.stream != w:
		_set_loop(w)
		_wind.stream = w
		_wind.play(rng.randf() * 50.0)
	for id in _beds:
		var p: AudioStreamPlayer = _beds[id]
		if p.stream == null and Audio.has(id):
			var st := Audio.stream_of(String(Audio.sounds[id]["files"][0]))
			_set_loop(st)
			p.stream = st
			p.play(rng.randf() * 50.0)


static func _set_loop(s: AudioStream) -> void:
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	elif s is AudioStreamWAV:
		(s as AudioStreamWAV).loop_mode = AudioStreamWAV.LOOP_FORWARD


static func sstep(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


## v0.1's daily window: 1 inside [a, b] (wrapping past midnight), easing in and out over f hours.
static func day_w(h: float, a: float, b: float, f: float) -> float:
	var inside := (h >= a and h <= b) if a <= b else (h >= a or h <= b)
	if not inside:
		return 0.0
	return minf(1.0, minf(fposmod(h - a, 24.0), fposmod(b - h, 24.0)) / f)


## Weights of the three loops of a bed for the value x (piecewise linear between their x).
static func mix_weights(levels: Array, x: float) -> Array:
	var out: Array = []
	out.resize(levels.size())
	out.fill(0.0)
	if x <= float(levels[0][0]):
		out[0] = x / maxf(0.001, float(levels[0][0]))
		return out
	for i in levels.size() - 1:
		var a := float(levels[i][0])
		var b := float(levels[i + 1][0])
		if x <= b:
			var t := (x - a) / (b - a)
			out[i] = 1.0 - t
			out[i + 1] = t
			return out
	out[levels.size() - 1] = 1.0
	return out


func _process(dt: float) -> void:
	_clock += dt
	if not on:
		_wind.volume_db = move_toward(_wind.volume_db, -80.0, dt * 40.0)
		for id in _beds:
			var p: AudioStreamPlayer = _beds[id]
			p.volume_db = move_toward(p.volume_db, -80.0, dt * 40.0)
		for e in _stream_em:
			(e[0] as AudioStreamPlayer3D).volume_db = -80.0
		return
	var near := minf(float(state["near"]), 1.0 - Audio.far_here_now())
	var rain := float(state["rain"])
	var wind := clampf(float(state["wind"]), 0.0, 1.0)
	var indoor := bool(state.get("indoor", false))
	var near_g := (0.03 + 0.97 * sstep(0.0, 0.6, near)) * (0.7 if bool(state.get("cinematic", false)) else 1.0) * (0.5 if indoor else 1.0)
	act = sstep(0.04, 0.6, near) * (0.4 if indoor else 1.0)
	var forest := float(state["forest"])
	var bamboo := float(state["bamboo"])
	var meadow := float(state["meadow"])
	var shrine := float(state["shrine"])
	var open := clampf(forest + bamboo + 1.3 * meadow + shrine + 0.5 * float(state["stream"]), 0.3, 1.3)
	# --- the wind: v0.1's gust random walk, now in real time (level and brightness), swelling as a gust front
	#     of the grass passes her (the world's own wind)
	if _clock >= _next_gust:
		_g_target = clampf(0.62 + (rng.randf() - 0.5) * (0.35 + 0.9 * wind), 0.15, 1.25)
		_g_tc = rng.randf_range(0.35, 1.4) * (1.3 - wind * 0.6)
		_next_gust = _clock + rng.randf_range(0.4, 1.8)
	gust = _g_target + (gust - _g_target) * exp(-dt / maxf(0.05, _g_tc))
	var g := gust * (1.0 + 0.45 * gust_front)
	var wv := (0.1 + 0.6 * wind) * open * 0.55
	var top := WIND_TOP_DB * clampf((wind - 0.35) / 0.55, 0.0, 1.0)
	_wind.volume_db = linear_to_db(maxf(1e-5, WIND_CAL * wv * g * near_g * heard("wind"))) + top
	if _wind_lp:
		var cut := lerpf(300.0, 1200.0, wind) * (1.0 + 0.25 * meadow) * pow(2.0, (g - 0.62) * 1100.0 / 1200.0)
		_wind_lp.cutoff_hz = clampf(cut, 60.0, 18000.0)
	# --- leaves, bamboo, rain: offline loops crossfaded by the wind (or the rain), scaled like v0.1's beds
	var wl := mix_weights(LEAVES, wind)
	for i in LEAVES.size():
		_bed(String(LEAVES[i][1]), float(wl[i]) * forest * near_g, dt)
	var ws := mix_weights(SASA, wind)
	for i in SASA.size():
		_bed(String(SASA[i][1]), float(ws[i]) * bamboo * near_g, dt)
	var wr := mix_weights(RAIN, rain) if rain > 0.0 else [0.0, 0.0, 0.0]
	for i in RAIN.size():
		_bed(String(RAIN[i][1]), float(wr[i]) * near_g, dt)
	wet = clampf(wet + (rain - wet) * (dt / 3.0 if rain > wet else dt / 90.0), 0.0, 1.0)
	_update_stream(near_g)
	# --- the creatures and the weather (v0.1's rates and windows), from places you can see
	if events_on and not bool(state.get("paused", false)):
		_events(dt)


## 1 if this part of the air is heard (no --audio-solo, or it is listed), else 0.
func heard(part: String) -> float:
	return 1.0 if solo.is_empty() or solo.has(part) else 0.0


func _bed(id: String, lin: float, dt: float) -> void:
	var p: AudioStreamPlayer = _beds.get(id)
	if p == null:
		return
	var target := linear_to_db(maxf(lin * heard("beds"), 1e-5)) + float(BED_TRIM_DB.get(id, 0.0))
	# v0.1 eased its bed levels (setTargetAtTime ~0.5 s)
	p.volume_db = lerpf(p.volume_db, target, clampf(dt / 0.5, 0.0, 1.0)) if target > -79.0 or p.volume_db > -79.0 else -80.0


## The brook: emitters along its line (every 5 m), the three loops in turn, each from a different place in its
## loop; only the ones within reach of her play.
func _update_stream(near_g: float) -> void:
	if Audio.world == null or places == null or not places.has_method("stream_points"):
		return
	if _stream_em.is_empty():
		var pts: PackedVector3Array = places.call("stream_points", STREAM_STEP)
		var i := 0
		for q in pts:
			var id := String(STREAM[i % STREAM.size()])
			i += 1
			if not Audio.has(id):
				continue
			var p := AudioStreamPlayer3D.new()
			p.bus = "Ambience"
			var st := Audio.stream_of(String(Audio.sounds[id]["files"][0]))
			_set_loop(st)
			p.stream = st
			p.unit_size = 3.0
			p.max_distance = 20.0
			p.max_db = 0.0
			p.attenuation_filter_cutoff_hz = 7000.0
			p.attenuation_filter_db = -10.0
			Audio.world.add_child(p)
			p.global_position = q + Vector3(0, 0.3, 0)
			_stream_em.append([p, q])
	var lp: Vector3 = places.call("listener") if places.has_method("listener") else Vector3.ZERO
	for e in _stream_em:
		var p: AudioStreamPlayer3D = e[0]
		var d := (e[1] as Vector3).distance_to(lp)
		if d < STREAM_REACH:
			if not p.playing:
				p.play(rng.randf() * 70.0)
			# five-metre spacing: neighbours overlap (STREAM_DB: the calibration above)
			p.volume_db = linear_to_db(maxf(1e-5, near_g * heard("stream"))) + STREAM_DB
		elif p.playing:
			p.stop()


# ------------------------------------------------------------------ the scheduler (v0.1 ambTick)

func _events(dt: float) -> void:
	var t := _clock
	for i in range(_pending.size() - 1, -1, -1):
		if float(_pending[i][0]) <= t:
			var cb: Callable = _pending[i][1]
			_pending.remove_at(i)
			cb.call()
	if act < 0.02 or heard("events") == 0.0:
		return
	var h := float(state["tod"])
	var rain := float(state["rain"])
	var wind := float(state["wind"])
	var forest := float(state["forest"])
	var bamboo := float(state["bamboo"])
	var meadow := float(state["meadow"])
	var shrine := float(state["shrine"])
	var water := float(state["stream"])
	var woods := forest + 0.6 * bamboo + 0.4 * shrine
	var dry := 1.0 - 0.9 * rain
	_maybe("minmin", day_w(h, 9.0, 16.5, 0.6) * (woods + 0.5 * meadow) * dry * act * 0.1, dt, 3, "tree", "ev_minmin")
	_maybe("higu", (day_w(h, 16.5, 19.0, 0.35) + day_w(h, 4.5, 5.75, 0.3)) * (woods + 0.25) * dry * act * 0.2, dt, 4, "tree", "ev_higu")
	_maybe("ugu", day_w(h, 5.0, 11.0, 0.5) * (forest + bamboo + 0.5 * shrine) * dry * act * 0.035, dt, 1, "tree", "ev_ugu")
	_maybe("tit", day_w(h, 6.0, 17.0, 0.5) * (woods + 0.3) * dry * act * 0.045, dt, 2, "tree", "ev_tit")
	_maybe("suzu", day_w(h, 19.5, 4.5, 0.5) * (0.4 + meadow + 0.6 * forest + 0.5 * shrine) * (1.0 - rain) * act * 0.9, dt, 3, "grass", "ev_suzumushi")
	_maybe("kajika", (day_w(h, 18.5, 4.5, 0.5) * 0.8 + 0.25) * water * (1.0 - 0.5 * rain) * act * 0.16, dt, 2, "water", "ev_kajika")
	_maybe("clack", bamboo * (0.04 + 0.55 * wind) * act, dt, 3, "bamboo", "ev_clack")
	_maybe("drip", wet * (0.4 + 2.6 * rain) * (forest + bamboo + 0.3) * act, dt, 4, "drip", "ev_drip")
	if rain > 0.7:
		_maybe("thunder", (rain - 0.7) * 0.07 * act, dt, 1, "sky", "thunder")


func _maybe(kind: String, rate: float, dt: float, cap: int, where: String, id: String) -> void:
	if not (rate > 0.0) or rng.randf() >= rate * dt:
		return
	var t := _clock
	var a: Array = _active.get(kind, [])
	for i in range(a.size() - 1, -1, -1):
		if float(a[i][0]) < t:
			a.remove_at(i)
	if a.size() >= cap:
		return
	var dur := _fire(kind, where, id, a)
	if dur > 0.0:
		_active[kind] = a
		if kind == "higu":
			_answer(1, dur)


## One call from a place of its kind; returns its length (0: no place, nothing sounded).
func _fire(kind: String, where: String, id: String, active: Array) -> float:
	if not Audio.has(id):
		return 0.0
	var e: Dictionary = Audio.sounds[id]
	var pos := Vector3.INF
	if Audio.world != null and places != null:
		match where:
			"tree":
				pos = places.call("tree", rng, 6.0, 32.0)
			"grass":
				pos = places.call("grass", rng, 2.5, 14.0)
			"water":
				pos = places.call("water", rng, 0.0, 22.0)
			"bamboo":
				pos = places.call("bamboo", rng, 0.0, 30.0)
			"drip":
				pos = places.call("tree", rng, 0.5, 7.0)
			"sky":
				pos = Vector3.ZERO
		if pos == Vector3.INF:
			return 0.0
	# rule 4: no two bell crickets on near pitches at once (their pitch is in the manifest, per variant)
	var opts := {}
	var freqs: Array = e.get("f0", [])
	if not freqs.is_empty():
		var tries := 0
		var vi := Audio._pool(id).pick()
		while tries < 6 and _clashes(float(freqs[vi]), active):
			vi = Audio._pool(id).pick()
			tries += 1
		if _clashes(float(freqs[vi]), active):
			return 0.0
		opts["variant"] = vi
	var length := 2.0
	if where == "sky" or Audio.world == null or places == null:
		var c := Audio.choose(id, opts)
		if c.is_empty():
			return 0.0
		var pan := rng.randf_range(-0.9, 0.9)
		_play_pan_stream(c, pan)
		length = (c[0] as AudioStream).get_length()
		opts["variant"] = c[3]
	else:
		var lift := 4.0 if where == "tree" else (2.6 if where == "drip" else 0.15)
		var unit := 12.0 if where == "tree" else (5.0 if where == "grass" else 8.0)
		var p := Audio.play_at(id, pos + Vector3(0, lift, 0), opts.merged({"unit": unit, "max": 60.0, "bus": "Ambience"}))
		if p == null or p.stream == null:
			return 0.0
		length = p.stream.get_length()
	var f0 := float(freqs[int(opts.get("variant", 0))]) if not freqs.is_empty() and opts.has("variant") else 0.0
	active.append([_clock + length, f0])
	if log_events:
		events_log.append([Time.get_ticks_msec(), kind, pos])
	return length


func _clashes(f: float, active: Array) -> bool:
	for a in active:
		if float(a[1]) > 0.0 and absf(float(a[1]) - f) < 60.0:
			return true
	return false


func _play_pan_stream(c: Array, pan: float) -> void:
	var q: AudioStreamPlayer2D = Audio._pf[Audio._nf]
	Audio._nf = (Audio._nf + 1) % Audio._pf.size()
	var vp := get_viewport()
	var sz := vp.get_visible_rect().size if vp else Vector2(640, 360)
	q.position = sz * 0.5 + Vector2(pan * sz.x * 0.5, 0.0)
	q.stream = c[0]
	q.bus = "Ambience"
	q.volume_db = c[1]
	q.pitch_scale = c[2]
	q.play()


## The higurashi answer each other (v0.1: 60 % of calls are answered, up to three in a chain, from another tree,
## as the last one ends: its length -1.2 .. +1.5 s).
func _answer(n: int, after: float) -> void:
	if n > 3 or rng.randf() >= 0.6:
		return
	var at := _clock + after + rng.randf_range(-1.2, 1.5)
	_pending.append([at, func() -> void:
		if act > 0.1 and on:
			var a: Array = _active.get("higu", [])
			var d := _fire("higu", "tree", "ev_higu", a)
			if d > 0.0:
				_active["higu"] = a
				_answer(n + 1, d)])
