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

# Normalize color attributes to RGBA for trimesh 5.x GLB export.
for name, geom in scene.geometry.items():
    visual = getattr(geom, 'visual', None)
    if visual is None:
        continue

    # ColorVisuals path
    if getattr(visual, 'kind', None) in ('vertex', 'face'):
        colors = np.asarray(visual.vertex_colors)
        if colors.ndim == 2 and colors.shape[1] == 3:
            alpha = np.full((colors.shape[0], 1), 255, dtype=colors.dtype)
            visual.vertex_colors = np.concatenate([colors, alpha], axis=1)

    # TextureVisuals stores custom per-vertex values in a DataStore.
    vattrs = getattr(visual, 'vertex_attributes', None)
    if vattrs is not None and 'color' in vattrs:
        colors = np.asarray(vattrs['color'])
        print('COLOR ATTR', name, colors.shape, colors.dtype)
        if colors.ndim == 2 and colors.shape[1] == 3:
            alpha_value = 255 if np.issubdtype(colors.dtype, np.integer) else 1.0
            alpha = np.full((colors.shape[0], 1), alpha_value, dtype=colors.dtype)
            vattrs['color'] = np.concatenate([colors, alpha], axis=1)
        elif colors.ndim == 1 and colors.size % 3 == 0:
            colors = colors.reshape((-1, 3))
            alpha_value = 255 if np.issubdtype(colors.dtype, np.integer) else 1.0
            alpha = np.full((colors.shape[0], 1), alpha_value, dtype=colors.dtype)
            vattrs['color'] = np.concatenate([colors, alpha], axis=1)

# Normalize to approx. 4m width and place floor at Y=0.
bmin,bmax=scene.bounds
width=float(bmax[0]-bmin[0])
scale=4.0/width
scene.apply_transform(trimesh.transformations.scale_matrix(scale))
bmin,bmax=scene.bounds
cx=(bmin[0]+bmax[0])*0.5
cz=(bmin[2]+bmax[2])*0.5
scene.apply_translation((-cx,-bmin[1],-cz))

# Two 70cm semi-transparent alignment pads, 2.4m apart.
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
print('wrote', OUT, OUT.stat().st_size)
