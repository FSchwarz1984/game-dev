extends TestCase
## The dialogue staging (story/staging.gd, docs/design/dialogue-staging.md): the script tags, the typing schedule,
## the default beats, the beats' tracks, skipping a line, 减少晃动, the flash limit, the pictures for every face, and
## StoryUI putting it on the real dialogue box without the card ever reaching the words.


func _line(st: Staging, who: String, face: String, text: String, card: bool = true) -> void:
	st.begin(who, face, Staging.parse(text), card)


func _run(st: Staging, seconds: float) -> void:
	for i in int(round(seconds * 30.0)):
		st.step(1.0 / 30.0)


func _tags(st: Staging) -> Array:
	var out: Array = []
	for e in st.beats_log:
		out.append(e[1] if e[2] == "" else "%s:%s" % [e[1], e[2]])
	return out


func test_tags_are_read_before_anything_is_escaped() -> void:
	var p := Staging.parse("[抖]不下！[/抖]这是我家！")
	eq(p["plain"], "不下！这是我家！")
	eq(p["bb"], "[pshake]不下！[/pshake]这是我家！")
	p = Staging.parse("[大]婆婆[/大]——！")
	eq(p["bb"], "[font_size=24]婆婆[/font_size]——！")
	p = Staging.parse("[轻]您小点声。[/轻]")
	eq(p["bb"], "[color=#f3ecdc8c]您小点声。[/color]")
	p = Staging.parse("[波]团子大人……[/波]")
	eq(p["bb"], "[pwave]团子大人……[/pwave]")
	# an unknown bracket shows as it is, escaped for the RichTextLabel; so does a stray closing tag
	p = Staging.parse("按[E]键[/x]")
	eq(p["plain"], "按[E]键[/x]")
	eq(p["bb"], "按[lb]E]键[lb]/x]")
	# point tags: where they stand in the words
	p = Staging.parse("婆婆[框抖]——！")
	eq(p["events"], [[2, "框抖", ""]])
	p = Staging.parse("[漫符:点点][慢]……[/慢][停0.4]第三个坛子里的梅干。")
	eq(p["plain"], "……第三个坛子里的梅干。")
	eq(p["events"], [[0, "漫符", "点点"]])
	near(float(p["pause"][2]), 0.4, 1e-6, "the pause after the dots")
	near(p["speed"][0], 0.5, 1e-6, "slow dots")
	near(p["speed"][2], 1.0, 1e-6, "then normal")
	check(not p["quiet"])
	p = Staging.parse("[静][漫符:汗@脸颊]您小点声。")
	check(p["quiet"], "[静]")
	eq(p["events"], [[0, "漫符", "汗@脸颊"]])
	p = Staging.parse("[快]最后是从窗户翻出来的。[/快]")
	near(p["speed"][0], 2.0)


func test_a_point_beat_fires_when_the_typing_reaches_it() -> void:
	var st := Staging.new()
	st.reset()
	_line(st, "tsuzumi", "neutral", "开头")
	_run(st, 1.0)
	_line(st, "tsuzumi", "neutral", "婆婆[框抖]——！")
	eq(st.box_offset(), Vector2.ZERO, "not before the words reach it")
	st.step(1.0 / 30.0)
	st.step(1.0 / 30.0)
	eq(st.shown, 2)
	eq(st.box_offset(), Vector2.ZERO, "still not: the dash has not come out")
	var moved := false
	for i in 6:
		st.step(1.0 / 30.0)
		moved = moved or st.box_offset() != Vector2.ZERO
	check(moved, "the box jolts once the dash comes out")
	_run(st, 1.0)
	eq(st.box_offset(), Vector2.ZERO, "and comes back to rest")


func test_typing_follows_punctuation_pauses_speed_tags_and_stops() -> void:
	var st := Staging.new()
	st.reset()
	# 30 characters a second; 0.22 s more after 。
	_line(st, "saji", "neutral", "一二。三")
	var t := 0.0
	while not st.typed_out and t < 5.0:
		st.step(1.0 / 120.0)
		t += 1.0 / 120.0
	near(t, 4.0 / 30.0 + 0.22, 0.02, "four characters and a full stop")
	_line(st, "saji", "neutral", "一二[停0.5]三四")
	t = 0.0
	while not st.typed_out and t < 5.0:
		st.step(1.0 / 120.0)
		t += 1.0 / 120.0
	near(t, 4.0 / 30.0 + 0.5, 0.02, "[停0.5]")
	_line(st, "saji", "neutral", "[慢]一二三四[/慢]")
	t = 0.0
	while not st.typed_out and t < 5.0:
		st.step(1.0 / 120.0)
		t += 1.0 / 120.0
	near(t, 4.0 / 15.0, 0.02, "[慢] halves the speed")
	_line(st, "saji", "neutral", "[快]一二三四[/快]")
	t = 0.0
	while not st.typed_out and t < 5.0:
		st.step(1.0 / 120.0)
		t += 1.0 / 120.0
	near(t, 4.0 / 60.0, 0.02, "[快] doubles it")
	# fast-forward (the advance key held) triples the rate
	_line(st, "saji", "neutral", "一二三四五六")
	var typed := st.step(6.5 / 90.0, 3.0)
	eq(typed.size(), 6, "held: three times as fast")
	eq(typed[0], [0, "一"])


func test_default_beats_follow_the_speakers_and_their_faces() -> void:
	var st := Staging.new()
	st.reset()
	_line(st, "saji", "laugh", "好，从今天起这儿就是我家了！")
	eq(_tags(st), ["入场"], "her first line slides in, nothing else")
	_run(st, 2.0)
	_line(st, "saji", "laugh", "还是这张脸")
	eq(_tags(st), [], "the same face again: no beat")
	_line(st, "saji", "angry", "[抖]不下！[/抖]这是我家！")
	eq(_tags(st), ["横抖"], "a new face: its own beat")
	_line(st, "tsuzumi", "neutral", "没吃。")
	eq(_tags(st), ["入场"], "the other speaker's first line slides in")
	_line(st, "saji", "shout", "这是我家！下去！")
	eq(_tags(st), ["框抖"], "back to her with a shout: the shout's beat")
	_line(st, "tsuzumi", "calm", "……")
	eq(_tags(st), ["弹"], "a change of speaker to a face without a beat: a hop")
	_line(st, "saji", "mischievous", "鼓槌在你那儿吧？我看见她塞的。")
	eq(_tags(st), ["弹", "漫符:闪光"], "mischievous brings the sparkle")
	_line(st, "saji", "tired", "[静]……")
	eq(_tags(st), [], "[静]: no default beat and no default mark")
	_line(st, "saji", "surprise", "[横抖]钟？")
	eq(_tags(st), ["跳", "横抖"], "the line's own card beat comes after the default one and wins")
	_line(st, "narr", "", "送り盆", false)
	eq(_tags(st), [], "narration has no card")
	st.reset()
	_line(st, "saji", "neutral", "钟？")
	eq(_tags(st), ["入场"], "a new conversation: she slides in again")


func test_tracks_hold_settle_and_stay_on_whole_pixels() -> void:
	var st := Staging.new()
	st.reset()
	_line(st, "saji", "neutral", "开头")
	_run(st, 1.0)
	_line(st, "saji", "surprise", "梁、梁飘起来了……你把它吃了？！")
	_run(st, 0.5)
	eq(st.card_offset(), Vector2(0, -2), "跳 stays 2 px up")
	_run(st, 3.0)
	eq(st.card_offset(), Vector2(0, -2), "until the line ends")
	_line(st, "saji", "sad", "……")
	_run(st, 1.0)
	eq(st.card_offset(), Vector2(0, 2), "沉 sinks 2 px and stays")
	# every offset of every track is whole pixels, and the card never moves more than 3 px toward the words
	for tr in Staging.CARD_TRACKS.values():
		for v in tr[1]:
			check(v == v.round(), "whole pixels")
			check(v.x <= 3.0, "at most 3 px toward the words")
	for v in Staging.BOX_TRACK[1] + Staging.VIEW_TRACK[1]:
		check(v == v.round(), "whole pixels")
		check(absf(v.x) <= 4.0 and absf(v.y) <= 4.0, "within the stage's shake margin")
	check(PixelStage.SHAKE_MARGIN >= 4, "the stage draws enough beyond the screen for the view shake")
	# 颤: one pixel either way while typing, still 0.3 s after
	_line(st, "saji", "afraid", "家、家里的事……不好往外说……")
	var seen := {}
	for i in 30:
		st.step(1.0 / 30.0)
		seen[st.card_offset().x] = true
		check(absf(st.card_offset().x) <= 1.0)
	check(seen.size() >= 2, "it trembles")
	_run(st, 5.0)
	eq(st.card_offset(), Vector2.ZERO, "and is still once the line has settled")


func test_a_skipped_line_settles_its_beats_and_drops_the_momentary_ones() -> void:
	var st := Staging.new()
	st.reset()
	_line(st, "tsuzumi", "neutral", "开头")
	_run(st, 1.0)
	_line(st, "tsuzumi", "neutral", "那是[漫符:惊]什么[跳]啊[漫符:汗]……[闪白][震屏][网点]")
	st.complete()
	check(st.typed_out)
	eq(st.flash_alpha(), 0.0, "no flash after the fact")
	eq(st.view_offset(), Vector2i.ZERO, "no shake after the fact")
	eq(st.card_offset(), Vector2(0, -2), "the hop is held where it would have ended")
	var names: Array = []
	for m in st.marks_now():
		names.append(m["name"])
	eq(names, ["sweat"], "the sweat stays, the surprise lines were only a moment")
	eq(st.snapshot()["tone"], true, "the dot screen is up")


func test_reduce_motion_keeps_everything_still() -> void:
	var st := Staging.new()
	st.reset()
	st.reduce_motion = true
	_line(st, "saji", "angry", "[震屏][闪白][框抖][抖]不下！[/抖][漫符:怒]")
	for i in 20:
		st.step(1.0 / 30.0)
		eq(st.card_offset(), Vector2.ZERO)
		eq(st.box_offset(), Vector2.ZERO)
		eq(st.view_offset(), Vector2i.ZERO)
		eq(st.flash_alpha(), 0.0)
		check(not st.text_moving())
	var m: Array = st.marks_now()
	eq(m.size(), 1, "the mark still shows")
	eq(m[0]["frame"], 1, "its settled frame")


func test_flashes_are_one_a_line_and_three_a_second_at_most() -> void:
	var st := Staging.new()
	st.reset()
	_line(st, "tsuzumi", "surprise", "[闪白]诶？[闪白]送火")
	st.step(1.0 / 30.0)
	check(st.flash_alpha() > 0.5, "the first flash")
	_run(st, 1.0)
	var n := 0
	for e in st.beats_log:
		n += 1 if e[1] == "闪白" else 0
	eq(n, 2, "both tags are read")
	var lit := 0
	_line(st, "tsuzumi", "surprise", "[闪白]一")
	for i in 3:
		_line(st, "tsuzumi", "surprise", "[闪白]二")
		if st.flash_alpha() > 0.0:
			lit += 1
		st.step(0.05)
	check(lit <= 2, "no more than three flashes inside one second (one was already lit just before)")


func test_every_face_has_its_pieces_and_every_mark_its_frames() -> void:
	var f := FileAccess.open("res://art/portraits/portraits.json", FileAccess.READ)
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	for who in data["characters"]:
		check(Staging.atlas(who) != null, "%s's atlas" % who)
		for expr in data["characters"][who]["expressions"]:
			for kind in Staging.FACE_PIECES:
				var fr := Staging.face_piece(who, expr, kind)
				check(fr.size() >= 3, "%s/%s %s frames" % [who, expr, kind])
				if not fr.is_empty():
					check(int(fr[-1][2]) > 0, "%s/%s %s is drawn" % [who, expr, kind])
					var r: Array = fr[-1]
					check(int(r[4]) >= 0 and int(r[5]) >= 0 and int(r[4]) + int(r[2]) <= 128 and int(r[5]) + int(r[3]) <= 128,
						"%s/%s %s stays on the portrait" % [who, expr, kind])
		check(Staging.ANCHORS.has(who), "%s has anchors" % who)
	for n in Staging.MARK_ANCHOR:
		check(not Staging.mark_frames(n).is_empty(), "mark %s" % n)
	eq(Staging.art_meta()["tone"].size(), 3, "the dot screen's frames")
	check(Staging.atlas("marks") != null)
	for k in Staging.MARKS:
		var n: String = Staging.MARKS[k]
		check(Staging.MARK_ANCHOR.has(n) or n in Staging.FACE_PIECES, "%s is drawn somehow" % k)


func test_story_ui_stages_lines_on_the_real_box_and_the_card_never_reaches_the_words() -> void:
	var root := (Engine.get_main_loop() as SceneTree).root
	var ui := StoryUI.new()
	root.add_child(ui)
	ui.apply_theme("pixel")
	var shakes: Array = []
	ui.view_shake = func(o: Vector2i) -> void: shakes.append(o)
	var lines := [
		{"who": "saji", "face": "surprise", "text": "梁、梁飘起来了……你把它吃了？！"},
		{"who": "saji", "face": "angry", "text": "[震屏][抖]不下！[/抖]这是我家！"},
		{"who": "tsuzumi", "face": "shout", "text": "[大]婆婆[/大]——！"},
	]
	ui.say(lines)
	var worst := 999.0
	for li in lines.size():
		for i in 90:
			ui.update(1.0 / 30.0)
			if ui.dlg.portrait_tex != null:
				worst = minf(worst, ui.dlg.text.position.x - ui.dlg.card.end.x)
			check(ui.dlg.card.position == ui.dlg.card.position.round(), "the card on whole pixels")
		eq(ui.dlg.text.get_parsed_text(), ui.stg.plain, "the words on screen are the line without its tags")
		ui.advance()
	check(worst >= 4.0 and worst <= 8.0, "the card stays clear of the words (closest %s px)" % worst)
	check(shakes.size() >= 2 and shakes[-1] == Vector2i.ZERO, "the view shook and came back")
	check(not ui.dialogue_open, "closed after the last line")
	eq(ui.dlg.card_offset, Vector2.ZERO)
	ui.queue_free()
