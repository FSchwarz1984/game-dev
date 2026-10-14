class_name CharacterLibrary
## Sprite frames for the characters, built once from actors/characters.json (the layout of the
## sheets in art/sprites/, converted from src/art/characters.data.js by tools/godot/sync_assets.py).
## The sheets are PLACEHOLDERS until the new sprites arrive; a new set only needs a new JSON in the
## same shape. Each frame is an AtlasTexture over a CanvasTexture (albedo + normal map), so 2D
## lights shade the characters per pixel.
## Animation names in the SpriteFrames: "<anim>_<view>", view = front | side | back. Side frames are
## drawn facing right; facing left mirrors them (flip_h) when the animation allows it.

const LAYOUT_PATH := "res://actors/characters.json"
const VIEW_FALLBACK := {
	"front": ["front", "side", "back"],
	"back": ["back", "side", "front"],
	"side": ["side", "front", "back"],
}

static var _layout: Dictionary = {}
static var _frames: Dictionary = {}   # "<char>/<sheet>" -> SpriteFrames
static var _anchors: Dictionary = {}  # "<char>/<sheet>/<anim>_<view>" -> Array of anchor dicts


static func layout() -> Dictionary:
	if _layout.is_empty():
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT_PATH))
		_layout = parsed if parsed is Dictionary else {}
	return _layout


static func character(id: String) -> Dictionary:
	return layout().get(id, {})


static func sheets(id: String) -> Array:
	return character(id).get("sheets", {}).keys()


## Frame cell size and the foot pivot inside it (native px).
static func frame_size(id: String) -> Vector2i:
	var f: Array = character(id).get("frame", [32, 32])
	return Vector2i(f[0], f[1])


static func pivot(id: String) -> Vector2i:
	var p: Array = character(id).get("pivot", [16, 30])
	return Vector2i(p[0], p[1])


static func frames(id: String, sheet: String) -> SpriteFrames:
	var key := id + "/" + sheet
	if _frames.has(key):
		return _frames[key]
	var c := character(id)
	var sd: Dictionary = c.get("sheets", {}).get(sheet, {})
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	if sd.is_empty():
		_frames[key] = sf
		return sf
	var albedo := load("res://art/sprites/%s.png" % sd["file"]) as Texture2D
	var normal := load("res://art/sprites/%s_n.png" % sd["file"]) as Texture2D
	var tex := CanvasTexture.new()
	tex.diffuse_texture = albedo
	tex.normal_texture = normal
	tex.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var fs := frame_size(id)
	var metas: Dictionary = c.get("anims", {})
	for anim in sd["anims"]:
		var meta: Dictionary = metas.get(anim, {"fps": 8, "loop": true})
		for view in sd["anims"][anim]:
			var entry: Dictionary = sd["anims"][anim][view]
			var name := "%s_%s" % [anim, view]
			sf.add_animation(name)
			sf.set_animation_speed(name, float(meta.get("fps", 8)))
			sf.set_animation_loop(name, bool(meta.get("loop", true)))
			for i in int(entry["frames"]):
				var at := AtlasTexture.new()
				at.atlas = tex
				at.region = Rect2(i * fs.x, int(entry["row"]) * fs.y, fs.x, fs.y)
				sf.add_frame(name, at)
			_anchors[key + "/" + name] = entry.get("anchors", [])
	_frames[key] = sf
	return sf


## The view an animation actually has for a wanted view ("" when the animation does not exist).
static func view_for(id: String, sheet: String, anim: String, want: String) -> String:
	var sd: Dictionary = character(id).get("sheets", {}).get(sheet, {})
	var views: Dictionary = sd.get("anims", {}).get(anim, {})
	for v in VIEW_FALLBACK.get(want, ["front"]):
		if views.has(v):
			return v
	return ""


static func has_anim(id: String, sheet: String, anim: String) -> bool:
	return character(id).get("sheets", {}).get(sheet, {}).get("anims", {}).has(anim)


static func anim_meta(id: String, anim: String) -> Dictionary:
	return character(id).get("anims", {}).get(anim, {})


## Seconds one cycle of an animation lasts in a view (0 when it does not exist).
static func duration(id: String, sheet: String, anim: String, view: String) -> float:
	var v := view_for(id, sheet, anim, view)
	if v == "":
		return 0.0
	var n := int(character(id)["sheets"][sheet]["anims"][anim][v]["frames"])
	return n / maxf(0.1, float(anim_meta(id, anim).get("fps", 8)))


static func anchors(id: String, sheet: String, name: String) -> Array:
	return _anchors.get(id + "/" + sheet + "/" + name, [])
