class_name W3Lamps
extends Node
## Lanterns and fires of the 3D pixel renderer, lit by the renderer itself instead of engine lights
## (docs/knowledge/21-3d-pixel-render.md §5, lamps). The Mobile renderer gives each object at most
## eight point lights, and its falloff summed and quantised drew one flat "stage light" over a row of
## lanterns. Here every lamp lives in a small data texture (the global `w3_lamps`, 2 rows: position
## and reach; colour times energy and the lit amount), and the world's shaders step each lamp's light
## themselves (w3_lamp_light in pixel_toon.gdshaderinc): a warm core, three rings stepping down and
## turning orange, the outermost meeting the dark; lamps combine by their brightest, so a row of
## lanterns reads as a row of pools with darker gaps between them.
## Lamps light up one after another when the evening comes (or go out at dawn), each over ~1.2 s.

const MAX := 64

var enabled := true            # false: no lamp light at all (debugging, --nolamps)
var lamps: Array = []          # {pos, reach, col (Color, linear, times energy), on, want, delay, flicker}
var _img := Image.create(MAX, 2, false, Image.FORMAT_RGBAF)
var _tex: ImageTexture
var _t := 0.0


func _ready() -> void:
	_tex = ImageTexture.create_from_image(_img)
	RenderingServer.global_shader_parameter_set("w3_lamps", _tex)
	RenderingServer.global_shader_parameter_set("w3_lamp_n", 0.0)


## A lamp at a world point. reach: metres to the end of its light; col: its colour (linear);
## energy: the core's strength (1 lights a mid-grey ground to about L* 60). flicker: 0 still .. 1 a
## live flame.
func add(pos: Vector3, reach: float, col: Color, energy: float, flicker := 0.15, manual := false) -> int:
	lamps.append({"pos": pos, "reach": reach, "col": Color(col.r * energy, col.g * energy, col.b * energy),
		"on": 0.0, "want": 0.0, "delay": 0.0, "flicker": flicker, "phase": float(lamps.size()) * 1.618,
		"manual": manual})
	return lamps.size() - 1


## A lamp that something else drives (a wandering will-o'-wisp): its place and how lit it is.
func set_lamp(i: int, pos: Vector3, on: float) -> void:
	var l: Dictionary = lamps[i]
	l["pos"] = pos
	l["on"] = on
	l["want"] = on


## Turn the lamps on (or off). stagger > 0: one after another, that many seconds apart, each fading
## in over `fade` seconds; instant = true sets them at once (a still, a jump in time).
func set_on(on: bool, instant := false, stagger := 0.18, fade := 1.2) -> void:
	var order := range(lamps.size())
	for i in order:
		var l: Dictionary = lamps[i]
		if l["manual"]:
			continue
		var w := 1.0 if on else 0.0
		if instant:
			l["on"] = w
			l["want"] = w
			l["delay"] = 0.0
		elif absf(float(l["want"]) - w) > 0.01:
			l["want"] = w
			l["delay"] = float(i) * stagger
		l["fade"] = fade


func update(dt: float) -> void:
	_t += dt
	var n := 0
	if not enabled:
		RenderingServer.global_shader_parameter_set("w3_lamp_n", 0.0)
		return
	for l in lamps:
		if l["manual"]:
			pass
		elif float(l["delay"]) > 0.0:
			l["delay"] = float(l["delay"]) - dt
		else:
			var f := float(l.get("fade", 1.2))
			l["on"] = move_toward(float(l["on"]), float(l["want"]), dt / maxf(f, 0.01))
		var on := float(l["on"])
		if on <= 0.001 or n >= MAX:
			continue
		var p: Vector3 = l["pos"]
		var c: Color = l["col"]
		# a live flame breathes a little (whole steps of the rings shift only rarely)
		var fl := 1.0 + float(l["flicker"]) * (0.06 * sin(_t * 7.3 + float(l["phase"])) + 0.04 * sin(_t * 13.1 + float(l["phase"]) * 2.0))
		var k := on * fl
		_img.set_pixel(n, 0, Color(p.x, p.y, p.z, float(l["reach"])))
		_img.set_pixel(n, 1, Color(c.r * k, c.g * k, c.b * k, on))
		n += 1
	_tex.update(_img)
	RenderingServer.global_shader_parameter_set("w3_lamp_n", float(n))
