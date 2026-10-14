extends Node
## Internal feature test of the 3D pixel renderer (never shipped): ground, a leaning box, a stone
## lantern, a card-crown tree, at a time of day; saves the low-res frame and the window.
##   godot --path godot res://render3d/dev/feature_test.tscn -- --hours=10 --shot=/tmp/a.png

var pv: PixelView3D
var env: W3Env
var frame := 0
var args := {}
var target := Vector3(0, 0, 0)


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1]
	pv = PixelView3D.new()
	if args.has("pitch"):
		pv.pitch_deg = float(args["pitch"])
	add_child(pv)
	env = W3Env.new()
	add_child(env)
	env.setup(pv)
	env.set_time(float(args.get("hours", "10")))
	_build()
	pv.follow(func() -> Vector3: return target, {"cut": true})


func _mat(shader_path: String, params: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load(shader_path)
	for k in params:
		m.set_shader_parameter(k, params[k])
	return m


func _height(x: float, z: float) -> float:
	var h := 2.4 * exp(-((x - 6.0) * (x - 6.0) + (z + 2.0) * (z + 2.0)) / 20.0)
	h += 0.5 * sin(x * 0.35) * cos(z * 0.27)
	h -= 3.0 * smoothstep(4.0, 12.0, z)          # falls away to the south
	return h


func _build() -> void:
	var root := pv.world_root
	# ground
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 120
	var S := 48.0
	for j in n + 1:
		for i in n + 1:
			var x := -S * 0.5 + S * i / n
			var z := -S * 0.5 + S * j / n
			st.set_color(Color(0.36, 0.42, 0.24, 1.0))
			st.set_uv2(Vector2(0, 0))
			st.add_vertex(Vector3(x, _height(x, z), z))
	for j in n:
		for i in n:
			var a := j * (n + 1) + i
			st.add_index(a); st.add_index(a + 1); st.add_index(a + n + 1)
			st.add_index(a + 1); st.add_index(a + n + 2); st.add_index(a + n + 1)
	st.generate_normals()
	var ground := MeshInstance3D.new()
	ground.mesh = st.commit()
	ground.material_override = _mat("res://render3d/shaders/toon_solid.gdshader", {"lean": 0.0})
	root.add_child(ground)
	# a hut-sized box with plank walls, on the ground
	var box := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(3.0, 2.4, 2.4)
	box.mesh = bm
	box.position = Vector3(-4.0, _height(-4.0, -1.0), -1.0)
	box.mesh = _offset_mesh(bm, Vector3(0, 1.2, 0), Color(0.55, 0.42, 0.28), Vector2(1, 0))
	box.material_override = _mat("res://render3d/shaders/toon_solid.gdshader", {"lean": 1.0})
	root.add_child(box)
	# stone lantern: stacked cylinders
	var lan := Node3D.new()
	lan.position = Vector3(1.5, _height(1.5, 2.0), 2.0)
	root.add_child(lan)
	var parts := [[0.0, 0.25, 0.32, 0.3], [0.25, 0.9, 0.12, 0.12], [0.9, 1.25, 0.28, 0.24], [1.25, 1.45, 0.42, 0.1]]
	for p in parts:
		var cm := CylinderMesh.new()
		cm.top_radius = p[3]
		cm.bottom_radius = p[2]
		cm.height = p[1] - p[0]
		cm.radial_segments = 8
		var mi := MeshInstance3D.new()
		mi.mesh = _offset_mesh(cm, Vector3(0, (p[0] + p[1]) * 0.5, 0), Color(0.5, 0.5, 0.46), Vector2(4, 0.6))
		mi.material_override = _mat("res://render3d/shaders/toon_solid.gdshader", {"lean": 1.0})
		lan.add_child(mi)
	# a light inside the lantern
	var omni := OmniLight3D.new()
	omni.position = Vector3(0, 1.07, 0)
	omni.light_color = Color(1.0, 0.62, 0.3)
	omni.light_energy = 2.0
	omni.omni_range = 5.0
	omni.omni_attenuation = 1.0
	omni.shadow_enabled = false
	lan.add_child(omni)
	# tree: trunk + card crown
	var tree := Node3D.new()
	tree.position = Vector3(5.5, _height(5.5, -5.0), -5.0)
	root.add_child(tree)
	var trunk := CylinderMesh.new()
	trunk.top_radius = 0.18
	trunk.bottom_radius = 0.32
	trunk.height = 3.2
	trunk.radial_segments = 8
	var tm := MeshInstance3D.new()
	tm.mesh = _offset_mesh(trunk, Vector3(0, 1.6, 0), Color(0.35, 0.27, 0.2), Vector2(2, 0))
	tm.material_override = _mat("res://render3d/shaders/toon_solid.gdshader", {"lean": 1.0})
	tree.add_child(tm)
	var crown := MeshInstance3D.new()
	crown.mesh = _card_crown(Vector3(0, 4.2, 0), Vector3(2.6, 1.9, 2.6), 170)
	crown.material_override = _mat("res://render3d/shaders/toon_foliage.gdshader", {"foliage_mode": 1, "leaf_tex": _leaf_atlas()})
	crown.extra_cull_margin = 4.0
	tree.add_child(crown)


## Re-centres a primitive mesh and gives it vertex colours and a pattern id (UV2).
func _offset_mesh(prim: PrimitiveMesh, off: Vector3, col: Color, pat: Vector2) -> ArrayMesh:
	var arr := prim.get_mesh_arrays()
	var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	for i in verts.size():
		verts[i] += off
	arr[Mesh.ARRAY_VERTEX] = verts
	var cols := PackedColorArray()
	var uv2 := PackedVector2Array()
	cols.resize(verts.size())
	uv2.resize(verts.size())
	for i in verts.size():
		cols[i] = col
		uv2[i] = pat
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_TEX_UV2] = uv2
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


func _leaf_atlas() -> ImageTexture:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var tones := [Color8(58, 82, 44), Color8(76, 104, 52), Color8(98, 124, 62)]
	for cell in 16:
		var cx := (cell % 4) * 16 + 8
		var cy := (cell / 4) * 16 + 8
		for k in 26:
			var a := rng.randf() * TAU
			var r := sqrt(rng.randf()) * 6.0
			var px := int(cx + cos(a) * r)
			var py := int(cy + sin(a) * r * 0.85)
			var tone: Color = tones[clampi(int(2.0 - (py - cy + 6) / 6.0 + rng.randf() * 0.8), 0, 2)]
			for dx in [-1, 0, 1]:
				for dy in [0, 1]:
					if absi(dx) + dy > 1 and rng.randf() < 0.5:
						continue
					var x: int = clampi(px + dx, cx - 8, cx + 7)
					var y: int = clampi(py + dy, cy - 8, cy + 7)
					img.set_pixel(x, y, tone)
	return ImageTexture.create_from_image(img)


func _card_crown(centre: Vector3, radii: Vector3, count: int) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var cust := PackedFloat32Array()
	var cols := PackedColorArray()
	var idx := PackedInt32Array()
	for c in count:
		var d := Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1))
		while d.length() > 1.0:
			d = Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1))
		d = d.normalized() * pow(rng.randf(), 0.35)
		var anchor := centre + d * radii
		var nrm := (d * Vector3(1.0, 1.3, 1.0)).normalized()
		var cell := rng.randi() % 16
		var u0 := Vector2((cell % 4) * 16, (cell / 4) * 16) / 64.0
		var corners := [Vector2(-8, -8), Vector2(8, -8), Vector2(8, 8), Vector2(-8, 8)]
		var cuv := [Vector2(0, 16), Vector2(16, 16), Vector2(16, 0), Vector2(0, 0)]
		var base := verts.size()
		var flex := clampf(d.length(), 0.3, 1.0)
		for k in 4:
			verts.append(anchor + Vector3(corners[k].x, corners[k].y, 0) / 20.0)
			norms.append(nrm)
			uvs.append(u0 + cuv[k] / 64.0)
			uv2s.append(corners[k])
			cust.append_array([anchor.x, anchor.y, anchor.z, flex])
			cols.append(Color(1, 1, 1, lerpf(0.65, 1.0, d.y * 0.5 + 0.5)))
		idx.append_array([base, base + 2, base + 1, base, base + 3, base + 2])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_TEX_UV2] = uv2s
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_CUSTOM0] = cust
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr, [], {}, Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
	return m


func _process(dt: float) -> void:
	frame += 1
	env.tick(dt)
	if args.has("move"):
		target = Vector3(frame * 0.013, 0, frame * 0.007)
	pv.update_camera(dt)
	var shot_at := int(args.get("frames", "40"))
	if frame == shot_at:
		var img := pv.vp.get_texture().get_image()
		img.save_png(args.get("shot", "/tmp/w3_shot.png"))
		var win := get_viewport().get_texture().get_image()
		win.save_png(String(args.get("shot", "/tmp/w3_shot.png")).replace(".png", "_win.png"))
		print("SHOT ", img.get_size())
		get_tree().quit()
