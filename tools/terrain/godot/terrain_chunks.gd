class_name TerrainChunks
extends Node2D
## Draws a baked terrain region (tools/terrain) lit: one Sprite2D per chunk with a CanvasTexture
## (albedo + normal map) and terrain.gdshader (baked sun horizon + sky visibility).
## Reference implementation for the core (docs/knowledge/17-terrain-pipeline.md); not wired in yet.
##
##   var t := TerrainChunks.new()
##   add_child(t)
##   t.load_region("res://world/regions/home_saddle", region_def)   # region_def = parsed region.json
##   t.set_sun(elevation_deg)                                         # every frame or on time change
##
## Lighting contract: CanvasModulate = ambient (sky) colour; one DirectionalLight2D = the sun's
## colour and energy (its 2D direction is ignored by the terrain: the world-space sun vector below
## is used instead); PointLight2D lanterns work through the normal map.

var materials: Array[ShaderMaterial] = []
var toward_xz := Vector2(-0.92, 0.38)   # fixed azimuth from the bake (region.json terrain.sun.toward_xz)


func load_region(dir: String, def: Dictionary) -> void:
	var t: Dictionary = def.get("terrain", {})
	if t.is_empty():
		push_error("TerrainChunks: region has no 'terrain' section")
		return
	var sun: Dictionary = t.get("sun", {})
	var tw: Array = sun.get("toward_xz", [-0.92, 0.38])
	toward_xz = Vector2(tw[0], tw[1]).normalized()
	var shader := load(dir.path_join(String(t.get("shader", "terrain.gdshader")))) as Shader
	for c in t.get("chunks", []):
		var files: Dictionary = c["files"]
		var ct := CanvasTexture.new()
		ct.diffuse_texture = load(dir.path_join(files["albedo"])) as Texture2D
		ct.normal_texture = load(dir.path_join(files["normal"])) as Texture2D
		ct.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		var s := Sprite2D.new()
		s.name = String(c["name"])
		s.texture = ct
		s.centered = false
		s.position = Vector2(c["pos_px"][0], c["pos_px"][1])
		var m := ShaderMaterial.new()
		m.shader = shader
		m.set_shader_parameter("light_tex", load(dir.path_join(files["light"])) as Texture2D)
		s.material = m
		materials.append(m)
		add_child(s)


## Sun elevation in degrees above the horizon (the azimuth is fixed: upper left of the screen).
## Changing it continuously moves every shadow continuously (no jumps, R-7).
func set_sun(elevation_deg: float, bounce_k: float = 0.45) -> void:
	var e := deg_to_rad(elevation_deg)
	var d := Vector3(toward_xz.x * cos(e), sin(e), toward_xz.y * cos(e))
	for m in materials:
		m.set_shader_parameter("sun_dir", d)
		m.set_shader_parameter("sun_elev_deg", elevation_deg)
		m.set_shader_parameter("bounce_k", bounce_k)
