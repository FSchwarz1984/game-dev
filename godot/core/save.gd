extends Node
## Save (autoload): JSON envelopes under user://saves/<slot>.json, versioned and migrated.
##   Save.write("game", {...}) -> bool      Save.read("game") -> {"format", "saved_unix", "data"} or {}
## Writes go to <slot>.json.tmp first, the old file is kept as <slot>.json.bak, then the new one
## replaces it, so a crash mid-write never loses the last good save.
## Storage may be missing (a phone with no space, a read-only folder, a sandbox): every failure is
## caught, `available` turns false, `last_error` says why, and the session keeps its saves in memory.
## Nothing here may stop the game.

const FORMAT := 1
const GAME := "tengan"

## Migrations from format N to N+1, applied in order on read: MIGRATIONS[N] = Callable(env) -> env.
## (Format 1 is the first; add an entry here whenever the save shape changes.)
const MIGRATIONS := {}

var root := "user://saves"
var available := true
var last_error := ""
var _memory: Dictionary = {}


## "-- --save-root=<dir>" sends every save elsewhere (the playtest bot isolates its runs this way, so
## a checking run never changes the player's settings or saves).
func _init() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--save-root="):
			root = a.substr(12)


func path_of(slot: String) -> String:
	return root.path_join(slot + ".json")


func _ensure_dir() -> bool:
	if DirAccess.dir_exists_absolute(root):
		return true
	# a file where a folder should be (or similar): fail quietly instead of asking the OS to try
	var i := root.find("/", root.find("://") + 3 if root.contains("://") else 1)
	while i > 0:
		var prefix := root.substr(0, i)
		if FileAccess.file_exists(prefix):
			_fail("cannot create %s: %s is a file" % [root, prefix])
			return false
		i = root.find("/", i + 1)
	if FileAccess.file_exists(root):
		_fail("cannot create %s: it is a file" % root)
		return false
	var err := DirAccess.make_dir_recursive_absolute(root)
	if err != OK:
		_fail("cannot create %s: %s" % [root, error_string(err)])
		return false
	return true


func _fail(why: String) -> void:
	available = false
	last_error = why
	push_warning("Save: " + why)


func write(slot: String, data: Dictionary) -> bool:
	var env := {"format": FORMAT, "game": GAME, "slot": slot, "saved_unix": Time.get_unix_time_from_system(), "data": data}
	_memory[slot] = env.duplicate(true)
	if not _ensure_dir():
		return false
	var path := path_of(slot)
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		_fail("cannot write %s: %s" % [tmp, error_string(FileAccess.get_open_error())])
		return false
	f.store_string(JSON.stringify(env, "\t"))
	var werr := f.get_error()
	f.close()
	if werr != OK:
		_fail("write error on %s: %s" % [tmp, error_string(werr)])
		return false
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(path + ".bak")
		DirAccess.rename_absolute(path, path + ".bak")
	var err := DirAccess.rename_absolute(tmp, path)
	if err != OK:
		_fail("cannot replace %s: %s" % [path, error_string(err)])
		return false
	available = true
	last_error = ""
	return true


## The envelope of a slot, migrated to the current format; {} when there is none or it is unreadable.
func read(slot: String) -> Dictionary:
	var path := path_of(slot)
	for p in [path, path + ".bak"]:
		if not FileAccess.file_exists(p):
			continue
		var env := _parse(FileAccess.get_file_as_string(p))
		if not env.is_empty():
			return env
		push_warning("Save: %s is unreadable, trying the backup" % p)
	return _memory.get(slot, {}).duplicate(true)


func _parse(text: String) -> Dictionary:
	if text.is_empty():
		return {}
	var json := JSON.new()  # the instance API reports errors without printing them
	if json.parse(text) != OK:
		return {}
	var parsed = json.data
	if not (parsed is Dictionary) or not parsed.has("data"):
		return {}
	return migrate(parsed)


## Brings an envelope up to FORMAT; a save from a newer build is refused (empty), never misread.
func migrate(env: Dictionary) -> Dictionary:
	var v := int(env.get("format", 0))
	if v > FORMAT:
		push_warning("Save: format %d is newer than this build (%d)" % [v, FORMAT])
		return {}
	while v < FORMAT:
		if not MIGRATIONS.has(v):
			push_warning("Save: no migration from format %d" % v)
			return {}
		env = (MIGRATIONS[v] as Callable).call(env)
		v += 1
		env["format"] = v
	return env


func erase(slot: String) -> void:
	_memory.erase(slot)
	for p in [path_of(slot), path_of(slot) + ".bak"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(p)
