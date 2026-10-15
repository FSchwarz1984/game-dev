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
# Round 4 (decision-log G5R2-1): verdant and soft instead of withered yellow and hard. The sun is
# near-white at noon (warm, never yellow), golden only at the ends of the day; the shade is lit by a
# blue-cyan sky and a green bounce off the grass, so shadows lean blue-green; the grade's contrast is
# soft and its saturation favours the greens (composite.gdshader).
const KEYS := [
	[0.0, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[4.4, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[5.4, Color(0.95, 0.62, 0.58), 0.35, Color(0.22, 0.24, 0.36), Color(0.07, 0.07, 0.07), Color(0.45, 0.42, 0.52), Color(0.02, 0.012, 0.04), Color(1.02, 0.99, 1.02), 0.92, Color(-0.004, 0.002, 0.02), Color(0.02, 0.01, 0.0), 0.6],
	[6.4, Color(1.0, 0.80, 0.60), 1.6, Color(0.60, 0.67, 0.77), Color(0.15, 0.17, 0.11), Color(0.80, 0.78, 0.74), Color(0.010, 0.012, 0.016), Color(1.04, 1.02, 1.0), 1.0, Color(-0.01, 0.004, 0.02), Color(0.025, 0.012, 0.0), 0.0],
	[8.0, Color(1.0, 0.92, 0.80), 1.75, Color(0.52, 0.66, 0.88), Color(0.16, 0.20, 0.12), Color(0.80, 0.84, 0.86), Color(0.010, 0.012, 0.022), Color(1.03, 1.03, 1.01), 1.03, Color(-0.012, 0.004, 0.02), Color(0.018, 0.012, 0.0), 0.0],
	[12.0, Color(1.0, 0.95, 0.88), 1.8, Color(0.54, 0.68, 0.87), Color(0.17, 0.21, 0.12), Color(0.78, 0.85, 0.90), Color(0.010, 0.012, 0.022), Color(1.03, 1.03, 1.02), 1.04, Color(-0.012, 0.005, 0.02), Color(0.012, 0.010, 0.0), 0.0],
	[15.5, Color(1.0, 0.92, 0.80), 1.8, Color(0.54, 0.65, 0.86), Color(0.17, 0.20, 0.12), Color(0.80, 0.80, 0.80), Color(0.012, 0.010, 0.022), Color(1.03, 1.02, 1.0), 1.03, Color(-0.012, 0.004, 0.022), Color(0.02, 0.012, 0.0), 0.0],
	[17.4, Color(1.0, 0.80, 0.55), 1.9, Color(0.50, 0.54, 0.78), Color(0.15, 0.15, 0.10), Color(0.86, 0.74, 0.62), Color(0.010, 0.006, 0.026), Color(1.04, 1.01, 0.98), 1.03, Color(-0.02, 0.0, 0.05), Color(0.03, 0.02, 0.0), 0.0],
	[18.4, Color(1.0, 0.62, 0.40), 1.2, Color(0.34, 0.34, 0.56), Color(0.08, 0.07, 0.06), Color(0.50, 0.44, 0.50), Color(0.014, 0.010, 0.034), Color(1.02, 0.99, 0.98), 1.0, Color(-0.02, 0.0, 0.05), Color(0.025, 0.015, 0.0), 0.5],
	[19.6, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[24.0, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
]


var sky_mat: ShaderMaterial          # the hemisphere the ambient light comes from (not drawn)
var ambient_gain := 1.0
# by day the sky light is strong next to the sun (round 4: soft contrast; a shaded patch keeps about
# half the light of a sunlit one, so the shade reads as a large blue-green mass, not a black hole)
var ambient_day_gain := 1.5


func setup(v: PixelView3D) -> void:
	view = v
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.1, 0.12, 0.16)
	# the ambient light (round 4): the engine's, from a hemisphere sky of the hour (sky above, the
	# ground's bounce below), occluded by the VoxelGI, SSAO and each material's AO
	var sky := Sky.new()
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://render3d/shaders/ambient_sky.gdshader")
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	sky.process_mode = Sky.PROCESS_MODE_QUALITY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_sky_contribution = 1.0
	environment.ambient_light_energy = 1.0
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	# contact shade in the creases (only the ambient: the sun's shadows stay the sun's)
	environment.ssao_enabled = true
	environment.ssao_radius = 0.9
	environment.ssao_intensity = 1.6
	environment.ssao_power = 1.4
	environment.ssao_detail = 0.4
	environment.ssao_light_affect = 0.0

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


## Volumetric fog (Forward+): the air near the ground, one FogVolume over the terrain
## (shaders/ground_fog.gdshader): the sun's shafts through the crowns, the lanterns' halos, the
## morning mist that glows. The global density stays 0 (the air between the top-down camera and the
## ground is not air). strength scales the hour's density (0 turns it off).
var fog_volume: FogVolume
var fog_mat: ShaderMaterial
var fog_strength := 1.0
## The barrier (round 4, item 5): 0 outside .. 1 inside, by where she stands (sample.gd blends it
## across the gates' fog bands). Inside the light is softer and brighter: lifted, less contrast,
## warm-white highlights, more luminous shade, fuller air.
var realm := 0.0
var realm_mask: W3RealmMask


func use_volumetric_fog(strength: float, t: Terrain3D) -> void:
	fog_strength = strength
	environment.volumetric_fog_enabled = strength > 0.0
	environment.volumetric_fog_density = 0.0
	environment.volumetric_fog_albedo = Color(0.92, 0.95, 1.0)
	environment.volumetric_fog_anisotropy = 0.5           # light scatters forward: shafts toward the sun
	environment.volumetric_fog_length = view.cam_distance + 80.0
	environment.volumetric_fog_detail_spread = 1.0
	environment.volumetric_fog_gi_inject = 0.5
	environment.volumetric_fog_ambient_inject = 0.2
	environment.volumetric_fog_temporal_reprojection_enabled = false   # no ghosting as she walks
	sun.light_volumetric_fog_energy = 1.0
	if strength <= 0.0:
		return
	fog_volume = FogVolume.new()
	fog_volume.name = "GroundFog"
	var size := Vector2(float(t.nx - 1), float(t.nz - 1)) * t.cell
	fog_volume.size = Vector3(size.x, 90.0, size.y)
	fog_volume.position = Vector3(t.origin.x + size.x * 0.5, 0.0, t.origin.y + size.y * 0.5)
	fog_volume.shape = RenderingServer.FOG_VOLUME_SHAPE_BOX
	fog_mat = ShaderMaterial.new()
	fog_mat.shader = load("res://render3d/shaders/ground_fog.gdshader")
	fog_mat.set_shader_parameter("ground", t.height_texture())
	fog_mat.set_shader_parameter("frame", Vector4(t.origin.x, t.origin.y, t.cell, 0.0))
	fog_mat.set_shader_parameter("cells", Vector2(t.nx, t.nz))
	fog_volume.material = fog_mat
	view.world_root.add_child(fog_volume)
	if realm_mask == null:
		realm_mask = W3RealmMask.new()
		realm_mask.build(t)
	fog_mat.set_shader_parameter("realm", realm_mask.texture)
	fog_mat.set_shader_parameter("realm_frame", realm_mask.frame())
	fog_mat.set_shader_parameter("realm_cells", Vector2(realm_mask.nx, realm_mask.nz))
	_fog_for_hour()


# the ground fog per hour: thick, low and warm-lit in the early morning (the valley mist), a light
# haze by day (enough to show the shafts), clearer at dusk, a thin layer at night for the halos
func _fog_for_hour() -> void:
	if fog_mat == null:
		return
	var morning := clampf(1.0 - absf(hours - 6.8) / 2.4, 0.0, 1.0)
	var night := float(sample(hours)[11])
	var d := lerpf(0.009, 0.024, morning) + night * 0.01 + rain * 0.012
	var layer := lerpf(5.0, 3.0, morning)
	fog_mat.set_shader_parameter("density", d * fog_strength)
	fog_mat.set_shader_parameter("layer", layer)
	var fc: Color = sample(hours)[5]
	fog_mat.set_shader_parameter("albedo", Color(0.9, 0.94, 1.0).lerp(fc, 0.25))
	# inside the barrier the air holds more light by day; the gates' curtains stand at every hour
	fog_mat.set_shader_parameter("realm_boost", 0.45 * (1.0 - night) + 0.3 * night)
	fog_mat.set_shader_parameter("band_density", 0.35 * fog_strength)


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
	var rain_dim := 1.0 - 0.8 * rain           # overcast: hardly a shadow
	sun.light_color = k[1]
	sun.light_energy = float(k[2]) * rain_dim
	if absf(dir.y) > 0.999:
		dir = (dir + Vector3(0.01, 0, 0)).normalized()
	sun.basis = Basis.looking_at(-dir, Vector3.UP)
	var sky: Color = (k[3] as Color).lerp(Color(0.44, 0.5, 0.54) * (1.0 - float(k[11]) * 0.8), rain * 0.6)
	var ground: Color = k[4]
	var fog: Color = (k[5] as Color).lerp(Color(0.5, 0.53, 0.56) * (1.0 - float(k[11]) * 0.75), rain * 0.6)
	var night := float(k[11])
	RenderingServer.global_shader_parameter_set("w3_sun_dir", dir)
	RenderingServer.global_shader_parameter_set("w3_sun", Vector3(k[1].r, k[1].g, k[1].b) * float(k[2]) * rain_dim)
	RenderingServer.global_shader_parameter_set("w3_sky", Vector3(sky.r, sky.g, sky.b))
	RenderingServer.global_shader_parameter_set("w3_ground", Vector3(ground.r, ground.g, ground.b))
	if sky_mat:
		var ag := ambient_gain * lerpf(ambient_day_gain, 1.0, float(k[11]))
		sky_mat.set_shader_parameter("top", sky * ag)
		sky_mat.set_shader_parameter("bottom", ground * ag)
	RenderingServer.global_shader_parameter_set("w3_fog_col", Vector3(fog.r, fog.g, fog.b))
	RenderingServer.global_shader_parameter_set("w3_night", night)
	RenderingServer.global_shader_parameter_set("w3_wet", wet)
	# the golden hour: what the low sun does not reach is lit by the blue-violet sky (long cool shadows)
	var golden := clampf(1.0 - absf(hours - 17.7) / 1.3, 0.0, 1.0) * (1.0 - night)
	# the painter's shade colour (multiplies the ambient light only: sky, VoxelGI bounce): blue-green
	# by day, so the warm bounce off the sunlit earth never turns the shade brown (round 4: "大块的蓝绿阴影");
	# blue-violet in the golden hour; neutral at night (the night grade does it)
	var shade_tint := Vector3(0.88, 0.98, 1.08).lerp(Vector3(0.92, 0.95, 1.1), golden).lerp(Vector3(0.97, 1.0, 1.03), night)
	# inside the barrier the shade is more luminous (the realm's soft light)
	shade_tint *= 1.0 + 0.1 * realm * (1.0 - night)
	RenderingServer.global_shader_parameter_set("w3_shade_tint", shade_tint)
	RenderingServer.global_shader_parameter_set("w3_lit_tint", Vector3(1.01, 1.0, 0.98).lerp(Vector3(0.95, 1.0, 1.06), night))
	environment.background_color = fog
	# valley mist: thick in the early morning, thin at noon, back at dusk and at night
	var mist_k := clampf(1.0 - absf(hours - 6.6) / 3.2, 0.0, 1.0) * 0.85 + clampf(1.0 - absf(hours - 19.5) / 3.0, 0.0, 1.0) * 0.45 + night * 0.35 + rain * 0.4
	# early morning the mist stands higher, up through the saddle (thin there, thick in the gully and
	# down the spur), warm in the low sun; by mid-morning it has sunk back into the valleys
	var morning := clampf(1.0 - absf(hours - 7.2) / 2.6, 0.0, 1.0)
	var mist_top := lerpf(-11.0, 1.5, morning)
	var mist_bottom := lerpf(-26.0, -22.0, morning)
	RenderingServer.global_shader_parameter_set("w3_mist", Vector4(mist_top, mist_bottom, clampf(0.25 + mist_k, 0.0, lerpf(0.92, 0.7, morning)), 0.012))
	_fog_for_hour()
	var c := view.composite
	var rk := realm * (1.0 - 0.6 * night)
	c.set_shader_parameter("lift", Vector3(k[6].r, k[6].g, k[6].b) + Vector3(0.012, 0.014, 0.011) * rk)
	c.set_shader_parameter("gain", Vector3(k[7].r, k[7].g, k[7].b))
	# (rain: wet leaves and wet earth are deeper, not greyer; the light is what goes flat)
	c.set_shader_parameter("saturation", float(k[8]) * (1.0 + 0.05 * realm * (1.0 - night)))
	# split toning, a little stronger than the keys (round 4): shade leans blue-green, light warm
	c.set_shader_parameter("shadow_tone", Vector3(k[9].r, k[9].g, k[9].b) * 1.6 + Vector3(0.0, 0.004, 0.004) * (1.0 - night))
	c.set_shader_parameter("high_tone", Vector3(k[10].r, k[10].g, k[10].b) * 1.3 + Vector3(0.008, 0.006, 0.0) * rk)
	# a soft S-curve (round 4: soft contrast, nothing crushed), softer still at night and inside the
	# barrier
	c.set_shader_parameter("contrast", lerpf(0.16, 0.08, night) * (1.0 - 0.5 * rk))
	# exposure: a low sun lights the ground at a grazing angle; the eye (and a camera) open up for it
	var el_k := 1.0 - smoothstep(0.25, 0.75, maxf(dir.y, 0.0))
	c.set_shader_parameter("exposure", (1.0 + 0.6 * el_k * (1.0 - night)) * (1.0 + 0.12 * rk))


## Where she stands, in the barrier's terms (0 outside .. 1 inside): the frame's look follows.
func set_realm(k: float) -> void:
	k = clampf(k, 0.0, 1.0)
	if absf(k - realm) < 0.002:
		return
	realm = k
	set_time(hours)


func tick(dt: float) -> void:
	clock += dt
	if fog_mat:
		fog_mat.set_shader_parameter("drift", clock * 0.25 * wind)
	RenderingServer.global_shader_parameter_set("w3_time", clock)
	RenderingServer.global_shader_parameter_set("w3_wind", Vector4(1.0, 0.25, wind, 0.35))
