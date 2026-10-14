// Grid navigation for the crew: A* over a walkability grid, then string-pulled so routes are
// straight where the ground allows (followers should look like they know the way, not zig-zag).
// The grid is built once from a ground query; `blocked(x, z)` adds dynamic obstacles (a closed
// gate, a broken bridge) at search time. Pure logic on (x, z).

const SQRT2 = Math.SQRT2;
const NEIGHBOURS = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, SQRT2], [1, -1, SQRT2], [-1, 1, SQRT2], [-1, -1, SQRT2]];

export class NavGrid {
  /**
   * x0, z0: world corner; w, h: cells; cell: metres per cell.
   * ground(x, z) → height in metres, or null where nothing can stand (water, walls).
   * maxStep: the largest height change between neighbouring cells that can be walked.
   */
  constructor({ x0, z0, w, h, cell = 1, ground, maxStep = 0.6 }) {
    Object.assign(this, { x0, z0, w, h, cell, maxStep });
    this.height = new Float32Array(w * h);
    this.open = new Uint8Array(w * h);
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const y = ground(x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell);
        this.open[j * w + i] = y === null || y === undefined ? 0 : 1;
        this.height[j * w + i] = y ?? 0;
      }
    }
    this.blocked = null; // optional (x, z) => bool for dynamic obstacles
  }

  cellOf(x, z) {
    const i = Math.floor((x - this.x0) / this.cell), j = Math.floor((z - this.z0) / this.cell);
    return i < 0 || j < 0 || i >= this.w || j >= this.h ? -1 : j * this.w + i;
  }

  centre(c) {
    const i = c % this.w, j = (c - i) / this.w;
    return { x: this.x0 + (i + 0.5) * this.cell, z: this.z0 + (j + 0.5) * this.cell };
  }

  passable(c) {
    if (c < 0 || !this.open[c]) return false;
    if (!this.blocked) return true;
    const p = this.centre(c);
    return !this.blocked(p.x, p.z);
  }

  /** Can a walker go directly from cell a to its neighbour b? */
  link(a, b) { return this.passable(b) && Math.abs(this.height[a] - this.height[b]) <= this.maxStep; }

  /** Nearest passable cell to (x, z) within a few cells (targets often sit on a prop's footprint). */
  nearestOpen(x, z, radius = 4) {
    const c = this.cellOf(x, z);
    if (c >= 0 && this.passable(c)) return c;
    let best = -1, bestD = Infinity;
    const ci = Math.floor((x - this.x0) / this.cell), cj = Math.floor((z - this.z0) / this.cell);
    for (let dj = -radius; dj <= radius; dj++) {
      for (let di = -radius; di <= radius; di++) {
        const i = ci + di, j = cj + dj;
        if (i < 0 || j < 0 || i >= this.w || j >= this.h) continue;
        const k = j * this.w + i, d = di * di + dj * dj;
        if (d < bestD && this.passable(k)) { best = k; bestD = d; }
      }
    }
    return best;
  }

  /**
   * Route from (x0, z0) to (x1, z1): a list of waypoints ending at the goal, or null when the
   * goal cannot be reached. Searches at most `limit` cells.
   */
  route(x0, z0, x1, z1, limit = 6000) {
    const start = this.nearestOpen(x0, z0), goal = this.nearestOpen(x1, z1);
    if (start < 0 || goal < 0) return null;
    if (start === goal) return [{ x: x1, z: z1 }];
    const W = this.w, g = new Map([[start, 0]]), came = new Map(), closed = new Set();
    const gp = this.centre(goal);
    const hDist = c => { const p = this.centre(c), dx = Math.abs(p.x - gp.x), dz = Math.abs(p.z - gp.z); return (dx + dz + (SQRT2 - 2) * Math.min(dx, dz)) / this.cell; };
    const heap = new MinHeap();
    heap.push(start, hDist(start));
    let found = false;
    while (heap.size && closed.size < limit) {
      const c = heap.pop();
      if (c === goal) { found = true; break; }
      if (closed.has(c)) continue;
      closed.add(c);
      const i = c % W;
      for (const [di, dj, cost] of NEIGHBOURS) {
        const ni = i + di;
        if (ni < 0 || ni >= W) continue;
        const n = c + dj * W + di;
        if (n < 0 || n >= this.open.length || closed.has(n) || !this.link(c, n)) continue;
        // no corner cutting: a diagonal needs both orthogonal cells open
        if (di && dj && (!this.link(c, c + di) || !this.link(c, c + dj * W))) continue;
        const ng = g.get(c) + cost;
        if (ng < (g.get(n) ?? Infinity)) { g.set(n, ng); came.set(n, c); heap.push(n, ng + hDist(n)); }
      }
    }
    if (!found) return null;
    const cells = [goal];
    while (cells[0] !== start) cells.unshift(came.get(cells[0]));
    return this.smooth(cells, x0, z0, x1, z1);
  }

  /** String-pull: keep only the cells where a straight walk would leave walkable ground. */
  smooth(cells, x0, z0, x1, z1) {
    const pts = cells.map(c => this.centre(c));
    pts[0] = { x: x0, z: z0 };
    pts[pts.length - 1] = { x: x1, z: z1 };
    const out = [];
    let anchor = 0;
    while (anchor < pts.length - 1) {
      let far = anchor + 1;
      for (let k = pts.length - 1; k > anchor + 1; k--) if (this.clear(pts[anchor], pts[k])) { far = k; break; }
      out.push(pts[far]);
      anchor = far;
    }
    return out;
  }

  /** Is the straight segment a→b walkable (sampled every half cell)? */
  clear(a, b) {
    const d = Math.hypot(b.x - a.x, b.z - a.z), n = Math.max(1, Math.ceil(d / (this.cell * 0.5)));
    let prev = this.cellOf(a.x, a.z);
    for (let s = 1; s <= n; s++) {
      const c = this.cellOf(a.x + (b.x - a.x) * s / n, a.z + (b.z - a.z) * s / n);
      if (c === prev) continue;
      if (prev >= 0 && !this.link(prev, c)) return false;
      if (prev < 0 && !this.passable(c)) return false;
      prev = c;
    }
    return true;
  }
}

class MinHeap {
  constructor() { this.k = []; this.p = []; }
  get size() { return this.k.length; }
  push(key, pri) {
    const k = this.k, p = this.p;
    let i = k.length;
    k.push(key); p.push(pri);
    while (i > 0) {
      const up = (i - 1) >> 1;
      if (p[up] <= pri) break;
      k[i] = k[up]; p[i] = p[up]; i = up;
    }
    k[i] = key; p[i] = pri;
  }
  pop() {
    const k = this.k, p = this.p, top = k[0], lastK = k.pop(), lastP = p.pop();
    if (k.length) {
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i, mp = lastP;
        if (l < k.length && p[l] < mp) { m = l; mp = p[l]; }
        if (r < k.length && p[r] < mp) { m = r; mp = p[r]; }
        if (m === i) break;
        k[i] = k[m]; p[i] = p[m]; i = m;
      }
      k[i] = lastK; p[i] = lastP;
    }
    return top;
  }
}
