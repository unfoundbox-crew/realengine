import bpy,json
from mathutils import Vector
sc=bpy.data.scenes['MVEC_FINAL'];c=bpy.data.objects['CAM_Master'];dg=bpy.context.evaluated_depsgraph_get()
for n in ['LABEL_Prediction_0','CTRL_Prediction_0','LABEL_LevelText_0','CTRL_LayerLegend_0']:
 o=bpy.data.objects[n];print(n,o.location[:],[(c.matrix_world.inverted()@o.matrix_world@Vector(v)).z for v in o.bound_box],o.data.materials[0].name)
print('ENGINE',sc.render.engine,sc.camera.name)
