"""Exporting props: materials (toon_solid by vertex colour; an emissive one for lamp paper and fire),
the mesh, the scene with its anchor markers, the faded (遠化) twin and the catalog entry."""
from __future__ import annotations

import numpy as np

LIT = (1.0, 0.70, 0.40)          # lamp light colour (paper lit from inside), sRGB


def materials(a, porosity=0.7, cutaway=False, lit_energy=2.4, keys=('solid',)):
    """Material res paths by key: solid, roof (thatch: porous), noline (no outline: tiny bits), lit
    (emissive at dusk and night), paper (unlit lamp paper). A roof no longer stipples away over her:
    a hole in it showed the hut's inside but not her, behind its back wall; the renderer draws her
    silhouette through whatever covers her instead (render3d/shaders/sprite_xray.gdshader)."""
    m = {}
    if 'solid' in keys:
        m['solid'] = a.material('solid', 'toon_solid.gdshader', {'albedo_mode': 0, 'porosity': porosity, 'cutaway': cutaway})
    if 'roof' in keys:
        m['roof'] = a.material('roof', 'toon_solid.gdshader', {'albedo_mode': 0, 'porosity': 0.9, 'cutaway': False})
    if 'noline' in keys:
        m['noline'] = a.material('noline', 'toon_solid_noline.gdshader', {'albedo_mode': 0, 'porosity': porosity})
    if 'lit' in keys:
        m['lit'] = a.material('lit', 'toon_solid.gdshader', {'albedo_mode': 0, 'porosity': 0.2, 'dither': 0.0,
                                                               'emission_color': list(LIT), 'emission_energy': lit_energy,
                                                               'emission_at_night': 0.8})
    if 'paper' in keys:
        m['paper'] = a.material('paper', 'toon_solid.gdshader', {'albedo_mode': 0, 'porosity': 0.4})
    if 'shoji' in keys:
        # paper screens lit from inside after dusk: warm, below the bloom threshold (the renderer may
        # retune it for its continuous light; knowledge/25)
        m['shoji'] = a.material('shoji', 'toon_solid.gdshader', {'albedo_mode': 0, 'porosity': 0.4, 'emission_color': [1.0, 0.74, 0.42],
                                                                   'emission_energy': 0.9, 'emission_at_night': 1.0})
    if 'sway' in keys:
        # cloth, paper strips, hanging things: the foliage material in mesh mode, each piece a sway group
        m['sway'] = a.material('sway', 'toon_foliage.gdshader', {'foliage_mode': 0, 'wind_px': 1.5, 'porosity': 0.7,
                                                                 'cutaway': False, 'transmit': 0.25})
    if 'swaynl' in keys:
        m['swaynl'] = a.material('swaynl', 'toon_foliage_noline.gdshader', {'foliage_mode': 0, 'wind_px': 1.5, 'porosity': 0.7,
                                                                            'cutaway': False, 'transmit': 0.25})
    return m


def export_prop(out, name, category, prop, catalog, porosity=0.7, cutaway=False, far=True, markers=None,
                variants=None, meta=None, lit_energy=2.4, budget=2000, ground=True, script=None, extras=None,
                cards=None, asset=None):
    """prop: kit.Prop. variants: {key: kit.Prop} extra scenes <name>_<key>.tscn sharing the materials
    (e.g. 'lit'). extras: {node name: (kit.Prop, pos)} separate meshes as their own nodes (things the
    story moves or takes: the dango, a beam), with their faded twins in the far scene. Material keys
    used by pieces: solid / roof / noline / lit / paper. Returns stats."""
    a = asset if asset is not None else out.asset(name, category)
    keys = {pc.mat for pc in prop.pieces}
    for v in (variants or {}).values():
        keys |= {pc.mat for pc in v.pieces}
    for ev in (extras or {}).values():
        keys |= {pc.mat for pc in ev[0].pieces}
    if far:
        keys.add('solid')
    mats = materials(a, porosity=porosity, cutaway=cutaway, lit_energy=lit_energy, keys=tuple(sorted(keys)))

    def mesh_of(p, key, pale=False, with_cards=False):
        parts = p.finish(pale=pale, ground=ground)
        surfaces = []
        for k in sorted(parts):
            mk = k
            if pale and k in ('lit', 'shoji'):          # a faded lamp does not glow
                mk = 'paper' if 'paper' in mats else 'solid'
                if mk not in mats:
                    mats[mk] = materials(a, porosity=porosity, keys=(mk,))[mk]
            surfaces.append((mats[mk], parts[k]))
        if with_cards and cards:
            surfaces += list(cards)
        return a.mesh(key, surfaces)

    extra_mesh = {}
    for en, ev in (extras or {}).items():
        ep, epos = ev[0], ev[1]
        over = ev[2] if len(ev) > 2 else {}
        extra_mesh[en] = (mesh_of(ep, en.lower()), mesh_of(ep, en.lower() + '_far', pale=True) if far else None, epos, ep.tris,
                          over)

    def nodes_for(mesh, pale=False, variant=None):
        nd = [{'name': 'Mesh', 'type': 'mesh', 'mesh': mesh}]
        for en, (m_n, m_f, epos, _, over) in extra_mesh.items():
            o = over.get(variant, {})
            n = {'name': en, 'type': 'mesh', 'mesh': m_f if (pale and m_f) else m_n,
                 'pos': [float(x) for x in o.get('pos', epos)], 'meta': {'w3a_far_mesh': m_f or '', 'w3a_mesh': m_n}}
            if 'rot' in o:
                n['rot'] = [float(x) for x in o['rot']]
            nd.append(n)
        for mname, pos in (markers or {}).items():
            if isinstance(pos[0], (list, tuple)):
                for i, q in enumerate(pos):
                    nd.append({'name': f'{mname}_{i}', 'type': 'marker', 'pos': [float(x) for x in q]})
            else:
                nd.append({'name': mname, 'type': 'marker', 'pos': [float(x) for x in pos]})
        return nd
    base_meta = {'w3a_kind': category}
    base_meta.update(meta or {})
    m0 = mesh_of(prop, 'mesh', with_cards=True)
    a.scene(nodes_for(m0), meta=base_meta, script=script)
    tris = {'': prop.tris + sum(len(md.arrays()['idx']) for _, md in (cards or []))}
    if far:
        mf = mesh_of(prop, 'far_mesh', pale=True)
        a.scene(nodes_for(mf, pale=True), meta=dict(base_meta, w3a_far=True), key='far', script=script)
    for key, vp in (variants or {}).items():
        mv = mesh_of(vp, key + '_mesh', with_cards=True)
        a.scene(nodes_for(mv, variant=key), meta=dict(base_meta, w3a_variant=key), key=key, script=script)
        tris[key] = vp.tris
        if far and key != 'lit':
            mvf = mesh_of(vp, key + '_far_mesh', pale=True)
            a.scene(nodes_for(mvf, pale=True, variant=key), meta=dict(base_meta, w3a_variant=key, w3a_far=True), key=key + '_far',
                    script=script)
    cat = dict(catalog)
    cat.setdefault('category', category)
    vs = {}
    if far:
        vs['far'] = f'res://world3d/assets/{a.rel}/{name}_far.tscn'
    for key in (variants or {}):
        vs[key] = f'res://world3d/assets/{a.rel}/{name}_{key}.tscn'
        if far and key != 'lit':
            vs[key + '_far'] = f'res://world3d/assets/{a.rel}/{name}_{key}_far.tscn'
    if vs:
        cat['variants'] = vs
    if markers:
        anc = dict(cat.get('anchors', {}))
        for k, v in markers.items():
            anc.setdefault(k, v)
        cat['anchors'] = anc
    lo, hi = prop.bounds()
    cat.setdefault('height', round(float(hi[1]), 2))
    cat.setdefault('size', [round(float(x), 2) for x in (hi - lo)])
    a.catalog = cat
    ex = sum(v[3] for v in extra_mesh.values())
    for k, t in tris.items():
        assert t + ex <= budget, f'{name}{k}: {t + ex} triangles > budget {budget}'
    if ex:
        tris['extras'] = ex
    return {k or 'base': t for k, t in tris.items()}
