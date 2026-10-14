/* =====================================================================
   gfx/shaders — GLSL ES 3.00 for the 2D deferred pixel pipeline.
   World px: X east, Y south, Z up (1 m = 20 px). The view is the 3/4
   oblique: screen = (X, Y − Z), depth key D = Y + Z (bigger = nearer).
   World-screen y grows downward; GL's gl_FragCoord.y grows upward, the
   vertex shaders flip. Native buffer: uLow (W, H), camera centre uCam.

   G-buffer: G0 albedo.rgb + material · G1 world normal + emission ·
   G2 far, wet, class bits, caster id · depth.
   class bits (G2.b*255): 1 foliage, 2 character, 4 ground, 8 water edge,
   16..112 character slot (slot*16 for slot 1..7).

   Ported from legacy/v0.1/src/shaders.js. Changes for the owner's
   critique: characters get their own stable light (no flecks, no
   banding, a floor, a fill and a rim); canopy flecks are soft and slow;
   dither is world-locked (no crawling); the Far is a pale, low-contrast
   haze look on any pixel; occluders that hide a character are drawn in
   a forward pass with the same lighting at reduced opacity.
   ===================================================================== */

export const COMMON = `
uniform vec2 uCam; uniform vec2 uLow; uniform float uTime;
uniform mat4 uLVP;
uniform vec3 uSunDir; uniform vec3 uShadeDir; uniform vec3 uSunCol; uniform vec3 uSkyCol; uniform vec3 uGndCol;
uniform vec3 uWind;
uniform vec2 uDith;
const float DR = 1600.; const float DOFF = 200.;
float h12(vec2 p){ vec3 p3=fract(vec3(p.xyx)*.1031); p3+=dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float vn(vec2 p){ vec2 i=floor(p),f=fract(p); vec2 u=f*f*(3.-2.*f); return mix(mix(h12(i),h12(i+vec2(1,0)),u.x),mix(h12(i+vec2(0,1)),h12(i+vec2(1,1)),u.x),u.y); }
float fbm(vec2 p){ return vn(p)*.5+vn(p*2.03+7.1)*.27+vn(p*4.11+3.7)*.15+vn(p*8.3+1.3)*.08; }
float bayer4(vec2 p){ ivec2 i=ivec2(mod(p,4.)); int k=i.x+i.y*4; float m[16]=float[16](0.,8.,2.,10.,12.,4.,14.,6.,3.,11.,1.,9.,15.,7.,13.,5.); return (m[k]+.5)/16.; }
float lum(vec3 c){ return dot(c,vec3(.299,.587,.114)); }
// world-screen position of a fragment (y down)
vec2 wsOf(vec2 frag){ return vec2(uCam.x-uLow.x*.5+frag.x, uCam.y+uLow.y*.5-frag.y); }
float ndcZ(float D){ return clamp(-(D-uCam.y-DOFF)/DR, -1., 1.); }
float fragZ(float D){ return ndcZ(D)*.5+.5; }
vec4 clipOf(vec2 ws){ return vec4((ws.x-uCam.x)*2./uLow.x, -(ws.y-uCam.y)*2./uLow.y, 0., 1.); }
// camera-space sprite normal (x right, y screen-up, z toward viewer) → world
vec3 spriteN(vec3 n){ return normalize(vec3(n.x, (n.z-n.y)*.70710678, (n.z+n.y)*.70710678)); }
`;

/* ---------------- ground chunks: baked albedo/normal/height ---------------- */
export const groundVS = `
layout(location=0) in vec2 aQ;
uniform vec4 uRect; // sx sy w h (world-screen px)
out vec2 vT;
void main(){ vT=aQ*uRect.zw; gl_Position=clipOf(uRect.xy+vT); }`;
export const groundFS = `
in vec2 vT;
uniform sampler2D uT0; uniform sampler2D uT1; uniform vec4 uRect;
uniform sampler2D uFar; uniform vec4 uFarR;
layout(location=0) out vec4 o0; layout(location=1) out vec4 o1; layout(location=2) out vec4 o2;
void main(){
  ivec2 t=ivec2(floor(vT));
  vec4 a=texelFetch(uT0,t,0), b=texelFetch(uT1,t,0);
  if(b.z==0. && b.w==0.) discard;
  float zz=(b.z*255.+b.w*255.*256.)-16384.; float Z=zz/8.;
  float row=uRect.y+float(t.y)+.5; float D=row+2.*Z;
  gl_FragDepth=fragZ(D);
  float mb=floor(a.a*255.+.5); float mat=mod(mb,32.); float fl=floor(mb/32.);
  vec2 nxy=(b.xy*255.-128.)/127.; vec3 N=vec3(nxy, sqrt(max(0.,1.-dot(nxy,nxy))));
  vec3 alb=a.rgb;
  // wind rolling over the meadow: blade pixels catch the light along moving bands
  if(mat==1. && mod(fl,2.)==1.){ float X=uRect.x+float(t.x); float Y=row+Z; float wv=sin(dot(vec2(X,Y),uWind.xy)*.035-uTime*(1.2+uWind.z*1.6)+vn(vec2(X,Y)*.01)*5.)*.5+.5; alb*=1.+(wv-.5)*.16*(.35+uWind.z); }
  o0=vec4(alb, mat/255.);
  o1=vec4(N*.5+.5, 0.);
  vec2 XY=vec2(uRect.x+float(t.x)+.5, row+Z);
  float far=texture(uFar,(XY-uFarR.xy)*uFarR.zw).r;
  o2=vec4(far, (mat==5.||fl>=4.)?.6:0., 4./255., 0.);
}`;

/* ---------------- sprites: instanced billboards ----------------
   Two sources: the static atlas (texture array: ALB + NRM with bulge and
   material) and character sheets (2D albedo + tangent normal map). */
const spriteIO = `
layout(location=0) in vec2 aQ;
layout(location=1) in vec4 iP;   // X Y Z sway
layout(location=2) in vec4 iS;   // w h ax ay
layout(location=3) in vec4 iA;   // u0 v0 layer flags
layout(location=4) in vec4 iB;   // bmin bscale id far
layout(location=5) in vec4 iT;   // tint rgb, fade
layout(location=6) in vec4 iX;   // recede(px) scale charSlot shimmerPhase
`;
export const spriteVS = spriteIO + `
uniform float uPass;   // 0 G-buffer (opaque, non-fading), 1 shadow, 2 forward (fading only)
uniform vec2 uFocus;   // the protected character's ground position (world px) for the Far recede
out vec2 vPx; flat out vec4 vP; flat out vec4 vS; flat out vec4 vA; flat out vec4 vB; flat out vec4 vT; flat out vec4 vX; out float vH;
void main(){
  int fl=int(iA.w+.5);
  bool hidden=(fl&64)!=0;
  float fade=iT.a;
  bool kill = hidden || (uPass==0. && fade>.01) || (uPass==2. && fade<=.01) || (uPass==1. && (fl&2)==0);
  float m=iP.w>0.?3.:0.;
  vec2 px=vec2(mix(-m,iS.x+m,aQ.x), aQ.y*iS.y);
  float far=iB.w;
  // the Far stands one step back: smaller around its base, nudged away, more so as you come close
  float near=0.; if(far>0.){ float dd=length(iP.xy-uFocus)/20.; near=smoothstep(7.,1.5,dd); }
  float rec=far*(2.+near*5.)+iX.x;
  float sc=iX.y*(1.-far*(.025+near*.06));
  vec2 rel=(px-iS.zw)*sc;
  vec2 ws=vec2(iP.x+rel.x, iP.y-iP.z-rec+rel.y);
  vPx=px; vP=iP; vS=iS; vA=iA; vB=iB; vT=iT; vX=vec4(rec,sc,iX.zw); vH=iS.w-px.y;
  if(uPass==1.){
    // shadow card: turned toward the sun around the vertical axis through the anchor
    vec2 L=normalize(uSunDir.xy+vec2(1e-4)); vec2 p=vec2(-L.y,L.x);
    vec3 w=vec3(iP.xy+p*rel.x, iP.z+(iS.w-px.y)*sc);
    gl_Position=uLVP*vec4(w,1.);
  } else {
    gl_Position=clipOf(ws);
    // cull off-screen instances
    vec2 a=ws-uCam; vec2 hs=uLow*.5+vec2(4.);
    float x0=iP.x-iS.z*sc-m-uCam.x, x1=iP.x+(iS.x-iS.z)*sc+m-uCam.x, y0=iP.y-iP.z-rec-iS.w*sc-uCam.y, y1=iP.y-iP.z-rec+(iS.y-iS.w)*sc-uCam.y;
    if(x1<-hs.x||x0>hs.x||y1<-hs.y||y0>hs.y) kill=true;
  }
  if(kill) gl_Position=vec4(2.,2.,2.,1.);
}`;

// shared fetch + decode for both sprite fragment programs
const spriteFetch = (sheet) => `
in vec2 vPx; flat in vec4 vP; flat in vec4 vS; flat in vec4 vA; flat in vec4 vB; flat in vec4 vT; flat in vec4 vX; in float vH;
${sheet ? 'uniform sampler2D uAlb; uniform sampler2D uNrm; uniform vec2 uSheet;' : 'uniform sampler2DArray uAlb; uniform sampler2DArray uNrm;'}
bool spr(out vec4 a, out vec4 nr, out vec2 px){
  px=floor(vPx);
  int fl=int(vA.w+.5);
  // wind: whole-pixel shifts per row, stronger toward the top; each clump breathes on its own phase
  if(vP.w>0.){
    float hgt=clamp((vS.w-px.y)/max(vS.y,1.),0.,1.);
    float ph=vP.x*.031+vP.y*.017;
    float s=sin(uTime*1.3+ph)*.6+sin(uTime*2.1+ph*1.7+px.y*.05)*.3+sin(uTime*.37+ph*3.)*.4;
    float gust=uWind.z*(.6+.4*sin(uTime*.5+vP.x*.01));
    px.x-=floor((s*.5+uWind.x*gust*1.2)*vP.w*pow(hgt,1.6)+.5);
  }
  // the Far: a slow heat-haze wobble of whole rows
  float far=vB.w;
  if(far>0.){ px.x-=floor(sin(uTime*1.3+px.y*.37+vX.w)*far*.9+.5*step(.5,h12(vec2(px.y,floor(uTime*2.)+vX.w)))*far); }
  if(px.x<0.||px.x>=vS.x||px.y<0.||px.y>=vS.y) return false;
  vec2 tx=vec2((fl&1)!=0? vS.x-1.-px.x : px.x, px.y);
  ${sheet ? `ivec2 it=ivec2(vA.xy+tx); a=texelFetch(uAlb,it,0); if(a.a<.5) return false; nr=texelFetch(uNrm,it,0);`
           : `ivec3 it=ivec3(vA.xy+tx, int(vA.z+.5)); a=texelFetch(uAlb,it,0); if(a.a<.5) return false; nr=texelFetch(uNrm,it,0);`}
  return true;
}
bool sprEdge(vec2 px){
  int fl=int(vA.w+.5);
  vec2 tx=vec2((fl&1)!=0? vS.x-1.-px.x : px.x, px.y); float e=0.;
  for(int k=0;k<4;k++){ vec2 o=vec2(k==0?1.:k==1?-1.:0., k==2?1.:k==3?-1.:0.); vec2 q=tx+o;
    if(q.x<0.||q.y<0.||q.x>=vS.x||q.y>=vS.y){ e=1.; break; }
    ${sheet ? 'if(texelFetch(uAlb,ivec2(vA.xy+q),0).a<.5){ e=1.; break; }' : 'if(texelFetch(uAlb,ivec3(vA.xy+q,int(vA.z+.5)),0).a<.5){ e=1.; break; }'}
  }
  return e>.5;
}
`;

// decode: atlas NRM = (nx, ny) camera space, bulge byte, mat(5 bits)|emi(3 bits)<<5
// sheet NRM = tangent normal map (rgb), material = character
const spriteDecode = (sheet) => sheet ? `
void dec(vec4 nr, out vec3 N, out float bulge, out float mat, out float emi){
  vec3 n=nr.rgb*2.-1.; n.y*=uSheet.y; if((int(vA.w+.5)&1)!=0) n.x=-n.x; n.z=max(n.z,.05); N=spriteN(normalize(n)); bulge=vB.x; mat=30.; emi=0.;
}` : `
void dec(vec4 nr, out vec3 N, out float bulge, out float mat, out float emi){
  vec3 n=vec3(nr.x*2.-1., nr.y*2.-1., 0.); if((int(vA.w+.5)&1)!=0) n.x=-n.x; n.z=sqrt(max(0.,1.-dot(n.xy,n.xy)));
  N=spriteN(n); bulge=vB.x+nr.z*255.*vB.y; float mb=floor(nr.a*255.+.5); mat=mod(mb,32.); emi=floor(mb/32.)/7.;
}`;

export const spriteGFS = (sheet) => spriteFetch(sheet) + spriteDecode(sheet) + `
layout(location=0) out vec4 o0; layout(location=1) out vec4 o1; layout(location=2) out vec4 o2;
void main(){
  vec4 a, nr; vec2 px; if(!spr(a,nr,px)) discard;
  vec3 N; float bulge, mat, emi; dec(nr,N,bulge,mat,emi);
  int fl=int(vA.w+.5);
  float sc=vX.y;
  float D=(vP.y-vX.x)+vP.z+(vS.w-px.y-.5)*sc+bulge*sc;
  gl_FragDepth=fragZ(D);
  vec3 col=a.rgb*vT.rgb;
  float far=vB.w;
  if(far>0. && sprEdge(px)){ float sh=step(.55,h12(px+floor(uTime*2.5)+vX.w)); col=mix(col,vec3(.86,.9,.97),far*(.35+.4*sh)); }
  float cls=((fl&8)!=0?1.:0.)+((fl&16)!=0?2.+16.*vX.z:0.);
  o0=vec4(col, mat/255.);
  o1=vec4(N*.5+.5, (fl&32)!=0?1.:emi);
  o2=vec4(far, 0., cls/255., vB.z/255.);
}`;

export const spriteShadowFS = (sheet) => spriteFetch(sheet) + `
layout(location=0) out vec4 o0;
void main(){
  vec4 a, nr; vec2 px; if(!spr(a,nr,px)) discard;
  int fl=int(vA.w+.5);
  ${sheet ? 'float mat=30.;' : 'float mat=mod(floor(nr.a*255.+.5),32.);'}
  float leafy=(mat==6.||mat==15.||mat==19.||(fl&8)!=0)?1.:0.;
  o0=vec4(leafy, vB.z/255., 0., 1.);
}`;

/* ---------------- terrain in the shadow map (back faces only) ---------------- */
export const shTerrainVS = `layout(location=0) in vec3 aP; void main(){ gl_Position=uLVP*vec4(aP,1.); }`;
export const shTerrainFS = `layout(location=0) out vec4 o0; void main(){ o0=vec4(0.,0.,0.,1.); }`;

/* ---------------- fullscreen ---------------- */
export const fsVS = `out vec2 vUV; void main(){ vec2 p=vec2((gl_VertexID<<1)&2, gl_VertexID&2); vUV=p; gl_Position=vec4(p*2.-1.,0.,1.); }`;

/* ---------------- lighting (shared by the deferred pass and the forward sprite pass) ---------------- */
export const LIGHTING = `
uniform highp sampler2DShadow uShM; uniform sampler2D uShC;
uniform vec4 uLP[32]; uniform vec4 uLC[32]; uniform int uNL;
uniform vec4 uChar[8];
uniform vec4 uMist; uniform vec3 uFogCol; uniform float uMistZ;
uniform float uCloud; uniform float uShafts; uniform float uNight; uniform float uShaftSteps;
uniform vec3 uFarCol; uniform vec4 uBounds; uniform float uEdgeFar; uniform vec4 uCharK; uniform float uFlecks;
vec3 worldAt(vec2 frag, float d){ vec2 ws=wsOf(frag); float D=uCam.y+DOFF-(d*2.-1.)*DR; return vec3(ws.x,(D+ws.y)*.5,(D-ws.y)*.5); }
float shadowAt(vec3 P, vec3 N, float rTex, float selfId){
  vec4 lp=uLVP*vec4(P+N*1.5+uSunDir*1.2,1.); vec3 sc=lp.xyz*.5+.5;
  if(sc.x<0.||sc.x>1.||sc.y<0.||sc.y>1.||sc.z>1.) return 1.;
  if(selfId>.5){ vec4 c=texture(uShC,sc.xy); if(abs(c.g*255.-selfId)<.5) return 1.; }
  vec2 tx=rTex/vec2(textureSize(uShM,0)); float b=.0009;
  float s=texture(uShM,vec3(sc.xy,sc.z-b))*.4;
  s+=texture(uShM,vec3(sc.xy+vec2(tx.x,0.),sc.z-b))*.15+texture(uShM,vec3(sc.xy-vec2(tx.x,0.),sc.z-b))*.15;
  s+=texture(uShM,vec3(sc.xy+vec2(0.,tx.y),sc.z-b))*.15+texture(uShM,vec3(sc.xy-vec2(0.,tx.y),sc.z-b))*.15;
  return s;
}
// a character's single, smoothed sun visibility: wide disc around its body, no flecks, no banding
float charShadow(int slot){
  vec4 C=uChar[slot]; if(C.w<.5) return 1.;
  float acc=0.;
  for(int k=0;k<12;k++){ float a=float(k)*2.39996; float r=sqrt((float(k)+.5)/12.)*14.;
    vec3 P=C.xyz+vec3(cos(a)*r, sin(a)*r*.5, 6.+float(k%3)*10.);
    vec4 lp=uLVP*vec4(P+uSunDir*2.,1.); vec3 sc=lp.xyz*.5+.5;
    acc+= (sc.x<0.||sc.x>1.||sc.y<0.||sc.y>1.)?1.:texture(uShM,vec3(sc.xy,sc.z-.0015)); }
  return acc/12.;
}
float leafy(vec3 P){ vec4 lp=uLVP*vec4(P,1.); vec2 sc=lp.xy*.5+.5; return texture(uShC,sc).r; }
float clouds(vec3 P){ vec2 q=(P.xy-uSunDir.xy/max(uSunDir.z,.2)*P.z)*.0012+uWind.xy*uTime*.004; float c=fbm(q*1.3)+fbm(q*3.1+5.)*.35; return 1.-smoothstep(.55,.75,c*.85)*uCloud; }
float band(float v, vec2 f){ float d=bayer4(f+uDith)-.5; return floor(clamp(v,0.,1.)*4.+.5+d*.3)/4.; }

// the whole surface model; cls bits: 1 foliage, 2 char, 4 ground
vec3 shade(vec3 alb, vec3 N, vec3 P, float mat, float emi, float wet, float cls, float selfId, vec2 f, out float visOut){
  bool isChar=mod(floor(cls/2.),2.)==1.; bool foliage=mod(cls,2.)==1.; bool ground=mod(floor(cls/4.),2.)==1.;
  int slot=int(floor(cls/16.));
  float vis;
  if(isChar) vis=charShadow(slot);
  else {
    vis=shadowAt(P,N,1.,selfId);
    if(uFlecks>0. && vis<.99 && leafy(P)>.5){ // sun-flecks leaking through the canopy: soft, slow
      vec2 q=(P.xy-uSunDir.xy/max(uSunDir.z,.3)*P.z)*.075; float sw=sin(uTime*.45+q.y*.4)*.18*(.3+uWind.z);
      float n=vn(q+vec2(sw,uTime*.02))*.62+vn(q*2.1+vec2(-uTime*.03,sw*1.3)+9.)*.38;
      vis=max(vis, smoothstep(.6,.76,n)*.7*uFlecks);
    }
  }
  vis*=clouds(P);
  visOut=vis;
  float wrap=foliage?.5:(isChar?.6:.3);
  float ndl=(dot(N,uShadeDir)+wrap)/(1.+wrap);
  float direct=clamp(ndl,0.,1.)*vis;
  if(!isChar) direct=band(direct,f);
  vec3 amb=mix(uGndCol,uSkyCol,N.z*.5+.5);
  vec3 col=alb*(amb+uSunCol*direct);
  if(foliage){ float back=clamp(-dot(N,uSunDir)*.5+.45,0.,1.)*vis; col+=alb*uSunCol*back*.32*vec3(1.,1.06,.7); }
  // glossy things: wet stone, lacquer, metal, glass
  vec3 H=normalize(uShadeDir+vec3(0.,.70710678,.70710678)); float sp=pow(max(dot(N,H),0.),mat==14.?40.:mat==21.?60.:24.);
  float gloss=(mat==14.?.6:mat==21.?.8:mat==22.?1.:0.)+wet*.5;
  col+=uSunCol*step(.55,sp)*gloss*vis*.5;
  // point lights
  vec3 pl=vec3(0.);
  for(int i=0;i<32;i++){ if(i>=uNL) break; vec3 dl=uLP[i].xyz-P; float dist=length(dl); float a=clamp(1.-dist/uLP[i].w,0.,1.); a*=a;
    float nl=max(dot(N,dl/max(dist,1e-3)),0.)*.55+.45; float v=a*nl;
    if(!isChar) v=floor(v*6.+bayer4(f+uDith)*.9)/6.;
    pl+=uLC[i].rgb*v; }
  col+=alb*pl;
  col+=alb*emi*3.;
  if(isChar){
    vec3 fill=alb*(uSkyCol*uCharK.y+pl*.25);
    col+=fill;
    col=max(col, alb*uCharK.x*(.55+.45*uSkyCol/max(max(uSkyCol.r,uSkyCol.g),max(uSkyCol.b,.01))));
  }
  return col;
}
vec3 farLook(vec3 col, float F){
  if(F<=0.) return col;
  float l=lum(col);
  vec3 pale=mix(uFarCol*.66, uFarCol*1.1, smoothstep(0.,.75,l));
  pale=mix(pale, uFarCol*(.72+l*.5), .35);
  return mix(col, pale, clamp(F,0.,1.)*.88);
}
vec3 atmos(vec3 col, vec3 P, vec2 f, bool isChar){
  // mist: a thin veil everywhere, thick in the hollows; light shafts through it
  float hollow=clamp((uMistZ-P.z)/260.,0.,1.);
  float wisp=.62+.38*fbm(P.xy*.005+vec2(uTime*.011,uTime*.004));
  float mist=uMist.a*(.18+hollow*.82)*wisp;
  if(uShafts>0.){ float acc=0.; float j=bayer4(f+uDith); int n=int(uShaftSteps);
    for(int k=0;k<12;k++){ if(k>=n) break; float t=(float(k)+j)*7.; vec3 S=P+vec3(0.,.70710678,.70710678)*t; vec4 lp=uLVP*vec4(S,1.); vec3 sc=lp.xyz*.5+.5;
      float sv=(sc.x<0.||sc.x>1.||sc.y<0.||sc.y>1.)?1.:texture(uShM,vec3(sc.xy,sc.z-.002)); acc+=sv; }
    acc/=max(1.,float(n));
    float sh=isChar? acc : floor(acc*5.+bayer4(f+uDith)*.7)/5.;
    col+=uSunCol*vec3(1.,.9,.72)*sh*uShafts*(uMist.a*.5+.08)*(isChar?.5:1.); }
  col=mix(col, uMist.rgb, clamp(mist,0.,.85));
  return col;
}
float edgeFar(vec3 P){
  vec2 d=max(uBounds.xy-P.xy, P.xy-uBounds.zw); float e=max(d.x,d.y);
  float wob=(fbm(P.xy*.004+uTime*.01)-.5)*90.;
  return smoothstep(-40.,260.,e+wob)*uEdgeFar;
}
`;

export const lightFS = LIGHTING + `
in vec2 vUV;
uniform sampler2D uG0; uniform sampler2D uG1; uniform sampler2D uG2; uniform sampler2D uDep; uniform sampler2D uBack; uniform int uDebug;
layout(location=0) out vec4 oC;
void main(){
  vec2 f=gl_FragCoord.xy; ivec2 ip=ivec2(f);
  vec4 g0=texelFetch(uG0,ip,0); float mat=floor(g0.a*255.+.5);
  if(mat<.5){ oC=vec4(texelFetch(uBack,ip,0).rgb,1.); return; }
  vec4 g1=texelFetch(uG1,ip,0), g2=texelFetch(uG2,ip,0); float d=texelFetch(uDep,ip,0).r;
  vec3 P=worldAt(f,d); vec3 N=normalize(g1.xyz*2.-1.);
  float cls=floor(g2.b*255.+.5); bool isChar=mod(floor(cls/2.),2.)==1.;
  float vis;
  vec3 col=shade(g0.rgb,N,P,mat,g1.a,g2.g,cls,floor(g2.a*255.+.5),f,vis);
  if(uDebug==1){ oC=vec4(vec3(vis),1.); return; }
  if(uDebug==2){ oC=vec4(N*.5+.5,1.); return; }
  if(uDebug==3){ oC=vec4(g0.rgb,1.); return; }
  if(uDebug==4){ oC=vec4(fract(P.z/40.),fract(P.y/200.),fract(P.x/200.),1.); return; }
  if(uDebug==8){ oC=vec4(texture(uShM,vec3(.5,.5,.5)), texture(uShM,vec3(.5,.5,.999)), texture(uShM,vec3(.5,.5,.001)),1.); return; }
  if(uDebug==6){ vec4 lp=uLVP*vec4(P,1.); vec3 sc=lp.xyz*.5+.5; oC=vec4(sc,1.); return; }
  if(uDebug==7){ vec4 lp=uLVP*vec4(P,1.); vec3 sc=lp.xyz*.5+.5; oC=vec4(texture(uShM,vec3(sc.xy,sc.z-.001)), texture(uShC,sc.xy).a, clouds(P), 1.); return; }
  if(uDebug==5){ float D=uCam.y+DOFF-(d*2.-1.)*DR; vec2 ws=wsOf(f); oC=vec4(fract(D/64.), fract(ws.y/64.), step(abs(P.z),2.), 1.); return; }
  if(isChar){ // rim light: the top/left silhouette catches the sky and the sun
    float rim=0.; for(int k=0;k<2;k++){ ivec2 o=k==0?ivec2(-1,0):ivec2(0,1); vec4 n2=texelFetch(uG2,ip+o,0); float c2=floor(n2.b*255.+.5); if(mod(floor(c2/2.),2.)!=1.) rim=1.; }
    col+=g0.rgb*rim*(uSunCol*(.25+.45*vis)+uSkyCol*.35)*uCharK.z;
  } else {
    // a dark line on the near side of a sprite's silhouette against what lies behind it
    float dn=0.; for(int k=0;k<4;k++){ ivec2 o=ivec2(k==0?1:k==1?-1:0, k==2?1:k==3?-1:0); dn=max(dn,texelFetch(uDep,ip+o,0).r-d); }
    if(dn>.006 && mod(floor(cls/4.),2.)!=1.) col*=vec3(.74,.73,.8);
  }
  col=atmos(col,P,f,isChar);
  float F=max(g2.r, edgeFar(P));
  col=farLook(col,F);
  oC=vec4(col,1.);
}`;

/* forward-lit sprites (occluders fading because a character is behind them) */
export const spriteFwdFS = (sheet) => spriteFetch(sheet) + spriteDecode(sheet) + LIGHTING + `
uniform sampler2D uDep; uniform vec2 uFocusS; // focus point on screen (native px, gl coords)
layout(location=0) out vec4 oC;
void main(){
  vec4 a, nr; vec2 px; if(!spr(a,nr,px)) discard;
  vec3 N; float bulge, mat, emi; dec(nr,N,bulge,mat,emi);
  int fl=int(vA.w+.5); float sc=vX.y;
  float D=(vP.y-vX.x)+vP.z+(vS.w-px.y-.5)*sc+bulge*sc;
  float dz=fragZ(D); float sd=texelFetch(uDep,ivec2(gl_FragCoord.xy),0).r;
  if(dz>sd) discard; // something opaque is in front
  vec2 f=gl_FragCoord.xy; vec3 P=worldAt(f,dz);
  float cls=(fl&8)!=0?1.:0.; float vis;
  vec3 col=shade(a.rgb*vT.rgb,N,P,mat,emi,0.,cls,vB.z,f,vis);
  col=atmos(col,P,f,false); col=farLook(col,max(vB.w,edgeFar(P)));
  // fade: strongest around the hidden character, softer further out; dithered so it stays pixel art
  float r=length(f-uFocusS); float k=vT.a*mix(.78,.42,smoothstep(26.,70.,r));
  if(bayer4(f+uDith)<k) discard;
  oC=vec4(col,1.);
}`;

/* ---------------- water: refraction, reflection, foam, falls ---------------- */
export const waterFS = `
in vec2 vT;
uniform sampler2D uW0; uniform sampler2D uW1; uniform vec4 uRect;
uniform sampler2D uScene; uniform sampler2D uDep; uniform vec3 uSkyTop; uniform vec3 uSkyHor; uniform float uSSR;
uniform vec4 uMist; uniform float uMistZ; uniform vec3 uFarCol; uniform sampler2D uFar; uniform vec4 uFarR;
layout(location=0) out vec4 oC;
void main(){
  ivec2 t=ivec2(floor(vT));
  vec4 w0=texelFetch(uW0,t,0), w1=texelFetch(uW1,t,0);
  if(w1.a<.5) discard;
  float zz=(w1.r*255.+w1.g*255.*256.)-16384.; float Z=zz/8.;
  float row=uRect.y+float(t.y)+.5; float D=row+2.*Z+1.;
  vec2 f=gl_FragCoord.xy;
  float sd=texelFetch(uDep,ivec2(f),0).r; if(fragZ(D)>sd+.00005) discard;
  vec2 P=vec2(uRect.x+float(t.x), row); float tm=uTime;
  vec2 fl=(w0.xy*255.-128.)/100.; float spd=length(fl); float dep=w0.z*255./4.; float flags=floor(w0.w*255./32.);
  bool fall=mod(flags,2.)==1.; float shore=w1.b;
  vec3 col;
  if(fall){
    // falling water: bright streaks racing down, a dark sheet between, a white lip at the top
    float s1=vn(vec2(P.x*.7, P.y*.08-tm*3.2)), s2=vn(vec2(P.x*1.6+5., P.y*.05-tm*4.1));
    float s=s1*.6+s2*.4;
    vec3 sheet=mix(vec3(.24,.36,.42),vec3(.62,.74,.8),s);
    col=sheet*(uSkyCol*.8+uSunCol*.45+.08);
    col+=step(.72,s)*vec3(.85,.92,.95)*(uSkyCol*.4+uSunCol*.5+.12);
    if(mod(floor(flags/4.),2.)==1.) col=mix(col,vec3(.9,.95,.97)*(uSkyCol*.5+uSunCol*.6+.15),.8);
  } else {
    vec2 fd=spd>.02?fl/spd:vec2(0.,1.); vec2 q=vec2(dot(P,vec2(fd.y,-fd.x)),dot(P,fd));
    float still=1.-smoothstep(.05,.4,spd);
    float rip=vn(P*.09+vec2(tm*.2,tm*.13))*.6+vn(P*.21-vec2(tm*.15,-tm*.1)+3.)*.4;
    float streak=vn(vec2(q.x*.35,q.y*.06-tm*(1.+spd*3.)))*.6+vn(vec2(q.x*.7+3.,q.y*.12-tm*(1.6+spd*4.)))*.4;
    float pat=mix(streak,rip,still);
    vec2 off=(vec2(rip,vn(P*.13+tm*.2))-.5)*vec2(2.,1.5)*clamp(dep*.06,0.,1.);
    vec3 under=texelFetch(uScene,ivec2(f+off),0).rgb;
    vec3 deepC=vec3(.05,.15,.17), midC=vec3(.1,.27,.28), shalC=vec3(.28,.45,.42);
    vec3 wc=dep<8.?mix(shalC,midC,dep/8.):mix(midC,deepC,clamp((dep-8.)/24.,0.,1.));
    wc*=uSkyCol*.9+uSunCol*.4+.05;
    float a=clamp(.18+dep*.035,0.,.85);
    col=mix(under,wc,a);
    vec3 refl=mix(uSkyHor,uSkyTop,.4);
    if(uSSR>0.){ float roff=floor((pat-.5)*3.);
      for(int k=1;k<120;k++){ if(float(k)>uSSR) break; vec2 g=f+vec2(roff,float(k)*2.); if(g.y>=uLow.y-1.){ refl=mix(uSkyHor,uSkyTop,clamp(float(k)/120.,0.,1.)); break; }
        float d2=texelFetch(uDep,ivec2(g),0).r; float D2=uCam.y+DOFF-(d2*2.-1.)*DR; float ws2=uCam.y+uLow.y*.5-g.y;
        float Z2=(D2-ws2)*.5; if(d2<.9999 && Z2>Z+2.){ refl=texelFetch(uScene,ivec2(g),0).rgb; break; } } }
    float fres=.2+.28*smoothstep(4.,24.,dep);
    col=mix(col,refl*vec3(.85,.95,1.),fres*(.7+.5*pat));
    float crest=step(.73,pat)*step(pat,.77)*step(.5,h12(floor(P/3.)));
    col+=crest*(uSkyCol*.22+uSunCol*.22);
    float glint=step(.996,h12(P+floor(tm*4.)))*step(.55,pat)*step(.3,uShadeDir.z);
    col+=glint*uSunCol*1.4;
    float lap=sin(tm*1.4+fbm(P*.05)*8.)*.5+.5;
    float foam=step(.55,shore*(.6+lap*.5))*step(.42,vn(P*.25+vec2(tm*.3,0.)));
    float rap=step(.9,spd*(.45+streak*.9))*step(.45,h12(P+floor(tm*6.)));
    col=mix(col,vec3(.88,.94,.95)*(uSkyCol*.5+uSunCol*.6+.12),clamp(foam*.55+rap*.7,0.,1.));
  }
  float hollow=clamp((uMistZ-Z)/260.,0.,1.); col=mix(col,uMist.rgb,clamp(uMist.a*(.18+hollow*.82),0.,.85));
  float far=texture(uFar,(vec2(P.x,row+Z)-uFarR.xy)*uFarR.zw).r;
  if(far>0.){ float l=lum(col); col=mix(col,mix(uFarCol*.7,uFarCol*1.1,l),far*.85); }
  oC=vec4(col,1.);
}`;
export const waterVS = groundVS;

/* ---------------- particles (pixel squares) ---------------- */
export const partVS = `
layout(location=0) in vec4 aP; layout(location=1) in vec4 aC;
out vec4 vC;
void main(){ vC=aC; vec2 ws=vec2(aP.x, aP.y-aP.z); vec4 c=clipOf(ws); c.xy=(floor((c.xy*.5+.5)*uLow)+.5)/uLow*2.-1.;
  c.z=ndcZ(aP.y+aP.z); gl_Position=c; gl_PointSize=aP.w; }`;
export const partFS = `in vec4 vC; layout(location=0) out vec4 oC; void main(){ if(vC.a<1. && bayer4(gl_FragCoord.xy+uDith)>vC.a) discard; oC=vec4(vC.rgb,1.); }`;
export const partAddFS = `in vec4 vC; layout(location=0) out vec4 oC; void main(){ oC=vec4(vC.rgb*vC.a,1.); }`;

/* ---------------- glow cards (additive halos, light pools) ---------------- */
export const glowVS = `
layout(location=0) in vec2 aQ;
layout(location=1) in vec4 iP;  // x y z kind
layout(location=2) in vec4 iS;  // w h - -
layout(location=3) in vec4 iC;  // rgb intensity
out vec2 vQ; out vec4 vC; flat out float vK;
void main(){
  vec2 o=(aQ-.5)*iS.xy;
  vec2 ws=iP.w>1.5? vec2(iP.x+o.x, iP.y-iP.z+o.y) : vec2(iP.x+o.x, iP.y+o.y*.5-iP.z);
  vQ=aQ*2.-1.; vC=iC; vK=iP.w;
  gl_Position=clipOf(ws); gl_Position.z=ndcZ(iP.y+iP.z+(iP.w>1.5?40.:0.));
}`;
export const glowFS = `
in vec2 vQ; in vec4 vC; flat in float vK; layout(location=0) out vec4 oC;
void main(){ float d=length(vQ); float a=1.-smoothstep(0.,1.,d); a*=a;
  a=floor(a*vC.a*7.+bayer4(gl_FragCoord.xy+uDith))/7.; oC=vec4(vC.rgb*a,1.); }`;

/* ---------------- backdrop: sky and the painted far layers ---------------- */
export const backFS = `
in vec2 vUV;
uniform sampler2D uLayer; uniform vec4 uLayerR; // x0 y0 (world-screen at parallax 0), w h
uniform vec2 uPar; uniform vec3 uSkyTop; uniform vec3 uSkyHor; uniform vec3 uHaze; uniform float uNightK;
uniform vec4 uRed; // red beacon: x y (layer px) blink intensity
layout(location=0) out vec4 oC;
void main(){
  vec2 f=gl_FragCoord.xy; vec2 ws=wsOf(f);
  // parallax: the layer moves at uPar of the camera speed
  vec2 lp=(ws-uCam)+uCam*uPar-uLayerR.xy;
  float sky=clamp((lp.y+uLayerR.w*.2)/uLayerR.w,0.,1.);
  vec3 col=mix(uSkyTop,uSkyHor,smoothstep(0.,1.,sky));
  if(uNightK>.5){ float st=step(.997,h12(floor(lp*.5)))*(.6+.4*sin(uTime*2.+h12(floor(lp))*30.)); col+=vec3(.75,.8,1.)*st*.55*(1.-sky); }
  if(lp.x>=0.&&lp.y>=0.&&lp.x<uLayerR.z&&lp.y<uLayerR.w){
    vec4 L=texelFetch(uLayer,ivec2(lp),0);
    if(L.a>0.){ // layer pixels carry a grey value and a depth (alpha: 1 near … 0.1 far)
      float depth=L.a; vec3 base=L.rgb;
      vec3 c=mix(uHaze, base*(uSkyTop*.35+uSkyHor*.55+uSunCol*.25), smoothstep(.05,1.,depth)*.8+.2*depth);
      col=mix(col,c,1.);
    }
  }
  float rb=length(lp-uRed.xy); if(uRed.w>0. && rb<1.2) col+=vec3(1.,.12,.08)*uRed.z*uRed.w*3.;
  oC=vec4(col,1.);
}`;

/* ---------------- post ---------------- */
export const copyFS = `in vec2 vUV; uniform sampler2D uTex; layout(location=0) out vec4 oC; void main(){ oC=texture(uTex,vUV); }`;
export const brightFS = `in vec2 vUV; uniform sampler2D uTex; uniform vec2 uTx; uniform float uThr; layout(location=0) out vec4 oC;
void main(){ vec3 c=vec3(0); for(int i=0;i<4;i++){ vec2 o=vec2(float(i&1),float(i>>1))-.5; c+=texture(uTex,vUV+o*uTx).rgb; } c*=.25; float l=max(c.r,max(c.g,c.b)); oC=vec4(c*smoothstep(uThr,uThr+.35,l),1.); }`;
export const blurFS = `in vec2 vUV; uniform sampler2D uTex; uniform vec2 uDir; layout(location=0) out vec4 oC;
void main(){ vec3 c=texture(uTex,vUV).rgb*.227027; c+=texture(uTex,vUV+uDir*1.3846).rgb*.316216; c+=texture(uTex,vUV-uDir*1.3846).rgb*.316216; c+=texture(uTex,vUV+uDir*3.2308).rgb*.07027; c+=texture(uTex,vUV-uDir*3.2308).rgb*.07027; oC=vec4(c,1.); }`;
export const compFS = `
in vec2 vUV;
uniform sampler2D uLowT; uniform sampler2D uBloom;
uniform vec2 uLowS; uniform vec2 uOff; uniform float uScale; uniform vec2 uScr; uniform vec2 uPad;
uniform vec3 uLift; uniform vec3 uGain; uniform float uSat; uniform float uBloomK; uniform float uVig;
uniform vec4 uFade; uniform float uT; uniform vec3 uShT; uniform vec3 uHiT; uniform float uBox; uniform float uExpo;
layout(location=0) out vec4 oC;
vec3 tone(vec3 c){ c*=uExpo; vec3 e=max(c-.8,0.); return min(c,.8)+.2*(1.-exp(-e/.2)); }
void main(){
  vec2 sp=gl_FragCoord.xy;
  float bh=uBox*uScr.y*.11; if(sp.y<bh||sp.y>uScr.y-bh){ oC=vec4(0.,0.,0.,1.); return; }
  vec2 lp=(sp-uPad)/uScale+uOff+1.;
  vec2 uv=(floor(lp)+.5)/uLowS;
  vec3 c=texture(uLowT,uv).rgb;
  c+=texture(uBloom,lp/uLowS).rgb*uBloomK;
  c=tone(c);
  float l=lum(c);
  c=mix(vec3(l),c,uSat);
  c=uLift+c*(uGain-uLift);
  float l2=lum(c); c+=uShT*(1.-smoothstep(0.,.5,l2))+uHiT*smoothstep(.45,1.,l2);
  vec2 q=vUV-.5; c*=1.-dot(q,q)*uVig;
  c=mix(c,uFade.rgb,uFade.a);
  oC=vec4(c,1.);
}`;
