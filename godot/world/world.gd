class_name World
extends Node2D
## The world at runtime, inside the stage's world viewport. P1 runs one region; regions are loaded by
## id under Regions/<id> (the streaming skeleton: P3 loads neighbours ahead of her, no loading
## screens). Owns the region art, the y-sorted things (entity views and actors), Saji's follow,
## and implements the director's stage adapter: actor(id), shot(name, opts), cam(x, z, opts),
## follow(opts), tod(hour).

var stage: PixelStage
var field: Field
var region: RegionData
var regions_node: Node2D
var things: Node2D
var shade: CanvasModulate
var views: Dictionary = {}      # entity id -> EntityView
var actors: Dictionary = {}     # actor id -> Actor
var companion: Companion
var companion_entity: FieldEntity
var her: Actor


func setup(p_stage: PixelStage, p_field: Field) -> void:
	name = "World"
	stage = p_stage
	field = p_field
	regions_node = Node2D.new()
	regions_node.name = "Regions"
	regions_node.z_index = -10
	add_child(regions_node)
	things = Node2D.new()
	things.name = "Things"
	things.y_sort_enabled = true
	add_child(things)
	shade = CanvasModulate.new()
	shade.color = Color.WHITE
	add_child(shade)


## Loads a region's ground (logic and art) and its things into the field.
func load_region(id: String) -> RegionData:
	var dir := "res://world/regions/" + id
	region = RegionData.load_dir(dir)
	# the field reads this region's ground before anything is placed on it (things take their height)
	field.ground = region.ground_kind
	field.height = region.height_at
	var node := Node2D.new()
	node.name = id
	regions_node.add_child(node)
	var art := Sprite2D.new()
	art.name = "Ground"
	art.centered = false
	art.texture = load(dir.path_join(String(region.def.get("art", "ground.png")))) as Texture2D
	var off: Array = region.def.get("art_offset_px", [0, 0])
	art.position = Vector2(off[0], off[1])
	node.add_child(art)
	if art.texture != null:
		stage.cam.bounds = Rect2(art.position, art.texture.get_size())
	for def in region.def.get("entities", []):
		var e := field.add(def)
		var v := EntityView.new()
		v.setup(e, def.get("view", {}))
		things.add_child(v)
		views[e.id] = v
	for z in region.def.get("zones", []):
		var zd: Dictionary = z.duplicate()
		if zd.has("wind"):
			zd["wind"] = Vector2(zd["wind"][0], zd["wind"][1])
		field.zone(zd)
	return region


func add_actor(id: String, body = null) -> Actor:
	var a := Actor.new(id, body)
	things.add_child(a)
	actors[id] = a
	a.step.connect(func(_foot: int) -> void: _footstep(a))
	return a


## Saji: an actor that follows her, and a field entity at the same spot (so she can be talked to).
func add_companion(id: String, x: float, z: float, ctx: Dictionary) -> Actor:
	companion = Companion.new(x, z)
	var a := add_actor(id)
	a.x = x
	a.z = z
	companion_entity = field.add({"id": id, "kind": "npc", "name": String(StoryUI.CAST[id]["name"]), "x": x, "z": z,
		"r": 0.3, "priority": 1, "ctx": ctx, "data": {"showQualities": false, "promptH": 1.5}})
	return a


func _footstep(a: Actor) -> void:
	var mat := region.step_sound(a.x, a.z) if region != null else "grass"
	if a == her:
		Audio.footstep(mat, field.player.body.step_sound())
	else:
		Audio.footstep(mat, {"volume": 0.45, "pitch": 1.25})


func _companion_blocker(x: float, z: float, fx: float, fz: float) -> Dictionary:
	var g := region.ground_kind(x, z, fx, fz) if region != null else Field.Ground.GROUND
	return {"wall": true} if g != Field.Ground.GROUND else {}


func tick(dt: float) -> void:
	var P := field.player
	if companion != null:
		var a: Actor = actors[companion_entity.id]
		if a.state == Actor.State.LOCOMOTION:
			companion.lead(P.x, P.z)
			companion.x = a.x
			companion.z = a.z
			companion.update(dt, P.x, P.z, her.face if her != null else "front", _companion_blocker)
			a.x = companion.x
			a.z = companion.z
		companion_entity.x = a.x
		companion_entity.z = a.z
		companion_entity.h = field.ground_height(a.x, a.z)
	for id in actors:
		var a: Actor = actors[id]
		a.h = field.ground_height(a.x, a.z)
		a.tick(dt)
	for id in views:
		var v: EntityView = views[id]
		v.targeted = field.target == v.e
		v.tick(dt)


## The thing under a tap (logical screen px), by the drawn shapes of things and actors.
func pick_at(screen: Vector2) -> FieldEntity:
	var w := stage.screen_to_world(screen)
	var best: FieldEntity = null
	var best_d := INF
	for e in field.entities:
		if e.hidden or not e.targetable:
			continue
		var r := Rect2()
		if views.has(e.id):
			r = (views[e.id] as EntityView).hit_rect_world()
		else:
			var foot := Proj.to_px(e.x, e.z, e.h)
			r = Rect2(foot.x - 10, foot.y - 32, 20, 34)
		if r.grow(6.0).has_point(w):
			var d := r.get_center().distance_to(w)
			if d < best_d:
				best_d = d
				best = e
	return best


func her_focus() -> Vector2:
	var P := field.player
	return Proj.to_px(P.x, P.z, P.h + 1.0)


# ------------------------------------------------------------------ the director's stage

func actor(id: String) -> Actor:
	return actors.get(id)


func shot(name: String, opts: Dictionary = {}) -> void:
	var s := region.shot(name) if region != null else {}
	if s.is_empty():
		push_warning("World.shot: no shot '%s'" % name)
		return
	cam(float(s["x"]), float(s["z"]), opts)


func cam(x: float, z: float, opts: Dictionary = {}) -> void:
	var y := float(opts.get("y", field.ground_height(x, z)))
	stage.cam.point(Proj.to_px(x, z, y), opts)


func follow(opts: Dictionary = {}) -> void:
	stage.cam.follow(her_focus, opts)


## Time of day as a canvas tint (placeholder until the lighting of P2).
func tod(hour: float) -> void:
	var day := clampf(sin((hour - 6.0) / 12.0 * PI), 0.0, 1.0)
	var warm := clampf(1.0 - absf(hour - 18.0) / 2.0, 0.0, 1.0)
	var c := Color(0.42, 0.45, 0.62).lerp(Color.WHITE, day)
	shade.color = c.lerp(Color(1.0, 0.82, 0.62), warm * 0.5)
