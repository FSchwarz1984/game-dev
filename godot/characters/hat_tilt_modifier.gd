class_name HatTiltModifier
extends SkeletonModifier3D
## The sugegasa convention (docs/knowledge/24-3d-characters.md §hat): a wide hat seen from the game's
## camera would cover her whole face. As the user's portraits show it (worn tipped back), the hat
## bone is turned every frame so the hat's top leans away from the camera by `tilt` while she faces
## the camera (the front brim lifts, the navy underside frames her face), easing to `tilt_away` as
## she turns her back (seen from behind, the top with its red band shows), and leans toward the
## screen's right by `roll` while she faces the camera or away from it (the art's asymmetric, jaunty
## set: the navy on one side, the top and its band on the other; none in profile). The hat still turns with her head (its red band shows where she looks), tips
## back further when she looks up (`pitch_share` of the head's pitch), and keeps the animation's own
## hat moves (a hand tipping the brim) on top.

var bone := -1
var head_bone := -1
var tilt := deg_to_rad(52.0)
var tilt_away := deg_to_rad(24.0)
var roll := deg_to_rad(12.0)
var pitch_share := 0.5
var last_t := 0.0                 # (checks) the tilt and the head's facing of the last frame
var last_fwd := Vector3.ZERO
var last_look_up := 0.0


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or bone < 0:
		return
	var pose := sk.get_bone_global_pose(bone)
	var to_world := sk.global_transform.basis.orthonormalized()
	# the head's facing on the ground plane, and how far it looks up (+) or down (-)
	var head_b := (to_world * sk.get_bone_global_pose(head_bone).basis).orthonormalized() if head_bone >= 0 else to_world
	var hf := head_b.z
	var look_up := asin(clampf(hf.y, -1.0, 1.0))
	var fwd := Vector3(hf.x, 0.0, hf.z)
	if fwd.length() < 1e-4:
		fwd = Vector3(0, 0, 1)
	fwd = fwd.normalized()
	# facing the camera (south, +z) 1 .. facing away 0
	var face_cam := 0.5 + 0.5 * fwd.z
	# looking up tips the hat further back while she faces the camera; facing away it keeps its tilt
	# (tipped toward the camera it would cover her back as a full disc)
	var t := clampf(lerpf(tilt_away, tilt, face_cam) + look_up * pitch_share * maxf(fwd.z, 0.0),
			deg_to_rad(8.0), deg_to_rad(68.0))
	last_t = t
	last_fwd = fwd
	last_look_up = look_up
	# the hat's up leans north (away from the camera, which always looks north), then toward the
	# screen's right, but only across her facing: the roll's direction is east with her own forward
	# taken out, so it fades away in profile. (East as such tipped the brim down over her face when
	# she faced east; her own left tipped the top over her face when she faced west.)
	var side := Vector3.RIGHT - fwd * Vector3.RIGHT.dot(fwd)
	var k := side.length()
	var rr := roll * k
	var up := Vector3(0.0, cos(t), -sin(t)) * cos(rr)
	if k > 1e-4:
		up += side / k * sin(rr)
	up = up.normalized()
	var z := (fwd - up * fwd.dot(up)).normalized()
	var x := up.cross(z).normalized()
	var want := Basis(x, up, z)
	# the animation's own move of the hat (its local pose against its rest) on top
	var delta := sk.get_bone_rest(bone).basis.orthonormalized().inverse() * sk.get_bone_pose(bone).basis.orthonormalized()
	var w := want * delta
	sk.set_bone_global_pose(bone, Transform3D((to_world.inverse() * w).orthonormalized(), pose.origin))
