import bpy,json
from pathlib import Path
sc=bpy.data.scenes['MVEC_FINAL'];OUT=Path('/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final')
names=['CAM_Master','CAM_LeftOrthographic','CAM_FrontOrthographic','CAM_TopOrthographic','CAM_ExplodedLayers','CAM_Detail']
# Render one per MCP invocation; this leaves a recoverable artifact at each step.
index=int(sc.get('next_qa',0));name=names[index];cam=bpy.data.objects[name];sc.camera=cam
for o in sc.objects:
 if o.get('view'):o.hide_render=o['view']== 'EDITABLE_CARD_SOLIDS' or o['view']!=name
for n in ['CTX_Frontal','CTX_Parietal','CTX_Temporal','CTX_Occipital']:
 o=bpy.data.objects[n];o.location=(0,0,0);o.data=bpy.data.meshes['CUTAWAY_'+n[4:]] if name=='CAM_Detail' else bpy.data.meshes[o['full_mesh']]
bpy.data.objects['HEAD_Shell'].hide_render=name in ['CAM_TopOrthographic','CAM_ExplodedLayers','CAM_Detail']
if name=='CAM_ExplodedLayers':
 for n,offset in [('CTX_Frontal',(0,-.025,.045)),('CTX_Parietal',(0,0,.062)),('CTX_Temporal',(0,-.005,.012)),('CTX_Occipital',(0,.025,.045))]:bpy.data.objects[n].location=offset
 # Show the actual, dimensioned processing stack alongside the exploded anatomy.
 for o in sc.objects:
  if o.get('view')=='STACK_PHYSICAL':o.hide_render=False
 cam.data.lens=55;cam.data.shift_x=.10
sc.render.resolution_x=2048 if name=='CAM_Master' else 1600;sc.render.resolution_y=1152 if name=='CAM_Master' else 1600
sc.render.resolution_percentage=100;sc.render.use_compositing=False;sc.cycles.samples=128
sc.render.filepath=str(OUT/('%02d_%s_rgba.png'%(index+1,name[4:])))
bpy.ops.render.render(write_still=True,scene=sc.name)
sc['next_qa']=index+1
print('QA_DONE',name)
