# Writes the engine's own licence and third-party notices (Engine.get_license_text, get_copyright_info,
# get_license_info) into <out_dir>: godot --headless -s tools/godot/dump_licenses.gd -- <out_dir>
extends SceneTree

func _init() -> void:
	var out := OS.get_cmdline_user_args()[0]
	var f := FileAccess.open(out + "/GODOT_LICENSE.txt", FileAccess.WRITE)
	f.store_string(Engine.get_license_text())
	f.close()
	var t := "Godot Engine third-party components (Engine.get_copyright_info / get_license_info)\n\n"
	for c in Engine.get_copyright_info():
		t += "- %s\n" % c["name"]
		for p in c["parts"]:
			t += "    files: %s\n    copyright: %s\n    license: %s\n" % [", ".join(p["files"]), "; ".join(p["copyright"]), p["license"]]
		t += "\n"
	t += "\n\nLicense texts\n=============\n\n"
	var li := Engine.get_license_info()
	for k in li:
		t += "----- %s -----\n\n%s\n\n" % [k, li[k]]
	f = FileAccess.open(out + "/GODOT_THIRDPARTY.txt", FileAccess.WRITE)
	f.store_string(t)
	f.close()
	print("LICENSES_OK")
	quit()
