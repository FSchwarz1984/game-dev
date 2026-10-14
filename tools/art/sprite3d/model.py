"""A character model and the frame renderer.

A model (one per character, in chars/) provides proportions, a palette, the shapes for a given
context, chains (secondary motion), face features and anchors. render_frame() turns a pose into a
pixel-art frame: RGBA albedo, normal map, and anchors in pixels relative to the foot pivot.

Pixel grid: cell column i covers screen u in [i - PVX - 0.5, i - PVX + 0.5) (her centre line runs
through the middle of the pivot column) and row j covers v in [j - PVY, j - PVY + 1): the ground
plane (v = 0) is the top edge of the pivot row, so soles end on row PVY - 1 and their outline sits
on the pivot row (the engine draws the frame with the pivot pixel's top-left corner on her ground
point)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

import geom as G
import humanoid as Hu
import style as St
from render import render


@dataclass
class ChainSpec:
    anchor: str                 # bone
    offset: tuple               # in the anchor bone's frame
    n: int
    seg: float
    rest: tuple = (0, -1, 0)    # rest direction in the anchor bone's frame
    damping: float = 0.15
    stiff: float = 0.10
    gravity: float = 0.30
    wind: float = 1.0           # how much the walk drag acts on it
    up: tuple = (0, 0, 1)       # anchor-frame axis that fixes the twist of the segments
    collide: object = None      # optional callable(points_in_body_frame, bones) -> points


@dataclass
class FrameSpec:
    pose: dict
    ctx: dict = field(default_factory=dict)
    wind: tuple = (0, 0, 0)     # body-frame acceleration on the chains this frame


class Model:
    NAME = 'model'
    FRAME = (48, 48)
    PIVOT = (24, 44)
    S = 6                       # supersampling per pixel side

    def __init__(self):
        self.P = self.props()
        self.sk = Hu.build_skeleton(self.P)
        self.pal = self.palette()
        self.chains = self.chain_specs()

    # --- to override
    def props(self) -> dict: raise NotImplementedError
    def palette(self) -> St.Palette: raise NotImplementedError
    def shapes(self, ctx) -> list: raise NotImplementedError
    def chain_specs(self) -> dict: return {}
    def features(self, ctx) -> dict: return {}          # name -> (bone, (x, y, z), normal-local)
    def anchors(self, ctx) -> dict: return {}           # name -> (bone, (x, y, z))
    def decals(self, img, px, feats, ctx): pass
    def head_bones(self) -> tuple: return ('head',)     # bones snapped together as the head unit

    # --- posing
    def bones(self, pose: dict):
        rot = {k: v for k, v in pose.items() if k in self.sk.parent and k != 'root'}
        if 'root_m' in pose:
            rootm = np.asarray(pose['root_m'], float)
        else:
            root = pose.get('root', (0, 0, 0, 0, 0, 0))
            x, y, z, yaw, pitch, roll = (list(root) + [0] * 6)[:6]
            R = G.euler(pitch, yaw, roll)
            rootm = G.M4(R, (x, y, z))
        if 'pelvis_y' in pose:
            off = dict(self.sk.offset)
            self.sk.offset['pelvis'] = np.array([0, pose['pelvis_y'], 0], float)
            bw = self.sk.world(rot, rootm)
            self.sk.offset.update(off)
        else:
            bw = self.sk.world(rot, rootm)
        return bw

    def simulate(self, frames: list, loop: bool, warm: int = 3):
        """Adds chain bones to every frame: returns a list of bone dicts (body frame)."""
        base = [self.bones(f.pose) for f in frames]
        if not self.chains:
            return base
        sims = {k: Hu.Chain(c.n, c.seg, (0, -1, 0), c.damping, c.stiff, c.gravity) for k, c in self.chains.items()}

        def anchor_of(bw, c):
            m = bw[c.anchor]
            p = m @ np.array([c.offset[0], c.offset[1], c.offset[2], 1.0])
            rest = m[:3, :3] @ np.asarray(c.rest, float)
            return p[:3], rest

        for k, c in self.chains.items():
            a, r = anchor_of(base[0], c)
            sims[k].reset(a, r / np.linalg.norm(r))
        out_pts = [dict() for _ in frames]
        cycles = (warm + 1) if loop else 1
        if not loop:   # settle at the first frame
            for _ in range(24):
                for k, c in self.chains.items():
                    a, r = anchor_of(base[0], c)
                    sims[k].step(a, r, wind=np.asarray(frames[0].wind) * c.wind)
        for cyc in range(cycles):
            for i, f in enumerate(frames):
                for k, c in self.chains.items():
                    a, r = anchor_of(base[i], c)
                    col = (lambda pts, bw=base[i], c=c: c.collide(pts, bw)) if c.collide else None
                    pts = sims[k].step(a, r, wind=np.asarray(f.wind) * c.wind,
                                       collide=None)
                    if c.collide is not None:
                        pts = c.collide(pts, base[i])
                        sims[k].p[:] = pts
                    if cyc == cycles - 1:
                        out_pts[i][k] = pts
        result = []
        for i, f in enumerate(frames):
            bw = dict(base[i])
            for k, c in self.chains.items():
                pts = out_pts[i][k]
                m = bw[c.anchor]
                up = m[:3, :3] @ np.asarray(c.up, float)
                for j in range(c.n):
                    d = pts[j + 1] - pts[j]
                    ln = np.linalg.norm(d)
                    ydir = -d / ln if ln > 1e-9 else np.array([0, 1.0, 0])
                    zdir = up - ydir * np.dot(up, ydir)
                    if np.linalg.norm(zdir) < 1e-6:
                        zdir = np.array([0, 0, 1.0]) - ydir * ydir[2]
                    zdir /= np.linalg.norm(zdir)
                    xdir = np.cross(ydir, zdir)
                    M = np.eye(4)
                    M[:3, 0], M[:3, 1], M[:3, 2] = xdir, ydir, zdir
                    M[:3, 3] = pts[j]
                    bw[f'{k}{j}'] = M
                bw[f'{k}{c.n}'] = G.M4(bw[f'{k}{c.n - 1}'][:3, :3], pts[c.n])
            result.append(bw)
        return result

    def head_phase(self, yaw, variant=None):
        """Screen position (u, v) of the head joint in the rest pose for this view: the reference
        sub-pixel phase every frame's head is snapped to."""
        bw = self.simulate([FrameSpec(self.rest_pose(), {'variant': variant})], loop=False)[0]
        cam = G.camera() @ G.M4(G.Ry(yaw))
        c = math.cos(math.radians(G.PITCH))
        hp = cam @ bw['head'] @ np.array([0, 0, 0, 1.0])
        return (hp[0], -hp[1] / c)

    def rest_pose(self):
        return {}

    # --- rendering
    def render_frame(self, bw: dict, yaw: float, ctx: dict, snap_head=None):
        FW, FH = self.FRAME
        PVX, PVY = self.PIVOT
        S = self.S
        cam = G.camera() @ G.M4(G.Ry(yaw))
        c = math.cos(math.radians(G.PITCH))
        bw = dict(bw)
        if snap_head is not None:
            # move the head unit so its screen position keeps the reference sub-pixel phase
            hp = cam @ bw['head'] @ np.array([0, 0, 0, 1.0])
            u, v = hp[0], -hp[1] / c
            du = (round(u - snap_head[0]) + snap_head[0]) - u
            dv = (round(v - snap_head[1]) + snap_head[1]) - v
            # screen offset -> body-frame offset (x along camera x, y up = -v * cos / ... )
            inv = np.linalg.inv(cam[:3, :3])
            off = inv @ np.array([du, -dv * c, 0.0])
            for b in self.head_bones_all(bw):
                m = bw[b].copy(); m[:3, 3] += off; bw[b] = m
        shapes = self.shapes(dict(ctx, bones=bw, yaw=yaw))
        part_ids, group_ids = {}, {}
        prims = G.assemble(shapes, bw, cam, self.pal.ids, part_ids, group_ids)
        x0 = -PVX - 0.5
        y0 = PVY * c
        zs, rs = prims[:, 32], prims[:, 33]
        buf = render(prims, FW * S, FH * S, x0, y0, 1.0 / S, c / S, float((zs + rs).max() + 1),
                     float((zs - rs).min() - 1), self.pal.L.astype(np.float32), ao_dist=self.P.get('ao', 2.4),
                     shadow_k=self.P.get('shadow_k', 8.0))
        px = St.stylize(buf, S, self.pal, cover=self.P.get('cover', 0.5))
        px['part_names'] = {v: k for k, v in part_ids.items()}
        self.post(px, ctx)
        St.clean_tones(px, self.pal)
        St.merge_islands(px, self.pal, max_size=self.P.get('island', 2), skip=self.P.get('island_skip', ()))
        St.separation_lines(px, self.pal, gap=self.P.get('line_gap', 1.6))
        St.outline(px, self.pal)
        img = St.to_rgba(px, self.pal)
        feats = self.project(self.features(ctx), bw, cam, c)
        self.decals(img, px, feats, ctx)
        nrm = St.normal_map(px)
        nrm[..., 3] = np.where(img[..., 3] > 0, 255, 0)
        nrm[img[..., 3] == 0, :3] = (128, 128, 255)
        anchors = {}
        for name, (bone, p) in self.anchors(ctx).items():
            if bone not in bw:
                continue
            q = cam @ bw[bone] @ np.array([p[0], p[1], p[2], 1.0])
            anchors[name] = [round(q[0], 1), round(-q[1] / c, 1)]
        return img, nrm, anchors, px

    def head_bones_all(self, bw):
        hb = set(self.head_bones())
        out = [b for b in bw if b in hb or any(b.startswith(h) for h in self.head_chain_prefixes())]
        return out

    def head_chain_prefixes(self):
        return ()

    def post(self, px, ctx):
        pass

    def project(self, feats, bw, cam, c):
        """Feature points -> continuous pixel coords (X, Y), camera depth, camera-space normal."""
        PVX, PVY = self.PIVOT
        out = {}
        for name, (bone, p, n) in feats.items():
            if bone not in bw:
                continue
            M = cam @ bw[bone]
            q = M @ np.array([p[0], p[1], p[2], 1.0])
            nn = M[:3, :3] @ np.asarray(n, float)
            nn /= max(np.linalg.norm(nn), 1e-9)
            out[name] = (q[0] + PVX + 0.5, -q[1] / c + PVY, q[2], nn)
        return out


# ---------------------------------------------------------------------------------------------
# Decal stamping


def stamp(img, px, X, Y, grid, cmap, anchor, depth=None, tol=0.8, only_on=None):
    """Paint a small grid with its anchor at continuous pixel coords (X, Y). '.' = skip. When depth
    is given, pixels whose rendered surface is nearer than depth - tol (something in front) are
    skipped. only_on: material ids the stamp may paint over."""
    H, W = img.shape[:2]
    ax, ay = anchor
    x0, y0 = int(math.floor(X - ax + 0.5)), int(math.floor(Y - ay + 0.5))
    for j, row in enumerate(grid):
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            x, y = x0 + i, y0 + j
            if not (0 <= x < W and 0 <= y < H):
                continue
            if depth is not None and px['mat'][y, x] >= 0 and px['depth'][y, x] > depth + tol:
                continue
            if only_on is not None and px['mat'][y, x] not in only_on:
                continue
            img[y, x, :3] = cmap[ch]
            img[y, x, 3] = 255
