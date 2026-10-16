extends Node
## Audio (autoload): buses Music, Ambience, SFX, Voice (audio/default_bus_layout.tres) and a small
## manager. Ambience is the CC0 field recordings (audio/ambience/*.ogg, exact loops built by
## tools/godot/build_audio.py; spots/*.ogg are one-shot calls). Feedback sounds (verbs, refusals,
## footsteps, voice blips) are synthesised here until the JS synth is rendered to OGG (godot-plan
## P5); every verb has a sound within one frame (the five-step spell feedback, CLAUDE.md §3).
##   Audio.ambience(["night", "night2"], 2.0)   crossfade to these loops
##   Audio.spot("birds_bulbul_a")               a one-shot call
##   Audio.sfx("take", {"k": "w"})              take / give / release / deny / ui / regain / ignite
##   Audio.blip("saji", i)                      a dialogue voice blip
##   Audio.footstep("stone", {"volume", "pitch", "extra"})   from BodyState.step_sound()
##   Audio.duck(0.35, 0.3)                      lower music and ambience under dialogue
##   Audio.far(k)                               the 遠化 fills k (0..1) of what she looks at: the ambience
##                                              recedes, quieter and muffled (world3d/vista3d.gd)

const RATE := 22050
const BUSES := ["Music", "Ambience", "SFX", "Voice"]
const VOICES := {
	"tsuzumi": {"f": 520.0, "wave": "tri"},
	"saji": {"f": 760.0, "wave": "square"},
	"shione": {"f": 400.0, "wave": "sine"},
}
const QUALITY_PITCH := {"w": 0.72, "h": 1.0, "l": 1.34, "s": 1.18, "v": 0.9}

var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _amb: Array[AudioStreamPlayer] = []
var _amb_names: Array = []
var _cache: Dictionary = {}
var _duck := 0.0
var _duck_target := 0.0
var _duck_speed := 4.0
var played: Array = []       # recent sounds (name, time) for the debug bridge
var _far := 0.0              # the 遠化's share of the view, eased (Audio.far)
var _far_target := 0.0
var _far_logged := -1.0
var _far_fx: AudioEffectLowPassFilter
const FAR_DB := -14.0         # the ambience this much quieter when the 遠化 fills the view
const FAR_CUTOFF := 1100.0    # and muffled down to this


func _ready() -> void:
	for b in BUSES:
		if AudioServer.get_bus_index(b) < 0:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, b)
			AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	for i in 10:
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		_players.append(p)
	for i in 2:
		var a := AudioStreamPlayer.new()
		a.bus = "Ambience"
		a.volume_db = -80.0
		add_child(a)
		_amb.append(a)
	# the 遠化's muffle on the ambience (open while nothing is far)
	var ai := AudioServer.get_bus_index("Ambience")
	if ai >= 0:
		_far_fx = AudioEffectLowPassFilter.new()
		_far_fx.cutoff_hz = 20000.0
		AudioServer.add_bus_effect(ai, _far_fx)
	apply_volumes()
	GameState.settings_changed.connect(func(key: String, _v) -> void:
		if key.begins_with("vol_"):
			apply_volumes())


func apply_volumes() -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(float(GameState.setting("vol_master"))))
	for b in BUSES:
		var i := AudioServer.get_bus_index(b)
		var v := float(GameState.setting("vol_" + String(b).to_lower()))
		AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.0001)))


func _process(dt: float) -> void:
	_duck = move_toward(_duck, _duck_target, _duck_speed * dt)
	var off := linear_to_db(maxf(0.0001, 1.0 - _duck))
	# (about a second to recede or to come back)
	_far = move_toward(_far, _far_target, dt / 1.2)
	for b in ["Music", "Ambience"]:
		var i := AudioServer.get_bus_index(b)
		var v := float(GameState.setting("vol_" + String(b).to_lower()))
		AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.0001)) + off + (FAR_DB * _far if b == "Ambience" else 0.0))
	if _far_fx:
		_far_fx.cutoff_hz = 20000.0 * pow(FAR_CUTOFF / 20000.0, _far)
	if absf(_far - _far_logged) >= 0.05 or (_far == _far_target and _far != _far_logged):
		_far_logged = _far
		print("AUDIO far=%.2f ambience_db=%+.1f lowpass_hz=%.0f" % [_far, FAR_DB * _far, _far_fx.cutoff_hz if _far_fx else 20000.0])


## The 遠化 fills k (0..1) of what she looks at (world3d/vista3d.gd): the ambience recedes, quieter and
## muffled, and comes back as she turns away. No new sound.
func far(k: float) -> void:
	_far_target = clampf(k, 0.0, 1.0)


func duck(amount: float, dur: float = 0.3) -> void:
	_duck_target = clampf(amount, 0.0, 0.95)
	_duck_speed = absf(_duck_target - _duck) / maxf(0.01, dur)


# ------------------------------------------------------------------ ambience

func ambience(names: Array, fade: float = 2.0) -> void:
	if names == _amb_names:
		return
	_amb_names = names.duplicate()
	# one loop per player; a second name rides on the other player (two layers at most)
	for i in _amb.size():
		var p := _amb[i]
		var tw := create_tween()
		if i < names.size():
			var s := load("res://audio/ambience/%s.ogg" % names[i]) as AudioStreamOggVorbis
			if s == null:
				continue
			s.loop = true
			if p.stream != s:
				p.stream = s
				p.volume_db = -60.0
				p.play()
			tw.tween_property(p, "volume_db", 0.0 if i == 0 else -6.0, fade)
		else:
			tw.tween_property(p, "volume_db", -80.0, fade)
			tw.tween_callback(p.stop)


func spot(name: String, volume_db: float = -4.0) -> void:
	var s := load("res://audio/spots/%s.ogg" % name) as AudioStream
	if s != null:
		_play(s, "Ambience", volume_db, 1.0, name)


func music(_name: String, _opts: Dictionary = {}) -> void:
	pass  # no music yet: the JS synth will be rendered to OGG (godot-plan P5)


# ------------------------------------------------------------------ feedback sounds

func sfx(name: String, opts: Dictionary = {}) -> void:
	var k := String(opts.get("k", ""))
	var pitch := float(QUALITY_PITCH.get(k, 1.0))
	match name:
		"take":
			_play(_synth("take", 440.0, 880.0, 0.12, "tri", 0.5), "SFX", -6.0, pitch, name)
		"give":
			_play(_synth("give", 880.0, 440.0, 0.14, "tri", 0.5), "SFX", -6.0, pitch, name)
		"release":
			_play(_synth("release", 300.0, 900.0, 0.22, "noise", 0.35), "SFX", -8.0, pitch, name)
		"regain":
			_play(_synth("regain", 660.0, 990.0, 0.18, "sine", 0.45), "SFX", -8.0, pitch, name)
		"deny":
			_play(_synth("deny", 180.0, 150.0, 0.16, "square", 0.3), "SFX", -10.0, 1.0, name)
		"ignite":
			_play(_synth("ignite", 200.0, 120.0, 0.4, "noise", 0.5), "SFX", -6.0, 1.0, name)
		"ui":
			_play(_synth("ui", 1200.0, 1200.0, 0.04, "sine", 0.3), "SFX", -14.0, 1.0, name)
		_:
			_play(_synth("ui", 1200.0, 1200.0, 0.04, "sine", 0.3), "SFX", -14.0, 1.0, name)


func blip(voice: String, i: int = 0) -> void:
	var v: Dictionary = VOICES.get(voice, VOICES["tsuzumi"])
	var s := _synth("blip_" + voice, v["f"], v["f"] * 0.92, 0.045, v["wave"], 0.4)
	_play(s, "Voice", -12.0, 1.0 + 0.04 * float((i * 7) % 5 - 2), "blip")


func footstep(material: String, params: Dictionary = {}) -> void:
	var vol := float(params.get("volume", 1.0))
	if vol <= 0.0:
		return
	var base := {"stone": 900.0, "wood": 500.0, "water": 1400.0, "grass": 700.0, "dirt": 600.0, "sand": 650.0}
	var f: float = base.get(material, 700.0)
	var s := _synth("step_" + material, f, f * 0.6, 0.06, "noise", 0.35)
	_play(s, "SFX", -18.0 + linear_to_db(vol), float(params.get("pitch", 1.0)), "step")
	match String(params.get("extra", "")):
		"thud":
			_play(_synth("thud", 90.0, 60.0, 0.12, "sine", 0.7), "SFX", -10.0, 1.0, "thud")
		"drum":
			_play(_synth("drum", 160.0, 110.0, 0.16, "sine", 0.8), "SFX", -8.0, 1.0, "drum")
			_play(_synth("chime", 880.0, 880.0, 0.12, "sine", 0.3), "SFX", -16.0, 1.0, "chime")


func _play(stream: AudioStream, bus: String, volume_db: float, pitch: float, label: String) -> void:
	var p := _players[_next]
	_next = (_next + 1) % _players.size()
	p.stream = stream
	p.bus = bus
	p.volume_db = volume_db
	p.pitch_scale = maxf(0.05, pitch)
	p.play()
	played.append([label, Time.get_ticks_msec()])
	if played.size() > 24:
		played.pop_front()


## A short synthesised tone or noise burst (cached by key).
func _synth(key: String, f0: float, f1: float, dur: float, wave: String, vol: float) -> AudioStreamWAV:
	if _cache.has(key):
		return _cache[key]
	var n := int(dur * RATE)
	var data := PackedByteArray()
	data.resize(n * 2)
	var phase := 0.0
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key)
	var lp := 0.0
	for i in n:
		var t := float(i) / RATE
		var k := t / dur
		phase += TAU * lerpf(f0, f1, k) / RATE
		var s := 0.0
		match wave:
			"square":
				s = 1.0 if sin(phase) >= 0.0 else -1.0
			"tri":
				s = 2.0 * absf(2.0 * (phase / TAU - floor(phase / TAU + 0.5))) - 1.0
			"noise":
				lp += (rng.randf_range(-1.0, 1.0) - lp) * clampf(lerpf(f0, f1, k) / RATE * 6.0, 0.02, 1.0)
				s = lp * 2.0
			_:
				s = sin(phase)
		var env := minf(1.0, t / 0.004) * pow(1.0 - k, 2.0)
		data.encode_s16(i * 2, int(clampf(s * env * vol, -1.0, 1.0) * 32767.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.stereo = false
	w.data = data
	_cache[key] = w
	return w
