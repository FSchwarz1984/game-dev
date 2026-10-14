// Sun (or moon) with a tight, texel-snapped ortho shadow frustum that follows the camera target,
// hemisphere fill, colour-matched fog, lanterns, and the per-frame terms for protected sprites.

import * as THREE from 'three';
import { shared } from './materials.js';
import { characterLight } from './sprites.js';
import { approach } from '../core/math.js';

const DEG = Math.PI / 180;
const UP = new THREE.Vector3(0, 1, 0);

/**
 * Time-of-day presets. Colours are sRGB hex. Intensities use three's units: a directional light of
 * intensity pi lights albedo 1 to 1. az: degrees clockwise from north (-Z); el: degrees up.
 * character: brightness floor, camera-front fill [colour, strength] and rim [colour, strength].
 */
export const PRESETS = {
  morning: {
    sun: { az: 108, el: 21, color: 0xffd6a8, intensity: 3.1 },
    hemi: { sky: 0xa9c3ee, ground: 0x7d6a52, intensity: 1.2 },
    fog: { color: 0xd3d9e3, near: 36, far: 150 },
    exposure: 1.0,
    lanterns: 0,
    character: { floor: 0.55, fill: [0xfff0e0, 0.18], rim: [0xffe0b0, 0.5] },
    grade: { lift: [0.01, 0.0, 0.025], gamma: [1, 1, 1], gain: [1.02, 1.0, 0.97], saturation: 1.1 },
    bloom: 0.6, vignette: 0.3, glint: 2.6,
  },
  noon: {
    sun: { az: 145, el: 56, color: 0xfff6e8, intensity: 3.3 },
    hemi: { sky: 0xb7d4ff, ground: 0x6f6448, intensity: 1.15 },
    fog: { color: 0xc4dceb, near: 45, far: 170 },
    exposure: 1.0,
    lanterns: 0,
    character: { floor: 0.5, fill: [0xffffff, 0.14], rim: [0xfffbe8, 0.4] },
    grade: { lift: [0, 0, 0.01], gamma: [1, 1, 1], gain: [1, 1, 1], saturation: 1.06 },
    bloom: 0.5, vignette: 0.28, glint: 3.0,
  },
  evening: {
    sun: { az: 258, el: 16, color: 0xffa868, intensity: 3.6 },
    hemi: { sky: 0x9a9ccc, ground: 0x6e5040, intensity: 1.3 },
    fog: { color: 0xd8a888, near: 34, far: 140 },
    exposure: 1.05,
    lanterns: 0.6,
    character: { floor: 0.5, fill: [0xffe0c8, 0.16], rim: [0xffb878, 0.65] },
    grade: { lift: [0.02, 0.0, 0.03], gamma: [1, 1, 1], gain: [1.04, 0.98, 0.92], saturation: 1.12 },
    bloom: 0.8, vignette: 0.34, glint: 3.2,
  },
  night: {
    sun: { az: 200, el: 48, color: 0x8aa4ff, intensity: 1.1 }, // moonlight
    hemi: { sky: 0x33467a, ground: 0x161622, intensity: 1.05 },
    fog: { color: 0x101a30, near: 30, far: 120 },
    exposure: 1.2,
    lanterns: 1,
    character: { floor: 0.4, fill: [0xb8c8ff, 0.12], rim: [0x9fc0ff, 0.6] },
    grade: { lift: [0.0, 0.01, 0.035], gamma: [1, 1, 1.02], gain: [0.98, 1, 1.06], saturation: 1.05 },
    bloom: 1.0, vignette: 0.38, glint: 1.4,
  },
};
export const PRESET_ORDER = ['morning', 'noon', 'evening', 'night'];

// three's point-light distance attenuation (decay 2 with a smooth cutoff).
const attenuation = (d, cutoff, decay) => {
  const f = 1 / Math.max(d ** decay, 0.01);
  if (cutoff <= 0) return f;
  const s = Math.max(0, Math.min(1, 1 - (d / cutoff) ** 4));
  return f * s * s;
};

const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _d = new THREE.Vector3(), _dir = new THREE.Vector3();
const _x = new THREE.Vector3(), _y = new THREE.Vector3(), _c = new THREE.Vector3();
const _right = new THREE.Vector3(), _up = new THREE.Vector3();
const _key = new THREE.Color();

export class Lighting {
  constructor(scene, proxies, tier) {
    this.scene = scene;
    this.proxies = proxies;
    this.sunDir = shared.uSunDir.value;

    this.sun = new THREE.DirectionalLight();
    this.sun.castShadow = true;
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.04;
    this.sun.shadow.camera.near = 1;
    this.sun.shadow.camera.far = 260;
    this.hemi = new THREE.HemisphereLight();
    scene.add(this.sun, this.sun.target, this.hemi);
    scene.fog = new THREE.Fog(0xffffff, 40, 160);
    scene.background = new THREE.Color();

    this.lanterns = [];  // { position, color, intensity, distance, priority }
    this.lights = [];    // PointLight pool, limited per tier
    this.glows = [];     // { material, strength }: emissive driven by the lantern level
    this.listeners = [];
    this.extentScale = 1;
    this.preset = null;
    this.setTier(tier);
  }

  onPreset(fn) { this.listeners.push(fn); if (this.preset) fn(this.preset); }

  addLantern({ position, color = 0xffb35c, intensity = 9, distance = 9, priority = 0 }) {
    this.lanterns.push({ position: position.clone(), color: new THREE.Color(color), intensity, distance, priority });
    this.rebuildLights();
  }

  /** An emissive material (lantern paper, window) that glows with the lantern level. */
  addGlow(material, color, strength) {
    material.emissive = new THREE.Color(color);
    this.glows.push({ material, strength });
    if (this.preset) material.emissiveIntensity = strength * this.preset.lanterns;
  }

  setTier(tier) {
    this.tier = tier;
    const s = this.sun.shadow;
    s.mapSize.set(tier.shadowMapSize, tier.shadowMapSize);
    s.radius = tier.shadowRadius;
    if (s.map) { s.map.dispose(); s.map = null; }
    this.rebuildLights();
  }

  rebuildLights() {
    for (const l of this.lights) this.scene.remove(l);
    const chosen = [...this.lanterns].sort((a, b) => b.priority - a.priority).slice(0, this.tier.pointLights);
    this.lights = chosen.map(L => {
      const light = new THREE.PointLight(L.color, 0, L.distance, 2);
      light.position.copy(L.position);
      light.userData.base = L.intensity;
      this.scene.add(light);
      return light;
    });
    if (this.preset) this.applyLanterns();
  }

  applyLanterns() {
    const k = this.preset.lanterns;
    for (const l of this.lights) { l.intensity = l.userData.base * k; l.visible = l.intensity > 0; }
    for (const g of this.glows) g.material.emissiveIntensity = g.strength * k;
  }

  setPreset(name) {
    const p = PRESETS[name];
    this.presetName = name;
    this.preset = p;
    const el = p.sun.el * DEG, az = p.sun.az * DEG;
    this.sunDir.set(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
    this.sun.color.set(p.sun.color);
    this.sun.intensity = p.sun.intensity;
    this.hemi.color.set(p.hemi.sky);
    this.hemi.groundColor.set(p.hemi.ground);
    this.hemi.intensity = p.hemi.intensity;
    this.scene.fog.color.set(p.fog.color);
    this.scene.fog.near = p.fog.near;
    this.scene.fog.far = p.fog.far;
    this.scene.background.set(p.fog.color);

    // Character terms use the same 1/pi convention as three's Lambert BRDF.
    const cl = characterLight;
    cl.uSunColor.value.copy(this.sun.color).multiplyScalar(p.sun.intensity / Math.PI);
    cl.uSkyColor.value.copy(this.hemi.color).multiplyScalar(p.hemi.intensity / Math.PI);
    cl.uGroundColor.value.copy(this.hemi.groundColor).multiplyScalar(p.hemi.intensity / Math.PI);
    cl.uFillColor.value.set(p.character.fill[0]).multiplyScalar(p.character.fill[1]);
    cl.uRimColor.value.set(p.character.rim[0]);
    cl.uRimStrength.value = p.character.rim[1];
    cl.uFloor.value = p.character.floor;

    this.applyLanterns();
    for (const fn of this.listeners) fn(p);
  }

  /** center: middle of the visible ground; camera: for the rim direction; characters: protected sprites. */
  update(dt, center, camera, characters) {
    this.updateShadowFrustum(center);
    _right.setFromMatrixColumn(camera.matrixWorld, 0);
    _up.setFromMatrixColumn(camera.matrixWorld, 1);
    const rim = characterLight.uRimDir.value.set(this.sunDir.dot(_right), this.sunDir.dot(_up) + 0.35);
    if (rim.lengthSq() < 1e-4) rim.set(0, 1); else rim.normalize();
    for (const c of characters) this.updateCharacter(c, dt);
  }

  // Snapping the frustum to whole shadow texels keeps shadow edges from swimming as the camera moves.
  updateShadowFrustum(center) {
    const ext = this.tier.shadowExtent * this.extentScale;
    const cam = this.sun.shadow.camera;
    if (cam.right !== ext) {
      cam.left = cam.bottom = -ext;
      cam.right = cam.top = ext;
      cam.updateProjectionMatrix();
    }
    const texel = (2 * ext) / this.sun.shadow.mapSize.x;
    _x.crossVectors(UP, this.sunDir).normalize();
    _y.crossVectors(this.sunDir, _x);
    const px = center.dot(_x), py = center.dot(_y);
    _c.copy(center)
      .addScaledVector(_x, Math.round(px / texel) * texel - px)
      .addScaledVector(_y, Math.round(py / texel) * texel - py);
    this.sun.target.position.copy(_c);
    this.sun.position.copy(_c).addScaledVector(this.sunDir, 120);
    this.sun.target.updateMatrixWorld();
    this.sun.updateMatrixWorld();
  }

  /** One smoothed sun-visibility value per character plus a key light from nearby lanterns. */
  updateCharacter(mesh, dt, snap = false) {
    const u = mesh.userData.sprite.uniforms;
    const p = mesh.position;
    let vis = 0;
    for (const h of [0.45, 1.15]) {
      _a.set(p.x, p.y + h, p.z);
      _b.copy(_a).addScaledVector(this.sunDir, 70);
      vis += 0.5 * this.proxies.transmittance(_a, _b, 'shade');
    }
    u.uShade.value = snap ? vis : approach(u.uShade.value, vis, 5, dt);

    _key.setRGB(0, 0, 0);
    _dir.set(0, 0, 0);
    _a.set(p.x, p.y + 0.8, p.z);
    for (const l of this.lights) {
      if (!l.visible) continue;
      _d.subVectors(l.position, _a);
      const f = attenuation(_d.length(), l.distance, l.decay) * l.intensity / Math.PI;
      _key.r += l.color.r * f; _key.g += l.color.g * f; _key.b += l.color.b * f;
      _dir.addScaledVector(_d.normalize(), f);
    }
    u.uKeyColor.value.copy(_key);
    u.uKeyDir.value.copy(_dir.lengthSq() > 1e-8 ? _dir.normalize() : UP);
  }
}
