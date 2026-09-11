import bpy,math
from mathutils import Vector
sc=bpy.data.scenes['MVEC_FINAL'];tree=sc.compositing_node_group
ao=next(n for n in tree.nodes if n.bl_idname=='CompositorNodeAlphaOver');rl=next(n for n in tree.nodes if n.bl_idname=='CompositorNodeRLayers')
for l in list(tree.links):
 if l.to_node==ao:tree.links.remove(l)
ao.inputs['Background'].default_value=(15,15,15,1);tree.links.new(rl.outputs['Image'],ao.inputs['Foreground']);sc.render.use_compositing=True
for o in sc.objects:
 if o.type=='LIGHT':o.data.energy*=.45
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25
cam=bpy.data.objects['CAM_LeftOrthographic'];cam.location=(.6,0,.02);cam.rotation_euler=(Vector((0,0,.02))-cam.location).to_track_quat('-Z','Y').to_euler()
sc.camera=cam;sc.cycles.samples=48;sc.render.filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/stage_anatomy_left.png'
bpy.ops.render.render(write_still=True,scene=sc.name)
