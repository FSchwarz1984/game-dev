// Gray-box test scene: terraced blocks rising to the north, a stream, groves of six tree species
// with open ground between them, the giant tree over a clearing with a small shrine, a vermilion
// torii, a chibi house, rocks and a stone lantern. Content-neutral: no story, no named characters.

import * as THREE from 'three';
import { makeRng, fbm } from '../core/math.js';
import { createEnvMaterial, createBillboardMaterial, UPRIGHT_QUAD } from '../render/materials.js';
import { layerArray, pixelTexture } from '../render/textures.js';
import { createSprite } from '../render/sprites.js';
import { terrainLayers, clumpAtlas, groundAtlas, jarSprite, L, GROUND } from './art.js';
import { Terrain, SITE } from './terrain.js';
import { createWater } from './water.js';
import { buildProps } from './props.js';
import { buildTrees } from './trees.js';

// Grove regions: [species, x0, z0, x1, z1, count, variant?]
const GROVES = [
  ['broadleaf', 13, -6, 20, 6, 3], ['broadleaf', -17, 17, -7, 27, 3], ['broadleaf', -14, -31, 2, -25, 3], ['broadleaf', 24, 12, 35, 22, 3],
  ['cedar', -40, -46, 40, -34, 16], ['cedar', 39, -24, 46, 24, 6], ['cedar', -46, -30, -38, 22, 6],
  ['pine', 22, -13, 34, 0, 4], ['pine', 13, 16, 21, 22, 2], ['pine', -31, 22, -18, 33, 3],
  ['maple', -12, 17, -3, 23, 4], ['maple', -13, -13, -8, -6, 2],
  ['bamboo', -32, -15, -25, -4, 3],
  ['broadleaf', 10, 7, 14, 10, 1], ['sapling', 7, 6, 10, 9, 1], ['bush', 10, -4, 15, 0, 2],
  ['pine', -11, 6, -7, 9, 1], ['sapling', -7, 7, -4, 9, 1],
  ['bush', -18, -7, -8, -1, 4], ['bush', 14, -15, 21, -7, 4], ['bush', -6, 18, 10, 23, 3, 'azalea'], ['bush', 19, 5, 26, 10, 3],
  ['bush', -20, 9, -14, 13, 2, 'azalea'],
];

// Places that must stay open (landmarks, paths of sight).
const CLEAR = [
  [SITE.spawn.x, SITE.spawn.z, 4], [SITE.torii.x, SITE.torii.z, 3.5], [SITE.shrine.x, SITE.shrine.z, 4],
  [SITE.giantTree.x, SITE.giantTree.z, 7], [-12, 3.5, 4], [3.5, 14, 4.5], [0.9, -2, 2], [6.8, 4.6, 2.5],
];

function isOpen(terrain, x, z, r) {
  if (CLEAR.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr + r)) return false;
  const h = terrain.heightAt(x, z);
  for (const [dx, dz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) {
    if (!terrain.walkable(x + dx, z + dz) || Math.abs(terrain.heightAt(x + dx, z + dz) - h) > 0.01) return false;
  }
  const top = terrain.top[terrain.idx(x, z)];
  return top !== L.PATH && top !== L.PAVING && top !== L.SAND;
}

function scatterTrees(terrain, rng) {
  const out = [];
  for (const [species, x0, z0, x1, z1, count, variant] of GROVES) {
    let placed = 0;
    for (let tries = 0; tries < count * 40 && placed < count; tries++) {
      const x = rng.range(x0, x1), z = rng.range(z0, z1);
      const gap = species === 'bush' ? 2.2 : species === 'cedar' ? 4.2 : 5;
      if (!isOpen(terrain, x, z, 0.8) || out.some(p => Math.hypot(p.x - x, p.z - z) < gap)) continue;
      out.push({ species, x, y: terrain.heightAt(x, z), z, variant });
      placed++;
    }
  }
  return out;
}

// Grass tufts and flowers in noise-driven patches, leaving bare ground between them.
function groundCover(terrain, texture, rng) {
  const spots = [];
  for (let i = 0; i < 9000 && spots.length < 1400; i++) {
    const x = rng.range(-40, 40), z = rng.range(-40, 36);
    const patch = fbm(x * 0.12, z * 0.12, 3, 41);
    if (patch < 0.56 || !isOpen(terrain, x, z, 0.3)) continue;
    const top = terrain.top[terrain.idx(x, z)];
    if (top !== L.GRASS && top !== L.MOSS) continue;
    const flowers = patch > 0.66 && top === L.GRASS;
    const tile = flowers ? rng.pick([GROUND.WHITE, GROUND.YELLOW, GROUND.PINK, GROUND.TUFT_A]) : rng.pick([GROUND.TUFT_A, GROUND.TUFT_B, GROUND.TUFT_C, GROUND.REEDS, GROUND.FERN]);
    spots.push({ x, y: terrain.heightAt(x, z) - 0.02, z, tile, s: rng.range(0.8, 1.15) });
  }
  const opts = { map: texture, mode: 'upright', atlas: [8, 1], wind: true };
  const geo = UPRIGHT_QUAD.clone();
  const mesh = new THREE.InstancedMesh(geo, createBillboardMaterial(opts), spots.length);
  const tiles = new Float32Array(spots.length), sways = new Float32Array(spots.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
  spots.forEach((g, i) => {
    mesh.setMatrixAt(i, m.compose(p.set(g.x, g.y, g.z), q, s.set(g.s, g.s, 1)));
    tiles[i] = g.tile + (rng() < 0.5 ? 0.5 : 0);
    sways[i] = rng.range(0.6, 1.2);
    mesh.setColorAt(i, c.setScalar(rng.range(0.88, 1.05)));
  });
  geo.setAttribute('aTile', new THREE.InstancedBufferAttribute(tiles, 1));
  geo.setAttribute('aSway', new THREE.InstancedBufferAttribute(sways, 1));
  mesh.receiveShadow = true;
  mesh.computeBoundingSphere();
  mesh.name = 'ground-cover';
  return mesh;
}

/**
 * Builds the scene into `scene`. Returns { terrain, colliders, highlightables }.
 * Occluders (cut out around the player): terrain, trunks, foliage, torii, house.
 * Highlightable: the boulder, the stone lantern, the shrine and a jar sprite.
 */
export function buildTestScene({ scene, lighting, proxies }) {
  const rng = makeRng(1234);
  const layers = layerArray(terrainLayers());

  const terrain = new Terrain();
  const ground = new THREE.Mesh(terrain.buildGeometry(), createEnvMaterial(layers, { lip: true, variation: true, occluder: true }));
  ground.castShadow = ground.receiveShadow = true;
  ground.name = 'terrain';
  scene.add(ground);
  proxies.setGround((x, z) => terrain.heightAt(x, z));

  const water = createWater(terrain);
  scene.add(water);
  lighting.onPreset(p => { water.material.uniforms.uGlint.value = p.glint; });

  const props = buildProps({ layers, terrain, lighting, proxies });
  scene.add(props.group);

  const trees = buildTrees({
    placements: scatterTrees(terrain, rng),
    giant: SITE.giantTree,
    layers,
    clumpTexture: pixelTexture(clumpAtlas()),
    proxies,
  });
  scene.add(trees.group);
  scene.add(groundCover(terrain, pixelTexture(groundAtlas()), rng));

  // A prop sprite (normal lighting) to exercise the sprite outline path of the highlight API.
  const jar = createSprite({ sheet: { texture: pixelTexture(jarSprite()), frameW: 32, frameH: 32 }, size: [0.8, 0.8], kind: 'prop' });
  jar.position.set(-10.3, terrain.heightAt(-10.3, 5.9) - 0.05, 5.9);
  jar.name = 'jar';
  scene.add(jar);

  return {
    terrain,
    colliders: [...props.colliders, ...trees.colliders, { x: jar.position.x, z: jar.position.z, r: 0.35 }],
    highlightables: [...props.highlightables, jar],
  };
}
