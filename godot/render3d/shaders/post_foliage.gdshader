// Screen post, outline class 2 (foliage): softer silhouette, no creases (leaf cards would speckle).
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
stencil_mode read, compare_equal, 2;
#define OL_SIL 0.6
#define OL_CREASE 0.0
#define OL_TINT vec3(0.6, 0.66, 0.72)
#define OL_RIM 0
#include "res://render3d/shaders/post_body.gdshaderinc"
