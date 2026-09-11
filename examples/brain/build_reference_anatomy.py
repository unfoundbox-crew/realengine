import bpy, math
from mathutils import Vector
sc=bpy.data.scenes.get('MVEC_Brain_ReferenceFaithful') or bpy.data.scenes.new('MVEC_Brain_ReferenceFaithful'); bpy.context.window.scene=sc; root=sc.collection
names=['00_REFERENCE','01_HEAD','02_BRAIN_CORTEX','03_SUBCORTICAL','04_FLOW_ARROWS','05_LAYER_STACK','06_CONTROL_LOOP','07_LABELS','08_LEGENDS','09_CAMERAS','10_LIGHTS']
for n in names:
 c=bpy.data.collections.get(n) or bpy.data.collections.new(n)
 if n not in {x.name for x in root.children}: root.children.link(c)
cols={c.name:c for c in root.children}
def link(o,n):
 for c in list(o.users_collection):c.objects.unlink(o)
 cols[n].objects.link(o)
def m(n,h,a=1):
 x=bpy.data.materials.get(n) or bpy.data.materials.new(n);x.diffuse_color=tuple(int(h[i:i+2],16)/255 for i in(1,3,5))+(a,);return x
P={'F':m('MAT_Frontal','#6495ED',.62),'P':m('MAT_Parietal','#4CAF50',.62),'T':m('MAT_Temporal','#FFB74D',.62),'O':m('MAT_Occipital','#9C66CC',.62),'H':m('MAT_Head','#B5D8E6',.12),'S':m('MAT_Thalamus','#EF5350'),'I':m('MAT_Hippocampus','#00BCD4'),'A':m('MAT_Amygdala','#FF8A65'),'B':m('MAT_BasalGanglia','#BA68C8'),'C':m('MAT_Cerebellum','#F48FB1'),'G':m('MAT_Brainstem','#9E9E9E')}
def uv(n,loc,scale,ma,col):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=loc);o=bpy.context.object;o.name=n;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma);link(o,col);bpy.ops.object.shade_smooth();return o
# transparent head envelope and bilateral gyri, driven by top/lateral proportions
uv('HEAD_Shell',(0,0,.02),(.088,.108,.12),P['H'],'01_HEAD')
regions=[('CTX_Frontal','F',-.035,.035,.058,.055),('CTX_Parietal','P',.02,.035,.058,.052),('CTX_Temporal','T',-.005,.067,.04,.034),('CTX_Occipital','O',.06,.025,.046,.05)]
for rn,k,cy,sy,rz,sz in regions:
 for side in(-1,1):
  for i in range(18):
   u=(i%6)/5-.5;v=(i//6)/2-.5;x=side*(.018+abs(u)*.055);y=cy+u*sy;z=.045+v*rz
   uv(rn+'_Gyrus_%s_%02d'%('L'if side<0 else'R',i),(x,y,z),(.014,.016,.010+abs(v)*.004),P[k],'02_BRAIN_CORTEX')
# exact required named structures, kept editable
uv('SUB_Thalamus',(0,-.04,.043),(.018,.014,.013),P['S'],'03_SUBCORTICAL')
uv('SUB_Hippocampus',(-.02,-.052,.014),(.028,.008,.008),P['I'],'03_SUBCORTICAL')
uv('SUB_Amygdala',(-.042,-.054,.014),(.008,.008,.008),P['A'],'03_SUBCORTICAL')
uv('SUB_BasalGanglia',(.018,-.05,.03),(.017,.012,.012),P['B'],'03_SUBCORTICAL')
uv('SUB_Cerebellum',(.035,.067,-.004),(.036,.026,.025),P['C'],'03_SUBCORTICAL')
uv('SUB_Brainstem',(0,.032,-.055),(.011,.01,.042),P['G'],'03_SUBCORTICAL')
uv('SUB_ACC',(0,-.055,.065),(.035,.006,.007),P['B'],'03_SUBCORTICAL')
bpy.ops.wm.save_as_mainfile(filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/mvec_brain_reference_faithful.blend')
