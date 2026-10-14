class_name VistaFigure
extends AnimatedSprite2D
## Her real sprite on the camphor limb in the prologue vista, seen from behind: the host puts one of
## these in Vista.figure_slot() and calls set_pose() with Vista.state.pose ("sit", "stand", "shout").
## Poses come from the sprite sheets (docs/knowledge/20-sprites.md): sitEdge, standUp and shout,
## back view, on the "plain" sheet (her load stays at the roots while she climbs). The slot's origin
## is her ground point, so the sprite is drawn with its pivot there.

const ID := "tsuzumi"
const SHEET := "plain"
const POSES := {"sit": "sitEdge_back", "stand": "standUp_back", "shout": "shout_back"}

var pose := ""


func _ready() -> void:
	centered = false
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sprite_frames = CharacterLibrary.frames(ID, SHEET)
	offset = -Vector2(CharacterLibrary.pivot(ID))
	set_pose("sit")


func set_pose(p: String) -> void:
	if p == pose or not POSES.has(p):
		return
	pose = p
	var anim: String = POSES[p]
	if sprite_frames == null or not sprite_frames.has_animation(anim):
		push_warning("VistaFigure: no animation %s" % anim)
		return
	play(anim)
