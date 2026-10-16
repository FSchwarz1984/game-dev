// Minimal PNG reader for the bake (Node): 8-bit RGBA or RGB, not interlaced (what the 3D terrain
// export writes, tools/world3d/w3terrain). Returns { w, h, data: Uint8Array RGBA }. Exact bytes: no
// colour management, no premultiplication (a browser canvas would do both).
import fs from 'node:fs';
import zlib from 'node:zlib';

export function readPNG(path) {
  const b = fs.readFileSync(path);
  if (b.readUInt32BE(0) !== 0x89504e47) throw new Error('not a PNG: ' + path);
  let o = 8, w = 0, h = 0, ct = 0, depth = 0, inter = 0;
  const idat = [];
  while (o < b.length) {
    const len = b.readUInt32BE(o), type = b.toString('ascii', o + 4, o + 8), body = b.subarray(o + 8, o + 8 + len);
    if (type === 'IHDR') { w = body.readUInt32BE(0); h = body.readUInt32BE(4); depth = body[8]; ct = body[9]; inter = body[12]; }
    else if (type === 'IDAT') idat.push(body);
    else if (type === 'IEND') break;
    o += 12 + len;
  }
  if (depth !== 8 || (ct !== 6 && ct !== 2) || inter) throw new Error(`unsupported PNG (depth ${depth}, colour type ${ct}, interlace ${inter}): ${path}`);
  const bpp = ct === 6 ? 4 : 3, stride = w * bpp;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const px = new Uint8Array(w * h * bpp);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = y * (stride + 1) + 1, dst = y * stride;
    for (let x = 0; x < stride; x++) {
      const v = raw[src + x];
      const a = x >= bpp ? px[dst + x - bpp] : 0, up = y > 0 ? px[dst - stride + x] : 0, c = x >= bpp && y > 0 ? px[dst - stride + x - bpp] : 0;
      let r;
      switch (f) {
        case 0: r = v; break;
        case 1: r = v + a; break;
        case 2: r = v + up; break;
        case 3: r = v + ((a + up) >> 1); break;
        case 4: { const p = a + up - c, pa = Math.abs(p - a), pb = Math.abs(p - up), pc = Math.abs(p - c); r = v + (pa <= pb && pa <= pc ? a : pb <= pc ? up : c); break; }
        default: throw new Error('bad PNG filter ' + f);
      }
      px[dst + x] = r & 255;
    }
  }
  if (bpp === 4) return { w, h, data: px };
  const out = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) { out[i * 4] = px[i * 3]; out[i * 4 + 1] = px[i * 3 + 1]; out[i * 4 + 2] = px[i * 3 + 2]; out[i * 4 + 3] = 255; }
  return { w, h, data: out };
}
