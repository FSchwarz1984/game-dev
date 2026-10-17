// The bridge between the gathered lights and the burst (G5R3-61, variant "drain", a proposal): after
// the 「隔」 tower goes dark the gate draws the town's own colours up out of the ground. Every grain
// leaves a pixel of the town (bucket <= the drained radius) in the colour of what that pixel is made
// of (its material's own, unlit), lifts slowly, is pulled into one of three strands that wind round
// each other up a common way (out of the town, bending left and up into the gate's mouth from below),
// faster and faster, and turns the sky shore's pale jade past half its way, as the rising lights do. A 1 px core
// (a few with a faint 2 px halo), a tail of 1-3 pixels along its own curve; nothing joins two grains.
// Two more instances: the burst at the town (variants "drain" and "flash"), a white flash with a
// stepped halo decaying in about half a second, and the gate's flare in the same frame ("flash" only).
// instance: x0 y0 | o dur | jit lift ; colour: own sRGB (0..1) | flags ; custom: seg nt kind strand
//   o: departure (s after the drain began), dur: s to the gate, jit: px off its strand, lift: px it
//   rises before it is drawn in; kind 0 grain, 2 the burst at the town, 3 the gate's flare; strand
//   0..2, 3 loose (a sheath round the strands), + 4 with a halo
// Output: sRGB units into the rising lights' buffer (composite.gdshader), cores pushed into HDR.
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform float el = -1.0;       // seconds since the drain began (< 0: none)
uniform float fl = -1.0;       // seconds since the burst (< 0: none)
uniform vec2 town;             // canvas px: the middle of the town (ground zero)
uniform vec2 gate;             // canvas px: the gate's mouth
uniform float amp = 5.0;       // half width of the braid (px)
uniform float twists = 1.4;    // turns of the braid along the way
uniform float bloom = 0.35;
uniform float gate_k = 0.0;    // the gate's flare in the burst's frame (variant "flash"): 1, else 0

varying flat vec4 v_core;      // core x, y, size, alpha
varying flat vec4 v_glow;      // glow centre x, y, radius, alpha
varying flat vec3 v_rc;
varying flat float v_seg;
varying flat float v_kind;
varying vec2 v_px;

const vec3 C_JADE = vec3(196.0, 246.0, 226.0);
const vec3 C_BURST = vec3(232.0, 240.0, 255.0);
const float TAU_D = 6.2831853;

vec2 bez(vec2 a, vec2 b, vec2 c, vec2 d, float s) {
	float u = 1.0 - s;
	return u * u * u * a + 3.0 * u * u * s * b + 3.0 * u * s * s * c + s * s * s * d;
}

vec2 bezd(vec2 a, vec2 b, vec2 c, vec2 d, float s) {
	float u = 1.0 - s;
	return 3.0 * u * u * (b - a) + 6.0 * u * s * (c - b) + 3.0 * s * s * (d - c);
}

// where a grain is at s (0 its pixel of the town .. 1 the gate): its own short lift, drawn into its
// strand of the common way (VistaSouthDrain.pos_at is the same on the CPU)
vec2 pos_at(vec2 p0, float lift, float jit, float strand, float s) {
	float h = town.y - gate.y;
	vec2 a = town + vec2(0.0, -4.0);
	vec2 b = town + vec2(-2.0, -0.42 * h);
	vec2 c = gate + vec2(0.2 * (town.x - gate.x), 0.36 * h);
	vec2 d = gate + vec2(0.0, 1.0);
	vec2 sp = bez(a, b, c, d, s);
	vec2 dv = bezd(a, b, c, d, s);
	vec2 n = normalize(vec2(-dv.y, dv.x) + vec2(1e-5, 0.0));
	float off;
	if (strand < 2.5) {
		float env = smoothj(0.2, 0.42, s) * (1.0 - smoothj(0.74, 0.985, s));
		off = amp * env * sin(TAU_D * twists * s + strand * TAU_D / 3.0) + jit * (1.0 - smoothj(0.8, 1.0, s));
	} else {
		off = jit * (1.0 - smoothj(0.45, 0.95, s));
	}
	vec2 r = sp + n * off;
	// it rises off the ground first, then is drawn in sideways: its height joins the way's early, its
	// x late, so the grains of the whole town go up as a sheaf that gathers into the strands above it
	vec2 q = p0 + vec2(0.0, -lift * smoothj(0.0, 0.3, s));
	return vec2(mix(q.x, r.x, smoothj(0.1, 0.46, s)), mix(q.y, r.y, smoothj(0.04, 0.36, s)));
}

void vertex() {
	vec2 p0 = MODEL_MATRIX[0].xy;
	float o = MODEL_MATRIX[1].x, dur = MODEL_MATRIX[1].y;
	float jit = MODEL_MATRIX[2].x, lift = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	vec2 corner = VERTEX;          // the unit quad's corner (VERTEX is overwritten below)
	vec3 own = COLOR.rgb * 255.0;
	float seg = INSTANCE_CUSTOM.r, nt = INSTANCE_CUSTOM.g, kind = INSTANCE_CUSTOM.b, fla = INSTANCE_CUSTOM.a;
	bool halo = fla > 3.5;
	float strand = halo ? fla - 4.0 : fla;
	v_seg = seg;
	v_kind = kind;
	v_core = vec4(0.0);
	v_glow = vec4(0.0);
	v_rc = own;
	VERTEX = vec2(-100000.0);
	if (kind > 1.5) {
		// the burst at the town (kind 2): a white flash and its halo, half a second; kind 3, in the same
		// frame, the gate's flare (variant "flash" only)
		bool at_gate = kind > 2.5;
		float k = fl >= 0.0 ? exp(-fl / 0.2) : 0.0;
		float k2 = fl >= 0.0 ? exp(-fl / 0.5) : 0.0;
		if (at_gate) {
			k *= gate_k;
			k2 *= gate_k;
		}
		if (k2 > 0.01) {
			vec2 at = at_gate ? gate : town;
			vec2 c = vec2(roundj(at.x), roundj(at.y)) - vec2(1.0, 1.0);
			v_rc = at_gate ? mix(C_BURST, C_JADE, 0.35) : C_BURST;
			v_core = vec4(c, 2.0, min(1.0, k * 1.2));
			v_glow = vec4(c, 11.0, 0.7 * k2);
			vec2 lo = c - 12.0, hi = c + 14.0;
			v_px = lo + corner * (hi - lo);
			VERTEX = world + v_px;
		}
	} else if (el >= 0.0) {
		float u = (el - o) / dur;
		if (u >= 0.0 && u < 1.0) {
			float s = u * 0.3 + u * u * 0.7;
			float kk = smoothj(0.45, 0.88, s);
			v_rc = mix(own, C_JADE, kk * kk * (3.0 - 2.0 * kk));
			float a = smoothj(0.0, 0.12, u) * (1.0 - smoothj(0.95, 1.0, s) * 0.6) * (strand > 2.5 ? 0.45 : 0.72);
			if (seg > nt) {
			} else if (seg < 0.5) {
				vec2 q = pos_at(p0, lift, jit, strand, s);
				vec2 c = vec2(roundj(q.x), roundj(q.y));
				v_core = vec4(c, 1.0, a);
				float r = halo ? 2.0 : 0.0;
				v_glow = vec4(c, r, halo ? a * 0.35 : 0.0);
				vec2 lo = c - r, hi = c + r + 1.0;
				v_px = lo + corner * (hi - lo);
				VERTEX = world + v_px;
			} else {
				// the tail: back along its own curve, a little longer the faster it goes
				float ds = max(0.011, (0.3 + 1.4 * u) / 30.0 / dur * 0.6);
				vec2 q = pos_at(p0, lift, jit, strand, max(0.0, s - seg * ds));
				vec2 c = vec2(roundj(q.x), roundj(q.y));
				v_core = vec4(c, 1.0, a * (0.55 - seg * (0.5 / (nt + 1.0))));
				v_px = c + corner;
				VERTEX = world + v_px;
			}
		}
	}
}

void fragment() {
	vec2 p = floor(v_px);
	vec3 c = vec3(0.0);
	float hdr = 0.0;
	vec2 d = p - v_core.xy;
	if (d.x >= 0.0 && d.y >= 0.0 && d.x < v_core.z && d.y < v_core.z) {
		c += mix(v_rc, vec3(255.0), v_kind > 1.5 ? 0.25 : 0.12) * v_core.w;
		hdr = v_seg < 0.5 ? v_core.w * (v_kind > 1.5 ? 2.0 : 1.0) : 0.0;
	}
	if (v_glow.z > 0.0) c += v_rc * v_glow.w * (v_kind > 1.5 ? glow_w2(p - v_glow.xy, v_glow.z) : glow_w(p - v_glow.xy, v_glow.z));
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + v_rc / 255.0 * hdr * bloom, 1.0);
}
