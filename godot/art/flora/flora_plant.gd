class_name FloraPlant
extends Node2D
## The root of a plant scene built by tools/flora (docs/knowledge/18-vegetation.md).
##
## Placement, like every thing in World.things (knowledge/16 §3): the node position is the ground
## point of the plant's foot, Proj.sort_px(x, z); place(x, z, h) also lifts the drawing by the
## ground height without moving the sort points. The root is y_sort_enabled, so its children sort
## among the other things: Trunk at the foot, Crown at the crown's southern edge on the ground
## (metadata flora_crown_sort_px), so whoever stands under the crown is drawn before it. Shadow and
## ShadowContact (z_index -9) and Ground (roots, z_index -8) lie on the ground under every thing.
##
## Metadata: flora_species, flora_kind (tree / shrub / herb), flora_layout (tree: trunk + crown;
## body: one sorted body), flora_block (circles [x, z, r] in metres from the foot that stop her;
## empty for plants she walks through), flora_collision (the drawn footprint, px from the foot).

var ground_h := 0.0
var _base := {}


func place(x: float, z: float, h: float = 0.0) -> void:
	position = Proj.sort_px(x, z)
	lift(h)


## Lifts the drawing by h metres (ground height) and keeps the sort points on the ground.
func lift(h: float) -> void:
	ground_h = h
	var dy := -Proj.PPM * h
	for c in get_children():
		var s := c as Sprite2D
		if s == null:
			continue
		if not _base.has(s.name):
			_base[s.name] = [s.position, s.offset]
		var b: Array = _base[s.name]
		if s.z_index < 0:
			s.position = b[0] + Vector2(0, dy)    # lies on the ground under everything: no sorting
		else:
			s.offset = b[1] + Vector2(0, dy)      # sorted: the sort point stays, the picture rises


## How much of the sun reaches this plant (0..1): 1 in the open, less in a cliff's shadow (the
## terrain's sun mask at the foot). Per instance; the shadow it casts is not changed.
func set_sun_vis(v: float) -> void:
	for c in get_children():
		var s := c as Sprite2D
		if s != null and s.z_index >= -8 and s.material is ShaderMaterial:
			s.set_instance_shader_parameter("sun_vis", v)


## Circles that stop her, in metres relative to the foot: [Vector3(x, z, r), ...].
func block_circles() -> Array:
	var out: Array = []
	for c in get_meta("flora_block", []):
		out.append(Vector3(c[0], c[1], c[2]))
	return out


func _enter_tree() -> void:
	FloraField.add_plant(self)


func _exit_tree() -> void:
	FloraField.remove_plant(self)
