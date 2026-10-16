class_name VistaSouth
extends Node2D
## The treetop vista south over the plain (prologue 「送魂夜」): the HEAD scene of the JS vista
## (src/vista/south.js), baked by tools/vista, drawn at native resolution in the Vista's HDR viewport;
## the rising lights are 8196ebf's (VistaRise). Layers, back to front (as south.js draw()):
##   far group (parallax 0.1): sky, stars, sky shore + its lights, cloud deck, ground (with the wave),
##     lights on the ground, river lanterns, the wave's curtain and motes, the rising lights
##   canopy group (parallax 1): crown behind her, stirring sprays, her figure, crown in front of her
##   near leaves (parallax 2.4 at 480x270, only while the camera rises out of the crown)
##   the end of the wave (white rising over everything, motes rushing past)
## Layout: the composition is the JS 480x270 frame; a larger logical view (integer scale, expand)
## shows more of the same world around it. The horizon sits where the JS put it for that height
## (yh = clamp(0.475 H, H - 165, H - 118)); the sky shore is baked for a few heights (it scaled with
## the frame in the JS) and the tallest class that fits is used.

const SH := {
	"sky": preload("res://vista/shaders/sky.gdshader"),
	"palette": preload("res://vista/shaders/palette.gdshader"),
	"ground": preload("res://vista/shaders/ground.gdshader"),
	"shore": preload("res://vista/shaders/shore.gdshader"),
	"deck": preload("res://vista/shaders/deck.gdshader"),
}

var data: VistaData
var m: Dictionary            # data.meta
var view := Vector2i(480, 270)
var cls: Dictionary = {}     # the height class in use
var cls_index := -1
var yh := 128                # horizon row on screen (pan 1)
var pan_d := 107.0           # camera rise over the pan (px at parallax 1)
var dx := 0                  # screen x of canvas x 0
var exact := false           # JS parity for checks: snap the hour to the JS palette keys, step the deck's hole

var far: Node2D
var canopy: Node2D
var sky: VistaQuad
var shore: VistaQuad
var deck: VistaQuad
var ground: VistaQuad
var back: VistaQuad
var front: VistaQuad
var near: VistaQuad
var stir: Array[VistaQuad] = []
var stir_ph: Array[float] = []
var stir_xy: Array[Vector2] = []
var figure: Node2D           # her sprite goes here (between the crown behind her and in front of her)
var env: VistaEnv
var anchors := {}            # screen px: branch (where she sits), stand (where she stands)
var reveal := 0.0
var closed := 1.0
var flux := 0.0
var oy_far := 0
var oy_canopy := 0
var lights: VistaSouthLights
var quality := "high"
var js_lamps := false         # lamps go out at once when their light leaves (the JS), for checks
# light buffers (sRGB units, added onto the scene like the JS 'lighter' canvas: composite.gdshader)
var add_shore: SubViewport
var add_main: SubViewport
var add_rise: SubViewport
var add_shore_root: Node2D
var add_main_root: Node2D
var add_rise_root: Node2D
var comp_shore: VistaQuad
var comp_main: VistaQuad
var comp_rise: VistaQuad
# how much of what passes 1.0 becomes HDR (= what the glow blooms): the gate and the rising sparks
# glow, the lamps on the plain stay almost as the JS clamped them (a dense town must not flare)
var excess_shore := 0.6
var excess_main := 0.06
var excess_rise := 0.45
var wave_fx: VistaSouthWave
var pose := "sit"


func setup(p_data: VistaData) -> void:
	data = p_data
	m = data.meta
	name = "South"
	far = Node2D.new()
	far.name = "Far"
	add_child(far)
	var wc := float(m["Wc"])
	sky = _quad("Sky", Vector2(wc, float(m["GH"])), "sky", far)
	sky.set_param("ref_x0", float(m["ox"]))
	sky.set_param("horizon", float(m["YL"]))
	lights = VistaSouthLights.new()
	lights.setup(self, far, quality)
	add_shore = _add_viewport("AddShore")
	add_shore_root = add_shore.get_child(0)
	add_main = _add_viewport("AddMain")
	add_main_root = add_main.get_child(0)
	add_rise = _add_viewport("AddRise")
	add_rise_root = add_rise.get_child(0)
	far.add_child(lights.layer("stars"))
	lights.stars.set_param("ref_x0", float(m["ox"]))
	lights.stars.set_param("horizon", float(m["YL"]))
	shore = _quad("Shore", Vector2.ZERO, "shore", far)
	shore.set_param("lut", data.tex("lutShore"))
	add_shore_root.add_child(lights.layer("shore"))
	comp_shore = _composite("ShoreLight", add_shore)
	deck = _quad("Deck", Vector2(wc, float(m["deckRows"])), "deck", far)
	deck.set_param("dens", data.tex("deck"))
	deck.set_param("lut", data.tex("lutCloud"))
	deck.set_param("cx", float(m["Cx"]))
	deck.set_param("yh", float(m["YL"]))
	deck.set_param("f", float(m["f"]))
	deck.set_param("hc", float(m["Hcl"]))
	deck.set_param("ya", float(m["deckYa"]))
	deck.set_param("yb", float(m["deckRows"]))
	deck.set_param("wc", wc)
	ground = _quad("Ground", Vector2(wc, float(m["GH"])), "ground", far)
	ground.set_param("ids", data.tex("ground"))
	ground.set_param("lut", data.tex("lutGround"))
	ground.set_param("lut_far", data.tex("lutFar"))
	ground.set_param("fade_map", data.tex("groundFade"))
	add_main_root.add_child(lights.layer("lamps"))
	add_main_root.add_child(lights.layer("river"))
	wave_fx = VistaSouthWave.new()
	wave_fx.setup(self, quality)
	add_main_root.add_child(wave_fx.curtain)
	add_main_root.add_child(wave_fx.motes)
	comp_main = _composite("PlainLight", add_main)
	add_rise_root.add_child(lights.layer("rise"))
	comp_rise = _composite("RisingLight", add_rise)

	canopy = Node2D.new()
	canopy.name = "Canopy"
	add_child(canopy)
	back = _foliage("Back", data.tex("canopyBack"), canopy)
	var strip := data.tex("stir")
	var i := 0
	for sp in data.lists.get("stir", []):
		var q := _quad("Stir%d" % i, Vector2(float(sp["w"]), float(sp["h"])), "palette", canopy)
		q.set_param("ids", strip)
		q.set_param("lut", data.tex("lutFoliage"))
		q.set_param("src_ofs", Vector2(26.0 * i, 0.0))
		stir.append(q)
		stir_ph.append(float(sp["ph"]))
		stir_xy.append(Vector2(float(sp["x"]), float(sp["y"])))
		i += 1
	figure = Node2D.new()
	figure.name = "Figure"
	canopy.add_child(figure)
	front = _foliage("Front", data.tex("canopyFront"), canopy)
	near = _foliage("Near", data.tex("near"), self)
	add_child(wave_fx.end_motes)
	env = VistaEnv.at(20.0)


func _quad(n: String, size: Vector2, shader: String, parent: Node) -> VistaQuad:
	var q := VistaQuad.new(size, SH[shader])
	q.name = n
	parent.add_child(q)
	return q


## A float buffer the lights are summed into (sRGB units, like the JS AddBuffer), rendered before
## the vista's own viewport (it is a child of it).
func _add_viewport(n: String) -> SubViewport:
	var v := SubViewport.new()
	v.name = n
	v.use_hdr_2d = true
	v.transparent_bg = true
	v.snap_2d_transforms_to_pixel = true
	v.snap_2d_vertices_to_pixel = true
	v.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	v.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	v.gui_disable_input = true
	v.size = Vector2i(482, 272)
	var r := Node2D.new()
	r.name = "Root"
	v.add_child(r)
	add_child(v)
	return v


## Adds a light buffer onto everything drawn so far (a fresh copy of the screen first).
func _composite(n: String, src: SubViewport) -> VistaQuad:
	var b := BackBufferCopy.new()
	b.name = n + "Copy"
	b.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
	far.add_child(b)
	var q := VistaQuad.new(Vector2(482, 272), preload("res://vista/shaders/composite.gdshader"))
	q.name = n
	q.set_param("add_tex", src.get_texture())
	far.add_child(q)
	return q


func _foliage(n: String, ids: Texture2D, parent: Node) -> VistaQuad:
	var q := _quad(n, Vector2(ids.get_width(), ids.get_height()), "palette", parent)
	q.set_param("ids", ids)
	q.set_param("lut", data.tex("lutFoliage"))
	return q


static func yh_of(h: int) -> int:
	return int(floor(clampf(h * 0.475, h - 165.0, h - 118.0) + 0.5))


## Fit the composition to a logical view (called on every size change).
func layout(p_view: Vector2i) -> void:
	view = p_view
	var vs := view + Vector2i(2, 2)
	for v in [add_shore, add_main, add_rise]:
		v.size = vs
	for q in [comp_shore, comp_main, comp_rise]:
		q.size = Vector2(vs)
	var h := view.y
	yh = yh_of(h)
	pan_d = maxf(40.0, floor(h - float(m["CT"]) - h * 0.36 + 0.5))
	dx = int(floor((view.x - float(m["refW"])) / 2.0 + 0.5)) - int(m["ox"])
	var classes: Array = m["classes"]
	var ci := 0
	for k in classes.size():
		if int(classes[k]["yh"]) <= yh:
			ci = k
	if ci != cls_index:
		cls_index = ci
		cls = classes[ci]
		var tex := data.tex("shore%d" % int(cls["H"]))
		shore.size = Vector2(tex.get_width(), tex.get_height())
		shore.position = Vector2(0, float(cls["y0"]))
		shore.set_param("ids", tex)
		shore.set_param("row0", float(cls["y0"]))
		shore.set_param("haze_edge", float(cls["hazeEdgeY"]))
		var hole: Dictionary = cls["hole"]
		deck.set_param("gate", Vector2(cls["T"][0], cls["T"][1]))
		deck.set_param("hole", Vector3(float(hole["X"]), float(hole["Z"]), 0.0))
		lights.build_for_class(ci)
		lights.shore.set_param("haze_edge", float(cls["hazeEdgeY"]))
	var fade: Array = cls["fade"]
	shore.set_param("fade", Vector2(fade[0], fade[1]) if yh > int(cls["yh"]) else Vector2(-1000, -999))
	sky.set_param("sky_s", maxf(110.0, yh * 1.1))
	lights.stars.set_param("sky_s", maxf(110.0, yh * 1.1))


## The gate's mouth in canvas coordinates (where the rising lights go in).
func gate() -> Vector2:
	return Vector2(cls["T"][0], cls["T"][1])


func tod_row(tod: float) -> float:
	if exact:
		tod = floor(tod * 20.0 + 0.5) / 20.0
	return clampf((tod - float(m["tod0"])) / float(m["todStep"]), 0.0, float(m["todRows"]) - 1.0)


## One frame: st = {tod, pan, rise, sky, wave, settled}; t is the vista clock.
func update(st: Dictionary, t: float) -> void:
	if cls_index < 0:
		layout(view)
	var tod := clampf(float(st.get("tod", 21.0)), 16.5, 24.0)
	var etod: float = floor(tod * 20.0 + 0.5) / 20.0 if exact else tod
	env = VistaEnv.at(etod)
	var row := tod_row(tod)
	var pan_k := VistaEnv.smoothj(0.0, 1.0, clampf(float(st.get("pan", 1.0)), 0.0, 1.0))
	var dy := (1.0 - pan_k) * pan_d
	var sky_k := clampf(float(st.get("sky", 0.0)), 0.0, 1.0)
	var wave := float(st.get("wave", -1.0))
	# the far has been and gone (G5R3-18): the land at its final stage of peeled blocks, no lamps, no
	# front, no curtain (the art sample's last frame)
	var settled := float(st.get("settled", 0.0)) > 0.5
	if settled:
		wave = -1.0
	var lamp_wave := 2.0 if settled else wave
	reveal = VistaEnv.smoothj(0.05, 0.75, sky_k)
	closed = 1.0 - VistaEnv.smoothj(0.15, 0.6, sky_k)

	# positions (whole native pixels): JS oFar = -round(dy * 0.1) - padTop, oC = round(H - CT - dy)
	oy_far = yh - int(m["YL"]) - int(floor(dy * 0.1 + 0.5))
	far.position = Vector2(dx, oy_far)
	# the light buffers see the far group where the vista's viewport does (1 px border)
	for r in [add_shore_root, add_main_root, add_rise_root]:
		r.position = far.position + Vector2.ONE
	for q in [comp_shore, comp_main, comp_rise]:
		q.position = -far.position - Vector2.ONE
	comp_shore.set_param("excess", excess_shore)
	comp_main.set_param("excess", excess_main)
	comp_rise.set_param("excess", excess_rise)
	oy_canopy = int(floor(view.y - float(m["CT"]) - dy + 0.5)) - int(m["oyC"])
	canopy.position = Vector2(dx, oy_canopy)
	# near leaves: JS oN = round(H + 4 - 2.4 dy). Its sprays were laid out for the frame's height, so on
	# a taller view (longer crane) they would hang in the open sky at pan 0; instead they keep the
	# reference frame's place against the crown at pan 0 (80 px above it) and the same 150 px of travel
	# past it, leaving the frame at pan 1 as in the JS
	var near_k := 2.4 if (exact or view.y <= int(m["refH"])) else (150.0 + pan_d) / pan_d
	var on := int(floor(view.y + 4.0 - dy * near_k + 0.5))
	near.position = Vector2(dx, on)
	near.visible = on < view.y

	# lights: departures and arrivals; the deck is lit from below by what is in the air
	var rise_k := clampf(float(st.get("rise", 0.0)), 0.0, 1.0)
	lights.update(rise_k, t)
	flux = clampf(lights.in_flight / 40.0, 0.0, 1.0) + 0.35 * minf(lights.flash, 1.5) * closed
	lights.lamps.set_param("tod", tod)
	lights.lamps.set_param("wave", lamp_wave)
	lights.lamps.set_param("js_off", 1.0 if js_lamps else 0.0)
	var sg := Vector3.ZERO
	for k in 3:
		sg[k] = 0.55 + 0.45 * sin(t * (1.1 + k * 0.37) + k * 2.1)
	lights.lamps.set_param("star_groups", sg)
	lights.rise.set_param("closed", closed)
	lights.stars.set_param("t", t)
	lights.stars.set_param("stars", env.stars)
	lights.stars.visible = env.stars > 0.02
	lights.shore.visible = reveal > 0.0
	lights.shore.set_param("t", t)
	lights.shore.set_param("reveal", reveal)
	lights.shore.set_param("inflow", lights.inflow)
	lights.shore.set_param("flash", lights.flash)
	lights.update_river(t, tod, rise_k, lamp_wave)
	lights.river.set_param("tod", tod)
	lights.river.set_param("wave", -1.0)
	# sky (the stars are mixed over the same painted sky)
	for n in [sky, lights.stars]:
		n.set_param("sky_z", env.sky_z)
		n.set_param("sky_up", env.sky_up)
		n.set_param("sky_lo", env.sky_lo)
		n.set_param("sky_ho", env.sky_ho)
		n.set_param("sky_glow", env.glow)
		n.set_param("glow_amt", env.glow_amt)
	comp_shore.visible = reveal > 0.0
	# sky shore
	shore.visible = reveal > 0.0
	if shore.visible:
		shore.set_param("tod_row", row)
		shore.set_param("reveal", reveal)
		shore.set_param("band_col", _band(row))
		shore.set_param("fade_col", (env.sky_z * 1.25).round().clamp(Vector3.ZERO, Vector3(255, 255, 255)))
	# cloud deck: the hole opens with the sky
	var hr := pow(sky_k, 1.15)
	if exact:
		hr = floor(hr * 32.0 + 0.5) / 32.0
	var hole: Dictionary = cls["hole"]
	deck.set_param("hole", Vector3(float(hole["X"]), float(hole["Z"]), hr * 9.5))
	deck.set_param("tod_row", row)
	deck.set_param("light_dir", Vector2(0.82 - 0.7 * env.night, 0.58 + 0.3 * env.night))
	deck.set_param("flux", flux)
	deck.set_param("reveal", reveal)
	# ground
	ground.set_param("tod_row", row)
	ground.set_param("wave", wave)
	ground.set_param("settled", 1.0 if settled else 0.0)
	# canopy: the sprays on the crown's edge stir in the evening air
	back.set_param("tod_row", row)
	front.set_param("tod_row", row)
	near.set_param("tod_row", row)
	for k in stir.size():
		var s := sin(t * 0.8 + stir_ph[k]) + 0.35 * sin(t * 2.1 + stir_ph[k] * 2.0)
		stir[k].position = stir_xy[k] + Vector2(floor(s * 0.8 + 0.5), floor(maxf(0.0, -s) * 0.6 + 0.5))
		stir[k].set_param("tod_row", row)
	# the wave's curtain, motes and end
	wave_fx.update(wave, t, _dt(t), view)
	# anchors (screen px) and her place: sitting on the limb, or standing on it
	var a: Dictionary = m["anchors"]
	anchors["branch"] = Vector2(a["branch"]["x"], a["branch"]["y"]) + canopy.position
	anchors["stand"] = Vector2(a["stand"]["x"], a["stand"]["y"]) + canopy.position
	pose = String(st.get("pose", "sit"))
	var at: Dictionary = a["branch"] if pose == "sit" else a["stand"]
	figure.position = Vector2(at["x"], at["y"])


func _band(row: float) -> Vector3:
	var b: Array = m["shoreBand"]
	var r0 := int(floor(row))
	var r1 := mini(r0 + 1, b.size() - 1)
	var a := Vector3(b[r0][0], b[r0][1], b[r0][2])
	return a.lerp(Vector3(b[r1][0], b[r1][1], b[r1][2]), row - r0)


var _last_t := -1.0


## The frame's dt from the vista clock (the update gets the clock, not the step).
func _dt(t: float) -> float:
	var d := 1.0 / 60.0 if _last_t < 0.0 else clampf(t - _last_t, 0.0, 0.1)
	_last_t = t
	return d
