/* =====================================================================
   env/mapkit — turns a layout (terrain shapes, placed sprites, lights,
   emitters, named objects and camera shots) into
     1. the gameplay map: heightAt / waterAt / walkable / colliders /
        objects / spawn / shots, all in metres (x east, z south, y up);
     2. map.render: everything the renderer uploads (ground and water
        chunk textures, a coarse height grid for shadows, the sprite
        atlas, static sprite instances, the ground far mask, the
        backdrop layer, particle emitters, bounds).
   Pure JS (no DOM), so it also runs in Node for tests and previews.
   ===================================================================== */
import { Terrain, PPM } from './terrain.js';
import { Atlas } from '../gfx/atlas.js';
import { clamp, RNG } from './core.js';

export class MapKit {
  /** o: {painted: {x0,z0,x1,z1}, playable: {x0,z0,x1,z1}, seed} (metres) */
  constructor(o) {
    this.o = o; this.T = new Terrain(o.painted, o.seed || 1);
    this.atlas = new Atlas(2048, 2048); this.painters = {}; this.statics = []; this.objects = {}; this.colliders = [];
    this.emitters = []; this.shots = {}; this.lights = []; this.R = RNG(o.seed || 1);
    this.spriteNames = new Set();
  }
  /** register a painter: fn() → SB, meta; painted lazily on first use */
  sprite(name, fn, meta = {}) { this.painters[name] = { fn, meta }; return name; }
  rect(name) {
    if (this.atlas.rects[name]) return this.atlas.rects[name];
    const p = this.painters[name]; if (!p) throw new Error('unknown sprite ' + name);
    const out = p.fn(); const s = out.s || out; const meta = Object.assign({}, p.meta, out.meta || {});
    this.spriteNames.add(name);
    return this.atlas.add(name, s, meta);
  }
  /** place a static sprite at (x, z) metres; y = ground height unless given. o: {flip, far, name, collide (r m), occluder, sway, tint, y, dz (sink px)} */
  place(sprite, x, z, o = {}) {
    const r = this.rect(sprite);
    const y = o.y ?? this.T.heightAt(x, z);
    const s = { r, x: Math.round(x * PPM), y: Math.round(z * PPM), z: Math.round(y * PPM) - (o.sink || 0), flip: !!o.flip, far: o.far || 0, name: o.name, sway: o.sway ?? r.sway, tint: o.tint, occluder: o.occluder, hidden: !!o.hidden, recede: o.recede || 0, flags: o.flags };
    this.statics.push(s);
    if (o.collide) this.colliders.push({ type: 'circle', x, z, r: o.collide });
    if (o.box) this.colliders.push({ type: 'box', x0: x + o.box[0], z0: z + o.box[1], x1: x + o.box[2], z1: z + o.box[3] });
    return s;
  }
  object(name, o) { this.objects[name] = Object.assign({ name }, o); return this.objects[name]; }

  /** bake everything; returns the map object */
  bake(o = {}) {
    const t0 = Date.now(), T = this.T, ms = {};
    T.paint(); ms.paint = Date.now() - t0; T.paintWater(); ms.water = Date.now() - t0 - ms.paint;
    const ground = T.pack(256);
    // coarse height grid (world px) for the shadow pass: 4 px cells
    const cell = 4, gw = Math.floor(T.W / cell) + 1, gh = Math.floor(T.H / cell) + 1, zg = new Float32Array(gw * gh);
    for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) { const X = Math.min(T.W - 1, i * cell), Y = Math.min(T.H - 1, j * cell); zg[j * gw + i] = T.Z[Y * T.W + X] / 4; }
    const zgrid = { x0: T.ox, y0: T.oy, cell, w: gw, h: gh, data: zg };
    // far mask (4 px cells over the painted region)
    const fw = Math.ceil(T.W / 4), fh = Math.ceil(T.H / 4);
    const far = { x0: T.ox, y0: T.oy, cell: 4, w: fw, h: fh, data: new Uint8Array(fw * fh) };
    // statics: make sure every placed rect exists (lazy painters already ran)
    const pl = this.o.playable, pa = this.o.painted;
    const bounds = { x0: pl.x0 * PPM, y0: pl.z0 * PPM, x1: pl.x1 * PPM, y1: pl.z1 * PPM };
    const camBounds = this.o.camBounds ? { x0: this.o.camBounds.x0 * PPM, y0: this.o.camBounds.y0 * PPM, x1: this.o.camBounds.x1 * PPM, y1: this.o.camBounds.y1 * PPM }
      : { x0: pa.x0 * PPM + 4, x1: pa.x1 * PPM - 4, y0: T.rowMin + 4, y1: T.rowMin + T.rows - 4 };
    this.buildNav();
    ms.total = Date.now() - t0;
    const map = this.gameMap();
    map.render = {
      ground, zgrid, atlas: this.atlas, statics: this.statics, far, backdrop: this.backdrop || null, emitters: this.emitters,
      bounds, camBounds, mistZ: (this.o.mistZ ?? 0) * PPM, edgeFar: this.o.edgeFar ?? 0.7, timings: ms,
    };
    map.heightPx = (X, Y) => { const Xi = Math.floor(X), Yi = Math.floor(Y); if (!T.inb(Xi, Yi)) return 0; return T.Z[T.idx(Xi, Yi)] / 4; };
    if (o.free) this.freeBake();
    return map;
  }
  /** drop the big screen-space arrays once packed */
  freeBake() { const T = this.T; T.alb = T.nrm = T.sz = T.sm = T.sf = T.wfl = T.wdep = T.wsz = T.wflag = T.wshore = null; }

  /* ---------------- gameplay data ---------------- */
  buildNav() {
    const T = this.T, cell = 0.25, cp = cell * PPM;
    const x0 = this.o.painted.x0, z0 = this.o.painted.z0;
    const w = Math.floor((this.o.painted.x1 - x0) / cell), h = Math.floor((this.o.painted.z1 - z0) / cell);
    const hgt = new Float32Array(w * h), nav = new Uint8Array(w * h);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const x = x0 + (i + 0.5) * cell, z = z0 + (j + 0.5) * cell; hgt[j * w + i] = T.heightAt(x, z);
      const wt = T.waterAt(x, z); nav[j * w + i] = wt && wt.depth > 0.3 ? 0 : 1;
    }
    // cliffs: a step of more than 0.3 m to any neighbour blocks (stairs rise 0.2 m per tread)
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const k = j * w + i, z = hgt[k]; if (!nav[k]) continue;
      for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ii = i + di, jj = j + dj; if (ii < 0 || jj < 0 || ii >= w || jj >= h) continue; if (Math.abs(hgt[jj * w + ii] - z) > 0.3) { nav[k] = 0; break; } }
    }
    // colliders
    for (const c of this.colliders) {
      if (c.type === 'circle') { const i0 = Math.floor((c.x - c.r - x0) / cell), i1 = Math.ceil((c.x + c.r - x0) / cell), j0 = Math.floor((c.z - c.r - z0) / cell), j1 = Math.ceil((c.z + c.r - z0) / cell);
        for (let j = Math.max(0, j0); j <= Math.min(h - 1, j1); j++) for (let i = Math.max(0, i0); i <= Math.min(w - 1, i1); i++) { const x = x0 + (i + 0.5) * cell, z = z0 + (j + 0.5) * cell; if (Math.hypot(x - c.x, z - c.z) < c.r) nav[j * w + i] = 0; } }
      else if (c.type === 'box') { for (let j = Math.max(0, Math.floor((c.z0 - z0) / cell)); j <= Math.min(h - 1, Math.ceil((c.z1 - z0) / cell)); j++) for (let i = Math.max(0, Math.floor((c.x0 - x0) / cell)); i <= Math.min(w - 1, Math.ceil((c.x1 - x0) / cell)); i++) { const x = x0 + (i + 0.5) * cell, z = z0 + (j + 0.5) * cell; if (x >= c.x0 && x <= c.x1 && z >= c.z0 && z <= c.z1) nav[j * w + i] = 0; } }
    }
    // outside the playable area is closed
    const pl = this.o.playable;
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const x = x0 + (i + 0.5) * cell, z = z0 + (j + 0.5) * cell; if (x < pl.x0 || x > pl.x1 || z < pl.z0 || z > pl.z1) nav[j * w + i] = 0; }
    this.nav = { x0, z0, cell, w, h, data: nav, hgt };
  }
  gameMap() {
    const T = this.T, N = this.nav, pl = this.o.playable;
    const navAt = (x, z) => { const i = Math.floor((x - N.x0) / N.cell), j = Math.floor((z - N.z0) / N.cell); if (i < 0 || j < 0 || i >= N.w || j >= N.h) return 0; return N.data[j * N.w + i]; };
    return {
      pxPerMetre: PPM,
      size: { w: pl.x1 - pl.x0, h: pl.z1 - pl.z0 }, playable: pl, painted: this.o.painted,
      /** walkable surface height (metres) */
      heightAt: (x, z) => T.heightAt(x, z),
      /** water at a point: {surface, depth} metres, or null (cliffs and ravines are NOT water) */
      waterAt: (x, z) => T.waterAt(x, z),
      water: (x, z) => { const w = T.waterAt(x, z); return w ? w.depth : 0; },
      /** ground material name at a point */
      material: (x, z) => MATNAME[T.topAt(x, z)] || 'grass',
      walkable: (x, z) => navAt(x, z) === 1,
      nav: N, colliders: this.colliders, objects: this.objects, spawn: this.spawn, shots: this.shots, sprites: [...this.spriteNames],
    };
  }
}
const MATNAME = { 1: 'grass', 2: 'clearing', 3: 'moss', 4: 'forest', 5: 'path', 6: 'paving', 7: 'steps', 8: 'root', 9: 'gravel', 10: 'water', 11: 'rock', 12: 'mud', 13: 'meadow', 14: 'needles', 15: 'scree' };
