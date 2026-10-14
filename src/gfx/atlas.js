/* =====================================================================
   gfx/atlas — shelf packer for painted sprites into 2048² RGBA8 pages
   (uploaded as two texture arrays: ALB and NRM). CPU only, no GL, so
   the env painters can pack in Node for previews.
     ALB = colour + alpha
     NRM = normal.x, normal.y (camera space, 0..255), bulge byte,
           material (5 bits) | emission (3 bits) << 5
   Bulge (px toward the viewer, used for per-pixel depth) is quantised
   per sprite: bulge = bmin + byte * bscale.
   ===================================================================== */

export class Atlas {
  constructor(W = 2048, H = 2048) { this.W = W; this.H = H; this.pages = []; this.rects = {}; this.list = []; this.newPage(); }
  newPage() { this.pages.push({ alb: new Uint8Array(this.W * this.H * 4), nrm: new Uint8Array(this.W * this.H * 4), shelves: [] }); }
  place(w, h) {
    for (let p = 0; p < this.pages.length; p++) {
      const pg = this.pages[p];
      for (const s of pg.shelves) if (h <= s.h && s.x + w + 1 <= this.W) { const r = { x: s.x, y: s.y, layer: p }; s.x += w + 1; return r; }
      const y = pg.shelves.length ? pg.shelves[pg.shelves.length - 1].y + pg.shelves[pg.shelves.length - 1].h + 1 : 1;
      if (y + h + 1 <= this.H && w + 2 <= this.W) { pg.shelves.push({ x: 1 + w + 1, y, h }); return { x: 1, y, layer: p }; }
    }
    if (w + 2 > this.W || h + 2 > this.H) throw new Error(`sprite ${w}x${h} larger than an atlas page`);
    this.newPage(); return this.place(w, h);
  }
  /** add a painted SB (env/paint.js). meta: {ax, ay, sway, shadow, foliage, occluder, kind} */
  add(name, s, meta = {}) {
    // crop to the opaque bounding box, keep the anchor
    let x0 = s.w, y0 = s.h, x1 = -1, y1 = -1;
    for (let y = 0; y < s.h; y++) for (let x = 0; x < s.w; x++) if (s.c[(y * s.w + x) * 4 + 3]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    if (x1 < 0) { x0 = y0 = 0; x1 = y1 = 0; }
    const w = x1 - x0 + 1, h = y1 - y0 + 1;
    const ax = (meta.ax ?? s.w / 2) - x0, ay = (meta.ay ?? s.h) - y0;
    let bmin = 1e9, bmax = -1e9;
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const i = y * s.w + x; if (!s.c[i * 4 + 3]) continue; const b = s.b[i]; if (b < bmin) bmin = b; if (b > bmax) bmax = b; }
    if (bmin > bmax) { bmin = 0; bmax = 0; }
    const bscale = Math.max(1 / 64, (bmax - bmin) / 255);
    const p = this.place(w, h), pg = this.pages[p.layer], W = this.W;
    const N = s.N;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y + y0) * s.w + (x + x0), k = i * 4; if (!s.c[k + 3]) continue;
      const t = ((p.y + y) * W + p.x + x) * 4;
      pg.alb[t] = s.c[k]; pg.alb[t + 1] = s.c[k + 1]; pg.alb[t + 2] = s.c[k + 2]; pg.alb[t + 3] = 255;
      const nx = N ? N[i * 3] : 0, ny = N ? N[i * 3 + 1] : 0;
      pg.nrm[t] = Math.max(0, Math.min(255, Math.round(nx * 127.5 + 127.5))); pg.nrm[t + 1] = Math.max(0, Math.min(255, Math.round(ny * 127.5 + 127.5)));
      pg.nrm[t + 2] = Math.max(0, Math.min(255, Math.round((s.b[i] - bmin) / bscale)));
      pg.nrm[t + 3] = (s.m[i] & 31) | ((s.e[i] & 7) << 5);
    }
    const r = { name, x: p.x, y: p.y, layer: p.layer, w, h, ax, ay, bmin, bscale, sway: meta.sway || 0, shadow: meta.shadow ?? 1, foliage: !!meta.foliage, occluder: !!meta.occluder, kind: meta.kind || '', idx: this.list.length };
    this.rects[name] = r; this.list.push(r); return r;
  }
  get(name) { const r = this.rects[name]; if (!r) throw new Error('no sprite ' + name); return r; }
}
