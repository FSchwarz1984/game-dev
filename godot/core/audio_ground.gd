class_name AudioGround
extends RefCounted
## What her feet meet, for the step sounds (v0.1's eight grounds: grass, soil, stone, wood, water, leaves, sand,
## moss), read from the terrain's own data so it follows the map when the map changes: the splat (m0: grass,
## dirt, gravel, rock; m1: moss, litter, bank, paddy), the water (Terrain3D.water_at) and the stones and logs
## the roads laid (roads.bin: their upward faces, rasterised once on a worker thread; grey = stone, brown = a
## log step).

const ROAD_NONE := 0
const ROAD_STONE := 1
const ROAD_WOOD := 2

var terrain: Terrain3D
var origin := Vector2.ZERO
var cell := 0.25
var nx := 0
var nz := 0
var m0: Image
var m1: Image
var road := PackedByteArray()
var roads_ready := false
var road_cells := 0
var _task := -1


func build(t: Terrain3D) -> void:
	terrain = t
	if t == null or t.info.is_empty():
		return
	var sp: Dictionary = t.info.get("splat", {})
	origin = t.origin
	cell = float(sp.get("cell", 0.25))
	var size: Array = sp.get("size", [0, 0])
	nx = int(size[0])
	nz = int(size[1])
	var dir := "res://world3d/terrain/" + String(t.info.get("name", "saddle"))
	m0 = load(dir.path_join("m0.png")) as Image
	m1 = load(dir.path_join("m1.png")) as Image
	if m0 and m0.is_compressed():
		m0.decompress()
	if m1 and m1.is_compressed():
		m1.decompress()
	var info: Dictionary = t.info.get("roads", {})
	if info.is_empty():
		roads_ready = true
		return
	var path := dir.path_join(String(info.get("file", "roads.bin")))
	_task = WorkerThreadPool.add_task(_raster_roads.bind(path, info.get("chunks", []).duplicate(true)), false, "AudioGround roads")


## Waits for the road raster (tests and checks; the game just uses it once it is there).
func wait() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1


func _raster_roads(path: String, chunks: Array) -> void:
	var b := FileAccess.get_file_as_bytes(path)
	if b.size() > 2 and b[0] == 0x1f and b[1] == 0x8b:
		b = b.decompress_dynamic(1 << 28, FileAccess.COMPRESSION_GZIP)
	var out := PackedByteArray()
	out.resize(nx * nz)
	var n_set := 0
	for c in chunks:
		var n := int(c["vertices"])
		var tc := int(c["triangles"])
		var o := int(c["offset"])
		var verts := b.slice(o, o + n * 12).to_vector3_array()
		o += n * 12
		var norms := b.slice(o, o + n * 12).to_vector3_array()
		o += n * 12
		var cols := b.slice(o, o + n * 16).to_color_array()
		o += n * 16 + n * 8
		var idx := b.slice(o, o + tc * 12).to_int32_array()
		for k in tc:
			var i0 := idx[k * 3]
			var i1 := idx[k * 3 + 1]
			var i2 := idx[k * 3 + 2]
			if norms[i0].y + norms[i1].y + norms[i2].y < 1.8:
				continue                  # sides of stones and logs: not walked on
			var col := cols[i0]
			var kind := ROAD_WOOD if col.r - col.b > 0.1 else ROAD_STONE
			var cx := (verts[i0].x + verts[i1].x + verts[i2].x) / 3.0
			var cz := (verts[i0].z + verts[i1].z + verts[i2].z) / 3.0
			for p in [Vector2(cx, cz), Vector2(verts[i0].x, verts[i0].z), Vector2(verts[i1].x, verts[i1].z), Vector2(verts[i2].x, verts[i2].z)]:
				var gi := roundi((p.x - origin.x) / cell)
				var gj := roundi((p.y - origin.y) / cell)
				if gi >= 0 and gj >= 0 and gi < nx and gj < nz:
					var q := gj * nx + gi
					if out[q] == 0:
						n_set += 1
					out[q] = kind
	road = out
	road_cells = n_set
	roads_ready = true


func road_at(x: float, z: float) -> int:
	if not roads_ready or road.is_empty():
		return ROAD_NONE
	var gi := roundi((x - origin.x) / cell)
	var gj := roundi((z - origin.y) / cell)
	if gi < 0 or gj < 0 or gi >= nx or gj >= nz:
		return ROAD_NONE
	return road[gj * nx + gi]


## v0.1's ground name under (x, z).
func material_at(x: float, z: float) -> String:
	if terrain == null:
		return "grass"
	var w := terrain.water_at(x, z)
	if int(w["kind"]) > 0 and float(w["h"]) > terrain.height_at(x, z) + 0.02:
		return "water"
	match road_at(x, z):
		ROAD_STONE:
			return "stone"
		ROAD_WOOD:
			return "wood"
	if m0 == null:
		return "grass"
	var i := clampi(roundi((x - origin.x) / cell), 0, nx - 1)
	var j := clampi(roundi((z - origin.y) / cell), 0, nz - 1)
	var a := m0.get_pixel(i, j)
	var b := m1.get_pixel(i, j) if m1 else Color(0, 0, 0, 0)
	var names := ["grass", "soil", "sand", "stone", "moss", "leaves", "soil", "water"]
	var vals := [a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a]
	var best := 0
	for k in vals.size():
		if float(vals[k]) > float(vals[best]):
			best = k
	if float(vals[best]) < 0.05:
		return "grass"
	return names[best]
