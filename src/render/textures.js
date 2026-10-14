// Texture helpers for procedural pixel art.

import * as THREE from 'three';

export function makeCanvas(width, height) {
  const c = document.createElement('canvas');
  c.width = width;
  c.height = height;
  return c;
}

/**
 * Pixel-art texture sampled with PIXEL_SAMPLING (linear filtering + pixel snapping in the shader).
 * Mipmaps keep distant surfaces from shimmering. repeat: tile across UVs outside 0..1.
 */
export function pixelTexture(canvas, { repeat = false } = {}) {
  const t = new THREE.CanvasTexture(canvas);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.LinearFilter;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

/** Stacks equally sized canvases into one sRGB texture array (one material for many surfaces). */
export function layerArray(canvases) {
  const { width, height } = canvases[0];
  const data = new Uint8Array(width * height * 4 * canvases.length);
  canvases.forEach((c, i) => {
    data.set(c.getContext('2d').getImageData(0, 0, width, height).data, i * width * height * 4);
  });
  const t = new THREE.DataArrayTexture(data, width, height, canvases.length);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.magFilter = THREE.LinearFilter;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}
