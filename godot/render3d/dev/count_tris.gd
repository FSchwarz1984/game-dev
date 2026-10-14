extends SceneTree
## Dev tool: triangles per scene for the asset catalog (perf notes).
##   godot --headless --path godot -s res://render3d/dev/count_tris.gd -- [name ...]

func _count(n: Node, acc: Dictionary) -> void:
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var m := (n as MeshInstance3D).mesh
		var t := 0
		for si in m.get_surface_count():
			var arr := m.surface_get_arrays(si)
			var idx = arr[Mesh.ARRAY_INDEX]
			if idx != null and idx.size() > 0:
				t += idx.size() / 3
			else:
				t += (arr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() / 3
		acc["tris"] = int(acc.get("tris", 0)) + t
		acc["meshes"] = int(acc.get("meshes", 0)) + 1
	if n is MultiMeshInstance3D and (n as MultiMeshInstance3D).multimesh:
		var mm := (n as MultiMeshInstance3D).multimesh
		acc["mm_instances"] = int(acc.get("mm_instances", 0)) + mm.instance_count
	for c in n.get_children():
		_count(c, acc)


func _init() -> void:
	var f := FileAccess.open("res://world3d/assets/catalog.json", FileAccess.READ)
	var cat: Dictionary = JSON.parse_string(f.get_as_text())["assets"]
	var only := OS.get_cmdline_user_args()
	var rows := []
	for name in cat:
		if not only.is_empty() and not (name in only):
			continue
		var ps: PackedScene = load(String(cat[name]["scene"]))
		if ps == null:
			continue
		var inst := ps.instantiate()
		var acc := {}
		_count(inst, acc)
		rows.append([name, int(acc.get("tris", 0)), int(acc.get("meshes", 0))])
		inst.free()
	rows.sort_custom(func(a, b): return a[1] > b[1])
	for r in rows:
		print("TRIS %-22s %8d tris %3d meshes" % r)
	quit()
