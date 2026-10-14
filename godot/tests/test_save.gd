extends TestCase
## Save: versioned envelopes under user://, a backup kept on every write, and no crash when the
## storage is unavailable (the game keeps its saves in memory).

const SaveScript := preload("res://core/save.gd")


func fresh(root: String) -> Node:
	var s: Node = SaveScript.new()
	s.root = root
	return s


func test_a_save_round_trips_with_its_format_version() -> void:
	var s := fresh("user://test_saves/a")
	check(s.write("game", {"stage": "day1", "flags": {"beam": true}}), "written")
	var env: Dictionary = s.read("game")
	eq(env.get("format"), SaveScript.FORMAT)
	eq(env["data"]["stage"], "day1")
	eq(env["data"]["flags"], {"beam": true})
	check(FileAccess.file_exists(s.path_of("game")), "on disk")
	s.erase("game")
	s.free()


func test_the_previous_save_is_kept_and_used_when_the_new_one_is_corrupt() -> void:
	var s := fresh("user://test_saves/b")
	s.write("game", {"n": 1})
	s.write("game", {"n": 2})
	check(FileAccess.file_exists(s.path_of("game") + ".bak"), "backup kept")
	var f := FileAccess.open(s.path_of("game"), FileAccess.WRITE)
	f.store_string("{ this is not json")
	f.close()
	eq(s.read("game").get("data", {}).get("n"), 1, "falls back to the backup")
	s.erase("game")
	s.free()


func test_a_save_from_a_newer_build_is_refused_not_misread() -> void:
	var s := fresh("user://test_saves/c")
	eq(s.migrate({"format": SaveScript.FORMAT + 1, "data": {}}), {}, "newer format refused")
	eq(s.migrate({"format": SaveScript.FORMAT, "data": {"x": 1}})["data"], {"x": 1}, "current format accepted")
	eq(s.migrate({"format": 0, "data": {}}), {}, "an unknown old format without a migration is refused")
	s.free()


func test_unavailable_storage_never_crashes_and_the_session_keeps_its_save() -> void:
	# a regular file where the save folder should be: creating the folder must fail
	DirAccess.make_dir_recursive_absolute("user://test_saves")
	var blocker := FileAccess.open("user://test_saves/blocker", FileAccess.WRITE)
	blocker.store_string("not a folder")
	blocker.close()
	var s := fresh("user://test_saves/blocker/saves")
	var ok: bool = s.write("game", {"stage": "prologue"})
	eq(ok, false, "the write reports failure")
	eq(s.available, false, "storage marked unavailable")
	check(String(s.last_error) != "", "with a reason")
	eq(s.read("game").get("data", {}).get("stage"), "prologue", "the session still has its save")
	s.free()
	DirAccess.remove_absolute("user://test_saves/blocker")
