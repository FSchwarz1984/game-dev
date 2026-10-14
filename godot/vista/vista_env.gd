class_name VistaEnv
extends RefCounted
## The time of day of the vistas: a port of src/vista/tod.js (todEnv, keyed, skyAt). The palettes of
## the painted layers are baked per time of day (tools/vista); what is left here is what the shaders
## need every frame: the sky's painted colours (zenith .. horizon, the warm west), the star alpha and
## how far night has come. Colours are 0..255 sRGB like the JS.

const SKY := [
	# h,    zenith,          upper,            lower,            horizon,          glow (west),      glow, stars
	[17.0, [92, 124, 170], [140, 160, 186], [204, 192, 170], [232, 206, 164], [255, 222, 168], 0.7, 0.0],
	[17.8, [80, 104, 156], [132, 136, 170], [212, 168, 146], [240, 186, 132], [255, 198, 128], 0.85, 0.0],
	[18.5, [58, 70, 122], [108, 100, 144], [190, 128, 124], [230, 150, 110], [255, 172, 112], 0.8, 0.05],
	[19.1, [34, 42, 86], [72, 64, 112], [128, 82, 108], [178, 104, 98], [214, 120, 96], 0.45, 0.35],
	[19.7, [18, 23, 54], [38, 40, 82], [70, 52, 88], [118, 70, 82], [138, 78, 82], 0.18, 0.8],
	[20.4, [11, 15, 38], [27, 33, 70], [58, 44, 78], [104, 62, 70], [104, 62, 70], 0.0, 1.0],
	[24.0, [10, 13, 34], [24, 30, 64], [54, 42, 76], [98, 60, 70], [98, 60, 70], 0.0, 1.0],
]

var tod := 21.0
var night := 1.0
var stars := 1.0
var sky_z := Vector3.ZERO
var sky_up := Vector3.ZERO
var sky_lo := Vector3.ZERO
var sky_ho := Vector3.ZERO
var glow := Vector3.ZERO
var glow_amt := 0.0


static func smoothj(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


static func at(hour: float) -> VistaEnv:
	var e := VistaEnv.new()
	e.tod = hour
	e.night = smoothj(18.9, 20.2, hour)
	e.sky_z = _keyed3(hour, 1)
	e.sky_up = _keyed3(hour, 2)
	e.sky_lo = _keyed3(hour, 3)
	e.sky_ho = _keyed3(hour, 4)
	e.glow = _keyed3(hour, 5)
	e.glow_amt = _keyed1(hour, 6)
	e.stars = _keyed1(hour, 7)
	return e


## JS keyed(): smoothstep between the two keyframes around k.
static func _span(k: float) -> Array:
	if k <= SKY[0][0]:
		return [0, 0, 0.0]
	for j in SKY.size() - 1:
		var a: Array = SKY[j]
		var b: Array = SKY[j + 1]
		if k <= b[0]:
			return [j, j + 1, smoothj(0.0, 1.0, (k - a[0]) / (b[0] - a[0]))]
	return [SKY.size() - 1, SKY.size() - 1, 0.0]


static func _keyed3(k: float, i: int) -> Vector3:
	var s := _span(k)
	var a: Array = SKY[s[0]][i]
	var b: Array = SKY[s[1]][i]
	return Vector3(a[0], a[1], a[2]).lerp(Vector3(b[0], b[1], b[2]), s[2])


static func _keyed1(k: float, i: int) -> float:
	var s := _span(k)
	return lerpf(SKY[s[0]][i], SKY[s[1]][i], s[2])


## skyAt(env, e, u) of tod.js: the painted sky at elevation e (0 horizon .. 1 top) and u (0 east .. 1 west).
func sky_at(e: float, u: float = 0.5) -> Vector3:
	e = clampf(e, 0.0, 1.0)
	var c: Vector3
	if e < 0.16:
		c = sky_ho.lerp(sky_lo, smoothj(0.0, 0.16, e))
	elif e < 0.5:
		c = sky_lo.lerp(sky_up, smoothj(0.16, 0.5, e))
	else:
		c = sky_up.lerp(sky_z, smoothj(0.5, 1.0, e))
	var gw := glow_amt * pow(clampf(u, 0.0, 1.0), 2.2) * pow(1.0 - clampf(e / 0.55, 0.0, 1.0), 1.6)
	if gw > 0.0:
		c = c.lerp(glow, clampf(gw, 0.0, 1.0) * 0.85)
	return c
