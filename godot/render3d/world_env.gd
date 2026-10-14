class_name W3Env
extends Node
## Time of day, weather and the shader globals of the 3D pixel renderer
## (docs/knowledge/21-3d-pixel-render.md §5).
##
## The sun follows a continuous stylised arc (R-7: shadows never jump): it rises in the
## east-north-east, stands high in the north-north-west at noon (so cast shadows fall to the lower
## right and the upper-left light convention of the 2D art holds), and sets in the west-south-west,
## warming the camera-facing slopes at dusk. At night a pale moon stands high in the north-west.
## Colours and grading are keyframed per hour and interpolated.

var view: PixelView3D
var sun: DirectionalLight3D
var environment: Environment
var hours := 10.0
var rain := 0.0                 # 0..1
var wind := 1.0                 # 0..2
var clock := 0.0                # w3_time (seconds); advanced by tick()
var fog_haze_focus := 0.0       # height the haze is measured from (her height)

# hour, sun colour (linear), sun energy, sky ambient, ground bounce, fog colour,
# grade lift, grade gain, saturation, shadow tone, high tone, night
const KEYS := [
	[0.0,  Color(0.42, 0.52, 0.85), 0.34, Color(0.105, 0.13, 0.22), Color(0.03, 0.03, 0.05), Color(0.09, 0.11, 0.19), Color(0.015, 0.02, 0.05), Color(0.96, 1.0, 1.1), 0.78, Color(-0.01, 0.0, 0.03), Color(0.0, 0.0, 0.0), 1.0],
	[4.4,  Color(0.42, 0.52, 0.85), 0.32, Color(0.11, 0.13, 0.22), Color(0.03, 0.03, 0.05), Color(0.10, 0.11, 0.19), Color(0.015, 0.02, 0.05), Color(0.96, 1.0, 1.1), 0.78, Color(-0.01, 0.0, 0.03), Color(0.0, 0.0, 0.0), 1.0],
	[5.4,  Color(0.85, 0.55, 0.55), 0.35, Color(0.20, 0.19, 0.30), Color(0.06, 0.05, 0.06), Color(0.42, 0.36, 0.46), Color(0.02, 0.01, 0.04), Color(1.02, 0.98, 1.02), 0.86, Color(-0.005, 0.0, 0.02), Color(0.02, 0.01, 0.0), 0.6],
	[6.4, Color(1.0, 0.74, 0.50), 1.30, Color(0.42, 0.43, 0.56), Color(0.140, 0.110, 0.095), Color(0.88, 0.72, 0.60), Color(0.012, 0.006, 0.022), Color(1.08, 1.04, 1.00), 1.0, Color(-0.012, 0.0, 0.024), Color(0.035, 0.02, 0.0), 0.0],
	[8.0, Color(1.0, 0.89, 0.68), 1.75, Color(0.56, 0.62, 0.78), Color(0.175, 0.155, 0.125), Color(0.86, 0.80, 0.72), Color(0.0, 0.0, 0.014), Color(1.07, 1.05, 1.02), 1.06, Color(-0.012, 0.0, 0.022), Color(0.03, 0.018, 0.0), 0.0],
	[12.0, Color(1.0, 0.95, 0.82), 2.0, Color(0.60, 0.68, 0.86), Color(0.185, 0.170, 0.140), Color(0.78, 0.82, 0.86), Color(0.0, 0.0, 0.014), Color(1.08, 1.06, 1.03), 1.08, Color(-0.014, 0.0, 0.022), Color(0.025, 0.015, 0.0), 0.0],
	[15.5, Color(1.0, 0.87, 0.62), 1.85, Color(0.57, 0.61, 0.77), Color(0.185, 0.155, 0.125), Color(0.80, 0.75, 0.70), Color(0.005, 0.0, 0.014), Color(1.08, 1.05, 1.00), 1.08, Color(-0.012, 0.0, 0.022), Color(0.035, 0.018, 0.0), 0.0],
	[17.4, Color(1.0, 0.70, 0.46), 0.948, Color(0.435, 0.420, 0.566), Color(0.156, 0.117, 0.104), Color(0.70, 0.56, 0.52), Color(0.015, 0.0, 0.02), Color(1.08, 1.03, 0.98), 0.94, Color(-0.012, -0.004, 0.03), Color(0.035, 0.015, -0.005), 0.0],
	[18.4, Color(0.92, 0.52, 0.34), 0.5, Color(0.22, 0.2, 0.28), Color(0.08, 0.055, 0.05), Color(0.44, 0.3, 0.32), Color(0.025, 0.01, 0.035), Color(1.02, 0.96, 0.98), 0.9, Color(-0.008, -0.004, 0.03), Color(0.035, 0.012, -0.004), 0.5],
	[19.6, Color(0.42, 0.52, 0.85), 0.34, Color(0.105, 0.13, 0.22), Color(0.03, 0.03, 0.05), Color(0.09, 0.11, 0.19), Color(0.015, 0.02, 0.05), Color(0.96, 1.0, 1.1), 0.78, Color(-0.01, 0.0, 0.03), Color(0.0, 0.0, 0.0), 1.0],
	[24.0, Color(0.42, 0.52, 0.85), 0.34, Color(0.105, 0.13, 0.22), Color(0.03, 0.03, 0.05), Color(0.09, 0.11, 0.19), Color(0.015, 0.02, 0.05), Color(0.96, 1.0, 1.1), 0.78, Color(-0.01, 0.0, 0.03), Color(0.0, 0.0, 0.0), 1.0],
]


func setup(v: PixelView3D) -> void:
	view = v
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.1, 0.12, 0.16)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment.tonemap_exposure = 1.0
	environment.glow_enabled = true
	environment.glow_normalized = false
	environment.glow_intensity = 0.9
	environment.glow_strength = 1.0
	environment.glow_bloom = 0.0
	environment.glow_hdr_threshold = 1.0
	environment.glow_hdr_scale = 2.0
	environment.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	environment.set_glow_level(0, 0.0)
	environment.set_glow_level(1, 1.0)
	environment.set_glow_level(2, 0.6)
	environment.set_glow_level(3, 0.3)
	environment.set_glow_level(4, 0.0)
	view.set_environment(environment)

	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	# With an orthogonal camera Godot ignores the max distance: the shadow map covers the camera's
	# near..far box (pixel_view3d.gd keeps it tight). Godot 4.7 scales the depth bias of a
	# directional light by shadow_blur, so with blur 0 (hard edges) shadow_bias does nothing; the
	# normal bias (in shadow texels) and the ground casting from inside itself (toon_terrain) keep
	# the acne away.
	sun.directional_shadow_max_distance = 48.0
	sun.directional_shadow_fade_start = 1.0
	sun.shadow_bias = 0.0
	sun.shadow_normal_bias = 2.0
	sun.shadow_blur = 0.0
	sun.light_specular = 0.0
	view.vp.add_child(sun)


static func _lerp_key(a: Array, b: Array, t: float) -> Array:
	var out := []
	for i in a.size():
		var x = a[i]
		var y = b[i]
		if x is Color:
			out.append((x as Color).lerp(y, t))
		else:
			out.append(lerpf(x, y, t))
	return out


func sample(h: float) -> Array:
	h = fposmod(h, 24.0)
	for i in KEYS.size() - 1:
		var a: Array = KEYS[i]
		var b: Array = KEYS[i + 1]
		var h0: float = a[0]
		var h1: float = b[0]
		if h >= h0 and h <= h1:
			var t: float = (h - h0) / maxf(0.001, h1 - h0)
			t = t * t * (3.0 - 2.0 * t)
			return _lerp_key(a, b, t)
	return KEYS[0]


## Direction toward the sun (or the moon at night) for an hour of the day.
static func sun_direction(h: float) -> Vector3:
	h = fposmod(h, 24.0)
	var day := clampf((h - 5.6) / (18.6 - 5.6), 0.0, 1.0)
	var az := deg_to_rad(68.0 - 183.0 * day)            # clockwise from north
	var el := deg_to_rad(6.0 + 56.0 * sin(PI * day))
	var sun_v := Vector3(sin(az) * cos(el), sin(el), -cos(az) * cos(el))
	var moon_v := Vector3(-0.42, 0.78, -0.46).normalized()
	# the light swings smoothly from the low sun to the moon through dusk (and back at dawn),
	# while it is dim: shadows turn, they never jump
	var w := smoothstep(5.0, 5.9, h) * (1.0 - smoothstep(18.3, 19.1, h))
	return moon_v.lerp(sun_v, w).normalized()


func set_time(h: float) -> void:
	hours = fposmod(h, 24.0)
	var k := sample(hours)
	var dir := sun_direction(hours)
	var wet := rain
	var rain_dim := 1.0 - 0.55 * rain
	sun.light_color = k[1]
	sun.light_energy = float(k[2]) * rain_dim
	if absf(dir.y) > 0.999:
		dir = (dir + Vector3(0.01, 0, 0)).normalized()
	sun.basis = Basis.looking_at(-dir, Vector3.UP)
	var sky: Color = (k[3] as Color).lerp(Color(0.2, 0.22, 0.26), rain * 0.5)
	var ground: Color = k[4]
	var fog: Color = (k[5] as Color).lerp(Color(0.5, 0.53, 0.56) * (1.0 - float(k[11]) * 0.75), rain * 0.6)
	var night := float(k[11])
	RenderingServer.global_shader_parameter_set("w3_sun_dir", dir)
	RenderingServer.global_shader_parameter_set("w3_sun", Vector3(k[1].r, k[1].g, k[1].b) * float(k[2]) * rain_dim)
	RenderingServer.global_shader_parameter_set("w3_sky", Vector3(sky.r, sky.g, sky.b))
	RenderingServer.global_shader_parameter_set("w3_ground", Vector3(ground.r, ground.g, ground.b))
	RenderingServer.global_shader_parameter_set("w3_fog_col", Vector3(fog.r, fog.g, fog.b))
	RenderingServer.global_shader_parameter_set("w3_night", night)
	RenderingServer.global_shader_parameter_set("w3_wet", wet)
	RenderingServer.global_shader_parameter_set("w3_shade_tint", Vector3(0.95, 0.98, 1.05).lerp(Vector3(0.95, 0.98, 1.05), night))
	RenderingServer.global_shader_parameter_set("w3_lit_tint", Vector3(1.05, 1.0, 0.92).lerp(Vector3(0.95, 1.0, 1.06), night))
	environment.background_color = fog
	# valley mist: thick in the early morning, thin at noon, back at dusk and at night
	var mist_k := clampf(1.0 - absf(hours - 6.6) / 3.2, 0.0, 1.0) * 0.85 + clampf(1.0 - absf(hours - 19.5) / 3.0, 0.0, 1.0) * 0.45 + night * 0.35 + rain * 0.4
	RenderingServer.global_shader_parameter_set("w3_mist", Vector4(-11.0, -26.0, clampf(0.25 + mist_k, 0.0, 0.92), 0.012))
	var c := view.composite
	c.set_shader_parameter("lift", Vector3(k[6].r, k[6].g, k[6].b))
	c.set_shader_parameter("gain", Vector3(k[7].r, k[7].g, k[7].b))
	c.set_shader_parameter("saturation", float(k[8]) * (1.0 - 0.15 * rain))
	c.set_shader_parameter("shadow_tone", Vector3(k[9].r, k[9].g, k[9].b))
	c.set_shader_parameter("high_tone", Vector3(k[10].r, k[10].g, k[10].b))
	# a gentle S-curve by day (light that reads as sunlight), softer at night
	c.set_shader_parameter("contrast", lerpf(0.32, 0.12, night))


func tick(dt: float) -> void:
	clock += dt
	RenderingServer.global_shader_parameter_set("w3_time", clock)
	RenderingServer.global_shader_parameter_set("w3_wind", Vector4(1.0, 0.25, wind, 0.35))
