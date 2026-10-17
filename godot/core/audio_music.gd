class_name AudioMusic
extends Node
## The music (Audio.mus): v0.1's pieces, rendered offline (godot/audio/music), played with v0.1's rules.
##   play("title" | "home" | "prologue" | "wonder" | "tension" | "explore" | "none", fade, restart)
## "explore" is v0.1's field music: mostly silence; after 8-22 s (later 25-70 s) one short phrase coloured by the
## hour (morning: flute over light koto; noon: koto alone, sparse; dusk: low shamisen; night: celesta or
## harmonics), never the same phrase twice running; a phrase always ends with its own tail. "wonder" plays once
## and gives the field back to "explore" (v0.1 musicEnded). The far festival (遠囃子) is a set of loops rendered
## in the same time line, one per intensity and nearness, crossfaded in step (festival()).
## No music in the 遠化 (5e, G5R3-65): where she stands in it (Audio.far_here) the level follows
## 1 - smoothstep(0.15, 0.5, k). Looking at the 遠化 from outside (Audio.far, the lookout) leaves the music be.

const PIECES := {"title": "mus_title", "home": "mus_home", "prologue": "mus_prologue", "wonder": "mus_wonder",
	"tension": "mus_tension"}
const MODES := ["morning", "noon", "dusk", "night"]
# The calibration (in-game recordings): v0.1's title piece made the menu -18 LUFS against a -25 walk; 4 dB down
# puts it about 2 LU above the field.
const LEVEL_DB := {"title": -4.0}
const FEST := [[0.4, 0.8, "fest_40_080"], [0.25, 0.6, "fest_25_060"], [0.1, 0.3, "fest_10_030"],
	[0.55, 1.0, "fest_55_100"], [0.35, 0.5, "fest_35_050"]]

var current := "none"
var previous := "none"
var rng := RandomNumberGenerator.new()
var _a: AudioStreamPlayer          # the piece now
var _a_db := 0.0                   # its own level (dB) before fades
var _a_gain := 0.0                 # 0..1 fade
var _a_target := 1.0
var _a_speed := 1.0
var _fading: Array = []            # [player, gain, per second, its own dB]: pieces on their way out
var _spare: Array[AudioStreamPlayer] = []
var _explore_next := -1.0          # when the next phrase starts (s on _clock); -1: not exploring
var _phrase_end := 0.0
var _clock := 0.0
var _fest: Array = []              # [AudioStreamPlayer, a, near, gain, target]
var _fest_speed := 1.0
var _fest_started := false
var phrases_played: Array = []     # [clock, file] (checks)


func _ready() -> void:
	rng.seed = Time.get_ticks_usec() ^ 0x2545f491
	_a = _player()


func _player() -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = "Music"
	p.volume_db = -80.0
	add_child(p)
	return p


func stop_all() -> void:
	current = "none"
	var all: Array = [_a]
	for f in _fading:
		all.append(f[0])
	for f in _fest:
		all.append(f[0])
	all.append_array(_spare)
	for p in all:
		if p != null and is_instance_valid(p):
			(p as AudioStreamPlayer).stop()
			(p as AudioStreamPlayer).stream = null
	_fading.clear()


func play(name: String, fade: float = 1.5, restart: bool = false) -> void:
	if name == current and not restart:
		return
	previous = current
	current = name
	# the old piece goes to the fading player
	_swap_out(maxf(0.05, fade))
	_explore_next = -1.0
	if name == "none":
		return
	if name == "explore":
		# v0.1: the first silence is 8-22 s; a phrase still ringing from a cut piece is left to end
		_explore_next = _clock + rng.randf_range(8.0, 22.0)
		return
	var id: String = PIECES.get(name, "")
	if id == "" or not Audio.has(id):
		push_warning("AudioMusic: no piece %s" % name)
		return
	var e: Dictionary = Audio.sounds[id]
	var st := Audio.stream_of(String(e["files"][0]))
	if st is AudioStreamOggVorbis:
		(st as AudioStreamOggVorbis).loop = bool(e.get("loop", false))
	_start(st, float(LEVEL_DB.get(name, 0.0)), maxf(0.05, fade * 0.6) if previous != "none" else 0.05)


func _swap_out(fade: float) -> void:
	if _a.playing:
		_fading.append([_a, _a_gain, 1.0 / fade, _a_db])
		_a = _spare.pop_back() if not _spare.is_empty() else _player()
	_a_gain = 0.0


func _start(st: AudioStream, db: float, fade: float) -> void:
	_a.stream = st
	_a_db = db
	_a_gain = 0.0 if fade > 0.06 else 1.0
	_a_target = 1.0
	_a_speed = 1.0 / fade
	_a.volume_db = -80.0
	_a.play()


func _process(dt: float) -> void:
	_clock += dt
	var far_k := Audio.music_in_far(Audio.far_here_now())
	# the piece and the one leaving
	_a_gain = move_toward(_a_gain, _a_target, _a_speed * dt)
	_a.volume_db = linear_to_db(maxf(1e-5, _a_gain * far_k)) + _a_db if _a.playing else -80.0
	for i in range(_fading.size() - 1, -1, -1):
		var f: Array = _fading[i]
		var pl: AudioStreamPlayer = f[0]
		f[1] = move_toward(float(f[1]), 0.0, float(f[2]) * dt)
		pl.volume_db = linear_to_db(maxf(1e-5, float(f[1]) * far_k)) + float(f[3])
		if float(f[1]) <= 0.0 or not pl.playing:
			pl.stop()
			_fading.remove_at(i)
			_spare.append(pl)
	# one-shot pieces end: wonder gives the field back (v0.1 musicEnded)
	if current in ["wonder"] and _a.stream != null and not _a.playing and _a_gain > 0.0:
		_a_gain = 0.0
		var back := "explore" if previous == "explore" else "none"
		current = "none"
		play(back, 0.1)
	# the field music: a phrase now and then
	if current == "explore" and _explore_next >= 0.0 and _clock >= _explore_next and not _a.playing:
		_phrase()
	_update_fest(dt, far_k)


func _mode() -> String:
	var h := float(Audio.amb.state.get("tod", 12.0))
	if h >= 5.0 and h < 11.0:
		return "morning"
	if h >= 11.0 and h < 16.5:
		return "noon"
	if h >= 16.5 and h < 19.5:
		return "dusk"
	return "night"


func _phrase() -> void:
	var id := "mus_explore_" + _mode()
	if not Audio.has(id):
		_explore_next = _clock + 30.0
		return
	var c := Audio.choose(id)
	if c.is_empty():
		return
	_a.stream = c[0]
	_a_db = c[1]
	_a_gain = 1.0
	_a_target = 1.0
	_a.play()
	var length := (c[0] as AudioStream).get_length()
	phrases_played.append([_clock, id, c[3]])
	# v0.1: then 25-70 s of nothing (counted from the phrase's end)
	_explore_next = _clock + length + rng.randf_range(25.0, 70.0)


# ------------------------------------------------------------------ the far festival

## v0.1's AU.festival(a, {near}): a = how much, near = how near (0 far and dark .. 1 close and clear). The loop
## rendered nearest to (a, near) comes up, the others go, all in one time line; a = 0 fades everything.
func festival(a: float, near: float = 0.0, fade: float = 1.2) -> void:
	_ensure_fest()
	var best := -1
	var bd := 1e9
	if a > 0.001:
		for i in FEST.size():
			var d := absf(float(FEST[i][0]) - a) * 2.0 + absf(float(FEST[i][1]) - near)
			if d < bd:
				bd = d
				best = i
	for i in _fest.size():
		_fest[i][4] = 1.0 if i == best else 0.0
	_fest_speed = 1.0 / maxf(0.05, fade)


func festival_level() -> float:
	var s := 0.0
	for f in _fest:
		s += float(f[3])
	return s


func _ensure_fest() -> void:
	if _fest_started:
		return
	_fest_started = true
	if not _fest.is_empty():
		for f in _fest:
			(f[0] as AudioStreamPlayer).play()
		return
	for row in FEST:
		var id := String(row[2])
		if not Audio.has(id):
			continue
		var p := _player()
		var st := Audio.stream_of(String(Audio.sounds[id]["files"][0]))
		if st is AudioStreamOggVorbis:
			(st as AudioStreamOggVorbis).loop = true
		p.stream = st
		_fest.append([p, float(row[0]), float(row[1]), 0.0, 0.0])
	# all in one time line: started in the same frame they begin on the same mix step
	for f in _fest:
		(f[0] as AudioStreamPlayer).play()


func _update_fest(dt: float, far_k: float) -> void:
	var any := false
	for f in _fest:
		f[3] = move_toward(float(f[3]), float(f[4]), _fest_speed * dt)
		(f[0] as AudioStreamPlayer).volume_db = linear_to_db(maxf(1e-5, float(f[3]) * far_k))
		any = any or float(f[3]) > 0.0 or float(f[4]) > 0.0
	# silent for good: stop decoding (they start again together, in one time line, at the next festival())
	if _fest_started and not any:
		for f in _fest:
			(f[0] as AudioStreamPlayer).stop()
		_fest_started = false
