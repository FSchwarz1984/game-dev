class_name W3LampOcclusion
extends CompositorEffect
## How much of each lamp the camera sees (G5R3-27, the lead's review of the perspective camera): a
## lamp's glow in the air is the volumetric fog its light reaches, and lamps cast no shadows, so a
## lantern hidden under an eave or behind a crown still lit the air in front of what hides it: a
## glow with no source. After the opaque pass this looks at the depth buffer round each lamp's point
## on the screen (a 5 x 5 pixel patch, compute shader below) and reads the share that nothing nearer
## covers back to the CPU without stalling (RenderingDevice.buffer_get_data_async); W3Lamps scales
## each lamp's fog energy by it (eased), so a hidden lamp's glow goes with it. The orthographic
## camera does not use it (its picture stays exactly the old one).
## Nothing asynchronous may call back into this object: it is freed when she leaves the home area,
## and a read-back can land a frame or two later. An exported game does not check that a method
## Callable's object is still alive (core/variant/callable.cpp checks only under DEBUG_ENABLED, so the
## editor shows nothing), and such a call crashed the game on going back to the menu. The read-back
## goes to a lambda that holds the _Sink below (a RefCounted outliving this object), and the shader
## and buffers are made lazily in the first render callback instead of through call_on_render_thread.

const MAX := 64
const TOLERANCE := 0.3        # m: what lies less than this in front of the lamp's point (its own lantern) does not hide it

const SOURCE := """
#version 450
layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;
layout(set = 0, binding = 0) uniform sampler2D depth_tex;
layout(set = 0, binding = 1, std430) restrict readonly buffer Lamps { vec4 data[]; } lamps;
layout(set = 0, binding = 2, std430) restrict writeonly buffer Vis { float vis[]; } outv;
layout(push_constant, std430) uniform Params {
	vec2 size;      // the viewport in px
	float count;
	float ortho;    // 1: orthographic (linear depth)
	float near;
	float far;
	float tol;
	float pad;
} p;
// the depth buffer is reversed (1 at the near plane, 0 at the far one)
float view_depth(float b) {
	if (p.ortho > 0.5) {
		return p.far - b * (p.far - p.near);
	}
	return p.near * p.far / (p.near + b * (p.far - p.near));
}
void main() {
	uint i = gl_GlobalInvocationID.x;
	if (float(i) >= p.count) {
		return;
	}
	vec4 l = lamps.data[i];     // xy: its point on the screen (px), z: its depth (m), w: 1 on the screen
	if (l.w < 0.5) {
		outv.vis[i] = 1.0;
		return;
	}
	float seen = 0.0;
	for (int y = -2; y <= 2; y++) {
		for (int x = -2; x <= 2; x++) {
			vec2 px = clamp(floor(l.xy) + vec2(float(x), float(y)) + 0.5, vec2(0.5), p.size - 0.5);
			float d = view_depth(textureLod(depth_tex, px / p.size, 0.0).r);
			seen += d > l.z - p.tol ? 1.0 : 0.0;
		}
	}
	outv.vis[i] = seen / 25.0;
}
"""

## where the read-back lands (see the top): the lambda handed to buffer_get_data_async holds it
class _Sink extends RefCounted:
	var mutex := Mutex.new()
	var vis := PackedFloat32Array()
	var pending := false

	func take(bytes: PackedByteArray) -> void:
		mutex.lock()
		vis = bytes.to_float32_array()
		pending = false
		mutex.unlock()

	func is_pending() -> bool:
		mutex.lock()
		var p := pending
		mutex.unlock()
		return p

var rd: RenderingDevice
var _shader := RID()
var _pipeline := RID()
var _in_buf := RID()
var _out_buf := RID()
var _sampler := RID()
var _mutex := Mutex.new()
var _data := PackedFloat32Array()
var _params := PackedFloat32Array()
var _count := 0
var _sink := _Sink.new()
var _waiting := 0             # frames since a read-back was asked for (0: none outstanding)
var _set_up := false
var failed := false


func _init() -> void:
	effect_callback_type = EFFECT_CALLBACK_TYPE_POST_OPAQUE
	rd = RenderingServer.get_rendering_device()
	if rd == null:
		failed = true


## Render thread, the first render callback (see the top: no call_on_render_thread with this object)
func _setup() -> void:
	_set_up = true
	var src := RDShaderSource.new()
	src.language = RenderingDevice.SHADER_LANGUAGE_GLSL
	src.source_compute = SOURCE
	var spirv := rd.shader_compile_spirv_from_source(src)
	if spirv.compile_error_compute != "":
		push_error("lamp occlusion: " + spirv.compile_error_compute)
		failed = true
		return
	_shader = rd.shader_create_from_spirv(spirv)
	_pipeline = rd.compute_pipeline_create(_shader)
	var z4 := PackedFloat32Array()
	z4.resize(MAX * 4)
	_in_buf = rd.storage_buffer_create(MAX * 16, z4.to_byte_array())
	var z1 := PackedFloat32Array()
	z1.resize(MAX)
	z1.fill(1.0)
	_out_buf = rd.storage_buffer_create(MAX * 4, z1.to_byte_array())
	var ss := RDSamplerState.new()
	ss.min_filter = RenderingDevice.SAMPLER_FILTER_NEAREST
	ss.mag_filter = RenderingDevice.SAMPLER_FILTER_NEAREST
	_sampler = rd.sampler_create(ss)


func _notification(what: int) -> void:
	if what == NOTIFICATION_PREDELETE and rd != null:
		for r in [_pipeline, _shader, _in_buf, _out_buf, _sampler]:
			if (r as RID).is_valid():
				rd.free_rid(r)


## Main thread, every frame: the lamps' points on the screen (4 floats each: px x, px y, depth along
## the view in m, 1 on the screen / 0 not), and the camera (viewport size, orthographic, near, far).
func set_lamps(data: PackedFloat32Array, count: int, size: Vector2, ortho: bool, near: float, far: float) -> void:
	_mutex.lock()
	_data = data
	_count = mini(count, MAX)
	_params = PackedFloat32Array([size.x, size.y, float(_count), 1.0 if ortho else 0.0, near, far, TOLERANCE, 0.0])
	_mutex.unlock()


## Main thread: the latest shares (one per lamp, in the order given; empty until the first read-back).
func visibility() -> PackedFloat32Array:
	_sink.mutex.lock()
	var v := _sink.vis
	_sink.mutex.unlock()
	return v


func _render_callback(callback_type: int, render_data: RenderData) -> void:
	if failed or callback_type != EFFECT_CALLBACK_TYPE_POST_OPAQUE:
		return
	if not _set_up:
		_setup()
		if failed:
			return
	if _waiting > 0:
		if _sink.is_pending():
			_waiting += 1
			if _waiting < 30:
				return
		_waiting = 0       # (it came, or a read-back that never came: ask again)
	_mutex.lock()
	var data := _data
	var count := _count
	var params := _params
	_mutex.unlock()
	if count <= 0:
		return
	var sb := render_data.get_render_scene_buffers() as RenderSceneBuffersRD
	if sb == null:
		return
	var depth := sb.get_depth_layer(0)
	if not depth.is_valid():
		return
	var bytes := data.to_byte_array()
	rd.buffer_update(_in_buf, 0, mini(bytes.size(), MAX * 16), bytes)
	var u0 := RDUniform.new()
	u0.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	u0.binding = 0
	u0.add_id(_sampler)
	u0.add_id(depth)
	var u1 := RDUniform.new()
	u1.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u1.binding = 1
	u1.add_id(_in_buf)
	var u2 := RDUniform.new()
	u2.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u2.binding = 2
	u2.add_id(_out_buf)
	var uset := UniformSetCacheRD.get_cache(_shader, 0, [u0, u1, u2])
	var pc := params.to_byte_array()
	var cl := rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(cl, _pipeline)
	rd.compute_list_bind_uniform_set(cl, uset, 0)
	rd.compute_list_set_push_constant(cl, pc, pc.size())
	rd.compute_list_dispatch(cl, 1, 1, 1)
	rd.compute_list_end()
	var sink := _sink
	sink.mutex.lock()
	sink.pending = true
	sink.mutex.unlock()
	# (a lambda that touches only its capture is not bound to this object, see the top)
	if rd.buffer_get_data_async(_out_buf, func(bytes: PackedByteArray) -> void: sink.take(bytes), 0, count * 4) == OK:
		_waiting = 1
	else:
		sink.take(PackedByteArray())
