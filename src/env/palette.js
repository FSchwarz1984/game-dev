/* =====================================================================
   env/palette — the art direction in numbers. Late-summer cedar
   mountains: olive and moss greens, blue-green shadows, honeyed light,
   grey-brown bark, weathered vermilion. Ramps run dark→light and are
   hue-shifted (cool violet-blue in shadow, warm yellow in light).
   The ground colours are v0.1's terrain shader values (the part of v0.1
   the owner liked), kept as the anchor; everything else is tuned to sit
   next to them. Characters are kept out of this palette's value range:
   the ground and foliage stay mid-value and low-chroma on purpose.
   ===================================================================== */
import { ramp, hexRGB } from './core.js';

const R = (hex, n, o) => ramp(hex, n, o);

export const PAL = {
  // ---- ground (v0.1 terrain values) ----
  grassDark: [hexRGB('#2a4632'), hexRGB('#345a2f')],
  grassMid: [hexRGB('#4a7232'), hexRGB('#5b8436')],
  grassLite: [hexRGB('#7a9a42'), hexRGB('#93ab52')],
  grassBlade: hexRGB('#a8bc6a'),
  grassDry: hexRGB('#818149'), grassOlive: hexRGB('#6a7743'),
  flowerWhite: hexRGB('#ecebdc'), flowerYellow: hexRGB('#e6d25a'), flowerBlue: hexRGB('#8a92dc'), flowerPink: hexRGB('#d89aa6'),
  floor: [hexRGB('#3b2e2a'), hexRGB('#4e443c'), hexRGB('#645935')], needle: hexRGB('#7c5630'), litter: [hexRGB('#8b574e'), hexRGB('#9a6a3c'), hexRGB('#6e5a34'), hexRGB('#a88a4a')],
  path: R('#8b8160', 6, { lo: 0.5, hi: 0.42, hueShift: 0.04 }),
  pathDark: hexRGB('#5e553c'),
  moss: R('#4f7a33', 6, { lo: 0.55, hi: 0.45, hueShift: 0.06 }),
  mossDeep: R('#3c5c2a', 5, { lo: 0.5, hi: 0.45 }),
  soil: R('#6e523b', 6, { lo: 0.5, hi: 0.45 }),
  gravel: R('#8f8a72', 5, { lo: 0.45, hi: 0.4 }),
  bed: R('#6d7366', 5, { lo: 0.5, hi: 0.4 }),
  // ---- stone ----
  stone: R('#7a7d7c', 7, { lo: 0.55, hi: 0.5, hueShift: 0.04 }),
  stoneWarm: R('#837a6c', 7, { lo: 0.55, hi: 0.48, hueShift: 0.04 }),
  stoneCool: R('#6c737a', 6, { lo: 0.55, hi: 0.48, hueShift: 0.03 }),
  rock: R('#6e6e6c', 7, { lo: 0.58, hi: 0.5, hueShift: 0.05 }),
  rockWarm: R('#7a6a58', 7, { lo: 0.58, hi: 0.48, hueShift: 0.05 }),
  lichen: R('#a7a26a', 4, { lo: 0.4, hi: 0.3 }),
  // ---- wood & bark ----
  barkCedar: R('#6b4330', 6, { lo: 0.55, hi: 0.45 }),
  barkGrey: R('#6c6359', 7, { lo: 0.6, hi: 0.45 }),
  barkCamphor: R('#5f5a4e', 8, { lo: 0.62, hi: 0.48, hueShift: 0.05 }),
  barkPine: R('#6a4a3a', 6, { lo: 0.55, hi: 0.45 }),
  wood: R('#7a6450', 6, { lo: 0.5, hi: 0.45 }),
  woodDark: R('#4d3a2e', 6, { lo: 0.5, hi: 0.45 }),
  woodGrey: R('#7f7468', 6, { lo: 0.52, hi: 0.45 }), // silvered old boards
  woodNew: R('#b08a5a', 6, { lo: 0.5, hi: 0.4 }),
  woodRed: R('#a8452e', 6, { lo: 0.5, hi: 0.4 }),
  // ---- foliage ----
  cedar: R('#2d4a3c', 7, { lo: 0.55, hi: 0.55, hueShift: 0.07 }),
  cedarDeep: R('#223a33', 5, { lo: 0.5, hi: 0.45 }),
  pine: R('#2f4a35', 7, { lo: 0.55, hi: 0.55, hueShift: 0.07 }),
  pineNeedle: R('#3b5a38', 7, { lo: 0.55, hi: 0.55, hueShift: 0.08 }),
  barkPineBlack: R('#5b4e45', 6, { lo: 0.55, hi: 0.42, hueShift: 0.05 }),
  mapleYoung: R('#6f9a3e', 7, { lo: 0.55, hi: 0.4, hueShift: 0.07 }),
  camphor: R('#4d7434', 8, { lo: 0.6, hi: 0.52, hueShift: 0.08 }),
  camphorDeep: R('#2c4a35', 6, { lo: 0.55, hi: 0.45, hueShift: 0.06 }),
  camphorNew: R('#86a645', 6, { lo: 0.45, hi: 0.4 }),
  maple: R('#56853a', 7, { lo: 0.55, hi: 0.45, hueShift: 0.07 }),
  mapleRed: R('#9a3a2c', 7, { lo: 0.55, hi: 0.4, hueShift: 0.04, satShift: -0.05 }),
  broad: R('#3f6634', 7, { lo: 0.55, hi: 0.5, hueShift: 0.07 }),   // camellia / azalea: darker, glossier
  bamboo: R('#6f9a45', 6, { lo: 0.5, hi: 0.45 }),
  bambooOld: R('#a39a55', 5, { lo: 0.45, hi: 0.4 }),
  bambooLeaf: R('#4f7f3b', 6, { lo: 0.5, hi: 0.5 }),
  fern: R('#4f7c39', 6, { lo: 0.5, hi: 0.5 }),
  sasa: R('#4c7a34', 6, { lo: 0.5, hi: 0.45 }),
  kudzu: R('#4a7034', 6, { lo: 0.5, hi: 0.42, satShift: -0.05 }),
  kudzuFlower: R('#9b4f9a', 4, { lo: 0.45, hi: 0.4 }),
  susuki: R('#8f9a5a', 5, { lo: 0.45, hi: 0.4 }),
  plume: R('#d9cdb0', 4, { lo: 0.35, hi: 0.3 }),
  lily: R('#efe9dc', 4, { lo: 0.3, hi: 0.2 }),
  hydr: [R('#6f86c4', 5, { lo: 0.4, hi: 0.35 }), R('#9a7fbf', 5, { lo: 0.4, hi: 0.35 }), R('#8d9fc9', 5, { lo: 0.4, hi: 0.3 })],
  // ---- made things ----
  straw: R('#b89a5c', 6, { lo: 0.5, hi: 0.4 }),
  thatch: R('#8a7442', 7, { lo: 0.55, hi: 0.42 }),
  rope: R('#c2a868', 5, { lo: 0.45, hi: 0.35 }),
  paper: R('#ece4d2', 5, { lo: 0.32, hi: 0.2 }),
  plaster: R('#d8cdb4', 5, { lo: 0.35, hi: 0.25 }),
  cloth: R('#3e4f7a', 6, { lo: 0.5, hi: 0.45 }),     // indigo
  clothRed: R('#a8402e', 5, { lo: 0.5, hi: 0.4 }),
  clothOchre: R('#b08a3a', 5, { lo: 0.5, hi: 0.4 }),
  wicker: R('#a17a45', 6, { lo: 0.5, hi: 0.4 }),
  metal: R('#5d6366', 5, { lo: 0.5, hi: 0.5 }),
  rust: R('#7b4a2c', 5, { lo: 0.5, hi: 0.4 }),
  lacquer: R('#5a2a22', 5, { lo: 0.5, hi: 0.4 }),
  // ---- character placeholder ----
  hat: R('#c9a463', 6, { lo: 0.5, hi: 0.35, hueShift: 0.04 }),
  hair: R('#2c2430', 5, { lo: 0.45, hi: 0.4 }),
  skin: R('#f1d9bd', 5, { lo: 0.3, hi: 0.25, hueShift: 0.03 }),
  indigo: R('#2c3c6b', 6, { lo: 0.55, hi: 0.5, hueShift: 0.04 }),
  sash: R('#c53a2b', 5, { lo: 0.5, hi: 0.4 }),
  cream: R('#f0e4cc', 4, { lo: 0.3, hi: 0.2 }),
  // ---- the Far ----
  far: R('#a9b8d2', 5, { lo: 0.35, hi: 0.25 }),
};
