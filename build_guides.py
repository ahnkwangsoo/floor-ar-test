from pathlib import Path
import urllib.request
import struct, json
import numpy as np
import trimesh

SRC='https://raw.githubusercontent.com/ahnkwangsoo/jungja-ar/main/src/assets/jungja.glb'
TMP=Path('jungja_source.glb')
OUT=Path('assets/jungja_guides.glb')
OUT.parent.mkdir(parents=True, exist_ok=True)
urllib.request.urlretrieve(SRC, TMP)

def align4(data: bytes, pad: bytes):
    return data + pad * ((4 - len(data) % 4) % 4)

raw=TMP.read_bytes()
magic,version,total=struct.unpack_from('<4sII',raw,0)
assert magic==b'glTF' and version==2
pos=12; chunks=[]
while pos < len(raw):
    length,ctype=struct.unpack_from('<II',raw,pos); pos += 8
    chunks.append((ctype, raw[pos:pos+length])); pos += length
json_bytes=next(b for t,b in chunks if t==0x4E4F534A)
bin_bytes=next((b for t,b in chunks if t==0x004E4942), b'')
gltf=json.loads(json_bytes.decode('utf-8').rstrip(' \t\r\n\x00'))

# Use trimesh only to read world-space bounds. Original GLB binary/material data is preserved.
scene_tm=trimesh.load(TMP, force='scene')
bmin,bmax=scene_tm.bounds
cx=float((bmin[0]+bmax[0])*0.5)
cz=float((bmin[2]+bmax[2])*0.5)
width=float(max(bmax[0]-bmin[0], bmax[2]-bmin[2]))
scale=4.0/width

buf=bytearray(bin_bytes)
def append_blob(blob: bytes, target=None):
    while len(buf)%4: buf.append(0)
    off=len(buf); buf.extend(blob)
    view={'buffer':0,'byteOffset':off,'byteLength':len(blob)}
    if target is not None: view['target']=target
    gltf.setdefault('bufferViews',[]).append(view)
    return len(gltf['bufferViews'])-1

# 70cm square frame, 56cm inner opening.
O=0.35; I=0.28
verts=np.array([
[-O,0,-O],[ O,0,-O],[ O,0, O],[-O,0, O],
[-I,0,-I],[ I,0,-I],[ I,0, I],[-I,0, I],
], dtype='<f4')
indices=np.array([
0,1,5, 0,5,4,
1,2,6, 1,6,5,
2,3,7, 2,7,6,
3,0,4, 3,4,7,
], dtype='<u2')

vview=append_blob(verts.tobytes(),34962)
iview=append_blob(indices.tobytes(),34963)
accessors=gltf.setdefault('accessors',[])
pos_acc=len(accessors)
accessors.append({'bufferView':vview,'componentType':5126,'count':8,'type':'VEC3','min':[-O,0,-O],'max':[O,0,O]})
idx_acc=len(accessors)
accessors.append({'bufferView':iview,'componentType':5123,'count':int(indices.size),'type':'SCALAR','min':[0],'max':[7]})

materials=gltf.setdefault('materials',[])
def add_material(name,base,emissive):
    idx=len(materials)
    materials.append({
        'name':name,
        'doubleSided':True,
        'alphaMode':'BLEND',
        'pbrMetallicRoughness':{
            'baseColorFactor':base,
            'metallicFactor':0.0,
            'roughnessFactor':1.0
        },
        'emissiveFactor':emissive
    })
    return idx
mat_a=add_material('Guide_A',[0.1,0.85,1.0,0.72],[0.1,0.6,0.8])
mat_b=add_material('Guide_B',[1.0,0.72,0.05,0.72],[0.8,0.45,0.02])

meshes=gltf.setdefault('meshes',[])
def add_mesh(name,material):
    idx=len(meshes)
    meshes.append({'name':name,'primitives':[{'attributes':{'POSITION':pos_acc},'indices':idx_acc,'material':material,'mode':4}]})
    return idx
mesh_a=add_mesh('Guide_A_Frame',mat_a)
mesh_b=add_mesh('Guide_B_Frame',mat_b)

nodes=gltf.setdefault('nodes',[])
def add_node(obj):
    idx=len(nodes); nodes.append(obj); return idx
scene_index=gltf.get('scene',0)
scene_def=gltf.setdefault('scenes',[{'nodes':[]}])[scene_index]
original_roots=list(scene_def.get('nodes',[]))
model_wrapper=add_node({
    'name':'Jungja_Normalized',
    'children':original_roots,
    'scale':[scale,scale,scale],
    'translation':[-scale*cx,-scale*float(bmin[1]),-scale*cz]
})
guide_a=add_node({'name':'Guide_A','mesh':mesh_a,'translation':[-1.2,0.01,1.15]})
guide_b=add_node({'name':'Guide_B','mesh':mesh_b,'translation':[1.2,0.01,1.15]})
root=add_node({'name':'AR_Alignment_Root','children':[model_wrapper,guide_a,guide_b]})
scene_def['nodes']=[root]

gltf.setdefault('buffers',[{}])[0]['byteLength']=len(buf)
json_out=align4(json.dumps(gltf,separators=(',',':'),ensure_ascii=False).encode('utf-8'), b' ')
bin_out=align4(bytes(buf), b'\x00')
total_len=12+8+len(json_out)+8+len(bin_out)
out=bytearray(struct.pack('<4sII',b'glTF',2,total_len))
out.extend(struct.pack('<II',len(json_out),0x4E4F534A)); out.extend(json_out)
out.extend(struct.pack('<II',len(bin_out),0x004E4942)); out.extend(bin_out)
OUT.write_bytes(out)
print('wrote', OUT, OUT.stat().st_size)
