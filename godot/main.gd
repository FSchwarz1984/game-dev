extends Node
## The game: assembles the stage (world viewport), the world and its field, the HUD, the story layer
## and the director, and runs every frame in one fixed order:
##   input -> field (her body, movement, targeting) -> world (actors, Saji, views) -> camera ->
##   director (scene clock) -> story text -> fade/letterbox -> HUD (projected on this frame's camera)
## Canvas layers, bottom to top: world (stage) < Cinema 5 (letterbox, fade) < HUD 10 < Story 20.
## P1: this is the internal test region, not content. Every quality and verb is unlocked so the
## systems can be checked; the story will teach them (P4/P5).

var stage: PixelStage
var world: World
var field: Field
var hud: Hud
var story: StoryUI
var cinema: Cinema
var director: Director
var her: Actor
var saji: Actor
var frame := 0


func _ready() -> void:
	stage = PixelStage.new()
	add_child(stage)
	cinema = Cinema.new()
	_layer(5, "CinemaLayer").add_child(cinema)
	hud = Hud.new()
	_layer(10, "HudLayer").add_child(hud)
	story = StoryUI.new()
	_layer(20, "StoryLayer").add_child(story)
	story.cinema = cinema
	story.view_shake = func(o: Vector2i) -> void: stage.shake = o     # the dialogue's 震屏 moves the world only

	field = Field.new({"profile": GameState.body_profile()})
	world = World.new()
	stage.world_root.add_child(world)
	world.setup(stage, field)
	var region := world.load_region(_region_id())
	var spawn: Dictionary = region.def.get("spawn", {})
	field.player.x = float(spawn.get("x", 0.0))
	field.player.z = float(spawn.get("z", 0.0))
	field.player.h = field.ground_height(field.player.x, field.player.z)
	var f := Proj.face_vector(String(spawn.get("face", "front")))
	field.player.fx = f.x
	field.player.fz = f.y
	her = world.add_actor("tsuzumi", field.player)
	world.her = her
	her.face = String(spawn.get("face", "front"))
	var comp: Dictionary = region.def.get("companion", {})
	saji = world.add_companion("saji", float(comp.get("x", 0.0)), float(comp.get("z", 0.0)),
		{"label": func() -> String: return "说话", "run": _talk_to_saji})
	var sign := field.get_entity("sign")
	if sign != null:
		sign.ctx = {"label": func() -> String: return "看", "run": _read_sign}
	for k in Qualities.ALL:
		field.allow(k, ["take", "give", "release"])

	director = Director.new(world, story, Audio)
	story.wait = director.wait
	hud.field = field
	hud.stage = stage
	hud.her = her
	GameState.field = field
	GameState.region = region
	GameState.director = director
	GameState.settings_changed.connect(_on_setting)
	InputRouter.action.connect(_on_action)
	_apply_theme()
	world.follow({"cut": true})
	Audio.ambience(["wind"])
	DebugBridge.attach(self)
	print("BOOT_OK region=%s profile=%s scheme=%s font=%s touch_ui=%s" % [region.id, GameState.setting("body_profile"),
		GameState.setting("control_scheme"), GameState.setting("font_theme"), GameState.touch_ui_on()])


## The region to load: "test" (the internal test region), or another id given on the command line
## for checking (`-- --region=home_saddle`); not saved.
func _region_id() -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--region="):
			return a.trim_prefix("--region=")
	return "test"


func _exit_tree() -> void:
	CharacterLibrary.clear()
	UiTheme.clear()
	Staging.clear()


func _layer(n: int, label: String) -> CanvasLayer:
	var l := CanvasLayer.new()
	l.layer = n
	l.name = label
	add_child(l)
	return l


func _apply_theme() -> void:
	var k := String(GameState.setting("font_theme"))
	story.apply_theme(k)
	hud.apply_theme(k)


func _on_setting(key: String, _value) -> void:
	match key:
		"font_theme":
			_apply_theme()
		"body_profile":
			field.set_profile(GameState.body_profile())


func _process(dt: float) -> void:
	frame += 1
	if frame == 1:
		print("FIRST_FRAME ticks=%d" % Time.get_ticks_msec())
	InputRouter.enabled = true
	var mv := InputRouter.move_vector() if not story.blocking else Vector2.ZERO
	field.update(dt, {"mx": mv.x, "mz": mv.y})
	for e in field.drain():
		_on_field_event(e)
	her.heavy = int(field.player.body.levels["w"]) >= 2
	her.set_body_look(field.player.body.look())
	world.tick(dt)
	stage.cam.update(dt)
	stage.apply_camera()
	director.tick(dt)
	story.update(dt)
	cinema.tick(dt)
	hud.update_hud(dt)


# ------------------------------------------------------------------ input

func _on_action(a: Dictionary) -> void:
	var type := String(a.get("type", ""))
	if story.dialogue_open:
		if type in ["context", "advance", "dodge"]:
			story.advance()
		return
	if story.blocking:
		return
	match type:
		"quality":
			_quality(String(a["k"]), String(a["gesture"]))
		"context":
			if field.context() == "" and field.target != null:
				Audio.sfx("deny")
		"cycle":
			field.targeting.cycle()
		"pick":
			var e := world.pick_at(a["pos"])
			if e != null and not field.pick(e):
				hud.say("far")
				Audio.sfx("deny")
		"dev":
			_dev(String(a["what"]))
		"pause":
			pass  # no menu yet (P1)


## What a quality key does: the explicit scheme names the verb by the gesture; the obvious scheme
## lets the field plan it (Field.plan). Feedback within the same frame: a sound, her gesture, the
## target's bounce, or a refusal line with its reason.
func _quality(k: String, gesture: String) -> void:
	var e: Dictionary
	if String(GameState.setting("control_scheme")) == "obvious" and gesture != "release":
		e = field.act(k, gesture == "alt")
	else:
		e = field.transfer({"press": "take", "alt": "give", "release": "release"}[gesture], k)
	if e.is_empty():
		return
	if e["type"] == "refused":
		hud.say(String(e["reason"]), k)
		Audio.sfx("deny")
		return
	var verb := String(e.get("verb", "release"))
	Audio.sfx(verb, {"k": k})
	her.play(verb)
	var target = e.get("from") if verb == "take" else e.get("to")
	for id in world.views:
		var v: EntityView = world.views[id]
		if v.e.holder == target:
			v.bounce = 1.0


func _on_field_event(e: Dictionary) -> void:
	match String(e.get("type", "")):
		"regained":
			Audio.sfx("regain", {"k": e["k"]})
		"ignite":
			Audio.sfx("ignite")
		"blocked":
			story.bark({"who": "tsuzumi", "text": String(e["say"])})
	DebugBridge.note_event(e)


func _dev(what: String) -> void:
	var cycle := func(key: String, values: Array) -> void:
		var i := values.find(GameState.setting(key))
		GameState.set_setting(key, values[(i + 1) % values.size()])
	match what:
		"scheme":
			cycle.call("control_scheme", ["explicit", "obvious"])
		"font":
			cycle.call("font_theme", ["pixel", "vector"])
		"body":
			cycle.call("body_profile", ["draft", "legacy"])
		"touch":
			cycle.call("touch_ui", ["auto", "on", "off"])
		"cinema":
			_cinema_check()
			return
	print("DEV %s -> scheme=%s font=%s body=%s touch_ui=%s" % [what, GameState.setting("control_scheme"),
		GameState.setting("font_theme"), GameState.setting("body_profile"), GameState.setting("touch_ui")])


# ------------------------------------------------------------------ internal checks (debug builds)

## F10: every director verb in one scene, to check by eye and by the bot: a camera shot with a
## slow crane, Saji's scripted walk, her bow, the letterbox, a fade to black with a caption card on
## top of it (the fade must stay under the words), a title drop over white, a subtitle, and the
## hand-back of actors and camera at the end.
func _cinema_check() -> void:
	if director.busy:
		return
	director.scene(func(d: Director) -> void:
		field.control = false
		hud.show_hud(false)
		d.letterbox(true)
		d.shot("stairs", {"speed": 1.5})
		await d.move("saji", [Vector2(saji.x, saji.z - 1.5)], {"speed": 2.0})
		await d.play("tsuzumi", "bow")
		await d.fade(1.0, 0.6, Color.BLACK)
		await d.card("（测试）字幕卡", "淡入淡出在文字下面", 2.0)
		await d.fade(1.0, 0.5, Color.WHITE)
		await d.title("天岸", "（测试）标题", 2.0)
		await d.fade(0.0, 0.6)
		await d.sub("（测试）字幕：没有对话框的台词。", 1.6)
		d.letterbox(false)
		d.follow({"speed": 4.0})
		await d.wait(0.6)
		field.control = true
		hud.show_hud(true))


# ------------------------------------------------------------------ test dialogues (internal)

func _talk(lines: Array) -> void:
	director.scene(func(d: Director) -> void:
		field.control = false
		hud.show_hud(false)
		await d.say(lines)
		field.control = true
		hud.show_hud(true))


func _talk_to_saji() -> String:
	_talk([
		{"who": "saji", "face": "smile", "text": "（测试对话）名牌一行、立绘在自己的框里、正文从框右边开始。"},
		{"who": "tsuzumi", "face": "neutral", "text": "（测试）「百々かさゝぎ」「家守さぢ」「垣外しをね」——ゝゞヽヾ々っゃゅょ。取「重」，予「熱」。"},
		{"who": "saji", "face": "think", "text": "（测试）第三行：两行换行与打字机的停顿；句读不放在行首，小假名不放在行首。"},
		{"who": "saji", "face": "cry_loud", "text": "（测试）[震屏]震屏只震画面，对话框和字不动；[等]按一下接着打。"},
	])
	return "说话"


func _read_sign() -> String:
	_talk([{"who": "narr", "text": "（测试）道标。旁白没有立绘，正文占满整个对话框的宽度。"}])
	return "看"
