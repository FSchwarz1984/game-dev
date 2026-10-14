class_name FloraField
extends RefCounted
## What every plant from tools/flora shares at run time (docs/knowledge/18-vegetation.md): where she
## is (x-ray holes in crowns and big trunks), the wind, and the sun of the lighting contract shared
## with the terrain (the same sun_dir and sun_elev_deg the terrain shader takes).
##
## Plants (FloraPlant) register their materials when they enter the tree and drop them when they
## leave. A plant scene's materials are shared by all its instances, so one call per material
## reaches every copy: the cost does not grow with the number of plants placed.
##
##   FloraField.set_player(feet_px, sort_y)    every frame: her feet as drawn (Proj.to_px(x, z, h))
##                                             and her ground point y (Proj.sort_px(x, z).y)
##   FloraField.set_sun(elev_deg, sun_color, sky_color)   when the time of day changes: sun_color =
##                                             the DirectionalLight2D colour * energy, sky_color = the
##                                             CanvasModulate colour
##   FloraField.set_wind(strength)             0 calm, 1 normal, 2 gale

## Toward the sun on the ground (x east, z south). Must match the terrain bake (tools/terrain,
## region.json "sun.toward_xz") and tools/flora/flora/core.py SUN_TOWARD_XZ.
const TOWARD_XZ := Vector2(-0.92, 0.38)

enum Kind { LIT, SHADOW }

static var _mats: Dictionary = {}     # ShaderMaterial -> {"kind", "users", "occluder"}
static var player_feet := Vector2(-100000, -100000)
static var player_sort_y := -100000.0
static var wind := 1.0
static var sun_dir := Vector3(-0.708, 0.643, 0.292)
static var sun_elev_deg := 40.0
static var shade_color := Color(0.50, 0.53, 0.62)
static var shadow_strength := 1.0


static func add_plant(plant: Node) -> void:
	for c in plant.get_children():
		var ci := c as CanvasItem
		if ci == null or not (ci.material is ShaderMaterial):
			continue
		var m := ci.material as ShaderMaterial
		if _mats.has(m):
			_mats[m]["users"] += 1
			continue
		var is_shadow := m.shader != null and m.shader.resource_path.ends_with("flora_shadow.gdshader")
		var e := {"kind": Kind.SHADOW if is_shadow else Kind.LIT, "users": 1,
			"occluder": not is_shadow and bool(m.get_shader_parameter("occluder"))}
		_mats[m] = e
		_apply(m, e)


static func remove_plant(plant: Node) -> void:
	for c in plant.get_children():
		var ci := c as CanvasItem
		if ci == null or not (ci.material is ShaderMaterial) or not _mats.has(ci.material):
			continue
		_mats[ci.material]["users"] -= 1
		if _mats[ci.material]["users"] <= 0:
			_mats.erase(ci.material)


static func set_player(feet_px: Vector2, sort_y: float) -> void:
	player_feet = feet_px
	player_sort_y = sort_y
	for m in _mats:
		if _mats[m]["occluder"]:
			m.set_shader_parameter("player_feet", feet_px)
			m.set_shader_parameter("player_sort_y", sort_y)


static func set_wind(strength: float) -> void:
	wind = strength
	for m in _mats:
		if _mats[m]["kind"] == Kind.LIT:
			m.set_shader_parameter("wind_strength", strength)


## The sun at elev_deg above the horizon on the fixed azimuth. A plant's shadow on open ground ends
## as dark as the terrain's own shadows: lit ground = albedo * (sky + sun * N.L), shadowed = albedo
## * sky (the terrain shader's model), so the shadow multiplies by sky / (sky + sun * N.L).
static func set_sun(elev_deg: float, sun_color: Color, sky_color: Color, strength: float = 1.0) -> void:
	var d := TOWARD_XZ.normalized()
	var e := deg_to_rad(elev_deg)
	sun_dir = Vector3(d.x * cos(e), sin(e), d.y * cos(e))
	sun_elev_deg = elev_deg
	var ndl := maxf(sun_dir.y, 0.0)
	shade_color = Color(_ratio(sky_color.r, sun_color.r * ndl), _ratio(sky_color.g, sun_color.g * ndl),
		_ratio(sky_color.b, sun_color.b * ndl))
	shadow_strength = strength
	for m in _mats:
		_apply_sun(m, _mats[m])


static func _ratio(sky: float, sun: float) -> float:
	return clampf(sky / maxf(sky + sun, 0.0001), 0.0, 1.0)


static func _apply(m: ShaderMaterial, e: Dictionary) -> void:
	if e["kind"] == Kind.LIT:
		m.set_shader_parameter("wind_strength", wind)
		if e["occluder"]:
			m.set_shader_parameter("player_feet", player_feet)
			m.set_shader_parameter("player_sort_y", player_sort_y)
	_apply_sun(m, e)


static func _apply_sun(m: ShaderMaterial, e: Dictionary) -> void:
	if e["kind"] == Kind.LIT:
		m.set_shader_parameter("sun_dir", sun_dir)
	else:
		m.set_shader_parameter("sun_elev_deg", sun_elev_deg)
		m.set_shader_parameter("shade_color", shade_color)
		m.set_shader_parameter("shadow_strength", shadow_strength)
