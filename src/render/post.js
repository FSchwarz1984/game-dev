// Post chain (pmndrs/postprocessing): its EffectPass merges bloom, depth of field / tilt-shift,
// tone mapping, grading and vignette into ONE full-screen shader, which three's own
// EffectComposer + ShaderPass cannot do.
//   high: scene -> [SMAA(depth edges), DoF(half-res bokeh), bloom(8 mips), tone map, grade, vignette]
//   low:  scene -> [tilt-shift(half-res), bloom(4 mips), tone map, grade, vignette] -> [FXAA]
// Tone mapping is Khronos PBR Neutral: hue and saturation pass through untouched up to the
// highlights (ACES and AgX desaturate and shift hues; DQ3 HD-2D lost saturation that way).
// The UI is DOM and never passes through this chain.

import * as THREE from 'three';
import {
  EffectComposer, RenderPass, EffectPass, Effect, BlendFunction, KernelSize,
  BloomEffect, DepthOfFieldEffect, TiltShiftEffect, ToneMappingEffect, ToneMappingMode,
  VignetteEffect, FXAAEffect, SMAAEffect, SMAAPreset, EdgeDetectionMode,
} from 'postprocessing';

// Lift / gamma / gain and saturation, applied in display space after tone mapping.
const GRADE_FRAGMENT = /* glsl */ `
uniform vec3 gradeLift;
uniform vec3 gradeGamma;
uniform vec3 gradeGain;
uniform float gradeSaturation;
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec3 c = pow(max(inputColor.rgb, 0.0), vec3(1.0 / 2.2));
  c = gradeGain * (c + gradeLift * (1.0 - c));
  c = pow(max(c, 0.0), 1.0 / gradeGamma);
  c = mix(vec3(dot(c, vec3(0.2126, 0.7152, 0.0722))), c, gradeSaturation);
  outputColor = vec4(pow(max(c, 0.0), vec3(2.2)), inputColor.a);
}
`;

class GradeEffect extends Effect {
  constructor() {
    super('GradeEffect', GRADE_FRAGMENT, {
      blendFunction: BlendFunction.SRC,
      uniforms: new Map([
        ['gradeLift', new THREE.Uniform(new THREE.Vector3(0, 0, 0))],
        ['gradeGamma', new THREE.Uniform(new THREE.Vector3(1, 1, 1))],
        ['gradeGain', new THREE.Uniform(new THREE.Vector3(1, 1, 1))],
        ['gradeSaturation', new THREE.Uniform(1)],
      ]),
    });
  }

  apply({ lift, gamma, gain, saturation }) {
    this.uniforms.get('gradeLift').value.fromArray(lift);
    this.uniforms.get('gradeGamma').value.fromArray(gamma);
    this.uniforms.get('gradeGain').value.fromArray(gain);
    this.uniforms.get('gradeSaturation').value = saturation;
  }
}

const _ndc = new THREE.Vector3();

export class PostChain {
  constructor(renderer, scene, camera, tier, { dof = true } = {}) {
    this.renderer = renderer;
    this.camera = camera;
    this.dofEnabled = dof;
    this.focusTarget = new THREE.Vector3();
    this.preset = null;
    this.composer = new EffectComposer(renderer, { frameBufferType: THREE.HalfFloatType });
    this.composer.addPass(new RenderPass(scene, camera));
    this.effectPasses = [];
    this.build(tier);
  }

  build(tier) {
    for (const p of this.effectPasses) { this.composer.removePass(p); p.dispose(); }
    const camera = this.camera;
    this.tier = tier;
    this.dof = this.tilt = null;

    const effects = [];
    if (tier.aa === 'smaa') effects.push(new SMAAEffect({ preset: SMAAPreset.MEDIUM, edgeDetectionMode: EdgeDetectionMode.DEPTH }));
    if (this.dofEnabled && tier.dof === 'bokeh') {
      // Wide focus band: the playfield around the player stays sharp; far terraces and the
      // nearest foreground soften a little (DQ3 HD-2D was criticised for too much blur).
      this.dof = new DepthOfFieldEffect(camera, { focusRange: 26, bokehScale: 2.0, resolutionScale: 0.5 });
      this.dof.target = this.focusTarget;
      effects.push(this.dof);
    } else if (this.dofEnabled) {
      this.tilt = new TiltShiftEffect({ focusArea: 1.0, feather: 0.45, kernelSize: KernelSize.SMALL, resolutionScale: 0.5 });
      effects.push(this.tilt);
    }
    this.bloom = new BloomEffect({ mipmapBlur: true, luminanceThreshold: 1.0, luminanceSmoothing: 0.12, intensity: 0.6, radius: 0.62, levels: tier.bloomLevels });
    this.toneMapping = new ToneMappingEffect({ mode: ToneMappingMode.NEUTRAL });
    this.grade = new GradeEffect();
    this.vignette = new VignetteEffect({ offset: 0.38, darkness: 0.3 });
    effects.push(this.bloom, this.toneMapping, this.grade, this.vignette);

    this.effectPasses = [new EffectPass(camera, ...effects)];
    if (tier.aa === 'fxaa') {
      const fxaa = new FXAAEffect();
      fxaa.subpixelQuality = 0.35; // keep single-pixel art details crisp
      this.effectPasses.push(new EffectPass(camera, fxaa));
    }
    for (const p of this.effectPasses) this.composer.addPass(p);
    if (this.preset) this.applyPreset(this.preset);
  }

  applyPreset(p) {
    this.preset = p;
    this.renderer.toneMappingExposure = p.exposure;
    this.bloom.intensity = p.bloom;
    this.vignette.darkness = p.vignette;
    this.grade.apply(p.grade);
  }

  setSize(width, height) { this.composer.setSize(width, height); }

  /** focus: the player's position; keeps the DoF focus / tilt-shift band on her. */
  render(dt, focus) {
    this.focusTarget.copy(focus);
    if (this.tilt) {
      _ndc.copy(focus).project(this.camera);
      this.tilt.offset = _ndc.y;
    }
    this.composer.render(dt);
  }

  /** Full-screen passes this frame (render pass + effect passes), for the debug overlay. */
  describe() {
    const names = this.effectPasses.map(p => p.effects.map(e => e.name.replace('Effect', '')).join('+'));
    return ['Scene', ...names].join(' > ');
  }
}
