import bpy,json
sc=bpy.data.scenes['MVEC_FINAL']
print('CAM',sc.camera.name, list(sc.camera.location),list(sc.camera.rotation_euler))
print('NODES',[(n.bl_idname,[(x.name,str(x.default_value) if hasattr(x,'default_value') else '') for x in n.inputs]) for n in sc.compositing_node_group.nodes])
print('COL',[(c.name,c.hide_render) for c in sc.collection.children])
sc.render.use_compositing=False;sc.render.filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/raw.png'
bpy.ops.render.render(write_still=True,scene=sc.name)
