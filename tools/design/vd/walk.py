"""Walkability from the registry: one grid, every unwalkable cell carries its cause, and a check that
the walkable ground inside the realm is closed off by visible things except at the three gates (no
air walls: G5R3-48, charter F-1)."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from . import registry as reg

OK, SLOPE, WATER, SOLID, WALL, THICKET, BUILDING, TREE = 0, 1, 2, 3, 4, 5, 6, 7
CAUSE_NAMES = {SLOPE: "陡坡与崖（>35°）", WATER: "水面", SOLID: "岩石与实心物件", WALL: "石垣与瑞垣",
               THICKET: "篠竹丛", BUILDING: "建筑", TREE: "树干与根"}
CAUSE_COLORS = {SLOPE: "#a0673f", WATER: "#3f7d97", SOLID: "#6b665c", WALL: "#7a4f8a", THICKET: "#4f6b2f",
                BUILDING: "#8a5a2b", TREE: "#3d5a3a"}
MAX_SLOPE = 35.0


class Walk:
    def __init__(self, R, T, trees_by_planting):
        self.R, self.T = R, T
        X, Y = T.X, T.Y
        cause = np.zeros(X.shape, dtype=np.uint8)
        cause[T.slope > MAX_SLOPE] = SLOPE
        # water: the streams' surfaces where wider than 0.8 m
        for w in R["water"]:
            if w.get("collision") == "solid_water":
                P, _ = reg.resample(w["pts"], 0.25)
                m, d, i = T._nearest(P[:, :2], X, Y, float(P[:, 3].max()) / 2 + 0.2)
                idx = np.where(m)
                half = P[np.clip(i, 0, len(P) - 1), 3] / 2.0
                wide = P[np.clip(i, 0, len(P) - 1), 3] >= 0.8
                hit = np.isfinite(d) & (d <= half) & wide
                sub = cause[idx]
                sub[hit] = WATER
                cause[idx] = sub
            elif w.get("collision") == "solid" and w["id"].startswith("WA-FAL"):
                cause[np.hypot(X - w["pos"][0], Y - w["pos"][1]) < 1.2] = WATER
        # thickets
        for pl in R["plantings"]:
            if pl.get("collision") == "solid" and pl.get("poly"):
                cause[reg.points_in_poly(X, Y, pl["poly"])] = THICKET
        # planting trunks
        for pid, trees in trees_by_planting.items():
            for t in trees:
                r = t["trunk_r"]
                x0, y0 = t["x"], t["y"]
                sl = self._window(x0, y0, r + 0.5)
                if sl is None:
                    continue
                sub = np.hypot(X[sl] - x0, Y[sl] - y0) <= r
                cause[sl][sub] = TREE
        # elements
        self.walk_mask = np.zeros(X.shape, dtype=bool)
        self.climb_mask = np.zeros(X.shape, dtype=bool)
        for e in R["elements"]:
            col = e.get("collision")
            shapes = reg.footprint_shapes(e)
            if not shapes:
                continue
            m = self._raster(shapes)
            if col == "solid":
                c = SOLID
                if e["cat"] == "BL":
                    c = BUILDING
                elif e["cat"] == "TR" or e["cat"] == "SH":
                    c = TREE
                elif e["kind"] in ("GAK", "MZG"):
                    c = WALL
                cause[m] = c
            elif col == "walk":
                self.walk_mask |= m
            elif col == "climb":
                self.climb_mask |= m
                cause[m] = TREE           # the low part of the G limb blocks from the side
        # built walkable surfaces: steps, bridges, the engawa, platforms
        for rd in R["roads"]:
            if rd["kind"] in ("DAN", "KIR", "NOB", "TOB"):
                d = reg.dist_to_polyline(X, Y, rd["pts"])
                self.walk_mask |= d <= rd["w"] / 2.0
        for e in R["elements"]:
            if e.get("engawa"):
                self.walk_mask |= reg.points_in_poly(X, Y, e["engawa"]["poly"])
            if e["kind"] == "HAS":
                d = reg.dist_to_polyline(X, Y, e["pts"])
                self.walk_mask |= d <= e["size"][1] / 2.0
        cause[self.walk_mask & (cause != BUILDING)] = OK
        self.cause = cause
        self.ok = cause == OK

    def _window(self, x, y, r):
        T = self.T
        i0 = int(np.floor((y - r - T.y0) / T.cell))
        i1 = int(np.ceil((y + r - T.y0) / T.cell)) + 1
        j0 = int(np.floor((x - r - T.x0) / T.cell))
        j1 = int(np.ceil((x + r - T.x0) / T.cell)) + 1
        if i1 <= 0 or j1 <= 0 or i0 >= T.X.shape[0] or j0 >= T.X.shape[1]:
            return None
        return (slice(max(i0, 0), min(i1, T.X.shape[0])), slice(max(j0, 0), min(j1, T.X.shape[1])))

    def _raster(self, shapes):
        T = self.T
        m = np.zeros(T.X.shape, dtype=bool)
        for sh in shapes:
            if sh[0] == "circle":
                _, x, y, r = sh
                sl = self._window(x, y, r + 0.5)
                if sl is None:
                    continue
                m[sl] |= np.hypot(T.X[sl] - x, T.Y[sl] - y) <= r + 0.25
            elif sh[0] == "poly":
                P = np.asarray(sh[1])
                x0, y0 = P.min(axis=0)
                x1, y1 = P.max(axis=0)
                sl = self._window((x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 + 1)
                if sl is None:
                    continue
                m[sl] |= reg.points_in_poly(T.X[sl], T.Y[sl], sh[1])
            elif sh[0] == "line":
                P = np.asarray(sh[1])
                x0, y0 = P.min(axis=0)
                x1, y1 = P.max(axis=0)
                sl = self._window((x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 + sh[2] + 1)
                if sl is None:
                    continue
                m[sl] |= reg.dist_to_polyline(T.X[sl], T.Y[sl], sh[1]) <= max(sh[2] / 2.0, 0.26)
        return m

    # ------------------------------------------------------------------------------------------------
    def realm_check(self):
        """Close the three gates, flood the walkable ground from the yard, and report where it leaves the
        realm polygon (an air wall would be needed there)."""
        R, T = self.R, self.T
        ok = self.ok.copy()
        for g in R["boundary"]["gates"]:
            (ax, ay), (bx, by) = g["between"]
            d = reg.dist_to_polyline(T.X, T.Y, [[ax, ay], [bx, by]])
            ok &= ~(d < 1.6)
        lab, n = ndimage.label(ok)
        seed = R["_index"]["BL-MIN-01"]["pos"]
        si = int(round((seed[1] - 6.0 - T.y0) / T.cell))
        sj = int(round((seed[0] - T.x0) / T.cell))
        comp = lab == lab[si, sj]
        inside = reg.points_in_poly(T.X, T.Y, R["boundary"]["poly"])
        # tolerance: 1.5 m outside the boundary line still counts as the edge zone
        dist_out = ndimage.distance_transform_edt(~inside) * T.cell
        leak = comp & ~inside & (dist_out > 1.5)
        pts = np.stack([T.X[leak], T.Y[leak]], axis=1) if leak.any() else np.zeros((0, 2))
        return {"component_cells": int(comp.sum()), "leak_cells": int(leak.sum()), "leak_pts": pts,
                "inside_walkable_m2": float((comp & inside).sum() * T.cell * T.cell), "comp": comp}

    def edge_causes(self):
        """Unwalkable cells that touch walkable ones, with their cause (for drawing the edge)."""
        okd = ndimage.binary_dilation(self.ok, iterations=1)
        edge = okd & ~self.ok
        return edge
