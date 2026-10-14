/* =====================================================================
   WORLD — 九十九折峠, the Pass of Ninety-Nine Bends. A saddle in a cedar
   ridge; an old road of switchbacks falls south from her shrine to a
   valley with a pond and a railway that went Far. East, a stream drops
   over a fall; west, cedars climb to a ruined inner shrine; south-west,
   a bamboo grove hides a charcoal-burner's hut; south-east, a susuki
   meadow looks out over where the plain used to be.
   Units: world pixels. X east, Y south, Z up.
   ===================================================================== */
"use strict";
const WD = {};
const LM = { // landmarks (world px)
  shrine: [1150, 560], spring: [1388, 604], fallTop: [1640, 986], pool: [1652, 1062], pond: [1250, 1822],
  inner: [432, 318], hut: [470, 1496], kiln: [580, 1570], lookout: [2072, 1374], tunnel: [1990, 1770], train: [1830, 1800],
  zone: { cx: 1150, cy: 1140, rx: 1130, ry: 930 },
};
const ROAD = [[1150, 400], [1150, 560], [1124, 636], [986, 694], [1006, 760], [1238, 818], [1252, 884], [1042, 948], [1022, 1012], [1222, 1078], [1236, 1142], [1062, 1202], [1050, 1264], [1198, 1330], [1184, 1402], [1118, 1478], [1146, 1560], [1150, 1650], [1166, 1760], [1186, 1900], [1204, 2060]];
const STREAM = [[1388, 604], [1420, 680], [1470, 760], [1530, 842], [1598, 920], [1640, 986], [1652, 1062], [1626, 1140], [1566, 1250], [1484, 1360], [1402, 1480], [1342, 1598], [1294, 1720], [1250, 1822], [1150, 1902], [1046, 2060]];
const STAIR = [[560, 640], [530, 560], [492, 480], [470, 400], [448, 340]];
const RAIL = [[2030, 1790], [1700, 1806], [1300, 1934], [900, 1960], [300, 1930], [-40, 1900]];

const WORLD = {
  build() {
    const W = 2304, H = 2048, S = 4, cw = W / S, ch = H / S, vx = cw + 1, vy = ch + 1;
    Object.assign(WD, { W, H, cell: S, cw, ch, nw: W / 8, nh: H / 8, wet: 0, props: [], grass: [] });
    const h = new Float32Array(vx * vy);
    WD.mat = new Uint8Array(cw * ch); WD.moist = new Uint8Array(cw * ch); WD.ao = new Uint8Array(cw * ch); WD.feat = new Uint8Array(cw * ch);
    WD.water = new Float32Array(cw * ch).fill(-999); WD.flow = new Float32Array(cw * ch * 2); WD.shore = new Uint8Array(cw * ch);
    WD.near = new Float32Array(WD.nw * WD.nh); WD.wear = new Float32Array(WD.nw * WD.nh);
    // ---------------- height ----------------
    const ridgeY = x => 470 + 50 * Math.sin(x * .0042 + .6) + 30 * Math.sin(x * .011);
    const peak = (x, c, w, a) => a * Math.exp(-Math.pow((x - c) / w, 2));
    const ridgeH = x => 236 + peak(x, 430, 260, 96) + peak(x, 1920, 300, 86) - peak(x, 1150, 140, 6) + 14 * Math.sin(x * .013);
    const distSeg = (px, py, pts) => { let best = 1e9, bt = 0, bi = 0; for (let i = 0; i < pts.length - 1; i++) { const [ax, ay] = pts[i], [bx, by] = pts[i + 1]; const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy; let t = ((px - ax) * dx + (py - ay) * dy) / L2; t = clamp(t, 0, 1); const d = hyp(px - ax - dx * t, py - ay - dy * t); if (d < best) { best = d; bt = t; bi = i; } } return { d: best, i: bi, t: bt }; };
    const base = (x, y) => {
      const ry = ridgeY(x), rh = ridgeH(x);
      let z;
      if (y < ry) z = rh - Math.pow((ry - y) / 260, 1.3) * 230;
      else { const t = clamp((y - ry) / (1880 - ry), 0, 1); z = rh * (1 - Math.pow(t, .82) * .9) + 6; }
      z += (fbm(x * .006, y * .006, 4, 3) - .5) * 46 + (fbm(x * .02, y * .02, 3, 7) - .5) * 10;
      // spurs and gullies running down the slope
      z += Math.sin(x * .009 + Math.sin(y * .004) * 2) * 14 * clamp((y - 600) / 600, 0, 1);
      return z;
    };
    for (let j = 0; j < vy; j++) for (let i = 0; i < vx; i++) h[j * vx + i] = base(i * S, j * S);
    const H0 = (x, y) => h[clamp(Math.round(y / S), 0, ch) * vx + clamp(Math.round(x / S), 0, cw)];
    const edit = (x0, y0, x1, y1, fn) => { for (let j = Math.max(0, Math.floor(y0 / S)); j <= Math.min(ch, Math.ceil(y1 / S)); j++) for (let i = Math.max(0, Math.floor(x0 / S)); i <= Math.min(cw, Math.ceil(x1 / S)); i++) { const k = j * vx + i; const r = fn(i * S, j * S, h[k]); if (r != null) h[k] = r; } };
    // terraces on the steep upper slopes: crisp cliff bands
    edit(0, 300, W, 1500, (x, y, z) => { const rocky = fbm(x * .004, y * .004, 3, 11); if (rocky < .52) return null; const k = sstep(.52, .62, rocky); const step = 26; const q = Math.floor(z / step) * step + sstep(.78, 1, fract(z / step)) * step; return lerp(z, q, k * .85); });
    // the pass shrine clearing: a level saddle with a little stone platform
    const [sx, sy] = LM.shrine, shZ = base(sx, sy) + 4;
    edit(sx - 130, sy - 110, sx + 130, sy + 110, (x, y, z) => { const d = hyp((x - sx) / 118, (y - sy) / 92); return d < 1 ? lerp(shZ, z, sstep(.72, 1, d)) : null; });
    WD.shrineZ = shZ;
    // the inner shrine on the north-west peak: a level terrace
    const [ix, iy] = LM.inner, inZ = base(ix, iy) + 6;
    edit(ix - 110, iy - 80, ix + 110, iy + 90, (x, y, z) => { const d = hyp((x - ix) / 96, (y - iy) / 72); return d < 1 ? lerp(inZ, z, sstep(.75, 1, d)) : null; });
    // stream: a ravine carved along its course; the fall is a sheer drop
    const fallI = 5;
    const sz = STREAM.map(([x, y], i) => base(x, y));
    for (let i = 1; i < sz.length; i++) sz[i] = Math.min(sz[i], sz[i - 1] - (i === fallI + 1 ? 48 : 3)); // water only runs downhill; one big drop
    WD.streamZ = sz;
    edit(1000, 560, 1760, 2048, (x, y, z) => {
      const r = distSeg(x, y, STREAM); const i = r.i, t = r.t; let bed = lerp(sz[i], sz[i + 1], i === fallI ? (t < .96 ? 0 : 1) : t) - 7;
      const wide = i >= 12 ? 0 : 1; const hw = (i === fallI + 1 ? 30 : 13) + (i >= 6 && i <= 7 ? 10 : 0);
      if (r.d < hw) return Math.min(z, bed);
      if (r.d < hw + 46) { const k = (r.d - hw) / 46; return Math.min(z, lerp(bed + 6, z, Math.pow(k, i <= fallI + 1 ? .45 : .8))); }
      return null;
    });
    // the pond basin
    const [px, py] = LM.pond, pZ = sz[13] - 3;
    edit(px - 160, py - 120, px + 160, py + 120, (x, y, z) => { const d = hyp((x - px) / 96, (y - py) / 64); if (d < 1) return Math.min(z, pZ - 10 * (1 - d * d)); if (d < 1.6) return Math.min(z, lerp(pZ + 1, z, (d - 1) / .6)); return null; });
    // the old road: a shelf cut into the slope, falling evenly bend to bend
    const rz = ROAD.map(([x, y]) => base(x, y)); rz[1] = shZ; rz[0] = shZ + 10;
    for (let i = 2; i < rz.length; i++) rz[i] = Math.min(rz[i - 1] - 2, lerp(rz[i - 1], base(ROAD[i][0], ROAD[i][1]), .85));
    WD.roadZ = rz;
    edit(900, 380, 1320, 2048, (x, y, z) => { const r = distSeg(x, y, ROAD); if (r.d > 30) return null; const rzz = lerp(rz[r.i], rz[r.i + 1], r.t); const k = r.d < 12 ? 1 : 1 - sstep(12, 30, r.d) ; return lerp(z, rzz, k); });
    // the inner-shrine stair: a cut through the cedar slope
    const stz = STAIR.map(([x, y]) => base(x, y)); stz[stz.length - 1] = inZ;
    edit(380, 300, 640, 700, (x, y, z) => { const r = distSeg(x, y, STAIR); if (r.d > 18) return null; const zz = lerp(stz[r.i], stz[r.i + 1], r.t); const q = Math.floor(zz / 5) * 5; return lerp(z, q, r.d < 8 ? 1 : 1 - sstep(8, 18, r.d)); });
    // railway bed along the valley floor
    const railZ = RAIL.map(([x, y]) => Math.min(base(x, y), 40));
    edit(0, 1700, W, 2048, (x, y, z) => { const r = distSeg(x, y, RAIL); if (r.d > 26) return null; const zz = lerp(railZ[r.i], railZ[r.i + 1], r.t); return lerp(z, zz, r.d < 12 ? 1 : 1 - sstep(12, 26, r.d)); });
    // the tunnel cuts into the east slope: a steep face above the portal
    edit(1900, 1640, 2120, 1800, (x, y, z) => { const dx = x - LM.tunnel[0]; if (y > 1772 || Math.abs(dx) > 90) return null; return Math.max(z, 40 + (1772 - y) * 2.2); });
    // the lookout rock on the meadow
    const [lx, ly] = LM.lookout; edit(lx - 50, ly - 40, lx + 50, ly + 40, (x, y, z) => { const d = hyp((x - lx) / 34, (y - ly) / 24); return d < 1 ? z + 26 * (1 - Math.pow(d, 6)) : null; });
    WD.h = h;
    // ---------------- water ----------------
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
      const x = i * S + 2, y = j * S + 2, k = j * cw + i; const gz = (h[j * vx + i] + h[j * vx + i + 1] + h[(j + 1) * vx + i] + h[(j + 1) * vx + i + 1]) / 4;
      const r = distSeg(x, y, STREAM);
      if (r.i < 13 || (r.i >= 13 && r.d < 20)) {
        const hw = (r.i === fallI + 1 ? 26 : r.i >= 13 ? 9 : 9) + (r.i === 6 ? 6 : 0);
        if (r.d < hw) { const surf = lerp(sz[r.i], sz[r.i + 1], r.i === fallI ? (r.t < .96 ? 0 : 1) : r.t) - 2.5; if (surf > gz + .5) { WD.water[k] = surf; const [ax, ay] = STREAM[r.i], [bx, by] = STREAM[r.i + 1]; const L = hyp(bx - ax, by - ay); const sp = r.i === fallI + 1 ? .25 : r.i >= 12 ? .35 : .8; WD.flow[k * 2] = (bx - ax) / L * sp; WD.flow[k * 2 + 1] = (by - ay) / L * sp; } }
      }
      const dp = hyp((x - px) / 96, (y - py) / 64); if (dp < 1.04) { WD.water[k] = pZ - 1; WD.flow[k * 2] = -.04; WD.flow[k * 2 + 1] = .03; }
    }
    // shore factor for foam
    for (let j = 1; j < ch - 1; j++) for (let i = 1; i < cw - 1; i++) { const k = j * cw + i; if (WD.water[k] < -500) continue; let dry = 0; for (let dj = -2; dj <= 2; dj++) for (let di = -2; di <= 2; di++) { const q = clamp(j + dj, 0, ch - 1) * cw + clamp(i + di, 0, cw - 1); if (WD.water[q] < -500) dry++; } WD.shore[k] = clamp(dry * 22, 0, 255); }
    // ---------------- materials ----------------
    const cedarZone = (x, y) => { const d = hyp((x - 520) / 420, (y - 920) / 380) + (fbm(x * .006, y * .006, 3, 21) - .5) * .5; return d < 1; };
    const bambooZone = (x, y) => hyp((x - 430) / 300, (y - 1660) / 270) + (fbm(x * .008, y * .008, 3, 23) - .5) * .4 < 1;
    const meadow = (x, y) => hyp((x - 1960) / 300, (y - 1450) / 260) + (fbm(x * .007, y * .007, 3, 25) - .5) * .4 < 1;
    WD.zones = { cedarZone, bambooZone, meadow };
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
      const x = i * S + 2, y = j * S + 2, k = j * cw + i; const z = h[j * vx + i];
      let m = 1, moist = 120 + fbm(x * .01, y * .01, 3, 5) * 100;
      if (cedarZone(x, y)) { m = fbm(x * .02, y * .02, 2, 4) > .6 ? 6 : 2; moist += 40; }
      if (bambooZone(x, y)) m = 2;
      if (z > 300) m = fbm(x * .03, y * .03, 2, 6) > .55 ? 3 : 1;
      // damp moss along the stream
      const rs = distSeg(x, y, STREAM); if (rs.d < 40 && rs.i < 13) { m = rs.d < 22 ? 8 : (fbm(x * .05, y * .05, 2, 9) > .45 ? 6 : m); moist = 255; }
      const dp = hyp((x - px) / 96, (y - py) / 64); if (dp < 1.25 && dp > .95) m = 9;
      // roads & stairs & rail
      const rr = distSeg(x, y, ROAD); if (rr.d < 11) { const paved = rr.i <= 2 || rr.i >= 15 && rr.i <= 16 || fbm(x * .03, y * .03, 2, 8) > .62; m = paved ? 7 : 4; WD.feat[k] = 1; }
      const st = distSeg(x, y, STAIR); if (st.d < 9) { m = 7; WD.feat[k] = 2; }
      const ra = distSeg(x, y, RAIL); if (ra.d < 10) { m = 10; WD.feat[k] = 3; }
      // the shrine clearing
      const ds = hyp((x - sx) / 60, (y - sy) / 46); if (ds < 1) m = ds < .55 ? 7 : 4;
      const di = hyp((x - ix) / 70, (y - iy) / 50); if (di < 1) m = 7;
      if (WD.water[k] > -500) m = 5;
      WD.mat[k] = m; WD.moist[k] = clamp(moist, 0, 255);
    }
    // baked occlusion: hollows and the feet of slopes
    for (let j = 0; j < ch; j++) for (let i = 0; i < cw; i++) {
      const z = h[j * vx + i]; let occ = 0;
      for (const [di, dj] of [[3, 0], [-3, 0], [0, -3], [2, -2], [-2, -2], [0, -6]]) { const q = clamp(j + dj, 0, ch) * vx + clamp(i + di, 0, cw); occ += clamp((h[q] - z) / 18, 0, 1); }
      WD.ao[j * cw + i] = clamp(255 - occ / 6 * 210, 30, 255);
    }
    // ---------------- nearness: the island of the Near in a sea of Far ----------------
    const Z = LM.zone;
    for (let j = 0; j < WD.nh; j++) for (let i = 0; i < WD.nw; i++) {
      const x = i * 8 + 4, y = j * 8 + 4; const a = Math.atan2(y - Z.cy, x - Z.cx);
      const d = hyp((x - Z.cx) / Z.rx, (y - Z.cy) / Z.ry) + (fbm(Math.cos(a) * 2 + 9, Math.sin(a) * 2 + 4, 3, 31) - .5) * .22;
      let n = 1 - sstep(.9, 1.04, d);
      WD.near[j * WD.nw + i] = n;
    }
    this.buildProps();
    this.buildGrass();
  },
  // spatial hash of scenery colliders (trunks, stones, the hut)
  buildGrid() { const g = new Map(); for (const p of WD.props) { if (!p.col) continue; const k = Math.floor(p.y / 64) * 1000 + Math.floor(p.x / 64); if (!g.has(k)) g.set(k, []); g.get(k).push([p.x, p.y, p.col]); } this.grid = g; },
  /* ---------- queries ---------- */
  heightAt(x, y) {
    const S = WD.cell, vx = WD.cw + 1; const fx = clamp(x / S, 0, WD.cw - .001), fy = clamp(y / S, 0, WD.ch - .001);
    const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j, h = WD.h;
    const a = h[j * vx + i], b = h[j * vx + i + 1], c = h[(j + 1) * vx + i], d = h[(j + 1) * vx + i + 1];
    return lerp(lerp(a, b, u), lerp(c, d, u), v);
  },
  cellAt(x, y) { return clamp(Math.floor(y / WD.cell), 0, WD.ch - 1) * WD.cw + clamp(Math.floor(x / WD.cell), 0, WD.cw - 1); },
  matAt(x, y) { return WD.mat[this.cellAt(x, y)]; },
  waterAt(x, y) { return WD.water[this.cellAt(x, y)]; },
  flowAt(x, y) { const k = this.cellAt(x, y); return [WD.flow[k * 2], WD.flow[k * 2 + 1]]; },
  nearIdx(x, y) { return clamp(Math.floor(y / 8), 0, WD.nh - 1) * WD.nw + clamp(Math.floor(x / 8), 0, WD.nw - 1); },
  nearAt(x, y) { return WD.near[this.nearIdx(x, y)]; },
  wearAt(x, y) { return WD.wear[this.nearIdx(x, y)]; },
  roadInfo(x, y) { let best = 1e9, bi = 0; for (let i = 0; i < ROAD.length - 1; i++) { const [ax, ay] = ROAD[i], [bx, by] = ROAD[i + 1]; const dx = bx - ax, dy = by - ay; let t = clamp(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1); const d = hyp(x - ax - dx * t, y - ay - dy * t); if (d < best) { best = d; bi = i; } } return { d: best, bend: bi }; },
  /* ---------- scenery ---------- */
  buildProps() {
    const R = RNG(2024), P = WD.props, A = ATLAS.rects;
    const occ = []; // blocked discs for spacing
    const free = (x, y, r) => { for (const o of occ) if (hyp(o[0] - x, o[1] - y) < o[2] + r) return false; return true; };
    const onRoad = (x, y, m = 16) => { for (const pts of [ROAD, STAIR]) { for (let i = 0; i < pts.length - 1; i++) { const [ax, ay] = pts[i], [bx, by] = pts[i + 1]; const dx = bx - ax, dy = by - ay; const t = clamp(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1); if (hyp(x - ax - dx * t, y - ay - dy * t) < m) return true; } } return false; };
    const wet = (x, y, m = 6) => { for (let dy = -m; dy <= m; dy += m) for (let dx = -m; dx <= m; dx += m) if (this.waterAt(x + dx, y + dy) > -500) return true; return false; };
    const steep = (x, y) => { const a = this.heightAt(x - 4, y), b = this.heightAt(x + 4, y), c = this.heightAt(x, y - 4), d = this.heightAt(x, y + 4); return Math.max(Math.abs(a - b), Math.abs(c - d)) > 9; };
    const add = (name, x, y, o = {}) => { const r = A[name]; if (!r) return null; const p = Object.assign({ name, x: Math.round(x), y: Math.round(y), z: Math.round(this.heightAt(x, y)) - (o.sink || 0), r, sway: r.sway, flip: R() < .5, col: 0 }, o); P.push(p); if (o.col) occ.push([x, y, o.col]); return p; };
    const [sx, sy] = LM.shrine;
    const keepOut = [[sx, sy, 92], [LM.hut[0], LM.hut[1], 70], [LM.kiln[0], LM.kiln[1], 40], [LM.inner[0], LM.inner[1], 80], [LM.tunnel[0], LM.tunnel[1] + 10, 80], [LM.lookout[0], LM.lookout[1], 50]];
    for (const k of keepOut) occ.push(k);
    // cedars: the forest west, a line along the ridge, a few sentinels on the east slope
    for (let k = 0; k < 9000 && P.length < 420; k++) {
      const x = R() * WD.W, y = 200 + R() * 1500; const inZ = WD.zones.cedarZone(x, y), ridge = Math.abs(y - (470 + 50 * Math.sin(x * .0042 + .6))) < 140 && R() < .5, east = x > 1650 && y < 1200 && R() < .25;
      if (!(inZ || ridge || east)) continue; if (onRoad(x, y, 22) || wet(x, y, 14) || steep(x, y)) continue; if (!free(x, y, 18)) continue;
      add("cedar" + R.int(0, 5), x, y, { col: 6, kind: "tree", sink: 2 });
    }
    // broadleaf maples along the stream and around the shrine; one deep-red maple by the shrine
    for (let k = 0; k < 2400 && P.filter(p => p.kind === "maple").length < 40; k++) {
      const s = STREAM[R.int(0, 12)], x = s[0] + R.range(-90, 90), y = s[1] + R.range(-60, 60);
      if (onRoad(x, y, 22) || wet(x, y, 16) || steep(x, y) || !free(x, y, 26)) continue; add("maple" + R.int(0, 2), x, y, { col: 5, kind: "maple" });
    }
    add("mapleRed", sx - 108, sy + 34, { col: 6, kind: "maple" }); occ.push([sx - 108, sy + 34, 26]);
    for (const [x, y] of [[sx + 120, sy - 30], [sx - 140, sy - 60], [sx + 96, sy + 74]]) if (free(x, y, 20)) add("maple" + R.int(0, 2), x, y, { col: 5, kind: "maple" });
    // bamboo grove
    for (let k = 0; k < 7000 && P.filter(p => p.kind === "bamboo").length < 260; k++) {
      const x = 120 + R() * 640, y = 1360 + R() * 600; if (!WD.zones.bambooZone(x, y)) continue; if (onRoad(x, y, 16) || !free(x, y, 8)) continue;
      add("bamboo" + R.int(0, 5), x, y, { col: 3, kind: "bamboo" });
    }
    // rocks: clusters along the stream and at cliff feet, scattered on the slopes
    for (let k = 0; k < 4000 && P.filter(p => p.kind === "rock").length < 150; k++) {
      let x, y; if (R() < .55) { const s = STREAM[R.int(0, 13)]; x = s[0] + R.range(-50, 50); y = s[1] + R.range(-50, 50); } else { x = 120 + R() * 2060; y = 300 + R() * 1600; }
      if (onRoad(x, y, 18) || !free(x, y, 10) || hyp((x - LM.zone.cx) / LM.zone.rx, (y - LM.zone.cy) / LM.zone.ry) > 1.05) continue;
      const big = R() < .2; add((big ? "rockL" : "rock") + R.int(0, 3), x, y, { col: big ? 14 : 6, kind: "rock", sink: 2 });
    }
    // undergrowth
    const under = (n, names, test, sp) => { for (let k = 0; k < n * 20 && n > 0; k++) { const x = R() * WD.W, y = 200 + R() * 1800; if (!test(x, y)) continue; if (onRoad(x, y, 12) || wet(x, y, 6) || !free(x, y, sp)) continue; add(R.pick(names), x, y, { kind: "under" }); n--; } };
    under(260, ["fern0", "fern1", "fern2", "sasa0", "sasa1"], (x, y) => WD.zones.cedarZone(x, y) || (WD.zones.bambooZone(x, y) && R() < .4), 5);
    under(70, ["kudzu0", "kudzu1"], (x, y) => { const c = WD.zones.cedarZone(x, y); const near = WD.zones.cedarZone(x + 70, y) !== c || WD.zones.cedarZone(x - 70, y) !== c; return near; }, 20);
    under(120, ["susuki0", "susuki1", "susuki2"], (x, y) => WD.zones.meadow(x, y), 6);
    under(40, ["lily0", "lily1"], (x, y) => !WD.zones.bambooZone(x, y) && this.matAt(x, y) === 1 && hyp((x - LM.zone.cx) / LM.zone.rx, (y - LM.zone.cy) / LM.zone.ry) < .9, 30);
    under(60, ["dayfl0", "dayfl1"], (x, y) => this.matAt(x, y) === 1 && wet(x, y, 30), 8);
    under(30, ["mush0", "mush1"], (x, y) => WD.zones.cedarZone(x, y), 30);
    // hydrangeas beside the shrine and the jizō
    for (const [x, y] of [[sx - 70, sy + 50], [sx + 70, sy + 54], [sx - 30, sy + 78]]) add("hydr" + R.int(0, 1), x, y, { kind: "under" });
    // ---- landmarks on the road
    add("torii", sx, sy + 66, { kind: "torii", col: 0, sway: 0 });
    add("toro", sx - 34, sy + 40, { kind: "toro", col: 6 }); add("toro", sx + 34, sy + 40, { kind: "toro", col: 6 });
    // jizō at every few bends, way-markers (丁石) between
    for (let i = 2; i < ROAD.length - 2; i++) { const [x, y] = ROAD[i]; const side = i % 2 ? 1 : -1; if (i % 3 === 0) { add("jizo", x + side * 20, y - 8, { kind: "jizo", col: 6 }); add("hydr0", x + side * 34, y - 4, { kind: "under" }); } else add("mich", x + side * 18, y - 6, { kind: "mich", col: 4 }); }
    // the inner shrine stair: lanterns either side, a big torii at the top
    for (let i = 0; i < STAIR.length - 1; i++) { const [x, y] = STAIR[i]; add("toro", x - 22, y, { kind: "toro", col: 6 }); add("toro", x + 22, y, { kind: "toro", col: 6 }); }
    add("toriiBig", LM.inner[0], LM.inner[1] + 64, { kind: "torii", sway: 0 });
    // charcoal hut, kiln, woodpile
    add("hut", LM.hut[0], LM.hut[1], { kind: "hut", col: 40, sway: 0 }); add("kiln", LM.kiln[0], LM.kiln[1], { kind: "kiln", col: 26 });
    add("log0", LM.hut[0] + 60, LM.hut[1] + 10, { kind: "log", col: 10 });
    // tunnel portal
    add("tunnel", LM.tunnel[0], LM.tunnel[1], { kind: "tunnel", sway: 0, col: 0 });
    // stepping stones in the shallows below the pool
    for (let k = 0; k < 6; k++) { const t = k / 5, x = lerp(1600, 1640, t) + R.range(-4, 4), y = lerp(1150, 1112, t); add("rock" + R.int(0, 3), x, y, { kind: "rock", z: Math.round(this.heightAt(x, y)) }); }
  },
  buildGrass() {
    const R = RNG(77), G = [];
    for (let k = 0; k < 120000 && G.length < 26000 * 8; k++) {
      const x = R() * WD.W, y = 160 + R() * (WD.H - 160);
      const m = this.matAt(x, y); if (m !== 1) continue; if (this.waterAt(x, y) > -500) continue;
      if (this.nearAt(x, y) < .05) continue;
      const a = this.heightAt(x - 3, y), b = this.heightAt(x + 3, y), c = this.heightAt(x, y - 3), d = this.heightAt(x, y + 3); if (Math.max(Math.abs(a - b), Math.abs(c - d)) > 7) continue;
      const dens = fbm(x * .012, y * .012, 3, 41); if (R() > dens * 1.4 - .2) continue;
      G.push(Math.round(x), Math.round(y), Math.round(this.heightAt(x, y)), R.int(0, 11), R() * 6.28, R(), R(), 0);
    }
    WD.grass = new Float32Array(G);
  },
};

/* ---------------------------------------------------------------------
   ART REGISTRY — generate every scenery sprite once into the atlas.
   --------------------------------------------------------------------- */
const ARTREG = {
  build(progress) {
    ATLAS.init(2048, 2048);
    TZ.init();
    const add = (n, s, m) => ATLAS.add(n, s, m);
    add("camphor", FLORA.camphor(7), { sway: .7, kind: "tree" });
    for (let i = 0; i < 6; i++) add("cedar" + i, FLORA.cedar(i + 1, 128 + (i % 3) * 16, 40 + (i % 2) * 8), { sway: .55, kind: "tree" });
    for (let i = 0; i < 3; i++) add("maple" + i, FLORA.maple(i + 3), { sway: .8, kind: "tree" });
    add("mapleRed", FLORA.maple(9, true), { sway: .8, kind: "tree" });
    for (let i = 0; i < 6; i++) add("bamboo" + i, FLORA.bamboo(i + 1, 170 + (i % 3) * 18), { sway: 1.6, kind: "tree" });
    for (let i = 0; i < 3; i++) add("fern" + i, FLORA.fern(i + 1), { sway: .9, shadow: 0 });
    for (let i = 0; i < 2; i++) add("sasa" + i, FLORA.sasa(i + 1), { sway: .9, shadow: 0 });
    for (let i = 0; i < 2; i++) add("kudzu" + i, FLORA.kudzu(i + 1), { sway: .5, shadow: 0 });
    for (let i = 0; i < 3; i++) add("susuki" + i, FLORA.susuki(i + 1), { sway: 1.8 });
    for (let i = 0; i < 2; i++) add("lily" + i, FLORA.lily(i + 1), { sway: 1 });
    for (let i = 0; i < 2; i++) add("hydr" + i, FLORA.hydrangea(i + 1), { sway: .4, shadow: 0 });
    for (let i = 0; i < 2; i++) add("dayfl" + i, FLORA.dayflower(i + 1), { sway: .6, shadow: 0 });
    for (let i = 0; i < 2; i++) add("mush" + i, FLORA.mushroom(i + 1), { shadow: 0 });
    progress && progress(.45);
    for (let i = 0; i < 4; i++) add("rock" + i, PROPS.rock(i + 1, 16 + i * 4, 11 + i * 3), {});
    for (let i = 0; i < 4; i++) add("rockL" + i, PROPS.rock(i + 11, 34 + i * 6, 22 + i * 4), {});
    for (let s = 0; s <= 4; s++) add("hokora" + s, PROPS.hokora(s), {});
    add("toro", PROPS.ishidoro(1), {}); add("toroLit", PROPS.ishidoro(2, true), {});
    add("jizo", PROPS.jizo(3), {}); add("torii", PROPS.torii(), {}); add("toriiBig", PROPS.torii(76, 84), {});
    add("mich", PROPS.michishirube(1), {});
    for (let i = 0; i < 2; i++) add("log" + i, PROPS.log(i + 1, 44 + i * 8), {});
    add("pole", PROPS.pole(1), {}); add("bark", PROPS.bark(1), {}); add("vine", PROPS.vine(1), {}); add("flatstone", PROPS.flatstone(1), {});
    add("holed", PROPS.holedstone(), {}); add("basket", PROPS.basket(), {}); add("radio", PROPS.radio(), {});
    for (const k of Object.keys(OFFER_ART)) add("off_" + k, PROPS.offering(k), { shadow: 0 });
    add("tunnel", PROPS.tunnel(), {}); add("train", PROPS.train(), {}); add("hut", PROPS.hut(), {}); add("kiln", PROPS.kiln(), {});
    add("steps", PROPS.steps(), {}); add("pebbles", PROPS.pebbles(1), { shadow: 0 });
    progress && progress(.8);
    ATLAS.upload();
  },
};
