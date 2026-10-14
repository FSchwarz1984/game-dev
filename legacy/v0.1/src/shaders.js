/* =====================================================================
   SHADERS — GLSL ES 3.00 for the deferred 2.5D pixel pipeline.
   World: X right (east), Y down-screen (south), Z up. The camera is a
   45° oblique orthographic view: screen = (X, Y−Z); depth = Y+Z.
   G-buffer: G0 albedo+material · G1 normal+emission · G2 nearness,
   wetness, flags, occlusion · depth. Lighting is banded and dithered so
   it stays pixel art; shadows come from a real sun shadow map.
   ===================================================================== */
"use strict";
const SH = {};
SH.COMMON = `
uniform mat4 uVP; uniform mat4 uLVP;
uniform vec2 uCam; uniform vec2 uLow; uniform float uTime;
uniform vec3 uSunDir; uniform vec3 uSunCol; uniform vec3 uSkyCol; uniform vec3 uGndCol;
uniform vec3 uWind;            // xy direction, z strength 0..1
uniform sampler2D uNear;       // world nearness: r near, g trail wear, b wet, a far-tint override
uniform vec4 uNearR;           // x0, y0, 1/w, 1/h (world px)
uniform sampler2D uHgt;        // world height (r16f / encoded) for water & mist
uniform vec4 uHgtR;
const vec3 VCAM = vec3(0., .70710678, .70710678); // toward the camera
float h12(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float vn(vec2 p){ vec2 i=floor(p),f=fract(p); vec2 u=f*f*(3.-2.*f); return mix(mix(h12(i),h12(i+vec2(1,0)),u.x),mix(h12(i+vec2(0,1)),h12(i+vec2(1,1)),u.x),u.y); }
float fbm(vec2 p){ return vn(p)*.5+vn(p*2.03+7.1)*.27+vn(p*4.11+3.7)*.15+vn(p*8.3+1.3)*.08; }
float bayer4(vec2 p){ ivec2 i=ivec2(mod(p,4.)); int k=i.x+i.y*4; float m[16]=float[16](0.,8.,2.,10.,12.,4.,14.,6.,3.,11.,1.,9.,15.,7.,13.,5.); return (m[k]+.5)/16.; }
vec4 nearAt(vec2 xy){ vec2 uv=(xy-uNearR.xy)*uNearR.zw; if(uv.x<0.||uv.y<0.||uv.x>1.||uv.y>1.) return vec4(0.,0.,0.,1.); return texture(uNear,uv); }
float hgtAt(vec2 xy){ return texture(uHgt,(xy-uHgtR.xy)*uHgtR.zw).r; }
float lum(vec3 c){ return dot(c,vec3(.299,.587,.114)); }
vec3 hsv2rgb(vec3 c){ vec3 p=abs(fract(c.xxx+vec3(1.,2./3.,1./3.))*6.-3.); return c.z*mix(vec3(1.),clamp(p-1.,0.,1.),c.y); }
// camera-space sprite normal → world
vec3 spriteN(vec3 n){ return normalize(vec3(n.x, (n.z-n.y)*.70710678, (n.z+n.y)*.70710678)); }
float depthOf(float yz){ return -(yz-uCam.y-200.)/1200.; }   // NDC depth for a given Y+Z
`;

/* ---------------- terrain: world-space procedural pixel texturing ---------------- */
SH.terrainVS = `
layout(location=0) in vec3 aP; layout(location=1) in vec3 aN; layout(location=2) in vec4 aM;
out vec3 vW; out vec3 vN; out vec4 vM;
void main(){ vW=aP; vN=aN; vM=aM; gl_Position=uVP*vec4(aP,1.); }`;
SH.terrainFS = `
in vec3 vW; in vec3 vN; in vec4 vM;
uniform sampler2D uMat;   // per 4px cell: r material, g moisture/variant, b baked AO, a road/feature mask
uniform vec4 uMatR;
uniform sampler2D uWat;   // per cell: r water surface height/512, g flow x, b flow y, a water mask
layout(location=0) out vec4 o0; layout(location=1) out vec4 o1; layout(location=2) out vec4 o2;
vec3 hx(float h){ return vec3(floor(h/65536.),mod(floor(h/256.),256.),mod(h,256.))/255.; }
vec4 matAt(vec2 xy){ return texture(uMat,(xy-uMatR.xy)*uMatR.zw); }
vec3 pick(float r, vec3 a, vec3 b, vec3 c, float pa, float pb){ return r<pa?a:(r<pa+pb?b:c); }
// ---- ground materials (ids match the world painter)
// 1 grass  2 forest floor  3 rock  4 path  5 river bed  6 moss  7 stone paving (ishidatami)  8 gravel/sand  9 mud  10 rail ballast
vec3 grassCol(vec2 P, vec2 W, float moist, out vec3 nb, out float mat){
  // painted, not noisy: big meadow patches → clumps of a few pixels → sparse blade highlights and crevices
  float big=fbm(W*.0055), mid=fbm(W*.022+3.), clump=vn(P*.2)*.6+vn(P*.47+5.)*.4, r=h12(P);
  vec3 d0=hx(2770482.), d1=hx(3430959.), m0=hx(4878898.), m1=hx(5997622.), l0=hx(8034882.), l1=hx(9677650.), dry=hx(8486985.), olive=hx(6977347.);
  float hue=smoothstep(.35,.75,big);
  vec3 dark=mix(d0,d1,hue), midc=mix(m0,m1,hue), lite=mix(l0,l1,hue);
  float wv=sin(dot(W,uWind.xy)*.04-uTime*(1.1+uWind.z*1.5)+fbm(W*.01)*6.)*.5+.5;
  float t=mid*.45+clump*.55+(wv-.5)*.12*(.4+uWind.z);
  vec3 c = t<.4?dark:(t<.62?midc:lite);
  // blade highlights only on the lit tops of clumps, crevices only in the hollows
  float blade=step(.84,h12(floor(P/vec2(1.,2.))+.3));
  if(t>.5 && blade>.5) c=mix(lite,hx(11058282.),.45+wv*.3*uWind.z);
  if(t<.45 && r<.07) c=dark*.82;
  c=mix(c,mix(dry,olive,mid),smoothstep(.6,.82,big+(1.-moist)*.28)*.6);
  float fl=h12(floor(P/2.)+.7);
  if(fl>.9985) c = h12(P+3.)<.33?hx(15527132.):(h12(P+3.)<.66?hx(15127386.):hx(9081564.));
  nb=vec3((clump-.5)*.5,(t-.5)*.8+blade*.2,1.); mat=1.;
  return c;
}
vec3 floorCol(vec2 P, vec2 W, out vec3 nb, out float mat){ // cedar forest floor: needles, leaf litter, roots
  float big=fbm(W*.012), r=h12(P), r2=h12(P+3.3);
  vec3 a=hx(5129276.), b=hx(6576437.), c2=hx(3878442.), nd=hx(8148528.), lf=hx(9131854.);
  vec3 c=pick(r*.6+big*.4, c2, a, b, .32, .48);
  float needle=step(.86,h12(floor(vec2(P.x+floor(P.y/3.)*2.,P.y)/vec2(3.,1.))+.1));
  if(needle>.5) c=mix(c,nd,.75);
  if(r2>.985) c=lf; if(r2<.006) c=hx(7368816.);
  nb=vec3((r-.5)*.5,(r2-.5)*.5,1.); mat=2.;
  return c;
}
vec3 rockCol(vec2 P, vec3 W, vec3 n, out vec3 nb, out float mat){ // cliff faces: strata, cracks, wet streaks
  vec2 q=vec2(abs(n.x)>.5?W.y:W.x, W.z);
  float band=floor(q.y/5.+fbm(vec2(q.x*.05,0.))*2.); float bk=h12(vec2(band,floor(q.x/9.)));
  vec3 c=mix(hx(7106933.),hx(6052453.),step(.5,bk)); float r=h12(P);
  c*= r<.12?.85:(r>.9?1.1:1.);
  float crack=step(.93,h12(vec2(floor(q.x),floor(q.y/3.))));
  c=mix(c,c*.55,crack);
  float streak=smoothstep(.6,.8,vn(vec2(q.x*.25,q.y*.02)));
  c=mix(c,c*vec3(.72,.78,.8),streak*.6);
  nb=vec3((r-.5)*.6,(bk-.5)*.4+(crack>.5?-.6:0.),1.); mat=3.;
  return c;
}
vec3 pathCol(vec2 P, vec2 W, out vec3 nb, out float mat){ // trodden earth of the old road
  float r=h12(P), big=fbm(W*.03);
  vec3 c=pick(r*.5+big*.5,hx(7826763.),hx(9142624.),hx(10392698.),.3,.45);
  if(h12(floor(P/2.)+.4)>.975) c=hx(9145227.);
  nb=vec3((r-.5)*.3,0.,1.); mat=4.;
  return c;
}
vec3 pavingCol(vec2 P, vec2 W, out vec3 nb, out float mat){ // 石畳: irregular flat stones, moss in the joints
  vec2 g=W/vec2(9.,6.5); vec2 id=floor(g+vec2(step(1.,mod(floor(g.y),2.))*.5,0.)); vec2 f=fract(g+vec2(step(1.,mod(floor(g.y),2.))*.5,0.));
  float jit=h12(id)*.3; float edge=min(min(f.x,1.-f.x)*9.,min(f.y,1.-f.y)*6.5);
  float stone=step(1.2+jit*2.,edge);
  vec3 sc=mix(hx(8420736.),hx(9934739.),h12(id+.5)); sc*= .92+h12(P)*.1;
  vec3 joint=mix(hx(4876073.),hx(3093553.),step(.5,h12(P)));
  vec3 c=mix(joint,sc,stone);
  nb=vec3(0.,(stone-.5)*.5,1.); mat=stone>.5?7.:9.;
  return c;
}
void main(){
  vec3 W=vW; vec3 n=normalize(vN);
  vec2 P=floor(vec2(W.x, W.y-W.z)+.5);            // screen-locked pixel coordinate: crisp on every slope
  vec4 M=matAt(W.xy+vec2(vn(P*.21)-.5,vn(P*.21+9.)-.5)*3.); // jittered lookup = ragged material borders
  float id=floor(M.r*255.+.5), moist=M.g, ao=M.b;
  vec4 NR=nearAt(W.xy);
  float wear=NR.g;
  vec3 nb=vec3(0.,0.,1.); float mat=1.; vec3 c;
  bool cliff=n.z<.55;
  if(cliff){ c=rockCol(P,W,n,nb,mat);
    // grass lip along the top of a cliff face
    float top=hgtAt(W.xy+vec2(0.,-1.5))-W.z; if(top<3.+h12(vec2(P.x,0.))*3. && top>-.5){ vec3 b; float m; c=grassCol(P,W.xy,moist,b,m)*.9; mat=1.; }
  }
  else if(id<1.5) c=grassCol(P,W.xy,moist,nb,mat);
  else if(id<2.5) c=floorCol(P,W.xy,nb,mat);
  else if(id<3.5) c=rockCol(P,W,vec3(0.,1.,0.),nb,mat);
  else if(id<4.5) c=pathCol(P,W.xy,nb,mat);
  else if(id<5.5){ float r=h12(P), r2=h12(floor(P/2.)+.3); c=pick(r2,hx(7896434.),hx(9409666.),hx(6116182.),.4,.35); if(r>.92) c=hx(11119016.); nb=vec3((r-.5)*.6,(r2-.5)*.6,1.); mat=5.; }
  else if(id<6.5){ float r=h12(P), big=fbm(W.xy*.03); c=pick(r*.4+big*.6,hx(3955754.),hx(4746288.),hx(5799994.),.35,.45); if(h12(P+2.)>.985) c=hx(10135648.); nb=vec3((r-.5)*.5,(big-.5)*.5,1.); mat=9.; }
  else if(id<7.5) c=pavingCol(P,W.xy,nb,mat);
  else if(id<8.5){ float r=h12(P), r2=h12(floor(P/2.)); c=pick(r,hx(10196340.),hx(8749918.),hx(11777931.),.45,.3); if(r2>.9) c=hx(7366503.); nb=vec3((r-.5)*.8,(r2-.5)*.8,1.); mat=8.; }
  else if(id<9.5){ float r=h12(P); c=mix(hx(3683879.),hx(4602669.),r); nb=vec3(0.,0.,1.); mat=2.; }
  else { float r=h12(P); vec2 q=fract(W.xy/vec2(1.,6.)); c=mix(hx(6974576.),hx(8487302.),r); if(q.y<.3) c=hx(5389622.); nb=vec3((r-.5)*.7,0.,1.); mat=8.; }
  // trail wear: grass and floor give way to trodden earth along the lines she walks
  if(!cliff && (id<2.5) ){ float w=wear*1.25-(h12(P)*.45+vn(P*.3)*.3); if(w>.2){ vec3 b; float m; vec3 pc=pathCol(P,W.xy,b,m); c=mix(c,pc,smoothstep(.2,.42,w)); if(w>.32){ mat=4.; nb=b; } } }
  // under water: caustic light on a shallow bed; wet darkening at the water's edge
  vec4 WT=texture(uWat,(W.xy-uMatR.xy)*uMatR.zw); float wl=WT.r*512.-64.;
  float under=wl-W.z;
  if(WT.a>.5 && under>.0){ c*=mix(vec3(.82,.9,.92),vec3(.5,.66,.72),clamp(under/18.,0.,1.)); }
  else if(WT.a>.5 && under>-3.){ c*=.78; }
  // baked occlusion from the heightfield (hollows, cliff feet)
  c*=mix(.6,1.,ao);
  vec3 N=normalize(n+vec3(nb.x,-nb.y*.0,0.)*.18+vec3(0.,nb.y*.12,0.));
  o0=vec4(c, mat/255.);
  o1=vec4(N*.5+.5, 0.);
  o2=vec4(NR.r, max(NR.b, (WT.a>.5&&under>-4.)?.6:0.), mat<1.5?.35:0., 1.);
}`;

/* ---------------- sprites: instanced billboards with normal + bulge maps ---------------- */
SH.spriteVS = `
layout(location=0) in vec2 aQ;           // 0..1 quad
layout(location=1) in vec4 iP;           // X, Y, Z (base), sway
layout(location=2) in vec4 iS;           // w, h, ax, ay  (px)
layout(location=3) in vec4 iUV;          // u0 v0 u1 v1
layout(location=4) in vec4 iT;           // tint rgb, flash
layout(location=5) in vec4 iF;           // flags: x = flip, y = shadow caster, z = bulge scale, w = near override (-1 none)
uniform float uShadow; uniform float uMargin;
out vec2 vUV; out vec2 vPx; flat out vec4 vP; flat out vec4 vS; flat out vec4 vUVr; flat out vec4 vT; flat out vec4 vF; out float vH;
void main(){
  float m=iP.w>0.?uMargin:0.;
  vec2 px=vec2(mix(-m,iS.x+m,aQ.x), aQ.y*iS.y);          // sprite pixel coords (y down from the top)
  float hx=px.x-iS.z, hz=iS.w-px.y;                        // offset from the anchor: right, up
  vec3 w;
  if(uShadow>.5){ vec2 L=normalize(uSunDir.xy+vec2(1e-4)); vec2 p=vec2(-L.y,L.x); w=vec3(iP.xy+p*hx, iP.z+hz); }
  else w=vec3(iP.x+hx, iP.y, iP.z+hz);
  vPx=px; vH=hz; vP=iP; vS=iS; vUVr=iUV; vT=iT; vF=iF;
  vUV=vec2(0.);
  gl_Position=(uShadow>.5?uLVP:uVP)*vec4(w,1.);
}`;
SH.spriteFS = `
in vec2 vUV; in vec2 vPx; flat in vec4 vP; flat in vec4 vS; flat in vec4 vUVr; flat in vec4 vT; flat in vec4 vF; in float vH;
uniform sampler2D uAlb; uniform sampler2D uNrm; uniform vec2 uAtlas; uniform float uShadow;
layout(location=0) out vec4 o0; layout(location=1) out vec4 o1; layout(location=2) out vec4 o2;
void main(){
  vec2 px=floor(vPx);
  // wind: whole-pixel shifts per row, stronger toward the top; clumps breathe on their own phase
  if(vP.w>0.){
    float hgt=clamp((vS.w-px.y)/max(vS.y,1.),0.,1.);
    float ph=vP.x*.031+vP.y*.017;
    float s=sin(uTime*1.3+ph)*.6+sin(uTime*2.1+ph*1.7+px.y*.05)*.3+sin(uTime*.37+ph*3.)*.4;
    float gust=uWind.z*(.6+.4*sin(uTime*.5+vP.x*.01));
    float off=(s*.5+uWind.x*gust*1.2)*vP.w*pow(hgt,1.6);
    px.x-=floor(off+.5);
  }
  if(px.x<0.||px.x>=vS.x||px.y<0.||px.y>=vS.y) discard;
  vec2 tx=vec2(vF.x>.5? vS.x-1.-px.x : px.x, px.y)+.5;
  vec2 uv=vec2(mix(vUVr.x,vUVr.z,tx.x/vS.x), mix(vUVr.y,vUVr.w,tx.y/vS.y));
  vec4 a=texture(uAlb,uv); if(a.a<.5) discard;
  vec4 nr=texture(uNrm,uv);
  float matb=floor(nr.a*255.+.5); float mat=mod(matb,32.), emi=floor(matb/32.)/7.;
  if(uShadow>.5){ o0=vec4(mat==6.||mat==15.||mat==19.?1.:0.,0.,0.,1.); gl_FragDepth=gl_FragCoord.z; return; }
  vec3 ns=vec3(nr.x*2.-1., nr.y*2.-1., 0.); if(vF.x>.5) ns.x=-ns.x; ns.z=sqrt(max(0.,1.-dot(ns.xy,ns.xy)));
  vec3 N=spriteN(ns);
  float bulge=nr.z*63.75*vF.z;
  float zz=vP.z+(vS.w-px.y-.5);
  gl_FragDepth=clamp((depthOf(vP.y+zz+bulge+.5))*.5+.5,0.,1.);
  vec4 NR=nearAt(vP.xy);
  float near=vF.w>=0.?vF.w:NR.r;
  vec3 col=a.rgb*vT.rgb; col=mix(col,vec3(1.,.97,.9),vT.a);
  float trans=(mat==6.||mat==15.||mat==16.||mat==13.)?1.:0.;
  o0=vec4(col, mat/255.);
  o1=vec4(N*.5+.5, emi);
  o2=vec4(near, NR.b*.6, trans, 1.);
}`;

/* ---------------- grass tufts (instanced, into the G-buffer) ---------------- */
SH.grassVS = `
layout(location=0) in vec2 aQ;
layout(location=1) in vec4 iP;   // X Y Z variant
layout(location=2) in vec4 iS;   // phase, tone, scale, near
uniform vec4 uBend[6]; uniform float uN; uniform vec2 uTS;  // tuft size
out vec2 vPx; flat out vec4 vP; flat out vec4 vS; out float vBend;
void main(){
  vec2 px=vec2(aQ.x*(uTS.x+4.)-2., aQ.y*uTS.y);
  float hz=uTS.y-px.y;
  vec3 w=vec3(iP.x+px.x-uTS.x*.5, iP.y, iP.z+hz);
  float b=0.; for(int i=0;i<6;i++){ vec2 d=iP.xy-uBend[i].xy; float dl=length(d); float k=clamp(1.-dl/uBend[i].z,0.,1.)*uBend[i].w; b+=k*sign(d.x+.001)*3.; }
  vBend=b; vPx=px; vP=iP; vS=iS;
  gl_Position=uVP*vec4(w,1.);
}`;
SH.grassFS = `
in vec2 vPx; flat in vec4 vP; flat in vec4 vS; in float vBend;
uniform sampler2D uTuft; uniform float uN; uniform vec2 uTS;
layout(location=0) out vec4 o0; layout(location=1) out vec4 o1; layout(location=2) out vec4 o2;
vec3 hx(float h){ return vec3(floor(h/65536.),mod(floor(h/256.),256.),mod(h,256.))/255.; }
void main(){
  vec2 px=floor(vPx);
  float hgt=clamp((uTS.y-px.y)/uTS.y,0.,1.);
  float ph=vS.x+vP.x*.07+vP.y*.05;
  float wv=sin(dot(vP.xy,uWind.xy)*.045-uTime*(1.2+uWind.z*1.6))*.5+.5;
  float off=(sin(uTime*2.3+ph)*.5+uWind.x*uWind.z*1.3+wv*uWind.z*1.2)*pow(hgt,1.3)*1.2+vBend*hgt;
  px.x-=floor(off+.5);
  if(px.x<0.||px.x>=uTS.x) discard;
  vec2 uv=vec2((px.x+.5)/uTS.x, (vP.w*uTS.y+px.y+.5)/(uTS.y*uN));
  vec4 t=texture(uTuft,uv); if(t.a<.5) discard;
  vec3 col;
  if(t.r>.9&&t.g<.2){ float f=fract(vS.y*13.7+vP.x*.11); col=f<.3?hx(15527132.):(f<.55?hx(15127386.):(f<.8?hx(14918053.):hx(9081564.))); }
  else { float big=vn(vP.xy*.0065); vec3 dark=mix(hx(2770482.),hx(3430959.),big), mid=mix(hx(4878898.),hx(5997622.),big), lite=mix(hx(8034882.),hx(9677650.),big);
    col=t.r<.4?dark:(t.r<.75?mid:lite); col*=.92+vS.y*.16; col=mix(col,hx(8551241.),vS.z*.0); }
  float zz=vP.z+(uTS.y-px.y-.5);
  gl_FragDepth=clamp(depthOf(vP.y+zz+1.)*.5+.5,0.,1.);
  vec4 NR=nearAt(vP.xy);
  o0=vec4(col, 15./255.);
  o1=vec4(normalize(vec3((t.r-.5)*.3,.35,.95))*.5+.5, 0.);
  o2=vec4(NR.r, NR.b*.5, 1., 1.);
}`;

/* ---------------- shadow-pass terrain ---------------- */
SH.depthVS = `layout(location=0) in vec3 aP; void main(){ gl_Position=uLVP*vec4(aP,1.); }`;
SH.depthFS = `layout(location=0) out vec4 o0; void main(){ o0=vec4(0.,0.,0.,1.); }`;

/* ---------------- fullscreen ---------------- */
SH.fsVS = `out vec2 vUV; void main(){ vec2 p=vec2((gl_VertexID<<1)&2, gl_VertexID&2); vUV=p; gl_Position=vec4(p*2.-1.,0.,1.); }`;

/* ---------------- lighting ---------------- */
SH.lightFS = `
in vec2 vUV;
uniform sampler2D uG0; uniform sampler2D uG1; uniform sampler2D uG2; uniform sampler2D uDep;
uniform highp sampler2DShadow uShadowM; uniform sampler2D uShadowC; uniform sampler2D uAO;
uniform vec4 uLP[32]; uniform vec4 uLC[32]; uniform int uNL;
uniform vec4 uFogC; uniform vec4 uMist;   // mist: rgb, density
uniform float uCloud; uniform float uShafts; uniform vec3 uFar; uniform float uRain; uniform float uNight; uniform float uFarWave;
layout(location=0) out vec4 oC;
vec3 worldAt(vec2 frag, float d){ float yz=uCam.y+200.-(d*2.-1.)*1200.; float ymz=uCam.y+(uLow.y*.5-frag.y); float X=uCam.x+(frag.x-uLow.x*.5); return vec3(X,(ymz+yz)*.5,(yz-ymz)*.5); }
float shadowAt(vec3 P, vec3 N){
  vec4 lp=uLVP*vec4(P+N*1.2,1.); vec3 sc=lp.xyz*.5+.5;
  if(sc.x<0.||sc.x>1.||sc.y<0.||sc.y>1.||sc.z>1.) return 1.;
  float b=.0012; vec2 tx=1./vec2(textureSize(uShadowM,0));
  float s=texture(uShadowM,vec3(sc.xy,sc.z-b))*.4;
  s+=texture(uShadowM,vec3(sc.xy+vec2(tx.x,0.),sc.z-b))*.15+texture(uShadowM,vec3(sc.xy-vec2(tx.x,0.),sc.z-b))*.15;
  s+=texture(uShadowM,vec3(sc.xy+vec2(0.,tx.y),sc.z-b))*.15+texture(uShadowM,vec3(sc.xy-vec2(0.,tx.y),sc.z-b))*.15;
  return smoothstep(.3,.7,s);
}
float leafy(vec3 P){ vec4 lp=uLVP*vec4(P,1.); vec2 sc=lp.xy*.5+.5; return texture(uShadowC,sc).r; }
float clouds(vec3 P){ vec2 q=(P.xy-uSunDir.xy/max(uSunDir.z,.2)*P.z)*.0016+uWind.xy*uTime*.006; float c=fbm(q*1.3)+fbm(q*3.1+5.)*.35; return 1.-smoothstep(.55,.72,c*.85)*uCloud; }
float band(float v, vec2 f){ float d=bayer4(f)-.5; return floor(clamp(v,0.,1.)*4.+.5+d*.22)/4.; }
void main(){
  vec2 f=gl_FragCoord.xy;
  vec4 g0=texelFetch(uG0,ivec2(f),0), g1=texelFetch(uG1,ivec2(f),0), g2=texelFetch(uG2,ivec2(f),0); float d=texelFetch(uDep,ivec2(f),0).r;
  float mat=floor(g0.a*255.+.5);
  if(mat<.5){ oC=vec4(uFogC.rgb*.6,1.); return; }
  vec3 alb=g0.rgb, N=normalize(g1.xyz*2.-1.), P=worldAt(f,d);
  float near=g2.r, wet=g2.g, trans=g2.b, ao=g2.a*texelFetch(uAO,ivec2(f),0).r;
  if(uFarWave>-9000.){ float k=smoothstep(-6.,30.,P.y-uFarWave+(vn(P.xy*.05+uTime)-.5)*24.); near=min(near,mix(1.,.06,k)); }
  vec3 L=uSunDir;
  // ---- sun & sky
  float vis=shadowAt(P,N);
  float lf=leafy(P);
  if(vis<.99 && lf>.5){ // light leaking through the canopy: sun-flecks that sway with the leaves
    vec2 q=(P.xy-L.xy/max(L.z,.25)*P.z)*.11; float sw=sin(uTime*.9+q.y*.5)*.25*(.4+uWind.z);
    float n=vn(q+vec2(sw,uTime*.03))*.6+vn(q*2.3+vec2(-uTime*.05,sw*1.4)+9.)*.4; vis=max(vis, smoothstep(.62,.66,n)*.85);
  }
  vis*=clouds(P);
  float wrap=(mat==10.||mat==11.||mat==12.)?.45:(mat==6.||mat==15.)?.3:.12;
  vec3 Ls=normalize(vec3(L.xy,max(L.z,.62)));   // shade as if the sun stood higher; shadows keep the true low sun
  float ndl=(dot(N,Ls)+wrap)/(1.+wrap);
  float diff=band(ndl*vis,f);
  vec3 amb=mix(uGndCol,uSkyCol,N.z*.5+.5)*mix(.55,1.,ao);
  vec3 col=alb*(amb+uSunCol*diff);
  // light through leaves and paper when the sun is behind them
  if(trans>.5){ float back=clamp(-dot(N,L)*.6+.4,0.,1.)*vis; col+=alb*uSunCol*back*.45*vec3(1.,1.05,.7); }
  // glossy things: water-slick stone, lacquer, metal, wet ground
  vec3 H=normalize(L+VCAM); float spec=pow(max(dot(N,H),0.),mat==14.?40.:mat==21.?60.:24.);
  float gloss=(mat==14.?.7:mat==21.?.8:mat==22.?1.:0.)+wet*.55;
  col+=uSunCol*step(.55,spec)*gloss*vis*.6;
  col*=1.-wet*.18;
  // ---- point lights (lanterns, fireflies, her glow), banded
  vec3 pl=vec3(0.);
  for(int i=0;i<32;i++){ if(i>=uNL) break; vec3 dl=uLP[i].xyz-P; float dist=length(dl); float a=clamp(1.-dist/uLP[i].w,0.,1.); a*=a;
    float nl=max(dot(N,dl/max(dist,1e-3)),0.)*.6+.4; pl+=uLC[i].rgb*floor(a*nl*5.+bayer4(f))/5.; }
  col+=alb*pl;
  col+=alb*g1.a*3.2;   // emission
  // ---- outline: a darker ring on the near side of a silhouette
  float dn=0.; for(int k=0;k<4;k++){ ivec2 o=ivec2(k==0?1:k==1?-1:0, k==2?1:k==3?-1:0); float d2=texelFetch(uDep,ivec2(f)+o,0).r; dn=max(dn,d2-d); }
  if(dn>.012) col*=mix(vec3(.5,.48,.58),vec3(1.),.15);
  // ---- mist: a thin veil everywhere, thick in the hollows, lit where the sun reaches it; sun-shafts through it
  float gz=hgtAt(P.xy);
  float valley=clamp((200.-P.z)/220.,0.,1.);
  float wisp=.6+.4*fbm(P.xy*.006+vec2(uTime*.012,uTime*.004));
  float mist=uMist.a*(.32+valley*.68)*wisp*clamp(1.-(P.z-gz)/90.,.5,1.);
  vec3 mistC=uMist.rgb*(.62+.38*vis);
  if(uShafts>0.){ float acc=0.; float j=bayer4(f);
    for(int k=0;k<12;k++){ float t=(float(k)+j)*6.; vec3 S=P+VCAM*t; float sv=shadowAt(S,vec3(0.,0.,1.)); acc+=sv*clamp(1.-(S.z-gz)/80.,0.,1.); }
    col+=uSunCol*vec3(1.,.9,.72)*floor(acc/12.*5.+bayer4(f)*.7)/5.*uShafts*uMist.a*.22; }
  col=mix(col,mistC,clamp(mist,0.,.8));
  // ---- the Far: colour drains toward pale distance-blue
  float far=1.-near;
  vec3 farC=mix(uFar, uFar*1.25, lum(col));
  col=mix(col, mix(vec3(lum(col)),farC, .7)*1.1, smoothstep(.25,1.,far)*.92);
  oC=vec4(col,1.);
}`;

/* ---------------- water: refraction, SSR, foam, glints ---------------- */
SH.waterVS = `
layout(location=0) in vec3 aP; layout(location=1) in vec3 aF;   // flow xy, shore
out vec3 vW; out vec3 vF;
void main(){ vW=aP; vF=aF; gl_Position=uVP*vec4(aP,1.); }`;
SH.waterFS = `
in vec3 vW; in vec3 vF;
uniform sampler2D uScene; uniform sampler2D uDep; uniform vec3 uSkyTop; uniform vec3 uSkyHor; uniform float uRain;
layout(location=0) out vec4 oC;
void main(){
  vec2 f=gl_FragCoord.xy; float t=uTime;
  { float sd=texelFetch(uDep,ivec2(f),0).r; float syz=uCam.y+200.-(sd*2.-1.)*1200.; if(syz>vW.y+vW.z+.6) discard; }
  vec2 P=floor(vec2(vW.x, vW.y-vW.z)+.5);
  float gz=hgtAt(vW.xy); float dep=max(vW.z-gz,0.);
  vec2 fl=vF.xy; float spd=length(fl);
  // surface pattern: slow cross ripples on still water, combed streaks in the current
  vec2 fd=spd>.02?fl/spd:vec2(0.,1.);
  vec2 q=vec2(dot(P,vec2(fd.y,-fd.x)),dot(P,fd));
  float still=1.-smoothstep(.05,.4,spd);
  float rip=vn(P*.09+vec2(t*.2,t*.13))*.6+vn(P*.21-vec2(t*.15,-t*.1)+3.)*.4;
  float streak=vn(vec2(q.x*.35,q.y*.06-t*(1.+spd*3.)))*.6+vn(vec2(q.x*.7+3.,q.y*.12-t*(1.6+spd*4.)))*.4;
  float pat=mix(streak,rip,still);
  // refraction
  vec2 off=(vec2(rip,vn(P*.13+t*.2))-.5)*vec2(2.,1.5)*clamp(dep*.3,0.,1.);
  vec3 under=texelFetch(uScene,ivec2(f+off),0).rgb;
  vec3 deepC=vec3(.06,.18,.2), midC=vec3(.12,.32,.32), shalC=vec3(.32,.5,.46);
  vec3 wc=dep<6.?mix(shalC,midC,dep/6.):mix(midC,deepC,clamp((dep-6.)/26.,0.,1.));
  wc*=uSkyCol*.9+uSunCol*.45+.05;
  float a=clamp(.2+dep*.05,0.,.88);
  vec3 col=mix(under,wc,a);
  // reflection: march up the column until something stands nearer than the water plane
  float yz=vW.y+vW.z; vec3 refl=mix(uSkyHor,uSkyTop,.4);
  float roff=floor((pat-.5)*3.*(1.+uRain*2.));
  for(int k=1;k<140;k++){ vec2 g=f+vec2(roff, float(k)*2.); if(g.y>=uLow.y-1.){ refl=mix(uSkyHor,uSkyTop,clamp(float(k)/140.,0.,1.)); break; }
    float d=texelFetch(uDep,ivec2(g),0).r; float syz=uCam.y+200.-(d*2.-1.)*1200.;
    if(syz>yz+1.){ refl=texelFetch(uScene,ivec2(g),0).rgb; break; } }
  float fres=.22+.3*smoothstep(4.,24.,dep);
  col=mix(col,refl*vec3(.85,.95,1.),fres*(.7+.5*pat));
  // highlights: crisp ripple crests, sun glints
  float crest=step(.72,pat)*step(pat,.76)*step(.5,h12(floor(P/3.)));
  col+=crest*(uSkyCol*.25+uSunCol*.25);
  float glint=step(.996,h12(P+floor(t*5.)))*step(.55,pat)*step(.3,uSunDir.z);
  col+=glint*uSunCol*1.6;
  // shore foam & white water
  float shore=vF.z; float lap=sin(t*1.4+fbm(P*.05)*8.)*.5+.5;
  float foam=step(.55,shore*(.6+lap*.5))*step(.4,vn(P*.25+vec2(t*.3,0.)));
  float rap=step(.85,spd*(.45+streak*.9))*step(.45,h12(P+floor(t*6.)));
  col=mix(col,vec3(.9,.95,.95)*(uSkyCol*.5+uSunCol*.6+.15),clamp(foam*.6+rap*.8,0.,1.));
  // rain rings
  if(uRain>0.){ vec2 cell=floor(P/7.); float ph=fract(h12(cell)+t*.9); vec2 c=(cell+.5+vec2(h12(cell+1.),h12(cell+2.))*.4)*7.; float r=length(P-c); col+=step(abs(r-ph*4.),.5)*(1.-ph)*uRain*.35*vec3(.8,.9,1.); }
  vec4 NR=nearAt(vW.xy); col=mix(col, mix(vec3(lum(col)),vec3(.6,.7,.86),.6)*1.1, smoothstep(.25,1.,1.-NR.r)*.9);
  oC=vec4(col,1.);
}`;

/* ---------------- the Far: ghosts of what went away ---------------- */
SH.ghostFS = `
in vec2 vUV; in vec2 vPx; flat in vec4 vP; flat in vec4 vS; flat in vec4 vUVr; flat in vec4 vT; flat in vec4 vF; in float vH;
uniform sampler2D uAlb; uniform float uAlpha; uniform vec3 uFarA; uniform vec3 uFarB;
layout(location=0) out vec4 oC;
void main(){
  vec2 px=floor(vPx);
  float wob=floor(sin(uTime*1.7+px.y*.21+vP.x*.01)*1.2*vT.a+.5); px.x-=wob;
  if(px.x<0.||px.x>=vS.x||px.y<0.||px.y>=vS.y) discard;
  vec2 tx=vec2(vF.x>.5? vS.x-1.-px.x : px.x, px.y)+.5;
  vec2 uv=vec2(mix(vUVr.x,vUVr.z,tx.x/vS.x), mix(vUVr.y,vUVr.w,tx.y/vS.y));
  vec4 a=texture(uAlb,uv); if(a.a<.5) discard;
  float l=lum(a.rgb); float hgt=px.y/vS.y;
  vec3 c=mix(uFarA,uFarB,smoothstep(.15,.85,l)); c=mix(c,uFarB*1.08,hgt*.35);   // paler toward the bottom, as if standing in haze
  float al=uAlpha*vT.r*(.75+.25*h12(px+floor(uTime*3.)));
  if(bayer4(gl_FragCoord.xy)>al) discard;
  oC=vec4(c,1.);
}`;

/* ---------------- particles (pixel squares) ---------------- */
SH.partVS = `
layout(location=0) in vec4 aP; layout(location=1) in vec4 aC;
out vec4 vC; flat out float vSz;
void main(){ vC=aC; vSz=aP.w; gl_Position=uVP*vec4(aP.xyz,1.); gl_Position.xy=(floor((gl_Position.xy*.5+.5)*uLow)+.5)/uLow*2.-1.; gl_PointSize=aP.w; }`;
SH.partFS = `in vec4 vC; flat in float vSz; layout(location=0) out vec4 oC; void main(){ if(vC.a<1. && bayer4(gl_FragCoord.xy)>vC.a) discard; oC=vec4(vC.rgb,1.); }`;
SH.partAddFS = `in vec4 vC; flat in float vSz; layout(location=0) out vec4 oC; void main(){ oC=vec4(vC.rgb*vC.a,1.); }`;

/* ---------------- glow cards (additive halos, light pools) ---------------- */
SH.glowVS = `
layout(location=0) in vec2 aQ;
layout(location=1) in vec4 iP;  // x y z kind
layout(location=2) in vec4 iS;  // w h phase -
layout(location=3) in vec4 iC;  // rgb intensity
out vec2 vQ; out vec4 vC; flat out float vK;
void main(){
  vec3 p=iP.w>1.5? vec3((aQ.x-.5)*iS.x,(aQ.y-.5)*iS.y,0.) : vec3((aQ.x-.5)*iS.x,0.,(aQ.y-.5)*iS.y);
  vQ=aQ*2.-1.; vC=iC; vK=iP.w;
  gl_Position=uVP*vec4(iP.xyz+p,1.); gl_Position.z=-1.;
}`;
SH.glowFS = `
in vec2 vQ; in vec4 vC; flat in float vK; layout(location=0) out vec4 oC;
void main(){ float d=length(vQ); float a=1.-smoothstep(0.,1.,d); a*=a; if(vK>2.5) a=smoothstep(.75,.88,d)*(1.-smoothstep(.9,1.,d));
  a=floor(a*vC.a*7.+bayer4(gl_FragCoord.xy))/7.; oC=vec4(vC.rgb*a,1.); }`;

/* ---------------- post ---------------- */
SH.copyFS = `in vec2 vUV; uniform sampler2D uTex; layout(location=0) out vec4 oC; void main(){ oC=texture(uTex,vUV); }`;
SH.brightFS = `in vec2 vUV; uniform sampler2D uTex; uniform vec2 uTx; uniform float uThr; layout(location=0) out vec4 oC;
void main(){ vec3 c=vec3(0); for(int i=0;i<4;i++){ vec2 o=vec2(float(i&1),float(i>>1))-.5; c+=texture(uTex,vUV+o*uTx).rgb; } c*=.25; float l=max(c.r,max(c.g,c.b)); oC=vec4(c*smoothstep(uThr,uThr+.4,l),1.); }`;
SH.blurFS = `in vec2 vUV; uniform sampler2D uTex; uniform vec2 uDir; layout(location=0) out vec4 oC;
void main(){ vec3 c=texture(uTex,vUV).rgb*.227027; c+=texture(uTex,vUV+uDir*1.3846).rgb*.316216; c+=texture(uTex,vUV-uDir*1.3846).rgb*.316216; c+=texture(uTex,vUV+uDir*3.2308).rgb*.07027; c+=texture(uTex,vUV-uDir*3.2308).rgb*.07027; oC=vec4(c,1.); }`;
SH.compFS = `
in vec2 vUV;
uniform sampler2D uLowT; uniform sampler2D uBloom;
uniform vec2 uLowS; uniform vec2 uOff; uniform float uScale; uniform vec2 uScr;
uniform vec3 uLift; uniform vec3 uGain; uniform float uSat; uniform float uBloomK; uniform float uVig; uniform float uGrain;
uniform vec4 uFade; uniform float uT; uniform vec3 uShT; uniform vec3 uHiT; uniform float uBox; uniform float uFarFx; uniform vec3 uFarTint; uniform float uExpo;
layout(location=0) out vec4 oC;
float hh(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
vec3 tone(vec3 c){ c*=uExpo; vec3 e=max(c-.82,0.); return min(c,.82)+.18*(1.-exp(-e/.18)); }
void main(){
  vec2 sp=gl_FragCoord.xy;
  // letterbox
  float bh=uBox*uScr.y*.11; if(sp.y<bh||sp.y>uScr.y-bh){ oC=vec4(0.,0.,0.,1.); return; }
  vec2 lp=sp/uScale+uOff+1.;
  // the Far shimmers at the edges of sight
  if(uFarFx>0.){ vec2 q=vUV-.5; float e=smoothstep(.15,.7,length(q))*uFarFx; lp.x+=floor(sin(lp.y*.3+uT*3.)*e*2.+.5); }
  vec2 uv=(floor(lp)+.5)/uLowS;
  vec3 c=texture(uLowT,uv).rgb;
  c+=texture(uBloom,lp/uLowS).rgb*uBloomK;
  c=tone(c);
  float l=dot(c,vec3(.299,.587,.114));
  c=mix(vec3(l),c,uSat);
  c=uLift+c*(uGain-uLift);
  float l2=dot(c,vec3(.299,.587,.114)); c+=uShT*(1.-smoothstep(0.,.5,l2))+uHiT*smoothstep(.45,1.,l2);
  if(uFarFx>0.){ vec2 q=vUV-.5; float e=smoothstep(.1,.75,length(q)*1.2)*uFarFx; c=mix(c,mix(vec3(l2),uFarTint,.65)*1.15,e*.85); }
  vec2 q=vUV-.5; c*=1.-dot(q,q)*uVig;
  c+=(hh(floor(sp/max(uScale,1.))+fract(uT)*91.)-.5)*uGrain;
  c=mix(c,uFade.rgb,uFade.a);
  oC=vec4(c,1.);
}`;
