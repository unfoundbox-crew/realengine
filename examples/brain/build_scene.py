import bpy, math
from mathutils import Vector

# Deterministic construction for the supplied MVEC brain handoff.
OUT = '/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/mvec_brain_predictive_control.blend'
RDIR = '/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/renders'
scene=bpy.data.scenes.new('MVEC_Brain_Predictive_Control')
bpy.context.window.scene=scene
root=scene.collection
base=bpy.data.collections.new('SCENE'); root.children.link(base)
cols={}
for n in ['00_REFERENCE','01_HEAD','02_BRAIN_CORTEX','03_SUBCORTICAL','04_FLOW_ARROWS','05_LAYER_STACK','06_CONTROL_LOOP','07_LABELS','08_LEGENDS','09_CAMERAS','10_LIGHTS']:
 c=bpy.data.collections.new(n); root.children.link(c); cols[n]=c
def link(o,c):
 for q in list(o.users_collection): q.objects.unlink(o)
 c.objects.link(o)
def mat(name,hex,alpha=1):
 m=bpy.data.materials.new(name); m.diffuse_color=tuple(int(hex[i:i+2],16)/255 for i in (1,3,5))+(alpha,); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=m.diffuse_color; p.inputs['Roughness'].default_value=.45; p.inputs['Alpha'].default_value=alpha
 if alpha<1: m.surface_render_method='DITHERED'
 return m
M={k:mat(k,v,a) for k,v,a in [('head','#E8EEF3',.1),('frontal','#7EA6FF',.58),('parietal','#82D6A4',.58),('temporal','#F0C96C',.58),('occipital','#A989D8',.58),('cyan','#35C9D6',.9),('teal','#38AFA5',.9),('coral','#E58982',.9),('orange','#E99B55',.9),('gray','#AEB8C2',.9),('pink','#C87086',.9),('white','#F8FAFC',1),('ink','#1F2937',1)]}
def uv(n,loc,scale,ma,col):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc); o=bpy.context.object; o.name=n; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); link(o,cols[col]); bpy.ops.object.shade_smooth(); return o
def cube(n,loc,scale,ma,col,bevel=.003):
 bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=n; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); link(o,cols[col]); b=o.modifiers.new('Rounded','BEVEL'); b.width=bevel;b.segments=3; return o
def text(n,s,loc,size,col='07_LABELS'):
 bpy.ops.object.text_add(location=loc,rotation=(math.radians(78),0,0)); o=bpy.context.object;o.name=n;o.data.body=s;o.data.align_x='CENTER';o.data.size=size;o.data.extrude=.00035;o.data.materials.append(M['ink']);link(o,cols[col]);return o
def curve(n,pts,ma,col,bevel=.0012):
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.bevel_depth=bevel;cu.bevel_resolution=3;sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(pts)-1)
 for p,co in zip(sp.bezier_points,pts):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
 o=bpy.data.objects.new(n,cu);cu.materials.append(ma);cols[col].objects.link(o);return o
# head shell and simplified brain envelope
uv('HEAD_Shell',(0,.035,.02),(.087,.108,.12),M['head'],'01_HEAD')
uv('BRAIN_Base',(0,-.003,.045),(.075,.087,.068),M['gray'],'02_BRAIN_CORTEX')
# cortical lobes: readable separate smooth volumes
uv('CTX_Frontal',(-.039,-.03,.065),(.04,.055,.06),M['frontal'],'02_BRAIN_CORTEX')
uv('CTX_Parietal',(.035,-.02,.07),(.041,.055,.061),M['parietal'],'02_BRAIN_CORTEX')
uv('CTX_Temporal',(-.043,-.005,.02),(.039,.052,.033),M['temporal'],'02_BRAIN_CORTEX')
uv('CTX_Occipital',(.062,.01,.045),(.022,.038,.045),M['occipital'],'02_BRAIN_CORTEX')
# required subcortical structures
uv('SUB_Thalamus',(0,-.065,.04),(.018,.014,.013),M['cyan'],'03_SUBCORTICAL')
uv('SUB_Hippocampus',(-.015,-.055,.017),(.026,.009,.008),M['teal'],'03_SUBCORTICAL')
uv('SUB_Amygdala',(-.034,-.064,.016),(.008,.008,.008),M['parietal'],'03_SUBCORTICAL')
uv('SUB_BasalGanglia',(.02,-.055,.027),(.015,.012,.012),M['coral'],'03_SUBCORTICAL')
uv('SUB_Cerebellum',(.035,.057,-.004),(.032,.022,.022),M['orange'],'03_SUBCORTICAL')
uv('SUB_Brainstem',(0,.025,-.055),(.01,.009,.034),M['gray'],'03_SUBCORTICAL')
uv('SUB_ACC',(-.005,-.052,.058),(.032,.006,.007),M['pink'],'03_SUBCORTICAL')
# five processing layers, deliberately separate
layers=[('L5 Language & Social Cognition','#A989D8'),('L4 Abstract Reasoning & Planning','#7EA6FF'),('L3 World Model / Internal Simulation','#82D6A4'),('L2 Perception & Representation','#F0C96C'),('L1 Sensorimotor & Homeostasis','#E58982')]
for i,(lab,h) in enumerate(layers):
 z=.12-i*.018; o=cube('LAYER_'+str(5-i),(.18,.02,z),(.06,.025,.002),mat('layer'+str(i),h,.58),'05_LAYER_STACK');text('LABEL_'+str(5-i),lab,(.18,-.012,z-.001),.007)
 for j in range(5): uv('LAYER_%d_NODE_%d'%(5-i,j),(.14+j*.02,.016,z+.005),(.0025,.0025,.0025),M['white'],'05_LAYER_STACK')
# control-loop cards and connecting curves
cards=['Environment','Perception','Internal Model','Comparison','Update','Decision','Action']
for i,s in enumerate(cards):
 x=.135+i*.044; cube('CTRL_'+s.replace(' ',''),(x,-.12,-.03),(.018,.008,.005),M['white'],'06_CONTROL_LOOP');text('LABEL_CTRL_'+str(i),s,(x,-.132,-.032),.0045)
for i in range(len(cards)-1): curve('FLOW_'+str(i),[(.135+i*.044,-.12,-.025),(.157+i*.044,-.12,-.025)],M['ink'],'04_FLOW_ARROWS',.0008)
curve('FLOW_Feedback',[(.4,-.12,-.025),(.42,-.12,.0),(.12,-.12,.0),(.135,-.12,-.025)],M['ink'],'04_FLOW_ARROWS',.0008)
# prediction loop vertical cards
for i,s in enumerate(['Perceive','Encode','Predict','Compare','Update','Plan & Decide','Act','Environment']):
 z=.105-i*.019; cube('CTRL_PIPE_'+str(i),(-.16,-.1,z),(.026,.008,.006),M['white'],'06_CONTROL_LOOP');text('LABEL_PIPE_'+str(i),s,(-.16,-.112,z-.002),.0045)
 if i: curve('FLOW_PIPE_'+str(i),[(-.16,-.1,z+.009),(-.16,-.1,z+.016)],M['ink'],'04_FLOW_ARROWS',.0009)
# title and key labels
text('LABEL_Title','Human Brain: A Layered Predictive Control System',(0,-.145,.16),.011)
for n,s,l in [('Frontal','Prefrontal Cortex',(-.09,-.14,.09)),('Parietal','Parietal Cortex',(.09,-.14,.1)),('Temporal','Temporal Cortex',(-.09,-.14,.03)),('Occipital','Occipital Cortex',(.1,-.14,.04)),('Thalamus','Thalamus',(0,-.14,.015)),('Hippocampus','Hippocampus',(-.04,-.14,-.005)),('Amygdala','Amygdala',(-.1,-.14,-.02)),('Cerebellum','Cerebellum',(.09,-.14,-.025)),('Brainstem','Brainstem',(0,-.14,-.07))]: text('LABEL_'+n,s,l,.006)
# cameras
def camera(n,loc,ortho=False):
 bpy.ops.object.camera_add(location=loc);o=bpy.context.object;o.name=n;o.data.type='ORTHO' if ortho else 'PERSP';o.data.lens=60;o.data.ortho_scale=.5 if ortho else 6;link(o,cols['09_CAMERAS']);direction=Vector((0,0,.04))-o.location;o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();return o
cams=[camera('CAM_Master',(.35,-.52,.27)),camera('CAM_LeftOrthographic',(-.5,-.02,.05),True),camera('CAM_FrontOrthographic',(0,-.55,.05),True),camera('CAM_TopOrthographic',(0,-.02,.55),True),camera('CAM_ExplodedLayers',(.48,-.55,.32)),camera('CAM_Detail',(.22,-.38,.14))]
bpy.context.scene.camera=cams[0]
for n,loc,energy,size in [('LIGHT_Key',(.2,-.3,.35),1000,.3),('LIGHT_Fill',(-.3,-.2,.2),500,.3),('LIGHT_Rim',(.2,.3,.3),300,.2)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=n;o.data.energy=energy;o.data.shape='DISK';o.data.size=size;link(o,cols['10_LIGHTS']);o.rotation_euler=(0,0,0)
sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.render.engine='BLENDER_EEVEE_NEXT';sc.render.resolution_x=2048;sc.render.resolution_y=1152;sc.render.resolution_percentage=50;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False;sc.world.color=(.96,.97,.98)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
