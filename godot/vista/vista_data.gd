class_name VistaData
extends RefCounted
## The baked vista data (tools/vista/bake.mjs -> godot/vista/data): <shot>.json with the lists and
## parameters, and its images as Image resources. Loaded once per shot and kept (textures are
## shared by every Vista); `dir` can point elsewhere (the 480x270 canonical bake used to check the
## renderer against the JS one).

const DEFAULT_DIR := "res://vista/data"

static var _cache := {}

var shot := ""
var meta: Dictionary = {}
var lists: Dictionary = {}
var images: Dictionary = {}     # name -> Image
var textures: Dictionary = {}   # name -> ImageTexture


static func load_shot(name: String, dir: String = DEFAULT_DIR) -> VistaData:
	var key := dir + "|" + name
	if _cache.has(key):
		return _cache[key]
	var path := dir.path_join(name + ".json")
	if not FileAccess.file_exists(path):
		push_error("vista: no baked data at %s (run node tools/vista/bake.mjs)" % path)
		return null
	var j := JSON.new()
	if j.parse(FileAccess.get_file_as_string(path)) != OK:
		push_error("vista: cannot parse %s" % path)
		return null
	var d := VistaData.new()
	d.shot = name
	var data: Dictionary = j.data
	d.meta = data.get("meta", {})
	for k in data:
		if k != "meta" and k != "imageFiles":
			d.lists[k] = data[k]
	var files: Dictionary = data.get("imageFiles", {})
	for n in files:
		var info: Dictionary = files[n]
		var res_path := dir.path_join(String(info["res"]))
		var img: Image = load(res_path) if res_path.begins_with("res://") else ResourceLoader.load(res_path)
		if img == null:
			push_error("vista: cannot load %s" % res_path)
			continue
		d.images[n] = img
		if String(info.get("fmt", "")) != "rg16":
			d.textures[n] = ImageTexture.create_from_image(img)
	_cache[key] = d
	return d


static func clear() -> void:
	_cache.clear()


func tex(name: String) -> Texture2D:
	return textures.get(name)


## Raw bytes of an "rg16" list image (u16 pairs, little endian).
func raw(name: String) -> PackedByteArray:
	var img: Image = images.get(name)
	return img.get_data() if img != null else PackedByteArray()
