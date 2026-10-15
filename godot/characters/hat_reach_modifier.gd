class_name HatReachModifier
extends SkeletonModifier3D
## 摸笠沿, her signature gesture (the art A_07, A_08; docs/knowledge/24-3d-characters.md §7): the right
## hand on the hat's brim. The brim is half a metre from the hat's axis and the hat's tilt is the
## game's own (camera-relative, hat_tilt_modifier.gd), so a clip alone could never put the hand on it:
## the clip (idle_hat) lifts the arm, and this modifier, run after the hat's tilt, takes the point of
## the brim nearest to where her hand goes, pulls the hat down on that side as far as it must for a
## chibi arm to reach it (she tips it by the brim, as in the art), and turns the arm onto it (two-bone
## IK, the elbow out to her side, the hand along the brim). `weight` (0..1) comes from the character
## (rig.json clips.idle_hat.reach: the frames where the reach fades in and out).

var weight := 0.0
var hat := -1
var upper := -1
var fore := -1
var hand := -1
var brim_y := -0.124          # the brim's plane below the hat bone's head (hat bone space, m)
var brim_r := 0.50            # the brim's radius
var hand_len := 0.062
var grip_in := 0.05           # the hand holds the brim this far in from its edge
var max_tip := deg_to_rad(42.0)
var side := -1.0              # her right: -x in her body (skeleton) space
var last_tip := 0.0           # (checks) the hat's extra tip and the hand's miss of the last frame
var last_miss := 0.0


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or weight <= 0.001 or hat < 0 or upper < 0 or fore < 0 or hand < 0:
		return
	var w := clampf(weight, 0.0, 1.0)
	var hp := sk.get_bone_global_pose(hat)
	var hb := hp.basis.orthonormalized()
	var pivot := hp.origin
	var s := sk.get_bone_global_pose(upper).origin
	var l1 := sk.get_bone_rest(fore).origin.length()
	var l2 := sk.get_bone_rest(hand).origin.length()
	# the wrist stops short of the grip by most of the hand
	var reach := (l1 + l2) * 0.985 + hand_len * 0.7
	# the brim point nearest to where a raised hand goes (out to her side, up beside the head)
	var axis := hb.y.normalized()
	var c := pivot + axis * brim_y
	var q := s + Vector3(side * 0.24, 0.30, 0.04)
	var qp := q - axis * axis.dot(q - c)
	var d := qp - c
	if d.length() < 1e-4:
		d = Vector3(side, 0.0, 0.0)
	var grip := c + d.normalized() * (brim_r - grip_in)
	# out of reach: tip the hat about its seat toward the shoulder, just enough
	var tip := 0.0
	var pg := grip - pivot
	var ps := s - pivot
	if s.distance_to(grip) > reach:
		var rg := pg.length()
		var ds := ps.length()
		var cos_t := clampf((rg * rg + ds * ds - reach * reach) / (2.0 * rg * ds), -1.0, 1.0)
		tip = clampf(pg.angle_to(ps) - acos(cos_t), 0.0, max_tip) * w
		var ax := pg.cross(ps)
		if tip > 0.0 and ax.length() > 1e-6:
			var rot := Basis(ax.normalized(), tip)
			hb = (rot * hb).orthonormalized()
			grip = pivot + rot * pg
			sk.set_bone_global_pose(hat, Transform3D(hb.scaled(hp.basis.get_scale()), pivot))
	last_tip = tip
	# the arm: two bones onto the wrist's target, the elbow out to her side and a little down
	var u := (grip - s).normalized()
	var wr := grip - u * hand_len * 0.7
	var dist := clampf(s.distance_to(wr), absf(l1 - l2) + 1e-3, (l1 + l2) * 0.999)
	var dh := (wr - s).normalized()
	wr = s + dh * dist
	var a := (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
	var h := sqrt(maxf(l1 * l1 - a * a, 0.0))
	var pole := Vector3(side * 0.85, -0.40, -0.30)
	var n := pole - dh * pole.dot(dh)
	n = n.normalized() if n.length() > 1e-5 else Vector3(side, 0.0, 0.0)
	var e := s + dh * a + n * h
	_aim(sk, upper, sk.get_bone_rest(fore).origin, e - s, w)
	_aim(sk, fore, sk.get_bone_rest(hand).origin, wr - e, w)
	# the hand along the brim toward the grip
	_aim(sk, hand, Vector3(0.0, 1.0, 0.0), grip - wr, w)
	last_miss = sk.get_bone_global_pose(hand).origin.distance_to(wr)


## Turns `bone` (in skeleton space) so its child's direction points along `want`, by `w`.
func _aim(sk: Skeleton3D, bone: int, child_local: Vector3, want: Vector3, w: float) -> void:
	if want.length() < 1e-6 or child_local.length() < 1e-6:
		return
	var g := sk.get_bone_global_pose(bone)
	var b := g.basis.orthonormalized()
	var cur := (b * child_local).normalized()
	var to := want.normalized()
	if cur.dot(to) > 0.99999:
		return
	var q := Quaternion(cur, to)
	var full := Quaternion(b)
	var turned := (q * full).normalized()
	var r := full.slerp(turned, w)
	sk.set_bone_global_pose(bone, Transform3D(Basis(r).scaled(g.basis.get_scale()), g.origin))
