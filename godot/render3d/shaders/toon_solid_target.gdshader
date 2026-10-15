// Solid toon material, outline class 4: the current target (warm highlight outline). See toon_solid_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_back;
stencil_mode write, compare_always, 4;
#include "res://render3d/shaders/toon_solid_body.gdshaderinc"
