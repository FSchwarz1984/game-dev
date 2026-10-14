// Visible transfers: a stream of quality-coloured motes arcing from the source to the
// receiver (the "性质流" of the feedback rules), a flash where it lands, and an expanding
// ring for 放 (release). Square points on purpose: they read as pixels.

import * as THREE from 'three';

const POOL = 640;

export class TransferFx {
  constructor(scene) {
    this.scene = scene;
    const g = new THREE.BufferGeometry();
    this.pos = new Float32Array(POOL * 3);
    this.col = new Float32Array(POOL * 3);
    this.alpha = new Float32Array(POOL);
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(this.col, 3));
    g.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1));
    const m = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uSize: { value: 7 * Math.min(2, window.devicePixelRatio || 1) } },
      vertexShader: `
        attribute vec3 color; attribute float alpha; varying vec3 vC; varying float vA; uniform float uSize;
        void main() { vC = color; vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv; gl_PointSize = uSize * (alpha > 0.0 ? 1.0 : 0.0); }`,
      fragmentShader: `
        varying vec3 vC; varying float vA;
        void main() { if (vA <= 0.0) discard; gl_FragColor = vec4(vC * 1.6, vA); }`,
    });
    this.points = new THREE.Points(g, m);
    this.points.frustumCulled = false;
    this.points.renderOrder = 10;
    scene.add(this.points);
    this.motes = [];
    this.rings = [];
    this.next = 0;
  }

  /** A stream of motes from `from` to `to` (THREE.Vector3), coloured `color` (CSS hex). */
  stream(from, to, color, { count = 16, duration = 0.42, onLand } = {}) {
    const c = new THREE.Color(color);
    const mid = from.clone().lerp(to, 0.5);
    mid.y += Math.max(0.6, from.distanceTo(to) * 0.35);
    for (let i = 0; i < count; i++) {
      const slot = this.next; this.next = (this.next + 1) % POOL;
      this.motes.push({
        slot, from: from.clone(), mid: mid.clone(), to: to.clone(), c,
        t: -i * (duration * 0.5 / count), dur: duration, jitter: (Math.random() - 0.5) * 0.25,
        land: i === count - 1 ? onLand : null,
      });
    }
  }

  /** An expanding ground ring for 放, coloured by the released quality. */
  ring(at, color, radius = 3) {
    const geo = new THREE.RingGeometry(0.9, 1, 48);
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.copy(at).add(new THREE.Vector3(0, 0.05, 0));
    this.scene.add(mesh);
    this.rings.push({ mesh, t: 0, dur: 0.5, radius });
  }

  update(dt) {
    const p = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3();
    for (let i = this.motes.length - 1; i >= 0; i--) {
      const m = this.motes[i];
      m.t += dt;
      const k = Math.min(1, Math.max(0, m.t / m.dur));
      const o = m.slot * 3;
      if (m.t < 0) { this.alpha[m.slot] = 0; continue; }
      // quadratic bezier with a little sideways jitter so the stream reads as many motes
      a.copy(m.from).lerp(m.mid, k); b.copy(m.mid).lerp(m.to, k); p.copy(a).lerp(b, k);
      p.x += Math.sin(k * Math.PI) * m.jitter; p.z += Math.cos(k * Math.PI * 2) * m.jitter * 0.6;
      this.pos[o] = p.x; this.pos[o + 1] = p.y; this.pos[o + 2] = p.z;
      this.col[o] = m.c.r; this.col[o + 1] = m.c.g; this.col[o + 2] = m.c.b;
      this.alpha[m.slot] = k < 1 ? 0.95 : 0;
      if (k >= 1) { if (m.land) m.land(); this.motes.splice(i, 1); }
    }
    const g = this.points.geometry;
    g.attributes.position.needsUpdate = true; g.attributes.color.needsUpdate = true; g.attributes.alpha.needsUpdate = true;

    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i];
      r.t += dt;
      const k = r.t / r.dur;
      r.mesh.scale.setScalar(0.3 + k * r.radius);
      r.mesh.material.opacity = Math.max(0, 0.9 * (1 - k));
      if (k >= 1) { this.scene.remove(r.mesh); r.mesh.geometry.dispose(); r.mesh.material.dispose(); this.rings.splice(i, 1); }
    }
  }
}
