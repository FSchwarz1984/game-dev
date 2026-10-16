class_name W3Grass
extends Node3D
## Ground vegetation (scene agent).
## Round 5 (decision-log G5R3-2, "旷野之息、原神那种：自然柔顺，和地面同一个色系、协调又分得开，有物理效果"):
## * the grass field: a continuous sward of small blade tufts (tools/world3d/w3terrain/grassfield.py ->
##   terrain/<name>/grass.bin), MultiMesh chunks drawn with grass_field.gdshader, which colours and lights
##   every tuft as the ground it grows from (the terrain's own palette, macro tone, AO, shade and sun
##   flecks) with the tips a tone lighter; it sways by whole pixels, gust fronts run across it with the
##   wind, and it is pushed aside and pressed down where she, Saji and the small creatures walk (the bend
##   map below), standing up again over a few seconds;
## * the accents (tools/world3d/w3terrain/cover.py -> cover.bin): ferns, sasa, pampas grass, horsetail,
##   moss cushions, the late-summer flowers and the weeds at the feet of walls and fences, as pixel-art
##   cards in the renderer's outline-less foliage material (card mode, lean 0).
## Binaries are gzip-compressed (read_blob inflates them; stonework.gd uses it too).
##
## The bend map: a SubViewport over the whole region (0.25 m a texel, the splat grid) that keeps its
## content from frame to frame. Each frame a full-rect pass moves every texel back toward "upright"
## (at least one 8-bit step, so everything recovers), then a stamp is drawn under every walker:
## rg = the push direction (x, z; 0.5 = none), b = pressed. Anything can push grass with
## W3Grass.push_at(world_pos, radius) once per frame (the small creatures do).

var terrain: Terrain3D
var mat := ShaderMaterial.new()          # the accents (foliage cards)
var grass_mat := ShaderMaterial.new()    # the grass field
var count := 0
var tris := 0
var tufts := 0
var bend_vp: SubViewport
var _decay: ColorRect
var _stamps: Array[ColorRect] = []
var _stamp_mat: ShaderMaterial
var _bend_origin := Vector2(-80.0, -96.0)
var _bend_cell := 0.25
var _first := true
var walkers: Array = []                  # nodes with a `pos` (feet, world): pressed every frame
static var _pushes: Array = []           # [Vector3, radius] queued by push_at() this frame

const RECOVER_S := 1.3                   # time constant of the grass standing up again


func build(t: Terrain3D) -> void:
	terrain = t
	_build_field(t)
	_build_accents(t)


## Queue a push for this frame (world position of the feet, radius in metres).
static func push_at(p: Vector3, r: float = 0.25) -> void:
	_pushes.append([p, r])


# ------------------------------------------------------------------------------------------------
# the grass field

func _build_field(t: Terrain3D) -> void:
	var info: Dictionary = t.info.get("grass", {})
	if info.is_empty():
		push_warning("W3Grass: the terrain has no grass field (rebuild it with tools/world3d/build_terrain.py)")
		return
	var dir := "res://world3d/terrain/" + String(t.info.get("name", "saddle"))
	var atlas: Image = load(String(info.get("atlas", "res://world3d/terrain/common/grass_blades.png")))
	var sward: Image = load(dir.path_join(String(info.get("map", "m4.png"))))
	if atlas == null or sward == null:
		push_warning("W3Grass: the grass atlas or the sward map is missing")
		return
	var lattice := int(info.get("lattice", 50))
	var chunk := float(info.get("chunk", 16.0))
	grass_mat.shader = load("res://world3d/grass_field.gdshader")
	grass_mat.set_shader_parameter("blades", ImageTexture.create_from_image(atlas))
	grass_mat.set_shader_parameter("m4", ImageTexture.create_from_image(sward))
	grass_mat.set_shader_parameter("cols", int(info.get("cols", 8)))
	grass_mat.set_shader_parameter("lattice", lattice)
	grass_mat.set_shader_parameter("chunk", chunk)
	grass_mat.set_shader_parameter("heights", t.height_texture())
	grass_mat.set_shader_parameter("h_origin", t.origin)
	grass_mat.set_shader_parameter("h_cell", t.cell)
	grass_mat.set_shader_parameter("h_size", Vector2(t.nx, t.nz))
	# the terrain's own data, so the grass is the ground's colour and light
	var tm: ShaderMaterial = t.terrain_mat
	for k in ["palette", "m2", "m3", "splat_origin", "splat_cell", "splat_size", "dry_bias", "shade_flatten"]:
		var v: Variant = tm.get_shader_parameter(k)
		if v != null:
			grass_mat.set_shader_parameter(k, v)
	var so: Variant = tm.get_shader_parameter("splat_origin")
	var ssz: Variant = tm.get_shader_parameter("splat_size")
	var sc: Variant = tm.get_shader_parameter("splat_cell")
	if so != null and ssz != null and sc != null:
		_bend_origin = so
		_bend_cell = float(sc)
		_make_bend(Vector2i(int(ssz.x) - 1, int(ssz.y) - 1))
	# one quad, the root one pixel into the ground, a 16 x 16 cell texel for pixel (the shader builds it)
	var q := ArrayMesh.new()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3(-0.27, 0, 0), Vector3(0.27, 0, 0), Vector3(0.27, 0.5, 0), Vector3(-0.27, 0.5, 0)])
	arr[Mesh.ARRAY_NORMAL] = PackedVector3Array([Vector3.UP, Vector3.UP, Vector3.UP, Vector3.UP])
	arr[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arr[Mesh.ARRAY_TEX_UV2] = PackedVector2Array([Vector2(-8, -1), Vector2(8, -1), Vector2(8, 15), Vector2(-8, 15)])
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 2, 1, 0, 3, 2])
	q.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	# one lattice for every chunk: the instances only carry their index (the shader places them)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = q
	mm.instance_count = lattice * lattice
	var buf := PackedFloat32Array()
	buf.resize(lattice * lattice * 12)
	for k in lattice * lattice:
		buf[k * 12] = 1.0
		buf[k * 12 + 5] = 1.0
		buf[k * 12 + 10] = 1.0
	mm.buffer = buf
	# the instances all sit at the chunk's corner; the shader spreads them over the chunk and puts
	# them on the ground: the bounds cover the chunk and the whole height range (each chunk node
	# narrows them with its own custom_aabb)
	var hr: Dictionary = t.info.get("height", {"min": -50.0, "range": 120.0})
	mm.custom_aabb = AABB(Vector3(-0.6, float(hr["min"]) - 0.5, -1.0), Vector3(chunk + 1.2, float(hr["range"]) + 2.0, chunk + 1.6))
	for c in info.get("chunks", []):
		var o: Array = c["origin"]
		var yr: Array = c["y"]
		var mi := MultiMeshInstance3D.new()
		mi.name = "Grass_%d_%d" % [int(o[0]), int(o[1])]
		mi.multimesh = mm
		mi.material_override = grass_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# (renderer: out of the VoxelGI bake, which plots every instance where its transform says, all
		# 2500 at the chunk's corner: wrong blobs in the GI and bake time; the ground carries the GI)
		mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		mi.position = Vector3(float(o[0]), 0.0, float(o[1]))
		# the tufts stand on the ground anywhere in the chunk; the cards lean back up to half a metre
		mi.custom_aabb = AABB(Vector3(-0.6, float(yr[0]), -1.0), Vector3(chunk + 1.2, float(yr[1]) - float(yr[0]) + 0.6, chunk + 1.6))
		add_child(mi)
	tufts = int(info.get("stats", {}).get("tufts", 0))
	count += tufts


func _make_bend(size: Vector2i) -> void:
	bend_vp = SubViewport.new()
	bend_vp.name = "GrassBend"
	bend_vp.size = size
	bend_vp.disable_3d = true
	bend_vp.transparent_bg = false
	bend_vp.use_hdr_2d = false
	bend_vp.render_target_clear_mode = SubViewport.CLEAR_MODE_NEVER
	bend_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	bend_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	add_child(bend_vp)
	_decay = ColorRect.new()
	_decay.size = Vector2(size)
	var dm := ShaderMaterial.new()
	dm.shader = load("res://world3d/grass_bend_decay.gdshader")
	_decay.material = dm
	bend_vp.add_child(_decay)
	_stamp_mat = ShaderMaterial.new()
	_stamp_mat.shader = load("res://world3d/grass_bend_stamp.gdshader")
	grass_mat.set_shader_parameter("bend", bend_vp.get_texture())
	grass_mat.set_shader_parameter("bend_origin", _bend_origin)
	grass_mat.set_shader_parameter("bend_extent", Vector2(size) * _bend_cell)


func _process(delta: float) -> void:
	if bend_vp == null:
		_pushes.clear()
		return
	var dm := _decay.material as ShaderMaterial
	dm.set_shader_parameter("k", 1.0 - exp(-max(delta, 0.0) / RECOVER_S))
	dm.set_shader_parameter("init", _first)
	_first = false
	var list: Array = []
	if walkers.is_empty():
		_find_walkers()
	for w in walkers:
		if is_instance_valid(w):
			var p: Vector3 = w.get("pos")
			# only on the ground (not up the great camphor)
			if terrain == null or p.y - terrain.height_at(p.x, p.z) < 0.4:
				list.append([p, 0.5 if list.is_empty() else 0.38])
	list.append_array(_pushes)
	_pushes.clear()
	while _stamps.size() < list.size():
		var s := ColorRect.new()
		s.material = _stamp_mat
		bend_vp.add_child(s)
		_stamps.append(s)
	for i in _stamps.size():
		var s := _stamps[i]
		if i >= list.size():
			s.visible = false
			continue
		var p: Vector3 = list[i][0]
		var r: float = list[i][1]
		var c := (Vector2(p.x, p.z) - _bend_origin) / _bend_cell
		var rp := r / _bend_cell
		s.visible = true
		s.position = c - Vector2(rp, rp)
		s.size = Vector2(rp, rp) * 2.0


func _find_walkers() -> void:
	var sc := _sample_node()
	if sc == null:
		return
	for k in ["her", "saji"]:
		var w: Variant = sc.get(k)
		# (an unseen walker, the sample's --nochar, bends no grass: grass pressed by no one reads as
		# something there)
		if w is Object and is_instance_valid(w) and (w as Object).get("pos") != null and (w as Object).get("ghost") != true:
			walkers.append(w)


## The scene that holds her (`her`, `saji`): the nearest ancestor that has them. The sample is the
## tree's current scene only when it runs on its own; in the showcase (the Windows build) the
## showcase is, and the sample one of its children (G5R3-24: no grass bent under her there).
func _sample_node() -> Node:
	var n := get_parent()
	while n != null:
		if "her" in n:
			return n
		n = n.get_parent()
	return get_tree().current_scene


# ------------------------------------------------------------------------------------------------
# the accents (cover.bin)

func _build_accents(t: Terrain3D) -> void:
	var info: Dictionary = t.info.get("cover", {})
	if info.is_empty():
		return
	var atlas: Image = load(String(info.get("atlas", "res://world3d/terrain/common/cover.png")))
	mat.shader = load("res://render3d/shaders/toon_foliage_noline.gdshader")
	mat.set_shader_parameter("foliage_mode", 1)
	mat.set_shader_parameter("leaf_tex", ImageTexture.create_from_image(atlas))
	mat.set_shader_parameter("lean", 0.0)
	mat.set_shader_parameter("cutaway", false)
	mat.set_shader_parameter("wind_px", 1.0)
	mat.set_shader_parameter("porosity", 0.6)
	mat.set_shader_parameter("lush", 0.0)
	# (round 5, renderer: the ground cover is painted for one sRGB conversion; round 3's deeper palette
	# for leaves, w3_ukiyo_tex, is not for it: the cover's darks went black)
	mat.set_shader_parameter("ukiyo", 0.0)
	mat.set_shader_parameter("transmit", 0.35)
	var dir := "res://world3d/terrain/" + String(t.info.get("name", "saddle"))
	var raw := W3Grass.read_blob(dir.path_join(String(info.get("file", "cover.bin"))))
	if raw.is_empty():
		return
	var fmt := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
	for c in info.get("chunks", []):
		var n := int(c["vertices"])
		var nt := int(c["triangles"])
		var o := int(c["offset"])
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = raw.slice(o, o + n * 12).to_vector3_array()
		o += n * 12
		arr[Mesh.ARRAY_NORMAL] = raw.slice(o, o + n * 12).to_vector3_array()
		o += n * 12
		arr[Mesh.ARRAY_TEX_UV] = raw.slice(o, o + n * 8).to_vector2_array()
		o += n * 8
		arr[Mesh.ARRAY_TEX_UV2] = raw.slice(o, o + n * 8).to_vector2_array()
		o += n * 8
		arr[Mesh.ARRAY_COLOR] = raw.slice(o, o + n * 16).to_color_array()
		o += n * 16
		arr[Mesh.ARRAY_CUSTOM0] = raw.slice(o, o + n * 16).to_float32_array()
		o += n * 16
		arr[Mesh.ARRAY_INDEX] = raw.slice(o, o + nt * 12).to_int32_array()
		var m := ArrayMesh.new()
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr, [], {}, fmt)
		var a: Array = c["aabb"]
		m.custom_aabb = AABB(Vector3(a[0][0], a[0][1], a[0][2]) - Vector3(1.0, 1.0, 1.5), Vector3(a[1][0], a[1][1], a[1][2]) + Vector3(2.0, 2.5, 3.0))
		var mi := MeshInstance3D.new()
		mi.name = "Cover_%d_%d_%s" % [int(c["chunk"][0]), int(c["chunk"][1]), String(c["layer"])]
		mi.mesh = m
		mi.material_override = mat
		var tall := String(c["layer"]) == "tall"
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if tall else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		count += n / 4
		tris += nt
	print("COVER grass=%d accents=%d tris=%d species=%s" % [tufts, count - tufts, tris, str(info.get("species", {}))])


## The bytes of a baked binary (grass.bin, cover.bin, roads.bin): gzip-compressed since round 4b (the
## terrain generator writes them with mtime 0, so they are committed as they are); a raw file still loads.
static func read_blob(path: String) -> PackedByteArray:
	var b := FileAccess.get_file_as_bytes(path)
	if b.size() > 2 and b[0] == 0x1f and b[1] == 0x8b:
		return b.decompress_dynamic(1 << 28, FileAccess.COMPRESSION_GZIP)
	return b
