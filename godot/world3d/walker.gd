class_name W3Walker
extends Node3D
## A character walking on the 3D terrain (the art sample): her sprite (CharSprite3D) with the
## 8-view idle / walk / run cycles from actors/characters.json, movement on the heightfield with the
## walkable mask and round footprints (trees, buildings), and a contact shadow handled by the
## renderer (the sprite casts its own silhouette). Walk and run play at the speed she really moves,
## like the 2D core's Actor (actors/actor.gd), so the feet never skate.

const VIEWS8 := ["front", "front_right", "right", "back_right", "back", "back_left", "left", "front_left"]
const VIEWS4 := ["front", "right", "back", "left"]
const SPEED_SCALE := Vector2(0.55, 1.7)
const RUN_HYST := 0.85

var terrain: Terrain3D
var sprite := CharSprite3D.new()
var char_id := "tsuzumi"
var sheet_name := "load"
var meta := {}                     # characters.json entry
var sheet := {}                    # meta["sheets"][sheet_name]
var pos := Vector3.ZERO            # feet, world
var vel := Vector3.ZERO
var facing := 0                    # index into VIEWS8
var speed := 0.0                   # measured ground speed, m/s (smoothed)
var base_speed := 2.4               # carrying a load she walks (the sprite cycle's own pace)
var sprite_dir := "res://world3d/sprites"
var anim := "idle"
var anim_t := 0.0
var running := false
var radius := 0.32
var blockers: Array = []           # [Vector3 centre (y unused), radius]
# round 4 (item 7): the 3D model (Character3D, docs/knowledge/24) when the characters are in the
# tree and this character has one; then the sprite is not used. The model stands in the world
# beside the walker; the walker moves it (its position is her feet) and hands it her ground speed.
const MODELS := {"tsuzumi": "kasasagi"}
var model: Node3D


func setup(t: Terrain3D, id: String, sheet_key: String, chars: Dictionary) -> void:
	terrain = t
	char_id = id
	sheet_name = sheet_key
	meta = chars[id]
	sheet = meta["sheets"][sheet_key]
	var fsize := Vector2i(meta["frame"][0], meta["frame"][1])
	var piv := Vector2i(meta["pivot"][0], meta["pivot"][1])
	var file: String = sheet["file"]
	var mid: String = MODELS.get(id, "")
	if mid != "" and ResourceLoader.exists(PixelView3D.CHAR3D) and FileAccess.file_exists("res://characters/%s/rig.json" % mid) \
			and not OS.get_cmdline_user_args().has("--sprites"):
		model = (load(PixelView3D.CHAR3D) as GDScript).new()
		model.name = "Model_" + mid
		get_parent().add_child(model)
		model.call("setup", mid)
		return
	sprite.setup(CharSprite3D.pixel_texture("%s/%s.png" % [sprite_dir, file]),
		CharSprite3D.pixel_texture("%s/%s_n.png" % [sprite_dir, file]), fsize, piv, float(chars.get("_sprite_pitch_deg", 39.33)))
	add_child(sprite)


func place(p: Vector3) -> void:
	pos = Vector3(p.x, terrain.height_at(p.x, p.z), p.z)
	_apply()


## dir: wanted movement in world x/z (length 0..1). Returns the distance actually moved.
func step(dt: float, dir: Vector2) -> float:
	var want := Vector3(dir.x, 0, dir.y) * base_speed * minf(1.0, dir.length())
	# slower uphill, a touch quicker downhill
	if want.length() > 0.01:
		var ahead := pos + want.normalized() * 0.6
		var rise := terrain.height_at(ahead.x, ahead.z) - pos.y
		want *= clampf(1.0 - rise / 0.6 * 0.45, 0.6, 1.1)
	vel = vel.lerp(want, clampf(dt * 14.0, 0.0, 1.0))
	var moved := _try_move(vel * dt)
	var inst := moved / maxf(dt, 1e-4)
	speed = lerpf(speed, inst, clampf(dt * 12.0, 0.0, 1.0)) if moved > 0.0005 else lerpf(speed, 0.0, clampf(dt * 20.0, 0.0, 1.0))
	if dir.length() > 0.2:
		facing = _view_of(dir)
	_animate(dt)
	_apply()
	if model:
		# her ground speed as she really moved (the gait locks to it: the feet never skate)
		var gv := Vector3(vel.x, 0.0, vel.z)
		if moved < 0.0005:
			gv = Vector3.ZERO
		model.call("drive", gv, dt)
	return moved


func _try_move(d: Vector3) -> float:
	if d.length() < 1e-5:
		return 0.0
	var start := pos
	for attempt in [d, Vector3(d.x, 0, 0), Vector3(0, 0, d.z)]:
		var np: Vector3 = pos + attempt
		if _free(np):
			pos = Vector3(np.x, terrain.height_at(np.x, np.z), np.z)
			break
	return Vector2(pos.x - start.x, pos.z - start.z).length()


func _free(p: Vector3) -> bool:
	if not terrain.walkable(p.x, p.z):
		return false
	for b in blockers:
		var c: Vector3 = b[0]
		var r: float = b[1]
		if Vector2(p.x - c.x, p.z - c.z).length() < r + radius:
			return false
	return true


func _view_of(dir: Vector2) -> int:
	# screen angle: 0 = toward the camera (south, +z), counter-clockwise as the views run
	var a := atan2(dir.x, dir.y)            # 0 south, +90 east
	return wrapi(roundi(a / (PI / 4.0)), 0, 8)


func _animate(dt: float) -> void:
	var runs: Dictionary = meta["anims"].get("run", {})
	var from := float(runs.get("from", 99.0))
	running = speed >= from * (RUN_HYST if running else 1.0)
	var want := "idle"
	if speed > 0.25:
		want = "run" if running else "walk"
	if want != anim:
		anim = want
		anim_t = 0.0
	var am: Dictionary = meta["anims"][anim]
	var fps := float(am.get("fps", 8))
	var nominal := float(am.get("speed", 0.0))
	var sc := 1.0
	if (anim == "walk" or anim == "run") and nominal > 0.0:
		sc = clampf(speed / nominal, SPEED_SCALE.x, SPEED_SCALE.y)
	anim_t += dt * fps * sc


func _apply() -> void:
	position = pos
	if model:
		model.position = pos
		model.set("ground_y", pos.y)
		return
	var views: Dictionary = sheet["anims"].get(anim, sheet["anims"]["idle"])
	var view: String = VIEWS8[facing]
	var flip := false
	if not views.has(view):
		# 4-view anims: nearest of front/right/back/left
		view = VIEWS4[int(roundf(facing / 2.0)) % 4]
	var info: Dictionary = views.get(view, views.values()[0])
	var n := int(info["frames"])
	var f := int(floor(anim_t)) % maxi(1, n)
	var head := Vector2(0.5, -35.0)
	var anchors: Array = info.get("anchors", [])
	if f < anchors.size() and (anchors[f] as Dictionary).has("head"):
		head = Vector2(anchors[f]["head"][0], anchors[f]["head"][1])
	sprite.show_frame(int(info.get("col", 0)) + f, int(info["row"]), flip, head)


## The colour of her silhouette where something covers her (sprite or model).
func set_xray_colour(c: Color) -> void:
	if model:
		model.call("set_xray_colour", c)
	else:
		sprite.set_xray_colour(c)


## Her chest, for the camera and the canopy cut-away.
func chest() -> Vector3:
	if model:
		return model.call("chest")
	return pos + Vector3(0, 1.0, -0.5)
