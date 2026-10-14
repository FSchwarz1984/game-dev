// Screen post, outline class 3 (characters): their sprites carry their own outline; fog only, lighter.
shader_type spatial;
render_mode unshaded, depth_draw_never, depth_test_disabled, cull_disabled, skip_vertex_transform, fog_disabled, blend_mix, shadows_disabled;
stencil_mode read, compare_equal, 3;
#define OL_SIL 0.0
#define OL_CREASE 0.0
#define OL_TINT vec3(1.0)
#define OL_RIM 0
#include "res://render3d/shaders/post_body.gdshaderinc"
