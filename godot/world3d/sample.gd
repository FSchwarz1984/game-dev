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
##   --route_quit, --route_log, --log_pos[=every n frames], --perf, --quit_after=n, --ambience=wind,night
##   (recordings: the ambience loops), and debugging switches
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
var realm_mask: W3RealmMask       # the barrier: where she stands sets the frame's look (W3Env.set_realm)
var hut_smoke := Vector3.INF      # the home's smoke hole (catalog anchors.smoke)
var _realm_k := -1.0
var _swell_k := 0.0


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
	if args.has("scale"):
		pv.force_scale = int(args["scale"])     # comparisons: e.g. --scale=4 at 1920x1080 = 480x270 x4
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	if args.has("amb"):
		env.ambient_day_gain = float(args["amb"])     # tuning: the day sky light next to the sun
	if args.get("ssao", "1") == "0":
		env.environment.ssao_enabled = false          # comparisons
	if args.has("noglow"):
		env.environment.glow_enabled = false
	cut_mode = String(args.get("cutmode", "cut"))
	env.rain = float(args.get("rain", "0"))
	env.set_time(float(args.get("hours", "9.5")))
	terrain = Terrain3D.new()
	terrain.name = "Terrain"
	pv.world_root.add_child(terrain)
	var t0 := Time.get_ticks_msec()
	terrain.load_region("res://world3d/terrain/saddle")
	print("TERRAIN_LOADED ms=", Time.get_ticks_msec() - t0)
	var r0 := Time.get_ticks_msec()
	realm_mask = W3RealmMask.new()
	realm_mask.build(terrain)
	env.realm_mask = realm_mask
	print("REALM_MASK ms=", Time.get_ticks_msec() - r0)
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
	lamps.world = pv.world_root
	add_child(lamps)
	dressing = W3Dressing.new()
	dressing.name = "Dressing"
	pv.world_root.add_child(dressing)
	dressing.lamps = lamps
	dressing.lean_k = pv_lean()
	dressing.build(terrain, catalog)
	_place_marker_props()
	_round3_leaf_palette(pv.world_root)
	_set_hours(env.hours)
	atmos = W3Atmosphere.new()
	atmos.name = "Atmosphere"
	pv.world_root.add_child(atmos)
	atmos.lamps = lamps
	var cm := terrain.marker("camphor")
	atmos.camphor = Vector3(cm.x, terrain.height_at(cm.x, cm.z), cm.z)
	atmos.setup(env, terrain)
	atmos.glints = dressing.glints
	atmos.realm_mask = realm_mask
	atmos.chimney = hut_smoke
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
	_setup_gi()
	if args.has("camdist"):
		pv.set_camera_distance(float(args["camdist"]))
	# the air near the ground (volumetric fog: shafts, halos, the morning mist, the gates' curtains);
	# --vfog=0 turns it off (comparisons, quick input checks)
	if float(args.get("vfog", "1")) > 0.0:
		env.use_volumetric_fog(float(args.get("vfog", "1")), terrain)
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
	if args.has("ambience"):
		# recordings: the ambience loops (audio/ambience), as a shell would start them (godot/showcase)
		var amb := get_node_or_null("/root/Audio")
		if amb:
			amb.call("ambience", Array(String(args["ambience"]).split(",")))
	if args.has("nolamps"):
		lamps.enabled = false                       # debugging: the night without its lanterns
	if args.has("noxray"):
		her.sprite.xray.visible = false             # debugging: no silhouettes through what covers them (sprites only)
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
	# the routes of the layout (terrain.json "routes", written by the scene generator for its own
	# layout) come first; the constants below are the round-3 layout's
	var lay_routes: Dictionary = terrain.info.get("routes", {})
	var rname: String = args.get("route", "")
	if rname == "lookout":
		args["vista"] = ""
	if rname != "" and lay_routes.has(rname):
		var pts: Array = []
		for p in lay_routes[rname]:
			pts.append(Vector2(float(p[0]), float(p[1])))
		# (--route_from=k: start at the k-th point; a short recording)
		_make_route(pts.slice(int(args.get("route_from", "0"))))
	elif rname == "walk":
		_make_route()
	elif rname == "night":
		_make_route(NIGHT_ROUTE)
	elif rname == "lookout":
		_make_route(LOOKOUT_ROUTE.slice(int(args.get("route_from", "0"))))
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


# Round 5 (decision-log G5R3-1, renderer): the leaves take round 3's deeper palette (pixel_toon
# w3_ukiyo_tex, the foliage material's `ukiyo` 1 by default). It reproduces how round 3 drew the
# textures it had (measured: the cedar within dE 1.7 of round 3, render3d/dev/asset_preview through
# both renderers). Textures painted since round 4's sRGB fix were painted for one conversion: the
# deeper palette in full would turn their darks black, so they take less of it (their `ukiyo`): the
# great camphor's new leaves 0.4 (measured: its crown then as light as round 3's, L* 58 lit, where
# 0 gave 75 and 1 gave 33), the rest 0 (their painted colour). Their owners can set the value in the
# material instead; this table then shrinks.
const ONE_CONVERSION_LEAVES := {
	"res://world3d/assets/trees/camphor_great/camphor_great_leaves.png": 0.4,
	"res://world3d/assets/trees/furusugi/furusugi_leaves.png": 0.0,
	"res://world3d/assets/buildings/hut/hut_cards.png": 0.0,
	"res://world3d/assets/props/fence_yotsume_a/fence_yotsume_a_vines.png": 0.0,
	"res://world3d/assets/props/fence_yotsume_b/fence_yotsume_b_vines.png": 0.0,
	"res://world3d/assets/props/fence_yotsume_c/fence_yotsume_c_vines.png": 0.0,
	"res://world3d/assets/props/hatake/hatake_plants.png": 0.0,
}


func _round3_leaf_palette(n: Node) -> void:
	var seen := {}
	var stack: Array[Node] = [n]
	while not stack.is_empty():
		var c: Node = stack.pop_back()
		for ch in c.get_children():
			stack.append(ch)
		if not (c is MeshInstance3D):
			continue
		var mi := c as MeshInstance3D
		var mats: Array[Material] = []
		if mi.material_override:
			mats.append(mi.material_override)
		for i in mi.get_surface_override_material_count():
			if mi.get_surface_override_material(i):
				mats.append(mi.get_surface_override_material(i))
		if mi.mesh:
			for i in mi.mesh.get_surface_count():
				if mi.mesh.surface_get_material(i):
					mats.append(mi.mesh.surface_get_material(i))
		for m in mats:
			if not (m is ShaderMaterial) or seen.has(m):
				continue
			seen[m] = true
			var sm := m as ShaderMaterial
			var tex = sm.get_shader_parameter("leaf_tex")
			if tex is Texture2D and ONE_CONVERSION_LEAVES.has(String((tex as Texture2D).resource_path)):
				sm.set_shader_parameter("ukiyo", float(ONE_CONVERSION_LEAVES[String((tex as Texture2D).resource_path)]))


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
			_tree_cutaway(inst, 3.2, float(a.get("height", 10.0)) * sc)
		elif kind != "camphor":
			_tree_cutaway(inst, 1.8, float(a.get("height", 10.0)) * sc)
		if kind == "camphor":
			# the great tree is always cut (she walks under it); trunk, limbs, rope and leaves alike
			_tree_cutaway(inst, float(args.get("camphor_cut", "3.8")), 0.0, true)
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
	var slots := [
		["hut", t.marker("hut"), 0.0, false],
		["shrine", t.marker("shrine"), 0.0, false],
		["offering_box", t.marker("offering_box"), 0.0, false],
		["graves", t.marker("graves"), deg_to_rad(-2.0), false],
		["dosojin", t.marker("dosojin"), 0.0, false],
	]
	# (the yard's and the paths' small things are the layout's own since round 4: dressing.asset_slots)
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
		if nm == "hut":
			# the home's hearth (its embers light the room through the open door and the shoji at
			# night) and the kitchen's smoke hole (the morning's and the evening's cooking smoke)
			var anc: Dictionary = a.get("anchors", {})
			var yaw := float(sl[2])
			if anc.has("light"):
				var la: Array = anc["light"]
				var lp := p + Vector3(la[0], la[1], la[2]).rotated(Vector3.UP, yaw)
				lamps.add(lp, 3.2, Color(1.0, 0.58, 0.3), 0.9, 0.3)
			if anc.has("smoke"):
				var sa: Array = anc["smoke"]
				hut_smoke = p + Vector3(sa[0], sa[1], sa[2]).rotated(Vector3.UP, yaw)
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
	# (round 5: the two red maples that stood here by the way down to the lookout and south of the road
	# are gone: the approved composition has one nomura maple on the east edge of the grounds, placed
	# by the layout; the view from the lookout keeps round 3's own, round3_props.json)


## Global illumination (round 4, Forward+): a VoxelGI over the sample region, baked once when the
## world is built (SDFGI does not work with the orthogonal camera: its cascades follow the camera,
## 120 m away, and band across the ground). The sun, the moon and the lanterns light it every frame,
## so the bounce follows the time of day. --gi=none turns it off (comparisons).
var gi: VoxelGI
var _gi_bake_at := -1


func _setup_gi() -> void:
	if args.get("gi", "voxel") == "none":
		return
	gi = VoxelGI.new()
	gi.name = "GI"
	# the terrain's frame: 160 x 208 m, heights -44 .. 84 m (the voxels: about 0.8 m)
	var o: Vector2 = terrain.origin
	var size := Vector2(float(terrain.nx - 1), float(terrain.nz - 1)) * terrain.cell
	gi.size = Vector3(size.x, 96.0, size.y)
	gi.position = Vector3(o.x + size.x * 0.5, 10.0, o.y + size.y * 0.5)
	gi.subdiv = VoxelGI.SUBDIV_256 if args.get("gi_subdiv", "256") == "256" else VoxelGI.SUBDIV_512
	pv.world_root.add_child(gi)
	_gi_bake_at = 2          # once the world is in the tree and has drawn (the shaders compiled)


func _bake_gi() -> void:
	var t0 := Time.get_ticks_msec()
	gi.bake()
	if gi.data:
		gi.data.energy = float(args.get("gi_energy", "1.0"))
		gi.data.propagation = 0.7
		gi.data.use_two_bounces = true
		gi.data.interior = false
	print("GI baked ms=", Time.get_ticks_msec() - t0)


func _instance(path: String) -> Node3D:
	var ps: PackedScene = load(path)
	if ps == null:
		return null
	return ps.instantiate() as Node3D


## For a shell around the sample (godot/showcase): the time of day, 0..24 (wraps). instant: a jump
## (everything at once); false: time passing in play (the lanterns are lit one after another).
## Names and meaning stay; the internals below may change.
func set_hours(h: float, instant := true) -> void:
	_set_hours(fposmod(h, 24.0), instant)


## For a shell: the rain, 0 (dry) .. 1 (a steady rain); the sky, the light, the wet ground and the
## puddles follow at once, at the present time of day.
func set_rain(r: float) -> void:
	env.rain = clampf(r, 0.0, 1.0)
	_set_hours(env.hours, true)


## For a shell: the picture's cost. 1 (the default) is the full picture; 0 is for a weak graphics card:
## the air's fog volume an eighth of the cells (64^3), the sun's shadow map half as fine (2048: a
## shadow texel about 1.4 screen pixels, so the shadows' edges can step), no SSAO. The colours, the
## GI and everything in the picture stay; the world is drawn at 640x360 whatever the window, so the
## window's size costs next to nothing.
func set_quality(level: int) -> void:
	var full := level >= 1
	RenderingServer.environment_set_volumetric_fog_volume_size(128 if full else 64, 128 if full else 64)
	RenderingServer.directional_shadow_atlas_set_size(4096 if full else 2048, false)
	env.environment.ssao_enabled = full


## The time of day for the world, the dressing's lights and the lit variants of the lanterns.
## instant: a still or a jump in time; otherwise (time passing in play) the lanterns are lit one
## after another as their light fades in (render3d/lamps.gd).
func _set_hours(h: float, instant := true) -> void:
	env.set_time(h)
	_fit_crown_proxy(h)
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
		verts[i] = Vector3(v.x * r * lob, v.y * ry, v.z * r * lob)
	arr[Mesh.ARRAY_VERTEX] = verts
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance3D.new()
	mi.name = "CrownShadow"
	mi.mesh = mesh
	mi.position = Vector3(float(c[0]), cy, float(c[2]))
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	parent.add_child(mi)
	crown_proxy = mi
	crown_proxy_at = mi.position
	crown_proxy_r = r
	_fit_crown_proxy(env.hours)


## The proxy shrinks and steps back from a low sun (morning, and toward dusk): the last low light
## comes in between the leaf masses on the crown's sunward side (the climbing path, the branch nest
## and the crows' nest catch it; scene agent 14:45), while the high sun of the day still finds a
## solid crown.
var crown_proxy: MeshInstance3D
var crown_proxy_at := Vector3.ZERO
var crown_proxy_r := 0.0


func _fit_crown_proxy(h: float) -> void:
	if crown_proxy == null:
		return
	var sd := W3Env.sun_direction(h)
	var k := lerpf(0.5, 1.0, smoothstep(0.12, 0.45, sd.y))
	var away := Vector3(-sd.x, 0.0, -sd.z).normalized() * crown_proxy_r * (1.0 - k) * 0.9
	crown_proxy.scale = Vector3(k, lerpf(0.75, 1.0, k), k)
	crown_proxy.position = crown_proxy_at + away


func _set_foliage_shader(n: Node, sh: Shader) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mi := n as MeshInstance3D
		for si in mi.mesh.get_surface_count():
			var m := mi.get_active_material(si)
			if m is ShaderMaterial and String((m as ShaderMaterial).shader.resource_path).ends_with("toon_foliage.gdshader"):
				(m as ShaderMaterial).shader = sh
	for c in n.get_children():
		_set_foliage_shader(c, sh)


## How a tree that stands between her and the camera lets her through (round 4, item 4: the
## trunk, the limbs and the leaves of one tree always go together). --cutmode=
##   cut  (default) every part of the tree opens the same hole around her (the same radius, the same
##        scattered edge), so a limb never hangs in a hole of leaves;
##   fade the whole tree turns see-through at once (a share of its pixels let through, eased);
##   none nothing opens: her silhouette shows through (the x-ray pass).
## The great tree is always "cut" (she walks under it; it keeps its lowest boughs at the top).
var cut_mode := "cut"
var _fade_objs: Array = []        # [node, base position, height m, [GeometryInstance3D], fade]


func _tree_cutaway(n: Node3D, k: float, height: float, dense := false) -> void:
	var mode := cut_mode if not dense else "cut"
	_set_cut(n, k if mode == "cut" else 0.0, dense)
	if mode == "fade" and height > 2.5:
		var gis: Array = []
		_collect_geometry(n, gis)
		_fade_objs.append([n, n.global_position, height, gis, 0.0])


func _set_cut(n: Node, k: float, dense: bool) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var mi := n as MeshInstance3D
		for si in mi.mesh.get_surface_count():
			var m := mi.get_active_material(si)
			if not (m is ShaderMaterial):
				continue
			var sm := m as ShaderMaterial
			var path := String(sm.shader.resource_path)
			if not (path.contains("toon_solid") or path.contains("foliage")):
				continue
			sm.set_shader_parameter("cutaway", k > 0.0)
			sm.set_shader_parameter("cutaway_scale", maxf(k, 1.0))
			if dense:
				# under the great crown the view keeps its lowest boughs along the top edge (she
				# stands under a roof of leaves; everything nearer to her than that opens)
				sm.set_shader_parameter("cutaway_keep_px", 96.0)
				if path.contains("foliage"):
					# the great evergreen crown: a deep shade in its heart (the crown proxy), in big
					# masses toward its rim (the cards cast a little larger than drawn; the sun
					# flecks on the ground are the terrain's own)
					sm.set_shader_parameter("shadow_shrink", 1.2)
					sm.set_shader_parameter("shadow_sieve", 0.0)
					# seen from its shaded side at midday: keep the masses, not a black lid (the
					# sky light and the VoxelGI bounce do most of it since round 4)
					sm.set_shader_parameter("shade_fill", 0.2)
				else:
					sm.set_shader_parameter("shade_fill", 0.3)
	for c in n.get_children():
		_set_cut(c, k, dense)


func _collect_geometry(n: Node, out: Array) -> void:
	if n is GeometryInstance3D and (n as GeometryInstance3D).cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY:
		out.append(n)
	for c in n.get_children():
		_collect_geometry(c, out)


## cutmode "fade": a tree hides her when her chest falls inside its drawn box and it stands nearer
## the camera (south of her); then all of it eases to see-through, and back when she leaves.
func _update_fades(dt: float) -> void:
	if _fade_objs.is_empty() or her == null:
		return
	var feet := her.pos
	var chest := pv.screen_of_upright(feet, 1.0)
	for o in _fade_objs:
		var base: Vector3 = o[1]
		var h: float = o[2]
		var target := 0.0
		if base.z > feet.z + 0.4 and base.z < feet.z + h * 1.6:
			var b0 := pv.screen_of_upright(base, 0.0)
			var b1 := pv.screen_of_upright(base, h)
			var half_w := h * 0.42 * PixelView3D.PPM
			if chest.x > b0.x - half_w and chest.x < b0.x + half_w and chest.y > b0.y + 6.0 and chest.y < b1.y:
				target = 0.62
		var f: float = o[4]
		f = move_toward(f, target, dt * 2.5)
		if f != o[4]:
			o[4] = f
			for g in o[3]:
				(g as GeometryInstance3D).set_instance_shader_parameter("obj_fade", f)


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
	her.set_xray_colour(Color(1.0, 0.84, 0.52))
	saji.set_xray_colour(Color(0.62, 0.86, 1.0))
	# (the 3D model casts its own shadow: her contact shadow is only the darkening right under her feet)
	her_shadow = _contact_shadow(Vector2(8.0, 3.0) if her.model else Vector2(9.0, 3.5))
	saji_shadow = _contact_shadow(Vector2(7.0, 3.0))
	# (comparison: the 3D model casts its own shadow; --nocontact hides the painted contact ellipse)
	if args.has("nocontact"):
		her_shadow.visible = false
		saji_shadow.visible = false


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


## Where she is asked to walk (world x/z, length 0..1): the keys (WASD, arrows), else a pad's left
## stick (its tilt is her pace) or its D-pad.
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
	if d.length() > 0.0:
		return d.normalized()
	return _pad_dir()


const PAD_DEADZONE := 0.2

## The pads (any connected): the left stick past a round dead zone (as tilted, at most 1; so a slight
## tilt is a slow walk, and anything past the dead zone is at least 0.2, enough to turn her), else the
## D-pad. Zero when nothing is held.
func _pad_dir() -> Vector2:
	var devs: Array[int] = Input.get_connected_joypads()
	if devs.is_empty():
		devs = [0]      # (events given to Input for device 0 count too: render3d/dev/shell_check.gd)
	var best := Vector2.ZERO
	for dev in devs:
		var v := Vector2(Input.get_joy_axis(dev, JOY_AXIS_LEFT_X), Input.get_joy_axis(dev, JOY_AXIS_LEFT_Y))
		if v.length() > PAD_DEADZONE and v.length() > best.length():
			best = v.limit_length(1.0)
	if best != Vector2.ZERO:
		return best
	for dev in devs:
		var dp := Vector2(float(Input.is_joy_button_pressed(dev, JOY_BUTTON_DPAD_RIGHT)) - float(Input.is_joy_button_pressed(dev, JOY_BUTTON_DPAD_LEFT)),
			float(Input.is_joy_button_pressed(dev, JOY_BUTTON_DPAD_DOWN)) - float(Input.is_joy_button_pressed(dev, JOY_BUTTON_DPAD_UP)))
		if dp != Vector2.ZERO:
			return dp.normalized()
	return Vector2.ZERO


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


func _make_route(given: Array = []) -> void:
	# Round the great camphor: out of the hut's door and across the yard, up the west side of the tree
	# between its trunk and the shrine's terrace; round the north side under the limbs and the crown
	# (she walks in a clearing in the leaves, the limbs reaching out over her); onto the old road and
	# south under the east limb that arches over it, to stop where the trunk and its rope are in view
	# (about 52 m, near 24 s)
	var pts := [Vector2(-17.6, 15.3), Vector2(-14.2, 15.2), Vector2(-13.1, 13.6), Vector2(-13.0, 10.8),
		Vector2(-11.2, 10.0), Vector2(-8.0, 9.9), Vector2(-6.4, 8.6), Vector2(-5.6, 5.0), Vector2(-6.0, 2.5),
		Vector2(-6.2, -1.0), Vector2(-5.5, -4.5), Vector2(-2.0, -7.0), Vector2(2.0, -6.9), Vector2(5.0, -5.4),
		Vector2(5.7, -3.0), Vector2(7.0, -0.5), Vector2(9.4, 1.0), Vector2(9.3, 4.0)]
	if not given.is_empty():
		pts = given
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
	# arrived; or stopped close to it by something in the way for a second (a waypoint the layout's
	# props have since crowded: the recording walks on rather than pushing at it forever)
	if d.length() < 0.6 or (d.length() < 1.3 and _stall_t > 1.0):
		if d.length() >= 0.6:
			print("ROUTE skip i=%d (stopped %.2f m short)" % [route_i, d.length()])
		route_i += 1
		_stall_t = 0.0
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
	if args.has("route_log") and _stall_t > 2.0 and _stall_t - get_process_delta_time() <= 2.0:
		# what holds her (debugging the layout's routes): the nearest round footprints
		var near: Array = []
		for b in her.blockers:
			var bp: Vector3 = b[0]
			var dd := Vector2(bp.x - her.pos.x, bp.z - her.pos.z).length() - float(b[1])
			if dd < 0.8:
				near.append("(%.2f, %.2f) r %.2f gap %.2f" % [bp.x, bp.z, float(b[1]), dd])
		print("ROUTE stalled at (%.2f, %.2f) toward (%.2f, %.2f): %s; walkable ahead %s" % [her.pos.x, her.pos.z, t.x, t.y,
			", ".join(near), str(terrain.walkable(her.pos.x + d.x * 0.4, her.pos.z + d.y * 0.4))])


# ------------------------------------------------------------------------------------------------

var _shot_list: Array = []
var _shot_i := 0


## The barrier's look follows where she stands, eased (she crosses a gate's fog band in two or three
## seconds); a cut (a still, a jump) sets it at once.
func _update_realm(dt: float) -> void:
	if realm_mask == null or her == null:
		return
	var here: Color = realm_mask.sample(her.pos.x, her.pos.z)
	var target: float = here.r
	var swell := smoothstep(0.62, 0.95, here.g)
	if _realm_k < 0.0:
		_realm_k = target
		_swell_k = swell
	else:
		_realm_k = lerpf(_realm_k, target, 1.0 - exp(-dt * 1.5))
		_swell_k = lerpf(_swell_k, swell, 1.0 - exp(-dt * 2.0))
	env.set_realm(_realm_k)
	env.set_band_swell(_swell_k)


func _set_view(i: int) -> void:
	var v: Array = _shot_list[i]
	her.place(Vector3(v[0], 0.0, v[1]))
	_realm_k = -1.0
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
			# (a pad: the stick or the D-pad left and right turns her head, up or down steps away)
			var pad := _pad_dir()
			if _key(KEY_A) or _key(KEY_LEFT) or pad.x < -0.5:
				vista.turn(-1.0, dt)
			if _key(KEY_D) or _key(KEY_RIGHT) or pad.x > 0.5:
				vista.turn(1.0, dt)
			if _key(KEY_W) or _key(KEY_S) or _key(KEY_UP) or _key(KEY_DOWN) or (absf(pad.y) > 0.6 and absf(pad.y) > absf(pad.x)):
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
	if frame == _gi_bake_at:
		_bake_gi()
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
	if args.has("perf") and frame == 3:
		RenderingServer.viewport_set_measure_render_time(pv.vp.get_viewport_rid(), true)
	if args.has("perf") and vista and vista.vp and frame % 60 == 1:
		RenderingServer.viewport_set_measure_render_time(vista.vp.get_viewport_rid(), true)
	if args.has("perf") and frame % 60 == 0 and frame > 0 and vista and vista.shown:
		# (the view from the lookout: its own viewport's render time while it is shown)
		print("PERF_VISTA f=%d fps=%.1f vista_gpu_ms=%.1f vista_cpu_ms=%.1f draws=%d" % [frame, Performance.get_monitor(Performance.TIME_FPS),
			RenderingServer.viewport_get_measured_render_time_gpu(vista.vp.get_viewport_rid()), RenderingServer.viewport_get_measured_render_time_cpu(vista.vp.get_viewport_rid()),
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)])
	if args.has("perf") and frame % 60 == 0 and frame > 0:
		# (the world viewport's own render time: on the software rasteriser "gpu" is the rasterising)
		var vr := pv.vp.get_viewport_rid()
		print("PERF f=%d fps=%.1f draws=%d prims=%d objects=%d vram_mb=%.0f world_gpu_ms=%.1f world_cpu_ms=%.1f" % [frame, Performance.get_monitor(Performance.TIME_FPS),
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME), Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
			RenderingServer.viewport_get_measured_render_time_gpu(vr), RenderingServer.viewport_get_measured_render_time_cpu(vr)])
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
	_update_fades(dt)
	_update_realm(dt)
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
