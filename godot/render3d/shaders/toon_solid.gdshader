// Solid toon material, outline class 1: outlined solid (default). See toon_solid_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, ambient_light_disabled, specular_disabled, fog_disabled, cull_back;
stencil_mode write, compare_always, 1;
#include "res://render3d/shaders/toon_solid_body.gdshaderinc"
