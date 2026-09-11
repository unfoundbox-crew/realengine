import bpy,math,json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sc=bpy.data.scenes['MVEC_FINAL'];cols={c.name:c for c in sc.collection.children}
# Render the white card interiors as the white page; retain their editable 3mm meshes.
for o in sc.objects:
 if o.name.startswith(('CTRL_Prediction_','CTRL_LayerLegend_')) and o.type=='MESH':o['view']='EDITABLE_CARD_SOLIDS';o.hide_render=True
# Use crisp outlined rows with palette marks, without bright solids obscuring small type.
master=bpy.data.objects['CAM_Master']
def local(c,x,y):return ((x/c['canvas_w']-.5)*c['overlay_width']+c.data.shift_x*c['overlay_width'],(.5-y/c['canvas_h'])*c['overlay_height']+c.data.shift_y*c['overlay_width'],-c['overlay_depth']+.012)
def line(c,name,pts,ma,width=1):
 d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=width*c['overlay_width']/c['canvas_w']/2;d.bevel_resolution=2;s=d.splines.new('POLY');s.points.add(len(pts)-1)
 for p,co in zip(s.points,pts):p.co=(*local(c,*co),1)
 o=bpy.data.objects.new(name,d);cols['07_LABELS'].objects.link(o);o.parent=c;o['view']=c.name;d.materials.append(ma);return o
for i,key in enumerate(['Occipital','Frontal','Parietal','Temporal','BasalGanglia']):
 ma=bpy.data.materials['MVEC_'+key];line(master,'LABEL_LayerColor_'+str(i),[(1268,224+i*69),(1268,258+i*69)],ma,6)
# Leaders go from text gutter to the projected location of the indicated structure.
targets={'Frontal':(.045,-.040,.075),'Parietal':(.045,.025,.087),'Temporal':(.053,.012,.027),'Occipital':(.036,.065,.057),'Thalamus':(0,.003,.048),'Hippocampus':(-.020,.01,.025),'Amygdala':(-.020,-.022,.022),'BasalGanglia':(-.013,-.018,.055),'Cerebellum':(0,.055,-.018),'Brainstem':(0,.02,-.024),'ACC':(-.004,0,.076)}
oldx,oldy=sc.render.resolution_x,sc.render.resolution_y
for c in [o for o in sc.objects if o.type=='CAMERA' and o!=master]:
 sc.render.resolution_x=1600;sc.render.resolution_y=1600
 for o in list(sc.objects):
  if o.type!='FONT' or not o.name.startswith('LABEL_Name_') or o.get('view')!=c.name:continue
  key=o.name[len('LABEL_Name_'):].split(c.name)[0]
  if key not in targets:continue
  p=world_to_camera_view(sc,c,Vector(targets[key]));tx=p.x*1600;ty=(1-p.y)*1600
  x=(o.location.x-c.data.shift_x*c['overlay_width'])/c['overlay_width']*1600+800;y=800-o.location.y/c['overlay_height']*1600
  left=x<800;sx=x+260 if left else x-22;ex=480 if left else 1120
  line(c,'LABEL_Leader_'+key+c.name,[(sx,y+7),(ex,y+7),(tx,ty)],bpy.data.materials['MVEC Rules'],1.2)
sc.render.resolution_x=oldx;sc.render.resolution_y=oldy
for o in sc.objects:
 if o.get('view'):o.hide_render=o['view']!=master.name
sc.camera=master
sc.render.resolution_percentage=60;sc.cycles.samples=96;sc.render.filepath='/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final/master_preview_rgba.png'
bpy.ops.render.render(write_still=True,scene=sc.name)
