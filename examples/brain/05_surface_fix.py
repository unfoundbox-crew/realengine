import bpy
sc=bpy.data.scenes['MVEC_FINAL']
for o in sc.objects:
 if o.name.startswith(('CTX_','HEAD_')):
  for p in o.data.polygons:p.flip()
  o.data.update()
sc.cycles.transparent_max_bounces=32;sc.cycles.samples=96
sc.render.filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/stage_anatomy_left.png'
bpy.ops.render.render(write_still=True,scene=sc.name)
