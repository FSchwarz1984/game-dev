class_name CharacterLibrary
## Sprite frames for the characters, built once from actors/characters.json (the layout of the
## sheets in art/sprites/, written by tools/art/sprite3d/build.py and copied by
## tools/godot/sync_assets.py; docs/knowledge/20-sprites.md §7). Each frame is an AtlasTexture over a
## CanvasTexture (albedo + normal map), so 2D lights shade the characters per pixel. Frame i of a
## strip is the cell (col + i, row); idle / walk / run strips always start at column 0.
## Animation names in the SpriteFrames: "<anim>_<view>". Views: the eight directions front,
## front_right, right, back_right, back, back_left, left, front_left (locomotion has all eight;
## scripted animations have the ones their scenes need). Left and right are drawn separately (the
## designs are asymmetric), never mirrored. The legacy "side" view (drawn facing right, mirrored for
## left) is still understood for old layouts.

const LAYOUT_PATH := "res://actors/characters.json"
## For a wanted view, the views to try in order. Diagonals fall back to their side view first
## (the walk reads by its legs, which the side view shows), then to front/back.
const VIEW_FALLBACK := {
	"front": ["front", "front_right", "front_left", "side", "right", "left", "back"],
	"back": ["back", "back_right", "back_left", "side", "right", "left", "front"],
	"right": ["right", "side", "front_right", "back_right", "front", "back", "left"],
	"left": ["left", "side", "front_left", "back_left", "front", "back", "right"],
	"front_right": ["front_right", "right", "front", "side", "back_right", "front_left", "back"],
	"front_left": ["front_left", "left", "front", "side", "back_left", "front_right", "back"],
	"back_right": ["back_right", "right", "back", "side", "front_right", "back_left", "front"],
	"back_left": ["back_left", "left", "back", "side", "front_left", "back_right", "front"],
	"side": ["side", "right", "left", "front", "back"],
}
const LEFTISH := ["left", "front_left", "back_left"]
const RIGHTISH := ["right", "front_right", "back_right", "side"]

static var _layout: Dictionary = {}
static var _frames: Dictionary = {}   # "<char>/<sheet>" -> SpriteFrames
static var _anchors: Dictionary = {}  # "<char>/<sheet>/<anim>_<view>" -> Array of anchor dicts


## Drops the caches (at exit, so no resource outlives the engine).
static func clear() -> void:
	_frames.clear()
	_anchors.clear()
	_layout.clear()


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
			# a strip starts at its column: 0 for idle / walk / run; other strips share rows
			var col := int(entry.get("col", 0))
			for i in int(entry["frames"]):
				var at := AtlasTexture.new()
				at.atlas = tex
				at.region = Rect2((col + i) * fs.x, int(entry["row"]) * fs.y, fs.x, fs.y)
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


## True when showing `got` for a wanted view `want` needs a horizontal flip: only for the legacy
## "side" view (drawn facing right) or a right-facing fallback, and only when the animation allows
## mirroring (the new layouts draw both sides and say mirrorLeft = false).
static func mirrored(id: String, anim: String, want: String, got: String) -> bool:
	if not LEFTISH.has(want) or not RIGHTISH.has(got):
		return false
	return bool(anim_meta(id, anim).get("mirrorLeft", got == "side"))


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
