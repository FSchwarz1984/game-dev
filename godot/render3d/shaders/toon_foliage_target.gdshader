// Foliage toon material, outline class 4: the current target (warm highlight outline). See toon_foliage_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_disabled;
stencil_mode write, compare_always, 4;
#include "res://render3d/shaders/toon_foliage_body.gdshaderinc"
