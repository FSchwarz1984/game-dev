extends SceneTree
## Headless unit-test runner:
##   godot --headless --path godot -s res://tests/run.gd                 every tests/test_*.gd
##   godot --headless --path godot -s res://tests/run.gd -- --only=field  files whose name contains it
## (tools/godot/test.sh imports the project first, then runs this.) Prints one line per test and a
## summary; the exit code is 1 when anything failed. Tests are TestCase subclasses; each test_*
## method may await. GDScript has no exceptions, so a Logger catches every engine or script error
## printed while a test runs, and such a test fails even if its checks passed. Autoloads are loaded
## in this mode, so they must stay headless-safe.


class ErrorLog:
	extends Logger
	var mutex := Mutex.new()
	var errors: Array[String] = []

	func _log_error(function: String, file: String, line: int, code: String, rationale: String, _notify: bool, error_type: int, _bt: Array[ScriptBacktrace]) -> void:
		if error_type == ERROR_TYPE_WARNING:
			return
		mutex.lock()
		errors.append("%s (%s:%d %s)" % [rationale if rationale != "" else code, file.get_file(), line, function])
		mutex.unlock()

	func _log_message(_message: String, _error: bool) -> void:
		pass

	func count() -> int:
		mutex.lock()
		var n := errors.size()
		mutex.unlock()
		return n

	func since(n: int) -> Array[String]:
		mutex.lock()
		var out := errors.slice(n)
		mutex.unlock()
		return out


func _initialize() -> void:
	# a hard stop in case a test never finishes (an await that is never resumed)
	create_timer(600.0).timeout.connect(func() -> void:
		print("tests: TIMEOUT after 600 s")
		quit(1))
	_main.call_deferred()


func _main() -> void:
	var log := ErrorLog.new()
	OS.add_logger(log)
	var only := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			only = a.substr(7)
	var files: Array = []
	for f in DirAccess.get_files_at("res://tests/"):
		if f.begins_with("test_") and f.ends_with(".gd") and f != "test_case.gd" and (only == "" or f.contains(only)):
			files.append(f)
	files.sort()
	var passed := 0
	var failed := 0
	var checks := 0
	var t0 := Time.get_ticks_msec()
	for f in files:
		var before := log.count()
		var script := load("res://tests/" + f) as GDScript
		if script == null or not script.can_instantiate():
			print("FAIL %s: does not compile" % f)
			for msg in log.since(before):
				print("     - %s" % msg)
			failed += 1
			continue
		var names: Array = []
		for m in script.get_script_method_list():
			var n := String(m["name"])
			if n.begins_with("test_") and not names.has(n):
				names.append(n)
		for n in names:
			var tc = script.new()
			tc.current = "%s::%s" % [f.get_basename(), n]
			var err0 := log.count()
			var r = tc.call(n)
			if r is Object and r != null and r.get_class() == "GDScriptFunctionState":
				await r.completed
			checks += tc.checks
			var errs := log.since(err0)
			if tc.failures.is_empty() and errs.is_empty():
				passed += 1
				print("ok   %s" % tc.current)
			else:
				failed += 1
				print("FAIL %s" % tc.current)
				for msg in tc.failures:
					print("     - %s" % msg)
				for msg in errs:
					print("     - error: %s" % msg)
	print("tests: %d passed, %d failed, %d checks, %d ms" % [passed, failed, checks, Time.get_ticks_msec() - t0])
	quit.call_deferred(1 if failed > 0 else 0)  # first, so a failing cleanup cannot hang the run
	# drop static caches so nothing outlives the engine (loaded by path: this script is compiled
	# before the autoloads exist, so it must not name classes that use them)
	for path in ["res://actors/character_library.gd", "res://ui/ui_theme.gd", "res://story/staging.gd"]:
		var s = load(path)
		if s != null and s.has_method("clear"):
			s.clear()
