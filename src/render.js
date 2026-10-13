/* =====================================================================
   RENDER — the deferred 2.5D pixel pipeline.
   shadow map (sun) → G-buffer (terrain, scenery, grass, dynamic sprites)
   → contact-shadow decals → lighting (banded sun, canopy flecks, cloud
   shadows, lamps, mist and sun-shafts, the Far) → water (refraction,
   reflections) → Far ghosts, particles, glows → bloom → composite.
   ===================================================================== */
"use strict";
const CHUNK = 64;          // terrain cells per chunk side (4 px cells → 256 px)
const RD = {
  cv: null, P: {}, f: {}, scale: 3, W: 480, H: 270, scrW: 0, scrH: 0, t: 0,
  cam: { x: 0, y: 0, tx: 0, ty: 0, off: [0, 0], shake: 0, vp: new Float32Array(16), lvp: new Float32Array(16), zoom: 1 },
  env: null, chunks: [], dyn: null, ghost: null, glows: null, parts: null, lights: [], blobs: [], bends: [],
  fade: [0, 0, 0, 0], box: 0, farFx: 0, quality: 1,
  init(cv) {
    this.cv = cv; if (!GL.init(cv)) return false;
    const gl = GL.gl, C = SH.COMMON, P = this.P;
    P.terrain = GL.prog("terrain", C + SH.terrainVS, C + SH.terrainFS);
    P.sprite = GL.prog("sprite", C + SH.spriteVS, C + SH.spriteFS);
    P.grass = GL.prog("grass", C + SH.grassVS, C + SH.grassFS);
    P.depth = GL.prog("depth", C + SH.depthVS, C + SH.depthFS);
    P.light = GL.prog("light", C + SH.fsVS, C + SH.lightFS);
    P.water = GL.prog("water", C + SH.waterVS, C + SH.waterFS);
    P.ghost = GL.prog("ghost", C + SH.spriteVS, C + SH.ghostFS);
    P.part = GL.prog("part", C + SH.partVS, C + SH.partFS);
    P.partAdd = GL.prog("partAdd", C + SH.partVS, C + SH.partAddFS);
    P.glow = GL.prog("glow", C + SH.glowVS, C + SH.glowFS);
    P.copy = GL.prog("copy", SH.fsVS, SH.copyFS);
    P.bright = GL.prog("bright", SH.fsVS, SH.brightFS);
    P.blur = GL.prog("blur", SH.fsVS, SH.blurFS);
    P.comp = GL.prog("comp", SH.fsVS, SH.compFS);
    P.blob = GL.prog("blob", C + SH.glowVS, C + `in vec2 vQ; in vec4 vC; flat in float vK; layout(location=0) out vec4 oC; void main(){ float d=length(vQ); if(d>1.) discard; float a=(1.-smoothstep(.35,1.,d))*vC.a; a=floor(a*4.+bayer4(gl_FragCoord.xy))/4.; oC=vec4(vec3(1.-a*.55),1.); }`);
    // unit quad (0..1) for instanced cards
    const q = new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]); const qi = [0, 1, 2, 0, 2, 3];
    const mkQ = () => GL.mesh(q, [["q", 2]], qi);
    const SL = [["p", 4], ["s", 4], ["uv", 4], ["t", 4], ["f", 4]];
    this.dyn = { mesh: mkQ() }; this.dyn.inst = GL.inst(this.dyn.mesh, SL, 2048);
    this.dynB = { mesh: mkQ() }; this.dynB.inst = GL.inst(this.dynB.mesh, SL, 128);     // characters (dynamic atlas)
    this.ghost = { mesh: mkQ() }; this.ghost.inst = GL.inst(this.ghost.mesh, SL, 128);
    this.glows = { mesh: mkQ() }; this.glows.inst = GL.inst(this.glows.mesh, [["p", 4], ["s", 4], ["c", 4]], 512);
    this.blobQ = { mesh: mkQ() }; this.blobQ.inst = GL.inst(this.blobQ.mesh, [["p", 4], ["s", 4], ["c", 4]], 128);
    this.quadMk = mkQ; this.SL = SL;
    // particles
    const pv = gl.createVertexArray(); gl.bindVertexArray(pv); const pb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, pb);
    gl.bufferData(gl.ARRAY_BUFFER, 8 * 4 * 6000, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 32, 0); gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 4, gl.FLOAT, false, 32, 16);
    gl.bindVertexArray(null);
    this.parts = { vao: pv, buf: pb, data: new Float32Array(8 * 6000), n: 0, add: new Float32Array(8 * 3000), na: 0 };
    // shadow map with an occluder-class colour target (1 = foliage)
    const SS = this.quality > .5 ? 2048 : 1024;
    this.sh = GL.fbo(SS, SS, [{}], "cmp");
    // dynamic atlas for characters: 512² albedo + normal pages written from the CPU each frame
    this.dynAtlas = { w: 512, h: 512, alb: new Uint8Array(512 * 512 * 4), nrm: new Uint8Array(512 * 512 * 4), slots: [] };
    this.dynAtlas.tA = GL.tex(512, 512, this.dynAtlas.alb); this.dynAtlas.tN = GL.tex(512, 512, this.dynAtlas.nrm);
    addEventListener("resize", () => this.resize()); this.resize();
    this.lp = new Float32Array(128); this.lc = new Float32Array(128); this.bendA = new Float32Array(24);
    return true;
  },
  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    const W = Math.max(320, Math.round(innerWidth * dpr)), H = Math.max(200, Math.round(innerHeight * dpr));
    this.cv.width = W; this.cv.height = H; this.scrW = W; this.scrH = H;
    const target = (IN.device === "touch" ? 250 : 270) / this.cam.zoom;
    const s = Math.max(1, Math.round(H / target)); this.scale = s;
    let lw = Math.ceil(W / s) + 2, lh = Math.ceil(H / s) + 2; lw += lw & 1; lh += lh & 1;
    if (lw === this.W && lh === this.H && this.f.g) return;
    this.W = lw; this.H = lh;
    for (const k in this.f) this.f[k].free && this.f[k].free();
    const gl = GL.gl, hdr = GL.hdr ? { ifmt: gl.RGBA16F, fmt: gl.RGBA, type: gl.HALF_FLOAT } : {};
    this.f.g = GL.fbo(lw, lh, [{}, {}, {}], true);
    this.f.ao = GL.fbo(lw, lh, [{}], null);
    this.f.lit = GL.fbo(lw, lh, [hdr], null);
    this.f.post = GL.fbo(lw, lh, [hdr], this.f.g.depth);
    // a second view of the same colour target without depth, for passes that must read the depth texture
    this.f.postN = { fb: gl.createFramebuffer(), w: lw, h: lh, tex: this.f.post.tex, free() { gl.deleteFramebuffer(this.fb); } };
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.f.postN.fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.f.post.tex[0], 0); gl.drawBuffers([gl.COLOR_ATTACHMENT0]); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    const hw = Math.max(8, lw >> 1), hh = Math.max(8, lh >> 1);
    this.f.b1 = GL.fbo(hw, hh, [Object.assign({ linear: true }, hdr)], null); this.f.b2 = GL.fbo(hw, hh, [Object.assign({ linear: true }, hdr)], null);
  },
  /* ---------------- world upload ---------------- */
  buildWorld(WD) {
    const gl = GL.gl; this.WD = WD;
    for (const c of this.chunks) { c.terrain && c.terrain.free(); }
    this.chunks = [];
    const cw = WD.cw, ch = WD.ch, S = WD.cell;
    // textures
    const mt = new Uint8Array(cw * ch * 4), wt = new Uint8Array(cw * ch * 4);
    for (let i = 0; i < cw * ch; i++) {
      mt[i * 4] = WD.mat[i]; mt[i * 4 + 1] = WD.moist[i]; mt[i * 4 + 2] = WD.ao[i]; mt[i * 4 + 3] = WD.feat[i];
      const w = WD.water[i]; if (w > -500) { wt[i * 4] = clamp(Math.round((w + 64) / 512 * 255), 0, 255); wt[i * 4 + 1] = clamp(Math.round((WD.flow[i * 2] * .5 + .5) * 255), 0, 255); wt[i * 4 + 2] = clamp(Math.round((WD.flow[i * 2 + 1] * .5 + .5) * 255), 0, 255); wt[i * 4 + 3] = 255; }
    }
    this.tMat = GL.tex(cw, ch, mt); this.tWat = GL.tex(cw, ch, wt);
    const hv = new Float32Array(WD.h); // R16F upload from float32
    this.tHgt = GL.tex(cw + 1, ch + 1, hv, { ifmt: gl.R32F, fmt: gl.RED, type: gl.FLOAT, linear: !!gl.getExtension("OES_texture_float_linear") });
    this.nearBuf = new Uint8Array(WD.nw * WD.nh * 4);
    this.tNear = GL.tex(WD.nw, WD.nh, this.nearBuf, { linear: true });
    this.uploadNear(true);
    // terrain chunks
    const vx = cw + 1;
    for (let cz = 0; cz < ch; cz += CHUNK) for (let cx = 0; cx < cw; cx += CHUNK) {
      const nx = Math.min(CHUNK, cw - cx), nz = Math.min(CHUNK, ch - cz);
      const verts = new Float32Array((nx + 1) * (nz + 1) * 6), idx = [];
      let zmin = 1e9, zmax = -1e9;
      for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
        const gx = cx + i, gz = cz + j, h = WD.h[gz * vx + gx];
        const hl = WD.h[gz * vx + Math.max(0, gx - 1)], hr = WD.h[gz * vx + Math.min(cw, gx + 1)], hu = WD.h[Math.max(0, gz - 1) * vx + gx], hd = WD.h[Math.min(ch, gz + 1) * vx + gx];
        let nX = -(hr - hl) / (2 * S), nY = -(hd - hu) / (2 * S), nZ = 1; const l = hyp(nX, nY, nZ);
        const k = (j * (nx + 1) + i) * 6; verts[k] = gx * S; verts[k + 1] = gz * S; verts[k + 2] = h; verts[k + 3] = nX / l; verts[k + 4] = nY / l; verts[k + 5] = nZ / l;
        zmin = Math.min(zmin, h); zmax = Math.max(zmax, h);
      }
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) { const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
      this.chunks.push({ x0: cx * S, y0: cz * S, x1: (cx + nx) * S, y1: (cz + nz) * S, zmin, zmax, terrain: GL.mesh(verts, [["p", 3], ["n", 3]], idx), props: null, grass: null, water: null });
    }
    // scenery & grass per chunk (static instance buffers)
    const chunkOf = (x, y) => { const i = Math.floor(x / (CHUNK * S)), j = Math.floor(y / (CHUNK * S)); const nxC = Math.ceil(cw / CHUNK); return this.chunks[clamp(j, 0, Math.ceil(ch / CHUNK) - 1) * nxC + clamp(i, 0, nxC - 1)]; };
    const groups = new Map();
    for (const p of WD.props) { const c = chunkOf(p.x, p.y); if (!groups.has(c)) groups.set(c, []); groups.get(c).push(p); }
    for (const [c, list] of groups) {
      const m = this.quadMk(), inst = GL.inst(m, this.SL, list.length); let n = 0;
      for (const p of list) { this.packSprite(inst.data, n++, p); c.zmax = Math.max(c.zmax, p.z + p.r.h); }
      inst.upload(n); c.props = { mesh: m, n, list };
    }
    const gg = new Map();
    for (let i = 0; i < WD.grass.length; i += 8) { const c = chunkOf(WD.grass[i], WD.grass[i + 1]); if (!gg.has(c)) gg.set(c, []); gg.get(c).push(i); }
    for (const [c, list] of gg) {
      const m = this.quadMk(), inst = GL.inst(m, [["p", 4], ["s", 4]], list.length);
      list.forEach((gi, n) => { for (let k = 0; k < 8; k++) inst.data[n * 8 + k] = WD.grass[gi + k]; });
      inst.upload(list.length); c.grass = { mesh: m, n: list.length };
    }
    // water surfaces: one quad per wet cell, merged into one mesh per chunk
    for (const c of this.chunks) {
      const v = []; const i0 = c.x0 / S, j0 = c.y0 / S, i1 = c.x1 / S, j1 = c.y1 / S;
      for (let j = j0; j < j1; j++) for (let i = i0; i < i1; i++) {
        const w = WD.water[j * cw + i]; if (w < -500) continue;
        const fx = WD.flow[(j * cw + i) * 2], fy = WD.flow[(j * cw + i) * 2 + 1], sh = WD.shore[j * cw + i] / 255;
        const x = i * S, y = j * S;
        v.push(x, y, w, fx, fy, sh, x + S, y, w, fx, fy, sh, x + S, y + S, w, fx, fy, sh, x, y, w, fx, fy, sh, x + S, y + S, w, fx, fy, sh, x, y + S, w, fx, fy, sh);
      }
      if (v.length) c.water = GL.mesh(new Float32Array(v), [["p", 3], ["f", 3]]);
    }
    // grass tuft atlas
    const tufts = FLORA.grassTufts(); this.tTuft = GL.canvasTex(tufts.cv); this.tuftN = tufts.n; this.tuftW = tufts.w; this.tuftH = tufts.h;
  },
  // pack a sprite instance: o = {x,y,z, r (atlas rect), sway, flip, shadow, bulge, tint:[r,g,b,flash], near}
  packSprite(d, n, o) {
    const k = n * 20, r = o.r;
    d[k] = Math.round(o.x); d[k + 1] = Math.round(o.y); d[k + 2] = Math.round(o.z || 0); d[k + 3] = o.sway ?? r.sway ?? 0;
    d[k + 4] = r.w; d[k + 5] = r.h; d[k + 6] = r.ax; d[k + 7] = r.ay;
    d[k + 8] = r.u0; d[k + 9] = r.v0; d[k + 10] = r.u1; d[k + 11] = r.v1;
    const t = o.tint || T4; d[k + 12] = t[0]; d[k + 13] = t[1]; d[k + 14] = t[2]; d[k + 15] = t[3];
    d[k + 16] = o.flip ? 1 : 0; d[k + 17] = o.shadow ?? r.shadow ?? 1; d[k + 18] = o.bulge ?? 1; d[k + 19] = o.near ?? -1;
  },
  uploadNear(all, rect) {
    const WD = this.WD, B = this.nearBuf;
    const x0 = rect ? rect[0] : 0, y0 = rect ? rect[1] : 0, x1 = rect ? rect[2] : WD.nw - 1, y1 = rect ? rect[3] : WD.nh - 1;
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const i = y * WD.nw + x; B[i * 4] = clamp(WD.near[i] * 255, 0, 255); B[i * 4 + 1] = clamp(WD.wear[i] * 255, 0, 255); B[i * 4 + 2] = clamp(WD.wet * 255, 0, 255); B[i * 4 + 3] = 255; }
    if (all || !rect) GL.texSub(this.tNear, 0, 0, WD.nw, WD.nh, B);
    else { const w = x1 - x0 + 1, h = y1 - y0 + 1, sub = new Uint8Array(w * h * 4); for (let y = 0; y < h; y++) sub.set(B.subarray(((y0 + y) * WD.nw + x0) * 4, ((y0 + y) * WD.nw + x0 + w) * 4), y * w * 4); GL.texSub(this.tNear, x0, y0, w, h, sub); }
  },
  /* ---------------- per-frame submission ---------------- */
  sprite(o) { const D = this.dyn.inst; if (D.n >= D.max) return; this.packSprite(D.data, D.n++, o); },
  charSprite(o) { const D = this.dynB.inst; if (D.n >= D.max) return; this.packSprite(D.data, D.n++, o); },
  ghostSprite(o) { const D = this.ghost.inst; if (D.n >= D.max) return; this.packSprite(D.data, D.n++, o); },
  light(x, y, z, r, cr, cg, cb) { if (this.lights.length < 32) this.lights.push([x, y, z, r, cr, cg, cb]); },
  glow(kind, x, y, z, w, h, r, g, b, a) { const G = this.glows.inst; if (G.n >= G.max) return; const d = G.data, k = G.n * 12; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = kind; d[k + 4] = w; d[k + 5] = h; d[k + 6] = 0; d[k + 7] = 0; d[k + 8] = r; d[k + 9] = g; d[k + 10] = b; d[k + 11] = a; G.n++; },
  blob(x, y, z, w, h, a = 1) { const G = this.blobQ.inst; if (G.n >= G.max) return; const d = G.data, k = G.n * 12; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = 2; d[k + 4] = w; d[k + 5] = h; d[k + 6] = 0; d[k + 7] = 0; d[k + 8] = 0; d[k + 9] = 0; d[k + 10] = 0; d[k + 11] = a; G.n++; },
  part(x, y, z, size, r, g, b, a, add) { const P = this.parts; if (add) { if (P.na >= 3000) return; const d = P.add, k = P.na * 8; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = size; d[k + 4] = r; d[k + 5] = g; d[k + 6] = b; d[k + 7] = a; P.na++; } else { if (P.n >= 6000) return; const d = P.data, k = P.n * 8; d[k] = x; d[k + 1] = y; d[k + 2] = z; d[k + 3] = size; d[k + 4] = r; d[k + 5] = g; d[k + 6] = b; d[k + 7] = a; P.n++; } },
  bend(x, y, r, k) { if (this.bends.length < 6) this.bends.push([x, y, r, k]); },
  // write a composed SB into the dynamic atlas at a slot; returns a rect usable by charSprite
  dynSlot(i, s, ax, ay) {
    const D = this.dynAtlas, sw = 64, cols = 8, sx = (i % cols) * sw, sy = Math.floor(i / cols) * sw;
    if (!s.N) PX.normals(s, .9);
    for (let y = 0; y < sw; y++) { const o = ((sy + y) * D.w + sx) * 4; D.alb.fill(0, o, o + sw * 4); D.nrm.fill(0, o, o + sw * 4); }
    for (let y = 0; y < Math.min(s.h, sw); y++) for (let x = 0; x < Math.min(s.w, sw); x++) {
      const k = (y * s.w + x), q = k * 4; if (!s.c[q + 3]) continue; const t = ((sy + y) * D.w + sx + x) * 4;
      D.alb[t] = s.c[q]; D.alb[t + 1] = s.c[q + 1]; D.alb[t + 2] = s.c[q + 2]; D.alb[t + 3] = 255;
      D.nrm[t] = (s.N[k * 3] * .5 + .5) * 255; D.nrm[t + 1] = (s.N[k * 3 + 1] * .5 + .5) * 255; D.nrm[t + 2] = clamp(s.b[k] * 4, 0, 255); D.nrm[t + 3] = (s.m[k] & 31) | ((s.e[k] & 7) << 5);
    }
    D.dirty = true;
    return { x: sx, y: sy, w: s.w, h: s.h, u0: sx / D.w, v0: sy / D.h, u1: (sx + s.w) / D.w, v1: (sy + s.h) / D.h, ax, ay, sway: 0, shadow: 1 };
  },
  renderOverlay(tex) {
    const gl = GL.gl, P = this.P, E = this.env, c = this.cam;
    gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND);
    GL.bind(this.f.postN); P.copy.use().t("uTex", tex); GL.tri();
    GL.bind(this.f.b1); P.bright.use().t("uTex", this.f.post.tex[0]).f("uTx", 1 / this.W, 1 / this.H).f("uThr", .55); GL.tri();
    for (let k = 0; k < 2; k++) { GL.bind(this.f.b2); P.blur.use().t("uTex", this.f.b1.tex[0]).f("uDir", 1 / this.f.b1.w, 0); GL.tri(); GL.bind(this.f.b1); P.blur.use().t("uTex", this.f.b2.tex[0]).f("uDir", 0, 1 / this.f.b1.h); GL.tri(); }
    GL.bind(null);
    P.comp.use().t("uLowT", this.f.post.tex[0]).t("uBloom", this.f.b1.tex[0]).f("uLowS", this.W, this.H).f("uOff", 0, 0).f("uScale", this.scale).f("uScr", this.scrW, this.scrH)
      .v("uLift", [.01, .01, .02]).v("uGain", [1, 1, 1]).f("uSat", 1).f("uBloomK", .9).f("uVig", .6).f("uGrain", .02).f("uFade", ...this.fade).f("uT", this.t)
      .v("uShT", [-.01, -.004, .02]).v("uHiT", [.02, .01, -.01]).f("uBox", this.box).f("uFarFx", 0).v("uFarTint", [.66, .74, .9]).f("uExpo", 1);
    GL.tri();
    this.dyn.inst.n = 0; this.dynB.inst.n = 0; this.ghost.inst.n = 0; this.glows.inst.n = 0; this.blobQ.inst.n = 0; this.parts.n = 0; this.parts.na = 0; this.lights.length = 0; this.bends.length = 0;
  },
  /* ---------------- camera ---------------- */
  setCamera(x, y) {
    const c = this.cam; c.x = x; c.y = y;
    let sx = Math.round(x), sy = Math.round(y);
    if (c.shake > 0) { sx += Math.round((Math.random() - .5) * c.shake * 2); sy += Math.round((Math.random() - .5) * c.shake * 2); }
    c.off[0] = x - sx; c.off[1] = y - sy; c.sx = sx; c.sy = sy;
    const W = this.W, H = this.H, m = c.vp;
    m.fill(0); m[0] = 2 / W; m[5] = -2 / H; m[6] = -1 / 1200; m[9] = 2 / H; m[10] = -1 / 1200; m[12] = -sx * 2 / W; m[13] = sy * 2 / H; m[14] = (sy + 200) / 1200; m[15] = 1;
    c.vx0 = sx - W / 2; c.vx1 = sx + W / 2; c.vy0 = sy - H / 2; c.vy1 = sy + H / 2;
  },
  // screen (CSS px) → world ground point
  screenToWorld(px, py) {
    const dpr = this.scrW / innerWidth, c = this.cam;
    const lx = px * dpr / this.scale - this.W / 2 + c.off[0], ly = py * dpr / this.scale - this.H / 2 + c.off[1];
    const X = c.sx + lx, ymz = c.sy + ly; // Y - Z
    for (let z = 400; z >= -40; z -= 1) { const Y = ymz + z; if (WORLD.heightAt(X, Y) >= z) return [X, Y, z]; }
    return [X, ymz, 0];
  },
  worldToScreen(x, y, z) { const c = this.cam; const lx = x - c.sx + this.W / 2 - c.off[0], ly = (y - z) - c.sy + this.H / 2 - c.off[1]; const dpr = this.scrW / innerWidth; return [lx * this.scale / dpr, ly * this.scale / dpr]; },
  /* ---------------- frame ---------------- */
  commonU(P) {
    const E = this.env, c = this.cam, WD = this.WD;
    P.m4("uVP", c.vp).m4("uLVP", c.lvp).f("uCam", c.sx, c.sy).f("uLow", this.W, this.H).f("uTime", this.t)
      .v("uSunDir", E.sunDir).v("uSunCol", E.sunCol).v("uSkyCol", E.skyCol).v("uGndCol", E.gndCol).v("uWind", E.wind)
      .t("uNear", this.tNear).f("uNearR", 0, 0, 1 / WD.W, 1 / WD.H).t("uHgt", this.tHgt).f("uHgtR", -WD.cell / 2, -WD.cell / 2, 1 / ((WD.cw + 1) * WD.cell), 1 / ((WD.ch + 1) * WD.cell));
    return P;
  },
  render() {
    const gl = GL.gl, P = this.P, c = this.cam, E = this.env, WD = this.WD;
    if (this.dynAtlas.dirty) { GL.texSub(this.dynAtlas.tA, 0, 0, 512, 512, this.dynAtlas.alb); GL.texSub(this.dynAtlas.tN, 0, 0, 512, 512, this.dynAtlas.nrm); this.dynAtlas.dirty = false; }
    // ---- light camera: an ortho box around the view, pushed toward the sun, snapped to texels
    const L = E.sunDir, half = Math.max(this.W, this.H) * .5 + 230, T = [c.sx, c.sy + 70, 40], D = 900;
    const up = Math.abs(L[1]) > .95 ? [0, 0, 1] : [0, -1, 0];
    const lv = M4.lookAt([T[0] + L[0] * D, T[1] + L[1] * D, T[2] + L[2] * D], T, up);
    const tex = half * 2 / this.sh.w, lx = lv[0] * T[0] + lv[4] * T[1] + lv[8] * T[2], ly = lv[1] * T[0] + lv[5] * T[1] + lv[9] * T[2];
    lv[12] -= lx - Math.round(lx / tex) * tex; lv[13] -= ly - Math.round(ly / tex) * tex;
    M4.mul(M4.ortho(-half, half, -half, half, 10, 2000), lv, c.lvp);
    const visS = ch => ch.x1 >= c.sx - half - 40 && ch.x0 <= c.sx + half + 40 && ch.y1 >= c.sy - half - 120 && ch.y0 <= c.sy + half + 260;
    const vis = ch => ch.x1 >= c.vx0 - 70 && ch.x0 <= c.vx1 + 70 && (ch.y1 - ch.zmin) >= c.vy0 - 20 && (ch.y0 - ch.zmax - 40) <= c.vy1 + 20;
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.disable(gl.BLEND); gl.depthMask(true);
    // ---- shadow pass
    GL.bind(this.sh); gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1.2, 2);
    const Dp = this.commonU(P.depth.use());
    for (const ch of this.chunks) if (visS(ch)) ch.terrain.draw();
    const Sp = this.commonU(P.sprite.use()); Sp.f("uShadow", 1).f("uMargin", 3).t("uAlb", ATLAS.tAlb).t("uNrm", ATLAS.tNrm);
    for (const ch of this.chunks) if (ch.props && visS(ch)) ch.props.mesh.drawInst(ch.props.n);
    if (this.dyn.inst.n) { this.dyn.inst.upload(this.dyn.inst.n); this.dyn.mesh.drawInst(this.dyn.inst.n); }
    if (this.dynB.inst.n) { Sp.t("uAlb", this.dynAtlas.tA).t("uNrm", this.dynAtlas.tN); this.dynB.inst.upload(this.dynB.inst.n); this.dynB.mesh.drawInst(this.dynB.inst.n); }
    gl.disable(gl.POLYGON_OFFSET_FILL);
    // ---- G-buffer
    GL.bind(this.f.g);
    gl.clearBufferfv(gl.COLOR, 0, [0, 0, 0, 0]); gl.clearBufferfv(gl.COLOR, 1, [.5, .5, 1, 0]); gl.clearBufferfv(gl.COLOR, 2, [1, 0, 0, 1]); gl.clear(gl.DEPTH_BUFFER_BIT);
    const Tr = this.commonU(P.terrain.use()); Tr.t("uMat", this.tMat).f("uMatR", 0, 0, 1 / WD.W, 1 / WD.H).t("uWat", this.tWat);
    for (const ch of this.chunks) if (vis(ch)) ch.terrain.draw();
    const Sg = this.commonU(P.sprite.use()); Sg.f("uShadow", 0).f("uMargin", 3).t("uAlb", ATLAS.tAlb).t("uNrm", ATLAS.tNrm);
    for (const ch of this.chunks) if (ch.props && vis(ch)) ch.props.mesh.drawInst(ch.props.n);
    if (this.dyn.inst.n) this.dyn.mesh.drawInst(this.dyn.inst.n);
    if (this.dynB.inst.n) { Sg.t("uAlb", this.dynAtlas.tA).t("uNrm", this.dynAtlas.tN); this.dynB.mesh.drawInst(this.dynB.inst.n); }
    const G = this.commonU(P.grass.use()); G.t("uTuft", this.tTuft).f("uN", this.tuftN).f("uTS", this.tuftW, this.tuftH);
    this.bendA.fill(0); this.bends.forEach((b, i) => this.bendA.set(b, i * 4)); G.v4a("uBend", this.bendA);
    for (const ch of this.chunks) if (ch.grass && vis(ch)) ch.grass.mesh.drawInst(ch.grass.n);
    // ---- contact shadows (multiplicative decals into the AO target)
    gl.disable(gl.DEPTH_TEST);
    GL.bind(this.f.ao); gl.clearColor(1, 1, 1, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    if (this.blobQ.inst.n) { gl.enable(gl.BLEND); gl.blendFunc(gl.DST_COLOR, gl.ZERO); const B = this.commonU(P.blob.use()); this.blobQ.inst.upload(this.blobQ.inst.n); this.blobQ.mesh.drawInst(this.blobQ.inst.n); gl.disable(gl.BLEND); }
    // ---- lighting
    GL.bind(this.f.lit);
    const LP = this.lp, LC = this.lc; LP.fill(0); LC.fill(0);
    this.lights.forEach((l, i) => { LP.set([l[0], l[1], l[2], l[3]], i * 4); LC.set([l[4], l[5], l[6], 1], i * 4); });
    const Li = this.commonU(P.light.use());
    Li.t("uG0", this.f.g.tex[0]).t("uG1", this.f.g.tex[1]).t("uG2", this.f.g.tex[2]).t("uDep", this.f.g.depth).t("uShadowM", this.sh.depth).t("uShadowC", this.sh.tex[0]).t("uAO", this.f.ao.tex[0])
      .v4a("uLP", LP).v4a("uLC", LC).i("uNL", this.lights.length).f("uFogC", ...E.fog, 1).f("uMist", ...E.mist).f("uCloud", E.cloud).f("uShafts", E.shafts).v("uFar", E.far).f("uRain", E.rain).f("uNight", E.night).f("uFarWave", this.farWave == null ? -1e4 : this.farWave);
    GL.tri();
    // ---- copy lit → post, then water (reads depth; drawn into the depth-less view)
    GL.bind(this.f.postN); P.copy.use().t("uTex", this.f.lit.tex[0]); GL.tri();
    const Wa = this.commonU(P.water.use()); Wa.t("uScene", this.f.lit.tex[0]).t("uDep", this.f.g.depth).v("uSkyTop", E.skyTop).v("uSkyHor", E.skyHor).f("uRain", E.rain);
    gl.disable(gl.DEPTH_TEST); // the water shader occludes itself against the depth texture
    for (const ch of this.chunks) if (ch.water && vis(ch)) ch.water.draw();
    // ---- ghosts, particles, glows: depth-tested against the scene, no depth writes
    GL.bind(this.f.post); gl.enable(gl.DEPTH_TEST); gl.depthMask(false);
    if (this.ghost.inst.n) { const Gh = this.commonU(P.ghost.use()); Gh.f("uShadow", 0).f("uMargin", 0).t("uAlb", ATLAS.tAlb).f("uAlpha", 1).v("uFarA", E.farA).v("uFarB", E.farB); this.ghost.inst.upload(this.ghost.inst.n); this.ghost.mesh.drawInst(this.ghost.inst.n); }
    const Pp = this.parts;
    if (Pp.n) { this.commonU(P.part.use()); gl.bindBuffer(gl.ARRAY_BUFFER, Pp.buf); gl.bufferSubData(gl.ARRAY_BUFFER, 0, Pp.data, 0, Pp.n * 8); gl.bindVertexArray(Pp.vao); gl.drawArrays(gl.POINTS, 0, Pp.n); }
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
    if (Pp.na) { this.commonU(P.partAdd.use()); gl.bindBuffer(gl.ARRAY_BUFFER, Pp.buf); gl.bufferSubData(gl.ARRAY_BUFFER, 0, Pp.add, 0, Pp.na * 8); gl.bindVertexArray(Pp.vao); gl.drawArrays(gl.POINTS, 0, Pp.na); }
    if (this.glows.inst.n) { gl.disable(gl.DEPTH_TEST); this.commonU(P.glow.use()); this.glows.inst.upload(this.glows.inst.n); this.glows.mesh.drawInst(this.glows.inst.n); }
    gl.disable(gl.BLEND); gl.depthMask(true); gl.disable(gl.DEPTH_TEST);
    // ---- bloom
    GL.bind(this.f.b1); P.bright.use().t("uTex", this.f.post.tex[0]).f("uTx", 1 / this.W, 1 / this.H).f("uThr", E.bloomThr); GL.tri();
    for (let k = 0; k < 2; k++) { GL.bind(this.f.b2); P.blur.use().t("uTex", this.f.b1.tex[0]).f("uDir", 1 / this.f.b1.w, 0); GL.tri(); GL.bind(this.f.b1); P.blur.use().t("uTex", this.f.b2.tex[0]).f("uDir", 0, 1 / this.f.b1.h); GL.tri(); }
    // ---- composite to screen
    GL.bind(null);
    P.comp.use().t("uLowT", this.f.post.tex[0]).t("uBloom", this.f.b1.tex[0]).f("uLowS", this.W, this.H).f("uOff", c.off[0], -c.off[1]).f("uScale", this.scale).f("uScr", this.scrW, this.scrH)
      .v("uLift", E.lift).v("uGain", E.gain).f("uSat", E.sat).f("uBloomK", E.bloomK).f("uVig", E.vig).f("uGrain", E.grain).f("uFade", ...this.fade).f("uT", this.t)
      .v("uShT", E.shT).v("uHiT", E.hiT).f("uBox", this.box).f("uFarFx", this.farFx).v("uFarTint", E.far).f("uExpo", E.expo || 1);
    GL.tri();
    // reset per-frame lists
    this.dyn.inst.n = 0; this.dynB.inst.n = 0; this.ghost.inst.n = 0; this.glows.inst.n = 0; this.blobQ.inst.n = 0; this.parts.n = 0; this.parts.na = 0;
    this.lights.length = 0; this.bends.length = 0;
  },
};
const T4 = [1, 1, 1, 0];

/* ---------------------------------------------------------------------
   TIME OF DAY → light, sky and grade. Keys are hours; a summer day at
   altitude: long blue dawn, white noon, honey-gold hour, violet dusk,
   moonlit indigo night.
   --------------------------------------------------------------------- */
const TOD = [
  // h,   sun col,          sky (amb),        ground bounce,     mist rgb,          mist, lift,               gain,              sat,  cloud, shafts
  [0,    [.36, .45, .74], [.21, .26, .44], [.06, .07, .12],   [.16, .2, .32],    .18, [.02, .025, .05], [.9, .95, 1.08],  .62, .5, 0],
  [4.2,  [.36, .43, .72], [.22, .25, .43], [.07, .07, .12],  [.22, .24, .36],   .3,  [.03, .03, .06],  [.92, .95, 1.06], .66, .5, 0],
  [5.2,  [.8, .56, .58],  [.42, .4, .56],  [.16, .13, .17],  [.62, .56, .66],   .55, [.04, .03, .06],  [1.0, .97, 1.0],  .8,  .45, .35],
  [6.2,  [1.25, .86, .58],[.54, .52, .64], [.28, .23, .2],   [.92, .8, .72],    .5,  [.03, .02, .04],  [1.04, 1.0, .96], .95, .4, 1.],
  [8,    [1.12, .98, .78],[.44, .52, .7],  [.28, .27, .21],   [.78, .8, .82],    .2,  [.02, .02, .03],  [1.02, 1.01, .99],1.0, .45, .6],
  [12,   [1.16, 1.06, .9], [.44, .54, .74], [.3, .3, .22],  [.8, .84, .88],    .05, [.02, .02, .025], [1.02, 1.01, 1.0],1.0, .55, .2],
  [16,   [1.16, .97, .72],[.46, .52, .7],  [.3, .26, .2],  [.84, .78, .72],   .08, [.025, .02, .02], [1.04, 1.0, .95], 1.0, .5, .4],
  [17.8, [1.3, .8, .48],  [.56, .48, .56], [.32, .22, .19],  [.92, .7, .58],    .24, [.04, .02, .03],  [1.07, .97, .9],  .97, .45, .9],
  [18.9, [.6, .38, .5],   [.34, .29, .46], [.13, .1, .15],   [.5, .36, .5],     .32, [.04, .02, .06],  [.98, .94, 1.04], .84, .45, .2],
  [20,   [.36, .45, .74], [.21, .26, .44], [.06, .07, .12],   [.16, .2, .32],    .2,  [.02, .025, .05], [.9, .95, 1.08],  .64, .5, 0],
  [24,   [.36, .45, .74], [.21, .26, .44], [.06, .07, .12],   [.16, .2, .32],    .18, [.02, .025, .05], [.9, .95, 1.08],  .62, .5, 0],
];
function todEnv(tod, w = {}) {
  tod = ((tod % 24) + 24) % 24;
  let a = TOD[0], b = TOD[1];
  for (let i = 0; i < TOD.length - 1; i++) if (tod >= TOD[i][0] && tod <= TOD[i + 1][0]) { a = TOD[i]; b = TOD[i + 1]; break; }
  const t = sstep(0, 1, (tod - a[0]) / Math.max(1e-3, b[0] - a[0]));
  const L = i => Array.isArray(a[i]) ? a[i].map((v, k) => lerp(v, b[i][k], t)) : lerp(a[i], b[i], t);
  const day = tod > 5.3 && tod < 18.9;
  let dir;
  if (day) { const s = clamp((tod - 5.3) / 13.6, 0, 1) * Math.PI; const x = Math.cos(s), e = Math.sin(s); const v = [x * .85, -.38, Math.max(.2, e * .95)]; const l = hyp(...v); dir = v.map(q => q / l); }
  else { const v = [-.3, -.45, .82]; const l = hyp(...v); dir = v.map(q => q / l); }
  const night = day ? 0 : 1, warm = clamp(1 - Math.abs(tod - 6.3) / 1.3, 0, 1) + clamp(1 - Math.abs(tod - 17.9) / 1.3, 0, 1);
  const rain = w.rain || 0, overcast = w.overcast || 0;
  let sun = L(1).map(v => v * (1 - overcast * .6 - rain * .3)), sky = L(2).map(v => v * (1 + overcast * .15)), gnd = L(3);
  const mistA = clamp(L(5) + (w.mist || 0) + rain * .15, 0, .9);
  return {
    sunDir: dir, sunCol: sun, skyCol: sky, gndCol: gnd, mist: [...L(4), mistA], fog: L(4),
    lift: L(6), gain: L(7), sat: L(8) * (1 - rain * .15), cloud: clamp(L(9) + overcast * .4, 0, 1), shafts: L(10) * (1 - overcast) * (1 - rain),
    night, rain, wind: w.wind || [1, .2, .3],
    shT: [-.012 - .012 * night, -.004, .024 + .022 * night], hiT: [.024 * warm + .006, .012 * warm, -.01 * warm],
    far: [.66, .74, .9], farA: [.5, .58, .76], farB: [.8, .86, .96],
    skyTop: night ? [.05, .07, .14] : mixRGB(sky, [.4, .55, .8], .5), skyHor: night ? [.1, .12, .2] : mixRGB(L(4), [.9, .9, .9], .3),
    bloomK: .55 + night * .25, bloomThr: .82 - night * .25, vig: .55 + night * .25, grain: .022, expo: 1,
  };
}
