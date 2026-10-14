/* SDF ray caster for the character sprites (tools/art/sprite3d). Orthographic rays along -z in
 * camera space (x right, y up, z toward the viewer). Called from Python through ctypes; compiled on
 * demand by render.py. Deterministic (no randomness, no threads).
 *
 * A primitive is STRIDE floats:
 *   0 type  1 material  2 part  3 group (-1 = none)  4 blend k  5 flags (1 = occluder only)
 *   6..17   camera -> local affine (3x4, row major: local = R p + t)
 *   18..29  shape parameters (see sd_prim)
 *   30..33  bounding sphere in camera space (cx, cy, cz, r), r already includes blend k
 *   34      band count (0..4)
 *   35..62  bands, 7 floats each: axis, lo, hi, material, wave amplitude, wave count, wave phase
 *           axis 0/1/2 = local x/y/z, 3 = radius in the local xz plane, 4 = angle about local y
 *           (degrees, atan2(x, z)); the wave moves lo and hi by amp * sin(count * angle + phase).
 *   64..67  optional cut plane in the shape frame (nx, ny, nz, d): keeps n.q <= d
 */
#include <math.h>
#include <stdint.h>
#include <string.h>

#define STRIDE 72
#define MAXCAND 160
#define MAXGROUP 64

enum { P_ELLIPSOID = 0, P_ROUNDCONE = 1, P_BOX = 2, P_CONE = 3, P_CYL = 4, P_TORUS = 5, P_SKIRT = 6, P_HALFELL = 7 };

static inline float clampf(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
static inline float maxf(float a, float b) { return a > b ? a : b; }
static inline float minf(float a, float b) { return a < b ? a : b; }
static inline float signf(float x) { return x < 0.f ? -1.f : 1.f; }

static inline float smin(float a, float b, float k) {
    if (k <= 0.f) return minf(a, b);
    float h = maxf(k - fabsf(a - b), 0.f) / k;
    return minf(a, b) - h * h * k * 0.25f;
}

static inline void to_local(const float *P, const float *p, float *q) {
    const float *M = P + 6;
    q[0] = M[0] * p[0] + M[1] * p[1] + M[2] * p[2] + M[3];
    q[1] = M[4] * p[0] + M[5] * p[1] + M[6] * p[2] + M[7];
    q[2] = M[8] * p[0] + M[9] * p[1] + M[10] * p[2] + M[11];
}

static float sd_ellipsoid(const float *q, const float *r) {
    float a = q[0] / r[0], b = q[1] / r[1], c = q[2] / r[2];
    float k0 = sqrtf(a * a + b * b + c * c);
    float a2 = q[0] / (r[0] * r[0]), b2 = q[1] / (r[1] * r[1]), c2 = q[2] / (r[2] * r[2]);
    float k1 = sqrtf(a2 * a2 + b2 * b2 + c2 * c2);
    if (k1 < 1e-6f) return -minf(r[0], minf(r[1], r[2]));
    return k0 * (k0 - 1.f) / k1;
}

/* iq's round cone between a (radius r1) and b (radius r2) */
static float sd_roundcone(const float *p, const float *a, const float *b, float r1, float r2) {
    float ba[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
    float l2 = ba[0] * ba[0] + ba[1] * ba[1] + ba[2] * ba[2];
    if (l2 < 1e-8f) {
        float d[3] = {p[0] - a[0], p[1] - a[1], p[2] - a[2]};
        return sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]) - maxf(r1, r2);
    }
    float rr = r1 - r2;
    float a2 = l2 - rr * rr;
    float il2 = 1.f / l2;
    float pa[3] = {p[0] - a[0], p[1] - a[1], p[2] - a[2]};
    float y = pa[0] * ba[0] + pa[1] * ba[1] + pa[2] * ba[2];
    float z = y - l2;
    float w[3] = {pa[0] * l2 - ba[0] * y, pa[1] * l2 - ba[1] * y, pa[2] * l2 - ba[2] * y};
    float x2 = w[0] * w[0] + w[1] * w[1] + w[2] * w[2];
    float y2 = y * y * l2;
    float z2 = z * z * l2;
    float k = signf(rr) * rr * rr * x2;
    if (signf(z) * a2 * z2 > k) return sqrtf(x2 + z2) * il2 - r2;
    if (signf(y) * a2 * y2 < k) return sqrtf(x2 + y2) * il2 - r1;
    return (sqrtf(x2 * a2 * il2) + y * rr) * il2 - r1;
}

static float sd_box(const float *q, const float *b, float r) {
    float d0 = fabsf(q[0]) - b[0] + r, d1 = fabsf(q[1]) - b[1] + r, d2 = fabsf(q[2]) - b[2] + r;
    float m0 = maxf(d0, 0.f), m1 = maxf(d1, 0.f), m2 = maxf(d2, 0.f);
    return sqrtf(m0 * m0 + m1 * m1 + m2 * m2) + minf(maxf(d0, maxf(d1, d2)), 0.f) - r;
}

/* iq's capped cone along y: bottom radius r1 at y=-h, top radius r2 at y=+h */
static float sd_capcone2(float qx, float qy, float h, float r1, float r2) {
    float k1x = r2, k1y = h;
    float k2x = r2 - r1, k2y = 2.f * h;
    float cax = qx - minf(qx, (qy < 0.f) ? r1 : r2), cay = fabsf(qy) - h;
    float t = ((k1x - qx) * k2x + (k1y - qy) * k2y) / (k2x * k2x + k2y * k2y);
    t = clampf(t, 0.f, 1.f);
    float cbx = qx - k1x + k2x * t, cby = qy - k1y + k2y * t;
    float s = (cbx < 0.f && cay < 0.f) ? -1.f : 1.f;
    return s * sqrtf(minf(cax * cax + cay * cay, cbx * cbx + cby * cby));
}

static float sd_prim_raw(const float *P, const float *q);

/* every primitive may carry a cut plane (64..67: nx, ny, nz, d in its frame): the shape keeps the
 * half space n.q <= d. A zero normal means no cut. */
static float sd_prim(const float *P, const float *q) {
    float d = sd_prim_raw(P, q);
    const float *c = P + 64;
    if (c[0] != 0.f || c[1] != 0.f || c[2] != 0.f) d = maxf(d, c[0] * q[0] + c[1] * q[1] + c[2] * q[2] - c[3]);
    return d;
}

static float sd_prim_raw(const float *P, const float *q) {
    const float *a = P + 18;
    int type = (int)P[0];
    switch (type) {
    case P_ELLIPSOID:
        return sd_ellipsoid(q, a);
    case P_HALFELL: { /* ellipsoid cut by the plane local y = a[3] (keeps y >= cut) */
        float d = sd_ellipsoid(q, a);
        return maxf(d, a[3] - q[1]);
    }
    case P_ROUNDCONE:
        return sd_roundcone(q, a, a + 4, a[3], a[7]);
    case P_BOX:
        return sd_box(q, a, a[3]);
    case P_CONE: { /* a: h, r1, r2, rounding, sx, sz (elliptic section) */
        float sx = a[4] > 0.f ? a[4] : 1.f, sz = a[5] > 0.f ? a[5] : 1.f;
        float qx = sqrtf((q[0] / sx) * (q[0] / sx) + (q[2] / sz) * (q[2] / sz)) * minf(sx, sz);
        return sd_capcone2(qx, q[1], a[0] - a[3], a[1] - a[3], a[2] - a[3]) - a[3];
    }
    case P_CYL: { /* a: h, r, rounding */
        float rr = a[2];
        float dx = sqrtf(q[0] * q[0] + q[2] * q[2]) - (a[1] - rr), dy = fabsf(q[1]) - (a[0] - rr);
        float mx = maxf(dx, 0.f), my = maxf(dy, 0.f);
        return minf(maxf(dx, dy), 0.f) + sqrtf(mx * mx + my * my) - rr;
    }
    case P_TORUS: { /* a: R, r */
        float l = sqrtf(q[0] * q[0] + q[2] * q[2]) - a[0];
        return sqrtf(l * l + q[1] * q[1]) - a[1];
    }
    case P_SKIRT: { /* a: h, r1 (hem), r2 (waist), sx, sz, hem wave amp, wave count, phase, flare amp, flare count, flare phase, rounding
                     * a negative wave count makes pointed tips (|sin|): panels that hang to points */
        float sx = a[3] > 0.f ? a[3] : 1.f, sz = a[4] > 0.f ? a[4] : 1.f;
        float ang = atan2f(q[0], q[2]);
        float f = clampf((a[0] - q[1]) / (2.f * a[0]), 0.f, 1.f); /* 0 at the waist, 1 at the hem */
        float wv = a[6] >= 0.f ? sinf(a[6] * ang + a[7]) : (1.f - 2.f * fabsf(sinf(-a[6] * 0.5f * ang + a[7])));
        float qy = q[1] - a[5] * wv * f;
        float flare = a[8] * sinf(a[9] * ang + a[10]) * f * f;
        float rr = a[11];
        float qx = sqrtf((q[0] / sx) * (q[0] / sx) + (q[2] / sz) * (q[2] / sz)) * minf(sx, sz) - flare;
        return sd_capcone2(qx, qy, a[0] - rr, a[1] - rr, a[2] - rr) - rr;
    }
    }
    return 1e9f;
}

/* scene distance at p over candidate prims; nearest raw prim index in *best */
static float scene(const float *prims, const int *cand, int nc, const float *p, int *best, int include_occ) {
    float gd[MAXGROUP];
    for (int g = 0; g < MAXGROUP; g++) gd[g] = 1e9f;
    float d = 1e9f, braw = 1e9f;
    int bi = -1;
    for (int c = 0; c < nc; c++) {
        const float *P = prims + (size_t)cand[c] * STRIDE;
        if (!include_occ && ((int)P[5] & 1)) continue;
        float q[3];
        to_local(P, p, q);
        float di = sd_prim(P, q);
        int g = (int)P[3];
        if (g >= 0 && g < MAXGROUP) gd[g] = smin(gd[g], di, P[4]);
        else d = minf(d, di);
        if (di < braw) { braw = di; bi = cand[c]; }
    }
    for (int g = 0; g < MAXGROUP; g++) d = minf(d, gd[g]);
    if (best) *best = bi;
    return d;
}

static int band_material(const float *P, const float *q, int mat) {
    int nb = (int)P[34];
    for (int b = 0; b < nb && b < 4; b++) {
        const float *B = P + 35 + b * 7;
        int axis = (int)B[0];
        float v;
        if (axis <= 2) v = q[axis];
        else if (axis == 3) v = sqrtf(q[0] * q[0] + q[2] * q[2]);
        else v = atan2f(q[0], q[2]) * 57.2957795f;
        float lo = B[1], hi = B[2];
        if (B[4] != 0.f) {
            float ang = atan2f(q[0], q[2]);
            float w = B[4] * sinf(B[5] * ang + B[6]);
            lo += w; hi += w;
        }
        if (v >= lo && v <= hi) mat = (int)B[3];
    }
    return mat;
}

/* Renders W x H rays. Ray (i, j) starts at (x0 + (i+.5) dx, y0 - (j+.5) dy, zmax) and runs to zmin.
 * light: unit vector toward the key light (camera space). Outputs per ray: depth (z; -1e9 on miss),
 * material (-1 miss, -2 occluder hole), part, normal xyz, ambient occlusion (0..1, 1 = open),
 * shadow (0..1, 1 = lit), and the local coordinates of the hit in its primitive (for patterns). */
int render(const float *prims, int np, int W, int H, float x0, float y0, float dx, float dy,
           float zmax, float zmin, const float *light, float ao_dist, float shadow_k,
           float *o_depth, int16_t *o_mat, int16_t *o_part, float *o_nrm, float *o_ao, float *o_sh, float *o_loc) {
    int cand[MAXCAND];
    int all[MAXCAND];
    int nall = np < MAXCAND ? np : MAXCAND;
    for (int i = 0; i < nall; i++) all[i] = i;
    int hits = 0;
    for (int j = 0; j < H; j++) {
        for (int i = 0; i < W; i++) {
            size_t o = (size_t)j * W + i;
            float px = x0 + (i + 0.5f) * dx, py = y0 - (j + 0.5f) * dy;
            int nc = 0;
            float zstart = -1e9f;
            for (int k = 0; k < np && nc < MAXCAND; k++) {
                const float *P = prims + (size_t)k * STRIDE;
                float ex = px - P[30], ey = py - P[31], r = P[33];
                float d2 = ex * ex + ey * ey;
                if (d2 <= r * r) {
                    cand[nc++] = k;
                    float zz = P[32] + sqrtf(r * r - d2);
                    if (zz > zstart) zstart = zz;
                }
            }
            o_depth[o] = -1e9f; o_mat[o] = -1; o_part[o] = -1;
            o_nrm[o * 3] = 0.f; o_nrm[o * 3 + 1] = 0.f; o_nrm[o * 3 + 2] = 1.f;
            o_ao[o] = 1.f; o_sh[o] = 1.f;
            o_loc[o * 3] = o_loc[o * 3 + 1] = o_loc[o * 3 + 2] = 0.f;
            if (nc == 0) continue;
            float z = minf(zstart + 0.01f, zmax);
            float p[3] = {px, py, z};
            int best = -1, hit = 0;
            for (int it = 0; it < 400 && p[2] > zmin; it++) {
                float d = scene(prims, cand, nc, p, &best, 1);
                if (d < 0.0015f) { hit = 1; break; }
                p[2] -= maxf(d * 0.8f, 0.0015f);
            }
            if (!hit || best < 0) continue;
            hits++;
            const float *P = prims + (size_t)best * STRIDE;
            o_depth[o] = p[2];
            if ((int)P[5] & 1) { o_mat[o] = -2; o_part[o] = (int16_t)P[2]; continue; }
            float q[3];
            to_local(P, p, q);
            o_mat[o] = (int16_t)band_material(P, q, (int)P[1]);
            o_part[o] = (int16_t)P[2];
            o_loc[o * 3] = q[0]; o_loc[o * 3 + 1] = q[1]; o_loc[o * 3 + 2] = q[2];
            /* normal: tetrahedron differences, visible geometry only */
            const float h = 0.02f;
            const float K[4][3] = {{1, -1, -1}, {-1, -1, 1}, {-1, 1, -1}, {1, 1, 1}};
            float n[3] = {0, 0, 0};
            for (int t = 0; t < 4; t++) {
                float s[3] = {p[0] + K[t][0] * h, p[1] + K[t][1] * h, p[2] + K[t][2] * h};
                float v = scene(prims, cand, nc, s, NULL, 0);
                n[0] += K[t][0] * v; n[1] += K[t][1] * v; n[2] += K[t][2] * v;
            }
            float ln = sqrtf(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
            if (ln > 1e-9f) { n[0] /= ln; n[1] /= ln; n[2] /= ln; } else { n[0] = 0; n[1] = 0; n[2] = 1; }
            o_nrm[o * 3] = n[0]; o_nrm[o * 3 + 1] = n[1]; o_nrm[o * 3 + 2] = n[2];
            /* ambient occlusion (all prims, not just this ray's candidates) */
            if (ao_dist > 0.f) {
                float occ = 0.f, sca = 1.f;
                for (int s = 1; s <= 5; s++) {
                    float hh = ao_dist * s / 5.f;
                    float sp[3] = {p[0] + n[0] * hh, p[1] + n[1] * hh, p[2] + n[2] * hh};
                    float dd = scene(prims, all, nall, sp, NULL, 0);
                    occ += (hh - dd) * sca;
                    sca *= 0.75f;
                }
                o_ao[o] = clampf(1.f - 1.6f * occ / ao_dist, 0.f, 1.f);
            }
            /* soft shadow toward the light */
            if (shadow_k > 0.f) {
                float res = 1.f, t = 0.25f;
                for (int s = 0; s < 64 && t < 60.f; s++) {
                    float sp[3] = {p[0] + n[0] * 0.05f + light[0] * t, p[1] + n[1] * 0.05f + light[1] * t, p[2] + n[2] * 0.05f + light[2] * t};
                    float dd = scene(prims, all, nall, sp, NULL, 0);
                    if (dd < 0.002f) { res = 0.f; break; }
                    res = minf(res, shadow_k * dd / t);
                    t += clampf(dd, 0.05f, 2.f);
                }
                o_sh[o] = clampf(res, 0.f, 1.f);
            }
        }
    }
    return hits;
}
