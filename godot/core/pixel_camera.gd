class_name PixelCamera
extends RefCounted
## The camera, in world pixels (the centre of the view). PixelStage renders the world with the
## integer part and shifts the upscaled image by the remainder, so camera motion is smooth while
## every texel stays on the native pixel grid.
##
## Following her, the camera is pixel-locked to her snapped position whenever she moves: a
## sub-pixel camera over a sprite that steps in whole pixels makes the sprite shimmer against the
## screen (the character must never flicker; CLAUDE.md §3). The follow lag is kept in whole pixels
## while she walks and eases out sub-pixel smooth once she stands still. Cinematic moves (cam/shot)
## are fully sub-pixel.
##   follow(getter, {"speed": rate 1/s, "cut": bool})   getter() -> Vector2 world px
##   point(world_px, {"speed": rate 1/s, "cut": bool})

var pos := Vector2.ZERO            # exact camera centre (world px), what is rendered
var mode := "follow"
var speed := 6.0                   # exponential approach rate (1/s): lower is a slower crane
var bounds := Rect2()              # world px the view should stay inside (size 0: no clamp)
var view := Vector2(480, 270)      # logical view size (set by the stage)
var _getter: Callable
var _point := Vector2.ZERO
var _smooth := Vector2.ZERO        # unsnapped follow position
var _last_target := Vector2.INF


func follow(getter: Callable, opts: Dictionary = {}) -> void:
	_getter = getter
	mode = "follow"
	speed = float(opts.get("speed", 6.0))
	if opts.get("cut", false) and getter.is_valid():
		var t: Vector2 = getter.call()
		_smooth = t
		pos = _clamp(t.round())
	else:
		_smooth = pos


func point(world_px: Vector2, opts: Dictionary = {}) -> void:
	mode = "point"
	_point = world_px
	speed = float(opts.get("speed", 3.0))
	if opts.get("cut", false):
		pos = _clamp(world_px)


func update(dt: float) -> void:
	var k := 1.0 - exp(-speed * dt)
	if mode == "follow" and _getter.is_valid():
		var t: Vector2 = (_getter.call() as Vector2).round()
		var moving := _last_target != Vector2.INF and t != _last_target
		_last_target = t
		_smooth += (t - _smooth) * k
		var lag := _smooth - t
		pos = _clamp(t + (lag.round() if moving else lag))
	elif mode == "point":
		pos += (_point - pos) * k
		if pos.distance_to(_point) < 0.01:
			pos = _point
		pos = _clamp(pos)


func settled() -> bool:
	if mode == "point":
		return pos.distance_to(_clamp(_point)) < 0.5
	return true


func _clamp(p: Vector2) -> Vector2:
	if bounds.size == Vector2.ZERO:
		return p
	var out := p
	var half := view * 0.5
	for axis in 2:
		var lo: float = bounds.position[axis] + half[axis]
		var hi: float = bounds.end[axis] - half[axis]
		out[axis] = (bounds.position[axis] + bounds.end[axis]) * 0.5 if lo > hi else clampf(p[axis], lo, hi)
	return out
