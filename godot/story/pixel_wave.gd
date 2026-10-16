@tool
class_name PixelWave
extends RichTextEffect
## [pwave]...[/pwave] (the script writes [波]...[/波]): the characters ride a slow wave of whole native pixels (one up
## or down), for singing and teasing. Settles like PixelShake.

var bbcode := "pwave"
var active := true
var t := 0.0


func _process_custom_fx(fx: CharFXTransform) -> bool:
	if not active:
		return true
	fx.offset = Vector2(0.0, roundf(sin(t * 7.0 - float(fx.relative_index) * 0.9)))
	return true
