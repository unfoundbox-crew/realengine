import bpy
from pathlib import Path
sc=bpy.data.scenes['MVEC_FINAL'];OUT=Path('/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final')
tree=bpy.data.node_groups.new('MVEC white compositing','CompositorNodeTree');tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor');sc.compositing_node_group=tree
rl=tree.nodes.new('CompositorNodeRLayers');rl.scene=sc;ao=tree.nodes.new('CompositorNodeAlphaOver');ao.inputs[1].default_value=(1,1,1,1);tree.links.new(rl.outputs['Image'],ao.inputs[2]);co=tree.nodes.new('NodeGroupOutput');tree.links.new(ao.outputs[0],co.inputs['Image'])
sc.camera=bpy.data.objects['CAM_LeftOrthographic'];sc.render.filepath=str(OUT/'stage_anatomy_left.png');bpy.context.window.scene=sc
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'working.blend'))
bpy.ops.render.render(write_still=True,scene=sc.name)
