class_name HeadTurnModifier
extends SkeletonModifier3D
## Readability (docs/knowledge/24-3d-characters.md §6): in profile and three-quarter-back views her
## head turns a little toward the camera, `bias` times the sine of the angle between her facing and the
## camera's direction (south). In profile the face otherwise shrinks to a one-pixel sliver behind the
## hair; with the turn she shows an eye and seems to glance at the player. Nothing when she faces the
## camera or directly away. Runs first among her modifiers (the hat and the springs follow the head).

var bone := -1
var bias := deg_to_rad(20.0)


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or bone < 0 or bias == 0.0:
		return
	var to_world := sk.global_transform.basis.orthonormalized()
	var pose := sk.get_bone_global_pose(bone)
	var hb := (to_world * pose.basis).orthonormalized()
	var f := Vector3(hb.z.x, 0.0, hb.z.z)
	if f.length() < 1e-4:
		return
	f = f.normalized()
	# the signed angle (about +y) from her facing to the camera's direction (+z, south)
	var d := atan2(f.cross(Vector3.BACK).y, f.dot(Vector3.BACK))
	var turned := (Basis(Vector3.UP, bias * sin(d)) * hb).orthonormalized()
	pose.basis = (to_world.inverse() * turned).orthonormalized()
	sk.set_bone_global_pose(bone, pose)
