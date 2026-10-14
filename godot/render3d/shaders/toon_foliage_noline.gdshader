// Foliage toon material without outlines (outline class 5): small plants with thin leaves (ferns,
// susuki, bamboo leaves), which the foliage outline would blacken. See toon_foliage_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_disabled;
stencil_mode write, compare_always, 5;
#include "res://render3d/shaders/toon_foliage_body.gdshaderinc"
