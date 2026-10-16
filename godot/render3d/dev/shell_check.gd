extends SceneTree
## Dev check of a shell's path into the sample (as godot/showcase does it): instantiate
## world3d/sample.tscn, give it `args` before it enters the tree, then drive it the way a shell does:
## a pad's left stick and D-pad, set_hours(), set_rain() and set_quality(). The container has no
## joypad device, so the pad is joypad events handed to Input for device 0 (Godot's own input path
## from the event on, not the OS's); with a real pad on Windows the same code reads the connected one.
##   (Xvfb) godot --path godot --rendering-method forward_plus --fixed-fps 30 \
##       -s res://render3d/dev/shell_check.gd -- --out=<dir>
## Prints PADCHECK / SHELLCHECK lines; saves the window at night, in the rain and at both qualities.

var sample: Node
var out := "."
var frame := 0
var marks := {}


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	var ps: PackedScene = load("res://world3d/sample.tscn")
	sample = ps.instantiate()
	sample.set("args", {"novista": "1", "gi": "none"})
	root.add_child(sample)


func _axis(axis: JoyAxis, v: float) -> void:
	var e := InputEventJoypadMotion.new()
	e.device = 0
	e.axis = axis
	e.axis_value = v
	Input.parse_input_event(e)


func _button(b: JoyButton, down: bool) -> void:
	var e := InputEventJoypadButton.new()
	e.device = 0
	e.button_index = b
	e.pressed = down
	Input.parse_input_event(e)


func _her() -> Vector3:
	return (sample.get("her") as Node).get("pos")


func _shot(name: String) -> void:
	var img := root.get_texture().get_image()
	img.save_png(out.path_join(name))
	print("SHELLCHECK saved %s %s" % [name, str(img.get_size())])


func _process(_dt: float) -> bool:
	frame += 1
	match frame:
		40:
			marks["a"] = _her()
			_axis(JOY_AXIS_LEFT_X, 1.0)              # full tilt east
		85:
			marks["b"] = _her()
			_axis(JOY_AXIS_LEFT_X, 0.0)
			print("PADCHECK stick east 1.5 s: moved x %+.2f z %+.2f" % [marks["b"].x - marks["a"].x, marks["b"].z - marks["a"].z])
		100:
			marks["c"] = _her()
			_axis(JOY_AXIS_LEFT_X, 0.15)             # inside the dead zone
		130:
			marks["d"] = _her()
			_axis(JOY_AXIS_LEFT_X, 0.0)
			print("PADCHECK dead zone (0.15) 1 s: moved %.3f" % (marks["d"] - marks["c"]).length())
			_axis(JOY_AXIS_LEFT_X, -0.45)            # a slight tilt west: a slow walk
		160:
			marks["e"] = _her()
			_axis(JOY_AXIS_LEFT_X, 0.0)
			print("PADCHECK half tilt west 1 s: moved x %+.2f" % (marks["e"].x - marks["d"].x))
			_button(JOY_BUTTON_DPAD_UP, true)
		190:
			marks["f"] = _her()
			_button(JOY_BUTTON_DPAD_UP, false)
			print("PADCHECK D-pad up 1 s: moved x %+.2f z %+.2f (north is -z)" % [marks["f"].x - marks["e"].x, marks["f"].z - marks["e"].z])
		205:
			sample.call("set_hours", 21.5, true)
			sample.call("set_rain", 0.0)
		230:
			print("SHELLCHECK hours %.2f rain %.2f" % [sample.get("env").get("hours"), sample.get("env").get("rain")])
			_shot("shell_2130.png")
			sample.call("set_hours", 14.0, true)
			sample.call("set_rain", 1.0)
		255:
			print("SHELLCHECK hours %.2f rain %.2f" % [sample.get("env").get("hours"), sample.get("env").get("rain")])
			_shot("shell_1400_rain.png")
			sample.call("set_hours", 37.5, false)  # wraps to 13.5, time passing
			sample.call("set_rain", 0.0)
		260:
			print("SHELLCHECK wrapped hours %.2f" % sample.get("env").get("hours"))
			_shot("shell_1330_q1.png")
			sample.call("set_quality", 0)
		285:
			_shot("shell_1330_q0.png")
			sample.call("set_quality", 1)
			print("SHELLCHECK quality 0 then 1")
		290:
			return true
	return false
