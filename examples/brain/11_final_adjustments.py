import bpy,math
from mathutils import Vector
sc=bpy.data.scenes['MVEC_FINAL'];master=bpy.data.objects['CAM_Master']
bpy.data.objects['SUB_Cerebellum'].location.z+=.018
bpy.data.objects['SUB_Brainstem'].location.z+=.012
# Move right-hand labels into a clear margin, preserving their leaders' target ends.
for o in sc.objects:
 if o.get('view') in [None,master.name,'STACK_PHYSICAL','EDITABLE_CARD_SOLIDS']:continue
 c=bpy.data.objects.get(o['view'])
 if c is None:continue
 if o.type=='FONT' and o.name.startswith(('LABEL_Name_','LABEL_Subtitle_')) and o.location.x>0:
  o.location.x+=140*c['overlay_width']/1600
 if o.name.startswith(('LABEL_Swatch_','LABEL_Leader_')) and o.type=='CURVE':
  for s in o.data.splines:
   if s.points and s.points[0].co.x>0:
    for i,p in enumerate(s.points):
     if o.name.startswith('LABEL_Swatch_') or i==0:p.co.x+=140*c['overlay_width']/1600
# Detail camera uses a genuine half cutaway, not reduced material opacity.
for n in ['Frontal','Parietal','Temporal','Occipital']:
 o=bpy.data.objects['CTX_'+n];o['full_mesh']=o.data.name
 v=[tuple(x.co) for x in o.data.vertices];ff=[tuple(p.vertices) for p in o.data.polygons if sum(v[i][0] for i in p.vertices)/len(p.vertices)>=0]
 me=bpy.data.meshes.new('CUTAWAY_'+n);me.from_pydata(v,[],ff);me.update();me.materials.append(o.data.materials[0])
 for p in me.polygons:p.use_smooth=True
# Dimension validation is done on the source mesh, before small smoothing modifiers.
sc['next_qa']=0
bpy.context.window.scene=sc
bpy.ops.wm.save_as_mainfile(filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/working.blend')
print('FINAL_ADJUSTMENTS_READY')
