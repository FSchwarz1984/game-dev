@tool
class_name PixelShake
extends RichTextEffect
## [pshake]...[/pshake] (the script writes [抖]...[/抖], docs/design/dialogue-staging.md §2.4): every character jumps
## by one whole native pixel in a random direction about 12 times a second. StoryUI stops it (active = false) 0.6 s
## after the line has typed out, and keeps it off under 减少晃动, so the words are still to read.

var bbcode := "pshake"
var active := true
var t := 0.0


func _process_custom_fx(fx: CharFXTransform) -> bool:
	if not active:
		return true
	var h := absi(hash(Vector3i(fx.relative_index, int(t * 12.0), 7)))
	fx.offset = Vector2(float(h % 3) - 1.0, float((h / 3) % 3) - 1.0)
	return true
