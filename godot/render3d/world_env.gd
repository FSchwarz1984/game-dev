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
# Round 5 (decision-log G5R3-1): the day is round 3's again (the user: round 4's freshening, the
# lush greens, the saturated grade, the blue-green shade, was "画蛇添足"; "全面 roll back"): the rows
# from 6:24 to 17:24 are round 3's own values. The night (the user: "夜里的光非常好，就按这个来") keeps
# round 4's rows: midnight, 4:24, the dawn twilight at 5:24, the sunset at 18:24, 19:36.
const KEYS := [
	[0.0, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[4.4, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[5.4, Color(0.95, 0.62, 0.58), 0.35, Color(0.22, 0.24, 0.36), Color(0.07, 0.07, 0.07), Color(0.45, 0.42, 0.52), Color(0.02, 0.012, 0.04), Color(1.02, 0.99, 1.02), 0.92, Color(-0.004, 0.002, 0.02), Color(0.02, 0.01, 0.0), 0.6],
	[6.4, Color(1.0, 0.74, 0.50), 1.30, Color(0.42, 0.43, 0.56), Color(0.140, 0.110, 0.095), Color(0.88, 0.72, 0.60), Color(0.012, 0.006, 0.022), Color(1.08, 1.04, 1.00), 1.0, Color(-0.012, 0.0, 0.024), Color(0.035, 0.02, 0.0), 0.0],
	[8.0, Color(1.0, 0.90, 0.72), 1.65, Color(0.70, 0.78, 0.97), Color(0.20, 0.175, 0.14), Color(0.86, 0.80, 0.72), Color(0.012, 0.012, 0.03), Color(1.06, 1.04, 1.01), 1.0, Color(-0.012, 0.0, 0.022), Color(0.03, 0.018, 0.0), 0.0],
	[12.0, Color(1.0, 0.96, 0.88), 1.72, Color(0.70, 0.80, 1.0), Color(0.20, 0.18, 0.15), Color(0.78, 0.82, 0.86), Color(0.012, 0.012, 0.03), Color(1.07, 1.05, 1.02), 1.08, Color(-0.014, 0.0, 0.022), Color(0.025, 0.015, 0.0), 0.0],
	[15.5, Color(1.0, 0.87, 0.62), 1.75, Color(0.71, 0.76, 0.96), Color(0.21, 0.175, 0.14), Color(0.80, 0.75, 0.70), Color(0.014, 0.01, 0.03), Color(1.07, 1.04, 1.0), 1.0, Color(-0.012, 0.0, 0.022), Color(0.035, 0.018, 0.0), 0.0],
	[17.4, Color(1.0, 0.86, 0.60), 1.8, Color(0.45, 0.48, 0.71), Color(0.17, 0.145, 0.11), Color(0.82, 0.74, 0.62), Color(0.010, 0.008, 0.026), Color(1.05, 1.03, 0.97), 1.07, Color(-0.024, -0.004, 0.066), Color(0.03, 0.026, 0.0), 0.0],
	[18.4, Color(1.0, 0.62, 0.40), 1.2, Color(0.34, 0.34, 0.56), Color(0.08, 0.07, 0.06), Color(0.50, 0.44, 0.50), Color(0.014, 0.010, 0.034), Color(1.02, 0.99, 0.98), 1.0, Color(-0.02, 0.0, 0.05), Color(0.025, 0.015, 0.0), 0.5],
	[19.6, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
	[24.0, Color(0.55, 0.65, 1.0), 0.6, Color(0.065, 0.088, 0.16), Color(0.020, 0.024, 0.034), Color(0.06, 0.08, 0.13), Color(0.006, 0.010, 0.022), Color(0.97, 1.0, 1.08), 0.86, Color(-0.004, 0.0, 0.014), Color(0.0, 0.0, 0.0), 1.0],
]


var sky_mat: ShaderMaterial          # the hemisphere the ambient light comes from (not drawn)
var ambient_gain := 1.0
# by day: how strong the sky's light is in the shade. Round 3 painted its shade with the sky's luma
# as it was; the engine's ambient from the sky hemisphere (its radiance map, filtered) delivers about
# three quarters to four fifths of that to a surface facing up: x1.2 matches round 3's shade (round 5, measured
# with render3d/dev/asset_preview on the same assets through both renderers)
var ambient_day_gain := 1.2
# by day the engine's ambient sky carries only this share of the sky's hue (round 3's painted shade:
# the luma and a fifth of the colour; the materials turn their own hue cool, w3_paint_shade); at
# night all of it (round 4's night, kept)
var ambient_day_hue := 0.2
# the sky's light let back into the sun's shadow while the sun is low (round 5, the lead: the
# mornings, the evenings and the shrine under the great camphor were far darker than round 3's;
# pixel_toon w3_shadow_fill): this share of the day's ambient sky, added where the sun is shadowed.
# None while the sun stands above about 58 degrees (round 3's midday is matched as it is), at night or
# in rain.
var shadow_fill := 0.8


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
	# (only as deep as the farthest ground the view can see, about 37 m past the focus: the froxel
	# slices are then about 1.2 m deep, fine enough for a mist that lies a metre over the ground)
	environment.volumetric_fog_length = view.cam_distance + 45.0
	environment.volumetric_fog_detail_spread = 1.0
	environment.volumetric_fog_gi_inject = 0.5
	environment.volumetric_fog_ambient_inject = 0.14
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


# the ground fog per hour: low and warm-lit in the early morning (the valley mist), all but gone by
# day (the air is clear: lead 16:00, "雾只在远处、清晨和特定的地方"; the shafts under the crowns are
# the atmosphere's own), a thin layer at night for the lanterns' halos
func _fog_for_hour() -> void:
	if fog_mat == null:
		return
	var morning := clampf(1.0 - absf(hours - 6.8) / 2.0, 0.0, 1.0)
	var night := float(sample(hours)[11])
	var d := lerpf(0.0025, 0.009, morning) + night * 0.007 + rain * 0.008
	var layer := lerpf(5.0, 3.0, morning)
	fog_mat.set_shader_parameter("density", d * fog_strength)
	fog_mat.set_shader_parameter("layer", layer)
	var fc: Color = sample(hours)[5]
	fog_mat.set_shader_parameter("albedo", Color(0.9, 0.94, 1.0).lerp(fc, 0.25))
	# (the barrier is not a grey veil: its air is as clear as outside; the gates' mist is its own)
	fog_mat.set_shader_parameter("realm_boost", 0.0)
	fog_mat.set_shader_parameter("band_density", 0.9 * fog_strength)
	# the morning mist lies in drifting banks with clear gaps between (not an even veil)
	fog_mat.set_shader_parameter("banks", lerpf(0.55, 0.9, morning))


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
	var rain_dim := 1.0 - 0.55 * rain          # overcast (round 3's)
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
	var ag := ambient_gain * lerpf(ambient_day_gain, 1.0, float(k[11]))
	var hue := lerpf(ambient_day_hue, 1.0, float(k[11]))
	if sky_mat:
		sky_mat.set_shader_parameter("top", _hue_share(sky, hue) * ag)
		sky_mat.set_shader_parameter("bottom", _hue_share(ground, hue) * ag)
	var low_sun := 1.0 - smoothstep(0.80, 0.86, dir.y)
	var fill := _hue_share(sky, hue) * ag * shadow_fill * low_sun * (1.0 - float(k[11])) * (1.0 - rain)
	RenderingServer.global_shader_parameter_set("w3_fill", Vector3(fill.r, fill.g, fill.b))
	RenderingServer.global_shader_parameter_set("w3_fog_col", Vector3(fog.r, fog.g, fog.b))
	RenderingServer.global_shader_parameter_set("w3_night", night)
	RenderingServer.global_shader_parameter_set("w3_wet", wet)
	# the golden hour: what the low sun does not reach is lit by the blue-violet sky (long cool shadows)
	var golden := clampf(1.0 - absf(hours - 17.7) / 1.3, 0.0, 1.0) * (1.0 - night)
	# the painter's shade colour (multiplies the ambient light only: sky, VoxelGI bounce; the materials
	# also turn their own hue cool, w3_paint_shade): round 3's by day, a little cool, blue-violet in the
	# golden hour; round 4's at night
	var shade_tint := Vector3(0.95, 0.98, 1.05).lerp(Vector3(0.93, 0.94, 1.14), golden).lerp(Vector3(0.97, 1.0, 1.03), night)
	RenderingServer.global_shader_parameter_set("w3_shade_tint", shade_tint)
	RenderingServer.global_shader_parameter_set("w3_lit_tint", Vector3(1.03, 1.0, 0.96).lerp(Vector3(0.95, 1.0, 1.06), night))
	environment.background_color = fog
	# valley mist: thick in the early morning, thin at noon, back at dusk and at night
	var mist_k := clampf(1.0 - absf(hours - 6.6) / 3.2, 0.0, 1.0) * 0.85 + clampf(1.0 - absf(hours - 19.5) / 3.0, 0.0, 1.0) * 0.45 + night * 0.35 + rain * 0.4
	# early morning the mist stands higher, up through the saddle (thin there, thick in the gully and
	# down the spur), warm in the low sun; by mid-morning it has sunk back into the valleys
	var morning := clampf(1.0 - absf(hours - 7.2) / 2.6, 0.0, 1.0)
	# (round 4: it stays in the low ground, the gully and the slopes below the gate; the saddle, the
	# yard and the shrine stand clear above it: "雾只在远处、清晨和特定的地方")
	var mist_top := lerpf(-11.0, -4.5, morning)
	var mist_bottom := lerpf(-26.0, -22.0, morning)
	RenderingServer.global_shader_parameter_set("w3_mist", Vector4(mist_top, mist_bottom, clampf(0.25 + mist_k, 0.0, lerpf(0.92, 0.6, morning)), 0.012))
	_fog_for_hour()
	var c := view.composite
	# the grade (round 5, G5R3-1): round 3's by day: its lift, gain and saturation (the keys), its
	# split toning as keyed, its S-curve (0.32), no exposure change; round 4's at night (a softer
	# curve, the toning a little stronger, the eye opened a quarter). The barrier has no grade of its
	# own any more: its difference is its content (the ground mist, the motes, the flowers), not a hue.
	c.set_shader_parameter("lift", Vector3(k[6].r, k[6].g, k[6].b))
	c.set_shader_parameter("soft_ends", 0.0)
	c.set_shader_parameter("gain", Vector3(k[7].r, k[7].g, k[7].b))
	c.set_shader_parameter("saturation", float(k[8]) * (1.0 - 0.15 * rain))
	c.set_shader_parameter("shadow_tone", Vector3(k[9].r, k[9].g, k[9].b) * lerpf(1.0, 1.6, night))
	c.set_shader_parameter("high_tone", Vector3(k[10].r, k[10].g, k[10].b) * lerpf(1.0, 1.3, night))
	c.set_shader_parameter("contrast", lerpf(0.32, 0.08, night))
	c.set_shader_parameter("exposure", 1.0 + 0.25 * night)
	# (round 4's hue-aware freshening of the greens: at night only, as round 4 had it)
	c.set_shader_parameter("green_turn", 0.08 * night)
	c.set_shader_parameter("green_gain", lerpf(1.0, 1.08, night))
	c.set_shader_parameter("yellow_gain", lerpf(1.0, 0.9, night))


## A colour with only a share of its hue left (the rest its luma): the ambient sky of the day.
static func _hue_share(c: Color, k: float) -> Color:
	var l := c.r * 0.2126 + c.g * 0.7152 + c.b * 0.0722
	return Color(l, l, l).lerp(c, k)


## How deep she stands in a gate's mist band (0 .. 1): the mist rises around her (ground_fog band_swell).
func set_band_swell(k: float) -> void:
	if fog_mat:
		fog_mat.set_shader_parameter("band_swell", clampf(k, 0.0, 1.0))


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
