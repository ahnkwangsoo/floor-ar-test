from pathlib import Path
import urllib.request
import numpy as np
import trimesh

SRC='https://raw.githubusercontent.com/ahnkwangsoo/jungja-ar/main/src/assets/jungja.glb'
TMP=Path('jungja_source.glb')
OUT=Path('assets/jungja_guides.glb')
OUT.parent.mkdir(parents=True, exist_ok=True)

urllib.request.urlretrieve(SRC, TMP)
scene=trimesh.load(TMP, force='scene')

# Diagnose and normalize any RGB-only color data before GLB export.
for name, geom in scene.geometry.items():
    visual = getattr(geom, 'visual', None)
    kind = getattr(visual, 'kind', None) if visual is not None else None
    try:
        colors = np.asarray(visual.vertex_colors)
        print('VIS', name, type(visual).__name__, 'kind=', kind, 'vertex_colors=', colors.shape)
        if colors.ndim == 2 and colors.shape[1] == 3:
            alpha = np.full((colors.shape[0], 1), 255, dtype=colors.dtype)
            visual.vertex_colors = np.concatenate([colors, alpha], axis=1)
        elif colors.ndim == 1 and colors.size % 3 == 0:
            colors = colors.reshape((-1, 3))
            alpha = np.full((colors.shape[0], 1), 255, dtype=colors.dtype)
            visual.vertex_colors = np.concatenate([colors, alpha], axis=1)
    except Exception as exc:
        print('VIS', name, type(visual).__name__ if visual is not None else None, 'kind=', kind, 'no vertex colors:', exc)

    attrs = getattr(geom, 'vertex_attributes', {})
    for key, value in attrs.items():
        arr = np.asarray(value)
        print('ATTR', name, key, arr.shape, arr.dtype)
        if key.upper() in ('COLOR_0', '_COLOR_0'):
            if arr.ndim == 2 and arr.shape[1] == 3:
                alpha = np.ones((arr.shape[0], 1), dtype=arr.dtype)
                geom.vertex_attributes[key] = np.concatenate([arr, alpha], axis=1)
            elif arr.ndim == 1 and arr.size % 3 == 0:
                arr = arr.reshape((-1, 3))
                alpha = np.ones((arr.shape[0], 1), dtype=arr.dtype)
                geom.vertex_attributes[key] = np.concatenate([arr, alpha], axis=1)

# Normalize to approx. 4m width and place floor at Y=0.
bmin,bmax=scene.bounds
width=float(bmax[0]-bmin[0])
scale=4.0/width
T=trimesh.transformations.scale_matrix(scale)
scene.apply_transform(T)
bmin,bmax=scene.bounds
cx=(bmin[0]+bmax[0])*0.5
cz=(bmin[2]+bmax[2])*0.5
scene.apply_translation((-cx,-bmin[1],-cz))

# Two 70cm alignment pads, 2.4m apart, near front edge.
mat=trimesh.visual.material.PBRMaterial(
    name='AlignmentGuide',
    baseColorFactor=[255,255,255,105],
    metallicFactor=0.0,
    roughnessFactor=1.0,
    alphaMode='BLEND',
    doubleSided=True,
)

def pad(x,z,name):
    m=trimesh.creation.box(extents=(0.70,0.015,0.70))
    m.apply_translation((x,0.0075,z))
    m.visual=trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(m,node_name=name,geom_name=name)

pad(-1.2,1.15,'Guide_A')
pad( 1.2,1.15,'Guide_B')
scene.export(OUT)
print('wrote',OUT,OUT.stat().st_size)
