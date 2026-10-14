class_name VistaTower
extends Node2D
## The insert of the 「隔」 tower on the summit ridge (src/vista/tower.js, HEAD), baked by tools/vista at
## its fixed hour: from the canopy, north-north-east to the ridge, the steel lattice tower with its
## red aviation lamp, the old tunnel's ventilation shaft, the sky shore's light behind the ridge.
##   state.tower: 1 = blinking (1.5 s cycle, 0.4 s on). Set 0: one last blink a beat later, a little
##   longer, guttering, then dark for good. (The lamp now blooms: it is a light source.)
## Layout for any logical view: the land (sky, ridge, tower) keeps the JS frame's place above the
## view's bottom, centred; the faint hanging sky shore hangs from the top; the framing leaves stick to
## their corners.

var data: VistaData
var m: Dictionary
var view := Vector2i(480, 270)
var exact := false
var quality := "high"
var js_lamps := false
var env: VistaEnv
var anchors := {}
var figure: Node2D = null

var land_g: Node2D
var sky: Sprite2D
var land: Sprite2D
var ghost: VistaQuad
var leaves := {}
var stars: VistaPoints
var lamp: VistaPoints
var light: VistaLightBuffer
var _prev_on = null
var _dying := false
var _dying_t := 0.0
var _dead := false
var _last_t := -1.0


func setup(p_data: VistaData) -> void:
	data = p_data
	m = data.meta
	name = "Tower"
	env = VistaEnv.at(21.0)
	land_g = Node2D.new()
	land_g.name = "Land"
	add_child(land_g)
	sky = _sprite("Sky", "sky", land_g)
	stars = VistaPoints.new(0, preload("res://vista/shaders/stars.gdshader"))
	stars.name = "Stars"
	var list: Array = data.lists.get("stars", [])
	stars.resize(list.size())
	for i in list.size():
		var st: Array = list[i]
		stars.put(i, [st[0], st[1], st[6], st[7], st[2], st[8]], Color(st[3] / 255.0, st[4] / 255.0, st[5] / 255.0, 1.0))
	stars.commit()
	stars.set_param("sky_from_tex", true)
	stars.set_param("sky_tex", data.tex("sky"))
	var oy := float(m["oy"])
	stars.set_param("fade_y0", oy + 270.0 * 0.62)
	stars.set_param("fade_y1", oy + 270.0 * 0.3)
	land_g.add_child(stars)
	# the ghost shore hangs from the view's top but is drawn between the sky and the ridge: it sits in
	# the land group and is placed back against the group's offset every frame
	var gt := data.tex("ghost")
	ghost = VistaQuad.new(Vector2(gt.get_width(), gt.get_height()), preload("res://vista/shaders/over_sky.gdshader"))
	ghost.name = "Ghost"
	ghost.set_param("img", gt)
	ghost.set_param("sky_tex", data.tex("sky"))
	land_g.add_child(ghost)
	land = _sprite("Ridge", "land", land_g)
	# the lamp, in its own light buffer (it blooms)
	light = VistaLightBuffer.new(self, land_g, "Lamp", 0.7)
	lamp = VistaPoints.new(1, preload("res://vista/shaders/points.gdshader"))
	lamp.name = "Lamp"
	var lp: Dictionary = m["lamp"]
	lamp.put(0, [float(lp["x"]) + float(m["ox"]), float(lp["y"]) + oy, 4.0, 0.0, 0.0, 0.0])
	lamp.commit()
	light.root.add_child(lamp)
	for k in ["TL", "BL", "BR"]:
		leaves[k] = _sprite("Leaves" + k, "leaves" + k, self)


func _sprite(n: String, img: String, parent: Node) -> Sprite2D:
	var s := Sprite2D.new()
	s.name = n
	s.texture = data.tex(img)
	s.centered = false
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	parent.add_child(s)
	return s


func layout(p_view: Vector2i) -> void:
	view = p_view
	light.fit(view)


func update(st: Dictionary, t: float) -> void:
	var dt := 1.0 / 60.0 if _last_t < 0.0 else clampf(t - _last_t, 0.0, 0.1)
	_last_t = t
	var dxv := floorf((view.x - float(m["refW"])) / 2.0 + 0.5)
	var top := float(view.y) - float(m["refH"])           # the reference frame's top on screen
	land_g.position = Vector2(dxv - float(m["ox"]), top - float(m["oy"]))
	ghost.position = Vector2(dxv - float(m["ox"]), 0.0) - land_g.position
	ghost.set_param("sky_ofs", ghost.position)
	var c: Dictionary = m["corners"]
	leaves["TL"].position = Vector2(dxv + float(c["TL"]["x"]), float(c["TL"]["y"]))
	leaves["BL"].position = Vector2(dxv + float(c["BL"]["x"]), top + float(c["BL"]["y"]))
	leaves["BR"].position = Vector2(dxv + float(c["BR"]["x"]), top + float(c["BR"]["y"]))
	light.follow(land_g.position + Vector2.ONE)
	stars.set_param("t", t)
	# the lamp: a 1.5 s cycle, 0.4 s on; off: one last blink, then nothing (tower.js)
	var on := float(st.get("tower", 1.0)) > 0.5
	if _prev_on == null:
		_dead = not on
		_prev_on = on
	if _prev_on and not on:
		_dying = true
		_dying_t = 0.0
	if on and _dead:
		_dead = false
		_dying = false
	_prev_on = on
	var k := 0.0
	var ph := fposmod(t, 1.5) / 1.5
	if not _dead and not _dying:
		k = VistaEnv.smoothj(0.0, 0.04, ph) * (1.0 - VistaEnv.smoothj(0.22, 0.27, ph)) if ph < 0.27 else 0.0
	if _dying:
		_dying_t += dt
		var u := _dying_t - 0.35
		k = 0.0 if u < 0.0 else ((0.85 + 0.15 * sin(u * 60.0)) * (1.0 - VistaEnv.smoothj(0.3, 0.5, u)) if u < 0.5 else 0.0)
		if u > 0.6:
			_dying = false
			_dead = true
	lamp.set_param("lamp_k", k)
	lamp.set_param("lamp_state", 0.0 if _dead else 1.0)
	var lp: Dictionary = m["lamp"]
	anchors["lamp"] = Vector2(lp["x"], lp["y"]) + Vector2(dxv, top)
	anchors["shaft"] = Vector2(m["shaft"]["x"], m["shaft"]["y"]) + Vector2(dxv, top)


func vignette() -> Dictionary:
	return m["vignette"]
