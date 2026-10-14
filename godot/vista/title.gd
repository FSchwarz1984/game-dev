class_name VistaTitle
extends Node2D
## The title backdrop (src/vista/title.js, HEAD), baked by tools/vista at its fixed hour: night under
## the great camphor, its canopy over the top of the frame rimmed by a moon half hidden in the leaves;
## below, the plain with its lamps, the Obon fires, flooded paddies holding the stars; a few pale jade
## reflections whose source is nowhere in the sky. Visual only (the menu belongs to the core); a calm
## space centre-left for the title: anchors()["text"].
## Live: twinkling stars, three groups of stars on the water, the moon's glitter, the jade
## reflections, flickering fires, two or three fireflies, the hanging sprays and the grass stirring.
## Layout for any logical view: the plain keeps the JS frame's place above the bottom, the canopy and
## the moon hang from the top, the grass runs along the bottom; centred.

var data: VistaData
var m: Dictionary
var view := Vector2i(480, 270)
var exact := false
var quality := "high"
var js_lamps := false
var env: VistaEnv
var anchors := {}
var figure: Node2D = null

var back_g: Node2D
var sky: Sprite2D
var moon: VistaQuad
var back: Sprite2D
var canopy: Sprite2D
var sprays: Array[Sprite2D] = []
var spray_d: Array = []
var grass: Array[Sprite2D] = []
var grass_d: Array = []
var stars: VistaPoints
var points: VistaPoints
var fires: VistaPoints
var light: VistaLightBuffer


func setup(p_data: VistaData) -> void:
	data = p_data
	m = data.meta
	name = "Title"
	env = VistaEnv.at(21.0)
	var ox := float(m["ox"])
	var oy := float(m["oy"])
	back_g = Node2D.new()
	back_g.name = "Back"
	add_child(back_g)
	sky = _sprite("Sky", "sky", back_g)
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
	stars.set_param("fade_y0", float(m["YH"]))
	stars.set_param("fade_y1", float(m["YH"]) - 30.0)
	back_g.add_child(stars)
	# the moon and its halo, over the sky in sRGB; placed against the top group every frame
	var mt := data.tex("moon")
	moon = VistaQuad.new(Vector2(mt.get_width(), mt.get_height()), preload("res://vista/shaders/over_sky.gdshader"))
	moon.name = "Moon"
	moon.set_param("img", mt)
	moon.set_param("sky_tex", data.tex("sky"))
	back_g.add_child(moon)
	back = _sprite("Plain", "back", back_g)
	# live lights of the plain, in a light buffer added onto it (before the canopy and the grass)
	light = VistaLightBuffer.new(self, back_g, "Plain", 0.25)
	var items: Array = []
	for w in data.lists.get("water", []):
		items.append([w[0], w[1], 0.0, w[3], float(int(floor(float(w[2]) * 5.0)) % 3), 0.0])
	for gl in data.lists.get("glitter", []):
		items.append([gl[0], gl[1], 1.0, gl[2], gl[3], 0.0])
	for h in data.lists.get("hook", []):
		items.append([h[0], h[1], 2.0, h[2], 0.0, 0.0])
	for fl in data.lists.get("flies", []):
		items.append([ox + float(fl[0]), oy + float(fl[1]), 3.0, fl[2], 0.0, 0.0])
	points = VistaPoints.new(items.size(), preload("res://vista/shaders/points.gdshader"))
	points.name = "Points"
	for i in items.size():
		points.put(i, items[i])
	points.commit()
	light.root.add_child(points)
	var fl_list: Array = data.lists.get("fires", [])
	fires = VistaPoints.new(fl_list.size(), preload("res://vista/shaders/lamps.gdshader"))
	fires.name = "Fires"
	for i in fl_list.size():
		var f: Array = fl_list[i]
		# lamp shader: x y | on ph | arr kind ; lit all night, never leaving
		fires.put(i, [f[0], f[1], -100.0, f[3], 9.0, f[2]], Color(0, 0, 0, 0))
	fires.commit()
	var never := Image.create(1, 1, false, Image.FORMAT_RF)
	never.fill(Color(-1.0e9, 0, 0, 0))
	fires.set_param("tdep", ImageTexture.create_from_image(never))
	fires.set_param("tod", 21.0)
	fires.set_param("wave", -1.0)
	light.root.add_child(fires)
	# the canopy overhead and its sprays (top group)
	canopy = _sprite("Canopy", "canopy", self)
	var k := 0
	for sp in data.lists.get("sprays", []):
		sprays.append(_sprite("Spray%d" % k, "spray%d" % k, self))
		spray_d.append(sp)
		k += 1
	k = 0
	for g in data.lists.get("grass", []):
		grass.append(_sprite("Grass%d" % k, "grass%d" % k, self))
		grass_d.append(g)
		k += 1


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


func update(_st: Dictionary, t: float) -> void:
	var ox := float(m["ox"])
	var dxv := floorf((view.x - float(m["refW"])) / 2.0 + 0.5)
	var top := float(view.y) - float(m["refH"])
	back_g.position = Vector2(dxv - ox, top - float(m["oy"]))
	light.follow(back_g.position + Vector2.ONE)
	# the top group: the reference frame's top-left at (dxv, 0)
	canopy.position = Vector2(dxv - float(m["mX"]), -float(m["mT"]))
	var mo: Dictionary = m["moon"]
	var hr := (moon.size.x - 1.0) / 2.0
	moon.position = Vector2(dxv + float(mo["x"]) - hr, float(mo["y"]) - hr) - back_g.position
	moon.set_param("sky_ofs", moon.position)
	for i in sprays.size():
		var sp: Dictionary = spray_d[i]
		var k := sin(t * 0.7 + float(sp["ph"])) + 0.35 * sin(t * 1.9 + float(sp["ph"]) * 2.0)
		sprays[i].position = Vector2(dxv + float(sp["x"]) + floorf(k * 0.8 + 0.5), float(sp["y"]) + floorf(maxf(0.0, k) * 0.6 + 0.5))
	for i in grass.size():
		var g: Dictionary = grass_d[i]
		var k := sin(t * 0.55 + float(g["ph"])) + 0.3 * sin(t * 1.7 + float(g["ph"]) * 3.0)
		grass[i].position = Vector2(dxv - ox - 2.0 + floorf(k * 0.9 + 0.5), float(view.y) - float(m["gh"]))
	var wg := Vector3.ZERO
	for k in 3:
		wg[k] = 0.45 + 0.55 * (0.5 + 0.5 * sin(t * (0.9 + k * 0.31) + k * 2.2))
	points.set_param("t", t)
	points.set_param("water_groups", wg)
	fires.set_param("t", t)
	stars.set_param("t", t)
	anchors["moon"] = Vector2(dxv + float(mo["x"]), float(mo["y"]))
	# the calm space for the title: between the canopy (hangs from the top) and the plain (stands on
	# the bottom), so halfway between where each would put it
	anchors["text"] = Vector2(dxv + float(m["text"]["x"]), floorf(float(m["text"]["y"]) + top / 2.0 + 0.5))


func vignette() -> Dictionary:
	return m["vignette"]
