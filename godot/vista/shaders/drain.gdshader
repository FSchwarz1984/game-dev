// The bridge between the gathered lights and the burst (G5R3-61, variant "drain", a proposal): after
// the 「隔」 tower goes dark the gate draws the town's own colours up out of the ground, the last breath
// of the lights' rising, in its language (8196ebf, rise.gdshader): every grain leaves a pixel of the
// town (bucket <= the drained radius) in the colour of what that pixel is made of (its material's
// own, unlit), and goes up on its own cubic Bezier: straight up off the ground first (its own height),
// then bent toward the gate, out to one side or the other of the way in its middle (the swarm's belly),
// gathering only near the gate's mouth, which it enters from below; each its own departure, speed and
// bend, slow at first and faster and faster (the rising lights take 7-10 s; these 1.6-2.7 s), turning
// the sky shore's pale jade past half its way. A 1 px core (a third with a faint 2 px halo), a tail of
// 1-2 pixels along its own curve; nothing joins two grains.
// More instances: the burst at the town (kind 2, variants "drain" and "flash"), a white flash with a
// stepped halo decaying in about half a second; the gate's flare in the same frame (kind 3, "flash"
// only); the gate drawing in its breath (kind 4, "drain"): a ring of faint specks of light closing in
// on its mouth (the breath drawn in, in the grains' own language: points, not a drawn circle).
// instance: x0 y0 | o dur | f b ; colour: own sRGB (0..1) | lift ; custom: seg nt kind seed
//   o: departure (s after the drain began), dur: s to the gate; f: where its second control point lies
//   on the way from the gate (0) to the town (1), b: how far off that way, across it (px; > 0 to the
//   left and down, away from the sky shore's pagoda), lift: how high it rises straight up first (px);
//   seed: the grain's number (+ 0.25 with a halo): its sideways drift and its point in the mouth
// Output: sRGB units into the rising lights' buffer (composite.gdshader), cores pushed into HDR.
shader_type canvas_item;
render_mode blend_add, skip_vertex_transform;
#include "res://vista/shaders/vista.gdshaderinc"

uniform float el = -1.0;       // seconds since the drain began (< 0: none)
uniform float fl = -1.0;       // seconds since the burst (< 0: none)
uniform vec2 town;             // canvas px: the middle of the town (ground zero)
uniform vec2 gate;             // canvas px: the gate's mouth
uniform float bloom = 0.35;
uniform float gate_k = 0.0;    // the gate's flare in the burst's frame (variant "flash"): 1, else 0
uniform vec2 inhale_t = vec2(0.3, 0.9);   // the gate's breath (s after the drain began)

varying flat vec4 v_core;      // core x, y, size, alpha
varying flat vec4 v_glow;      // glow centre x, y, radius, alpha (ring: radius, alpha)
varying flat vec3 v_rc;
varying flat float v_seg;
varying flat float v_kind;
varying vec2 v_px;

const vec3 C_JADE = vec3(196.0, 246.0, 226.0);
const vec3 C_BURST = vec3(232.0, 240.0, 255.0);

vec2 bez(vec2 a, vec2 b, vec2 c, vec2 d, float s) {
	float u = 1.0 - s;
	return u * u * u * a + 3.0 * u * u * s * b + 3.0 * u * s * s * c + s * s * s * d;
}

// where a grain is at s (0 its pixel of the town .. 1 the gate's mouth): its own curve
// (VistaSouthDrain.pos_at is the same on the CPU)
vec2 pos_at(vec2 p0, float lift, float f, float b, float seed, float s) {
	vec2 way = town - gate;
	vec2 across = normalize(vec2(-way.y, way.x));
	int k = int(seed);
	vec2 p1 = p0 + vec2((hash2(k, 1, 71) - 0.5) * 6.0, -lift);
	vec2 p2 = gate + way * f + across * b;
	vec2 p3 = gate + vec2((hash2(k, 2, 71) - 0.5) * 3.0, 1.0 + (hash2(k, 3, 71) - 0.5) * 2.0);
	return bez(p0, p1, p2, p3, s);
}

void vertex() {
	vec2 p0 = MODEL_MATRIX[0].xy;
	float o = MODEL_MATRIX[1].x, dur = MODEL_MATRIX[1].y;
	float f = MODEL_MATRIX[2].x, b = MODEL_MATRIX[2].y;
	vec2 world = MODEL_MATRIX[3].xy;
	vec2 corner = VERTEX;          // the unit quad's corner (VERTEX is overwritten below)
	vec3 own = COLOR.rgb * 255.0;
	float lift = COLOR.a;
	float seg = INSTANCE_CUSTOM.r, nt = INSTANCE_CUSTOM.g, kind = INSTANCE_CUSTOM.b, sd = INSTANCE_CUSTOM.a;
	bool halo = fract(sd) > 0.1;
	float seed = floor(sd);
	v_seg = seg;
	v_kind = kind;
	v_core = vec4(0.0);
	v_glow = vec4(0.0);
	v_rc = own;
	VERTEX = vec2(-100000.0);
	if (kind > 3.5) {
		// the gate drawing in its breath: specks of jade closing in on its mouth, turning a little
		float k = smoothj(inhale_t.x, inhale_t.y, el);
		if (el >= inhale_t.x && k < 0.999) {
			float r = mix(13.0, 2.0, k);
			v_rc = C_JADE;
			v_core = vec4(0.0, 0.0, 0.0, 0.6 * k);    // (x: unused; w: how far round the specks have turned)
			v_glow = vec4(vec2(roundj(gate.x), roundj(gate.y)), r, 0.5 * sin(3.14159 * k));
			vec2 lo = v_glow.xy - 14.0, hi = v_glow.xy + 15.0;
			v_px = lo + corner * (hi - lo);
			VERTEX = world + v_px;
		}
	} else if (kind > 1.5) {
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
			// slow off the ground, then faster and faster
			float s = u * 0.2 + u * u * 0.8;
			float kk = smoothj(0.45, 0.88, s);
			v_rc = mix(own, C_JADE, kk * kk * (3.0 - 2.0 * kk));
			float a = smoothj(0.0, 0.12, u) * (1.0 - smoothj(0.95, 1.0, s) * 0.6) * 0.75;
			if (seg > nt) {
			} else if (seg < 0.5) {
				vec2 q = pos_at(p0, lift, f, b, seed, s);
				vec2 c = vec2(roundj(q.x), roundj(q.y));
				v_core = vec4(c, 1.0, a);
				float r = halo ? 2.0 : 0.0;
				v_glow = vec4(c, r, halo ? a * 0.3 : 0.0);
				vec2 lo = c - r, hi = c + r + 1.0;
				v_px = lo + corner * (hi - lo);
				VERTEX = world + v_px;
			} else {
				// the tail: back along its own curve, a little longer the faster it goes
				float ds = max(0.012, (0.2 + 1.6 * u) / 30.0 / dur * 0.6);
				vec2 q = pos_at(p0, lift, f, b, seed, max(0.0, s - seg * ds));
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
	if (v_kind > 3.5) {
		// the breath: 12 specks on a circle of the radius, each the pixel nearest its place
		vec2 d = p - v_glow.xy;
		float ang = atan(d.y, d.x) - v_core.w;
		float spoke = floor(ang / (6.2831853 / 12.0) + 0.5) * (6.2831853 / 12.0) + v_core.w;
		vec2 sp = vec2(roundj(cos(spoke) * v_glow.z), roundj(sin(spoke) * v_glow.z));
		if (d == sp) c += v_rc * v_glow.w;
	} else {
		vec2 d = p - v_core.xy;
		if (d.x >= 0.0 && d.y >= 0.0 && d.x < v_core.z && d.y < v_core.z) {
			c += mix(v_rc, vec3(255.0), v_kind > 1.5 ? 0.25 : 0.12) * v_core.w;
			hdr = v_seg < 0.5 ? v_core.w * (v_kind > 1.5 ? 2.0 : 1.0) : 0.0;
		}
		if (v_glow.z > 0.0) c += v_rc * v_glow.w * (v_kind > 1.5 ? glow_w2(p - v_glow.xy, v_glow.z) : glow_w(p - v_glow.xy, v_glow.z));
	}
	COLOR = vec4(min(c, vec3(255.0)) / 255.0 + v_rc / 255.0 * hdr * bloom, 1.0);
}
