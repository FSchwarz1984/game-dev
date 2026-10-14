class_name Proj
## World and screen conventions shared by every layer.
##
## World: metres. x east, z south, h up (height above the zero level of the region).
## Screen: native pixels (480x270 at scale 1; more when the window is larger). x right, y down.
## Oblique 3/4 projection (docs/knowledge/15-perspective-rules.md): 1 m = 20 px on every axis;
##   screen x = 20 x,  screen y = 20 (z - h).
## Ground planes keep their top-down shape, south-facing walls are seen face-on, east/west walls are
## a line, north-facing walls are hidden. Things that stand on the ground are y-sorted by their
## ground z (their node position), and drawn lifted by 20 h.

const PPM := 20.0
const NATIVE := Vector2i(480, 270)

## Foot point of something standing at (x, z) on ground of height h, in world pixels.
static func to_px(x: float, z: float, h: float = 0.0) -> Vector2:
	return Vector2(x * PPM, (z - h) * PPM)


## Node position used for y-sorting: the ground point (height ignored), in world pixels.
static func sort_px(x: float, z: float) -> Vector2:
	return Vector2(x * PPM, z * PPM)


## Unit facing vector (x, z) -> the four sprite views of the 3/4 view, with hysteresis:
## once she faces sideways she keeps doing so until the motion is clearly vertical.
static func face_of(dx: float, dz: float, prev: String = "front") -> String:
	var ax := absf(dx)
	var az := absf(dz)
	var side := prev == "left" or prev == "right"
	if ax > az * (0.8 if side else 1.25):
		return "left" if dx < 0.0 else "right"
	return "back" if dz < 0.0 else "front"


## Facing for a scripted move (no hysteresis), as in the JS director.
static func face_of_move(dx: float, dz: float) -> String:
	if absf(dx) > absf(dz) * 1.15:
		return "left" if dx < 0.0 else "right"
	return "back" if dz < 0.0 else "front"


static func face_vector(face: String) -> Vector2:
	match face:
		"left":
			return Vector2(-1, 0)
		"right":
			return Vector2(1, 0)
		"back":
			return Vector2(0, -1)
	return Vector2(0, 1)
