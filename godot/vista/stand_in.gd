class_name VistaStandIn
extends Node2D
## PREVIEW ONLY: the stand-in for her sprite that the JS vista preview drew (src/vista-test.js
## standIn: seen from behind, wide hat, long dark hair, a white haori), so previews and checks frame
## like the frames the user saw. The game puts her real sprite in Vista.figure_slot() instead.

var pose := "sit"


func set_pose(p: String) -> void:
	if p != pose:
		pose = p
		queue_redraw()


func _draw() -> void:
	var hat := Color8(0x2b, 0x31, 0x57)
	var band := Color8(0x8c, 0x2a, 0x33)
	var hair := Color8(0x1a, 0x14, 0x24)
	var haori := Color8(0xc9, 0xc4, 0xb8)
	var haori_s := Color8(0x8f, 0x8c, 0x86)
	var ink := Color8(0x0d, 0x0d, 0x14)
	var r := func(c: Color, x: int, y: int, w: int, h: int) -> void: draw_rect(Rect2(x, y, w, h), c)
	if pose != "sit":
		r.call(ink, -3, -4, 2, 4)
		r.call(ink, 1, -4, 2, 4)
		r.call(haori, -5, -20, 10, 16)
		r.call(haori_s, 2, -20, 3, 16)
		r.call(hair, -3, -26, 6, 18)
		r.call(haori, -8, -20, 3, 9)
		r.call(haori, 5, -20, 3, 9)
		r.call(hat, -10, -30, 20, 3)
		r.call(hat, -6, -33, 12, 3)
		r.call(band, -6, -30, 12, 1)
	else:
		r.call(haori, -5, -13, 10, 11)
		r.call(haori_s, 2, -13, 3, 11)
		r.call(hair, -3, -18, 6, 14)
		r.call(ink, -6, -2, 12, 2)
		r.call(hat, -10, -22, 20, 3)
		r.call(hat, -6, -25, 12, 3)
		r.call(band, -6, -22, 12, 1)
