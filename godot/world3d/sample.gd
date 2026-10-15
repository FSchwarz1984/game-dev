extends Node
## The art sample (美术样章): the summit saddle of the pass in the 3D pixel renderer.
## Assembly of the terrain, water, ground cover, trees and props, the characters and the time of
## day. Run: godot --path godot res://world3d/sample.tscn [-- options]
##   --hours=h          time of day (default 9.5)        --rain=0..1
##   --at=x,z           start / camera focus (default: her spawn by the hut door)
##   --shot=path.png    save the low-res frame and the window after --frames frames, then quit
##   --shots=dir:x,z,h;x,z,h;...   several views
##   --route=walk       she walks the sample route (hut -> yard -> round the great camphor -> the
##                      old road) by pressing the same movement keys a player would (Input events),
##                      for recordings; --route=night: the night walk past the lanterns;
##                      --route=lookout: down the spur to the lookout, where she looks out (the view
##                      south, east, then back home), and the top-down view comes back
##   --novista          she does not look out from the lookout (the view from the lookout, W3Vista, is on
##                      by default: standing still on the rock for a moment she looks out)
##   --vshots=dir:yaw,h[,rain];...   views from the lookout (W3Vista), yaw in degrees (N 0, E 90)
##   --pitch=deg        camera pitch (evidence renders)
##   --route_quit, --route_log, --log_pos[=every n frames], --perf, --quit_after=n, and debugging switches
##   (--hide, --hide_props, --nowater, --nohaze, --noshadow, --sbias, --sblur, --pancake,
##   --camrange, --nolamps, --noxray, --noline, --camphor_cut, --timelapse): docs/knowledge/21 §12
## Keys: WASD / arrows walk (she walks with her load; Shift is the 2D core's "give" modifier, so it
## does not run here). On the lookout, looking out, A/D turn her head and W/S come back.

const CHARS_JSON := "res://world3d/sprites/characters.json"
const CATALOG := "res://world3d/assets/catalog.json"

var pv: PixelView3D
var env: W3Env
var terrain: Terrain3D
var args := {}
var frame := 0
var focus := Vector3.ZERO
var her: W3Walker
var saji: W3Walker
var her_shadow: MeshInstance3D
var saji_shadow: MeshInstance3D
var trail: Array[Vector3] = []
var catalog := {}
var props_root: Node3D
var blockers: Array = []
var route: Array[Vector2] = []
var route_i := 0
var _stall_at := Vector2.INF
var _stall_t := 0.0
var keys_down := {}
var _haze_h := 0.0
var atmos: W3Atmosphere
var dressing: W3Dressing
var lamps: W3Lamps
var vista: W3Vista
var _lit_on := -1                 # the lanterns' lit bodies: on (1), off (0), unset (-1)
var _lit_wait: Array = []         # [pair, seconds until it switches] while they light one by one
var _still := 0.0                 # seconds she has stood still on the lookout
var _route_done_t := -1.0         # route recordings: time since she reached the end
var placed_props: Array = []      # [catalog name, position, yaw, scale, height m]: for the vista's impostors


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
		elif a.begins_with("--"):
			args[a.substr(2)] = "1"
	pv = PixelView3D.new()
	if args.has("pitch"):
		pv.pitch_deg = float(args["pitch"])
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	env.rain = float(args.get("rain", "0"))
	env.set_time(float(args.get("hours", "9.5")))
	terrain = Terrain3D.new()
	terrain.name = "Terrain"
	pv.world_root.add_child(terrain)
	var t0 := Time.get_ticks_msec()
	terrain.load_region("res://world3d/terrain/saddle")
	print("TERRAIN_LOADED ms=", Time.get_ticks_msec() - t0)
	props_root = Node3D.new()
	props_root.name = "Props"
	pv.world_root.add_child(props_root)
	_load_catalog()
	_place_props()
	var rocks := W3Rocks.new()
	rocks.name = "Rocks"
	pv.world_root.add_child(rocks)
	rocks.build(terrain, terrain.info["placements"])
	blockers.append_array(rocks.blockers)
	var stones := W3Stonework.new()
	stones.name = "Stonework"
	pv.world_root.add_child(stones)
	stones.build(terrain, rocks)
	var g0 := Time.get_ticks_msec()
	var grass := W3Grass.new()
	grass.name = "Grass"
	pv.world_root.add_child(grass)
	grass.build(terrain)
	print("GRASS tufts=", grass.count, " ms=", Time.get_ticks_msec() - g0)
	lamps = W3Lamps.new()
	lamps.name = "Lamps"
	add_child(lamps)
	dressing = W3Dressing.new()
	dressing.name = "Dressing"
	pv.world_root.add_child(dressing)
	dressing.lamps = lamps
	dressing.lean_k = pv_lean()
	dressing.build(terrain, catalog)
	_place_marker_props()
	_set_hours(env.hours)
	atmos = W3Atmosphere.new()
	atmos.name = "Atmosphere"
	pv.world_root.add_child(atmos)
	atmos.lamps = lamps
	var cm := terrain.marker("camphor")
	atmos.camphor = Vector3(cm.x, terrain.height_at(cm.x, cm.z), cm.z)
	atmos.setup(env, terrain)
	atmos.glints = dressing.glints
	vista = W3Vista.new()
	vista.name = "Vista"
	vista.props = placed_props
	vista.lamp_src = lamps
	add_child(vista)
	vista.setup(pv, env, terrain)
	_spawn_characters()
	focus = her.pos
	if args.has("at"):
		var p := String(args["at"]).split(",")
		her.place(Vector3(float(p[0]), 0.0, float(p[1])))
		saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	pv.follow(_cam_target, {"cut": true})
	if args.has("nowater"):
		for wm in terrain.water_meshes:
			wm.visible = false
	if args.has("noshadow"):
		env.sun.shadow_enabled = false     # debugging: tell shadow-map artefacts from shading ones
	if args.has("sbias"):
		var sb := String(args["sbias"]).split(",")   # debugging: shadow bias, normal bias
		env.sun.shadow_bias = float(sb[0])
		env.sun.shadow_normal_bias = float(sb[1])
	if args.has("pancake"):
		env.sun.directional_shadow_pancake_size = float(args["pancake"])
	if args.has("sblur"):
		env.sun.shadow_blur = float(args["sblur"])
	if args.has("nolamps"):
		lamps.enabled = false                       # debugging: the night without its lanterns
	if args.has("noxray"):
		her.sprite.xray.visible = false             # debugging: no silhouettes through what covers them
		saji.sprite.xray.visible = false
	if args.has("hide_props"):
		# debugging: hide placed props whose node name contains one of these (camphor, hut, sugi, ...)
		var subs := String(args["hide_props"]).split(",")
		for c in props_root.get_children():
			for sub in subs:
				if String(c.name).to_lower().contains(sub):
					(c as Node3D).visible = false
	if args.has("noline"):
		# comparison: the foliage of the props whose names contain these (fern, take, ...) drawn with
		# the outline-less foliage class
		var nl := load("res://render3d/shaders/toon_foliage_noline.gdshader")
		var keys := String(args["noline"]).split(",")
		for c in props_root.get_children():
			for k in keys:
				if String(c.name).to_lower().contains(k):
					_set_foliage_shader(c, nl)
	if args.has("camrange"):
		var cr := String(args["camrange"]).split(",")  # debugging: the camera's near, far (m)
		pv.cam.near = float(cr[0])
		pv.cam.far = float(cr[1])
	if args.has("hide"):
		# debugging: hide parts of the world by node name (Grass, Rocks, Dressing, Atmosphere, ...)
		for n in String(args["hide"]).split(","):
			var node := pv.world_root.get_node_or_null(n)
			if node is Node3D:
				(node as Node3D).visible = false
	if args.get("route", "") == "walk":
		_make_route()
	elif args.get("route", "") == "night":
		_make_route(NIGHT_ROUTE)
	elif args.get("route", "") == "lookout":
		args["vista"] = ""
		_make_route(LOOKOUT_ROUTE)
	if not route.is_empty():
		# (the camera starts on her where the route starts, not swooping in from the spawn)
		pv.follow(_cam_target, {"cut": true})


func _cam_target() -> Vector3:
	if her == null:
		return focus
	return her.pos + Vector3(0.0, 0.9, -0.9 * pv_lean())


func pv_lean() -> float:
	return tan(deg_to_rad(pv.pitch_deg) * 0.5)


# ------------------------------------------------------------------------------------------------
# props

func _load_catalog() -> void:
	var f := FileAccess.open(CATALOG, FileAccess.READ)
	if f:
		catalog = JSON.parse_string(f.get_as_text()).get("assets", {})
	print("CATALOG assets=", catalog.size())


## Placement kinds (terrain generator) -> species / names the asset catalog may use.
const KIND_ALIASES := {
	"camphor": ["camphor"], "cedar": ["sugi", "cedar"], "pine": ["akamatsu", "matsu", "pine"],
	"maple": ["momiji", "kaede", "maple"], "persimmon": ["kaki", "persimmon"], "bamboo": ["take", "madake", "bamboo"],
	"beech": ["buna", "beech"], "broadleaf": ["konara", "kunugi", "keyaki", "nara", "broadleaf"],
	"azalea": ["tsutsuji", "azalea"], "hydrangea": ["ajisai", "hydrangea"], "fern": ["shida", "fern"],
	"shrub": ["tsubaki", "camellia", "shrub"], "choppable": ["kare", "choppable", "dead"], "susuki": ["susuki"],
}


## The asset that stands for a placement kind, if the catalog has one (variant picks among several).
## Assets tagged "accent" (the red maples) are kept for one maple in four, never for the stand-ins.
func _asset_for(kind: String, variant: int) -> String:
	var names := []
	var accents := []
	var keys: Array = KIND_ALIASES.get(kind, [kind])
	for name in catalog:
		var a: Dictionary = catalog[name]
		var sp := String(a.get("species", ""))
		for k in keys:
			if name == k or name.begins_with(k + "_") or sp == k:
				if "accent" in a.get("tags", []):
					accents.append(name)
				else:
					names.append(name)
				break
	if kind == "maple" and not accents.is_empty() and variant % 4 == 3:
		accents.sort()
		return accents[(variant / 4) % accents.size()]
	if names.is_empty():
		return ""
	names.sort()
	return names[variant % names.size()]


func _place_props() -> void:
	var n := 0
	for p in terrain.info["placements"]:
		var kind: String = p["kind"]
		var name := _asset_for(kind, int(p.get("variant", 0)))
		var sc := float(p.get("scale", 1.0))
		if name == "" and kind == "choppable" and catalog.has("sugi_e"):
			# no tree made for felling yet: a young cedar someone planted by the path
			name = "sugi_e"
			sc = 0.62
		if name == "" or not catalog.has(name):
			continue
		var a: Dictionary = catalog[name]
		var ps: PackedScene = load(a["scene"])
		if ps == null:
			continue
		var inst: Node3D = ps.instantiate()
		var pos := Vector3(p["x"], terrain.height_at(p["x"], p["z"]), p["z"])
		inst.position = pos
		if a.get("category", "") != "building":
			inst.rotation.y = float(p.get("rot", 0.0)) if kind != "camphor" else 0.0
		if kind != "camphor":
			inst.scale = Vector3.ONE * sc
		props_root.add_child(inst)
		placed_props.append([name, pos, inst.rotation.y, sc, float(a.get("height", 10.0)) * sc])
		if kind == "bamboo":
			# a grove is dense all the way down: open a wide hole around her, she reads first
			_scale_cutaway(inst, 3.2)
		elif kind != "camphor":
			_scale_cutaway(inst, 1.8)
		if kind == "camphor":
			_scale_cutaway(inst, float(args.get("camphor_cut", "3.8")), true)
			# the trunk and limbs only open where they really cover her (a wide hole would eat the
			# trunk above her head and the front of the shimenawa)
			_solid_cutaway(inst, 1.3)
			_crown_proxy(inst, a)
		for fp in a.get("footprint", []):
			var off := Vector3(fp[0], 0, fp[1]).rotated(Vector3.UP, inst.rotation.y) * sc
			blockers.append([pos + off, float(fp[2]) * sc])
		n += 1
	print("PROPS placed=", n)


## The catalog's buildings, lights and dressing at the layout's markers (and the light slots the
## dressing hands over). Lights with a lit variant swap to it from dusk to dawn.
var _lit_pairs: Array = []        # [unlit node, lit node]


func _place_marker_props() -> void:
	var t := terrain
	var door := t.marker("hut_door")
	var slots := [
		["hut", t.marker("hut"), 0.0, false],
		["shrine", t.marker("shrine"), 0.0, false],
		["offering_box", t.marker("offering_box"), 0.0, false],
		["graves", t.marker("graves"), deg_to_rad(-2.0), false],
		["dosojin", t.marker("dosojin"), 0.0, false],
		["woodpile", t.marker("woodpile"), deg_to_rad(90.0), false],
		["fallen_branch", t.marker("fallen_branch"), 0.6, false],
		["stump_axe", t.marker("choppable_tree") + Vector3(1.4, 0, 0.9), 0.3, false],
		["kakehi", t.marker("spring") + Vector3(1.6, 0, 2.2), 0.0, false],
		["fence_bamboo", Vector3(-23.0, 0, 17.3), 0.0, false],
		["fence_bamboo", Vector3(-21.0, 0, 17.3), 0.0, false],
		["signpost", Vector3(-16.4, 0, 19.0), 0.25, false],
		["waymark", Vector3(8.4, 0, 17.4), -0.1, false],
		["basket_tall", door + Vector3(-1.75, 0, 0.15), 0.4, false],
		["basket_flat", door + Vector3(-3.0, 0, 0.9), 0.0, false],
		["straw_sheaves", Vector3(-22.2, 0, 11.4), 1.4, false],
		["straw_heap", Vector3(-21.6, 0, 17.0), -0.3, false],
	]
	for ds in dressing.asset_slots:
		slots.append([ds[0], ds[1], ds[2], true])
	# the graves' hooks carry the ten paper lanterns of the bon (lit at night)
	if catalog.has("graves") and catalog.has("lantern_paper"):
		var g := t.marker("graves")
		g.y = t.height_at(g.x, g.z)
		var hooks: Array = catalog["graves"].get("anchors", {}).get("hook", [])
		for i in hooks.size():
			var hk: Array = hooks[i]
			slots.append(["lantern_paper", g + Vector3(hk[0], float(hk[1]) - 0.58, hk[2]), 0.0, true])
			# every lantern lights its own small pool (the renderer's lamps have no 8-light limit)
			dressing._light(g + Vector3(hk[0], float(hk[1]) - 0.45, float(hk[2]) + 0.25), Color(1.0, 0.74, 0.46), 1.35, 2.2)
	var lean := pv_lean()
	for sl in slots:
		var nm: String = sl[0]
		if not catalog.has(nm):
			continue
		var a: Dictionary = catalog[nm]
		var p: Vector3 = sl[1]
		var gy := t.height_at(p.x, p.z)
		if not sl[3]:
			p.y = gy
		else:
			# something hanging in the air leans with the thing it hangs from
			p.z -= lean * maxf(p.y - gy, 0.0)
		var base := _instance(String(a["scene"]))
		if base == null:
			continue
		base.position = p
		base.rotation.y = float(sl[2])
		props_root.add_child(base)
		if nm in ["hut", "shrine", "graves"]:
			placed_props.append([nm, p, float(sl[2]), 1.0, float(a.get("height", 3.0))])
		var lit_path := String(a.get("variants", {}).get("lit", ""))
		if lit_path != "":
			var lit := _instance(lit_path)
			if lit:
				lit.position = p
				lit.rotation.y = float(sl[2])
				lit.visible = false
				props_root.add_child(lit)
				_lit_pairs.append([base, lit])
		for fp in a.get("footprint", []):
			var off := Vector3(fp[0], 0, fp[1]).rotated(Vector3.UP, float(sl[2]))
			blockers.append([Vector3(p.x, 0, p.z) + off, float(fp[2])])
		if nm == "offering_box":
			var gl: Array = a.get("anchors", {}).get("glint", [0.0, 0.45, 0.0])
			dressing.glints.append([p + Vector3(gl[0], gl[1], float(gl[2]) - lean * float(gl[1])), 0.0])
	# two red maples by the way down to the lookout and south of the road (v0.1's red maples were
	# the accent the user liked); both stand where nothing she needs to see lies north of them
	# (and both stay out of the look back home from the lookout: W3Vista)
	for mp in [["maple_red_a", Vector2(-38.6, 42.8), 0.7], ["maple_red_b", Vector2(6.0, 28.0), 2.1]]:
		if not catalog.has(mp[0]):
			continue
		var tree := _instance(String(catalog[mp[0]]["scene"]))
		if tree == null:
			continue
		var at: Vector2 = mp[1]
		tree.position = Vector3(at.x, t.height_at(at.x, at.y), at.y)
		tree.rotation.y = float(mp[2])
		props_root.add_child(tree)
		placed_props.append([mp[0], tree.position, float(mp[2]), 1.0, float(catalog[mp[0]].get("height", 6.0))])
		_scale_cutaway(tree, 1.8)
		for fp in catalog[mp[0]].get("footprint", []):
			var off := Vector3(fp[0], 0, fp[1]).rotated(Vector3.UP, float(mp[2]))
			blockers.append([tree.position + off, float(fp[2])])


func _instance(path: String) -> Node3D:
	var ps: PackedScene = load(path)
	if ps == null:
		return null
	return ps.instantiate() as Node3D


## The time of day for the world, the dressing's lights and the lit variants of the lanterns.
## instant: a still or a jump in time; otherwise (time passing in play) the lanterns are lit one
## after another as their light fades in (render3d/lamps.gd).
func _set_hours(h: float, instant := true) -> void:
	env.set_time(h)
	if dressing:
		dressing.set_time(h, instant)
	var on := 1 if (h >= 18.4 or h <= 5.4) else 0
	if on == _lit_on:
		return
	_lit_wait.clear()
	for i in _lit_pairs.size():
		if instant or _lit_on < 0:
			_switch_lit(_lit_pairs[i], on == 1)
		else:
			_lit_wait.append([_lit_pairs[i], 0.18 * i, on == 1])
	_lit_on = on


func _switch_lit(lp: Array, on: bool) -> void:
	(lp[0] as Node3D).visible = not on
	(lp[1] as Node3D).visible = on


## A dense evergreen crown casts one deep shade: a shadow-only body inside the camphor's crown fills
## the gaps between its leaf masses in the shadow map. The leaf cards still cast the ragged rim, and
## the ground draws the small sun flecks inside the shade (toon_terrain).
func _crown_proxy(parent: Node3D, a: Dictionary) -> void:
	var cr: Dictionary = a.get("crown", {})
	if cr.is_empty():
		return
	var c: Array = cr["centre"]
	var r := float(cr["radius"]) * 0.55
	var base := float(cr["base"])
	var top := float(a.get("height", base + r))
	var cy := (base + top) * 0.5 + 0.5
	var ry := (top - base) * 0.42
	var sph := SphereMesh.new()
	sph.radial_segments = 32
	sph.rings = 12
	var arr := sph.get_mesh_arrays()
	var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var rng := RandomNumberGenerator.new()
	rng.seed = 4242
	var ph := [rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU]
	for i in verts.size():
		var v: Vector3 = verts[i] * 2.0
		var ang := atan2(v.z, v.x)
		var lob: float = 1.0 + 0.12 * sin(3.0 * ang + ph[0]) + 0.08 * sin(5.0 * ang + ph[1]) + 0.05 * sin(7.0 * ang + ph[2])
		verts[i] = Vector3(v.x * r * lob + float(c[0]), v.y * ry + cy, v.z * r * lob + float(c[2]))
	arr[Mesh.ARRAY_VERTEX] = verts
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance3D.new()
	mi.name = "CrownShadow"
	mi.mesh = mesh
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	parent.add_child(mi)


## Big canopies fade over a wide disc while she is under them (foreground that thins out).
func _scale_cutaway(n: Node, k: float, dense := false) -> void:
	if n is GeometryInstance3D:
		var gi := n as GeometryInstance3D
		var mats: Array = []
		if gi.material_override:
			mats.append(gi.material_override)
		if gi is MeshInstance3D and (gi as MeshInstance3D).mesh:
			var mesh := (gi as MeshInstance3D).mesh
			for si in mesh.get_surface_count():
				var sm := (gi as MeshInstance3D).get_active_material(si)
				if sm:
					mats.append(sm)
		for m in mats:
			if m is ShaderMaterial and String((m as ShaderMaterial).shader.resource_path).contains("foliage"):
				(m as ShaderMaterial).set_shader_parameter("cutaway_scale", k)
				if dense:
					# under the great crown the view keeps its lowest boughs along the top edge (she
					# stands under a roof of leaves; everything nearer to her than that opens)
					(m as ShaderMaterial).set_shader_parameter("cutaway_keep_px", 96.0)
					# the great evergreen crown: a deep shade in its heart (the crown proxy), dappled
					# toward its rim where the leaf masses part (the cards cast a little larger than
					# drawn, and let a few texels through); other trees keep their own lacy shade
					(m as ShaderMaterial).set_shader_parameter("shadow_shrink", 1.0)
					(m as ShaderMaterial).set_shader_parameter("shadow_sieve", 0.08)
					# seen from its shaded side at midday: keep the masses, not a black lid
					(m as ShaderMaterial).set_shader_parameter("shade_fill", 0.42)
	for c in n.get_children():
		_scale_cutaway(c, k, dense)


func _set_foliage_shader(n: Node, sh: Shader) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mi := n as MeshInstance3D
		for si in mi.mesh.get_surface_count():
			var m := mi.get_active_material(si)
			if m is ShaderMaterial and String((m as ShaderMaterial).shader.resource_path).ends_with("toon_foliage.gdshader"):
				(m as ShaderMaterial).shader = sh
	for c in n.get_children():
		_set_foliage_shader(c, sh)


## The great tree's limbs and trunk also thin out around her when they stand between her and us.
func _solid_cutaway(n: Node, k: float) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mi := n as MeshInstance3D
		for si in mi.mesh.get_surface_count():
			var m := mi.get_active_material(si)
			if m is ShaderMaterial and String((m as ShaderMaterial).shader.resource_path).contains("toon_solid"):
				(m as ShaderMaterial).set_shader_parameter("cutaway", true)
				(m as ShaderMaterial).set_shader_parameter("cutaway_scale", k)
				(m as ShaderMaterial).set_shader_parameter("shade_fill", 0.3)
	for c in n.get_children():
		_solid_cutaway(c, k)


# ------------------------------------------------------------------------------------------------
# characters

func _spawn_characters() -> void:
	var f := FileAccess.open(CHARS_JSON, FileAccess.READ)
	var chars: Dictionary = JSON.parse_string(f.get_as_text())
	her = W3Walker.new()
	her.name = "Tsuzumi"
	pv.world_root.add_child(her)
	her.setup(terrain, "tsuzumi", "load", chars)
	her.blockers = blockers
	her.place(terrain.marker("spawn"))
	saji = W3Walker.new()
	saji.name = "Saji"
	pv.world_root.add_child(saji)
	saji.setup(terrain, "saji", "main", chars)
	saji.blockers = blockers
	saji.radius = 0.25
	saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	# their outlines when something covers them: her warm (the lamp of her hat), さぢ a pale sky blue
	her.sprite.set_xray_colour(Color(1.0, 0.84, 0.52))
	saji.sprite.set_xray_colour(Color(0.62, 0.86, 1.0))
	her_shadow = _contact_shadow(Vector2(9.0, 3.5))
	saji_shadow = _contact_shadow(Vector2(7.0, 3.0))


func _contact_shadow(r: Vector2) -> MeshInstance3D:
	var q := MeshInstance3D.new()
	var m := PlaneMesh.new()
	m.size = Vector2(1.4, 1.0)
	q.mesh = m
	var sm := ShaderMaterial.new()
	sm.shader = load("res://render3d/shaders/contact_shadow.gdshader")
	sm.set_shader_parameter("radius_px", r)
	sm.render_priority = 1
	q.material_override = sm
	q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pv.world_root.add_child(q)
	return q


func _lay(shadow: MeshInstance3D, p: Vector3) -> void:
	var n := terrain.normal_at(p.x, p.z)
	var b := Basis.looking_at(n.cross(Vector3.RIGHT).normalized() if absf(n.x) < 0.9 else Vector3.FORWARD, n)
	shadow.global_transform = Transform3D(Basis(b.x, n, b.z).orthonormalized(), p + n * 0.04)


func _input_dir() -> Vector2:
	var d := Vector2.ZERO
	if _key(KEY_A) or _key(KEY_LEFT):
		d.x -= 1.0
	if _key(KEY_D) or _key(KEY_RIGHT):
		d.x += 1.0
	if _key(KEY_W) or _key(KEY_UP):
		d.y -= 1.0
	if _key(KEY_S) or _key(KEY_DOWN):
		d.y += 1.0
	return d.normalized() if d.length() > 0.0 else d


func _key(k: Key) -> bool:
	return Input.is_physical_key_pressed(k) or keys_down.get(k, false)


func _follow_saji(dt: float) -> void:
	# breadcrumbs of her path; she leads, さぢ keeps a step behind and to the north side of her
	if trail.is_empty() or trail[-1].distance_to(her.pos) > 0.25:
		trail.append(her.pos)
		if trail.size() > 64:
			trail.remove_at(0)
	var behind := her.pos
	var acc := 0.0
	for i in range(trail.size() - 1, 0, -1):
		acc += trail[i].distance_to(trail[i - 1])
		behind = trail[i - 1]
		if acc >= 1.5:
			break
	var side := Vector3(-0.55, 0, -0.35) if her.facing in [0, 1, 2, 3] else Vector3(0.55, 0, -0.35)
	var want := behind + side
	if her.speed < 0.3:
		want = her.pos + side * 1.6 + Vector3(0, 0, -0.2)
	var d := Vector2(want.x - saji.pos.x, want.z - saji.pos.z)
	var dist := d.length()
	var dir := Vector2.ZERO
	if dist > 0.3:
		dir = d / dist * clampf(dist * 0.9, 0.0, 1.15)
	saji.step(dt, dir)


# ------------------------------------------------------------------------------------------------
# route driver for recordings: presses the movement keys toward the next waypoint

## The night walk: out of the yard by the lanterns at the hut, along the front path past the bon
## lanterns over the graves (about 24 m, near 12 s)
const NIGHT_ROUTE := [Vector2(-16.6, 15.5), Vector2(-14.2, 15.2), Vector2(-13.1, 13.6), Vector2(-12.9, 10.8),
	Vector2(-11.0, 10.0), Vector2(-6.5, 10.0), Vector2(-2.0, 10.3), Vector2(2.5, 10.4), Vector2(5.5, 10.3)]
## Down the spur to the lookout's rock (about 12 m), where she stands still and looks out (W3Vista)
const LOOKOUT_ROUTE := [Vector2(-19.4, 30.6), Vector2(-20.8, 34.0), Vector2(-22.4, 38.2), Vector2(-23.5, 41.9)]


func _make_route(night: Array = []) -> void:
	# Round the great camphor: out of the hut's door and across the yard, up the west side of the tree
	# between its trunk and the shrine's terrace; round the north side under the limbs and the crown
	# (she walks in a clearing in the leaves, the limbs reaching out over her); onto the old road and
	# south under the east limb that arches over it, to stop where the trunk and its rope are in view
	# (about 52 m, near 24 s)
	var pts := [Vector2(-17.6, 15.3), Vector2(-14.2, 15.2), Vector2(-13.1, 13.6), Vector2(-13.0, 10.8),
		Vector2(-11.2, 10.0), Vector2(-8.0, 9.9), Vector2(-6.4, 8.6), Vector2(-5.6, 5.0), Vector2(-6.0, 2.5),
		Vector2(-6.2, -1.0), Vector2(-5.5, -4.5), Vector2(-2.0, -7.0), Vector2(2.0, -6.9), Vector2(5.0, -5.4),
		Vector2(5.7, -3.0), Vector2(7.0, -0.5), Vector2(9.4, 1.0), Vector2(9.3, 4.0)]
	if not night.is_empty():
		pts = night
	for p in pts:
		route.append(p)
	her.place(Vector3(pts[0].x, 0, pts[0].y))
	saji.place(her.pos + Vector3(-0.9, 0, -0.6))
	route_i = 1


func _drive_route() -> void:
	if args.has("route_log") and frame % 30 == 0:
		print("ROUTE f=%d i=%d her=(%.2f, %.2f) saji=(%.2f, %.2f)" % [frame, route_i, her.pos.x, her.pos.z, saji.pos.x, saji.pos.z])
	for k in [KEY_W, KEY_A, KEY_S, KEY_D]:
		keys_down[k] = false
	if route_i >= route.size():
		# she has arrived: hold a moment on the last view (or, with the vista, until she has looked
		# out and the top-down view is back), then end the recording
		_route_done_t = maxf(_route_done_t, 0.0) + get_process_delta_time()
		var vista_busy := args.has("vista") and (vista.active or vista.shown or vista.veil > 0.0 or _pan_done_t < 0.0)
		if vista_busy:
			_route_done_t = 0.0
		if args.has("route_quit") and _route_done_t > (0.9 if args.has("vista") else 1.6):
			get_tree().quit()
		return
	var t := route[route_i]
	var d := t - Vector2(her.pos.x, her.pos.z)
	if d.length() < 0.6:
		route_i += 1
		return
	d = d.normalized()
	# the keys a player would hold (8 directions)
	if d.x < -0.38:
		keys_down[KEY_A] = true
	if d.x > 0.38:
		keys_down[KEY_D] = true
	if d.y < -0.38:
		keys_down[KEY_W] = true
	if d.y > 0.38:
		keys_down[KEY_S] = true
	# a player who walks into a corner adds the sideways key: so does the driver when she stalls
	var p2 := Vector2(her.pos.x, her.pos.z)
	if p2.distance_to(_stall_at) > 0.12:
		_stall_at = p2
		_stall_t = 0.0
	else:
		_stall_t += get_process_delta_time()
	if _stall_t > 0.3:
		if absf(d.x) < 0.38:
			keys_down[KEY_D if d.x >= 0.0 else KEY_A] = true
		if absf(d.y) < 0.38:
			keys_down[KEY_S if d.y >= 0.0 else KEY_W] = true


# ------------------------------------------------------------------------------------------------

var _shot_list: Array = []
var _shot_i := 0


func _set_view(i: int) -> void:
	var v: Array = _shot_list[i]
	her.place(Vector3(v[0], 0.0, v[1]))
	saji.place(her.pos + Vector3(-0.9, 0, -0.5))
	trail.clear()
	env.rain = float(args.get("rain", "0"))
	if v.size() > 3:
		env.rain = v[3]
	_set_hours(v[2])
	# stills of the top-down view: she does not look out from the lookout here
	vista.hide_now()
	_still = -1.0
	pv.follow(_cam_target, {"cut": true})


## The lookout: standing still on it for a moment she looks out (W3Vista). A/D turn her head (held
## at the end of the range, she turns round: out over the land / back home); W/S (or walking keys)
## bring the top-down view back.
func _update_vista(dt: float, dir: Vector2) -> void:
	if args.has("novista") and not args.has("vshots"):
		return
	var lk := terrain.marker("lookout")
	var near := Vector2(her.pos.x - lk.x, her.pos.z - lk.z).length() < 1.9
	if not vista.active:
		# (standing still: no movement key held and no real walking; the rocks round the lookout can
		# nudge her by a hair every frame, which kept a finer test from ever passing)
		if near and dir == Vector2.ZERO and her.speed < 0.3 and _still >= 0.0 and not vista.shown:
			_still += dt
			if _still > 0.8:
				vista.sector = 0
				vista.yaw = 180.0
				vista.yaw_target = 180.0
				vista.active = true
				_pan_t = 0.0
				print("VISTA on f=%d" % frame)
		elif not near:
			_still = 0.0
	else:
		if not route.is_empty():
			_autopan(dt)
		elif vista.shown:
			if _key(KEY_A) or _key(KEY_LEFT):
				vista.turn(-1.0, dt)
			if _key(KEY_D) or _key(KEY_RIGHT):
				vista.turn(1.0, dt)
			if _key(KEY_W) or _key(KEY_S) or _key(KEY_UP) or _key(KEY_DOWN):
				vista.active = false
				_still = -1.0         # she has to step off before she looks out again
				print("VISTA off f=%d yaw=%.1f" % [frame, vista.yaw_target])
	if _still < 0.0 and not near:
		_still = 0.0
	vista.update(dt)


## Recordings: she looks out over the plain, turns her head east to the kiln's smoke, then turns
## round and looks back home at the great camphor; then the top-down view comes back.
## [seconds, place (0 out, 1 home), bearing]
const AUTOPAN := [[0.0, 0, 180.0], [2.2, 0, 180.0], [4.9, 0, 100.0], [5.8, 0, 100.0], [5.8, 1, 50.0], [6.9, 1, 50.0],
	[9.1, 1, 17.0], [11.6, 1, 17.0]]
var _pan_t := 0.0
var _pan_done_t := -1.0


func _autopan(dt: float) -> void:
	if not vista.shown and vista._trans == "":
		return
	_pan_t += dt
	var last: Array = AUTOPAN[-1]
	if _pan_t >= float(last[0]):
		vista.active = false
		_still = -1.0               # (she does not look out again until she steps off)
		_pan_done_t = 0.0
		return
	for i in AUTOPAN.size() - 1:
		var a: Array = AUTOPAN[i]
		var b: Array = AUTOPAN[i + 1]
		if _pan_t >= float(a[0]) and _pan_t < float(b[0]):
			if int(b[1]) != vista.sector:
				vista.flip_to(int(b[1]), float(b[2]))
			elif int(a[1]) == vista.sector:
				var t := smoothstep(float(a[0]), float(b[0]), _pan_t)
				vista.yaw_target = lerpf(float(a[2]), float(b[2]), t)
				vista.yaw = vista.yaw_target
			return


func _set_vview(i: int) -> void:
	var v: Array = _shot_list[i]
	env.rain = float(v[2])
	_set_hours(float(v[1]))
	var b := float(v[0])
	# bearings round the north are the look back home
	var sec := 1 if (b < 80.0 or b > 330.0) else 0
	vista.show_now(sec, wrapf(b, -180.0, 180.0) if sec == 1 else b)


## A still: the window as shown (graded, at the window's size) and the native frame taken from it
## (one pixel per native pixel, the grading included).
func _save_shot(base: String) -> void:
	var win := get_viewport().get_texture().get_image()
	win.save_png(base + "_win.png")
	var s := pv.scale_factor
	var lg := Vector2i(pv.logical)
	var nat := Image.create(lg.x, lg.y, false, Image.FORMAT_RGB8)
	var off := Vector2i(pv.margin) + Vector2i(s / 2, s / 2)
	for y in lg.y:
		for x in lg.x:
			nat.set_pixel(x, y, win.get_pixel(mini(off.x + x * s, win.get_width() - 1), mini(off.y + y * s, win.get_height() - 1)))
	nat.save_png(base + ".png")
	print("SHOT ", base, " ", lg, " x", s)


func _process(dt: float) -> void:
	frame += 1
	env.tick(dt)
	# time passing (verification of the evening): hours per second
	if args.has("timelapse"):
		_set_hours(fposmod(env.hours + float(args["timelapse"]) * dt, 24.0), false)
	for i in range(_lit_wait.size() - 1, -1, -1):
		var w: Array = _lit_wait[i]
		w[1] = float(w[1]) - dt
		if float(w[1]) <= 0.0:
			_switch_lit(w[0], w[2])
			_lit_wait.remove_at(i)
	if lamps:
		lamps.update(dt)
	if not route.is_empty():
		_drive_route()
	var dir := _input_dir()
	if args.has("perf") and frame % 60 == 0 and frame > 0:
		print("PERF f=%d fps=%.1f draws=%d prims=%d objects=%d vram_mb=%.0f" % [frame, Performance.get_monitor(Performance.TIME_FPS),
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME), Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0])
	if args.has("log_pos") and frame % maxi(int(args["log_pos"]), 1) == 0:
		print("POS f=%d her=(%.2f, %.2f) saji=(%.2f, %.2f) facing=%d vista=%s yaw=%.1f" % [frame, her.pos.x, her.pos.z, saji.pos.x, saji.pos.z, her.facing, str(vista.active), vista.yaw_target])
	_update_vista(dt, dir)
	if vista.active or vista.amount > 0.0:
		dir = Vector2.ZERO
	her.step(dt, dir)
	_follow_saji(dt)
	_lay(her_shadow, her.pos)
	_lay(saji_shadow, saji.pos)
	# aerial perspective measured from her: the land that falls away below her hazes over
	_haze_h = lerpf(_haze_h, her.pos.y, clampf(dt * 1.5, 0.0, 1.0)) if frame > 1 else her.pos.y
	# (it starts well below her, so the cuts and dips near her keep their colour; the plain below
	# the lookout, 40 m down, is in full haze)
	var haze_max := 0.0 if args.has("nohaze") else 0.78
	RenderingServer.global_shader_parameter_set("w3_haze", Vector4(_haze_h, 5.0, 40.0, haze_max))
	var chest := her.chest()
	RenderingServer.global_shader_parameter_set("w3_player", Vector4(chest.x, chest.y, chest.z, 26.0))
	pv.update_camera(dt)
	if atmos:
		atmos.update(dt, her.pos)
	if args.has("shots"):
		if _shot_list.is_empty():
			var spec := String(args["shots"]).split(":", true, 1)
			for v in spec[1].split(";"):
				var p := v.split(",")
				var e := [float(p[0]), float(p[1]), float(p[2]) if p.size() > 2 else 10.0]
				if p.size() > 3:
					e.append(float(p[3]))
				_shot_list.append(e)
			_set_view(0)
		if frame % int(args.get("settle", "40")) == 0:
			var outdir := String(args["shots"]).split(":", true, 1)[0]
			var v: Array = _shot_list[_shot_i]
			var base := "%s/v%02d_%d_%d_%sh" % [outdir, _shot_i, int(v[0]), int(v[1]), String.num(v[2], 1)]
			_save_shot(base)
			_shot_i += 1
			if _shot_i >= _shot_list.size():
				get_tree().quit()
				return
			_set_view(_shot_i)
		return
	if args.has("vshots"):
		# stills of the view from the lookout: --vshots=dir:bearing,hour[,rain];...
		if _shot_list.is_empty():
			var vspec := String(args["vshots"]).split(":", true, 1)
			for v in vspec[1].split(";"):
				var p := v.split(",")
				var e := [float(p[0]), float(p[1]) if p.size() > 1 else 10.0]
				e.append(float(p[2]) if p.size() > 2 else 0.0)
				_shot_list.append(e)
			var lk := terrain.marker("lookout")
			her.place(lk)
			saji.place(lk + Vector3(-0.9, 0, -0.5))
			_set_vview(0)
		if frame % int(args.get("settle", "40")) == 0:
			var vdir := String(args["vshots"]).split(":", true, 1)[0]
			var vv: Array = _shot_list[_shot_i]
			_save_shot("%s/vista%02d_%d_%sh" % [vdir, _shot_i, int(vv[0]), String.num(vv[1], 1)])
			_shot_i += 1
			if _shot_i >= _shot_list.size():
				get_tree().quit()
				return
			_set_vview(_shot_i)
		return
	if args.has("shot") and frame == int(args.get("frames", "30")):
		var path: String = args["shot"]
		var img := pv.vp.get_texture().get_image()
		img.save_png(path)
		get_viewport().get_texture().get_image().save_png(path.replace(".png", "_win.png"))
		print("SHOT ", path, " ", img.get_size())
		get_tree().quit()
	if args.has("quit_after") and frame >= int(args["quit_after"]):
		get_tree().quit()
