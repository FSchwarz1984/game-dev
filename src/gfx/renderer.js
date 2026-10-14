/* =====================================================================
   gfx/renderer — the 2D deferred pixel pipeline (WebGL2).

   Frame: sun shadow map (terrain back faces + sprite cards) → backdrop
   (sky and painted far layers, parallax) → G-buffer at native res
   (baked ground chunks, atlas sprites, character sheets) → lighting
   (banded sun with soft canopy flecks, sky and bounce, up to 32 point
   lights, emission, mist and light shafts, the Far, protected character
   light) → water (refraction, reflection, foam, falls) → occluders that
   hide a character (forward-lit, dithered fade) → particles and glows →
   bloom → composite (integer upscale with a sub-pixel camera offset,
   tone map, grade, vignette, letterbox, fade).

   Native resolution: the integer scale s is chosen so the view's area is
   closest to 480×270; the view then extends to fill any aspect ratio
   (no stretching, no letterbox): 1920×1080 → 480×270 at ×4, 390×844
   (dpr 3) → 234×506 at ×5, 844×390 → 506×234 at ×5.

   Units: the public API takes metres (x east, z south, y up) like the
   gameplay simulation; internally world px (1 m = 20 px).

   Public API (see src/gfx/index.js for the summary):
     const R = new Renderer(canvas, { quality: 'auto'|'high'|'mid'|'low' })
     R.loadMap(map)                     map from env/home.js createHomeMap()
     R.setTime(hours)                   17.5 dusk … 21 night, 7 morning
     R.setCamera({x, z, y}, speed)      target (metres) + follow speed (1/s); speed 0 = cut
     R.camera.snap()                    jump to the target now
     R.setFocus(x, z, y)                the protected character (fades, Far recede)
     R.addSprite(name, {x, z, y, ...})  → handle  (atlas sprite; name from map.sprites)
     R.setFar(handleOrName, amount)     0..1
     R.paintFar({x, z, rx, rz, amount, angle, ragged})   ground far mask
     R.addLight({x, z, y, color, radius, intensity, flicker}) → {set(o), remove()}
     R.loadSheet(name, albedoImg, normalImg, o) / R.addActor(sheet, o) → {set(o), remove()}
     R.fx (Particles), R.render(dt), R.stats
   ===================================================================== */
import { GLX, M4 } from './gl.js';
import * as SH from './shaders.js';
import { todEnv, PRESETS } from './tod.js';
import { Particles } from './particles.js';

const PPM = 20;
const SL = [['p', 4], ['s', 4], ['a', 4], ['b', 4], ['t', 4], ['x', 4]]; // sprite instance layout (24 floats)
const SF = 24;
export const FLAGS = { FLIP: 1, SHADOW: 2, OCCLUDER: 4, FOLIAGE: 8, CHAR: 16, EMISSIVE: 32, HIDDEN: 64 };

const QUALITY = {
  high: { shadow: 2048, pcf: 1, shafts: 10, ssr: 110, bloom: 2, particles: 1, flecks: 1 },
  mid: { shadow: 1536, pcf: 1, shafts: 6, ssr: 60, bloom: 1, particles: 0.7, flecks: 1 },
  low: { shadow: 1024, pcf: 1, shafts: 0, ssr: 0, bloom: 1, particles: 0.4, flecks: 0.6 },
};

export class Renderer {
  constructor(canvas, o = {}) {
    this.cv = canvas; this.x = new GLX(canvas, { preserve: o.preserve }); const gl = this.x.gl; this.gl = gl;
    this.q = this.pickQuality(o.quality); this.Q = QUALITY[this.q];
    this.dprCap = o.dprCap || 3;
    this.P = {};
    const C = SH.COMMON, P = this.P, X = this.x;
    P.ground = X.prog('ground', C + SH.groundVS, C + SH.groundFS);
    P.water = X.prog('water', C + SH.waterVS, C + SH.waterFS);
    P.spriteG = X.prog('spriteG', C + SH.spriteVS, C + SH.spriteGFS(false));
    P.sheetG = X.prog('sheetG', C + SH.spriteVS, C + SH.spriteGFS(true));
    P.spriteS = X.prog('spriteS', C + SH.spriteVS, C + SH.spriteShadowFS(false));
    P.sheetS = X.prog('sheetS', C + SH.spriteVS, C + SH.spriteShadowFS(true));
    P.spriteF = X.prog('spriteF', C + SH.spriteVS, C + SH.spriteFwdFS(false));
    P.shTerrain = X.prog('shTerrain', C + SH.shTerrainVS, C + SH.shTerrainFS);
    P.light = X.prog('light', C + SH.fsVS, C + SH.lightFS);
    P.back = X.prog('back', C + SH.fsVS, C + SH.backFS);
    P.part = X.prog('part', C + SH.partVS, C + SH.partFS);
    P.partAdd = X.prog('partAdd', C + SH.partVS, C + SH.partAddFS);
    P.glow = X.prog('glow', C + SH.glowVS, C + SH.glowFS);
    P.copy = X.prog('copy', SH.fsVS, SH.copyFS);
    P.bright = X.prog('bright', SH.fsVS, SH.brightFS);
    P.blur = X.prog('blur', SH.fsVS, SH.blurFS);
    P.comp = X.prog('comp', C + SH.fsVS, SH.compFS.replace('in vec2 vUV;', 'in vec2 vUV;\nfloat lum(vec3 c){ return dot(c,vec3(.299,.587,.114)); }'));
    const q = new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]); const qi = [0, 1, 2, 0, 2, 3];
    this.quad = () => X.mesh(q, [['q', 2]], qi);
    this.unitQuad = this.quad();
    this.dyn = this.quad(); this.dyn.inst = X.inst(this.dyn, SL, 1024); this.dynList = [];
    this.glowQ = this.quad(); this.glowQ.inst = X.inst(this.glowQ, [['p', 4], ['s', 4], ['c', 4]], 512);
    // particles
    const pv = gl.createVertexArray(); gl.bindVertexArray(pv); const pb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, pb);
    gl.bufferData(gl.ARRAY_BUFFER, 8 * 4 * 8000, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 32, 0); gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 4, gl.FLOAT, false, 32, 16);
    gl.bindVertexArray(null);
    this.parts = { vao: pv, buf: pb, data: new Float32Array(8 * 6000), n: 0, add: new Float32Array(8 * 2000), na: 0 };
    this.fx = new Particles(5000);
    this.f = {}; this.W = 0; this.H = 0; this.scale = 1;
    this.cam = { x: 0, y: 0, tx: 0, ty: 0, speed: 4, shake: 0, sx: 0, sy: 0, off: [0, 0], bounds: null, zoomFixed: true };
    this.camera = { snap: () => { this.cam.x = this.cam.tx; this.cam.y = this.cam.ty; } };
    this.t = 0; this.hour = 12; this.wind = [1, 0.25, 0.3]; this.env = todEnv(this.hour, { wind: this.wind });
    this.fade = [0, 0, 0, 0]; this.box = 0;
    this.lights = new Set(); this.lp = new Float32Array(128); this.lc = new Float32Array(128); this.frameLights = [];
    this.focus = null; this.charSlots = new Float32Array(32);
    this.actors = new Set(); this.sheets = {};
    this.stats = { calls: 0, passes: 0, ms: 0 };
    this.lastLVP = new Float32Array(16);
    this.resize();
    if (o.autoResize !== false) addEventListener('resize', () => this.resize());
  }
  pickQuality(q) {
    if (q && QUALITY[q]) return q;
    const touch = typeof matchMedia !== 'undefined' && matchMedia('(pointer:coarse)').matches;
    const cores = (typeof navigator !== 'undefined' && navigator.hardwareConcurrency) || 4;
    return touch ? (cores >= 6 ? 'mid' : 'low') : 'high';
  }
  setQuality(q) {
    if (!QUALITY[q]) return; this.q = q; this.Q = QUALITY[q];
    if (this.f.sh && this.f.sh.w !== this.Q.shadow) { this.f.sh.free(); this.f.sh = null; }
    this.ensureShadow();
  }
  ensureShadow() { if (!this.f.sh) { const S = this.Q.shadow; this.f.sh = this.x.fbo(S, S, [{}], 'cmp'); } }
  /** canvas size (device px) → integer scale and native view size */
  resize(w, h) {
    const dpr = Math.min(typeof devicePixelRatio !== 'undefined' ? devicePixelRatio : 1, this.dprCap);
    const W = Math.max(64, Math.round((w ?? this.cv.clientWidth ?? innerWidth) * dpr)), H = Math.max(64, Math.round((h ?? this.cv.clientHeight ?? innerHeight) * dpr));
    this.cv.width = W; this.cv.height = H; this.scrW = W; this.scrH = H;
    const s = Math.max(1, Math.round(Math.sqrt((W * H) / (480 * 270))));
    this.scale = s;
    let lw = Math.ceil(W / s) + 2, lh = Math.ceil(H / s) + 2; lw += lw & 1; lh += lh & 1;
    if (lw === this.W && lh === this.H && this.f.g) return;
    this.W = lw; this.H = lh; this.viewW = W / s; this.viewH = H / s;
    for (const k of ['g', 'lit', 'post', 'postN', 'b1', 'b2', 'back']) if (this.f[k]) { this.f[k].free(); this.f[k] = null; }
    const gl = this.gl, X = this.x, hdr = X.hdr ? { ifmt: gl.RGBA16F, fmt: gl.RGBA, type: gl.HALF_FLOAT } : {};
    this.f.g = X.fbo(lw, lh, [{}, {}, {}], true);
    this.f.lit = X.fbo(lw, lh, [hdr], null);
    this.f.back = X.fbo(lw, lh, [{}], null);
    this.f.post = X.fbo(lw, lh, [hdr], this.f.g.depth);
    this.f.postN = X.view(this.f.post.tex, lw, lh);
    const hw = Math.max(8, lw >> 1), hh = Math.max(8, lh >> 1);
    this.f.b1 = X.fbo(hw, hh, [Object.assign({ linear: true }, hdr)], null); this.f.b2 = X.fbo(hw, hh, [Object.assign({ linear: true }, hdr)], null);
    this.ensureShadow();
  }

  /* ---------------- world upload ---------------- */
  loadMap(map) {
    const gl = this.gl, X = this.x, M = map.render; this.map = map; this.M = M;
    // ground and water chunks
    this.chunks = M.ground.map(c => ({
      sx: c.sx, sy: c.sy, w: c.w, h: c.h,
      t0: c.t0 ? X.tex(c.w, c.h, c.t0) : null, t1: c.t1 ? X.tex(c.w, c.h, c.t1) : null,
      w0: c.w0 ? X.tex(c.w, c.h, c.w0) : null, w1: c.w1 ? X.tex(c.w, c.h, c.w1) : null,
    }));
    // terrain proxy for the shadow pass: heightfield chunks, back faces only
    this.shChunks = []; const Zg = M.zgrid; const CC = 48;
    for (let cy = 0; cy < Zg.h - 1; cy += CC) for (let cx = 0; cx < Zg.w - 1; cx += CC) {
      const nx = Math.min(CC, Zg.w - 1 - cx), ny = Math.min(CC, Zg.h - 1 - cy), v = new Float32Array((nx + 1) * (ny + 1) * 3), idx = [];
      let zmin = 1e9, zmax = -1e9;
      for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) { const z = Zg.data[(cy + j) * Zg.w + cx + i]; const k = (j * (nx + 1) + i) * 3; v[k] = Zg.x0 + (cx + i) * Zg.cell; v[k + 1] = Zg.y0 + (cy + j) * Zg.cell; v[k + 2] = z; zmin = Math.min(zmin, z); zmax = Math.max(zmax, z); }
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
      this.shChunks.push({ x0: Zg.x0 + cx * Zg.cell, y0: Zg.y0 + cy * Zg.cell, x1: Zg.x0 + (cx + nx) * Zg.cell, y1: Zg.y0 + (cy + ny) * Zg.cell, zmin, zmax, mesh: X.mesh(v, [['p', 3]], idx) });
    }
    // atlas → texture arrays
    const A = M.atlas, L = A.pages.length;
    this.tAlb = X.texArray(A.W, A.H, L); this.tNrm = X.texArray(A.W, A.H, L);
    A.pages.forEach((p, i) => { X.texArraySub(this.tAlb, i, 0, 0, A.W, A.H, p.alb); X.texArraySub(this.tNrm, i, 0, 0, A.W, A.H, p.nrm); });
    this.atlas = A;
    // static sprite instances, bucketed by world-screen tile for culling
    this.statics = []; this.byName = {};
    for (const s of M.statics) this.statics.push(Object.assign({}, s));
    this.buildBuckets();
    // a blurred, coarse height grid (16 px cells) for the depth haze in the lighting pass
    { const hc = 4, hw = Math.ceil(Zg.w / hc), hh = Math.ceil(Zg.h / hc); let hz = new Float32Array(hw * hh);
      for (let j = 0; j < hh; j++) for (let i = 0; i < hw; i++) { let a = 0, n = 0; for (let v = 0; v < hc; v++) for (let u = 0; u < hc; u++) { const x = i * hc + u, y = j * hc + v; if (x < Zg.w && y < Zg.h) { a += Zg.data[y * Zg.w + x]; n++; } } hz[j * hw + i] = n ? a / n : 0; }
      for (let pass = 0; pass < 2; pass++) { const o = new Float32Array(hw * hh); for (let j = 0; j < hh; j++) for (let i = 0; i < hw; i++) { let a = 0, n = 0; for (let v = -1; v <= 1; v++) for (let u = -1; u <= 1; u++) { const x = i + u, y = j + v; if (x >= 0 && y >= 0 && x < hw && y < hh) { a += hz[y * hw + x]; n++; } } o[j * hw + i] = a / n; } hz = o; }
      this.tZG = X.tex(hw, hh, hz, { ifmt: gl.R16F, fmt: gl.RED, type: gl.FLOAT, linear: true });
      this.zgR = [Zg.x0, Zg.y0, 1 / (hw * Zg.cell * hc), 1 / (hh * Zg.cell * hc)]; }
    // far mask
    const F = M.far; this.farM = F; this.tFar = X.tex(F.w, F.h, F.data, { ifmt: gl.R8, fmt: gl.RED, linear: true });
    // backdrop layer
    const B = M.backdrop; this.backL = B; this.tBack = B ? X.tex(B.w, B.h, B.data) : X.tex(1, 1, new Uint8Array(4));
    this.fx.setMap((x, y) => map.heightPx(x, y), M.emitters);
    this.boundsPx = M.bounds; this.cam.bounds = M.camBounds;
    this.sprites = map.sprites;
    if (map.spawn) { this.setCamera(map.spawn, 0); this.camera.snap(); }
    return this;
  }
  buildBuckets() {
    const gl = this.gl, X = this.x, T = 512; const S = this.statics; const map = new Map();
    S.forEach((s, i) => { s.i = i; const key = Math.floor(s.x / T) + ',' + Math.floor((s.y - s.z) / T); if (!map.has(key)) map.set(key, []); map.get(key).push(s); });
    // one shared buffer; each bucket gets its own VAO with the instance attributes offset into it
    const order = []; this.buckets = [];
    for (const [, list] of map) { const start = order.length; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const s of list) { order.push(s); const r = s.r; x0 = Math.min(x0, s.x - r.ax - 4); x1 = Math.max(x1, s.x + r.w - r.ax + 4); y0 = Math.min(y0, s.y - s.z - r.ay - 12); y1 = Math.max(y1, s.y - s.z + r.h - r.ay + 4); }
      this.buckets.push({ start, n: list.length, x0, y0, x1, y1 }); }
    order.forEach((s, i) => { s.slot = i; if (s.name) this.byName[s.name] = s; });
    this.staticOrder = order;
    this.sbuf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.sbuf);
    this.sdata = new Float32Array(Math.max(1, order.length) * SF);
    order.forEach((s, i) => this.packStatic(s, i));
    gl.bufferData(gl.ARRAY_BUFFER, this.sdata, gl.DYNAMIC_DRAW);
    for (const b of this.buckets) {
      const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.unitQuad.vb); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 8, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.unitQuad.ib);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.sbuf);
      for (let k = 0; k < 6; k++) { gl.enableVertexAttribArray(1 + k); gl.vertexAttribPointer(1 + k, 4, gl.FLOAT, false, SF * 4, (b.start * SF + k * 4) * 4); gl.vertexAttribDivisor(1 + k, 1); }
      gl.bindVertexArray(null); b.vao = vao;
    }
    this.dirty = null;
  }
  packStatic(s, i) {
    const d = this.sdata, k = i * SF, r = s.r;
    let fl = s.flags ?? ((r.shadow ? FLAGS.SHADOW : 0) | (r.foliage ? FLAGS.FOLIAGE : 0) | (r.occluder ? FLAGS.OCCLUDER : 0));
    if (s.flip) fl |= FLAGS.FLIP; if (s.hidden) fl |= FLAGS.HIDDEN; if (s.emissive) fl |= FLAGS.EMISSIVE;
    d[k] = s.x; d[k + 1] = s.y; d[k + 2] = s.z; d[k + 3] = s.sway ?? r.sway;
    d[k + 4] = r.w; d[k + 5] = r.h; d[k + 6] = r.ax; d[k + 7] = r.ay;
    d[k + 8] = r.x; d[k + 9] = r.y; d[k + 10] = r.layer; d[k + 11] = fl;
    d[k + 12] = r.bmin; d[k + 13] = r.bscale; d[k + 14] = s.id ?? ((i % 254) + 1); d[k + 15] = s.far || 0;
    const t = s.tint || [1, 1, 1]; d[k + 16] = t[0]; d[k + 17] = t[1]; d[k + 18] = t[2]; d[k + 19] = s.fade || 0;
    d[k + 20] = s.recede || 0; d[k + 21] = s.scale || 1; d[k + 22] = 0; d[k + 23] = (i * 1.37) % 7;
  }
  markDirty(s) { this.packStatic(s, s.slot); const a = s.slot, b = s.slot + 1; if (!this.dirty) this.dirty = [a, b]; else { this.dirty[0] = Math.min(this.dirty[0], a); this.dirty[1] = Math.max(this.dirty[1], b); } }
  flushStatics() { if (!this.dirty) return; const gl = this.gl; gl.bindBuffer(gl.ARRAY_BUFFER, this.sbuf); gl.bufferSubData(gl.ARRAY_BUFFER, this.dirty[0] * SF * 4, this.sdata, this.dirty[0] * SF, (this.dirty[1] - this.dirty[0]) * SF); this.dirty = null; }

  /* ---------------- objects ---------------- */
  /** resolve a target: static record, map object name (all its parts), or handle */
  resolve(t) {
    if (!t) return [];
    if (Array.isArray(t)) return t.flatMap(x => this.resolve(x));
    if (typeof t === 'string') { if (this.byName[t]) return [this.byName[t]]; const o = this.map && this.map.objects[t]; if (o && o.parts) return o.parts.map(n => this.byName[n]).filter(Boolean); return []; }
    if (t.kind === 'dyn') return [t]; if (t.slot != null) return [t]; if (t.parts) return this.resolve(t.parts);
    return [];
  }
  setFar(target, amount) { for (const s of this.resolve(target)) { s.far = Math.max(0, Math.min(1, amount)); if (s.kind !== 'dyn') this.markDirty(s); } }
  setHidden(target, hidden) { for (const s of this.resolve(target)) { s.hidden = !!hidden; if (s.kind !== 'dyn') this.markDirty(s); } }
  setTint(target, tint) { for (const s of this.resolve(target)) { s.tint = tint; if (s.kind !== 'dyn') this.markDirty(s); } }
  /** swap a static's image (e.g. lantern lit/unlit) */
  setImage(target, spriteName) { const r = this.atlas.get(spriteName); for (const s of this.resolve(target)) { s.r = r; s.emissive = false; if (s.kind !== 'dyn') this.markDirty(s); } }
  /** add a sprite from the atlas. o: {x, z, y (metres), flip, far, tint, dynamic, sway, shadow, occluder, name} → handle */
  addSprite(name, o = {}) {
    const r = this.atlas.get(name);
    const h = { kind: 'dyn', r, x: o.x * PPM, y: o.z * PPM, z: (o.y ?? 0) * PPM, flip: !!o.flip, far: o.far || 0, tint: o.tint, sway: o.sway ?? r.sway, hidden: false, fade: 0, scale: o.scale || 1,
      flags: ((o.shadow ?? r.shadow) ? FLAGS.SHADOW : 0) | (r.foliage ? FLAGS.FOLIAGE : 0) | (o.emissive ? FLAGS.EMISSIVE : 0), id: o.id ?? 200 + (this.dynList.length % 50) };
    h.set = p => { if (p.x != null) h.x = p.x * PPM; if (p.z != null) h.y = p.z * PPM; if (p.y != null) h.z = p.y * PPM; if (p.flip != null) h.flip = p.flip; if (p.far != null) h.far = p.far; if (p.image) h.r = this.atlas.get(p.image); if (p.hidden != null) h.hidden = p.hidden; if (p.tint) h.tint = p.tint; if (p.emissive != null) h.flags = (h.flags & ~FLAGS.EMISSIVE) | (p.emissive ? FLAGS.EMISSIVE : 0); return h; };
    h.remove = () => { const i = this.dynList.indexOf(h); if (i >= 0) this.dynList.splice(i, 1); };
    this.dynList.push(h); return h;
  }

  /* ---------------- character sheets ----------------
     albedo/normal: HTMLImageElement | ImageBitmap | canvas | {w, h, data}.
     o.flipNormalY: true if the normal map is DirectX-style (green down). */
  loadSheet(name, albedo, normal, o = {}) {
    const X = this.x, gl = this.gl;
    const up = img => (img && img.data && img.w) ? X.tex(img.w, img.h, img.data) : X.imgTex(img);
    const w = albedo.w || albedo.width, h = albedo.h || albedo.height;
    let nrm = normal; if (!nrm) { const d = new Uint8Array(w * h * 4); for (let i = 0; i < w * h; i++) { d[i * 4] = 128; d[i * 4 + 1] = 128; d[i * 4 + 2] = 255; d[i * 4 + 3] = 255; } nrm = { w, h, data: d }; }
    const sh = { name, w, h, tA: up(albedo), tN: up(nrm), flipY: o.flipNormalY ? -1 : 1, mesh: this.quad() };
    sh.mesh.inst = X.inst(sh.mesh, SL, 64); this.sheets[name] = sh; return sh;
  }
  /** an actor drawn from a sheet. o: {x, z, y, frame:[sx, sy, sw, sh], anchor:[ax, ay], flip, char:true, slot, far, shadow} */
  addActor(sheet, o = {}) {
    if (typeof sheet === 'string') sheet = this.sheets[sheet];
    const a = Object.assign({ sheet, x: 0, z: 0, y: 0, frame: [0, 0, 16, 32], anchor: [8, 31], flip: false, char: true, slot: this.actors.size % 8, far: 0, shadow: true, hidden: false, bulge: 6 }, o);
    a.set = p => { Object.assign(a, p); return a; }; a.remove = () => this.actors.delete(a);
    this.actors.add(a); return a;
  }

  /* ---------------- lights ---------------- */
  addLight(o = {}) {
    const L = { x: o.x || 0, z: o.z || 0, y: o.y ?? 1, color: hexOr(o.color, [1, 0.72, 0.4]), radius: o.radius ?? 4, intensity: o.intensity ?? 1, flicker: o.flicker ?? 0, on: true, ph: Math.random() * 10, glow: o.glow ?? true };
    L.set = p => { if (p.color) p.color = hexOr(p.color, L.color); Object.assign(L, p); return L; };
    L.remove = () => this.lights.delete(L);
    this.lights.add(L); return L;
  }
  pointLight(x, y, z, r, cr, cg, cb) { if (this.frameLights.length < 64) this.frameLights.push([x, y, z, r, cr, cg, cb]); }

  /* ---------------- the Far on the ground ---------------- */
  /** paint the ground far mask: ellipse (metres), amount 0..1, ragged edge, max-blend (o.mode 'set' to overwrite) */
  paintFar(o) {
    const F = this.farM; if (!F) return; const cell = F.cell;
    const cx = o.x * PPM, cy = o.z * PPM, rx = (o.rx ?? 2) * PPM, ry = (o.rz ?? o.rx ?? 2) * PPM, ang = o.angle || 0, amt = o.amount ?? 1, rag = o.ragged ?? 0.35;
    const R = Math.max(rx, ry) * 1.4;
    const i0 = Math.max(0, Math.floor((cx - R - F.x0) / cell)), i1 = Math.min(F.w - 1, Math.ceil((cx + R - F.x0) / cell));
    const j0 = Math.max(0, Math.floor((cy - R - F.y0) / cell)), j1 = Math.min(F.h - 1, Math.ceil((cy + R - F.y0) / cell));
    const ca = Math.cos(ang), sa = Math.sin(ang), seed = Math.random() * 100;
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const X = F.x0 + (i + 0.5) * cell - cx, Y = F.y0 + (j + 0.5) * cell - cy;
      const u = (X * ca + Y * sa) / rx, v = (-X * sa + Y * ca) / ry; const a = Math.atan2(v, u);
      const d = Math.hypot(u, v) * (1 + (Math.sin(a * 3 + seed) * 0.5 + Math.sin(a * 7 + seed * 2) * 0.3) * rag);
      const k = Math.max(0, Math.min(1, (1 - d) / 0.35)) * amt; const idx = j * F.w + i;
      F.data[idx] = o.mode === 'set' ? Math.round(k * 255) : Math.max(F.data[idx], Math.round(k * 255));
    }
    this.x.texSub(this.tFar, 0, 0, F.w, F.h, F.data, { fmt: this.gl.RED });
  }
  clearFar() { if (this.farM) { this.farM.data.fill(0); this.x.texSub(this.tFar, 0, 0, this.farM.w, this.farM.h, this.farM.data, { fmt: this.gl.RED }); } }

  /* ---------------- time, camera, focus ---------------- */
  setTime(h) { this.hour = typeof h === 'string' ? PRESETS[h] ?? 12 : h; }
  setWind(w) { this.wind = w; }
  /** camera target in metres (the screen centre shows world point x, z at height y); speed: follow rate (1/s), 0 = cut */
  setCamera(p, speed = 4) { this.cam.tx = p.x * PPM; this.cam.ty = (p.z - (p.y || 0)) * PPM - (p.lift || 0) * PPM; this.cam.speed = speed; if (!speed) this.camera.snap(); }
  setFocus(x, z, y = 0) { this.focus = x == null ? null : { x: x * PPM, y: z * PPM, z: y * PPM }; }
  /** screen (CSS px) → world ground point in metres (searches down the view ray) */
  screenToWorld(px, py) {
    const s = this.scale, dpr = this.scrW / (this.cv.clientWidth || this.scrW);
    const lx = px * dpr / s - this.W / 2 + 1 + this.cam.off[0], ly = py * dpr / s - this.H / 2 + 1 - this.cam.off[1];
    const X = this.cam.sx + lx, row = this.cam.sy + ly;
    for (let z = 400; z >= -400; z -= 1) { const Y = row + z; if (this.map.heightPx(X, Y) >= z) return { x: X / PPM, z: Y / PPM, y: z / PPM }; }
    return { x: X / PPM, z: row / PPM, y: 0 };
  }
  worldToScreen(x, z, y = 0) { const s = this.scale, dpr = this.scrW / (this.cv.clientWidth || this.scrW); const lx = x * PPM - this.cam.sx + this.W / 2 - 1 - this.cam.off[0], ly = (z - y) * PPM - this.cam.sy + this.H / 2 - 1 + this.cam.off[1]; return [lx * s / dpr, ly * s / dpr]; }
  updateCamera(dt) {
    const c = this.cam;
    if (c.speed > 0) { const k = 1 - Math.exp(-c.speed * dt); c.x += (c.tx - c.x) * k; c.y += (c.ty - c.y) * k; }
    else { c.x = c.tx; c.y = c.ty; }
    let x = c.x, y = c.y;
    if (c.bounds) { const B = c.bounds, hw = this.viewW / 2, hh = this.viewH / 2;
      x = B.x1 - B.x0 < hw * 2 ? (B.x0 + B.x1) / 2 : Math.max(B.x0 + hw, Math.min(B.x1 - hw, x));
      y = B.y1 - B.y0 < hh * 2 ? (B.y0 + B.y1) / 2 : Math.max(B.y0 + hh, Math.min(B.y1 - hh, y)); }
    if (c.shake > 0) { x += (Math.random() - 0.5) * c.shake * 2; y += (Math.random() - 0.5) * c.shake * 2; c.shake = Math.max(0, c.shake - dt * 8); }
    const sx = Math.round(x), sy = Math.round(y); c.off[0] = x - sx; c.off[1] = y - sy; c.sx = sx; c.sy = sy;
    this.view = { x0: sx - this.W / 2, x1: sx + this.W / 2, y0: sy - this.H / 2, y1: sy + this.H / 2 };
  }

  /* ---------------- per-frame lists ---------------- */
  part(x, y, z, size, r, g, b, a, add) {
    const P = this.parts;
    if (add) { if (P.na >= 2000) return; const d = P.add, k = P.na * 8; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = size * this.scale; d[k + 4] = r; d[k + 5] = g; d[k + 6] = b; d[k + 7] = a; P.na++; }
    else { if (P.n >= 6000) return; const d = P.data, k = P.n * 8; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = size; d[k + 4] = r; d[k + 5] = g; d[k + 6] = b; d[k + 7] = a; P.n++; }
  }
  glow(x, y, z, w, h, r, g, b, a, kind = 2) { const G = this.glowQ.inst; if (G.n >= G.max) return; const d = G.data, k = G.n * 12; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = kind; d[k + 4] = w; d[k + 5] = h; d[k + 6] = 0; d[k + 7] = 0; d[k + 8] = r; d[k + 9] = g; d[k + 10] = b; d[k + 11] = a; G.n++; }

  common(P) {
    const E = this.env, c = this.cam;
    return P.f('uCam', c.sx, c.sy).f('uLow', this.W, this.H).f('uTime', this.t).m4('uLVP', this.lvp)
      .v('uSunDir', E.sunDir).v('uShadeDir', E.shadeDir).v('uSunCol', E.sunCol).v('uSkyCol', E.skyCol).v('uGndCol', E.gndCol)
      .v('uWind', this.wind).f('uDith', ((c.sx % 4) + 4) % 4, ((-c.sy % 4) + 4) % 4);
  }
  lightingU(P) {
    const E = this.env;
    return P.t('uShM', this.f.sh.depth).t('uShC', this.f.sh.tex[0]).v4a('uLP', this.lp).v4a('uLC', this.lc).i('uNL', this.nl)
      .v4a('uChar', this.charSlots).f('uMist', ...E.mist).v('uFogCol', E.fog).f('uMistZ', this.M ? this.M.mistZ : 0)
      .f('uCloud', E.cloud).f('uShafts', this.Q.shafts ? E.shafts : 0).f('uShaftSteps', this.Q.shafts).f('uNight', E.night)
      .t('uZG', this.tZG).f('uZGR', ...(this.zgR || [0, 0, 0, 0]))
      .v('uFarCol', E.farCol).f('uBounds', ...this.boundsPx4()).f('uEdgeFar', this.edgeFar ?? (this.M ? this.M.edgeFar : 0.6)).v('uCharK', E.charK).f('uFlecks', E.flecks * this.Q.flecks);
  }
  boundsPx4() { const b = this.boundsPx || { x0: -1e5, y0: -1e5, x1: 1e5, y1: 1e5 }; return [b.x0, b.y0, b.x1, b.y1]; }

  /* ---------------- frame ---------------- */
  render(dt = 1 / 60) {
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const gl = this.gl, X = this.x, P = this.P, f = this.f; X.calls = 0; let passes = 0;
    this.t += dt;
    this.env = todEnv(this.hour, { wind: this.wind, mist: this.extraMist || 0 }); const E = this.env;
    this.updateCamera(dt);
    const c = this.cam, V = this.view;
    // ---- life
    this.fx.update(dt * (this.fxPaused ? 0 : 1), E, V);
    this.parts.n = 0; this.parts.na = 0; this.glowQ.inst.n = 0; this.frameLights.length = 0;
    this.fx.draw(this);
    // ---- lights: user lights (flicker) + particle lights, nearest to the view first
    const cand = [];
    for (const L of this.lights) { if (!L.on || L.intensity <= 0) continue;
      const fl = L.flicker ? 1 + (Math.sin(this.t * 7.3 + L.ph) * 0.5 + Math.sin(this.t * 12.1 + L.ph * 2) * 0.3 + Math.sin(this.t * 2.3 + L.ph) * 0.2) * 0.12 * L.flicker : 1;
      const I = L.intensity * fl; const x = L.x * PPM, y = L.z * PPM, z = L.y * PPM, r = L.radius * PPM;
      cand.push([x, y, z, r, L.color[0] * I, L.color[1] * I, L.color[2] * I]);
      if (L.glow && x > V.x0 - 40 && x < V.x1 + 40 && y - z > V.y0 - 40 && y - z < V.y1 + 40) this.glow(x, y, z, 26 * I, 26 * I, L.color[0] * 0.35, L.color[1] * 0.3, L.color[2] * 0.25, 1, 2);
    }
    for (const l of this.frameLights) cand.push(l);
    const cx = c.sx, cy = c.sy;
    cand.sort((a, b) => Math.hypot(a[0] - cx, a[1] - a[2] - cy) - Math.hypot(b[0] - cx, b[1] - b[2] - cy));
    this.lp.fill(0); this.lc.fill(0); this.nl = 0;
    for (const l of cand) { if (this.nl >= 32) break; if (Math.abs(l[0] - cx) > this.W / 2 + l[3] || Math.abs(l[1] - l[2] - cy) > this.H / 2 + l[3]) continue; const i = this.nl++; this.lp.set([l[0], l[1], l[2], l[3]], i * 4); this.lc.set([l[4], l[5], l[6], 1], i * 4); }
    // ---- protected characters: slots, focus, occluder fades
    this.charSlots.fill(0);
    for (const a of this.actors) if (a.char && !a.hidden) { const s = a.slot & 7; this.charSlots.set([a.x * PPM, a.z * PPM, a.y * PPM, 1], s * 4); }
    this.updateFades(dt);
    this.flushStatics();
    // ---- light camera: an ortho box around the view, pushed toward the sun, snapped to texels
    this.ensureShadow();
    const Ld = E.sunDir, half = Math.max(this.W, this.H) * 0.5 + 300, T = [c.sx, c.sy + 60, 60], D = 1600;
    const up = Math.abs(Ld[1]) > 0.95 ? [0, 0, 1] : [0, -1, 0];
    const lv = M4.lookAt([T[0] + Ld[0] * D, T[1] + Ld[1] * D, T[2] + Ld[2] * D], T, up);
    const tex = half * 2 / f.sh.w, lx = lv[0] * T[0] + lv[4] * T[1] + lv[8] * T[2], ly = lv[1] * T[0] + lv[5] * T[1] + lv[9] * T[2];
    lv[12] -= lx - Math.round(lx / tex) * tex; lv[13] -= ly - Math.round(ly / tex) * tex;
    this.lvp = M4.mul(M4.ortho(-half, half, -half, half, 10, 3600), lv);
    // ---- shadow pass
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.BLEND); gl.depthMask(true);
    X.bind(f.sh); gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK); // heightfield tops are GL-back in the light view: keep only faces turned away from the sun (cliffs)
    this.common(P.shTerrain.use());
    if (!this.noTerrainShadow) for (const ch of this.shChunks) if (ch.x1 >= c.sx - half - 80 && ch.x0 <= c.sx + half + 80 && ch.y1 >= c.sy - half && ch.y0 <= c.sy + half + 400) ch.mesh.draw();
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1.1, 2);
    const focusPx = this.focus ? [this.focus.x, this.focus.y] : [-1e5, -1e5];
    const Sp = this.common(P.spriteS.use()); Sp.f('uPass', 1).f('uFocus', ...focusPx).ta('uAlb', this.tAlb).ta('uNrm', this.tNrm);
    this.drawStatics(half + 200);
    this.drawDyn();
    this.drawActors(P.sheetS, 1, focusPx);
    gl.disable(gl.POLYGON_OFFSET_FILL); passes++;
    // ---- backdrop
    gl.disable(gl.DEPTH_TEST);
    X.bind(f.back);
    const B = this.backL; const Bk = this.common(P.back.use());
    Bk.t('uLayer', this.tBack).f('uLayerR', B ? B.x0 : 0, B ? B.y0 : 0, B ? B.w : 1, B ? B.h : 1).f('uPar', ...(B ? B.par : [0, 0]))
      .v('uSkyTop', E.skyTop).v('uSkyHor', E.skyHor).v('uHaze', E.haze).f('uNightK', E.night)
      .f('uRed', B && B.red ? B.red.x : -99, B && B.red ? B.red.y : -99, 0.55 + 0.45 * Math.max(0, Math.sin(this.t * 2.2)), E.night > 0.3 ? Math.min(1, (E.night - 0.3) / 0.4) : 0);
    X.tri(); passes++;
    // ---- G-buffer
    gl.enable(gl.DEPTH_TEST); X.bind(f.g);
    gl.clearBufferfv(gl.COLOR, 0, [0, 0, 0, 0]); gl.clearBufferfv(gl.COLOR, 1, [0.5, 0.5, 1, 0]); gl.clearBufferfv(gl.COLOR, 2, [0, 0, 0, 0]); gl.clear(gl.DEPTH_BUFFER_BIT);
    const Gp = this.common(P.ground.use()); Gp.t('uFar', this.tFar).f('uFarR', this.farM.x0, this.farM.y0, 1 / (this.farM.w * this.farM.cell), 1 / (this.farM.h * this.farM.cell));
    this.drawChunks(Gp, 't0', 't1', 'uT0', 'uT1');
    const Sg = this.common(P.spriteG.use()); Sg.f('uPass', 0).f('uFocus', ...focusPx).ta('uAlb', this.tAlb).ta('uNrm', this.tNrm);
    this.drawStatics(0); this.drawDyn();
    this.drawActors(P.sheetG, 0, focusPx);
    passes++;
    // ---- lighting
    gl.disable(gl.DEPTH_TEST);
    X.bind(f.lit);
    const Li = this.lightingU(this.common(P.light.use()));
    Li.t('uG0', f.g.tex[0]).t('uG1', f.g.tex[1]).t('uG2', f.g.tex[2]).t('uDep', f.g.depth).t('uBack', f.back.tex[0]).i('uDebug', this.debug | 0);
    X.tri(); passes++;
    // ---- copy → post, then water (reads the lit scene and the depth texture)
    X.bind(f.postN); P.copy.use().t('uTex', f.lit.tex[0]); X.tri();
    const Wa = this.common(P.water.use());
    Wa.t('uScene', f.lit.tex[0]).t('uDep', f.g.depth).v('uSkyTop', E.skyTop).v('uSkyHor', E.skyHor).f('uSSR', this.Q.ssr).f('uMist', ...E.mist).f('uMistZ', this.M.mistZ || 0).v('uFarCol', E.farCol)
      .t('uFar', this.tFar).f('uFarR', this.farM.x0, this.farM.y0, 1 / (this.farM.w * this.farM.cell), 1 / (this.farM.h * this.farM.cell));
    this.drawChunks(Wa, 'w0', 'w1', 'uW0', 'uW1'); passes++;
    // ---- occluders hiding a character: forward-lit, dithered fade
    if (this.anyFade) {
      const Fw = this.lightingU(this.common(P.spriteF.use())); Fw.f('uPass', 2).f('uFocus', ...focusPx).ta('uAlb', this.tAlb).ta('uNrm', this.tNrm).t('uDep', f.g.depth);
      const fs = this.focus ? [this.focus.x - c.sx + this.W / 2, this.H / 2 - (this.focus.y - this.focus.z - 18 - c.sy)] : [-999, -999];
      Fw.f('uFocusS', fs[0], fs[1]);
      this.drawStatics(0); passes++;
    }
    // ---- particles and glows: depth-tested, no depth writes
    X.bind(f.post); gl.enable(gl.DEPTH_TEST); gl.depthMask(false);
    const Pp = this.parts;
    if (Pp.n) { this.common(P.part.use()); gl.bindBuffer(gl.ARRAY_BUFFER, Pp.buf); gl.bufferSubData(gl.ARRAY_BUFFER, 0, Pp.data, 0, Pp.n * 8); gl.bindVertexArray(Pp.vao); X.calls++; gl.drawArrays(gl.POINTS, 0, Pp.n); }
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
    if (Pp.na) { this.common(P.partAdd.use()); gl.bindBuffer(gl.ARRAY_BUFFER, Pp.buf); gl.bufferSubData(gl.ARRAY_BUFFER, 0, Pp.add, 0, Pp.na * 8); gl.bindVertexArray(Pp.vao); X.calls++; gl.drawArrays(gl.POINTS, 0, Pp.na); }
    if (this.glowQ.inst.n) { gl.disable(gl.DEPTH_TEST); this.common(P.glow.use()); this.glowQ.inst.upload(); this.glowQ.drawInst(this.glowQ.inst.n); }
    gl.disable(gl.BLEND); gl.depthMask(true); gl.disable(gl.DEPTH_TEST); passes++;
    // ---- bloom
    X.bind(f.b1); P.bright.use().t('uTex', f.post.tex[0]).f('uTx', 1 / this.W, 1 / this.H).f('uThr', E.bloomThr); X.tri();
    for (let k = 0; k < this.Q.bloom; k++) { X.bind(f.b2); P.blur.use().t('uTex', f.b1.tex[0]).f('uDir', 1 / f.b1.w, 0); X.tri(); X.bind(f.b1); P.blur.use().t('uTex', f.b2.tex[0]).f('uDir', 0, 1 / f.b1.h); X.tri(); }
    passes++;
    // ---- composite
    X.bind(null);
    P.comp.use().t('uLowT', f.post.tex[0]).t('uBloom', f.b1.tex[0]).f('uLowS', this.W, this.H).f('uOff', c.off[0], -c.off[1]).f('uScale', this.scale).f('uScr', this.scrW, this.scrH).f('uPad', 0, 0)
      .v('uLift', E.lift).v('uGain', E.gain).f('uSat', E.sat).f('uBloomK', E.bloomK).f('uVig', E.vig).f('uFade', ...this.fade).f('uT', this.t)
      .v('uShT', E.shT).v('uHiT', E.hiT).f('uBox', this.box).f('uExpo', E.expo);
    X.tri(); passes++;
    this.stats = { calls: X.calls, passes, ms: (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0, native: [this.W, this.H], scale: this.scale, quality: this.q, lights: this.nl, particles: this.fx.P.length };
  }
  drawChunks(Pr, a, b, ua, ub) {
    const V = this.view; Pr.f('uRect', 0, 0, 1, 1);
    for (const ch of this.chunks) {
      if (!ch[a]) continue;
      if (ch.sx + ch.w < V.x0 - 2 || ch.sx > V.x1 + 2 || ch.sy + ch.h < V.y0 - 2 || ch.sy > V.y1 + 2) continue;
      const u0 = Pr.unit; Pr.t(ua, ch[a]).t(ub, ch[b]); Pr.unit = u0;
      Pr.f('uRect', ch.sx, ch.sy, ch.w, ch.h); this.unitQuad.draw();
    }
  }
  drawStatics(margin) {
    const gl = this.gl, V = this.view, m = margin;
    for (const b of this.buckets) {
      if (b.x1 < V.x0 - m || b.x0 > V.x1 + m || b.y1 < V.y0 - m || b.y0 > V.y1 + m + (m ? 300 : 0)) continue;
      gl.bindVertexArray(b.vao); this.x.calls++; gl.drawElementsInstanced(gl.TRIANGLES, 6, this.unitQuad.itype, 0, b.n);
    }
  }
  drawDyn() {
    const D = this.dyn.inst; let n = 0;
    for (const h of this.dynList) { if (n >= D.max) break; const k = n * SF, r = h.r, d = D.data;
      let fl = h.flags | (h.flip ? FLAGS.FLIP : 0) | (h.hidden ? FLAGS.HIDDEN : 0);
      d[k] = h.x; d[k + 1] = h.y; d[k + 2] = h.z; d[k + 3] = h.sway || 0; d[k + 4] = r.w; d[k + 5] = r.h; d[k + 6] = r.ax; d[k + 7] = r.ay;
      d[k + 8] = r.x; d[k + 9] = r.y; d[k + 10] = r.layer; d[k + 11] = fl; d[k + 12] = r.bmin; d[k + 13] = r.bscale; d[k + 14] = h.id; d[k + 15] = h.far || 0;
      const t = h.tint || [1, 1, 1]; d[k + 16] = t[0]; d[k + 17] = t[1]; d[k + 18] = t[2]; d[k + 19] = 0; d[k + 20] = 0; d[k + 21] = h.scale || 1; d[k + 22] = 0; d[k + 23] = n * 1.3; n++; }
    if (!n) return; D.upload(n); this.dyn.drawInst(n);
  }
  drawActors(prog, pass, focusPx) {
    if (!this.actors.size) return;
    const by = new Map(); for (const a of this.actors) { if (a.hidden) continue; if (!by.has(a.sheet)) by.set(a.sheet, []); by.get(a.sheet).push(a); }
    for (const [sh, list] of by) {
      const Pp = this.common(prog.use()); Pp.f('uPass', pass).f('uFocus', ...focusPx).t('uAlb', sh.tA).t('uNrm', sh.tN).f('uSheet', 1, sh.flipY);
      const I = sh.mesh.inst; let n = 0;
      for (const a of list) { if (n >= I.max) break; const k = n * SF, d = I.data, fr = a.frame;
        d[k] = a.x * PPM; d[k + 1] = a.z * PPM; d[k + 2] = a.y * PPM; d[k + 3] = 0; d[k + 4] = fr[2]; d[k + 5] = fr[3]; d[k + 6] = a.anchor[0]; d[k + 7] = a.anchor[1];
        d[k + 8] = fr[0]; d[k + 9] = fr[1]; d[k + 10] = 0; d[k + 11] = (a.flip ? 1 : 0) | (a.shadow ? 2 : 0) | (a.char ? 16 : 0);
        d[k + 12] = a.bulge; d[k + 13] = 0; d[k + 14] = 250 - (a.slot & 7); d[k + 15] = a.far || 0; d[k + 16] = 1; d[k + 17] = 1; d[k + 18] = 1; d[k + 19] = 0;
        d[k + 20] = 0; d[k + 21] = 1; d[k + 22] = a.slot & 7; d[k + 23] = 0; n++; }
      I.upload(n); sh.mesh.drawInst(n);
    }
  }
  /** occluders in front of a protected character fade (forward pass); smooth in and out */
  updateFades(dt) {
    let any = false; const k = 1 - Math.exp(-dt * 7);
    const chars = []; for (const a of this.actors) if (a.char && !a.hidden) chars.push(a);
    if (this.focus) chars.push({ x: this.focus.x / PPM, z: this.focus.y / PPM, y: this.focus.z / PPM });
    const V = this.view;
    for (const b of this.buckets) {
      if (b.x1 < V.x0 - 60 || b.x0 > V.x1 + 60 || b.y1 < V.y0 - 60 || b.y0 > V.y1 + 360) { continue; }
      for (let i = b.start; i < b.start + b.n; i++) {
        const s = this.staticOrder[i]; const r = s.r; if (!(r.occluder || s.occluder)) { continue; }
        let target = 0;
        for (const a of chars) {
          const ax = a.x * PPM, ay = a.z * PPM, az = a.y * PPM; if (ay >= s.y - 2) continue; // only things in front (south) of her
          const sx0 = s.x - r.ax, sx1 = s.x - r.ax + r.w, sy1 = s.y - s.z - r.ay + r.h, sy0 = s.y - s.z - r.ay;
          const px = ax, py = ay - az - 16;
          if (px > sx0 + 3 && px < sx1 - 3 && py > sy0 + 4 && py < sy1 - 2) { if (!this.coversAt(s, px, py)) continue; target = 1; break; }
        }
        const f0 = s.fade || 0; const f1 = f0 + (target - f0) * k; const fv = Math.abs(f1 - target) < 0.02 ? target : f1;
        if (fv !== f0) { s.fade = fv; this.markDirty(s); }
        if (fv > 0.01) any = true;
      }
    }
    this.anyFade = any;
  }
  /** does sprite s actually have opaque pixels around screen point (px, py)? (atlas lookup, CPU) */
  coversAt(s, px, py) {
    const r = s.r, A = this.atlas, pg = A.pages[r.layer]; if (!pg || !pg.alb) return true;
    let hit = 0; for (const [dx, dy] of [[0, 0], [-4, -6], [4, -6], [0, -12], [-4, 4], [4, 4]]) {
      let lx = Math.floor(px + dx - (s.x - r.ax)), ly = Math.floor(py + dy - (s.y - s.z - r.ay)); if (s.flip) lx = r.w - 1 - lx;
      if (lx < 0 || ly < 0 || lx >= r.w || ly >= r.h) continue; if (pg.alb[((r.y + ly) * A.W + r.x + lx) * 4 + 3]) hit++; }
    return hit >= 2;
  }
}

function hexOr(c, d) { if (!c) return d; if (Array.isArray(c)) return c; const n = parseInt(String(c).replace('#', ''), 16); return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; }
