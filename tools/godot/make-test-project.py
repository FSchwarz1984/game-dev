#!/usr/bin/env python3
# Writes the Godot toolchain test project (not game content) into a directory:
#   python3 -I tools/godot/make-test-project.py <project_dir> [--noto <dir with Sans/SubsetOTF>]
# The project checks what the web build must do for this game: 480x270 viewport stretched by
# integer steps, a Sprite2D with a CanvasTexture (diffuse + normal map) lit by a PointLight2D and a
# DirectionalLight2D with shadows from LightOccluder2D, a TileMapLayer, CJK text with line wrapping
# (including a kinsoku report for the active text server), keyboard and touch input moving the
# sprite, and an OGG blip on input. main.gd prints BOOT_OK / FIRST_FRAME / FPS / EVT / WRAP lines
# that tools/godot/webtest.mjs reads from the browser console.
# Needs Pillow, fontTools (pip install fonttools) and ffmpeg with libvorbis. Noto Sans CJK (OFL) is
# taken from --noto, or sparse-cloned from github.com/notofonts/noto-cjk into
# $GODOT_HOME/fonts/noto-cjk (two subset OTFs, about 13 MB).
# Run it with python3 -I: it reads downloaded font files.

import math
import os
import random
import subprocess
import sys

from PIL import Image

TEST_TITLE = "天岸 Godot web test"  # 天岸

# All on-screen strings live in main.gd; the font subsets are cut to exactly these characters.
MAIN_GD = r'''extends Node2D
# Toolchain test scene (see tools/godot/make-test-project.py). Prints machine-readable lines:
#   BOOT_OK, FIRST_FRAME, FPS, EVT, WRAP, WRAPLINES  (read by tools/godot/webtest.mjs)

const SPEED := 80.0
const ZWSP := "​"
# Kinsoku: characters that must not start a line, and ones that must not end a line.
const NO_LINE_START := "、。，．・：；？！ー）」』】〕〉》｝ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ々ゝゞ…‥"
const NO_LINE_END := "（「『【〔〈《｛"
const JA_SAMPLE := "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。「百々つゞみ」「家守さぢ」「垣外しをね」――ゝゞヽヾ々っゃゅょ。"
const ZH_SAMPLE := "床前明月光，疑是地上霜。举头望明月，低头思故乡。这些字们说：取、予、放；重・熱・光・音・生。"

@onready var hero: Sprite2D = $Hero
@onready var ground: TileMapLayer = $Ground
@onready var blip: AudioStreamPlayer = $Blip
@onready var dbg: Label = $UI/Debug

var _first_frame := true
var _fps_t := 0.0
var _last := "none"
var _target = null
var _keys := 0
var _touches := 0
var _drags := 0


func _ready() -> void:
	for a in [["ui_left", KEY_A], ["ui_right", KEY_D], ["ui_up", KEY_W], ["ui_down", KEY_S]]:
		var ev := InputEventKey.new()
		ev.physical_keycode = a[1]
		InputMap.action_add_event(a[0], ev)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for y in range(-2, 24):
		for x in range(-2, 44):
			var t := 0
			var r := rng.randf()
			if r < 0.12:
				t = 3
			elif r < 0.2:
				t = 2
			if y == 12 or y == 13:
				t = 1
			ground.set_cell(Vector2i(x, y), 0, Vector2i(t, 0))
	$UI/Title.text = "天岸 Godot %s web test  百々つゞみ・家守さぢ・垣外しをね" % Engine.get_version_info().string
	$UI/WrapSmart.text = JA_SAMPLE
	$UI/WrapArbitrary.text = JA_SAMPLE
	$UI/WrapKinsoku.text = kinsoku_zwsp(JA_SAMPLE)
	$UI/Zh.text = ZH_SAMPLE
	var ts := TextServerManager.get_primary_interface()
	print("BOOT_OK ticks=%d text_server=%s viewport=%s window=%s" % [Time.get_ticks_msec(), ts.get_name(), get_viewport().get_visible_rect().size, DisplayServer.window_get_size()])
	_wrap_report()


func _process(delta: float) -> void:
	if _first_frame:
		_first_frame = false
		print("FIRST_FRAME ticks=%d" % Time.get_ticks_msec())
	var dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if dir != Vector2.ZERO:
		_target = null
	hero.position += dir * SPEED * delta
	if _target != null:
		hero.position = hero.position.move_toward(_target, SPEED * delta)
		if hero.position.distance_to(_target) < 0.5:
			_target = null
	_fps_t += delta
	if _fps_t >= 1.0:
		_fps_t = 0.0
		print("FPS %d pos=%d,%d keys=%d touches=%d drags=%d" % [Engine.get_frames_per_second(), hero.position.x, hero.position.y, _keys, _touches, _drags])
	dbg.text = "fps %d  pos %d,%d  %s" % [Engine.get_frames_per_second(), hero.position.x, hero.position.y, _last]


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		_keys += 1
		_last = "key %s" % OS.get_keycode_string(event.keycode)
		blip.play()
		print("EVT key %s pos=%d,%d" % [OS.get_keycode_string(event.keycode), hero.position.x, hero.position.y])
	elif event is InputEventScreenTouch:
		_touches += 1
		_last = "touch %d,%d" % [event.position.x, event.position.y]
		if event.pressed:
			_target = event.position
			blip.play()
		print("EVT touch index=%d pressed=%s at=%d,%d" % [event.index, event.pressed, event.position.x, event.position.y])
	elif event is InputEventScreenDrag:
		_drags += 1
		_target = null
		hero.position += event.relative
		_last = "drag %d,%d" % [event.position.x, event.position.y]
		if _drags % 5 == 1:
			print("EVT drag at=%d,%d rel=%.1f,%.1f hero=%d,%d" % [event.position.x, event.position.y, event.relative.x, event.relative.y, hero.position.x, hero.position.y])
	elif event is InputEventMouseButton and event.pressed:
		print("EVT mouse button=%d at=%d,%d" % [event.button_index, event.position.x, event.position.y])


# Inserts U+200B where CJK text may break, except before a no-line-start character or after a
# no-line-end one. Fallback text server breaks only at whitespace (U+200B counts as whitespace).
static func kinsoku_zwsp(s: String) -> String:
	var out := ""
	for i in s.length():
		var c := s[i]
		out += c
		if i + 1 < s.length():
			var n := s[i + 1]
			if (c.unicode_at(0) >= 0x3000 or n.unicode_at(0) >= 0x3000) and not NO_LINE_START.contains(n) and not NO_LINE_END.contains(c):
				out += ZWSP
	return out


# For each wrap mode, wraps JA_SAMPLE at 31 widths and counts lines that overflow the width or
# break a kinsoku rule, using the active text server exactly as Label does.
func _wrap_report() -> void:
	var ts := TextServerManager.get_primary_interface()
	var font: Font = $UI/WrapSmart.get_theme_font("font")
	var trim := TextServer.BREAK_TRIM_START_EDGE_SPACES | TextServer.BREAK_TRIM_END_EDGE_SPACES
	var modes := [
		["word", TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND],
		["smart", TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE],
		["arbitrary", TextServer.BREAK_MANDATORY | TextServer.BREAK_GRAPHEME_BOUND],
	]
	for prep in ["raw", "zwsp"]:
		var text: String = JA_SAMPLE if prep == "raw" else kinsoku_zwsp(JA_SAMPLE)
		var rid := ts.create_shaped_text()
		ts.shaped_text_add_string(rid, text, font.get_rids(), 12, {}, "ja")
		for m in modes:
			var lines := 0
			var overflow := 0
			var bad_start := 0
			var bad_end := 0
			var sample := ""
			for w in range(60, 241, 6):
				var brk := ts.shaped_text_get_line_breaks(rid, w, 0, m[1] | trim)
				var parts := []
				for i in range(0, brk.size(), 2):
					var s := text.substr(brk[i], brk[i + 1] - brk[i]).replace(ZWSP, "")
					var sub := ts.shaped_text_substr(rid, brk[i], brk[i + 1] - brk[i])
					var lw := ts.shaped_text_get_width(sub)
					ts.free_rid(sub)
					lines += 1
					if lw > w + 0.5:
						overflow += 1
					if i > 0 and s.length() > 0 and NO_LINE_START.contains(s[0]):
						bad_start += 1
					if i + 2 < brk.size() and s.length() > 0 and NO_LINE_END.contains(s[s.length() - 1]):
						bad_end += 1
					parts.append(s)
				if w == 150:
					sample = " | ".join(parts)
			print("WRAP server=%s mode=%s prep=%s lines=%d overflow=%d bad_line_start=%d bad_line_end=%d" % [ts.get_name(), m[0], prep, lines, overflow, bad_start, bad_end])
			print("WRAPLINES mode=%s prep=%s w=150: %s" % [m[0], prep, sample])
		ts.free_rid(rid)
'''

MAIN_TSCN = '''[gd_scene format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]
[ext_resource type="Texture2D" path="res://sprites/hero.png" id="2"]
[ext_resource type="Texture2D" path="res://sprites/hero_n.png" id="3"]
[ext_resource type="Texture2D" path="res://tiles/tiles.png" id="4"]
[ext_resource type="Texture2D" path="res://tiles/tiles_n.png" id="5"]
[ext_resource type="Texture2D" path="res://sprites/pillar.png" id="6"]
[ext_resource type="Texture2D" path="res://sprites/pillar_n.png" id="7"]
[ext_resource type="AudioStream" path="res://sfx/blip.ogg" id="8"]

[sub_resource type="CanvasTexture" id="hero_tex"]
diffuse_texture = ExtResource("2")
normal_texture = ExtResource("3")

[sub_resource type="CanvasTexture" id="pillar_tex"]
diffuse_texture = ExtResource("6")
normal_texture = ExtResource("7")

[sub_resource type="CanvasTexture" id="tiles_tex"]
diffuse_texture = ExtResource("4")
normal_texture = ExtResource("5")

[sub_resource type="TileSetAtlasSource" id="atlas"]
texture = SubResource("tiles_tex")
texture_region_size = Vector2i(16, 16)
0:0/0 = 0
1:0/0 = 0
2:0/0 = 0
3:0/0 = 0

[sub_resource type="TileSet" id="tileset"]
sources/0 = SubResource("atlas")

[sub_resource type="Gradient" id="grad"]
offsets = PackedFloat32Array(0, 0.35, 1)
colors = PackedColorArray(1, 1, 1, 1, 1, 1, 1, 0.55, 1, 1, 1, 0)

[sub_resource type="GradientTexture2D" id="light_tex"]
gradient = SubResource("grad")
width = 256
height = 256
fill = 1
fill_from = Vector2(0.5, 0.5)
fill_to = Vector2(1, 0.5)

[sub_resource type="OccluderPolygon2D" id="pillar_occ"]
polygon = PackedVector2Array(-7, -4, 7, -4, 7, 4, -7, 4)

[sub_resource type="OccluderPolygon2D" id="hero_occ"]
polygon = PackedVector2Array(-6, 10, 6, 10, 6, 15, -6, 15)

[node name="Main" type="Node2D"]
script = ExtResource("1")

[node name="Ambient" type="CanvasModulate" parent="."]
color = Color(0.42, 0.45, 0.6, 1)

[node name="Ground" type="TileMapLayer" parent="."]
tile_set = SubResource("tileset")

[node name="Pillar" type="Sprite2D" parent="."]
position = Vector2(170, 214)
texture = SubResource("pillar_tex")
offset = Vector2(0, -16)

[node name="Occluder" type="LightOccluder2D" parent="Pillar"]
occluder = SubResource("pillar_occ")

[node name="Hero" type="Sprite2D" parent="."]
position = Vector2(240, 200)
texture = SubResource("hero_tex")

[node name="Occluder" type="LightOccluder2D" parent="Hero"]
occluder = SubResource("hero_occ")

[node name="Sun" type="DirectionalLight2D" parent="."]
rotation = -0.7
color = Color(1, 0.93, 0.8, 1)
energy = 0.55
height = 0.45
shadow_enabled = true
shadow_color = Color(0, 0, 0, 0.55)
max_distance = 600.0

[node name="Lamp" type="PointLight2D" parent="."]
position = Vector2(205, 228)
color = Color(1, 0.72, 0.38, 1)
energy = 1.6
shadow_enabled = true
texture = SubResource("light_tex")
texture_scale = 0.75
height = 18.0

[node name="Blip" type="AudioStreamPlayer" parent="."]
stream = ExtResource("8")

[node name="UI" type="CanvasLayer" parent="."]

[node name="Panel" type="ColorRect" parent="UI"]
offset_left = 2.0
offset_top = 2.0
offset_right = 478.0
offset_bottom = 150.0
mouse_filter = 2
color = Color(0.05, 0.05, 0.08, 0.72)

[node name="Title" type="Label" parent="UI"]
offset_left = 6.0
offset_top = 3.0
offset_right = 476.0
offset_bottom = 19.0
theme_override_font_sizes/font_size = 12

[node name="WrapSmart" type="Label" parent="UI"]
offset_left = 6.0
offset_top = 20.0
offset_right = 156.0
offset_bottom = 124.0
theme_override_font_sizes/font_size = 12
autowrap_mode = 3
clip_text = true

[node name="WrapArbitrary" type="Label" parent="UI"]
offset_left = 164.0
offset_top = 20.0
offset_right = 314.0
offset_bottom = 124.0
theme_override_font_sizes/font_size = 12
autowrap_mode = 1
clip_text = true

[node name="WrapKinsoku" type="Label" parent="UI"]
offset_left = 322.0
offset_top = 20.0
offset_right = 472.0
offset_bottom = 124.0
theme_override_font_sizes/font_size = 12
autowrap_mode = 2
clip_text = true

[node name="Zh" type="Label" parent="UI"]
offset_left = 6.0
offset_top = 126.0
offset_right = 476.0
offset_bottom = 148.0
theme_override_font_sizes/font_size = 12
autowrap_mode = 3

[node name="Debug" type="Label" parent="UI"]
offset_left = 4.0
offset_top = 254.0
offset_right = 476.0
offset_bottom = 268.0
theme_override_font_sizes/font_size = 10
'''

PROJECT_GODOT = '''; Generated by tools/godot/make-test-project.py (toolchain test, not game content).
config_version=5

[application]

config/name="GodotWebToolchainTest"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")
boot_splash/show_image=false
boot_splash/bg_color=Color(0.07, 0.07, 0.09, 1)

[audio]

general/default_playback_type.web=1

[display]

window/size/viewport_width=480
window/size/viewport_height=270
window/stretch/mode="viewport"
window/stretch/aspect="expand"
window/stretch/scale_mode="integer"

[gui]

theme/custom_font="res://fonts/cjk_jp.otf"

[internationalization]

locale/include_text_server_data=false

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/canvas_textures/default_texture_filter=0
2d/snap/snap_2d_transforms_to_pixel=true
environment/defaults/default_clear_color=Color(0.1, 0.1, 0.12, 1)
'''

# Body-only HTML shell: the delivery host wraps the page body in its own <html><head>, so nothing
# here may rely on <head>. Same boot logic as Godot's misc/dist/html/full-size.html, minus the
# service-worker branch (PWA is off and the host forbids service workers). Pure ASCII.
BODY_SHELL = '''<style>
html, body, #canvas { margin: 0; padding: 0; border: 0; }
body { color: white; background-color: black; overflow: hidden; touch-action: none; }
#canvas { display: block; }
#canvas:focus { outline: none; }
#status, #status-progress { position: absolute; left: 0; right: 0; }
#status { top: 0; bottom: 0; background-color: $GODOT_SPLASH_COLOR; display: flex;
  flex-direction: column; justify-content: center; align-items: center; visibility: hidden; }
#status-progress, #status-notice { display: none; }
#status-progress { bottom: 10%; width: 50%; margin: 0 auto; }
#status-notice { background-color: #5b3943; border-radius: 0.5rem; border: 1px solid #9b3943;
  color: #e0e0e0; font-family: sans-serif; line-height: 1.3; margin: 0 2rem; padding: 1rem;
  text-align: center; z-index: 1; }
</style>
<canvas id="canvas">Your browser does not support the canvas tag.</canvas>
<div id="status">
  <progress id="status-progress"></progress>
  <div id="status-notice"></div>
</div>
<script src="$GODOT_URL"></script>
<script>
(function () {
  const GODOT_CONFIG = $GODOT_CONFIG;
  const GODOT_THREADS_ENABLED = $GODOT_THREADS_ENABLED;
  const engine = new Engine(GODOT_CONFIG);
  const statusOverlay = document.getElementById('status');
  const statusProgress = document.getElementById('status-progress');
  const statusNotice = document.getElementById('status-notice');
  let initializing = true;
  function setStatusMode(mode) {
    if (!initializing) { return; }
    if (mode === 'hidden') { statusOverlay.remove(); initializing = false; return; }
    statusOverlay.style.visibility = 'visible';
    statusProgress.style.display = mode === 'progress' ? 'block' : 'none';
    statusNotice.style.display = mode === 'notice' ? 'block' : 'none';
  }
  function fail(err) {
    console.error(err);
    statusNotice.textContent = (err && err.message) ? err.message : String(err);
    setStatusMode('notice');
    initializing = false;
  }
  const missing = Engine.getMissingFeatures({ threads: GODOT_THREADS_ENABLED });
  if (missing.length !== 0) {
    fail('Missing browser features: ' + missing.join(', '));
    return;
  }
  setStatusMode('progress');
  engine.startGame({
    'onProgress': function (current, total) {
      if (current > 0 && total > 0) { statusProgress.value = current; statusProgress.max = total; }
    },
  }).then(function () { setStatusMode('hidden'); }, fail);
}());
</script>
'''

EXPORT_PRESETS = '''[preset.0]

name="Web"
platform="Web"
runnable=true
advanced_options=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="export/index.html"
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug="@TEMPLATE_DEBUG@"
custom_template/release="@TEMPLATE_RELEASE@"
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=false
vram_texture_compression/for_mobile=false
html/export_icon=false
html/custom_html_shell="res://shell/body.html"
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
'''


def lerp(a, b, t):
    return a + (b - a) * t


def normal_map(alpha, k, extra=None):
    """Normal map (OpenGL convention, +Y up) from a height field: blurred alpha (+ extra)."""
    w, h = len(alpha[0]), len(alpha)
    hf = [[0.0] * w for _ in range(h)]
    r = 3
    for y in range(h):
        for x in range(w):
            s, n = 0.0, 0
            for yy in range(y - r, y + r + 1):
                for xx in range(x - r, x + r + 1):
                    if 0 <= xx < w and 0 <= yy < h:
                        s += alpha[yy][xx]
                    n += 1
            hf[y][x] = s / n + (extra[y][x] if extra else 0.0)
    img = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w):
            dx = hf[y][min(x + 1, w - 1)] - hf[y][max(x - 1, 0)]
            dy = hf[min(y + 1, h - 1)][x] - hf[max(y - 1, 0)][x]
            nx, ny, nz = -dx * k, dy * k, 1.0
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            nx, ny, nz = nx / ln, ny / ln, nz / ln
            a = 255 if alpha[y][x] > 0 else 0
            img.putpixel((x, y), (int((nx * 0.5 + 0.5) * 255), int((ny * 0.5 + 0.5) * 255), int((nz * 0.5 + 0.5) * 255), a))
    return img


def make_hero(path, npath):
    w, h = 20, 32
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    alpha = [[0.0] * w for _ in range(h)]
    cloak = (88, 104, 122)
    cloak_d = (58, 68, 84)
    skin = (236, 196, 160)
    hair = (52, 40, 44)
    outline = (28, 26, 34)
    for y in range(h):
        for x in range(w):
            cx = x - 9.5
            inside = None
            if 2 <= y <= 13 and (cx * cx) / 36.0 + ((y - 8) ** 2) / 36.0 <= 1.0:
                inside = hair if (y < 8 or abs(cx) > 3.5) else skin
            elif 13 < y <= 30:
                half = lerp(4.0, 8.5, (y - 13) / 17.0)
                if abs(cx) <= half:
                    inside = cloak if cx < 1 else cloak_d
            if inside:
                img.putpixel((x, y), inside + (255,))
                alpha[y][x] = 1.0
    for y in range(h):
        for x in range(w):
            if alpha[y][x] == 0 and any(0 <= x + dx < w and 0 <= y + dy < h and alpha[y + dy][x + dx] > 0
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                img.putpixel((x, y), outline + (255,))
    for x, y in ((7, 9), (12, 9)):
        img.putpixel((x, y), outline + (255,))
    for y in range(h):
        for x in range(w):
            if img.getpixel((x, y))[3]:
                alpha[y][x] = 1.0
    img.save(path)
    normal_map(alpha, 2.2).save(npath)


def make_pillar(path, npath):
    w, h = 16, 40
    rnd = random.Random(3)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    alpha = [[0.0] * w for _ in range(h)]
    bump = [[0.0] * w for _ in range(h)]
    for y in range(2, h):
        for x in range(1, w - 1):
            top = y < 8
            if top and not (2 <= x <= 13):
                continue
            v = 120 + rnd.randint(-14, 14) - (8 if x > 9 else 0)
            if y % 9 == 0:
                v -= 30
                bump[y][x] = -0.4
            img.putpixel((x, y), (v, v + 4, v - 6, 255))
            alpha[y][x] = 1.0
    img.save(path)
    normal_map(alpha, 1.6, bump).save(npath)


def make_tiles(path, npath):
    rnd = random.Random(11)
    img = Image.new("RGBA", (64, 16))
    height = [[0.0] * 64 for _ in range(16)]
    for t in range(4):
        for y in range(16):
            for x in range(16):
                X = t * 16 + x
                n = rnd.random()
                if t in (0, 3):  # grass (3: with flowers)
                    c = (78, 98, 52) if n > 0.25 else (66, 84, 44)
                    if n > 0.9:
                        c = (98, 118, 62)
                        height[y][X] = 0.5
                elif t == 1:  # dirt path
                    c = (120, 96, 68) if n > 0.2 else (104, 82, 58)
                    if n > 0.94:
                        c = (150, 138, 120)
                        height[y][X] = 0.8
                else:  # stones
                    c = (104, 106, 98) if (x // 5 + y // 4) % 2 else (92, 94, 88)
                    if x % 5 == 0 or y % 4 == 0:
                        c = (66, 68, 64)
                        height[y][X] = -0.6
                img.putpixel((X, y), c + (255,))
        if t == 3:
            for _ in range(5):
                fx, fy = rnd.randint(2, 13), rnd.randint(2, 13)
                img.putpixel((t * 16 + fx, fy), (220, 200, 120, 255))
                height[fy][t * 16 + fx] = 1.0
    img.save(path)
    nimg = Image.new("RGBA", (64, 16))
    for y in range(16):
        for x in range(64):
            dx = height[y][min(x + 1, 63)] - height[y][max(x - 1, 0)]
            dy = height[min(y + 1, 15)][x] - height[max(y - 1, 0)][x]
            nx, ny, nz = -dx * 0.8, dy * 0.8, 1.0
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            nimg.putpixel((x, y), (int((nx / ln * 0.5 + 0.5) * 255), int((ny / ln * 0.5 + 0.5) * 255), int((nz / ln * 0.5 + 0.5) * 255), 255))
    nimg.save(npath)


def fetch_noto(dest):
    if os.path.exists(os.path.join(dest, "Sans/SubsetOTF/JP/NotoSansJP-Regular.otf")):
        return dest
    subprocess.check_call(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                           "https://github.com/notofonts/noto-cjk", dest])
    subprocess.check_call(["git", "-C", dest, "sparse-checkout", "set", "--no-cone",
                           "/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf",
                           "/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf", "/Sans/LICENSE"])
    return dest


def subset_font(src, dst, text):
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]  # keep locl/vert/kern etc. for the Advanced text server
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(src, opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    subset.save_font(font, dst, opts)


def main():
    if len(sys.argv) < 2:
        print(__doc__ or "usage: make-test-project.py <project_dir> [--noto DIR]")
        sys.exit(2)
    out = os.path.abspath(sys.argv[1])
    noto = None
    if "--noto" in sys.argv:
        noto = sys.argv[sys.argv.index("--noto") + 1]
    else:
        home = os.environ.get("GODOT_HOME", "/home/user/godotengine")
        noto = fetch_noto(os.path.join(home, "fonts", "noto-cjk"))
    for d in ("sprites", "tiles", "fonts", "sfx", "shell"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    files = {
        "project.godot": PROJECT_GODOT,
        "main.gd": MAIN_GD,
        "main.tscn": MAIN_TSCN,
        "shell/body.html": BODY_SHELL,
        "export_presets.cfg.in": EXPORT_PRESETS,
    }
    for name, text in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    make_hero(os.path.join(out, "sprites/hero.png"), os.path.join(out, "sprites/hero_n.png"))
    make_pillar(os.path.join(out, "sprites/pillar.png"), os.path.join(out, "sprites/pillar_n.png"))
    make_tiles(os.path.join(out, "tiles/tiles.png"), os.path.join(out, "tiles/tiles_n.png"))
    # 0.15 s 880 Hz blip with a fast decay, OGG Vorbis.
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                           "sine=frequency=880:sample_rate=44100:duration=0.15", "-af",
                           "afade=t=out:st=0.01:d=0.14,volume=0.6", "-ac", "1", "-c:a", "libvorbis",
                           "-q:a", "4", os.path.join(out, "sfx/blip.ogg")])
    # Font subsets: every character in main.gd plus printable ASCII and the spaces used for wrapping.
    chars = set(MAIN_GD) | set(TEST_TITLE) | {chr(c) for c in range(0x20, 0x7f)} | {"​", "　"}
    chars |= set("0123456789.,:%")
    text = "".join(sorted(c for c in chars if c >= " "))
    subset_font(os.path.join(noto, "Sans/SubsetOTF/JP/NotoSansJP-Regular.otf"), os.path.join(out, "fonts/cjk_jp.otf"), text)
    subset_font(os.path.join(noto, "Sans/SubsetOTF/SC/NotoSansSC-Regular.otf"), os.path.join(out, "fonts/cjk_sc.otf"), text)
    with open(os.path.join(noto, "Sans/LICENSE"), encoding="utf-8") as f:
        lic = f.read()
    with open(os.path.join(out, "fonts/LICENSE-NotoSansCJK.txt"), "w", encoding="utf-8") as f:
        f.write(lic)
    print("test project written to", out)


if __name__ == "__main__":
    main()
