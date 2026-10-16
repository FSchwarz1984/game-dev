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
##   reduce_motion   减少晃动 (docs/design/dialogue-staging.md D6): no shaking, hopping or flashing in dialogue; off
##                    by default.
## Settings persist through Save ("settings" slot); flags are part of the game save.

signal settings_changed(key: String, value)
signal flag_changed(key: String, value)

const DEFAULT_SETTINGS := {
	"control_scheme": "explicit",
	"font_theme": "pixel",
	"body_profile": "draft",
	"touch_ui": "auto",
	"reduce_motion": false,
	"long_press_s": 0.34,
	"swipe_px": 14.0,
	"vol_master": 1.0,
	"vol_music": 0.8,
	"vol_ambience": 0.8,
	"vol_sfx": 0.9,
	"vol_voice": 0.9,
}

var settings: Dictionary = DEFAULT_SETTINGS.duplicate()
var overrides: Dictionary = {}   # from the command line: in force for this run, never saved
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
## --font=pixel|vector, --body=draft|legacy, --touch-ui=on|off|auto, --reduce-motion=on|off. Not saved.
func _apply_cmdline() -> void:
	var names := {"scheme": "control_scheme", "font": "font_theme", "body": "body_profile", "touch-ui": "touch_ui",
		"reduce-motion": "reduce_motion"}
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		if kv.size() == 2 and names.has(kv[0]):
			overrides[names[kv[0]]] = kv[1]


func setting(key: String):
	if overrides.has(key):
		return overrides[key]
	return settings.get(key, DEFAULT_SETTINGS.get(key))


## A choice made in the game (or a debug key): it replaces any command-line override and is saved.
func set_setting(key: String, value) -> void:
	if setting(key) == value:
		return
	overrides.erase(key)
	settings[key] = value
	Save.write("settings", settings)
	settings_changed.emit(key, value)


## 减少晃动: the setting as a bool (a command-line override is a string: on / 1 / true).
func reduce_motion() -> bool:
	var v: Variant = setting("reduce_motion")
	if v is bool:
		return v
	return String(v).to_lower() in ["on", "1", "true", "yes"]


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
