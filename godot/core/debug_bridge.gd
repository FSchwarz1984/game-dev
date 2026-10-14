extends Node
## DebugBridge (autoload): exposes the game's state to the playtest bot. DEBUG BUILDS ONLY, and only
## when asked on the command line (after "--"):
##   --bot-state=<file.json>  the state is written there every other frame (atomically: tmp, rename)
##   --bot-cmd=<file.json>    polled every frame for {"id": n, "cmd": "shot", "path": png} or
##                            {"id": n, "cmd": "quit"}; the state's "cmd_ack" reports the last id done
##   --bot-log                print every routed input action (ACTION lines)
## The bot drives the game only through real input (xdotool through the X server); this bridge
## only reports, so a passing bot run proves the real input path (CLAUDE.md §4). Positions are given
## in window pixels too, so the bot can aim like a player looking at the screen.

var state_path := ""
var cmd_path := ""
var main: Node = null
var active := false
var cmd_ack := -1
var events: Array = []
var _frame := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	if not OS.is_debug_build():
		return
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--bot-state="):
			state_path = a.substr(12)
		elif a.begins_with("--bot-cmd="):
			cmd_path = a.substr(10)
		elif a == "--bot-log":
			InputRouter.log_events = true
	active = state_path != "" or cmd_path != ""


func attach(m: Node) -> void:
	main = m


func note_event(e: Dictionary) -> void:
	if not active:
		return
	var out := {"type": e.get("type", ""), "frame": Engine.get_process_frames()}
	for k in ["verb", "k", "reason", "zone", "say"]:
		if e.has(k):
			out[k] = e[k]
	if e.get("e") is FieldEntity:
		out["e"] = (e["e"] as FieldEntity).id
	events.append(out)
	if events.size() > 40:
		events.pop_front()


func _process(_dt: float) -> void:
	if not active or main == null or not is_instance_valid(main):
		return
	_frame += 1
	if cmd_path != "" and FileAccess.file_exists(cmd_path):
		_run_command()
	if state_path != "" and _frame % 2 == 0:
		_write_state()


func _run_command() -> void:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(cmd_path))
	if not (parsed is Dictionary):
		return
	var id := int(parsed.get("id", -1))
	if id <= cmd_ack:
		return
	match String(parsed.get("cmd", "")):
		"shot":
			var img := get_viewport().get_texture().get_image()
			if get_viewport().use_hdr_2d and RenderingServer.get_current_rendering_method() != "gl_compatibility":
				img.convert(Image.FORMAT_RGBAF)
				for y in img.get_height():
					for x in img.get_width():
						img.set_pixel(x, y, img.get_pixel(x, y).linear_to_srgb())
				img.convert(Image.FORMAT_RGBA8)
			var err := img.save_png(String(parsed.get("path", "user://shot.png")))
			print("SHOT %s %dx%d err=%d" % [parsed.get("path", ""), img.get_width(), img.get_height(), err])
		"quit":
			get_tree().quit()
	cmd_ack = id


func _write_state() -> void:
	var m = main
	var stage: PixelStage = m.stage
	var field: Field = m.field
	var P := field.player
	var win := Vector2(get_window().size)
	var to_win := func(world_px: Vector2) -> Array:
		var s := stage.to_window(stage.world_to_screen(world_px))
		return [roundi(s.x), roundi(s.y)]
	var ents: Array = []
	for e in field.entities:
		var hit := Rect2()
		if m.world.views.has(e.id):
			hit = (m.world.views[e.id] as EntityView).hit_rect_world()
		else:
			var foot := Proj.to_px(e.x, e.z, e.h)
			hit = Rect2(foot.x - 10, foot.y - 32, 20, 34)
		ents.append({"id": e.id, "name": e.name, "x": snappedf(e.x, 0.001), "z": snappedf(e.z, 0.001), "h": e.h,
			"q": e.holder.q, "base": e.holder.base, "far": snappedf(e.far, 0.001), "sacred": e.holder.sacred,
			"screen": to_win.call(hit.get_center()), "foot": to_win.call(Proj.to_px(e.x, e.z, e.h))})
	var keys := {}
	for id in InputRouter.keys:
		var k: Dictionary = InputRouter.keys[id]
		var r: Rect2 = k["rect"]
		var a := stage.to_window(r.position)
		keys[id] = {"rect": [roundi(a.x), roundi(a.y), roundi(r.size.x * stage.scale_factor), roundi(r.size.y * stage.scale_factor)],
			"visible": k.get("visible", false)}
	var her: Actor = m.her
	var dlg: Dictionary = m.story.snapshot()
	if dlg.get("open", false):
		for key in ["box", "card", "text_rect"]:
			var r: Array = dlg[key]
			var a := stage.to_window(Vector2(r[0], r[1]))
			dlg[key + "_win"] = [roundi(a.x), roundi(a.y), roundi(r[2] * stage.scale_factor), roundi(r[3] * stage.scale_factor)]
	var plans := {}
	for k in m.hud.plans:
		var p: Dictionary = m.hud.plans[k]
		plans[k] = {"verb": p.get("verb", ""), "reason": p.get("reason", ""), "gesture": p.get("gesture", "")}
	var s := {
		"ready": true, "frame": Engine.get_process_frames(), "t": snappedf(Time.get_ticks_msec() / 1000.0, 0.001),
		"fps": Engine.get_frames_per_second(), "window": [win.x, win.y], "logical": [stage.logical.x, stage.logical.y],
		"scale": stage.scale_factor, "margin": [stage.margin.x, stage.margin.y],
		"settings": {"scheme": GameState.setting("control_scheme"), "font": GameState.setting("font_theme"),
			"body": GameState.setting("body_profile"), "touch_ui": GameState.touch_ui_on()},
		"player": {"x": snappedf(P.x, 0.001), "z": snappedf(P.z, 0.001), "h": snappedf(P.h, 0.001),
			"fx": snappedf(P.fx, 0.001), "fz": snappedf(P.fz, 0.001), "moving": P.moving, "control": field.control,
			"q": P.holder.q, "base": P.holder.base, "levels": P.body.levels, "progress": P.body.progress,
			"burning": P.body.burning, "integrity": P.body.integrity, "speed": snappedf(P.body.speed(), 0.001),
			"anim": her.anim_name, "state": her.state_name(), "face": her.face,
			"screen": to_win.call(Proj.to_px(P.x, P.z, P.h)), "look": P.body.look()},
		"target": {"id": field.target.id, "name": field.target.name} if field.target != null else null,
		"entities": ents, "keys": keys, "stick": not InputRouter.stick.is_empty(),
		"hud": {"plans": plans, "prompt": [m.hud.prompt_rect.position.x, m.hud.prompt_rect.position.y, m.hud.prompt_rect.size.x, m.hud.prompt_rect.size.y]},
		"dialogue": dlg,
		"ledger": {"totals": field.L.totals(), "air": field.L.air},
		"camera": [snappedf(stage.render_cam.x, 0.01), snappedf(stage.render_cam.y, 0.01)],
		"sounds": Audio.played.map(func(p): return p[0]),
		"events": events, "cmd_ack": cmd_ack,
	}
	var tmp := state_path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(s))
	f.close()
	DirAccess.rename_absolute(tmp, state_path)
