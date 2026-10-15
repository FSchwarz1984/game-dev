// char_common.gdshaderinc — shared by the 3D character materials (docs/knowledge/24-3d-characters.md).
// The renderer's contract (pixel_toon.gdshaderinc: lean-back, the screen-texel lattice, the world's
// light globals and lamps) plus what only characters need:
//   * lean + pixel snap after skinning: verticals 30 px per metre like every upright object, her
//     feet's screen point on the pixel lattice (she never shimmers by sub-pixel moves), shadows
//     cast by the upright skeleton;
//   * the material ids the builder writes into UV2.x (tools/characters3d/c3d/surf.py);
//   * the face: pixel-art stamps (eyes, brows, mouth, blush, tears) drawn on the screen lattice at
//     landmarks the script projects every frame (characters/character3d.gd).
#include "res://render3d/shaders/pixel_toon.gdshaderinc"

const int CM_SKIN = 0;
const int CM_FACE = 1;
const int CM_HAIR = 2;
const int CM_CLOTH = 3;
const int CM_HAT_TOP = 4;
const int CM_HAT_UNDER = 5;
const int CM_STRAW = 6;
const int CM_WOOD = 7;
const int CM_ROPE = 8;
const int CM_TIE = 9;

// her logical ground point (the feet, world) and the ground height under her: set every frame by
// character3d.gd. The lean's base stays on the ground when she leaves it (a jump is 30 px per metre
// like any upright thing), and the snap moves the whole figure so that her feet's screen point sits
// on the pixel lattice.
instance uniform vec3 c3_anchor;
instance uniform float c3_base_y;
// 1: upright, no lean and no snap: the figure is drawn by a camera of its own, not the top-down one
// (the view from the lookout bakes her through an orthographic camera behind her: world3d/vista3d.gd)
instance uniform float c3_no_lean;

vec3 c3_leaned_anchor() {
	return vec3(c3_anchor.x, c3_anchor.y, c3_anchor.z - w3_view.w * (c3_anchor.y - c3_base_y));
}

vec3 c3_lean_snap(vec3 wp) {
	if (c3_no_lean > 0.5) {
		return wp;
	}
	wp = w3_lean(wp, c3_base_y, 1.0);
	return wp + w3_snap(c3_leaned_anchor());
}
