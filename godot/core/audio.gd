extends Node
## Audio (autoload): the game's sound and music. All of it is synthesized (G5R3-53, G5R3-65): v0.1's
## synthesizer, rendered offline by tools/audio/build_sounds.py into godot/audio/ (listed in sounds.json, every
## file's recipe in SOURCES.json), then chosen, layered, placed in 3D and mixed here; the wind is pink noise
## filtered and gusted in real time. Which part is offline and which is real time, and why: decision 2 of
## docs/design/audio-music-draft.md. No recording is used.
##   Audio.play("ui_ok")                        a sound by its id in sounds.json (a variant, never the same twice running)
##   Audio.play_at("caw", pos)                  the same, placed in the 3D world (attach_world); 2D without one
##   Audio.sfx("take", {"k": "w"})              the verbs (take / give / release / deny / regain / ignite / ui)
##   Audio.blip("saji", i)                      a dialogue voice blip (v0.1: every other character)
##   Audio.footstep("stone", {...})             the 2D core's steps (BodyState.step_sound); footstep_at() in 3D
##   Audio.duck(0.35, 0.3)                      under a dialogue: music down 9 dB, ambience down 4 dB (decision 2)
##   Audio.far(k)                               the 遠化 fills k (0..1) of what she looks at: the ambience recedes
##   Audio.far_here(k)                          she stands in a place k far (0..1): no music there (5e), the air
##                                              thins as v0.1's nearness did
##   Audio.music("title", {"fade": 3.0})        a piece (AudioMusic); "none" fades out
##   Audio.festival(a, near)                    the far festival (遠囃子), v0.1's intensity and nearness
##   Audio.ambience(["night"])                  a bed preset for screens without a 3D world (menu, gallery, vista)
##   Audio.amb                                  the ambience (AudioAmbience): set_state() each frame from the world

const MANIFEST := "res://audio/sounds.json"
const BUSES := ["Music", "Ambience", "SFX", "Voice"]
## dialogue ducking (decision 2, G5R3-65): at duck(0.35), the amount the story asks for, music -9 dB, ambience -4 dB
const DUCK_MUSIC_DB := -9.0
const DUCK_AMB_DB := -4.0
const DUCK_REF := 0.35
const FAR_DB := -14.0         # the ambience this much quieter when the 遠化 fills the view
const FAR_CUTOFF := 1100.0    # and muffled down to this
const POOL_2D := 16
const POOL_3D := 24
## the 2D core's step materials (region_data.gd) -> the step sounds rendered (v0.1's eight grounds)
const STEP_MAT := {"stone": "stone", "wood": "wood", "water": "water", "grass": "grass", "dirt": "soil",
	"soil": "soil", "sand": "sand", "moss": "moss", "leaves": "leaves", "gravel": "sand"}
const VOICES := ["tsuzumi", "saji", "shione", "old", "radio", "crow", "kago", "tsuzura"]

var sounds := {}               # id -> sounds.json entry
var amb: AudioAmbience
var mus: AudioMusic
## where 3D sounds are placed (the 3D sample's world root; its viewport must listen: attach_world sets that)
var world: Node3D = null
var played: Array = []         # recent plays: [id, variant, msec] (debug bridge, checks)
var play_count := {}           # id -> {variant: count} (the variation check counts what really played)
var _log: FileAccess = null    # -- --audio-log=PATH: one line per play (checks)
var _pools := {}               # id -> VariantPool
var _streams := {}             # file -> AudioStream (loaded once)
var _p2d: Array[AudioStreamPlayer] = []
var _n2d := 0
var _p3d: Array[AudioStreamPlayer3D] = []
var _n3d := 0
var _pf: Array[AudioStreamPlayer2D] = []   # 2D screens: sounds placed left or right of the middle
var _nf := 0
var _duck := 0.0
var _duck_target := 0.0
var _duck_speed := 4.0
var _far := 0.0
var _far_target := 0.0
var _hush := 1.0                 # v0.1's far wave: everything cut, then back (hush())
var _hush_t := 0.0
var _hush_back := 1.1
var _here := 0.0                 # how far the place she stands in is (far_here)
var _here_target := 0.0
var _far_logged := -1.0
var _far_fx: AudioEffectLowPassFilter
var _rng := RandomNumberGenerator.new()
# checks (tools/audio/check_mix.py): -- --audio-record=PATH.wav records the master bus (what the player hears) and
# writes it when the game quits, or after --audio-record-secs=N seconds (then quits)
var _rec_path := ""
var _rec_secs := 0.0
var _rec: AudioEffectRecord
var _rec_t := 0.0


## A sound's variants, never the same one twice running: a shuffled bag (each variant once per round), and the
## first of a new round is never the last of the old one.
class VariantPool:
	var n := 0
	var last := -1
	var bag: Array[int] = []
	var rng: RandomNumberGenerator

	func _init(count: int, r: RandomNumberGenerator) -> void:
		n = count
		rng = r

	func pick() -> int:
		if n <= 1:
			last = 0
			return 0
		if bag.is_empty():
			for i in n:
				bag.append(i)
			for i in range(n - 1, 0, -1):
				var j := rng.randi_range(0, i)
				var t := bag[i]
				bag[i] = bag[j]
				bag[j] = t
			if bag[0] == last:
				var t2 := bag[0]
				bag[0] = bag[n - 1]
				bag[n - 1] = t2
		last = bag.pop_front()
		return last


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rng.seed = Time.get_ticks_usec()
	for b in BUSES:
		if AudioServer.get_bus_index(b) < 0:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, b)
			AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	_setup_effects()
	_load_manifest()
	for i in POOL_2D:
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		_p2d.append(p)
	for i in 8:
		var q := AudioStreamPlayer2D.new()
		q.bus = "Ambience"
		q.attenuation = 0.0001
		q.max_distance = 1.0e6
		add_child(q)
		_pf.append(q)
	amb = AudioAmbience.new()
	amb.name = "Ambience"
	add_child(amb)
	mus = AudioMusic.new()
	mus.name = "Music"
	add_child(mus)
	apply_volumes()
	GameState.settings_changed.connect(func(key: String, _v) -> void:
		if key.begins_with("vol_"):
			apply_volumes())
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--audio-log="):
			_log = FileAccess.open(a.substr(12), FileAccess.WRITE)
		elif a.begins_with("--audio-record="):
			_rec_path = a.substr(15)
		elif a.begins_with("--audio-record-secs="):
			_rec_secs = float(a.substr(20))
	if _rec_path != "":
		_start_recording()


func _start_recording() -> void:
	_rec = AudioEffectRecord.new()
	_rec.format = AudioStreamWAV.FORMAT_16_BITS
	AudioServer.add_bus_effect(0, _rec)
	_rec.set_recording_active(true)
	print("AUDIO recording the master bus to %s" % _rec_path)
	if _log != null:
		# the plays log's clock (ms since the engine started) at the recording's first sample (checks align on it)
		_log.store_line(JSON.stringify([Time.get_ticks_msec(), "_rec", 0]))


func _save_recording() -> void:
	if _rec == null or not _rec.is_recording_active():
		return
	var w := _rec.get_recording()
	_rec.set_recording_active(false)
	if w != null:
		w.save_to_wav(_rec_path)
		print("AUDIO recording saved: %s (%.1f s)" % [_rec_path, w.get_length()])
	if _log != null:
		_log.flush()


## Quitting (the window closed, or the tree torn down): every player stopped and every stream let go, so no
## playback is left in the audio server when the engine shuts down (knowledge/16 §12: late callbacks at exit).
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_EXIT_TREE or what == NOTIFICATION_PREDELETE:
		_save_recording()
		stop_all()


func stop_all() -> void:
	for p in _p2d:
		if is_instance_valid(p):
			p.stop()
			p.stream = null
	for p in _p3d:
		if is_instance_valid(p):
			p.stop()
			p.stream = null
	for q in _pf:
		if is_instance_valid(q):
			q.stop()
			q.stream = null
	if amb != null and is_instance_valid(amb):
		amb.stop_all()
	if mus != null and is_instance_valid(mus):
		mus.stop_all()
	_streams.clear()


## v0.1's glue compressor (threshold -15 dB, ratio 3, 6 ms / 280 ms) on the music only: on the whole mix, as in
## v0.1, it pulled the brook down whenever the wind swelled (the brook-and-wind check, G5R3-65 2.3: -0.67 dB a gust
## at wind 0.9 in the game; v0.1 itself swung 0.7-1.0 dB). Wind, water, rain and her steps are separate sources and
## share no dynamics; the master has only a hard limiter at -1 dBTP so nothing ever clips. The ambience's 遠化
## low-pass.
func _setup_effects() -> void:
	var m := 0
	var mi := AudioServer.get_bus_index("Music")
	if mi >= 0 and not _has_effect(mi, "AudioEffectCompressor"):
		var c := AudioEffectCompressor.new()
		c.threshold = -15.0
		c.ratio = 3.0
		c.attack_us = 6000.0
		c.release_ms = 280.0
		c.gain = 0.0
		AudioServer.add_bus_effect(mi, c)
	if not _has_effect(m, "AudioEffectHardLimiter"):
		var l := AudioEffectHardLimiter.new()
		l.ceiling_db = -1.0
		AudioServer.add_bus_effect(m, l)
	var ai := AudioServer.get_bus_index("Ambience")
	if ai >= 0:
		_far_fx = AudioEffectLowPassFilter.new()
		_far_fx.cutoff_hz = 20000.0
		AudioServer.add_bus_effect(ai, _far_fx)


func _has_effect(bus: int, cls: String) -> bool:
	for i in AudioServer.get_bus_effect_count(bus):
		if AudioServer.get_bus_effect(bus, i).is_class(cls):
			return true
	return false


func _load_manifest() -> void:
	var f := FileAccess.open(MANIFEST, FileAccess.READ)
	if f == null:
		push_warning("Audio: no %s" % MANIFEST)
		return
	var d: Variant = JSON.parse_string(f.get_as_text())
	if d is Dictionary:
		sounds = (d as Dictionary).get("sounds", {})


func apply_volumes() -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(float(GameState.setting("vol_master")), 0.0001) * maxf(_hush, 0.00001)))
	for b in BUSES:
		_apply_bus(b)


func _apply_bus(b: String) -> void:
	var i := AudioServer.get_bus_index(b)
	if i < 0:
		return
	var v := float(GameState.setting("vol_" + String(b).to_lower()))
	var db := linear_to_db(maxf(v, 0.0001))
	if b == "Music":
		db += duck_db("Music")
		if amb != null and not amb.solo.is_empty() and not amb.solo.has("music"):
			db = -80.0
	elif b == "Ambience":
		db += duck_db("Ambience") + FAR_DB * _far
	AudioServer.set_bus_volume_db(i, db)


func _process(dt: float) -> void:
	if _rec != null and _rec_secs > 0.0:
		_rec_t += dt
		if _rec_t >= _rec_secs:
			_rec_secs = 0.0
			_save_recording()
			get_tree().quit()
	_duck = move_toward(_duck, _duck_target, _duck_speed * dt)
	_far = move_toward(_far, _far_target, dt / 1.2)
	_here = move_toward(_here, _here_target, dt / 2.0)
	if _hush < 1.0 or _hush_t > 0.0:
		if _hush_t > 0.0:
			_hush_t -= dt
			_hush = 0.0
		else:
			# v0.1: setTargetAtTime(1, tc 1.1)
			_hush = 1.0 - (1.0 - _hush) * exp(-dt / _hush_back)
			if _hush > 0.999:
				_hush = 1.0
		AudioServer.set_bus_volume_db(0, linear_to_db(maxf(float(GameState.setting("vol_master")), 0.0001) * maxf(_hush, 0.00001)))
	_apply_bus("Music")
	_apply_bus("Ambience")
	if _far_fx:
		_far_fx.cutoff_hz = 20000.0 * pow(FAR_CUTOFF / 20000.0, _far)
	if absf(_far - _far_logged) >= 0.05 or (_far == _far_target and _far != _far_logged):
		_far_logged = _far
		print("AUDIO far=%.2f ambience_db=%+.1f lowpass_hz=%.0f" % [_far, FAR_DB * _far, _far_fx.cutoff_hz if _far_fx else 20000.0])


# ------------------------------------------------------------------ mixing state

## How far the dialogue ducking has pulled a bus down now (dB): Music -9, Ambience -4 at duck(0.35).
func duck_db(bus: String) -> float:
	var k := clampf(_duck / DUCK_REF, 0.0, 2.0)
	if bus == "Music":
		return DUCK_MUSIC_DB * k
	if bus == "Ambience":
		return DUCK_AMB_DB * k
	return 0.0


func duck(amount: float, dur: float = 0.3) -> void:
	_duck_target = clampf(amount, 0.0, 0.95)
	_duck_speed = absf(_duck_target - _duck) / maxf(0.01, dur)
	if _log != null:
		_log.store_line(JSON.stringify([Time.get_ticks_msec(), "_duck", _duck_target]))


## The 遠化 fills k (0..1) of what she looks at (world3d/vista3d.gd): the ambience recedes, quieter and muffled,
## and comes back as she turns away; the music leaves it (5e).
func far(k: float) -> void:
	_far_target = clampf(k, 0.0, 1.0)


func far_now() -> float:
	return _far


## v0.1's far wave ends in a hard cut: everything silent for `silent` seconds, then back (time constant `back`).
func hush(silent: float = 2.4, back: float = 1.1) -> void:
	_hush = 0.0
	_hush_t = silent
	_hush_back = back
	apply_volumes()


## She stands in a place the 遠化 has taken k (0..1) of: the music leaves (5e, G5R3-65: no music in the 遠化;
## it is gone from 0.5) and the air thins as v0.1's nearness did (AudioAmbience reads 1 - k).
func far_here(k: float) -> void:
	_here_target = clampf(k, 0.0, 1.0)


func far_here_now() -> float:
	return _here


## The music's level in the 遠化 (5e): 1 outside, 0 from k = 0.5 in.
static func music_in_far(k: float) -> float:
	return 1.0 - AudioAmbience.sstep(0.15, 0.5, k)


# ------------------------------------------------------------------ the world (3D placement)

## The 3D sounds go into this world (its viewport made to listen); null: back to 2D.
func attach_world(root: Node3D) -> void:
	if world == root:
		return
	for p in _p3d:
		if is_instance_valid(p):
			p.queue_free()
	_p3d.clear()
	world = root
	if root == null:
		return
	var vp := root.get_viewport()
	if vp:
		vp.audio_listener_enable_3d = true
	for i in POOL_3D:
		var p := AudioStreamPlayer3D.new()
		p.name = "Sound3D_%d" % i
		p.bus = "SFX"
		root.add_child(p)
		_p3d.append(p)
	amb.world_changed()


func detach_world(root: Node3D) -> void:
	if world == root:
		_p3d.clear()
		world = null
		amb.world_changed()


# ------------------------------------------------------------------ playing

func has(id: String) -> bool:
	return sounds.has(id)


func _pool(id: String) -> VariantPool:
	var p: VariantPool = _pools.get(id)
	if p == null:
		p = VariantPool.new((sounds[id]["files"] as Array).size(), _rng)
		_pools[id] = p
	return p


func stream_of(file: String) -> AudioStream:
	var s: AudioStream = _streams.get(file)
	if s == null:
		s = load(file) as AudioStream
		_streams[file] = s
	return s


## Choose a variant of id (or the given one) -> [stream, volume_db, pitch_scale, variant index], or [] if unknown.
func choose(id: String, opts: Dictionary = {}) -> Array:
	if not sounds.has(id):
		return []
	var e: Dictionary = sounds[id]
	var files: Array = e["files"]
	if files.is_empty():
		return []
	var vi := int(opts["variant"]) % files.size() if opts.has("variant") else _pool(id).pick()
	var file := String(files[vi])
	var db := float(opts.get("db", 0.0)) + float((e.get("gain_db", {}) as Dictionary).get(file, 0.0))
	var vj := float(e.get("vol_jitter_db", 0.0))
	if vj > 0.0 and not opts.has("variant"):
		db += _rng.randf_range(-vj, vj)
	var pitch := float(opts.get("pitch", 1.0))
	var pj := float(e.get("pitch_jitter", 0.0))
	if pj > 0.0 and not opts.has("variant"):
		pitch *= pow(2.0, _rng.randf_range(-pj, pj) / 12.0)
	_note(id, vi)
	return [stream_of(file), db, pitch, vi]


func _note(id: String, vi: int) -> void:
	played.append([id, vi, Time.get_ticks_msec()])
	if played.size() > 64:
		played.pop_front()
	var c: Dictionary = play_count.get(id, {})
	c[vi] = int(c.get(vi, 0)) + 1
	play_count[id] = c
	if _log != null:
		_log.store_line(JSON.stringify([Time.get_ticks_msec(), id, vi]))


## A sound in 2D (at the listener): menus, the dialogue, her own verbs. Returns the player (or null).
func play(id: String, opts: Dictionary = {}) -> AudioStreamPlayer:
	var c := choose(id, opts)
	if c.is_empty():
		return null
	var p := _p2d[_n2d]
	_n2d = (_n2d + 1) % _p2d.size()
	p.stream = c[0]
	p.bus = String(opts.get("bus", _bus_for(id)))
	p.volume_db = c[1]
	p.pitch_scale = maxf(0.05, c[2])
	p.play(float(opts.get("from", 0.0)))
	return p


## A sound placed in the world (3D, attach_world); on a screen without one it plays in 2D. opts: db, pitch,
## unit (m, full level within), max (m, silent beyond), bus, variant.
func play_at(id: String, pos: Vector3, opts: Dictionary = {}) -> AudioStreamPlayer3D:
	if world == null or _p3d.is_empty():
		play(id, opts)
		return null
	var c := choose(id, opts)
	if c.is_empty():
		return null
	var p := _p3d[_n3d]
	_n3d = (_n3d + 1) % _p3d.size()
	if not is_instance_valid(p):
		return null
	p.stream = c[0]
	p.bus = String(opts.get("bus", _bus_for(id)))
	p.volume_db = c[1]
	p.pitch_scale = maxf(0.05, c[2])
	p.unit_size = float(opts.get("unit", 6.0))
	p.max_distance = float(opts.get("max", 40.0))
	p.max_db = 0.0
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.attenuation_filter_cutoff_hz = float(opts.get("cutoff", 6500.0))
	p.attenuation_filter_db = float(opts.get("filter_db", -12.0))
	p.global_position = pos
	p.play()
	return p


## A sound on a 2D screen, a little left or right of the middle (pan -1..1).
func play_pan(id: String, pan: float, opts: Dictionary = {}) -> void:
	var c := choose(id, opts)
	if c.is_empty():
		return
	var q := _pf[_nf]
	_nf = (_nf + 1) % _pf.size()
	var vp := get_viewport()
	var w := float(vp.get_visible_rect().size.x) if vp else 640.0
	q.position = (vp.get_visible_rect().size * 0.5 if vp else Vector2(320, 180)) + Vector2(clampf(pan, -1.0, 1.0) * w * 0.5, 0.0)
	q.stream = c[0]
	q.bus = String(opts.get("bus", _bus_for(id)))
	q.volume_db = c[1]
	q.pitch_scale = c[2]
	q.play()


func _bus_for(id: String) -> String:
	var g := String(sounds.get(id, {}).get("group", ""))
	match g:
		"music", "stinger":
			return "Music"
		"voice":
			return "Voice"
		"creature", "bed", "weather", "festival":
			return "Ambience"
	return "SFX"


# ------------------------------------------------------------------ the old calls (2D core, story, shells)

func sfx(name: String, opts: Dictionary = {}) -> void:
	var k := String(opts.get("k", ""))
	match name:
		"take", "give", "release":
			play(name)
			if k != "":
				play("qual_%s_%s" % [k, name])
		"regain":
			play("qual_%s_take" % (k if k != "" else "s"), {"db": -4.0})
		"ignite":
			play("qual_h_give")
		"deny":
			play("deny")
		"ui":
			play("ui_move", {"db": -2.0})
		_:
			if sounds.has(name):
				play(name, opts)


func blip(voice: String, i: int = 0) -> void:
	var v := voice if voice in VOICES else "tsuzumi"
	play("blip_" + v, {"variant": posmod(i, 12)})


## The 2D core's steps (BodyState.step_sound(): volume, pitch, extra "thud" (heavy) or "drum" (音)).
func footstep(material: String, params: Dictionary = {}) -> void:
	var vol := float(params.get("volume", 1.0))
	if vol <= 0.0:
		return
	var m := String(STEP_MAT.get(material, "grass"))
	var o := {"db": linear_to_db(vol), "pitch": float(params.get("pitch", 1.0))}
	play("step_%s_walk" % m, o)
	match String(params.get("extra", "")):
		"thud":
			play("step_heavy")
		"drum":
			play("step_drum")


## Her steps in 3D (the showcase's driver): material from AudioGround, gait walk or run.
func footstep_at(material: String, pos: Vector3, run: bool = false, opts: Dictionary = {}) -> void:
	var m := String(STEP_MAT.get(material, "grass"))
	var o := opts.duplicate()
	o["unit"] = float(opts.get("unit", 3.0))
	o["max"] = float(opts.get("max", 25.0))
	play_at("step_%s_%s" % [m, "run" if run else "walk"], pos, o)


## A screen changes (the showcase's open()): the festival goes, nothing is far, nothing ducked.
func reset_scene() -> void:
	mus.festival(0.0, 0.0, 0.4)
	far(0.0)
	far_here(0.0)
	duck(0.0, 0.3)


func ambience(names: Array, _fade: float = 2.0) -> void:
	amb.preset(names)


## Recorded calls are gone (G5R3-53); the birds and crows come from AudioAmbience now, from where they are.
func spot(_name: String, _volume_db: float = -4.0) -> void:
	pass


func music(name: String, opts: Dictionary = {}) -> void:
	mus.play(name, float(opts.get("fade", 1.5)), bool(opts.get("restart", false)))


func stinger(name: String) -> void:
	play("sting_" + name, {"bus": "Music"})


func festival(a: float, near: float = 0.0, fade: float = 1.2) -> void:
	mus.festival(a, near, fade)
