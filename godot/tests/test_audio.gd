extends TestCase
## The sound (core/audio.gd, audio_ambience.gd, audio_music.gd; G5R3-53, G5R3-63, G5R3-65): no variant twice
## running, the dialogue ducking's amounts, no recording anywhere in the package, every file listed with its
## recipe, v0.1's time windows, no music in the 遠化 (5e), the creatures only from places that exist (rule 3),
## no two bell crickets on near pitches (rule 4), the footfalls on the walk cycle.

const AUDIO_EXT := ["ogg", "wav", "mp3", "flac", "opus", "aiff", "aif", "m4a", "aac", "wma"]


func test_variant_pool_never_plays_the_same_one_twice_running() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 12345
	for n in [2, 3, 4, 8, 12]:
		var pool := Audio.VariantPool.new(n, rng)
		var last := -1
		var counts := {}
		var repeats := 0
		for i in 2400:
			var v := pool.pick()
			check(v >= 0 and v < n, "variant in range")
			if v == last:
				repeats += 1
			last = v
			counts[v] = int(counts.get(v, 0)) + 1
		eq(repeats, 0, "repeats with %d variants" % n)
		# a shuffled bag: every variant comes up as often as the others (decision 7: no share above 2/n)
		for v in n:
			var share := float(counts.get(v, 0)) / 2400.0
			check(share <= 2.0 / n and share >= 0.5 / n, "share of variant %d of %d: %.3f" % [v, n, share])


func test_choose_on_the_real_sounds_never_repeats() -> void:
	for id in ["step_grass_walk", "step_stone_run", "caw", "ev_suzumushi", "ui_move"]:
		if not check(Audio.has(id), "%s in sounds.json" % id):
			continue
		var last := -1
		var rep := 0
		for i in 200:
			var c := Audio.choose(id)
			check(not c.is_empty() and c[0] is AudioStream, "%s chooses a stream" % id)
			if int(c[3]) == last:
				rep += 1
			last = int(c[3])
		eq(rep, 0, "%s repeats" % id)


func test_dialogue_ducking_is_9_db_for_music_and_4_for_the_air() -> void:
	Audio.duck(0.35, 0.01)
	for i in 10:
		Audio._process(0.05)
	near(Audio.duck_db("Music"), -9.0, 0.01, "music under a dialogue")
	near(Audio.duck_db("Ambience"), -4.0, 0.01, "ambience under a dialogue")
	near(Audio.duck_db("SFX"), 0.0, 0.0001, "the effects are not ducked")
	var mi := AudioServer.get_bus_index("Music")
	var base := linear_to_db(maxf(float(GameState.setting("vol_music")), 0.0001))
	near(AudioServer.get_bus_volume_db(mi), base - 9.0, 0.05, "the Music bus is down 9 dB")
	Audio.duck(0.0, 0.01)
	for i in 10:
		Audio._process(0.05)
	near(Audio.duck_db("Music"), 0.0, 0.01, "back after the dialogue")
	near(AudioServer.get_bus_volume_db(mi), base, 0.05)


func test_no_recording_is_packaged() -> void:
	# every audio file in the project is one of ours, listed in SOURCES.json with its synthesizer recipe
	var src := JSON.parse_string(FileAccess.get_file_as_string("res://audio/SOURCES.json")) as Dictionary
	check(src != null, "SOURCES.json reads")
	var files: Dictionary = src.get("files", {})
	var text := FileAccess.get_file_as_string("res://audio/SOURCES.json").to_lower()
	for w in ["freesound", "xeno-canto", "aporee", "archive.org", "recorded", "field recording", ".mp3"]:
		check(not text.contains(w), "SOURCES.json mentions %s" % w)
	var found: Array = []
	_scan("res://", found)
	check(found.size() > 100, "audio files found: %d" % found.size())
	for f in found:
		var rel := String(f).trim_prefix("res://")
		check(not rel.begins_with("audio/ambience/") and not rel.begins_with("audio/spots/"), "old recording %s" % rel)
		if check(files.has(rel), "%s is listed in SOURCES.json" % rel):
			var gen := String((files[rel] as Dictionary).get("generator", ""))
			check(gen.contains("synthesizer") or gen.contains("numpy"), "%s says how it was synthesized" % rel)
	# and every listed file is there
	for rel in files:
		check(FileAccess.file_exists("res://" + String(rel)), "listed file %s exists" % rel)


func _scan(dir: String, out: Array) -> void:
	for d in DirAccess.get_directories_at(dir):
		if d.begins_with("."):
			continue
		_scan(dir.path_join(d), out)
	for f in DirAccess.get_files_at(dir):
		if f.get_extension().to_lower() in AUDIO_EXT:
			out.append(dir.path_join(f))


func test_every_sound_the_game_asks_for_is_there() -> void:
	var ids: Array = ["noise_pink", "radio_fest", "caw", "wings", "thunder", "bell_saji", "step_heavy", "step_drum",
		"take", "give", "release", "deny", "far_pulse", "far_wave", "mus_title", "mus_home", "mus_prologue", "mus_wonder",
		"mus_tension"]
	for m in ["grass", "soil", "stone", "wood", "water", "leaves", "sand", "moss"]:
		ids.append("step_%s_walk" % m)
		ids.append("step_%s_run" % m)
	for m in ["soil", "grass", "wood", "stone"]:
		ids.append("saji_step_" + m)
	for k in ["w", "h", "l", "s", "v"]:
		for v in ["take", "give", "release"]:
			ids.append("qual_%s_%s" % [k, v])
	for u in ["ui_move", "ui_ok", "ui_back", "ui_open", "ui_close"]:
		ids.append(u)
	for v in Audio.VOICES:
		ids.append("blip_" + v)
	for e in ["minmin", "higu", "ugu", "tit", "suzumushi", "kajika", "clack", "drip"]:
		ids.append("ev_" + e)
	for row in AudioAmbience.LEAVES + AudioAmbience.SASA + AudioAmbience.RAIN:
		ids.append(String(row[1]))
	for s in AudioAmbience.STREAM:
		ids.append(s)
	for row in AudioMusic.FEST:
		ids.append(String(row[2]))
	for mo in AudioMusic.MODES:
		ids.append("mus_explore_" + mo)
	for id in ids:
		if check(Audio.has(id), "%s in sounds.json" % id):
			for f in Audio.sounds[id]["files"]:
				check(ResourceLoader.exists(String(f)), "%s exists" % f)
	# the loops say so; the music says its tempo and length
	check(bool(Audio.sounds["mus_home"].get("loop", false)), "the home piece loops")
	near(float(Audio.sounds["mus_home"].get("bpm", 0)), 60.0, 0.001, "home at v0.1's 60 bpm")
	check(not bool(Audio.sounds["mus_wonder"].get("loop", false)), "the wonder piece plays once")


func test_no_music_in_the_far() -> void:
	# 5e (G5R3-65): where she stands in the 遠化 the music is gone; looking at it from outside leaves it be
	near(Audio.music_in_far(0.0), 1.0, 1e-6)
	near(Audio.music_in_far(0.5), 0.0, 1e-6)
	near(Audio.music_in_far(1.0), 0.0, 1e-6)
	var mid := Audio.music_in_far(0.3)
	check(mid > 0.0 and mid < 1.0, "fades between: %.3f" % mid)


func test_v01_time_windows() -> void:
	# legacy/v0.1/src/audio.js dayW: 1 inside, easing over f hours, wrapping past midnight
	near(AudioAmbience.day_w(12.0, 9.0, 16.5, 0.6), 1.0, 1e-6, "cicadas at noon")
	near(AudioAmbience.day_w(9.3, 9.0, 16.5, 0.6), 0.5, 1e-6, "easing in")
	near(AudioAmbience.day_w(20.0, 9.0, 16.5, 0.6), 0.0, 1e-6, "none at night")
	near(AudioAmbience.day_w(23.0, 19.5, 4.5, 0.5), 1.0, 1e-6, "bell crickets at 23:00")
	near(AudioAmbience.day_w(2.0, 19.5, 4.5, 0.5), 1.0, 1e-6, "and past midnight")
	near(AudioAmbience.day_w(12.0, 19.5, 4.5, 0.5), 0.0, 1e-6, "not at noon")
	var w := AudioAmbience.mix_weights(AudioAmbience.LEAVES, 0.4)
	near(float(w[0]) + float(w[1]) + float(w[2]), 1.0, 1e-6, "crossfade weights sum to 1")
	check(float(w[0]) > 0.0 and float(w[1]) > 0.0, "between the first two loops")


class NoPlaces:
	extends RefCounted
	func tree(_r, _a, _b) -> Vector3: return Vector3.INF
	func grass(_r, _a, _b) -> Vector3: return Vector3.INF
	func water(_r, _a, _b) -> Vector3: return Vector3.INF
	func bamboo(_r, _a, _b) -> Vector3: return Vector3.INF
	func listener() -> Vector3: return Vector3.ZERO
	func stream_points(_s) -> PackedVector3Array: return PackedVector3Array()


class OnePlace:
	extends NoPlaces
	func tree(_r, _a, _b) -> Vector3: return Vector3(5, 0, 5)
	func grass(r: RandomNumberGenerator, _a, _b) -> Vector3: return Vector3(r.randf_range(-6, 6), 0, r.randf_range(-6, 6))


func test_creatures_sound_only_from_places_that_exist() -> void:
	var root := Node3D.new()
	Engine.get_main_loop().root.add_child(root)
	Audio.attach_world(root)
	var amb := Audio.amb
	amb.places = NoPlaces.new()
	amb.log_events = true
	amb.events_log.clear()
	amb._active.clear()
	for i in 40:
		amb._maybe("minmin", 1e6, 1.0, 3, "tree", "ev_minmin")
	eq(amb.events_log.size(), 0, "no tree round her: no cicada (rule 3)")
	amb.places = OnePlace.new()
	for i in 40:
		amb._maybe("minmin", 1e6, 1.0, 3, "tree", "ev_minmin")
	eq(amb.events_log.size(), 3, "a tree: cicadas, up to v0.1's three at once")
	# rule 4: bell crickets never on near pitches together
	amb.events_log.clear()
	amb._active.clear()
	var f0: Array = Audio.sounds["ev_suzumushi"].get("f0", [])
	check(f0.size() == (Audio.sounds["ev_suzumushi"]["files"] as Array).size(), "each bell cricket's pitch is known")
	for i in 60:
		amb._maybe("suzu", 1e6, 1.0, 3, "grass", "ev_suzumushi")
	var act: Array = amb._active.get("suzu", [])
	check(act.size() >= 1 and act.size() <= 3, "at most three at once (%d)" % act.size())
	for a in act:
		for b in act:
			if a != b:
				check(absf(float(a[1]) - float(b[1])) >= 60.0, "two crickets %.0f and %.0f Hz apart" % [a[1], b[1]])
	amb.log_events = false
	amb.places = null
	Audio.attach_world(null)
	root.queue_free()


func test_footfalls_on_the_walk_cycle() -> void:
	# her sheet's walk: 8 frames, the feet down at 1/16 and 9/16 of the cycle: two steps a cycle, never more
	eq(ShowcaseSound.footfalls(0.0, 0.1), 1, "the first foot")
	eq(ShowcaseSound.footfalls(0.1, 0.5), 0, "between the feet")
	eq(ShowcaseSound.footfalls(0.5, 0.6), 1, "the second foot")
	eq(ShowcaseSound.footfalls(0.9, 0.08), 1, "over the wrap: the first foot again")
	eq(ShowcaseSound.footfalls(0.6, 0.58), 2, "almost a whole cycle in one frame (a long frame): both feet")
