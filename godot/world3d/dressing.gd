class_name W3Dressing
extends Node3D
## The scene's dressing (round 4, scene agent): every placed thing that is not a tree or a rock
## comes from the layout's prop list (terrain.json "props", written by tools/world3d from
## tools/world3d/layouts/<name>.json) and is handed to the assembly as asset slots (sample.gd places
## them from the catalog, adds their footprints to what blocks her, swaps lit variants at dusk).
## Lamps (stone lanterns, paper lanterns, the brazier inside the house) register their light with
## the renderer's lamps. Small life that moves (crows, sparrows, dragonflies, butterflies, frogs,
## the cat's tail) lives in W3Life (dressing_life, built here when the catalog has the creatures).
##
## The east gate's giant straw sandal (node "Waraji" in michikiri_e) turns slowly on its cord.
##
## A prop entry: {"name": catalog name, "x", "z", "yaw" (degrees), "hang" (m above the ground,
## for things hung from an eave or a hook; leaned like what they hang from), "light": [height above
## the prop's origin, energy, reach] (a lamp: lit from dusk to dawn), "anchor": [prop name, anchor
## name] (place at another prop's anchor instead of x/z)}.

var terrain: Terrain3D
var lamps: W3Lamps                # the renderer's lamps (set by the assembly before build())
var _lit := -1                     # lamps on (1), off (0), not yet set (-1)
var flames: Array = []      # [ShaderMaterial, base energy]
var glints: Array = []    # [position, phase] places that catch the light (the offering box's coins)
var asset_slots: Array = []   # [catalog name, position, yaw]: placed by the assembly
var has_asset := {}       # names of things the asset catalog provides
var lean_k := 0.5206      # the camera's lean-back for upright things (tan(pitch / 2)), set by the sample
var catalog := {}
var placed := {}          # prop id or name -> [position, yaw] (for anchors of later props)


func build(t: Terrain3D, cat := {}) -> void:
	terrain = t
	catalog = cat
	for k in catalog:
		has_asset[k] = true
	var props: Array = t.info.get("props", [])
	for e in props:
		_prop(e)
	print("DRESSING props=%d slots=%d lamps=%d" % [props.size(), asset_slots.size(), _lamp_count])


var _lamp_count := 0
var _spin: Array = []        # [node, phase, base yaw]: things that turn in the wind on a cord
var _spin_t := 0.0
var _spin_looked := 0


## Things hung on a cord turn slowly back and forth (the gate's sandal). Found once the assembly has
## instanced the slots (a frame or two after build()).
func _process(delta: float) -> void:
	_spin_t += delta
	if _spin_looked < 2 and _spin_t > 0.2 * float(_spin_looked + 1):
		_spin_looked += 1
		_spin.clear()
		for n in get_tree().root.find_children("Waraji", "Node3D", true, false):
			_spin.append([n, fmod(float((n as Node3D).global_position.x) * 1.7, TAU), (n as Node3D).rotation.y])
	for sp in _spin:
		var n: Node3D = sp[0]
		if is_instance_valid(n):
			n.rotation.y = float(sp[2]) + 0.55 * sin(_spin_t * 0.33 + float(sp[1])) + 0.2 * sin(_spin_t * 0.12 + float(sp[1]) * 2.0)


func _prop(e: Dictionary) -> void:
	var nm := String(e.get("name", ""))
	if nm == "" or not catalog.has(nm):
		return
	var a: Dictionary = catalog[nm]
	var yaw := deg_to_rad(float(e.get("yaw", 0.0)))
	var pos := Vector3(float(e.get("x", 0.0)), 0.0, float(e.get("z", 0.0)))
	if e.has("anchor"):
		# at another placed prop's anchor (a lantern on the house's hook, the cat on the engawa)
		var host_key := String(e["anchor"][0])
		var host: Array = placed.get(host_key, [])
		var host_name := host_key
		if host.is_empty() and terrain.info.get("markers", {}).has(host_key):
			host = [terrain.marker(host_key), 0.0]
		if host.is_empty():
			return
		var host_cat: Dictionary = catalog.get(String(e.get("host", host_name)), {})
		var anc: Array = host_cat.get("anchors", {}).get(String(e["anchor"][1]), [0.0, 0.0, 0.0])
		var off := Vector3(anc[0], anc[1], anc[2]).rotated(Vector3.UP, float(host[1]))
		pos = Vector3((host[0] as Vector3).x, 0.0, (host[0] as Vector3).z) + Vector3(off.x, 0.0, off.z)
		if not e.has("hang"):
			e["hang"] = float(anc[1])
	var gy := terrain.height_at(pos.x, pos.z)
	pos.y = gy + float(e.get("hang", 0.0))
	asset_slots.append([nm, pos, yaw])
	placed[String(e.get("id", nm))] = [Vector3(pos.x, gy, pos.z), yaw]
	if e.has("light"):
		var l: Array = e["light"]
		var lp := pos + Vector3(0.0, float(l[0]), 0.0)
		lp.z -= lean_k * maxf(lp.y - gy, 0.0) * 0.0
		_light(lp + Vector3(0, 0, 0.2), Color(1.0, 0.68, 0.36), float(l[1]), float(l[2]))
		_lamp_count += 1
	if nm == "offering_box" or a.get("anchors", {}).has("glint"):
		var gl: Array = a.get("anchors", {}).get("glint", [])
		if not gl.is_empty():
			glints.append([pos + Vector3(gl[0], gl[1], float(gl[2]) - lean_k * float(gl[1])), 0.0])


func set_time(hours: float, instant := true) -> void:
	var dusk := clampf((hours - 17.6) / 1.4, 0.0, 1.0) if hours > 12.0 else 0.0
	var dawn := clampf((5.8 - hours) / 1.0, 0.0, 1.0) if hours < 12.0 else 0.0
	var on := maxf(dusk, dawn)
	if hours >= 19.0 or hours <= 4.8:
		on = 1.0
	# the lamps are lit at 18.4 h (and put out at dawn): one after another, each fading in
	var want := 1 if (hours >= 18.4 or hours <= 5.4) else 0
	if lamps and want != _lit:
		lamps.set_on(want == 1, instant or _lit < 0)
		_lit = want
	for f in flames:
		(f[0] as ShaderMaterial).set_shader_parameter("emission_energy", float(f[1]) * (0.15 + 0.85 * on))


## A lamp's light (the renderer lights it, render3d/lamps.gd). energy and reach are the old
## OmniLight numbers; the renderer's lamps reach a little less and step their light.
func _light(pos: Vector3, col: Color, energy: float, rng: float) -> void:
	if lamps:
		lamps.add(pos, rng * 0.85, col, energy * 0.75)
