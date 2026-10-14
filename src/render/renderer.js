// WebGL renderer, quality tiers and the adaptive fallback.
// Budgets follow the table in docs/knowledge/03-hd2d-web.md (desktop vs. mid-range phone).

import * as THREE from 'three';

export const TIERS = {
  low: {
    name: 'low',
    dprCap: 1.5,
    shadowMapSize: 1024,
    shadowType: THREE.BasicShadowMap, // crisp, no PCF noise; stable thanks to texel snapping
    shadowRadius: 1,
    shadowExtent: 18,                 // half-size of the sun's ortho frustum, metres
    pointLights: 3,
    bloomLevels: 4,
    dof: 'tiltshift',
    aa: 'fxaa',
  },
  high: {
    name: 'high',
    dprCap: 2,
    shadowMapSize: 2048,
    shadowType: THREE.PCFShadowMap,
    shadowRadius: 2,
    shadowExtent: 22,
    pointLights: 8,
    bloomLevels: 8,
    dof: 'bokeh',
    aa: 'smaa',
  },
};

/** Phones and tablets start on 'low'; touch laptops with a fine pointer stay on 'high'. */
export function detectTier() {
  const nav = window.navigator;
  const ua = nav.userAgent || '';
  const mobileUA = /Android|iPhone|iPad|iPod|Mobile/i.test(ua) || nav.userAgentData?.mobile === true;
  const iPadOS = /Macintosh/.test(ua) && nav.maxTouchPoints > 1;
  const coarse = window.matchMedia?.('(pointer: coarse)').matches;
  return mobileUA || iPadOS || (coarse && nav.maxTouchPoints > 0) ? 'low' : 'high';
}

/**
 * Largest ratio <= cap that divides the device ratio by a whole number, so the browser always
 * upscales the canvas by an integer factor (fractional upscaling smears pixel art).
 */
export function pixelRatioFor(deviceRatio, cap) {
  const dpr = deviceRatio || 1;
  return dpr / Math.max(1, Math.ceil(dpr / cap - 1e-3));
}

const SLOW_FRAME_MS = 22;
const SLOW_HOLD_S = 2;

export class RenderContext {
  constructor(canvas, { tier, auto }) {
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, stencil: false, powerPreference: 'high-performance' });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.NoToneMapping; // tone mapping happens in the post chain
    renderer.shadowMap.enabled = true;
    renderer.info.autoReset = false;            // one reset per frame: counts shadow + scene + post
    this.renderer = renderer;
    this.auto = auto;
    this.listeners = [];
    this.tier = TIERS[tier];
    this.applyTier();
  }

  onTierChange(fn) { this.listeners.push(fn); }

  setTier(name) {
    if (this.tier.name === name) return;
    this.tier = TIERS[name];
    this.applyTier();
    for (const fn of this.listeners) fn(this.tier);
  }

  applyTier() {
    const sm = this.renderer.shadowMap;
    sm.type = this.tier.shadowType;
    sm.needsUpdate = true;
    this.ema = 0;
    this.slowFor = 0;
    this.graceUntil = performance.now() + 2500; // ignore shader-compile hitches after a switch
    this.resize();
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.renderer.setPixelRatio(pixelRatioFor(window.devicePixelRatio, this.tier.dprCap));
    this.renderer.setSize(w, h);
    this.width = w;
    this.height = h;
  }

  /** Feed real frame intervals; drops an auto-picked 'high' tier to 'low' when it stays slow. */
  sampleFrame(ms, now) {
    if (!this.auto || this.tier.name === 'low') return;
    if (document.hidden || now < this.graceUntil) { this.slowFor = 0; return; }
    this.ema = this.ema ? this.ema + (Math.min(ms, 100) - this.ema) * 0.1 : Math.min(ms, 100);
    // Real elapsed time counts, but one long hitch can contribute at most half a second.
    this.slowFor = this.ema > SLOW_FRAME_MS ? this.slowFor + Math.min(ms, 500) / 1000 : 0;
    if (this.slowFor >= SLOW_HOLD_S) this.setTier('low');
  }
}
