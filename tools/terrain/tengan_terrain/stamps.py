"""Hand-pixelled glyphs (tufts, flowers, pebbles, leaves, stones) and a
priority stamper that writes them into indexed rasters.

Glyph cells: '.' transparent, digits are tone offsets relative to the pixel
underneath ('0' = -1 shadow, '1' = same, '2' = +1, '3' = +2, '4' = +3);
upper-case letters are absolute tones of the glyph's own ramp
('A' = 0 ... 'H' = 7). Glyphs are drawn with the anchor at their bottom row
centre; lower anchors (closer to the camera) win where glyphs overlap."""
import numpy as np


def _parse(rows):
    h = len(rows)
    w = max(len(r) for r in rows)
    rel = np.full((h, w), np.nan, np.float32)
    ab = np.full((h, w), -1, np.int16)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == '.':
                continue
            if ch.isdigit():
                rel[y, x] = int(ch) - 1
            else:
                ab[y, x] = ord(ch) - ord('A')
    return rel, ab


# grass tufts: blades point up (north on screen), shadow at the foot
TUFTS = [_parse(g) for g in [
    ["..3..", ".32.2", "21212", ".000."],
    ["3..2", "2321", ".00."],
    [".3...3.", ".23.32.", "2121212", ".00000."],
    [".3.", "212", ".0."],
    ["..3...", ".32.3.", ".2132.", "21212.", ".0000."],
    ["3.3", "232", "00."],
    [".3..3", "32.22", "21211", ".000."],
    ["..33..", ".3223.", "212212", ".0000."],
]]
# small low weeds / clover-like clusters (rounder)
WEEDS = [_parse(g) for g in [
    [".2.", "232", ".1.", ".0."],
    [".22.", "2332", ".21.", "..0."],
    ["2.2", ".3.", "202"],
]]
# pebbles in their ground's ramp (lit upper left, shadow lower right)
PEBBLES = [_parse(g) for g in [
    ["32", ".0"],
    ["332", "221", ".00"],
    ["3", "0"],
    [".32.", "3221", ".100", "..0."],
]]
# leaves (absolute tones in the litter ramp) and twigs (bark ramp)
LEAVES = [_parse(g) for g in [["FD"], ["E", "C"], ["GE"], ["D", "F"], ["FE", ".C"]]]
TWIGS = [_parse(g) for g in [["EDDC"], ["E...", ".DDC"], ["DDDCC"]]]
# flowers: absolute tones in a flower ramp; the stem/shadow pixel is relative (grass)
FLOWERS = [_parse(g) for g in [["G", "0"], ["GF", "0."], [".G.", "GFE", ".0."], ["F.G", "0.0"]]]


def stamp(prio, tone, ramp, ys, xs, glyphs, which, ramp_ids=None, tone_add=None, prio_add=None,
          allow=None, abs_ramp_id=None):
    """Write glyphs anchored at (ys, xs) (bottom-row centre) into tone/ramp rasters.

    prio: float raster of the current winning anchor y per pixel (updated).
    which: glyph index per anchor. ramp_ids: optional ramp per anchor for the
    glyph's absolute cells (flowers, leaves). allow: bool raster, pixels the
    stamp may touch. abs_ramp_id: ramp used for relative cells? (None keeps the
    underlying pixel's ramp). Returns the touched pixel mask."""
    H, W = tone.shape
    tgt, val, isabs, rid, pr = [], [], [], [], []
    base_prio = ys.astype(np.float32) + (0 if prio_add is None else prio_add)
    for gi, (rel, ab) in enumerate(glyphs):
        sel = np.nonzero(which == gi)[0]
        if len(sel) == 0:
            continue
        gh, gw = rel.shape
        cx = gw // 2
        for gy in range(gh):
            for gx in range(gw):
                r, a = rel[gy, gx], ab[gy, gx]
                if np.isnan(r) and a < 0:
                    continue
                yy = ys[sel] - (gh - 1 - gy)
                xx = xs[sel] + (gx - cx)
                ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
                if not ok.any():
                    continue
                s2 = sel[ok]
                tgt.append(yy[ok].astype(np.int64) * W + xx[ok])
                if a >= 0:
                    val.append(np.full(len(s2), a, np.float32))
                    isabs.append(np.ones(len(s2), bool))
                else:
                    add = r if tone_add is None else r + tone_add[s2]
                    val.append(np.full(len(s2), add, np.float32) if np.isscalar(add) else add.astype(np.float32))
                    isabs.append(np.zeros(len(s2), bool))
                rid.append(ramp_ids[s2] if ramp_ids is not None else np.zeros(len(s2), np.int16))
                pr.append(base_prio[s2])
    if not tgt:
        return np.zeros((H, W), bool)
    tgt = np.concatenate(tgt)
    val = np.concatenate(val)
    isabs = np.concatenate(isabs)
    rid = np.concatenate(rid)
    pr = np.concatenate(pr)
    if allow is not None:
        k = allow.ravel()[tgt]
        tgt, val, isabs, rid, pr = tgt[k], val[k], isabs[k], rid[k], pr[k]
    # keep the highest priority per pixel, and only if it beats what is there
    order = np.lexsort((pr, tgt))
    t_s = tgt[order]
    last = np.ones(len(t_s), bool)
    last[:-1] = t_s[1:] != t_s[:-1]
    w = order[last]
    tgt, val, isabs, rid, pr = tgt[w], val[w], isabs[w], rid[w], pr[w]
    pf = prio.ravel()
    beat = pr >= pf[tgt]
    tgt, val, isabs, rid, pr = tgt[beat], val[beat], isabs[beat], rid[beat], pr[beat]
    pf[tgt] = pr
    tf = tone.ravel()
    rf = ramp.ravel()
    rel_m = ~isabs
    tf[tgt[rel_m]] = tf[tgt[rel_m]] + val[rel_m]
    if abs_ramp_id is not None:
        rf[tgt[rel_m]] = abs_ramp_id
    tf[tgt[isabs]] = val[isabs]
    rf[tgt[isabs]] = rid[isabs]
    touched = np.zeros(H * W, bool)
    touched[tgt] = True
    return touched.reshape(H, W)


def jitter_points(mask, cell_w, cell_h, density, seed, frame_x0=0, frame_y0=0):
    """One candidate per cell of a jittered grid (odd rows offset half a cell);
    kept where rand < density (a raster sampled at the point). Returns ys, xs, h."""
    from .noise import hash2
    H, W = mask.shape
    gy, gx = np.mgrid[0:H // cell_h + 1, 0:W // cell_w + 2]
    gy = gy.ravel()
    gx = gx.ravel()
    h = hash2(gx + frame_x0, gy + frame_y0, seed)
    ox = (h & np.uint32(0xFF)).astype(np.float32) / 255.0
    oy = ((h >> np.uint32(8)) & np.uint32(0xFF)).astype(np.float32) / 255.0
    xs = (gx * cell_w + (gy & 1) * (cell_w // 2) + ox * cell_w).astype(np.int64) - cell_w // 2
    ys = (gy * cell_h + oy * cell_h).astype(np.int64)
    ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
    xs, ys, h = xs[ok], ys[ok], h[ok]
    ok = mask[ys, xs]
    xs, ys, h = xs[ok], ys[ok], h[ok]
    r = ((h >> np.uint32(16)) & np.uint32(0xFFFF)).astype(np.float32) / 65535.0
    d = density[ys, xs] if np.ndim(density) else density
    keep = r < d
    return ys[keep], xs[keep], h[keep]
