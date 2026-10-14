extends Node
## GameState (autoload): settings, story flags and the live session the other layers share.
## Settings that wait on the user's decisions are switches here, never hard-coded elsewhere:
##   control_scheme  "explicit" = approved scheme A (D13): 1-5 take, Shift+1-5 give, L then 1-5
##                    release; touch tap = take, swipe up = give, swipe down = release.
##                   "obvious"  = the prototype's one key does the obvious thing (pending,
##                    docs/design/body-effects-draft.md): 1-5 obvious, Shift+1-5 reverse;
##                    touch tap = obvious, long press = reverse.
##   font_theme      "pixel" (Fusion Pixel 12px) or "vector" (Noto Serif SC), pending.
##   body_profile    a BodyRules profile: "draft" (pending) or "legacy" (the JS segment 1 body).
##   touch_ui        "auto" (on for phones and after a real touch), "on", "off".
## Settings persist through Save ("settings" slot); flags are part of the game save.

signal settings_changed(key: String, value)
signal flag_changed(key: String, value)

const DEFAULT_SETTINGS := {
	"control_scheme": "explicit",
	"font_theme": "pixel",
	"body_profile": "draft",
	"touch_ui": "auto",
	"long_press_s": 0.34,
	"swipe_px": 14.0,
	"vol_master": 1.0,
	"vol_music": 0.8,
	"vol_ambience": 0.8,
	"vol_sfx": 0.9,
	"vol_voice": 0.9,
}

var settings: Dictionary = DEFAULT_SETTINGS.duplicate()
var flags: Dictionary = {}
var body_rules: BodyRules
var touch_seen := false   # a real (not mouse-emulated) touch has happened
## The live session, set by the game scene (read by the HUD, the debug bridge, saves).
var field: Field = null
var region: RegionData = null
var director: Director = null


func _ready() -> void:
	body_rules = load("res://systems/body_rules.tres") as BodyRules
	var saved: Dictionary = Save.read("settings")
	for k in saved.get("data", {}):
		if DEFAULT_SETTINGS.has(k):
			settings[k] = saved["data"][k]
	_apply_cmdline()


## Command-line overrides for checking (after "--"): --scheme=explicit|obvious,
## --font=pixel|vector, --body=draft|legacy, --touch-ui=on|off|auto.
func _apply_cmdline() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		if kv.size() != 2:
			continue
		match kv[0]:
			"scheme":
				settings["control_scheme"] = kv[1]
			"font":
				settings["font_theme"] = kv[1]
			"body":
				settings["body_profile"] = kv[1]
			"touch-ui":
				settings["touch_ui"] = kv[1]


func setting(key: String):
	return settings.get(key, DEFAULT_SETTINGS.get(key))


func set_setting(key: String, value) -> void:
	if settings.get(key) == value:
		return
	settings[key] = value
	Save.write("settings", settings)
	settings_changed.emit(key, value)


func body_profile() -> Dictionary:
	return body_rules.profile(String(setting("body_profile")))


func flag(key: String, default = null):
	return flags.get(key, default)


func set_flag(key: String, value) -> void:
	flags[key] = value
	flag_changed.emit(key, value)


## Whether the touch controls are shown.
func touch_ui_on() -> bool:
	match String(setting("touch_ui")):
		"on":
			return true
		"off":
			return false
	return touch_seen or OS.has_feature("mobile")
