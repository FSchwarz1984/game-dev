/* =====================================================================
   gfx/gl — thin WebGL2 helpers: programs with uniform setters, meshes,
   per-instance buffers, textures (2D and arrays), MRT framebuffers and
   a draw-call counter. Ported from legacy/v0.1/src/gl.js as a module.
   ===================================================================== */

export class GLX {
  constructor(canvas, o = {}) {
    const gl = canvas.getContext('webgl2', {
      antialias: false, alpha: false, depth: true, stencil: false, premultipliedAlpha: false,
      preserveDrawingBuffer: !!o.preserve, powerPreference: 'high-performance',
    });
    if (!gl) throw new Error('WebGL2 is not available');
    this.gl = gl;
    this.hdr = !!gl.getExtension('EXT_color_buffer_float');
    gl.getExtension('EXT_color_buffer_half_float');
    this.floatLinear = !!gl.getExtension('OES_texture_float_linear');
    this.fsVAO = gl.createVertexArray();
    this.calls = 0;
    this.maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
  }
  compile(type, src, name) {
    const gl = this.gl, s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(s) || '', lines = src.split('\n');
      const m = /ERROR: \d+:(\d+)/.exec(log); const ln = m ? +m[1] : 0;
      console.error('[shader ' + name + ']', log, '\n' + lines.slice(Math.max(0, ln - 6), ln + 3).map((l, i) => (Math.max(0, ln - 6) + i + 1) + ': ' + l).join('\n'));
      throw new Error('shader compile failed: ' + name + '\n' + log);
    }
    return s;
  }
  prog(name, vs, fs) {
    const gl = this.gl, head = '#version 300 es\nprecision highp float;\nprecision highp int;\nprecision highp sampler2D;\nprecision highp sampler2DArray;\nprecision highp sampler2DShadow;\n';
    const p = gl.createProgram();
    gl.attachShader(p, this.compile(gl.VERTEX_SHADER, head + vs, name + '.vs'));
    gl.attachShader(p, this.compile(gl.FRAGMENT_SHADER, head + fs, name + '.fs'));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('link failed ' + name + ': ' + gl.getProgramInfoLog(p));
    const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); u[info.name.replace(/\[0\]$/, '')] = gl.getUniformLocation(p, info.name); }
    const X = this;
    return {
      p, u, name, unit: 0,
      use() { gl.useProgram(p); this.unit = 0; return this; },
      f(n, ...v) { const l = u[n]; if (l == null) return this; if (v.length === 1) gl.uniform1f(l, v[0]); else if (v.length === 2) gl.uniform2f(l, v[0], v[1]); else if (v.length === 3) gl.uniform3f(l, v[0], v[1], v[2]); else gl.uniform4f(l, v[0], v[1], v[2], v[3]); return this; },
      v(n, a) { const l = u[n]; if (l == null) return this; if (a.length === 2) gl.uniform2fv(l, a); else if (a.length === 3) gl.uniform3fv(l, a); else gl.uniform4fv(l, a); return this; },
      i(n, v) { const l = u[n]; if (l != null) gl.uniform1i(l, v); return this; },
      v4a(n, arr) { const l = u[n]; if (l != null) gl.uniform4fv(l, arr); return this; },
      m4(n, m) { const l = u[n]; if (l != null) gl.uniformMatrix4fv(l, false, m); return this; },
      t(n, tex, target) { const l = u[n]; if (l == null || !tex) return this; gl.activeTexture(gl.TEXTURE0 + this.unit); gl.bindTexture(target || gl.TEXTURE_2D, tex); gl.uniform1i(l, this.unit); this.unit++; return this; },
      ta(n, tex) { return this.t(n, tex, gl.TEXTURE_2D_ARRAY); },
      x: X,
    };
  }
  /** interleaved float mesh; layout [[name,size],...] → attribute locations in order */
  mesh(verts, layout, idx, mode, usage) {
    const gl = this.gl, X = this, vao = gl.createVertexArray(); gl.bindVertexArray(vao);
    const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb); gl.bufferData(gl.ARRAY_BUFFER, verts, usage || gl.STATIC_DRAW);
    const stride = layout.reduce((s, a) => s + a[1], 0) * 4; let off = 0;
    layout.forEach((a, i) => { gl.enableVertexAttribArray(i); gl.vertexAttribPointer(i, a[1], gl.FLOAT, false, stride, off); off += a[1] * 4; });
    let ib = null, count = verts.length / (stride / 4), itype = 0;
    if (idx) {
      ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib);
      let mx = 0; for (let i = 0; i < idx.length; i++) if (idx[i] > mx) mx = idx[i];
      const arr = mx > 65535 ? new Uint32Array(idx) : new Uint16Array(idx);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, arr, gl.STATIC_DRAW); count = idx.length; itype = mx > 65535 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
    }
    gl.bindVertexArray(null);
    return {
      vao, vb, ib, count, itype, mode: mode ?? gl.TRIANGLES, layout, stride,
      draw() { gl.bindVertexArray(vao); X.calls++; if (ib) gl.drawElements(this.mode, this.count, this.itype, 0); else gl.drawArrays(this.mode, 0, this.count); },
      drawInst(n) { if (n <= 0) return; gl.bindVertexArray(vao); X.calls++; if (ib) gl.drawElementsInstanced(this.mode, this.count, this.itype, 0, n); else gl.drawArraysInstanced(this.mode, 0, this.count, n); },
      free() { gl.deleteBuffer(vb); if (ib) gl.deleteBuffer(ib); gl.deleteVertexArray(vao); },
    };
  }
  /** per-instance attributes appended after the mesh layout */
  inst(mesh, layout, maxN) {
    const gl = this.gl; gl.bindVertexArray(mesh.vao);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    const fl = layout.reduce((s, a) => s + a[1], 0); gl.bufferData(gl.ARRAY_BUFFER, maxN * fl * 4, gl.DYNAMIC_DRAW);
    let loc = mesh.layout.length, off = 0;
    for (const a of layout) { gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, a[1], gl.FLOAT, false, fl * 4, off); gl.vertexAttribDivisor(loc, 1); off += a[1] * 4; loc++; }
    gl.bindVertexArray(null);
    return {
      buf: b, floats: fl, max: maxN, data: new Float32Array(maxN * fl), n: 0,
      upload(n = this.n, from = 0) { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferSubData(gl.ARRAY_BUFFER, from * fl * 4, this.data, from * fl, (n - from) * fl); },
    };
  }
  tex(w, h, data, o = {}) {
    const gl = this.gl, t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, o.ifmt || gl.RGBA8, w, h, 0, o.fmt || gl.RGBA, o.type || gl.UNSIGNED_BYTE, data);
    const f = o.linear ? gl.LINEAR : gl.NEAREST;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
    const wr = o.repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wr); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wr);
    return t;
  }
  texSub(t, x, y, w, h, data, o = {}) { const gl = this.gl; gl.bindTexture(gl.TEXTURE_2D, t); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1); gl.texSubImage2D(gl.TEXTURE_2D, 0, x, y, w, h, o.fmt || gl.RGBA, o.type || gl.UNSIGNED_BYTE, data); }
  /** image / canvas → texture (no premultiply, no colour conversion) */
  imgTex(img, o = {}) {
    const gl = this.gl, t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE); gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    const f = o.linear ? gl.LINEAR : gl.NEAREST;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.BROWSER_DEFAULT_WEBGL);
    return t;
  }
  texArray(w, h, layers, o = {}) {
    const gl = this.gl, t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D_ARRAY, t);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY, 1, o.ifmt || gl.RGBA8, w, h, layers);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  texArraySub(t, layer, x, y, w, h, data) {
    const gl = this.gl; gl.bindTexture(gl.TEXTURE_2D_ARRAY, t); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, x, y, layer, w, h, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
  }
  /** colors: [{ifmt, fmt, type, linear}]; depth: true | 'cmp' (shadow) | texture (shared) | null */
  fbo(w, h, colors, depth) {
    const gl = this.gl, fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    const tex = [], bufs = [];
    colors.forEach((c, i) => {
      const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, c.ifmt || gl.RGBA8, w, h, 0, c.fmt || gl.RGBA, c.type || gl.UNSIGNED_BYTE, null);
      const f = c.linear ? gl.LINEAR : gl.NEAREST;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t, 0); tex.push(t); bufs.push(gl.COLOR_ATTACHMENT0 + i);
    });
    let dt = null;
    if (depth === true || depth === 'cmp') {
      dt = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, dt);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT24, w, h, 0, gl.DEPTH_COMPONENT, gl.UNSIGNED_INT, null);
      const f = depth === 'cmp' ? gl.LINEAR : gl.NEAREST;
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      if (depth === 'cmp') { gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_MODE, gl.COMPARE_REF_TO_TEXTURE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_FUNC, gl.LEQUAL); }
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, dt, 0);
    } else if (depth) { dt = depth; gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, dt, 0); }
    if (bufs.length) gl.drawBuffers(bufs); else { gl.drawBuffers([gl.NONE]); gl.readBuffer(gl.NONE); }
    const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER); if (st !== gl.FRAMEBUFFER_COMPLETE) console.error('FBO incomplete', st.toString(16), w, h);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return {
      fb, tex, depth: dt, w, h, ownDepth: depth === true || depth === 'cmp',
      free() { gl.deleteFramebuffer(fb); tex.forEach(t => gl.deleteTexture(t)); if (this.ownDepth && dt) gl.deleteTexture(dt); },
    };
  }
  /** a framebuffer view onto existing colour textures (no depth) */
  view(texs, w, h) {
    const gl = this.gl, fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    texs.forEach((t, i) => gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t, 0));
    gl.drawBuffers(texs.map((_, i) => gl.COLOR_ATTACHMENT0 + i)); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { fb, tex: texs, w, h, free() { gl.deleteFramebuffer(fb); } };
  }
  bind(f) { const gl = this.gl; if (f) { gl.bindFramebuffer(gl.FRAMEBUFFER, f.fb); gl.viewport(0, 0, f.w, f.h); } else { gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight); } }
  tri() { const gl = this.gl; gl.bindVertexArray(this.fsVAO); this.calls++; gl.drawArrays(gl.TRIANGLES, 0, 3); }
}

/* ---------- mat4 (column-major) ---------- */
export const M4 = {
  ident() { const m = new Float32Array(16); m[0] = m[5] = m[10] = m[15] = 1; return m; },
  mul(a, b, o = new Float32Array(16)) { for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; },
  ortho(l, r, b, t, n, f, o = new Float32Array(16)) { o.fill(0); o[0] = 2 / (r - l); o[5] = 2 / (t - b); o[10] = -2 / (f - n); o[12] = -(r + l) / (r - l); o[13] = -(t + b) / (t - b); o[14] = -(f + n) / (f - n); o[15] = 1; return o; },
  lookAt(e, c, up, o = new Float32Array(16)) {
    let fx = c[0] - e[0], fy = c[1] - e[1], fz = c[2] - e[2]; let l = Math.hypot(fx, fy, fz); fx /= l; fy /= l; fz /= l;
    let sx = fy * up[2] - fz * up[1], sy = fz * up[0] - fx * up[2], sz = fx * up[1] - fy * up[0]; l = Math.hypot(sx, sy, sz); sx /= l; sy /= l; sz /= l;
    const ux = sy * fz - sz * fy, uy = sz * fx - sx * fz, uz = sx * fy - sy * fx;
    o[0] = sx; o[4] = sy; o[8] = sz; o[1] = ux; o[5] = uy; o[9] = uz; o[2] = -fx; o[6] = -fy; o[10] = -fz;
    o[12] = -(sx * e[0] + sy * e[1] + sz * e[2]); o[13] = -(ux * e[0] + uy * e[1] + uz * e[2]); o[14] = (fx * e[0] + fy * e[1] + fz * e[2]);
    o[3] = o[7] = o[11] = 0; o[15] = 1; return o;
  },
};
