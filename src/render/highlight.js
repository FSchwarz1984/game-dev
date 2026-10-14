// Target highlight for the interaction-targeting system: a constant-width outline plus a pixel
// ring on the ground under the target, both pulsing.
// Outline method: inverted hull for meshes (one extra draw, no extra full-screen pass, works with
// the depth buffer), and a two-texel ring drawn by the sprite shader itself for billboards (a hull
// cannot outline an alpha-cut quad, and a post outline would not see the billboard's shape).

import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

// Silhouette dilated by uWidth pixels in screen space; uDepthBias pushes the dark outer line
// behind the bright inner one where they overlap.
const HULL_VERTEX = /* glsl */ `
uniform float uWidth;
uniform float uDepthBias;
uniform vec2 uResolution;
void main() {
  vec4 clip = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  vec2 dir = (normalMatrix * normal).xy;
  float len = length(dir);
  clip.xy += (len > 1e-4 ? dir / len : vec2(0.0)) * uWidth * 2.0 / uResolution * clip.w;
  clip.z += uDepthBias * clip.w;
  gl_Position = clip;
}
`;

const FLAT_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
void main() {
  gl_FragColor = vec4(uColor, 1.0);
  #include <colorspace_fragment>
}
`;

const RING_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

// Pixel-snapped ring: bright band with dark borders (reads on light and dark ground) and four
// slowly turning notches for motion.
const RING_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uTime;
uniform float uPulse;
uniform float uTexels;
varying vec2 vUv;
void main() {
  vec2 q = (floor(vUv * uTexels) + 0.5) / uTexels * 2.0 - 1.0;
  float r = length(q);
  float px = 2.0 / uTexels;
  float inner = 0.7 - 0.06 * uPulse;
  float notch = step(0.88, fract(atan(q.y, q.x) / 6.2831853 * 4.0 + uTime * 0.2));
  bool band = r > inner && r < 0.9 && notch < 0.5;
  bool border = r > inner - 1.5 * px && r < 0.9 + 1.5 * px;
  if (!border) discard;
  gl_FragColor = vec4(band ? uColor : vec3(0.03, 0.02, 0.015), 1.0);
  #include <colorspace_fragment>
}
`;

const _box = new THREE.Box3(), _size = new THREE.Vector3(), _pos = new THREE.Vector3();

export class Highlighter {
  constructor(scene, { color = 0xfff0a0, pulse = 4, width = 3 } = {}) {
    this.color = new THREE.Color(color);
    this.pulseSpeed = pulse;
    this.width = width;
    this.target = null;
    this.hulls = [];
    this.sprites = [];
    this.anchor = new THREE.Vector3();
    this.ringOffset = new THREE.Vector3();
    this.time = 0;
    this.hullGeometries = new WeakMap();
    this.current = new THREE.Color();

    // Two-tone outline: a bright line inside a dark one, so it reads on light and dark ground.
    const resolution = { value: new THREE.Vector2(1, 1) };
    const hull = (color, bias) => new THREE.ShaderMaterial({
      uniforms: { uColor: { value: color }, uWidth: { value: width }, uDepthBias: { value: bias }, uResolution: resolution },
      vertexShader: HULL_VERTEX,
      fragmentShader: FLAT_FRAGMENT,
      side: THREE.BackSide,
    });
    this.hullMaterials = [hull(new THREE.Color(0.03, 0.02, 0.015), 0.0004), hull(this.current, 0)];
    this.resolution = resolution.value;
    this.ring = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
      new THREE.ShaderMaterial({
        uniforms: { uColor: { value: this.current }, uTime: { value: 0 }, uPulse: { value: 0 }, uTexels: { value: 32 } },
        vertexShader: RING_VERTEX,
        fragmentShader: RING_FRAGMENT,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2,
      }),
    );
    this.ring.visible = false;
    this.ring.frustumCulled = false;
    scene.add(this.ring);
  }

  /** object: any Object3D (mesh, group or sprite) or null. opts: { color, pulse } (pulse = speed, 0 = steady). */
  highlight(object, opts = {}) {
    this.color.set(opts.color ?? this.color);
    if (opts.pulse !== undefined) this.pulseSpeed = opts.pulse;
    if (object === this.target) return;
    this.clear();
    this.target = object;
    if (!object) return;

    const meshes = [];
    object.traverse(o => {
      if (o.userData.sprite) this.sprites.push(o);
      else if (o.isMesh && !o.isInstancedMesh && o !== this.ring) meshes.push(o);
    });
    for (const o of meshes) { // hulls are added after the traversal so it never visits them
      for (const material of this.hullMaterials) {
        const hull = new THREE.Mesh(this.hullGeometry(o.geometry), material);
        hull.raycast = () => {};
        o.add(hull);
        this.hulls.push(hull);
      }
    }

    let radius, baseY;
    object.updateMatrixWorld(true);
    if (object.userData.sprite) {
      object.getWorldPosition(_pos);
      radius = object.userData.sprite.size[0] * 0.5;
      baseY = _pos.y;
      this.ring.position.set(_pos.x, 0, _pos.z);
    } else {
      _box.setFromObject(object).getSize(_size);
      radius = Math.max(_size.x, _size.z) * 0.5;
      baseY = _box.min.y;
      this.ring.position.set((_box.min.x + _box.max.x) / 2, 0, (_box.min.z + _box.max.z) / 2);
    }
    const r = radius + 0.5;
    this.ring.position.y = baseY + 0.04;
    // moving targets (a wandering yokai, a carried log) keep their ring under them
    object.getWorldPosition(this.anchor);
    this.ringOffset.set(this.ring.position.x - this.anchor.x, 0, this.ring.position.z - this.anchor.z);
    this.ring.scale.set(r * 2, 1, r * 2);
    this.ring.material.uniforms.uTexels.value = Math.round(r * 2 * 16); // 16 texels per metre
    this.ring.visible = true;
  }

  clear() {
    for (const h of this.hulls) h.removeFromParent();
    for (const s of this.sprites) s.userData.sprite.setOutline(null);
    this.hulls.length = 0;
    this.sprites.length = 0;
    this.ring.visible = false;
    this.target = null;
  }

  // Smooth normals (vertices merged by position) so the hull stays closed at hard edges.
  hullGeometry(geometry) {
    let g = this.hullGeometries.get(geometry);
    if (!g) {
      const base = new THREE.BufferGeometry();
      base.setAttribute('position', geometry.getAttribute('position'));
      if (geometry.index) base.setIndex(geometry.index);
      g = mergeVertices(base, 1e-3);
      g.computeVertexNormals();
      this.hullGeometries.set(geometry, g);
    }
    return g;
  }

  update(dt, renderer) {
    if (!this.target) return;
    this.target.getWorldPosition(this.anchor);
    this.ring.position.x = this.anchor.x + this.ringOffset.x;
    this.ring.position.z = this.anchor.z + this.ringOffset.z;
    this.time += dt;
    const pulse = this.pulseSpeed > 0 ? 0.5 + 0.5 * Math.sin(this.time * this.pulseSpeed) : 1;
    this.current.copy(this.color).multiplyScalar(0.75 + 0.25 * pulse);
    renderer.getDrawingBufferSize(this.resolution);
    const px = this.width * renderer.getPixelRatio();
    this.hullMaterials[0].uniforms.uWidth.value = px + 2 * renderer.getPixelRatio();
    this.hullMaterials[1].uniforms.uWidth.value = px;
    const ru = this.ring.material.uniforms;
    ru.uTime.value = this.time;
    ru.uPulse.value = pulse;
    for (const s of this.sprites) s.userData.sprite.setOutline(this.current);
  }
}
