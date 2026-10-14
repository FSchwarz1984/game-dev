class_name EntityView
extends Node2D
## PLACEHOLDER drawing of a field entity (internal test art; real props come with P2/P3).
## Shows what the rules need to show: the target outline (selection in the world, not in a corner),
## 遠化 (paler and fainter the more of its natural qualities it lost), qualities it gained beyond its
## natural state as small marks (A+B=AB: looks the same, plus a mark), and the shimenawa rope on
## sacred things. Node position = ground point (y-sorted); drawing lifted by the ground height.

var e: FieldEntity
var shape := "rock"
var size := Vector2(1, 1)       # metres: width, height
var color := Color("#8c8678")
var rope := false
var targeted := false
var bounce := 0.0               # a transfer just touched it


func setup(entity: FieldEntity, view: Dictionary) -> void:
	e = entity
	name = "E_" + e.id
	shape = String(view.get("shape", "rock"))
	size = Vector2(float(view.get("w", 0.8)), float(view.get("h", 0.8)))
	color = Color.html(String(view.get("color", "#8c8678")))
	rope = bool(view.get("rope", false)) or e.holder.sacred
	sync()


func sync() -> void:
	position = Proj.sort_px(e.x, e.z)
	visible = not e.hidden
	queue_redraw()


func tick(dt: float) -> void:
	bounce = maxf(0.0, bounce - dt * 4.0)
	sync()


## Screen-space hit box (world px, relative to the world): for touch picks.
func hit_rect_world() -> Rect2:
	var w := size.x * Proj.PPM
	var hh := size.y * Proj.PPM
	var foot := Proj.to_px(e.x, e.z, e.h)
	return Rect2(foot.x - w * 0.5 - 4.0, foot.y - hh - 4.0, w + 8.0, hh + 8.0)


func _draw() -> void:
	var lift := -Proj.PPM * e.h
	var far := clampf(e.far, 0.0, 1.0)
	var c := color.lerp(Color(0.85, 0.87, 0.92), far * 0.6)
	c.a = 1.0 - far * 0.55
	var w := size.x * Proj.PPM
	var hh := size.y * Proj.PPM * (1.0 + bounce * 0.16)
	var base := Vector2(0, lift)
	# ground shadow
	_ellipse(base + Vector2(2, 0), Vector2(w * 0.55, 3.0), Color(0, 0, 0, 0.3 * c.a))
	var outline := Color(1.0, 0.93, 0.7, 1.0) if targeted else Color(0.08, 0.07, 0.1, c.a)
	match shape:
		"beam":
			var r := Rect2(base + Vector2(-w * 0.5, -hh), Vector2(w, hh)).abs()
			draw_rect(r.grow(1.0), outline)
			draw_rect(r, c)
			draw_line(r.position + Vector2(2, 2), r.position + Vector2(r.size.x - 2, 2), c.lightened(0.2))
		"frame":
			var r := Rect2(base + Vector2(-w * 0.5, -hh), Vector2(w, hh))
			draw_rect(r.grow(1.0), outline, false, 1.0)
			draw_rect(Rect2(r.position, Vector2(3, r.size.y)), c)
			draw_rect(Rect2(r.position + Vector2(r.size.x - 3, 0), Vector2(3, r.size.y)), c)
			for i in 3:
				draw_rect(Rect2(r.position + Vector2(0, 4 + i * r.size.y * 0.3), Vector2(r.size.x, 2)), c.darkened(0.15))
		"lantern":
			var r := Rect2(base + Vector2(-w * 0.3, -hh), Vector2(w * 0.6, hh))
			draw_rect(r.grow(1.0), outline)
			draw_rect(r, c)
			var lit: bool = e.holder.q["l"] >= 1
			draw_rect(Rect2(r.position + Vector2(2, 4), Vector2(r.size.x - 4, 6)), Color(1.6, 1.2, 0.6) if lit else Color(0.2, 0.18, 0.22))
		"sign":
			draw_rect(Rect2(base + Vector2(-1.5, -hh), Vector2(3, hh)), c.darkened(0.2))
			var board := Rect2(base + Vector2(-w * 0.6, -hh), Vector2(w * 1.2, hh * 0.45))
			draw_rect(board.grow(1.0), outline)
			draw_rect(board, c)
		_:
			_ellipse(base + Vector2(0, -hh * 0.45), Vector2(w * 0.5 + 1.0, hh * 0.5 + 1.0), outline)
			_ellipse(base + Vector2(0, -hh * 0.45), Vector2(w * 0.5, hh * 0.5), c)
			_ellipse(base + Vector2(-w * 0.12, -hh * 0.62), Vector2(w * 0.18, hh * 0.14), c.lightened(0.18))
	if rope:
		var y := base.y - hh * 0.55
		draw_line(Vector2(-w * 0.55, y), Vector2(w * 0.55, y), Color(0.92, 0.86, 0.66), 2.0)
		for i in 3:
			var px := -w * 0.3 + i * w * 0.3
			draw_line(Vector2(px, y), Vector2(px, y + 5), Color(0.95, 0.95, 0.9), 1.0)
	# gained qualities: a small mark per unit above its natural state (A+B=AB)
	var marks := 0
	for k in Qualities.ALL:
		var extra: int = e.holder.q[k] - e.holder.base[k]
		for i in maxi(0, extra):
			var p := base + Vector2(-w * 0.5 + 3.0 + marks * 5.0, -hh - 4.0)
			draw_rect(Rect2(p, Vector2(3, 3)), Qualities.color(k))
			marks += 1


func _ellipse(c: Vector2, r: Vector2, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 20:
		var a := TAU * i / 20.0
		pts.append(c + Vector2(cos(a) * r.x, sin(a) * r.y))
	draw_colored_polygon(pts, col)
