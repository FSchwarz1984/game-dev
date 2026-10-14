/* =====================================================================
   env/terrain — the ground of a map: discrete height levels with
   organic, hand-drawn-looking edges, stairs, roads, roots and water,
   rasterised top-down at 1 px = 5 cm and then *painted in screen space*
   for the 3/4 oblique view (screen = (X, Y − Z), depth = Y + Z).

   The painter walks every world column north → south (painter's order)
   and draws each ground point at its projected row; when the height
   drops it fills the visible front face of the drop (cliff, dry-stone
   wall, stair riser, root side) with a face material. Vertical faces
   are therefore drawn full height like hand-pixelled cliffs, tops keep
   their texture, and occlusion between levels is exact.

   Output per screen pixel: albedo, material id, world normal (xy),
   world height Z and flags → packed into 256×256 chunk textures that
   the renderer draws as screen-aligned quads with per-pixel depth.
   Units inside: world px (X east, Y south, Z up). Inputs: metres.
   ===================================================================== */
import { clamp, lerp, hash2, hashi, fbm, smoothPath, NoiseTile, bayer } from './core.js';
import { TM, WM, FLAG, OUT, noise, grass, clearing, moss, floor, path, paving, tread, gravel, bed, rootTop, wall } from './groundmat.js';
import { MAT } from './paint.js';
import { PAL } from './palette.js';

export const PPM = 20; // pixels per metre
const ZS = 4;          // Z stored in quarter pixels (Int16)
const NOWATER = -32768;

export class Terrain {
  /** bounds in metres: {x0, z0, x1, z1} — the painted region (playable area + margins) */
  constructor(b, seed = 1) {
    this.b = b; this.seed = seed;
    this.ox = Math.round(b.x0 * PPM); this.oy = Math.round(b.z0 * PPM);
    this.W = Math.round((b.x1 - b.x0) * PPM); this.H = Math.round((b.z1 - b.z0) * PPM);
    const n = this.W * this.H;
    this.Z = new Int16Array(n);          // walkable surface height, quarter px
    this.top = new Uint8Array(n);        // TM id
    this.wallK = new Uint8Array(n);      // WM id of the face below this pixel's edge
    this.a0 = new Uint8Array(n);         // aux: step index / root along / path rut
    this.a1 = new Uint8Array(n);         // aux: across (0..255) / path edge
    this.pa = new Uint8Array(n);         // paint param A (calm / wear / leafy)
    this.pb = new Uint8Array(n);         // paint param B (flowers / moss)
    this.wz = new Int16Array(n).fill(NOWATER); // water surface, quarter px
    this.fl = new Int8Array(n * 2);      // water flow (x, y) * 100
    this.solid = new Uint8Array(n);      // gameplay: 1 = blocked (cliff lip, deep water, ...)
    this.top.fill(TM.GRASS); this.wallK.fill(WM.ROCK); this.pa.fill(40); this.pb.fill(80);
    noise();
  }
  idx(X, Y) { return (Y - this.oy) * this.W + (X - this.ox); }
  inb(X, Y) { return X >= this.ox && Y >= this.oy && X < this.ox + this.W && Y < this.oy + this.H; }

  /* ---------------- rasterisation helpers ---------------- */
  /** ragged closed contour (metres) → px polygon: Catmull-Rom smoothing + noise along the normal */
  ragged(polyM, amp = 0.5, scale = 3, seed = 1, fine = 0.12) {
    const P = smoothPath(polyM.map(p => [p[0] * PPM, p[1] * PPM]), 3, true);
    const out = []; const n = P.length; let s = 0;
    for (let i = 0; i < n; i++) {
      const a = P[(i - 1 + n) % n], b = P[(i + 1) % n], p = P[i];
      const tx = b[0] - a[0], ty = b[1] - a[1], tl = Math.hypot(tx, ty) || 1;
      s += Math.hypot(p[0] - a[0], p[1] - a[1]) * (i ? 0.5 : 0);
      const d = (fbm(s / (scale * PPM), seed * 0.37, 3, seed) - 0.5) * 2 * amp * PPM + (hash2(i, seed, 9) - 0.5) * fine * PPM;
      out.push([p[0] + ty / tl * d, p[1] - tx / tl * d]);
    }
    return out;
  }
  /** scanline fill of a px polygon over the world raster; fn(i, X, Y) */
  fill(poly, fn) {
    let y0 = 1e9, y1 = -1e9; for (const p of poly) { if (p[1] < y0) y0 = p[1]; if (p[1] > y1) y1 = p[1]; }
    y0 = Math.max(this.oy, Math.floor(y0)); y1 = Math.min(this.oy + this.H - 1, Math.ceil(y1));
    const xs = [];
    for (let Y = y0; Y <= y1; Y++) {
      const py = Y + 0.5; xs.length = 0;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const a = poly[i], b = poly[j];
        if ((a[1] > py) !== (b[1] > py)) xs.push((b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]);
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const xa = Math.max(this.ox, Math.ceil(xs[k] - 0.5)), xb = Math.min(this.ox + this.W - 1, Math.floor(xs[k + 1] - 0.5));
        for (let X = xa; X <= xb; X++) fn((Y - this.oy) * this.W + (X - this.ox), X, Y);
      }
    }
  }
  /** visit pixels within r px of a px polyline; fn(i, X, Y, d, segIndex, t, side, along).
      Nearest segment per pixel, kept in typed arrays over the polyline's bounding box (no Map, no garbage). */
  near(pts, r, fn) {
    let bx0 = 1e9, by0 = 1e9, bx1 = -1e9, by1 = -1e9;
    for (const p of pts) { if (p[0] < bx0) bx0 = p[0]; if (p[0] > bx1) bx1 = p[0]; if (p[1] < by0) by0 = p[1]; if (p[1] > by1) by1 = p[1]; }
    const X0 = Math.max(this.ox, Math.floor(bx0 - r)), X1 = Math.min(this.ox + this.W - 1, Math.ceil(bx1 + r));
    const Y0 = Math.max(this.oy, Math.floor(by0 - r)), Y1 = Math.min(this.oy + this.H - 1, Math.ceil(by1 + r));
    if (X1 < X0 || Y1 < Y0) return;
    const bw = X1 - X0 + 1, bh = Y1 - Y0 + 1, nb = bw * bh;
    const D = new Float32Array(nb).fill(1e9), S = new Int32Array(nb), Tt = new Float32Array(nb), Sd = new Int8Array(nb), A = new Float32Array(nb);
    let acc = 0;
    for (let s = 0; s < pts.length - 1; s++) {
      const [ax, ay] = pts[s], [bx, by] = pts[s + 1]; const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1, len = Math.sqrt(L2);
      const xa = Math.max(X0, Math.floor(Math.min(ax, bx) - r)), xb = Math.min(X1, Math.ceil(Math.max(ax, bx) + r));
      const ya = Math.max(Y0, Math.floor(Math.min(ay, by) - r)), yb = Math.min(Y1, Math.ceil(Math.max(ay, by) + r));
      for (let Y = ya; Y <= yb; Y++) for (let X = xa; X <= xb; X++) {
        let t = ((X + 0.5 - ax) * dx + (Y + 0.5 - ay) * dy) / L2; t = t < 0 ? 0 : t > 1 ? 1 : t;
        const ex = X + 0.5 - ax - dx * t, ey = Y + 0.5 - ay - dy * t, d = Math.sqrt(ex * ex + ey * ey);
        if (d > r) continue; const k = (Y - Y0) * bw + (X - X0);
        if (D[k] <= d) continue;
        D[k] = d; S[k] = s; Tt[k] = t; Sd[k] = dx * ey - dy * ex >= 0 ? 1 : -1; A[k] = acc + t * len;
      }
      acc += len;
    }
    for (let k = 0; k < nb; k++) { if (D[k] > 1e8) continue; const X = X0 + (k % bw), Y = Y0 + ((k / bw) | 0); fn((Y - this.oy) * this.W + (X - this.ox), X, Y, D[k], S[k], Tt[k], Sd[k], A[k]); }
  }

  /* ---------------- layout primitives (metres) ---------------- */
  /** a flat level: everything inside the ragged contour gets height Z (m) */
  level(polyM, Zm, o = {}) {
    const poly = o.raw ? polyM.map(p => [p[0] * PPM, p[1] * PPM]) : this.ragged(polyM, o.amp ?? 0.5, o.scale ?? 3, o.seed ?? 7, o.fine ?? 0.12);
    const z = Math.round(Zm * PPM * ZS);
    this.fill(poly, i => {
      this.Z[i] = z; if (o.top != null) this.top[i] = o.top; if (o.wall != null) this.wallK[i] = o.wall;
      if (o.pa != null) this.pa[i] = o.pa; if (o.pb != null) this.pb[i] = o.pb;
    });
    return poly;
  }
  /** change only the top material / paint params inside a contour */
  zone(polyM, o = {}) {
    const poly = o.raw ? polyM.map(p => [p[0] * PPM, p[1] * PPM]) : this.ragged(polyM, o.amp ?? 0.6, o.scale ?? 2.5, o.seed ?? 11, o.fine ?? 0.2);
    this.fill(poly, i => {
      if (o.only && !o.only.includes(this.top[i])) return;
      if (o.top != null) this.top[i] = o.top; if (o.pa != null) this.pa[i] = o.pa; if (o.pb != null) this.pb[i] = o.pb; if (o.wall != null) this.wallK[i] = o.wall;
    });
  }
  /** ellipse helper → polygon (metres) */
  static ell(cx, cz, rx, rz, n = 24, rot = 0) {
    const out = []; for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2; const x = Math.cos(a) * rx, z = Math.sin(a) * rz; out.push([cx + x * Math.cos(rot) - z * Math.sin(rot), cz + x * Math.sin(rot) + z * Math.cos(rot)]); }
    return out;
  }
  /** stairs from a (Z0) to b (Z1): n steps across `width` metres; quantised heights, stone treads and risers */
  stairs(a, b, width, Z0, Z1, n, o = {}) {
    const ax = a[0] * PPM, ay = a[1] * PPM, bx = b[0] * PPM, by = b[1] * PPM;
    const dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, hw = width * PPM / 2;
    const corners = [[ax - uy * hw, ay + ux * hw], [ax + uy * hw, ay - ux * hw], [bx + uy * hw, by - ux * hw], [bx - uy * hw, by + ux * hw]];
    const ragA = o.ragged ?? 1.5;
    this.fill(corners, (i, X, Y) => {
      const px = X + 0.5 - ax, py = Y + 0.5 - ay; const along = px * ux + py * uy, across = px * -uy + py * ux;
      // ragged ends of each tread so the flight doesn't read as a ruler-straight block
      if (Math.abs(across) > hw - ragA * hash2(Math.floor(along / 6), across > 0 ? 1 : 2, 91) * 2) return;
      const t = clamp(along / L, 0, 0.9999); const k = Math.floor(t * n);
      const z = lerp(Z0, Z1, (k + 1) / n) * PPM;
      this.Z[i] = Math.round(z * ZS); this.top[i] = TM.STEP; this.wallK[i] = WM.RISER;
      this.a0[i] = k & 255; this.a1[i] = clamp(Math.round(across + hw), 0, 255);
      this.pa[i] = clamp(Math.round((t * n - k) * (L / n)), 0, 255); // depth into the tread from its front edge... (px)
    });
  }
  /** a road / path material along a polyline (metres); o.mat TM.PATH|TM.PAVE, o.rut */
  road(ptsM, width, o = {}) {
    const P = smoothPath(ptsM.map(p => [p[0] * PPM, p[1] * PPM]), 4);
    const hw = width * PPM / 2, edge = (o.edge ?? 0.6) * PPM; const mat = o.mat ?? TM.PATH;
    const N = noise();
    this.near(P, hw + edge, (i, X, Y, d, s, t, side, along) => {
      const wob = (N.warp.sample(X * 0.25, Y * 0.25) - 0.5) * (o.wobble ?? 0.7) * PPM;
      const dd = d + wob;
      if (this.top[i] === TM.STEP && !o.overSteps) return;
      if (dd > hw + edge) return;
      const e = clamp((dd - (hw - edge * 0.5)) / edge, 0, 1); // 0 inside → 1 at the grass
      if (e >= 1) return;
      if (mat === TM.PAVE) { if (e > 0.55) return; this.top[i] = TM.PAVE; this.pb[i] = o.moss ?? 120; return; }
      this.top[i] = mat; this.a1[i] = Math.round(e * 255); this.a0[i] = clamp(Math.round(dd / hw * 120), 0, 255); this.pa[i] = o.rut ?? 0;
    });
  }
  /** a surface root of a tree: raised ridge (metres): pts from trunk outward, width & height taper */
  root(ptsM, w0, w1, h0, h1, o = {}) {
    const P = smoothPath(ptsM.map(p => [p[0] * PPM, p[1] * PPM]), 2);
    let total = 0; for (let s = 0; s < P.length - 1; s++) total += Math.hypot(P[s + 1][0] - P[s][0], P[s + 1][1] - P[s][1]);
    const base = o.base ?? null;
    this.near(P, w0 * PPM / 2 + 2, (i, X, Y, d, s, t, side, along) => {
      const u = along / total; const hw = lerp(w0, w1, u) * PPM / 2; if (d > hw) return;
      const across = side * d / hw;
      const hgt = lerp(h0, h1, Math.pow(u, 0.8)) * PPM * Math.sqrt(Math.max(0, 1 - across * across) * 0.7 + 0.3);
      const ground = base != null ? base * PPM : this.Z[i] / ZS;
      const z = Math.round((ground + hgt) * ZS);
      if (z <= this.Z[i] && this.top[i] === TM.ROOT) return;
      if (z < this.Z[i]) return;
      this.Z[i] = z; this.top[i] = TM.ROOT; this.wallK[i] = WM.BARK;
      this.a0[i] = Math.round(along) & 255; this.a1[i] = clamp(Math.round((across * 0.5 + 0.5) * 255), 0, 255);
    });
  }
  /** water along a polyline: surface Z per point (m), width (m); carves the bed */
  stream(ptsM, width, surfM, o = {}) {
    const P = ptsM.map(p => [p[0] * PPM, p[1] * PPM]); const hw = width * PPM / 2; const N = noise();
    this.near(P, hw + 3, (i, X, Y, d, s, t) => {
      const wob = (N.warp.sample(X * 0.3 + 40, Y * 0.3) - 0.5) * 0.5 * PPM; if (d + wob > hw) return;
      const sz = (o.step ? surfM[s] : lerp(surfM[s], surfM[s + 1], t)) * PPM;
      const depth = (o.depth ?? 0.35) * PPM * Math.sqrt(Math.max(0, 1 - Math.pow((d + wob) / hw, 2)));
      this.wz[i] = Math.round(sz * ZS);
      this.Z[i] = Math.round((sz - Math.max(1.5, depth)) * ZS); this.top[i] = TM.BED;
      const dx = P[s + 1][0] - P[s][0], dy = P[s + 1][1] - P[s][1], l = Math.hypot(dx, dy) || 1;
      const sp = o.speed ?? 0.8; this.fl[i * 2] = Math.round(dx / l * sp * 100); this.fl[i * 2 + 1] = Math.round(dy / l * sp * 100);
    });
  }
  /** a still pool (ellipse, metres) */
  pool(cx, cz, rx, rz, surfM, depthM, o = {}) {
    const poly = this.ragged(Terrain.ell(cx, cz, rx, rz, 28, o.rot || 0), o.amp ?? 0.35, 2, o.seed ?? 5);
    this.fill(poly, (i, X, Y) => {
      const u = (X / PPM - cx) / rx, v = (Y / PPM - cz) / rz; const k = clamp(1 - Math.sqrt(u * u + v * v), 0, 1);
      this.wz[i] = Math.round(surfM * PPM * ZS);
      this.Z[i] = Math.round((surfM - 0.08 - depthM * Math.sqrt(k)) * PPM * ZS); this.top[i] = TM.BED;
      this.fl[i * 2] = Math.round(-v * 12); this.fl[i * 2 + 1] = Math.round(u * 12);
    });
  }

  /* ---------------- queries (metres) ---------------- */
  heightAt(x, z) { const X = Math.floor(x * PPM), Y = Math.floor(z * PPM); if (!this.inb(X, Y)) return 0; return this.Z[this.idx(X, Y)] / ZS / PPM; }
  waterAt(x, z) { const X = Math.floor(x * PPM), Y = Math.floor(z * PPM); if (!this.inb(X, Y)) return null; const w = this.wz[this.idx(X, Y)]; if (w === NOWATER) return null; const s = w / ZS / PPM; return { surface: s, depth: s - this.Z[this.idx(X, Y)] / ZS / PPM }; }
  topAt(x, z) { const X = Math.floor(x * PPM), Y = Math.floor(z * PPM); return this.inb(X, Y) ? this.top[this.idx(X, Y)] : 0; }

  /* ---------------- the screen-space painter ---------------- */
  paint(o = {}) {
    const t0 = Date.now();
    const W = this.W, H = this.H, Z = this.Z;
    // screen rows: row = Y − Z − rowMin
    let zmax = -1e9, zmin = 1e9; for (let i = 0; i < Z.length; i++) { const z = Z[i]; if (z > zmax) zmax = z; if (z < zmin) zmin = z; }
    zmax = Math.ceil(zmax / ZS) + 2; zmin = Math.floor(zmin / ZS) - 2;
    const rowMin = this.oy - zmax, rows = H + zmax - zmin + 4; this.rowMin = rowMin; this.rows = rows;
    const n = W * rows;
    const alb = this.alb = new Uint8ClampedArray(n * 4), nrm = this.nrm = new Int8Array(n * 2), sz = this.sz = new Int16Array(n), sm = this.sm = new Uint8Array(n), sf = this.sf = new Uint8Array(n);
    sz.fill(-32768);
    // blurred height for face orientation
    const Zb = boxBlur(Z, W, H, 7);
    const LX = -0.99, LY = 0.11; // horizontal part of the top-left light (world)
    const N = noise();
    for (let x = 0; x < W; x++) {
      const X = x + this.ox; let prev = null, footAO = 0, lip = -1;
      for (let y = 0; y < H; y++) {
        const Y = y + this.oy, i = y * W + x, zq = Z[i], zi = Math.round(zq / ZS);
        if (this.top[i] === TM.NONE) { prev = null; lip = -1; continue; }
        const row = Y - zi - rowMin;
        // ---- the face below the previous top (height dropped going south)
        if (prev !== null && prev > zi) {
          const iu = i - W; const kind = this.wallK[iu], topU = this.top[iu];
          const Hh = prev - zi; const r0 = Y - prev - rowMin;
          // face orientation from the blurred height field
          const gx = (Zb[Math.min(W - 1, x + 4) + Math.max(0, y - 4) * W] - Zb[Math.max(0, x - 4) + Math.max(0, y - 4) * W]) / 8;
          const gy = (Zb[x + Math.min(H - 1, y + 2) * W] - Zb[x + Math.max(0, y - 6) * W]) / 8;
          let nx = -gx, ny = -gy; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl; if (ny < 0.15) { ny = 0.15; const l2 = Math.hypot(nx, ny); nx /= l2; ny /= l2; }
          const lit = nx * LX + ny * LY;
          const over = (topU === TM.GRASS || topU === TM.MEADOW || topU === TM.CLEAR || topU === TM.MOSS) ? overhang(X) : (topU === TM.FLOOR || topU === TM.NEEDLE) ? overhang(X) >> 1 : 0;
          for (let r = r0, k = 0; r < row; r++, k++) {
            if (r < 0 || r >= rows) continue;
            const h = Hh - k - 1; // height above the foot
            const j = r * W + x;
            if (k < over && Hh > 6) { // grass/moss hanging over the lip
              if (topU === TM.MOSS) moss(X, Y - 1, x, r, 0.3); else grass(X, Y - 1, x, r, 0.3, 0.6, 0);
              const dk = 0.86 - k * 0.07; OUT[0] *= dk; OUT[1] *= dk; OUT[2] *= dk; OUT[3] = nx * 0.5; OUT[4] = ny * 0.5; OUT[6] = FLAG.WALL;
            } else if (Hh <= 6 && kind !== WM.RISER && kind !== WM.BARK && (topU === TM.GRASS || topU === TM.MEADOW || topU === TM.CLEAR)) {
              // a small bank: a grassy slope, not a cliff
              grass(X, Y - 1 + k, x, r, 0.2, 0.6, 0); const dk = 0.8 - k * 0.04; OUT[0] *= dk; OUT[1] *= dk; OUT[2] *= dk; OUT[3] = nx * 0.4; OUT[4] = 0.4; OUT[6] = FLAG.WALL;
            } else if (kind === WM.RISER) {
              wall(WM.RISER, X, this.a1[iu] + this.a0[iu] * 37, prev - k, h, Hh, x, r, lit);
            } else if (kind === WM.BARK) {
              wall(WM.BARK, X, this.a0[iu] * 3 + x, prev - k, h, Hh, x, r, lit);
            } else {
              wall(kind, X, X, prev - k + 400, h, Hh, x, r, lit);
              if (kind !== WM.STONEWALL && h < 3 && hash2(X, h, 97) < 0.3) { OUT[0] *= 0.8; OUT[1] *= 0.82; OUT[2] *= 0.85; }
            }
            this._put(j, OUT, Y - 0.5, prev - k - 0.5, nx, ny);
          }
          footAO = Math.min(7, 2 + Hh / 6);
          if (lip >= 0 && lip < n) { // the lit lip of the level above
            const q = lip * 4; alb[q] = Math.min(255, alb[q] * 1.12 + 6); alb[q + 1] = Math.min(255, alb[q + 1] * 1.12 + 6); alb[q + 2] = Math.min(255, alb[q + 2] * 1.06 + 3); sf[lip] |= FLAG.LIP;
          }
        }
        // ---- the top surface
        if (row >= 0 && row < rows) {
          // ragged material borders (v0.1): the material is looked up a couple of pixels away along a
          // fine noise, on the same level only — so every border between grass, moss, earth and road frays
          const jx = Math.round((N.cl.sample(x * 0.84, row * 0.84) - 0.5) * 4.2), jy = Math.round((N.cl2.sample(x * 0.84 + 9, row * 0.84) - 0.5) * 4.2);
          let i2 = i; if ((jx || jy) && this.inb(X + jx, Y + jy)) { const k2 = i + jy * W + jx; if (Z[k2] === zq && this.top[k2] !== TM.NONE && this.top[k2] !== TM.STEP && this.top[i] !== TM.STEP) i2 = k2; }
          this._top(i2, X, Y, x, row);
          if (footAO > 0) { const k = 1 - footAO * 0.055; OUT[0] *= k; OUT[1] *= k; OUT[2] *= k * 1.02; footAO -= 1; }
          const j = row * W + x; this._put(j, OUT, Y, zi, OUT[3], OUT[4]);
          lip = j;
        }
        prev = zi;
      }
    }
    this._sideEdges();
    this.paintMs = Date.now() - t0;
    return this;
  }
  _top(i, X, Y, x, y) {
    const t = this.top[i], pa = this.pa[i] / 255, pb = this.pb[i] / 255;
    switch (t) {
      case TM.GRASS: grass(X, Y, x, y, pa * 0.6, 0.6, pb * 0.6); break;
      case TM.MEADOW: grass(X, Y, x, y, pa * 0.4, 0.45, 0.4 + pb * 0.6, 0.3); break;
      case TM.CLEAR: clearing(X, Y, x, y, pa); break;
      case TM.MOSS: moss(X, Y, x, y, pa); break;
      case TM.FLOOR: floor(X, Y, x, y, pb); break;
      case TM.NEEDLE: floor(X, Y, x, y, 0.1); break;
      case TM.PATH: { const e = this.a1[i] / 255; path(X, Y, x, y, e, this.a0[i] / 120 * 30, 30, pa); break; }
      case TM.PAVE: paving(X, Y, x, y, pb); break;
      case TM.STEP: tread(X, Y, x, y, this.a0[i], this.a1[i], this.pa[i], 0.4); break;
      case TM.ROOT: rootTop(X, Y, x, y, this.a0[i], this.a1[i] / 127.5 - 1); break;
      case TM.GRAVEL: gravel(X, Y, x, y); break;
      case TM.BED: bed(X, Y, x, y); break;
      case TM.SCREE: gravel(X, Y, x, y); OUT[0] *= 0.9; OUT[1] *= 0.9; break;
      case TM.ROCKTOP: wall(WM.MOSSROCK, X, X, Y, 50, 99, x, y, 0.5); OUT[6] = 0; OUT[3] = 0; OUT[4] = 0; break;
      case TM.MUD: floor(X, Y, x, y, 0); OUT[0] *= 0.7; OUT[1] *= 0.7; OUT[2] *= 0.72; OUT[6] = FLAG.WET; break;
      default: grass(X, Y, x, y, 0.3, 0.6, 0.2);
    }
  }
  _put(j, o, Yw, zpx, nx, ny) {
    const q = j * 4; this.alb[q] = o[0]; this.alb[q + 1] = o[1]; this.alb[q + 2] = o[2]; this.alb[q + 3] = 255;
    this.nrm[j * 2] = clamp(Math.round(nx * 127), -127, 127); this.nrm[j * 2 + 1] = clamp(Math.round(ny * 127), -127, 127);
    this.sz[j] = clamp(Math.round(zpx * 8), -32767, 32767); this.sm[j] = o[5]; this.sf[j] = o[6];
  }
  /** dark line where a higher level's side edge meets lower ground (N–S running edges) */
  _sideEdges() {
    const W = this.W, R = this.rows, sz = this.sz, alb = this.alb;
    for (let r = 0; r < R; r++) for (let x = 1; x < W - 1; x++) {
      const j = r * W + x; if (sz[j] === -32768) continue; const z = sz[j];
      for (const dx of [-1, 1]) {
        const k = j + dx; if (sz[k] === -32768) continue;
        if (sz[k] - z > 8 * 6 && !(this.sf[j] & FLAG.WALL)) { // neighbour is a higher level's edge: shade this side
          const q = j * 4; alb[q] *= 0.7; alb[q + 1] *= 0.72; alb[q + 2] *= 0.78;
        }
      }
    }
  }

  /* ---------------- water layer (screen space) ----------------
     For each water pixel: surface height, flow, depth, shore and fall flags.
     Falls are filled where the surface drops going south. */
  paintWater() {
    const W = this.W, H = this.H, rows = this.rows, rowMin = this.rowMin;
    const n = W * rows; const wf = this.wfl = new Int8Array(n * 2), wd = this.wdep = new Uint8Array(n), wsz = this.wsz = new Int16Array(n), wfg = this.wflag = new Uint8Array(n);
    wsz.fill(-32768);
    // shore distance (cheap): count dry neighbours in a 7×7 box
    for (let x = 0; x < W; x++) {
      let prev = null;
      for (let y = 0; y < H; y++) {
        const i = y * W + x; const w = this.wz[i]; const X = x + this.ox, Y = y + this.oy;
        if (w === NOWATER) { prev = null; continue; }
        const zi = Math.round(w / ZS); const row = Y - zi - rowMin;
        if (prev !== null && prev > zi + 1) { // a fall
          for (let r = Y - prev - rowMin, k = 0; r < row; r++, k++) {
            if (r < 0 || r >= rows) continue; const j = r * W + x;
            wsz[j] = (prev - k - 1) * 8; wf[j * 2] = 0; wf[j * 2 + 1] = 127; wd[j] = 40; wfg[j] = 1 | (k < 3 ? 4 : 0);
          }
        }
        if (row >= 0 && row < rows) {
          const j = row * W + x; let dry = 0;
          for (let d = -3; d <= 3; d += 1) { if (x + d < 0 || x + d >= W || this.wz[i + d] === NOWATER) dry++; if (y + d < 0 || y + d >= H || this.wz[i + d * W] === NOWATER) dry++; }
          wsz[j] = zi * 8; wf[j * 2] = this.fl[i * 2]; wf[j * 2 + 1] = this.fl[i * 2 + 1];
          wd[j] = clamp(Math.round((w - this.Z[i]) / ZS * 4), 0, 255); wfg[j] = dry > 0 ? 2 : 0; this.wshore = this.wshore || new Uint8Array(n); this.wshore[j] = clamp(dry * 18, 0, 255);
        }
        prev = zi;
      }
    }
    return this;
  }

  /* ---------------- packing into chunk textures ----------------
     T0: albedo rgb + material id; T1: normal x,y (0..255), Z (16 bit, 1/8 px + 4096 bias)
     Water chunks: W0: flow x,y, depth, flags; W1: Z (16 bit), shore, 0 */
  pack(CH = 256) {
    const W = this.W, R = this.rows, out = [];
    for (let cy = 0; cy < R; cy += CH) for (let cx = 0; cx < W; cx += CH) {
      const w = Math.min(CH, W - cx), h = Math.min(CH, R - cy); let any = false, anyW = false;
      const t0 = new Uint8Array(CH * CH * 4), t1 = new Uint8Array(CH * CH * 4);
      let w0 = null, w1 = null;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const j = (cy + y) * W + cx + x, k = (y * CH + x) * 4;
        if (this.sz[j] !== -32768) {
          any = true;
          t0[k] = this.alb[j * 4]; t0[k + 1] = this.alb[j * 4 + 1]; t0[k + 2] = this.alb[j * 4 + 2]; t0[k + 3] = (this.sm[j] & 31) | ((this.sf[j] & FLAG.BLADE) ? 32 : 0) | ((this.sf[j] & FLAG.WET) ? 128 : 0);
          t1[k] = this.nrm[j * 2] + 128; t1[k + 1] = this.nrm[j * 2 + 1] + 128; const zz = this.sz[j] + 16384; t1[k + 2] = zz & 255; t1[k + 3] = (zz >> 8) & 255;
        }
        if (this.wsz && this.wsz[j] !== -32768) {
          if (!w0) { w0 = new Uint8Array(CH * CH * 4); w1 = new Uint8Array(CH * CH * 4); }
          anyW = true;
          w0[k] = this.wfl[j * 2] + 128; w0[k + 1] = this.wfl[j * 2 + 1] + 128; w0[k + 2] = this.wdep[j]; w0[k + 3] = this.wflag[j] * 32 + 16;
          const zz = this.wsz[j] + 16384; w1[k] = zz & 255; w1[k + 1] = (zz >> 8) & 255; w1[k + 2] = this.wshore ? this.wshore[j] : 0; w1[k + 3] = 255;
        }
      }
      if (any || anyW) out.push({ sx: this.ox + cx, sy: this.rowMin + cy, w: CH, h: CH, t0: any ? t0 : null, t1: any ? t1 : null, w0, w1 });
    }
    return out;
  }
}

/** grass/moss overhang length at the top of a face (px), stable per column */
function overhang(X) { // sod hangs over in clumps (a smooth per-column length plus a little jitter), not a comb
  const c = Math.floor(X / 7), f = X / 7 - c, a = hash2(c, 0, 101), b = hash2(c + 1, 0, 101), n = a + (b - a) * f * f * (3 - 2 * f);
  const h = hash2(X, 0, 102); return Math.max(1, Math.round(n * 4.2 - 0.6) + (h < 0.18 ? 1 : 0));
}

/** separable box blur of an Int16 field (returns Float32, units = input units / ZS → px) */
function boxBlur(src, W, H, r) {
  const tmp = new Float32Array(W * H), out = new Float32Array(W * H), k = 1 / (2 * r + 1);
  for (let y = 0; y < H; y++) {
    let acc = 0; const o = y * W;
    for (let x = -r; x <= r; x++) acc += src[o + clamp(x, 0, W - 1)];
    for (let x = 0; x < W; x++) { tmp[o + x] = acc * k / ZS; acc += src[o + Math.min(W - 1, x + r + 1)] - src[o + Math.max(0, x - r)]; }
  }
  for (let x = 0; x < W; x++) {
    let acc = 0;
    for (let y = -r; y <= r; y++) acc += tmp[clamp(y, 0, H - 1) * W + x];
    for (let y = 0; y < H; y++) { out[y * W + x] = acc * k; acc += tmp[Math.min(H - 1, y + r + 1) * W + x] - tmp[Math.max(0, y - r) * W + x]; }
  }
  return out;
}
