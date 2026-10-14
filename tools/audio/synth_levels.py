# Estimate the synthesized engine's bed loudness at its ambience input (src/audio/audio.js, AMBIENCE),
# so the recorded beds in src/audio/field.js sit in the same range. WebAudio biquads = RBJ cookbook.
# Rough: noise generators and filters as in the engine, gust/rustle modulation approximated. Slow (pure Python loops).
import numpy as np, subprocess, re
SR = 44100
rng = np.random.default_rng(3)
def biquad(x, typ, f0, Q=None, gain_db=0.0):
    w0 = 2*np.pi*f0/SR; cw, sw = np.cos(w0), np.sin(w0)
    if typ in ("lowpass", "highpass"):
        Qlin = 10 ** ((Q or 0) / 20)   # WebAudio: lowpass/highpass Q is in dB
        a = sw / (2*Qlin)
        if typ == "lowpass": b = [(1-cw)/2, 1-cw, (1-cw)/2]
        else: b = [(1+cw)/2, -(1+cw), (1+cw)/2]
        A = [1+a, -2*cw, 1-a]
    elif typ == "bandpass":
        a = sw / (2*Q); b = [a, 0, -a]; A = [1+a, -2*cw, 1-a]
    b = np.array(b)/A[0]; A = np.array(A)/A[0]
    y = np.zeros_like(x); x1=x2=y1=y2=0.0
    # vectorised via lfilter-like loop in numpy chunks (simple python loop is slow; use recursion on arrays)
    for n in range(len(x)):
        xn = x[n]; yn = b[0]*xn + b[1]*x1 + b[2]*x2 - A[1]*y1 - A[2]*y2
        x2, x1, y2, y1 = x1, xn, y1, yn; y[n] = yn
    return y
def pink(n):
    w = rng.uniform(-1, 1, n); b0=b1=b2=0.0; out = np.zeros(n)
    for i in range(n):
        b0 = 0.99765*b0 + w[i]*0.099046; b1 = 0.963*b1 + w[i]*0.2965164; b2 = 0.57*b2 + w[i]*1.0526913
        out[i] = (b0 + b1 + b2 + w[i]*0.1848)*0.2
    return out
def brown(n):
    w = rng.uniform(-1, 1, n); br = 0.0; out = np.zeros(n)
    for i in range(n):
        br = (br + 0.02*w[i]) / 1.02; out[i] = br*3.2
    return out
def lufs(x):
    p = subprocess.run(["ffmpeg","-nostats","-v","info","-f","f32le","-ar",str(SR),"-ac","1","-i","-","-filter_complex","ebur128","-f","null","-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True)
    e = p.stderr.decode(); return float(re.search(r"I:\s+(-?[\d.]+) LUFS", e[e.rfind("Summary"):]).group(1))
N = SR * 12
wind = 0.3
wv = (0.1 + 0.6*wind) * 1.0 * 0.55
W = biquad(biquad(pink(N), "lowpass", 300 + (1200-300)*wind, 0), "highpass", 50, 0) * 0.62 * wv
leaves_g = 1.0 * (0.15 + 0.85*wind) * 0.3
burst = np.repeat(rng.uniform(0.1, 0.8, N // 4410 + 1), 4410)[:N]  # rustle bursts ~0.1-0.8 every 0.1 s
Lv = biquad(rng.uniform(-1,1,N)*0.7, "bandpass", 3600, 0.8) * burst * leaves_g
print(f"synth wind bed @wind=0.3:   {lufs(W):6.1f} LUFS")
print(f"synth leaves @wind=0.3:     {lufs(Lv):6.1f} LUFS")
print(f"synth wind+leaves:          {lufs(W+Lv):6.1f} LUFS")
# stream: white through 4 bandpasses with gains ~U(0.3,1.8), at water=1 -> ST.g 0.75 ; babble ignored (small)
x = rng.uniform(-1,1,N)*0.7
S = sum(biquad(x, "bandpass", (lo+hi)/2, q) * 1.05 for (lo,hi),q in zip([[280,520],[600,1100],[1200,2100],[2300,3600]],[5,7,8,9])) * 0.75
print(f"synth stream @water=1:      {lufs(S):6.1f} LUFS")
F = (biquad(brown(N), "lowpass", 420, 0) + biquad(rng.uniform(-1,1,N)*0.7, "bandpass", 2600, 0.5)*0.35) * 0.5
print(f"synth fall @fall=1:         {lufs(F):6.1f} LUFS")
# suzumushi: 0.9 events/s, 1-2 s, sine 4.3-4.6 kHz, AM by 38-48 Hz sine (gain 0.5 +- 0.5), level U(.012,.028)*0.75
t = np.arange(N)/SR; z = np.zeros(N); tt = 0.0
while tt < 12:
    tt += rng.exponential(1/0.9); L = rng.uniform(1,2); f = rng.uniform(4300,4600); lv = rng.uniform(0.012,0.028)*0.75
    i0 = int(tt*SR); i1 = min(N, int((tt+L)*SR))
    if i0 >= N: break
    tl = t[i0:i1]-tt; env = np.minimum(1, tl/0.06) * np.where(tl > L-0.15, np.maximum(0,(L-tl)/0.15)*0.7, 1)
    z[i0:i1] += lv * np.sin(2*np.pi*f*tl) * (0.5 + 0.5*np.sin(2*np.pi*rng.uniform(38,48)*tl)) * env
print(f"synth suzumushi chorus:     {lufs(z):6.1f} LUFS")
