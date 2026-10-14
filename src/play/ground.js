// How the simulation stands on the render terrain: ground / water / wall for her body, and the
// crew's navigation grid. Shared by the game and the tests (no rendering here).

import { WATER_Y } from '../world/terrain.js';
import { NavGrid } from '../game/nav.js';

export const BODY_R = 0.25;
export const MAX_STEP = 0.6;

/** colliders: props' circles { x, z, r } and boxes { minX, maxX, minZ, maxZ }. */
export function groundQueries(terrain, colliders = []) {
  const isWater = (x, z) => terrain.heightAt(x, z) < WATER_Y + 0.2;
  const hitsProp = (x, z, r) => colliders.some(c => (c.r !== undefined
    ? Math.hypot(x - c.x, z - c.z) < c.r + r
    : x > c.minX - r && x < c.maxX + r && z > c.minZ - r && z < c.maxZ + r));
  // standing on water (ice, a deck, skimming) puts her feet at the surface, not the bed
  const heightHere = (x, z) => (isWater(x, z) ? WATER_Y : terrain.heightAt(x, z));

  /** The simulation's ground hook: 'ground' | 'water' | 'wall' for her body at (x, z), coming from (fx, fz). */
  const ground = (x, z, fx, fz) => {
    const here = heightHere(fx, fz);
    let water = false;
    for (const [dx, dz] of [[0, 0], [BODY_R, 0], [-BODY_R, 0], [0, BODY_R], [0, -BODY_R]]) {
      const px = x + dx, pz = z + dz;
      if (isWater(px, pz)) { if (dx === 0 && dz === 0) water = true; continue; }
      if (!terrain.walkable(px, pz) || terrain.heightAt(px, pz) > here + MAX_STEP) return 'wall';
    }
    if (hitsProp(x, z, BODY_R) && !hitsProp(fx, fz, BODY_R)) return 'wall';
    return water ? 'water' : 'ground';
  };

  /** The crew's grid over the whole terrain (1 m cells): land without props. */
  const navGrid = () => new NavGrid({
    x0: -56, z0: -56, w: 112, h: 112, cell: 1, maxStep: MAX_STEP,
    ground: (x, z) => (terrain.walkable(x, z) && !isWater(x, z) && !hitsProp(x, z, 0.2) ? terrain.heightAt(x, z) : null),
  });

  return { isWater, hitsProp, heightHere, ground, navGrid };
}

/** Wire a simulation to the terrain: her ground hook and the crew's routes. */
export function attachTerrain(sim, terrain, colliders) {
  const q = groundQueries(terrain, colliders);
  sim.ground = q.ground;
  const nav = q.navGrid();
  nav.blocked = (x, z) => sim.navBlocked(x, z);
  sim.crew.opt.route = (a, b, c, d) => nav.route(a, b, c, d);
  return { ...q, nav };
}
