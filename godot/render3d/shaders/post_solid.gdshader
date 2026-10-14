// Screen post, outline class 1 (terrain, rocks, wood, buildings): full silhouettes and creases.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
stencil_mode read, compare_equal, 1;
#define OL_SIL 0.85
#define OL_CREASE 0.7
#define OL_TINT vec3(0.52, 0.56, 0.66)
#define OL_RIM 0
#include "res://render3d/shaders/post_body.gdshaderinc"
