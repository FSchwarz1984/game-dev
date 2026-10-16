class_name HeadSnapModifier
extends SkeletonModifier3D
## Moves the head (and with it the face, the hair on it and the hat) in whole native pixels on
## screen, like a pixel-art sprite's head (docs/knowledge/24-3d-characters.md §pixels). Without it a
## breath or a step moves the head by fractions of a pixel: the head's outline and the face's
## pixel stamps would round at different moments and the eyes would swim against the face. The
## head bone is shifted (never more than half a pixel, in the screen plane, depth unchanged) so the
## rendered screen position of its origin is always a whole pixel. Runs first among her modifiers.

var bone := -1
var character: Node3D       # Character3D: its view numbers, anchor, ground
var offset := Vector2.ZERO  # the head's origin lands this far into its pixel (0.5: the pixel's centre)


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or bone < 0 or character == null:
		return
	var v: Vector4 = Character3D.view_numbers
	var pose := sk.get_bone_global_pose(bone)
	var wp: Vector3 = sk.global_transform * pose.origin
	var s: Vector2 = character.call("screen_rendered", wp)
	var d: Vector2 = (s - offset).round() + offset - s
	# a screen shift (d px) of an upright point: x by d.x / ppm, height by d.y / ppm (the lean makes a
	# vertical metre exactly ppm pixels), no change in depth along the ground
	var w := Vector3(d.x / v.x, d.y / v.x, 0.0)
	var local := sk.global_transform.basis.inverse() * w
	pose.origin += local
	sk.set_bone_global_pose(bone, pose)
