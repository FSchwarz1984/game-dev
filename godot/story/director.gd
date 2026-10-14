class_name Director
extends RefCounted
## The director: await-based helpers for scenes, ported from src/story/cine.js. Every wait runs on
## the game clock, which the main loop advances with tick(dt): a paused game pauses the scene, and
## the tests drive it without a window. Waits resolve inside tick() (a signal emission resumes the
## awaiting scene at once), exactly like one real frame; nothing runs between frames.
##
## The world is reached only through `stage`, the screen only through `ui`, sound through `audio`
## (duck-typed; any of them may be null):
##   stage.actor(id) -> Actor-like {x, z, face, play(anim, opts) -> seconds, idle()}
##   stage.shot(name, opts) / stage.cam(x, z, opts) / stage.follow(opts) / stage.tod(hour)
##     opts: {"cut": bool, "speed": float (how fast the camera travels; lower is a slower crane)}
##   ui.say(lines) / card(head, sub, dur) / title(head, sub, dur) / sub(text, dur) /
##     fade(alpha, dur, color) / letterbox(on)       (the awaitable ones are coroutines)
##   audio.music(name, opts) / audio.sfx(name, opts)
##
##   var d := Director.new(stage, ui, audio)
##   d.scene(func(d): await d.wait(0.5); await d.move("saji", [Vector2(2, 0)]); await d.say([...]))

class Waiter:
	extends RefCounted
	signal done


var stage: Object
var ui: Object
var audio: Object
var t := 0.0
var rate := 1.0           # > 1 while the player holds the skip key
var running := 0          # scenes in progress
var _timers: Array = []   # [{"at": float, "w": Waiter}]
var _watches: Array = []  # [{"fn": Callable, "w": Waiter}]
var _touched: Dictionary = {}  # actors a scene moved or animated: handed back when scenes end


func _init(p_stage: Object = null, p_ui: Object = null, p_audio: Object = null) -> void:
	stage = p_stage
	ui = p_ui
	audio = p_audio


var busy: bool:
	get:
		return running > 0


## Advance the scene clock; called once per frame by the main loop.
func tick(dt: float) -> void:
	t += dt * rate
	if not _timers.is_empty():
		var due: Array = []
		var keep: Array = []
		for w in _timers:
			if w["at"] <= t:
				due.append(w)
			else:
				keep.append(w)
		if not due.is_empty():
			_timers = keep
			for w in due:
				(w["w"] as Waiter).done.emit()
	if not _watches.is_empty():
		var finished: Array = []
		for w in _watches.duplicate():
			var ok := true
			var r = (w["fn"] as Callable).call(dt)
			ok = bool(r)
			if ok:
				finished.append(w)
		if not finished.is_empty():
			_watches = _watches.filter(func(w): return not finished.has(w))
			for w in finished:
				(w["w"] as Waiter).done.emit()


## Drop every pending wait (back to the title): the scenes waiting on them never resume.
func reset() -> void:
	_timers = []
	_watches = []
	running = 0
	rate = 1.0
	_release_actors()


## Run a scene; `busy` is true until it ends. Actors the scene used return to their state machine
## when the last scene ends, whatever the scene left them doing.
func scene(fn: Callable) -> Variant:
	running += 1
	var r = await fn.call(self)
	running = maxi(0, running - 1)
	if running == 0:
		_release_actors()
	return r


func wait(s: float) -> void:
	var w := Waiter.new()
	_timers.append({"at": t + maxf(0.0, s), "w": w})
	await w.done


## Resolve when fn(dt) returns true; polled once per frame.
func until(fn: Callable) -> void:
	if bool(fn.call(0.0)):
		return
	var w := Waiter.new()
	_watches.append({"fn": fn, "w": w})
	await w.done


## Run fn(k) for k from 0 to 1 over `dur` seconds (smoothstep unless ease is false).
func tween(dur: float, fn: Callable, ease: bool = true) -> void:
	var t0 := t
	await until(func(_dt: float) -> bool:
		var k := clampf((t - t0) / maxf(1e-6, dur), 0.0, 1.0)
		fn.call(k * k * (3.0 - 2.0 * k) if ease else k)
		return k >= 1.0)


# ------------------------------------------------------------------ camera and world

func shot(name: String, opts: Dictionary = {}) -> void:
	if stage != null and stage.has_method("shot"):
		stage.shot(name, opts)


func cam(x: float, z: float, opts: Dictionary = {}) -> void:
	if stage != null and stage.has_method("cam"):
		stage.cam(x, z, opts)


func follow(opts: Dictionary = {}) -> void:
	if stage != null and stage.has_method("follow"):
		stage.follow(opts)


func tod(hour: float) -> void:
	if stage != null and stage.has_method("tod"):
		stage.tod(hour)


## Run the clock from hour a to b over dur seconds.
func timelapse(a: float, b: float, dur: float) -> void:
	await tween(dur, func(k: float) -> void: tod(a + (b - a) * k))


# ------------------------------------------------------------------ actors

func actor(id: String) -> Object:
	if stage == null or not stage.has_method("actor"):
		return null
	var a = stage.actor(id)
	if a != null:
		_touched[id] = a
	return a


## Walk an actor through points (Vector2(x, z) or [x, z]) at `speed` m/s; resolves on arrival.
## The actor faces its direction of travel and plays its walk loop meanwhile.
func move(id: String, points: Array, opts: Dictionary = {}) -> void:
	var a := actor(id)
	if a == null or points.is_empty():
		return
	var speed := float(opts.get("speed", 2.2))
	var anim := String(opts.get("anim", "walk"))
	var path: Array[Vector2] = []
	for p in points:
		path.append(p if p is Vector2 else Vector2(p[0], p[1]))
	# lambdas capture locals by value: progress lives in a shared dictionary
	var st := {"i": 0}
	if a.has_method("play"):
		a.play(anim, {"loop": true})
	await until(func(dt: float) -> bool:
		var step := speed * dt * rate
		while step > 0.0 and st["i"] < path.size():
			var target: Vector2 = path[st["i"]]
			var dx: float = target.x - a.x
			var dz: float = target.y - a.z
			var d := sqrt(dx * dx + dz * dz)
			if d > 1e-4:
				a.face = Proj.face_of_move(dx, dz)
			if d <= step:
				a.x = target.x
				a.z = target.y
				step -= d
				st["i"] += 1
			else:
				a.x += dx / d * step
				a.z += dz / d * step
				step = 0.0
		if st["i"] >= path.size():
			if a.has_method("idle"):
				a.idle()
			return true
		return false)


func face(id: String, dir: String) -> void:
	var a := actor(id)
	if a != null:
		a.face = dir


## Play a one-shot animation and resolve when it ends (or after `hold` seconds for loops).
func play(id: String, anim: String, opts: Dictionary = {}) -> void:
	var a := actor(id)
	if a == null:
		return
	var loop := bool(opts.get("loop", false))
	var hold := float(opts.get("hold", 0.0))
	var dur := 0.0
	if a.has_method("play"):
		dur = float(a.play(anim, {"loop": loop, "hold": hold}))
	await wait(hold if loop else maxf(dur, hold))


func _release_actors() -> void:
	for id in _touched:
		var a = _touched[id]
		if is_instance_valid(a) and a.has_method("end_scene"):
			a.end_scene()
	_touched.clear()


# ------------------------------------------------------------------ screen and sound

## lines: [{"who": "tsuzumi", "text": "..."}] (or several dictionaries as separate arguments).
func say(lines) -> void:
	if ui == null or not ui.has_method("say"):
		return
	var list: Array = lines if lines is Array else [lines]
	await ui.say(list)


func card(head: String, sub_text: String = "", dur: float = 3.6) -> void:
	if ui != null and ui.has_method("card"):
		await ui.card(head, sub_text, dur)


func title(head: String, sub_text: String = "", dur: float = 4.5) -> void:
	if ui != null and ui.has_method("title"):
		await ui.title(head, sub_text, dur)


func sub(text: String, dur: float = -1.0) -> void:
	if ui != null and ui.has_method("sub"):
		await ui.sub(text, dur)


func fade(alpha: float, dur: float = 0.6, color: Color = Color.BLACK) -> void:
	if ui != null and ui.has_method("fade"):
		await ui.fade(alpha, dur, color)


func letterbox(on: bool) -> void:
	if ui != null and ui.has_method("letterbox"):
		ui.letterbox(on)


func music(name: String, opts: Dictionary = {}) -> void:
	if audio != null and audio.has_method("music"):
		audio.music(name, opts)


func sfx(name: String, opts: Dictionary = {}) -> void:
	if audio != null and audio.has_method("sfx"):
		audio.sfx(name, opts)
