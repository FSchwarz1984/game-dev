extends SceneTree
## Dialogue-box screenshots for the portrait layout check (docs/knowledge/13-pixel-portraits.md §10):
##   godot --path godot --resolution 1920x1080 -s res://tests/shot_dialogue.gd -- --out=DIR [--bg=PNG] [--native=640x360]
## Not a unit test (run.gd only picks up test_*.gd). Builds a bare native canvas (the project's canvas_items
## stretch at an integer scale), puts a background picture behind it (e.g. a frame of the world, scaled to the
## native size), shows the real DialogueBox with the real portraits for each line below, and saves the window as
## DIR/dialogue_<n>_<who>_<face>.png. Also writes DIR/layout.txt: the box, card, text and name-plate rectangles
## and whether the card overlaps the text column (it must not).

## Lines from docs/design/script-03-draft.md and characters.md (layout fixtures only; the long one joins two of
## Shione's lines from characters.md to check a two-line page).
const LINES := [
	{"who": "tsuzumi", "face": "cry", "text": "您说，婆婆会不会当我是故意不去的。"},
	{"who": "shione", "face": "cry", "text": "……不要紧的。我这就把它插回去。"},
	{"who": "saji", "face": "cry", "text": "对不起对不起，我不是故意睡在你家祠底下的，路上的地藏我也一个一个道过歉了……"},
	{"who": "tsuzumi", "face": "smile", "text": "您的团子，我拿桃换了啊。婆婆说今早刚摘的，可甜了。"},
	{"who": "shione", "face": "surprise", "text": "啊，这个吗？刚才横在路上，我想搬开比较方便大家走。"},
	{"who": "saji", "face": "angry", "text": "看什么看！快抬啊！"},
	{"who": "tsuzumi", "face": "neutral", "text": "十盏灯，一包供品，送到山口那几座墓，对吧。运费还跟去年一样？"},
	{"who": "shione", "face": "neutral", "text": "啊，这个吗？刚才横在路上，我想搬开比较方便大家走。……不要紧的。我这就把它插回去。"},
	{"who": "narr", "face": "", "text": "送り盆"},
]

## Display names for the check: the protagonist's approved name (G5R2-5) is the longest one on the plate.
const NAMES := {"tsuzumi": "百々かさゝぎ", "shione": "垣外しをね", "saji": "家守さぢ", "narr": ""}

var out_dir := "user://shots"
var bg_path := ""
var native := Vector2i(640, 360)


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
		elif a.begins_with("--bg="):
			bg_path = a.substr(5)
		elif a.begins_with("--native="):
			var p := a.substr(9).split("x")
			native = Vector2i(int(p[0]), int(p[1]))
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _run() -> void:
	var win := get_root()
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	win.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	win.content_scale_stretch = Window.CONTENT_SCALE_STRETCH_INTEGER
	win.content_scale_size = native
	win.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	var layer := Control.new()
	layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	win.add_child(layer)
	var bg := ColorRect.new()
	bg.color = Color8(46, 58, 44)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(bg)
	if bg_path != "":
		var img := Image.load_from_file(bg_path)
		if img != null:
			var tr := TextureRect.new()
			tr.texture = ImageTexture.create_from_image(img)
			tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			tr.set_anchors_preset(Control.PRESET_FULL_RECT)
			tr.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			layer.add_child(tr)
	var box := DialogueBox.new()
	layer.add_child(box)
	box.apply_theme("pixel")
	var report := PackedStringArray()
	report.append("window %s, native %s" % [str(win.size), str(native)])
	var fnt := UiTheme.font("pixel")
	report.append("font height %.1f ascent %.1f descent %.1f at 12 px; line separation %d" % [
		fnt.get_height(12), fnt.get_ascent(12), fnt.get_descent(12), UiTheme.LINE["pixel"] - 12])
	var i := 0
	for line in LINES:
		var who := String(line["who"])
		var shown := String(NAMES.get(who, ""))
		var tex: Texture2D = null
		if shown != "":
			tex = _portrait(who, String(line["face"]))
		box.show_line(shown, tex, String(line["text"]))
		box.text.visible_characters = -1
		box.done = true
		for _f in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var shot := win.get_texture().get_image()
		var name := "dialogue_%d_%s_%s.png" % [i, who, String(line["face"])]
		shot.save_png(out_dir.path_join(name))
		var text_rect := Rect2(box.text.position, box.text.size)
		var lines_used := box.text.get_line_count()
		var content_h := box.text.get_content_height()
		var overlap := box.card.has_area() and box.card.intersects(text_rect)
		var plate_overlap := box.card.has_area() and box.plate.has_area() and box.card.intersects(box.plate)
		var clipped := content_h > text_rect.size.y
		report.append("%s  box %s  card %s  text %s (%d lines, content %d px, clipped: %s)  plate %s  card/text overlap: %s  card/plate overlap: %s" % [
			name, str(box.box), str(box.card), str(text_rect), lines_used, content_h, str(clipped), str(box.plate), str(overlap), str(plate_overlap)])
		i += 1
	var f := FileAccess.open(out_dir.path_join("layout.txt"), FileAccess.WRITE)
	f.store_string("\n".join(report) + "\n")
	f.close()
	print("\n".join(report))
	quit()


## The same lookup as StoryUI.portrait (not referenced here: story_ui.gd needs the autoloads, which a -s
## script does not get at compile time).
static func _portrait(who: String, face: String) -> Texture2D:
	for f in [face, "neutral"]:
		var p := "res://art/portraits/%s/%s.png" % [who, f]
		if ResourceLoader.exists(p):
			return load(p) as Texture2D
	return null
