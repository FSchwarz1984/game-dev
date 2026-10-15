class_name W3RealmMask
extends RefCounted
## The barrier (結界) as the renderer sees it (round 4, item 5): a map over the region, 1 m a texel,
## built from the layout's zones (terrain.json `zones`, `fog`):
##   R  inside the sanctum (zones.sanctum), feathered over about 3 m at its edge
##   G  the gates' fog bands (zones.fog_east|north|sw): their density 0..1, feathered
##   B  the band's height (m / 8)
##   A  the inner precinct (zones.oku: the great camphor and the shrine's terrace), feathered
## The ground fog reads it (more luminous air inside, the mist curtains at the gates); the look of
## the frame blends toward the realm's by where she stands (sample()); the air's life (motes,
## petals) gathers inside.

const CELL := 1.0

var origin := Vector2.ZERO
var nx := 0
var nz := 0
var image: Image
var texture: ImageTexture


func build(t: Terrain3D) -> void:
	origin = t.origin
	var size := Vector2(float(t.nx - 1), float(t.nz - 1)) * t.cell
	nx = int(ceil(size.x / CELL)) + 1
	nz = int(ceil(size.y / CELL)) + 1
	var zones: Dictionary = t.info.get("zones", {})
	var fog: Dictionary = t.info.get("fog", {})
	var sanct := _raster(zones.get("sanctum", []))
	var oku := _raster(zones.get("oku", []))
	var band := PackedFloat32Array()
	band.resize(nx * nz)
	var band_h := PackedFloat32Array()
	band_h.resize(nx * nz)
	for key in ["fog_east", "fog_north", "fog_sw"]:
		if not zones.has(key):
			continue
		var f: Dictionary = fog.get(key, {})
		var dens := float(f.get("density", 0.6))
		var h := float(f.get("height", 3.0))
		var m := _raster(zones[key])
		for i in m.size():
			if m[i] > 0.0 and m[i] * dens > band[i]:
				band[i] = m[i] * dens
				band_h[i] = h
	sanct = _blur(_blur(sanct))
	oku = _blur(_blur(oku))
	# the gate's mist spills a few metres past the path into the scrub on either side (a soft edge,
	# not a lit box): three passes, the core kept full
	band = _blur(_blur(_blur(band)))
	for i in band.size():
		band[i] = minf(band[i] * 1.6, 1.0)
	band_h = _spread(band_h, band)
	image = Image.create(nx, nz, false, Image.FORMAT_RGBA8)
	for j in nz:
		for i in nx:
			var k := j * nx + i
			image.set_pixel(i, j, Color(sanct[k], band[k], clampf(band_h[k] / 8.0, 0.0, 1.0), oku[k]))
	texture = ImageTexture.create_from_image(image)


## The mask at a world point (bilinear): Color(sanctum, band, band height / 8, oku).
func sample(x: float, z: float) -> Color:
	if image == null:
		return Color(0, 0, 0, 0)
	var fx := clampf((x - origin.x) / CELL, 0.0, float(nx - 1))
	var fz := clampf((z - origin.y) / CELL, 0.0, float(nz - 1))
	var i0 := int(floor(fx))
	var j0 := int(floor(fz))
	var i1 := mini(i0 + 1, nx - 1)
	var j1 := mini(j0 + 1, nz - 1)
	var tx := fx - float(i0)
	var tz := fz - float(j0)
	var a := image.get_pixel(i0, j0).lerp(image.get_pixel(i1, j0), tx)
	var b := image.get_pixel(i0, j1).lerp(image.get_pixel(i1, j1), tx)
	return a.lerp(b, tz)


## The frame for a shader: origin x, z, cell, and the texel counts.
func frame() -> Vector4:
	return Vector4(origin.x, origin.y, CELL, 0.0)


func _raster(poly_in: Array) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	out.resize(nx * nz)
	if poly_in.size() < 3:
		return out
	var poly := PackedVector2Array()
	for p in poly_in:
		poly.append(Vector2(float(p[0]), float(p[1])))
	var lo := poly[0]
	var hi := poly[0]
	for p in poly:
		lo = lo.min(p)
		hi = hi.max(p)
	var i0 := maxi(int(floor((lo.x - origin.x) / CELL)) - 1, 0)
	var i1 := mini(int(ceil((hi.x - origin.x) / CELL)) + 1, nx - 1)
	var j0 := maxi(int(floor((lo.y - origin.y) / CELL)) - 1, 0)
	var j1 := mini(int(ceil((hi.y - origin.y) / CELL)) + 1, nz - 1)
	for j in range(j0, j1 + 1):
		for i in range(i0, i1 + 1):
			var w := Vector2(origin.x + i * CELL, origin.y + j * CELL)
			if Geometry2D.is_point_in_polygon(w, poly):
				out[j * nx + i] = 1.0
	return out


# the band's height carried out to where the blurred band now reaches (max over 7 x 7)
func _spread(src: PackedFloat32Array, where: PackedFloat32Array) -> PackedFloat32Array:
	var out := src.duplicate()
	for j in nz:
		for i in nx:
			if where[j * nx + i] <= 0.0:
				continue
			var m := 0.0
			for dj in range(-3, 4):
				var jj := clampi(j + dj, 0, nz - 1)
				for di in range(-3, 4):
					m = maxf(m, src[jj * nx + clampi(i + di, 0, nx - 1)])
			out[j * nx + i] = m
	return out


# a 5 x 5 box blur (two passes of it feather an edge over about 3 m)
func _blur(src: PackedFloat32Array) -> PackedFloat32Array:
	var tmp := PackedFloat32Array()
	tmp.resize(src.size())
	var out := PackedFloat32Array()
	out.resize(src.size())
	for j in nz:
		var row := j * nx
		for i in nx:
			var s := 0.0
			for d in range(-2, 3):
				s += src[row + clampi(i + d, 0, nx - 1)]
			tmp[row + i] = s / 5.0
	for j in nz:
		for i in nx:
			var s := 0.0
			for d in range(-2, 3):
				s += tmp[clampi(j + d, 0, nz - 1) * nx + i]
			out[j * nx + i] = s / 5.0
	return out
