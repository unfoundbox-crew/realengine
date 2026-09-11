import bpy,gzip,base64,zlib,xml.etree.ElementTree as ET,math
import numpy as np
from pathlib import Path
sc=bpy.data.scenes['MVEC_FINAL'];base=Path('/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final')
surfs=[]
for side in ['left','right']:
 root=ET.fromstring(gzip.decompress((base/'assets'/('pial_'+side+'.gii.gz')).read_bytes()));arr={}
 for d in root.findall('DataArray'):
  dtype='<f4' if d.attrib['DataType']=='NIFTI_TYPE_FLOAT32' else '<i4';data=base64.b64decode(d.find('Data').text);data=zlib.decompress(data) if d.attrib['Encoding']=='GZipBase64Binary' else data
  arr[d.attrib['Intent']]=np.frombuffer(data,dtype=dtype).reshape(int(d.attrib['Dim0']),int(d.attrib['Dim1'])).copy()
 surfs.append((arr['NIFTI_INTENT_POINTSET'],arr['NIFTI_INTENT_TRIANGLE']))
v=np.concatenate([a for a,b in surfs]);faces=np.concatenate([surfs[0][1],surfs[1][1]+len(surfs[0][0])]);v[:,1]*=-1;faces=faces[:,::-1]
lo=v.min(axis=0);hi=v.max(axis=0);v=(v-(lo+hi)/2)/(hi-lo)*np.array([.150,.175,.135])+np.array([0,0,.060])
regions={n:[] for n in ['Frontal','Parietal','Temporal','Occipital']}
for face in faces:
 x,y,z=v[face].mean(axis=0)
 if y>.047:region='Occipital'
 elif z<.053 and y>-.047 and abs(x)>.018:region='Temporal'
 elif y>-.004+.10*(.060-z):region='Parietal'
 else:region='Frontal'
 regions[region].append(face)
for n,ff in regions.items():
 used=np.unique(np.array(ff));mapping={int(x):i for i,x in enumerate(used)};me=bpy.data.meshes.new('FSAVERAGE5_'+n);me.from_pydata(v[used].tolist(),[],[[mapping[int(i)] for i in f] for f in ff]);me.update()
 for p in me.polygons:p.use_smooth=True
 o=bpy.data.objects['CTX_'+n];o.data=me;me.materials.append(bpy.data.materials['MVEC_'+n]);o['surface_source']='Nilearn fsaverage5 pial surface';o['segmentation']='Schematic four-region spatial partition, not atlas parcellation';o.location=(0,0,0)
 sm=o.modifiers.new('Surface refinement','SUBSURF');sm.levels=1;sm.render_levels=1
bpy.data.objects['CAM_TopOrthographic'].rotation_euler=(0,0,math.pi)
sc.cycles.samples=128;sc.render.resolution_x=900;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.camera=bpy.data.objects['CAM_LeftOrthographic']
for o in sc.objects:
 if o.get('view'):o.hide_render=o['view']!=sc.camera.name
sc.render.filepath=str(base/'anatomical_surface_rgba.png');bpy.ops.render.render(write_still=True,scene=sc.name)
print('FSAVERAGE_SURFACE_IMPORTED',len(v),len(faces))
