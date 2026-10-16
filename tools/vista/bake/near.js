// The near branches of the treetop vista south: the camphor's own boughs right in front of the lens,
// which the camera rises past at the start of the crane (parallax 2.4 at 480x270; Godot's VistaSouth
// slides the layer down out of the frame as the camera comes up out of the crown).
//
// Round 4 (G5R2-4) gave HEAD's loose sprays the stems they grew from, so nothing hung in the air; the
// user then found the result copy-pasted (G5R3-10): every spray was the same caterpillar of four
// round lobes, every stem the same C-sweep into a vertical, every side twig the same pom-pom at the
// same spacing, all in one near-black. Here every bough is its own design, the way a painter lays out
// the branches of one tree in front of the lens:
//   * a heavy bough close to the lens at the right, its big mass of leaves almost black but for the
//     sky's edge; a long limb sweeping in from the lower left with two open masses; a slender shoot
//     with small clusters up its length; a Y-fork whose arms are unequal; an arch at the left whose
//     leaves hang; a dead snag; a flat spray lying open to the sky; one clear rosette; a thin whip with
//     four leaves at its tip; a mass of small leaves further back (and more boughs beyond the
//     reference frame, for wide views);
//   * the masses are the crown's own clumps seen ~2.4 times closer: rounded and lumpy like the clumps
//     behind, but made of leaves one can count, camphor leaves (ovate, pointed, glossy), each with its
//     own length, angle, droop and tilt; a leaf's two halves take the light differently; the masses
//     are lit from the sky above like the clumps behind (lit crowns, shaded undersides, a dark heart);
//   * every mass has its own shape (lobes, size, how it hangs), leaf size, density and tone, so the
//     masses differ in value as well as in shape and place.
// Every limb rises from below the layer and every leaf belongs to a mass or a sprig on a limb: the
// whole layer is one piece with the layer's bottom row (checked here and by
// godot/tests/test_vista.gd), so no branch ever ends in mid-air in the frame (G5R2-4). The layer keeps
// clear of the place where she sits (`keep`): the near leaves never cover her during the crane.
// Deterministic: its own seeded generators only (no draws from the bake's sequences).

import { clamp, lerp, rng, vnoise, IndexLayer, I, iMat } from '../../../src/vista/util.js';
import { F } from '../../../src/vista/foliage.js';

const REF_W = 480;
// the sky's light on the masses: from above, a little from the west (right) and toward the lens
const LIGHT = norm3([0.35, -0.85, 0.4]);

// ------------------------------------------------------------------------------------------------
// The designs. x: px of the 480-wide reference frame (outside 0..480 only on wide views); y: rows of
// the layer (0 at its top; the layer is 460 rows; at 1920x1080 rows 0..253 show at the start of the
// crane, at 1280x720 rows 0..207, the rest only on tall views). A limb is a path of control points
// from its root (below the layer) to its tip; `from` [limb, t] grows it out of an earlier limb of the
// same bough at that fraction of its length.
//   z      nearness (higher is nearer the lens; drawn over lower)
//   tone   0 = black against the crown .. 1 = full sky on the leaves
//   leaf   leaf length range (px)
//   rim    strength of the sky's edge on the tops of leaves and bark (0 none .. 3)
//   gloss  share of the leaves that catch the sky in a glint
// A mass sits at the end of a limb (or at `t` along it), its centre `off` from there; `size` [w, h]
// px; `lobes` how many rounded parts; `hang` how its lobes sag below the limb (0 .. 1); `droop` how
// the leaves hang; `dense` leaf spacing as a share of the leaf length (lower is denser); per-mass
// tone / leaf override the bough's. `sprigs`: short twigs off the limb with a few leaves at their
// ends, [count, from t, to t]. `rosette`: a single rosette of n leaves at the tip instead of a mass.
const DESIGNS = [
  // The tree's trunk is off to the right (her limb comes out of it), so its boughs reach in from the
  // lower right. The nearest, almost black, sweeps up and across toward the left under her, its leaves
  // in a spray along its end; out of it rise a big spray climbing at the right, a crooked branch with a
  // spray of small leaves further back, a twig with one clear rosette and a dead snag; a clump hangs
  // under it.
  { name: 'great bough', z: 8, tone: 0.07, leaf: [11, 14], rim: 1, gloss: 0.02, seed: 11,
    limbs: [
      { pts: [[480, 472], [462, 400], [442, 332], [414, 278], [380, 238], [338, 208], [290, 192], [246, 186], [212, 190]], r: [15, 3],
        masses: [{ along: [0.8, 1], size: [0, 30], lobes: 4, hang: 0.15, droop: 0.35, dense: 0.56, tone: 0.24, leaf: [8, 10], z: 7 },
          { t: 0.7, off: [4, 22], size: [42, 32], lobes: 3, hang: 0.85, droop: 0.75, dense: 0.5, tone: 0.11 }] },
      { from: [0, 0.48], pts: [[420, 246], [430, 206], [444, 170], [462, 140], [484, 118]], r: [8, 2.6],
        masses: [{ along: [0.4, 1], size: [0, 44], lobes: 5, hang: 0.1, droop: 0.4, dense: 0.5 }] },
      { from: [0, 0.92], pts: [[220, 170], [206, 158], [194, 148], [184, 142]], r: [3, 1.4],
        masses: [{ along: [0.3, 1], size: [0, 24], lobes: 3, hang: 0.1, droop: 0.3, dense: 0.62, tone: 0.2, leaf: [6, 8], z: 4 }] },
      { from: [0, 0.78], pts: [[302, 178], [306, 168]], r: [2.2, 1.3], rosette: 5, tone: 0.4, gloss: 0.15, leaf: [10, 12] },
      { from: [0, 0.64], pts: [[364, 214], [356, 196], [358, 186]], r: [2.4, 0.9], bare: true },
      { from: [4, 0.55], pts: [[352, 190], [346, 186]], r: [1.1, 0.7], bare: true },
    ] },
  // the left: a lower bough rises up the side and curls back over, a lighter spray along its top, its
  // tip hanging; a short arm reaches in toward the middle with a clump that hangs
  { name: 'left bough', z: 6, tone: 0.32, leaf: [8, 10], rim: 2, gloss: 0.12, seed: 23,
    limbs: [
      { pts: [[22, 472], [36, 400], [58, 330], [82, 272], [98, 230], [102, 196], [94, 168], [78, 150], [62, 146]], r: [10, 2.2],
        masses: [{ along: [0.66, 1], size: [0, 34], lobes: 5, hang: 0.1, droop: 0.3, dense: 0.56, tone: 0.36 }] },
      { from: [0, 0.8], pts: [[118, 214], [136, 222], [146, 232]], r: [3.4, 1.4],
        masses: [{ off: [2, 14], size: [32, 36], lobes: 3, hang: 0.9, droop: 0.8, dense: 0.55, tone: 0.2 }] },
      { from: [0, 0.97], pts: [[50, 152], [36, 166], [30, 182]], r: [2.4, 1.2],
        masses: [{ off: [0, 14], size: [24, 34], lobes: 2, hang: 1, droop: 0.95, dense: 0.58, tone: 0.16, leaf: [10, 12], z: 7 }] },
    ] },
  // a slender shoot from further down, between them, with a few small clusters up its top
  { name: 'slender shoot', z: 4, tone: 0.46, leaf: [7, 8], rim: 2, gloss: 0.15, seed: 37,
    limbs: [
      { pts: [[160, 472], [158, 400], [164, 330], [158, 276], [166, 236], [162, 212]], r: [4, 1.3],
        masses: [{ along: [0.8, 1], size: [0, 16], lobes: 3, hang: 0, droop: 0.1, dense: 0.6, young: 0.3 }], sprigs: [3, 0.7, 0.9] },
    ] },
  // beyond the reference frame (wide views): at the right another bough from the trunk's side with a
  // spray climbing and an arm arching out with hanging leaves; at the left a bough that splits three ways
  { name: 'right bough', z: 7, tone: 0.18, leaf: [9, 11], rim: 1, gloss: 0.05, seed: 101, ext: true,
    limbs: [
      { pts: [[700, 472], [682, 400], [660, 340], [628, 296], [596, 268]], r: [13, 6] },
      { from: [0, 1], pts: [[580, 240], [584, 200], [596, 166], [612, 140], [626, 124]], r: [6, 2.2],
        masses: [{ along: [0.35, 1], size: [0, 46], lobes: 5, hang: 0.15, droop: 0.4, dense: 0.5 }] },
      { from: [0, 0.8], pts: [[632, 280], [652, 250], [664, 214], [680, 196], [700, 200], [712, 216]], r: [5, 1.4],
        masses: [{ t: 0.82, off: [0, 18], size: [30, 40], lobes: 2, hang: 1, droop: 0.9, dense: 0.58, tone: 0.26 },
          { off: [0, 16], size: [24, 34], lobes: 2, hang: 1, droop: 0.9, dense: 0.6, tone: 0.22 }], sprigs: [2, 0.6, 0.8] },
    ] },
  { name: 'far left bough', z: 7, tone: 0.12, leaf: [10, 12], rim: 1, gloss: 0.03, seed: 83, ext: true,
    limbs: [
      { pts: [[-110, 472], [-118, 410], [-128, 356], [-140, 318]], r: [12, 8] },
      { from: [0, 1], pts: [[-150, 286], [-158, 236], [-168, 196], [-176, 160], [-180, 140]], r: [7, 2.4],
        masses: [{ along: [0.45, 1], size: [0, 50], lobes: 4, hang: 0.15, droop: 0.4, dense: 0.5 }] },
      { from: [1, 0.6], pts: [[-184, 196], [-210, 182], [-234, 184]], r: [3.6, 1.4],
        masses: [{ along: [0.3, 1], size: [0, 30], lobes: 3, hang: 0.3, droop: 0.5, dense: 0.54, tone: 0.18 }] },
      { from: [0, 0.85], pts: [[-118, 300], [-104, 262], [-94, 232], [-86, 214]], r: [5, 1.6],
        masses: [{ off: [6, -6], size: [46, 20], lobes: 4, hang: 0, droop: 0.05, dense: 0.62, flat: true, tone: 0.4, gloss: 0.12, leaf: [7, 9], z: 5 }] },
      { from: [0, 0.6], pts: [[-150, 330], [-204, 300], [-228, 262], [-238, 222], [-242, 190], [-238, 164]], r: [5, 1.4],
        masses: [{ along: [0.85, 1], size: [0, 22], lobes: 3, hang: 0, droop: 0.1, dense: 0.6, tone: 0.46, leaf: [7, 8], z: 4 }],
        sprigs: [3, 0.66, 0.88] },
    ] },
];

// ------------------------------------------------------------------------------------------------

/**
 * Paint the near branches. Wc: canvas width; ox: the reference frame's left edge in it; hL: the layer's
 * rows; ext: also the boughs beyond the reference frame; keep: {x0, x1, y1} a box (canvas px) kept
 * clear (where she sits, over the whole crane). Returns an IndexLayer; .dropped is the number of
 * pixels the final connectivity pass removed (a handful of stray leaf tips at most).
 */
export function* nearCrown(Wc, ox, hL, ext, keep) {
  const P = new Painter(Wc, hL, keep);
  const designs = DESIGNS.filter(d => ext || !d.ext);
  let id = 0;
  for (const d of designs) {
    const R = rng(d.seed * 7919 + 13);
    const placed = [];
    for (const lb of d.limbs) {
      const o = { ...d, ...lb, tone: lb.tone ?? d.tone, gloss: lb.gloss ?? d.gloss, leaf: lb.leaf ?? d.leaf };
      let ctrl = lb.pts.map(([x, y]) => [x + ox, y]);
      if (lb.from) ctrl = [placed[lb.from[0]].at(lb.from[1]), ...ctrl];
      const path = new Path(ctrl, lb.r, R);
      placed.push(path);
      P.limb(path, o, id, R);
      if (lb.sprigs) sprigs(P, path, o, id, R, lb.sprigs);
      if (lb.rosette) rosette(P, path, o, id, R, lb.rosette);
      for (const m of lb.masses || []) mass(P, path, { ...o, ...m, tone: m.tone ?? o.tone, leaf: m.leaf ?? o.leaf, gloss: m.gloss ?? o.gloss }, id, R);
      id++;
    }
    yield;
  }
  P.finish();
  P.L.dropped = P.dropped;
  P.L.spec = { designs: designs.map(d => d.name), dropped: P.dropped };
  return P.L;
}

// A limb's centre line: Catmull-Rom through the control points, a little crooked (a branch is a run
// of slightly bent pieces), sampled about every 1.5 px; radius tapering from root to tip.
class Path {
  constructor(ctrl, r, R) {
    const pts = ctrl.map((p, i) => (i === 0 || i === ctrl.length - 1) ? p : [p[0] + (R() - 0.5) * 3, p[1] + (R() - 0.5) * 3]);
    const out = [], n = pts.length;
    for (let i = 0; i < n - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(n - 1, i + 2)];
      const steps = Math.max(2, Math.ceil(Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / 1.5));
      for (let s = 0; s < steps; s++) {
        const t = s / steps, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(k => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    out.push(pts[n - 1].slice());
    const acc = [0];
    for (let i = 1; i < out.length; i++) acc.push(acc[i - 1] + Math.hypot(out[i][0] - out[i - 1][0], out[i][1] - out[i - 1][1]));
    this.p = out; this.acc = acc; this.len = acc[acc.length - 1];
    this.r0 = r[0]; this.r1 = r[1];
  }
  at(t) {
    const s = clamp(t, 0, 1) * this.len, a = this.acc;
    let i = 1; while (i < a.length - 1 && a[i] < s) i++;
    const f = (s - a[i - 1]) / Math.max(1e-6, a[i] - a[i - 1]);
    return [lerp(this.p[i - 1][0], this.p[i][0], f), lerp(this.p[i - 1][1], this.p[i][1], f)];
  }
  dir(t) {
    const a = this.at(Math.max(0, t - 0.01)), b = this.at(Math.min(1, t + 0.01)), l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    return [(b[0] - a[0]) / l, (b[1] - a[1]) / l];
  }
  radius(t) { return lerp(this.r0, this.r1, Math.pow(clamp(t, 0, 1), 0.8)); }
}

class Painter {
  constructor(w, h, keep) {
    this.w = w; this.h = h; this.keep = keep;
    this.L = new IndexLayer(w, h);
    this.Z = new Float32Array(w * h).fill(-1e9);
    this.face = new Float32Array(w * h);         // how much a leaf pixel faces the sky (0..1); -1 bark
    this.rimOf = new Uint8Array(w * h);           // the rim strength of the bough that painted it
    this.dropped = 0;
  }
  put(x, y, z, v, face, rim) {
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const k = this.keep;
    if (k && x >= k.x0 && x <= k.x1 && y <= k.y1) return;
    const i = y * this.w + x;
    if (z < this.Z[i]) return;
    this.Z[i] = z; this.L.idx[i] = v; this.face[i] = face; this.rimOf[i] = rim;
  }
  // bark: a cylinder lit from the sky above, fissures along it; the darkest boughs show only the sky's
  // edge on their top
  limb(path, o, owner, R) {
    const seed = Math.floor(R() * 1000), pts = path.p, acc = path.acc;
    for (let s = 0; s < pts.length - 1; s++) {
      const [ax, ay] = pts[s], [bx, by] = pts[s + 1];
      const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1, tx = dx / len, ty = dy / len;
      // across the limb toward the sky's light (up and a little right): that side is lit
      let ux = -ty, uy = tx; if (ux * LIGHT[0] + uy * LIGHT[1] < 0) { ux = -ux; uy = -uy; }
      const rmax = Math.max(path.radius(acc[s] / path.len), path.radius(acc[s + 1] / path.len)) * 1.2 + 1;
      for (let y = Math.floor(Math.min(ay, by) - rmax); y <= Math.ceil(Math.max(ay, by) + rmax); y++) {
        for (let x = Math.floor(Math.min(ax, bx) - rmax); x <= Math.ceil(Math.max(ax, bx) + rmax); x++) {
          const px = x + 0.5 - ax, py = y + 0.5 - ay;
          const tt = clamp((px * tx + py * ty) / len, 0, 1);
          const a = acc[s] + tt * len;
          const r = path.radius(a / path.len) * (1 + 0.12 * Math.sin(a * 0.19 + seed) + 0.08 * Math.sin(a * 0.47 + seed * 2));
          const cx = px - tx * tt * len, cy = py - ty * tt * len;
          if (Math.hypot(cx, cy) > Math.max(0.55, r)) continue;
          const c = r < 0.9 ? 0.3 : clamp((cx * ux + cy * uy) / r, -1, 1);   // +1 lit side .. -1 shaded
          this.put(x, y, o.z + 0.1 * Math.sqrt(Math.max(0, 1 - c * c)), bark(c, a, o, seed, r), -1, o.rim);
        }
      }
    }
  }
  // a thin stalk from (x, y) along a, slightly bent; returns its end
  stalk(x, y, a, len, bend, o) {
    const steps = Math.max(1, Math.round(len / 0.6));
    for (let i = 0; i < steps; i++) {
      a += bend / steps;
      x += Math.cos(a) * 0.6; y += Math.sin(a) * 0.6;
      this.put(x, y, o.z + 0.15, I(F.twig, o.tone > 0.3 ? 2 : 1, 2, 0), -1, 0);
    }
    return [x, y, a];
  }
  // the last pass: contact shade under nearer boughs, the sky's edge on the tops, then the layer is
  // made one piece with its bottom row (anything not hanging from it is removed and counted)
  finish() {
    const { w, h } = this, idx = this.L.idx, src = idx.slice();
    for (let y = 2; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x, v = src[i];
      if (!v) continue;
      const m = iMat(v), rim = this.rimOf[i];
      const j = (y - 2) * w + (x - 1);
      if (src[j] && this.Z[j] > this.Z[i] + 1.5 && m !== F.dark) { idx[i] = I(F.deep, 0, 0, 0); continue; }
      if (!rim || src[i - w]) continue;
      const f = this.face[i];
      if (f < 0) { if (m !== F.twig) idx[i] = I(F.rim, rim - 1, 3, 0); }
      else if (f > 0.45) idx[i] = I(F.rim, Math.min(7, rim + Math.round(f * 2) - 1), 3, 0);
    }
    this.L.despeckle(v => { const m = iMat(v); return m === F.leaf || m === F.deep || m === F.young; });
    this.dropped = keepConnected(idx, w, h);
    this.L.used = null;
  }
}

function bark(c, a, o, seed, r) {
  if (r < 0.9) return I(F.twig, 1, 1, 0);
  // inside the crown the boughs are in its shade: darker than their leaves; the top takes the sky
  const fur = Math.abs(Math.sin((c * 1.9 + (vnoise(a * 0.08, seed, seed + 3) - 0.5) * 2.4) * Math.PI));
  const plate = vnoise(a * 0.22, c * 2 + seed, seed + 4);
  if (c > 0.62) return I(F.bark, o.tone < 0.15 ? 1 : 2, 3, 0);
  if (c < -0.35 || (fur < 0.22 && plate > 0.4)) return I(F.dark, 0, 0, 0);
  if (o.tone < 0.15) return I(F.dark, 0, 1, 0);
  return I(F.bark, c > 0.15 ? 1 : 0, c > 0.15 ? 2 : 1, 0);
}

// ------------------------------------------------------------------------------------------------
// A mass of leaves: a few rounded lobes round the end of a limb, built of the clusters camphor's
// leaves grow in (each a little rosette of 3-6 leaves at a twig's end, held out and a little down),
// packed over the lobes back to front: the outline is the tips of the outermost clusters, uneven as a
// real clump's; inside, the clusters overlap with the dark of the clump's heart in the gaps. Each leaf
// takes the light of the lobe's surface where it sits (sky above, the clump's own shade under it), as
// the crown's clumps behind do, seen ~2.4 times closer.

function mass(P, path, o, owner, R) {
  const t = o.t ?? 1, [ax, ay] = path.at(t);
  const off = o.off ?? [0, 0], cx = ax + off[0], cy = ay + off[1], [W, H] = o.size;
  const flatK = o.flat ? 1.7 : 1;
  const n = o.lobes, lobes = [];
  if (o.along) {
    // a spray: lobes strung along the limb's outer part, mostly on its sky side, uneven in size and
    // spacing (the twigs that carry them are hidden in the leaves)
    const [t0, t1] = o.along;
    for (let i = 0; i < n; i++) {
      const tt = lerp(t0, t1, (i + 0.25 + R() * 0.5) / n), [px, py] = path.at(tt), [tx, ty] = path.dir(tt);
      let ux = -ty, uy = tx; if (uy > 0) { ux = -ux; uy = -uy; }
      const r = H * 0.5 * (0.6 + R() * 0.5) * (0.75 + 0.35 * (i / Math.max(1, n - 1)));
      const k = (R() * 0.55 - 0.1) * r;
      lobes.push([px + ux * k, py + uy * k + (o.hang ?? 0) * r * 0.5, r]);
    }
  } else {
    // a clump: the first lobe holds the limb's end; the others round the centre, sagging by `hang`
    lobes.push([ax, ay, Math.max(4, Math.min(W, H) * 0.26)]);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * 2 * Math.PI + R() * 1.2;
      const d = n === 1 ? 0 : 0.24 + R() * 0.22;
      const r = Math.min(W, H) * (0.26 + R() * 0.2) * (n === 1 ? 1.5 : 1);
      lobes.push([cx + Math.cos(a) * W * d, cy + Math.sin(a) * H * d / flatK + (o.hang ?? 0) * H * 0.12, r]);
    }
  }
  const surf = (x, y) => {
    let best = -1e9, li = 0;
    for (let i = 0; i < lobes.length; i++) {
      const [lx, ly, lr] = lobes[i], q = 1 - Math.hypot(x - lx, (y - ly) * flatK) / lr;
      if (q > best) { best = q; li = i; }
    }
    const [lx, ly, lr] = lobes[li];
    const nx = (x - lx) / lr, ny = (y - ly) * flatK / lr, nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny));
    return [best, nx, ny, nz];
  };
  const L1 = (o.leaf[0] + o.leaf[1]) / 2;
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const [lx, ly, lr] of lobes) { x0 = Math.min(x0, lx - lr); x1 = Math.max(x1, lx + lr); y0 = Math.min(y0, ly - lr / flatK); y1 = Math.max(y1, ly + lr / flatK); }
  // the heart: dark, behind every leaf, a little inside the outline
  const inset = Math.min(0.45, L1 * 0.55 / Math.max(6, Math.min(W, H) * 0.5));
  for (let y = Math.floor(y0); y <= Math.ceil(y1); y++) for (let x = Math.floor(x0); x <= Math.ceil(x1); x++) {
    const [q, , ny] = surf(x + 0.5, y + 0.5);
    if (q > inset + (o.along ? 0.18 : 0)) P.put(x, y, o.z - 1, I(ny > 0.3 && !o.along ? F.dark : F.deep, 0, 0, 0), 0, 0);
  }
  // the clusters, on a jittered grid over the lobes (spacing `dense` x leaf length), back to front
  const sp = L1 * (o.dense ?? 0.6) * 1.12;
  const list = [];
  for (let y = y0 + sp * 0.3; y <= y1; y += sp * 0.85) for (let x = x0 + sp * 0.3; x <= x1; x += sp) {
    const px = x + (R() - 0.5) * sp * 0.9, py = y + (R() - 0.5) * sp * 0.8;
    const [q, nx, ny, nz] = surf(px, py);
    if (q < 0.04) continue;
    list.push([px, py, nx, ny, nz, R()]);
  }
  list.sort((a, b) => a[4] - b[4]);
  for (const [px, py, nx, ny, nz, rr] of list) {
    const lam = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2];
    const dTone = (lam - 0.3) * 0.5 - Math.max(0, ny) * 0.16 + (rr - 0.5) * 0.14;
    // the cluster is held out from the clump and a little down; facing the lens, any way
    const out = Math.atan2(ny + 1e-4, nx);
    const a0 = nz > 0.88 ? R() * 2 * Math.PI : turnTo(out + (R() - 0.5) * 0.7, Math.PI / 2, clamp(0.15 + 0.5 * (o.droop ?? 0.3), 0, 0.8) * Math.max(0, 0.4 + 0.6 * ny));
    // a camphor cluster: a few broad leaves fanned out loosely (not a palmate star)
    const k = 3 + Math.floor(R() * 3);
    const spread = rad(80 + R() * 70);
    for (let i = 0; i < k; i++) {
      const f = i / (k - 1) - 0.5;
      const a = a0 + f * spread + (R() - 0.5) * 0.35;
      // leaves pointing toward the lens are foreshortened (shorter); the side ones are longest
      const len = lerp(o.leaf[0], o.leaf[1], R()) * (0.62 + 0.38 * (1 - nz * 0.7)) * (1 - 0.25 * Math.abs(f));
      // most leaves are in front of the twig that carries them, some behind it
      leaf(P, px, py, a, len, o, R, dTone, o.z + nz * 0.8 + (R() < 0.72 ? 0.2 : -0.3) + R() * 0.02, false);
    }
  }
}

function bodyShade(v) {
  if (v < 0.12) return I(F.dark, 0, 0, 0);
  if (v < 0.26) return I(F.deep, 1, 1, 0);
  if (v < 0.42) return I(F.leaf, 1, 1, 0);
  if (v < 0.58) return I(F.leaf, 2, 2, 0);
  if (v < 0.74) return I(F.leaf, 4, 2, 0);
  return I(F.leaf, 5, 3, 0);
}

// Short twigs off a limb, each with a few leaves at its end: [count, from t, to t].
function sprigs(P, path, o, owner, R, [k, t0, t1]) {
  for (let i = 0; i < k; i++) {
    const t = lerp(t0, t1, (i + 0.3 + R() * 0.4) / k), [x, y] = path.at(t), [tx, ty] = path.dir(t);
    const side = i % 2 ? 1 : -1;
    const a = liftUp(Math.atan2(ty, tx) + side * rad(40 + R() * 30), rad(30));
    const [ex, ey, ea] = P.stalk(x, y, a, 6 + R() * 9, (R() - 0.5) * 0.6, o);
    const nl = 2 + Math.floor(R() * 3);
    for (let j = 0; j < nl; j++) leaf(P, ex, ey, ea + (j - (nl - 1) / 2) * rad(50) + (R() - 0.5) * 0.3, lerp(o.leaf[0], o.leaf[1], R()) * 0.9, o, R, 0.05, o.z + 0.5, true);
  }
}

// A single rosette of n leaves at the tip (camphor's leaves crowd at the ends of its shoots).
function rosette(P, path, o, owner, R, n) {
  const [x, y] = path.at(1), [tx, ty] = path.dir(0.99), a0 = Math.atan2(ty, tx);
  for (let i = 0; i < n; i++) {
    const a = n >= 6 ? a0 + (i / n) * 2 * Math.PI + (R() - 0.5) * 0.3 : a0 + (i / (n - 1) - 0.5) * rad(150) + (R() - 0.5) * 0.3;
    leaf(P, x, y, a, lerp(o.leaf[0], o.leaf[1], R()), o, R, -Math.sin(a) * 0.1, o.z + 0.5 + R() * 0.2, true);
  }
}

// turn angle a toward angle b by a share k of the way (the short way round)
function turnTo(a, b, k) {
  let d = b - a;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return a + d * k;
}

// turn an angle toward straight up (-pi/2) by at most k radians (k < 0: toward straight down)
function liftUp(a, k) {
  const target = k >= 0 ? -Math.PI / 2 : Math.PI / 2;
  let d = target - a;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return a + clamp(d, -Math.abs(k), Math.abs(k));
}

// One camphor leaf: ovate (widest a little below the middle), pointed, about half as wide as long,
// on a short stalk. Its midrib bends down by the droop; its tilt says how much of its upper face the
// sky sees (a leaf seen edge-on is narrower and darker). The half toward the sky is the lighter one.
function leaf(P, x, y, ang, len, o, R, dTone, z, stalk) {
  const tilt = clamp(R() * 1.2 - 0.2 + (o.flat ? 0.4 : 0), 0, 1);
  const width = len * (0.58 + 0.1 * R()) * (0.72 + 0.28 * tilt);
  const droop = (o.droop ?? 0.3) * (0.5 + 0.9 * R());
  let sx = x, sy = y;
  if (stalk) {
    const sl = 1 + R() * 1.5;
    P.put(x, y, z, I(F.twig, 1, 2, 0), -1, 0);
    sx = x + Math.cos(ang) * sl; sy = y + Math.sin(ang) * sl;
    P.put((x + sx) / 2, (y + sy) / 2, z, I(F.twig, 1, 2, 0), -1, 0);
  }
  const dx = Math.cos(ang), dy = Math.sin(ang);
  const ex = sx + dx * len, ey = sy + dy * len + droop * len * 0.5;
  const mx = sx + dx * len * 0.5, my = sy + dy * len * 0.5 + droop * len * 0.1;
  const tone = clamp(o.tone + dTone + (tilt - 0.5) * 0.22 + (R() - 0.5) * 0.12, 0, 1);
  const glint = R() < (o.gloss ?? 0) * 0.45 * (0.4 + tilt);
  const gloss = glint ? 0.55 : 0;
  const young = R() < (o.young ?? 0);
  const steps = Math.ceil(len * 3);
  for (let i = 0; i <= steps; i++) {
    const u = i / steps, w1 = 1 - u;
    const cx = w1 * w1 * sx + 2 * w1 * u * mx + u * u * ex, cy = w1 * w1 * sy + 2 * w1 * u * my + u * u * ey;
    const gx = 2 * w1 * (mx - sx) + 2 * u * (ex - mx), gy = 2 * w1 * (my - sy) + 2 * u * (ey - my), gl = Math.hypot(gx, gy) || 1;
    let nx = -gy / gl, ny = gx / gl; if (ny > 0) { nx = -nx; ny = -ny; }   // the half toward the sky
    // ovate: widest a little below the middle, a short point
    const hw = width * 0.5 * Math.pow(Math.sin(Math.PI * Math.pow(u, 0.78)), 0.5);
    const vs = Math.max(0.5, hw);
    for (let v = -vs; v <= vs + 1e-6; v += 0.5) {
      if (Math.abs(v) > hw + 0.25 && i !== 0) continue;
      const upper = v > 0.25, mid = Math.abs(v) <= 0.25 && u > 0.12 && u < 0.85;
      let b = tone * 6 + (upper ? 0.5 : -0.3);
      if (mid && len >= 9 && tone > 0.28) b -= 1.1;                       // the midrib, a fold of shade
      if (u > 0.85) b -= 0.4;
      const v16 = leafShade(b + (upper && u > 0.2 && u < 0.75 ? gloss : 0), young);
      P.put(cx + nx * v, cy + ny * v, z + (upper ? 0.01 : 0), v16, clamp(tilt * (upper ? 1 : 0.6), 0, 1), o.rim);
    }
  }
}

function leafShade(b, young) {
  const m = young ? F.young : F.leaf;
  if (b < 0.7) return I(F.dark, 0, 0, 0);
  if (b < 1.6) return I(F.deep, 1, 1, 0);
  if (b < 2.5) return I(m, 1, 1, 0);
  if (b < 3.4) return I(m, 2, 2, 0);
  if (b < 4.3) return I(m, 3, 2, 0);
  if (b < 5.2) return I(m, 5, 3, 0);
  return I(F.glint, 6, 3, 0);
}

const rad = d => d * Math.PI / 180;
function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]); return [v[0] / l, v[1] / l, v[2] / l]; }

// Keeps only what hangs (8-connected) from the layer's bottom row; returns how many pixels it cleared.
function keepConnected(idx, w, h) {
  const seen = new Uint8Array(w * h), stack = [];
  for (let x = 0; x < w; x++) { const i = (h - 1) * w + x; if (idx[i]) { seen[i] = 1; stack.push(i); } }
  while (stack.length) {
    const i = stack.pop(), x = i % w, y = (i - x) / w;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const xx = x + dx, yy = y + dy;
      if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
      const j = yy * w + xx;
      if (idx[j] && !seen[j]) { seen[j] = 1; stack.push(j); }
    }
  }
  let n = 0;
  for (let i = 0; i < w * h; i++) if (idx[i] && !seen[i]) { idx[i] = 0; n++; }
  return n;
}

export { DESIGNS, REF_W, Path };
