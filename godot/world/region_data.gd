class_name RegionData
extends RefCounted
## The ground of one region, from its baked logic mask: walkable / height / material queries.
## logic.png: one pixel per cell (cell_m metres, 0.25 by default), RGB8:
##   R * 256 + G = ground height in centimetres (terraces at 0.5 m steps; stairs ramp between them)
##   B = material id (MATERIALS)
## Movement rule (docs/knowledge/15-perspective-rules.md): she may step to a cell whose ground is at
## most max_step_m (0.3 m) higher or lower, so the 0.5 m terrace edges are cliffs. Stairs are the way
## between levels: they rise north-south only, and their sides are walls (stepping sideways on or off
## a stair needs level ground), so a staircase is entered at its foot and left at its head.
## Pure data: no nodes, testable headless.

const MATERIALS := {
	0: {"name": "void", "kind": Field.Ground.WALL, "step": ""},
	1: {"name": "grass", "kind": Field.Ground.GROUND, "step": "grass"},
	2: {"name": "dirt", "kind": Field.Ground.GROUND, "step": "dirt"},
	3: {"name": "stone", "kind": Field.Ground.GROUND, "step": "stone"},
	4: {"name": "stairs", "kind": Field.Ground.GROUND, "step": "stone"},
	5: {"name": "water", "kind": Field.Ground.WATER, "step": "water"},
	6: {"name": "deep_water", "kind": Field.Ground.DEEP, "step": "water"},
	7: {"name": "cliff", "kind": Field.Ground.WALL, "step": ""},
	8: {"name": "wood", "kind": Field.Ground.GROUND, "step": "wood"},
	9: {"name": "sand", "kind": Field.Ground.GROUND, "step": "sand"},
}
const STAIRS := 4
const LEVEL_EPS_CM := 5

var id := ""
var def: Dictionary = {}
var dir := ""
var cell_m := 0.25
var max_step_cm := 30
var size := Vector2i.ZERO          # cells
var origin := Vector2.ZERO         # world metres of the mask's top-left corner
var heights := PackedInt32Array()  # centimetres
var mats := PackedByteArray()


## Loads res://world/regions/<id>/region.json and its logic mask.
static func load_dir(path: String) -> RegionData:
	var r := RegionData.new()
	r.dir = path
	var text := FileAccess.get_file_as_string(path.path_join("region.json"))
	var parsed = JSON.parse_string(text)
	if not (parsed is Dictionary):
		push_error("RegionData: cannot read %s/region.json" % path)
		return r
	r.def = parsed
	r.id = String(r.def.get("id", path.get_file()))
	r.cell_m = float(r.def.get("cell_m", 0.25))
	r.max_step_cm = int(round(float(r.def.get("max_step_m", 0.3)) * 100.0))
	var o: Array = r.def.get("origin_m", [0, 0])
	r.origin = Vector2(o[0], o[1])
	# imported with the "image" importer (lossless); a texture import still works if lossless
	var res = load(path.path_join(String(r.def.get("logic", "logic.png"))))
	var img: Image = res as Image
	if img == null and res is Texture2D:
		img = (res as Texture2D).get_image()
	if img == null:
		push_error("RegionData: no logic mask in %s" % path)
		return r
	r.set_mask(img)
	return r


func set_mask(img: Image) -> void:
	if img.get_format() != Image.FORMAT_RGB8:
		img = img.duplicate()
		img.convert(Image.FORMAT_RGB8)
	size = Vector2i(img.get_width(), img.get_height())
	var data := img.get_data()
	heights.resize(size.x * size.y)
	mats.resize(size.x * size.y)
	for i in size.x * size.y:
		heights[i] = int(data[i * 3]) * 256 + int(data[i * 3 + 1])
		mats[i] = data[i * 3 + 2]


func size_m() -> Vector2:
	return Vector2(size) * cell_m


func cell_index(x: float, z: float) -> int:
	var i := int(floor((x - origin.x) / cell_m))
	var j := int(floor((z - origin.y) / cell_m))
	if i < 0 or j < 0 or i >= size.x or j >= size.y:
		return -1
	return j * size.x + i


func height_cm(x: float, z: float) -> int:
	var c := cell_index(x, z)
	return heights[c] if c >= 0 else 0


## Ground height at (x, z) in metres (0 outside the region).
func height_at(x: float, z: float) -> float:
	return height_cm(x, z) / 100.0


func material_id(x: float, z: float) -> int:
	var c := cell_index(x, z)
	return mats[c] if c >= 0 else 0


func material_at(x: float, z: float) -> String:
	return String(MATERIALS.get(material_id(x, z), MATERIALS[0])["name"])


func step_sound(x: float, z: float) -> String:
	return String(MATERIALS.get(material_id(x, z), MATERIALS[0])["step"])


func walkable(x: float, z: float) -> bool:
	return int(MATERIALS.get(material_id(x, z), MATERIALS[0])["kind"]) != Field.Ground.WALL


## What stepping from (fx, fz) to (x, z) meets: Field.Ground.GROUND / WATER / DEEP / WALL.
func ground_kind(x: float, z: float, fx: float, fz: float) -> int:
	var c := cell_index(x, z)
	if c < 0:
		return Field.Ground.WALL
	var m := int(mats[c])
	var kind := int(MATERIALS.get(m, MATERIALS[0])["kind"])
	if kind == Field.Ground.WALL:
		return kind
	var f := cell_index(fx, fz)
	if f < 0 or f == c:
		return kind
	var dh := absi(heights[c] - heights[f])
	if dh > max_step_cm:
		return Field.Ground.WALL  # a cliff, up or down
	var fm := int(mats[f])
	if (m == STAIRS) != (fm == STAIRS) and dh > LEVEL_EPS_CM:
		# on or off a staircase: only along it (north-south), never over its side walls
		if absf(x - fx) > absf(z - fz):
			return Field.Ground.WALL
		var fi := f % size.x
		var ci := c % size.x
		if fi != ci:
			return Field.Ground.WALL
	return kind


## Named camera shot (region.json "shots"), as {x, z} metres; empty when unknown.
func shot(name: String) -> Dictionary:
	return def.get("shots", {}).get(name, {})
