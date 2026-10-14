// Screen post, outline class 4 (the current target): a warm rim on its silhouette.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
stencil_mode read, compare_equal, 4;
#define OL_SIL 1.0
#define OL_CREASE 0.0
#define OL_TINT vec3(1.0)
#define OL_RIM 1
#include "res://render3d/shaders/post_body.gdshaderinc"
