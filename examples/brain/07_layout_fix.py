import bpy,math
from mathutils import Vector
sc=bpy.data.scenes['MVEC_FINAL']
for o in sc.objects:
 if o.get('view') and o.type=='FONT':o.location.z+=.008
 if o.get('view') and o.type=='CURVE':
  for s in o.data.splines:
   for p in s.points:p.co.z+=.008
 if o.name.startswith('CTRL_'):
  for m in o.modifiers:
   if m.type=='SOLIDIFY':m.thickness=.003;m.offset=0
# White UI cards are unlit graphic elements, with enough display brightness after AgX.
m=bpy.data.materials['MVEC Card'];next(n for n in m.node_tree.nodes if n.type=='EMISSION').inputs['Strength'].default_value=4
# Keep the head above the control band and leave breathing room for the cortical key.
c=bpy.data.objects['CAM_Master'];c.location*=1.13;c.rotation_euler=(Vector((0,0,-.004))-c.location).to_track_quat('-Z','Y').to_euler()
sc.cycles.samples=128;sc.render.resolution_percentage=60;sc.render.filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/master_preview_rgba.png'
bpy.ops.render.render(write_still=True,scene=sc.name)
