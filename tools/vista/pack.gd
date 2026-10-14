extends SceneTree
## Packs the raw vista bake (tools/vista/bake.mjs) into Godot resources:
##   godot --headless --path godot -s tools/vista/pack.gd -- --in=<raw dir> --out=<dir> [--shots=a,b]
## Every image of <shot>.json becomes <out>/<shot>_<name>.res (an Image, zstd-compressed) and the
## lists go to <out>/<shot>.json with the image paths. Formats: rgba8 -> RGBA8, rg8 -> RG8 (two bytes
## per pixel, e.g. 16-bit fixed point), rg16 -> raw bytes in an R8 image 4096 wide (read on the CPU).


func _initialize() -> void:
	var src := ""
	var dst := ""
	var shots := PackedStringArray()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--in="):
			src = a.substr(5)
		elif a.begins_with("--out="):
			dst = a.substr(6)
		elif a.begins_with("--shots="):
			shots = a.substr(8).split(",")
	var ok := src != "" and dst != ""
	if ok:
		DirAccess.make_dir_recursive_absolute(dst)
		for shot in shots:
			ok = _pack(src, dst, shot) and ok
	quit(0 if ok else 1)


func _pack(src: String, dst: String, shot: String) -> bool:
	var j := JSON.new()
	if j.parse(FileAccess.get_file_as_string(src.path_join(shot + ".json"))) != OK:
		push_error("pack: cannot read %s.json" % shot)
		return false
	var d: Dictionary = j.data
	var files: Dictionary = d["imageFiles"]
	var out_files := {}
	var total := 0
	for name in files:
		var info: Dictionary = files[name]
		var bytes := FileAccess.get_file_as_bytes(src.path_join(String(info["file"])))
		var w := int(info["w"])
		var h := int(info["h"])
		var img: Image
		match String(info["fmt"]):
			"rgba8":
				img = Image.create_from_data(w, h, false, Image.FORMAT_RGBA8, bytes)
			"rg8":
				img = Image.create_from_data(w, h, false, Image.FORMAT_RG8, bytes)
			"rg16":
				var n := bytes.size()
				var rows := maxi(1, ceili(n / 4096.0))
				var padded := bytes.duplicate()
				padded.resize(rows * 4096)
				img = Image.create_from_data(4096, rows, false, Image.FORMAT_R8, padded)
				info["bytes"] = n
			_:
				push_error("pack: unknown format %s" % info["fmt"])
				return false
		var path := dst.path_join("%s_%s.res" % [shot, name])
		var err := ResourceSaver.save(img, path, ResourceSaver.FLAG_COMPRESS)
		if err != OK:
			push_error("pack: cannot save %s (%d)" % [path, err])
			return false
		total += FileAccess.get_file_as_bytes(path).size()
		info["res"] = "%s_%s.res" % [shot, name]
		info.erase("file")
		out_files[name] = info
	d["imageFiles"] = out_files
	var f := FileAccess.open(dst.path_join(shot + ".json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(d))
	f.close()
	print("pack: %s -> %d images, %.1f KB" % [shot, out_files.size(), total / 1024.0])
	return true
