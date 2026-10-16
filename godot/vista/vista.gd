class_name Vista
extends Control
## The side-view vistas of the prologue and the title: "south" (from the camphor's crown over the
## plain, dusk to night: the lights rise, the sky shore appears, the far comes up the mountain),
## "tower" (the insert of the 「隔」 tower on the summit ridge) and "title" (the backdrop of the title
## menu; the menu itself belongs to the core). Port of src/vista (HEAD) with the rising lights of
## 8196ebf (R-8, docs/knowledge/14).
##
## Put it on a CanvasLayer above the world (it is opaque and fills the logical canvas; hide the
## world meanwhile) and below the cinema layer (letterbox, fades) and the text layers. It renders in
## its own HDR viewport at native resolution (glow only on the light sources: they are the only
## values above 1). Its canvas is the one of the stage rule it was drawn for (480x270 base, round(h /
## 270)), shown at that rule's integer scale over the whole window whatever the stage's own canvas is
## (legacy_fit; `legacy = false` lays it out at the Control's size instead).
##
##   var v := Vista.new(); layer.add_child(v)
##   v.show_shot("south"); v.state.tod = 19.4 ...    or the timeline below, from a director scene
##   v.figure_slot()   a Node2D between the crown behind her and the leaves in front of her
##   v.anchors()       {branch, stand} in the vista's own px (where she sits / stands; she stands up
##                     where she sat); shown_scale / shown_origin map them to the stage's logical px
## State (as the JS vista): tod 17.5..21, pan 0..1 (crane out of the crown), rise 0..1 (the lights
## leave), sky 0..1 (the deck parts, the sky shore shows), wave -1 | 0..1 (the far), tower 1 | 0.
## The clock: by default the vista advances itself every frame (_process); a host that drives the
## director's clock (skip, pause) sets autoplay = false and calls advance(dt) with the same dt.

signal beat(name: String)

const BORDER := 1

var shot := ""
var state := {"tod": 19.4, "pan": 1.0, "rise": 0.0, "sky": 0.0, "wave": -1.0, "tower": 1.0, "pose": "sit"}
var t := 0.0
var autoplay := true
var exact := false            # JS parity mode (palette keys snapped, stepped deck hole): checks only
## Draw at the canvas of the stage rule the vista was made for and show it at that rule's integer
## scale (legacy_fit), whatever the stage's canvas is. False: the Control's own size is its canvas (for a
## host that sets the window's canvas to the vista's itself, or checks that lay it out by hand).
var legacy := true
var shown_scale := 1.0        # one vista pixel in the Control's (the stage's logical) pixels
var shown_origin := Vector2.ZERO
var quality := "auto"         # "high" | "low" | "auto" (low on phones): rising-light count, motes
var data_dir := VistaData.DEFAULT_DIR

var vp: SubViewport
var root: Node2D
var view_rect: TextureRect
var world_env: WorldEnvironment
var view := Vector2i.ZERO
var shots := {}
var _current: Node2D = null
var _own_director: Director = null   # play_standalone()'s, ticked with the vista's clock
var _figure: VistaFigure = null      # her sprite on the limb while it runs (follows state.pose)
var _wash_hold := -1.0               # >= 0: the white wash at this level whatever the wave (its ending)


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	vp = SubViewport.new()
	vp.name = "VistaViewport"
	vp.own_world_3d = true
	vp.use_hdr_2d = true
	vp.transparent_bg = false
	vp.snap_2d_transforms_to_pixel = true
	vp.snap_2d_vertices_to_pixel = true
	vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.gui_disable_input = true
	vp.handle_input_locally = false
	add_child(vp)
	world_env = WorldEnvironment.new()
	world_env.environment = _environment()
	vp.add_child(world_env)
	root = Node2D.new()
	root.name = "Root"
	root.position = Vector2(BORDER, BORDER)
	vp.add_child(root)
	view_rect = TextureRect.new()
	view_rect.name = "View"
	view_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	view_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	view_rect.stretch_mode = TextureRect.STRETCH_SCALE
	view_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	var mat := ShaderMaterial.new()
	mat.shader = preload("res://vista/shaders/display.gdshader")
	view_rect.material = mat
	view_rect.texture = vp.get_texture()
	add_child(view_rect)
	resized.connect(_fit)
	# the vista's canvas follows the window (legacy_fit), which can change while the stage's canvas does not
	get_window().size_changed.connect(_fit)
	_fit()
	if shot == "":
		show_shot("south")


## The glow of the light sources: tight levels (the lights are a pixel or two at native size), only
## above 1.0 (nothing painted reaches it; the cores of lights are pushed past it on purpose).
func _environment() -> Environment:
	var e := Environment.new()
	e.background_mode = Environment.BG_CANVAS
	e.glow_enabled = true
	e.glow_normalized = false
	e.set_glow_level(0, 1.0)
	e.set_glow_level(1, 0.8)
	e.set_glow_level(2, 0.45)
	e.set_glow_level(3, 0.0)
	e.set_glow_level(4, 0.0)
	e.set_glow_level(5, 0.0)
	e.set_glow_level(6, 0.0)
	e.glow_intensity = 0.55
	e.glow_strength = 1.0
	e.glow_bloom = 0.0
	e.glow_hdr_threshold = 1.0
	e.glow_hdr_scale = 2.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	e.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	# The numbers above were set on the Mobile renderer (the look the user approved, G5R2-4). Forward+
	# (the renderer since 2026-10-15) thresholds the glow after its first blur pass, where a lamp of a
	# pixel or two is averaged with the dark around it; Mobile thresholds a 4x4 average. With the same
	# numbers the halos come out much weaker on Forward+ (the open gate's 2-20 px rings 12-26 / 255
	# darker). These bring Forward+ back to the Mobile look in steady states (those rings within -5..+2 /
	# 255, 0.03-0.13 / 255 over the frame); the gate's flashes as the lights arrive come out a little
	# brighter (+9 / 255 on average in its 5-10 px ring, +24 at the brightest), as the two glows answer a
	# flash differently (knowledge/14 §7.9). Painted colours (her hat included) still stay under it.
	if RenderingServer.get_current_rendering_method() == "forward_plus":
		e.glow_hdr_threshold = 0.7
		e.glow_hdr_scale = 0.75
		e.glow_intensity = 0.68
	return e


func _fit() -> void:
	var s := Vector2i(size.round())
	if s.x < 16 or s.y < 16:
		s = Vector2i(get_viewport_rect().size.round())
	if s.x < 16 or s.y < 16:
		return
	var fit := {"view": s, "scale": 1.0, "origin": Vector2.ZERO}
	if legacy and is_inside_tree():
		fit = Vista.legacy_fit(Vector2(get_window().size), s)
	if fit["view"] == view and is_equal_approx(float(fit["scale"]), shown_scale) and fit["origin"] == shown_origin:
		return
	view = fit["view"]
	shown_scale = float(fit["scale"])
	shown_origin = fit["origin"]
	vp.size = view + Vector2i(BORDER * 2, BORDER * 2)
	view_rect.size = Vector2(vp.size)
	view_rect.scale = Vector2(shown_scale, shown_scale)
	view_rect.position = shown_origin - Vector2(BORDER, BORDER) * shown_scale
	var mat := view_rect.material as ShaderMaterial
	mat.set_shader_parameter("tex_size", Vector2(vp.size))
	mat.set_shader_parameter("border", Vector2(BORDER, BORDER))
	for n in shots:
		shots[n].layout(view)


## Where the vista goes for a window and the stage's logical canvas: its own canvas is the one of the
## stage rule it was drawn for (PixelStage.legacy_canvas, round(h / 270): 1280x720 -> 426x240 x3,
## 1920x1080 -> 480x270 x4), shown at that rule's integer scale (one vista pixel = scale x scale window
## pixels) and centred on the window on whole window pixels, whatever the stage's own rule is (640x360
## base since 2026-10-15: 1920x1080 is 640x360 x3, so a vista pixel is 4/3 of a logical one). Returns
## {view: its canvas, scale: a vista pixel in logical pixels, origin: its top-left in logical pixels}.
static func legacy_fit(win: Vector2, logical: Vector2i) -> Dictionary:
	var lc: Dictionary = PixelStage.legacy_canvas(win)
	var vs: Vector2i = lc["size"]
	var ls := float(lc["scale"])
	var ss := maxf(1.0, roundf(win.y / maxf(1.0, float(logical.y))))   # the stage's integer scale
	var stage_origin := ((win - Vector2(logical) * ss) * 0.5).round()   # window px of the logical (0, 0)
	var own_origin := ((win - Vector2(vs) * ls) * 0.5).floor()           # window px of the vista's (0, 0)
	return {"view": vs, "scale": ls / ss, "origin": (own_origin - stage_origin) / ss}


## Show a shot (builds it the first time: the data is loaded and kept).
func show_shot(name: String) -> void:
	if name == shot and _current != null:
		return
	if not shots.has(name):
		var node: Node2D = _make(name)
		if node == null:
			return
		shots[name] = node
		root.add_child(node)
		if view.x > 0:
			node.layout(view)
	shot = name
	for n in shots:
		shots[n].visible = n == name
	_current = shots[name]
	_current.update(state, t)


func _make(name: String) -> Node2D:
	var d := VistaData.load_shot(name, data_dir)
	if d == null:
		return null
	var node: Node2D
	match name:
		"south":
			node = VistaSouth.new()
		"tower":
			node = VistaTower.new()
		"title":
			node = VistaTitle.new()
		_:
			push_error("vista: unknown shot " + name)
			return null
	node.exact = exact
	node.quality = _quality()
	if exact:
		node.js_lamps = true
	node.setup(d)
	return node


func _process(dt: float) -> void:
	if _own_director != null:
		_own_director.tick(clampf(dt, 0.0, 0.1))
	if _figure != null and is_instance_valid(_figure):
		_figure.set_pose(String(state.get("pose", "sit")))
	if autoplay:
		advance(dt)


## Advance the vista clock and draw this frame's state.
func advance(dt: float) -> void:
	t += clampf(dt, 0.0, 0.1)
	if _current != null:
		_current.update(state, t)
		_finish()


func _finish() -> void:
	var mat := view_rect.material as ShaderMaterial
	var w := float(view.x)
	var h := float(view.y)
	var night: float = _current.env.night if "env" in _current and _current.env != null else 1.0
	# the vignette of each shot (south.js / tower.js / title.js)
	var vg: Dictionary = _current.vignette() if _current.has_method("vignette") else {"cx": 0.5, "cy": 0.45, "r0": 0.35, "r1": 0.62, "a": lerpf(0.35, 0.6, night)}
	mat.set_shader_parameter("vign_c", Vector2(w * float(vg["cx"]), h * float(vg["cy"])))
	mat.set_shader_parameter("vign_r", Vector2(minf(w, h) * float(vg["r0"]), Vector2(w, h).length() * float(vg["r1"])))
	mat.set_shader_parameter("vign_a", float(vg["a"]))
	var wv := float(state.get("wave", -1.0))
	mat.set_shader_parameter("wash_a", pow(VistaEnv.smoothj(0.88, 1.0, wv), 1.4) * 0.97 if wv > 0.88 else 0.0)
	mat.set_shader_parameter("view", Vector2(view))
	mat.set_shader_parameter("end_k", _current.wave_fx.end_k if "wave_fx" in _current else 0.0)
	if not ("wave_fx" in _current):
		mat.set_shader_parameter("wash_a", 0.0)
	elif _wash_hold >= 0.0:
		mat.set_shader_parameter("wash_a", _wash_hold)


## "high" on desktops, "low" on phones (unless set): companion sparks and the motes' count.
func _quality() -> String:
	if quality == "high" or quality == "low":
		return quality
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--vista-quality="):
			return a.substr(16)
	return "low" if OS.has_feature("mobile") or OS.has_feature("android") else "high"


# ------------------------------------------------------------------ timeline (the prologue's beats)
# The treetop beats in the order of the JS segment 1 (src/story/seg1.js rise()), which the user has
# seen, on the director's clock (await them inside a director scene). The lines are not here: the
# script is still pending (docs/design/script-02-draft.md §6); the host puts its lines between the
# beats, or passes `between` to play_prologue(). Durations default to the JS ones.

## The first state: the plain at dusk from inside the crown (pan 0), nothing has left yet.
func begin() -> void:
	state = {"tod": 19.4, "pan": 0.0, "rise": 0.0, "sky": 0.0, "wave": -1.0, "tower": 1.0, "pose": "sit"}
	show_shot("south")
	beat.emit("begin")


## The camera rises out of the leaves and the plain opens below (pan 0 -> 1); dusk deepens.
func crane_up(d: Director, dur: float = 7.0, tod_to: float = 19.8) -> void:
	beat.emit("crane_up")
	var tod0 := float(state["tod"])
	await d.tween(dur, func(k: float) -> void:
		state["pan"] = k
		state["tod"] = lerpf(tod0, tod_to, k))


## One light leaves the ground alone: the headman's lamp (at rise 0.03). Linear, slow.
func first_light(d: Director, dur: float = 6.0, to: float = 0.06) -> void:
	beat.emit("first_light")
	var r0 := float(state["rise"])
	await d.tween(dur, func(k: float) -> void: state["rise"] = lerpf(r0, to, k), false)


## A light out of a bonfire (0.11), then every place sends its lamps up, each on its own curve,
## all gathering into the gate; night comes on (rise 0.06 -> 0.66).
func lights_leave(d: Director, dur: float = 16.0, to: float = 0.66, tod_to: float = 20.3) -> void:
	beat.emit("lights_leave")
	var r0 := float(state["rise"])
	var tod0 := float(state["tod"])
	await d.tween(dur, func(k: float) -> void:
		state["rise"] = lerpf(r0, to, k)
		state["tod"] = lerpf(tod0, tod_to, k))


## The cloud deck parts over the gate and the other land shows, hanging upside down; the last of the
## lamps leave meanwhile (sky 0 -> 1, rise -> 1).
func sky_opens(d: Director, dur: float = 10.0) -> void:
	beat.emit("sky_opens")
	var r0 := float(state["rise"])
	await d.tween(dur, func(k: float) -> void:
		state["sky"] = k
		state["rise"] = lerpf(r0, 1.0, k))


## The insert: the 「隔」 tower on the summit ridge, its red lamp blinking; it blinks once more and
## goes dark; back to the plain.
func tower_goes_dark(d: Director, before: float = 2.0, after: float = 1.8) -> void:
	show_shot("tower")
	state["tower"] = 1.0
	beat.emit("tower")
	await d.wait(before)
	state["tower"] = 0.0
	beat.emit("tower_dark")
	await d.wait(after)
	show_shot("south")
	beat.emit("back_to_plain")


## The far: a pale ring spreads from under the sky shore over the plain to the mountain's foot
## (wave 0 -> 0.55, linear).
func far_spreads(d: Director, dur: float = 5.5, to: float = 0.55) -> void:
	beat.emit("far_spreads")
	await d.tween(dur, func(k: float) -> void: state["wave"] = to * k, false)


## ... and up the mountain, over the crown, the whole frame washing white (wave -> 1, linear).
func far_arrives(d: Director, dur: float = 2.6) -> void:
	beat.emit("far_arrives")
	var w0 := maxf(0.0, float(state["wave"]))
	await d.tween(dur, func(k: float) -> void: state["wave"] = lerpf(w0, 1.0, k), false)


## Her pose on the limb: "sit", "stand", "shout" (the host's sprite reads state.pose).
func set_pose(p: String) -> void:
	state["pose"] = p
	beat.emit("pose_" + p)


## All the beats with the pauses of the JS segment 1 (65.6 s). At each pause `between` (if given) is
## awaited as between.call(name, seconds) and must take about that long (its lines go there):
##   "plain" 5.7 s (after the crane)  "first_light" 1.5 s  "sky_shore" 4.5 s  "far" 3.0 s (she has
##   stood up; 0.4 s later she shouts: the pose changes are made here, the line is the host's)
func play_prologue(d: Director, between: Callable = Callable()) -> void:
	begin()
	await crane_up(d)
	await _pause(d, between, "plain", 5.7)
	await first_light(d)
	await _pause(d, between, "first_light", 1.5)
	await lights_leave(d)
	await sky_opens(d)
	await _pause(d, between, "sky_shore", 4.5)
	await tower_goes_dark(d)
	await far_spreads(d)
	set_pose("stand")
	await d.wait(0.4)
	set_pose("shout")
	await _pause(d, between, "far", 2.6)
	await far_arrives(d)
	beat.emit("end")


## The prologue's beats on their own, without the story or a host's director (the art sample's
## entry, ShowcaseVista): its own director on the vista's clock, her sprite on the limb following
## state.pose. When the far has washed the frame white the white holds a second, then thins back to
## the sky shore over the dark plain (the frame where 天岸 shows: the lamps gone up into the gate, she
## sitting on the limb) and the vista stays there, still alive. Returns then (beat "hold"); call it
## again to play it from the start. Needs autoplay (the vista advancing itself).
func play_standalone() -> void:
	if _own_director == null:
		_own_director = Director.new()
	_own_director.reset()
	_wash_hold = -1.0
	show_shot("south")
	_place_figure()
	await play_prologue(_own_director)
	await _own_director.wait(1.0)
	_wash_hold = 0.97
	state = {"tod": 20.3, "pan": 1.0, "rise": 1.0, "sky": 1.0, "wave": -1.0, "tower": 1.0, "pose": "sit"}
	show_shot("south")
	await _own_director.tween(2.2, func(k: float) -> void: _wash_hold = 0.97 * (1.0 - k))
	_wash_hold = -1.0
	beat.emit("hold")


func _place_figure() -> void:
	var slot := figure_slot()
	if slot == null:
		return
	if _figure == null or not is_instance_valid(_figure):
		_figure = VistaFigure.new()
		_figure.name = "Her"
		slot.add_child(_figure)
	_figure.set_pose(String(state.get("pose", "sit")))


func _pause(d: Director, between: Callable, name: String, seconds: float) -> void:
	beat.emit("pause_" + name)
	if between.is_valid():
		await between.call(name, seconds)
	else:
		await d.wait(seconds)


func anchors() -> Dictionary:
	return _current.anchors if _current != null else {}


func figure_slot() -> Node2D:
	return _current.figure if _current != null and "figure" in _current else null
