import bpy,math,textwrap,json
from mathutils import Vector
from pathlib import Path
sc=bpy.data.scenes['MVEC_FINAL'];OUT=Path('/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final');cols={c.name:c for c in sc.collection.children}
for n in sc.compositing_node_group.nodes:
 if n.bl_idname=='CompositorNodeAlphaOver':n.inputs['Background'].default_value=(1,1,1,1)
# Raw RGBA renders are composited onto display-white at export, after AgX.
sc.render.use_compositing=False
def linear(h):
 return tuple((x/12.92 if x<=.04045 else((x+.055)/1.055)**2.4) for x in [int(h[i:i+2],16)/255 for i in(1,3,5)])
def ink(n,h):
 m=bpy.data.materials.new(n);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();em=nt.nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(*linear(h),1);em.inputs[1].default_value=1;op=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(em.outputs[0],op.inputs['Surface']);return m
INK=ink('MVEC Type','#122C3D');MUTED=ink('MVEC Secondary','#526678');RULE=ink('MVEC Rules','#CCD7DF');WHITE=ink('MVEC Card','#FFFFFF');TEAL=ink('MVEC Accent','#257D83')
FONT=None
for p in ['/System/Library/Fonts/Supplemental/Arial.ttf','/System/Library/Fonts/Helvetica.ttc']:
 if Path(p).exists():FONT=bpy.data.fonts.load(p);break
def aim(c,loc,target):c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler()
master=bpy.data.objects['CAM_Master'];aim(master,(.66,-.9,.37),(0,0,.025));master.data.shift_x=.18
detail=bpy.data.objects['CAM_Detail'];aim(detail,(-.33,-.40,.19),(0,0,.04));detail.data.shift_x=0
expl=bpy.data.objects['CAM_ExplodedLayers'];aim(expl,(.47,-.62,.27),(0,0,.045))
top=bpy.data.objects['CAM_TopOrthographic'];top.rotation_euler=(0,0,0);top.location=(0,0,.65)
# Camera-local typography stays precisely camera-facing. Coordinates use a 1600/2048px canvas.
def setup(c,w=1600,h=1600):
 c['canvas_w']=w;c['canvas_h']=h
 c['overlay_depth']=.75 if c.data.type!='ORTHO' else .35
 c['overlay_width']=c.data.ortho_scale if c.data.type=='ORTHO' else c['overlay_depth']*.036/c.data.lens*1000
 c['overlay_height']=c['overlay_width']*h/w
def xy(c,x,y,z=0):return ((x/c['canvas_w']-.5)*c['overlay_width']+c.data.shift_x*c['overlay_width'],(.5-y/c['canvas_h'])*c['overlay_height']+c.data.shift_y*c['overlay_width'],-c['overlay_depth']+z)
def tag(o,c):o.parent=c;o['view']=c.name
def text(c,n,s,x,y,size=24,ma=None,align='LEFT',col='07_LABELS'):
 d=bpy.data.curves.new(n,'FONT');d.body=s;d.size=size*c['overlay_width']/c['canvas_w'];d.align_x=align;d.space_line=1.2
 if FONT:d.font=FONT
 o=bpy.data.objects.new(n,d);cols[col].objects.link(o);tag(o,c);o.location=xy(c,x,y,.001);d.materials.append(ma or INK);return o
def line(c,n,pts,ma=None,width=1.5,col='07_LABELS',arrow=False):
 d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.resolution_u=12;d.bevel_depth=width*c['overlay_width']/c['canvas_w']/2;d.bevel_resolution=2;s=d.splines.new('POLY');s.points.add(len(pts)-1)
 for p,co in zip(s.points,pts):p.co=(*xy(c,*co,.001),1)
 o=bpy.data.objects.new(n,d);cols[col].objects.link(o);tag(o,c);d.materials.append(ma or RULE)
 if arrow:
  a=Vector(pts[-2]);b=Vector(pts[-1]);u=(b-a).normalized();v=Vector((-u.y,u.x));aa=b-u*9+v*4;bb=b-u*9-v*4
  line(c,n+'_Head',[tuple(aa),tuple(b),tuple(bb)],ma or INK,width,col)
 return o
def card(c,n,x,y,w,h):
 pts=[(x+8,y),(x+w-8,y),(x+w,y+8),(x+w,y+h-8),(x+w-8,y+h),(x+8,y+h),(x,y+h-8),(x,y+8)]
 vv=[xy(c,a,b) for a,b in pts];me=bpy.data.meshes.new(n);me.from_pydata(vv,[],[tuple(range(8))]);me.update();o=bpy.data.objects.new(n,me);cols['06_CONTROL_LOOP'].objects.link(o);tag(o,c);o.data.materials.append(WHITE);sol=o.modifiers.new('3 mm card','SOLIDIFY');sol.thickness=.003
 line(c,n+'_Border',pts+[pts[0]],RULE,1.2,'06_CONTROL_LOOP');return o
titles={'CAM_Master':('THE PREDICTIVE BRAIN','From perception to action, with language as a high-level interface.'),'CAM_LeftOrthographic':('01 / LATERAL STRUCTURE','Four cortical regions. A shared anatomical coordinate system.'),'CAM_FrontOrthographic':('02 / FRONT STRUCTURE','Bilateral organization and the structures beneath the cortex.'),'CAM_TopOrthographic':('03 / SUPERIOR STRUCTURE','Anterior at top. Posterior at bottom. Paired hemispheres.'),'CAM_ExplodedLayers':('04 / EXPLODED ANATOMY','Cortical regions separated to reveal the subcortical structures.'),'CAM_Detail':('05 / INTERNAL STRUCTURES','Schematic volumes for memory, routing, selection and control.')}
for c in [o for o in sc.objects if o.type=='CAMERA']:
 setup(c,2048,1152) if c==master else setup(c)
 w=c['canvas_w'];h=c['canvas_h'];a,b=titles[c.name]
 text(c,'LABEL_Title_'+c.name,a,64,77,42);text(c,'LABEL_Deck_'+c.name,b,64,116,22,MUTED)
 line(c,'LEGEND_TopRule_'+c.name,[(64,145),(w-64,145)])
 text(c,'LEGEND_Footer_'+c.name,'MVEC  /  HUMAN BRAIN AS A LAYERED PREDICTIVE-CONTROL SYSTEM',64,h-45,15,MUTED,col='08_LEGENDS')
 text(c,'LEGEND_Note_'+c.name,'Schematic anatomy · not a medical atlas',w-64,h-45,15,MUTED,'RIGHT','08_LEGENDS')
labels=[('Frontal','Prefrontal Cortex','Planning, decision making, abstraction, goal management'),('Parietal','Parietal Cortex','Spatial representation, attention, sensorimotor integration'),('Temporal','Temporal Cortex','Object recognition, semantic memory, language comprehension'),('Occipital','Occipital Cortex','Visual processing'),('ACC','Anterior Cingulate Cortex','Error monitoring, conflict detection, attention control'),('BasalGanglia','Basal Ganglia','Action selection, habit learning, reward processing'),('Thalamus','Thalamus','Sensory relay and information routing'),('Hippocampus','Hippocampus','Memory formation and spatial navigation'),('Amygdala','Amygdala','Emotion, salience, threat detection'),('Cerebellum','Cerebellum','Motor control, prediction error correction, timing'),('Brainstem','Brainstem','Vital functions, arousal, neuromodulation')]
def label(c,k,title,sub,x,y,sz=24):
 color=bpy.data.materials['MVEC_'+k]['sRGB_hex'];accent=ink('LABEL_Color_'+k+'_'+c.name,color)
 line(c,'LABEL_Swatch_'+k+c.name,[(x,y-8),(x+22,y-8)],accent,6)
 text(c,'LABEL_Name_'+k+c.name,title,x+32,y,sz)
 text(c,'LABEL_Subtitle_'+k+c.name,'\n'.join(textwrap.wrap(sub,32 if c!=master else 33)),x+32,y+29,17 if c!=master else 16,MUTED)
# Orthographic presentation: labels outside anatomy; exact full subtitles in side/detail panels.
for c in [bpy.data.objects[n] for n in ['CAM_LeftOrthographic','CAM_FrontOrthographic','CAM_TopOrthographic','CAM_ExplodedLayers','CAM_Detail']]:
 if c.name=='CAM_TopOrthographic':items=labels[:4];places=[(70,350),(1150,350),(70,880),(1150,1050)]
 elif c.name=='CAM_LeftOrthographic':items=labels[:4]+labels[-2:];places=[(65,330),(1160,330),(65,800),(1160,700),(1160,1080),(65,1190)]
 else:items=labels[4:];places=[(65,300),(65,550),(1160,300),(65,830),(65,1100),(1160,890),(1160,1180)]
 for it,(x,y) in zip(items,places):label(c,*it,x,y,22)
 if c.name=='CAM_TopOrthographic':text(c,'LABEL_Anterior','ANTERIOR',800,210,18,MUTED,'CENTER');text(c,'LABEL_Posterior','POSTERIOR',800,1400,18,MUTED,'CENTER')
# Main overview: cortical key under the brain, internal names in a compact key to its left.
for it,(x,y) in zip(labels[:4],[(65,730),(340,730),(620,730),(910,730)]):
 label(master,*it,x,y,21)
text(master,'LABEL_AnatomyCaption','STRUCTURE  /  Four cortical regions + seven subcortical structures',66,190,18,MUTED)
for i,it in enumerate(labels[4:]):text(master,'LABEL_MainInternal_'+it[0],it[1],80,285+i*40,18,MUTED)
# Five exact-dimension transparent layers are actual 3D slabs in a separate spatial group.
layers=[('Language & Social Cognition','Occipital'),('Abstract Reasoning & Planning','Frontal'),('World Model / Internal Simulation','Parietal'),('Perception & Representation','Temporal'),('Sensorimotor & Homeostasis','BasalGanglia')]
text(master,'LABEL_StackHeading','FIVE LEVELS OF PROCESSING',1260,190,22)
def box(n,loc,dims,ma,col):
 x,y,z=[q/2 for q in dims];v=[(a*x,b*y,c*z) for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]];f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);o=bpy.data.objects.new(n,me);cols[col].objects.link(o);o.location=loc;o.data.materials.append(ma);be=o.modifiers.new('Soft edges','BEVEL');be.width=.001;be.segments=3;return o
for i,(lab,key) in enumerate(layers):
 z=.092-i*.018;slab=box('LAYER_L'+str(5-i),(.28,0,z),(.120,.050,.004),bpy.data.materials['MVEC_'+key],'05_LAYER_STACK');slab['view']='STACK_PHYSICAL'
 # A legible legend for the physical stack, on the main camera's plane.
 y=239+i*69;card(master,'CTRL_LayerLegend_'+str(i),1260,y-25,690,56)
 text(master,'LABEL_Level_'+str(i),'L'+str(5-i),1277,y+9,25,TEAL)
 text(master,'LABEL_LevelText_'+str(i),lab,1338,y+7,23)
 # sparse links/nodes remain editable curves on the actual slab
 pts=[(.235+j*.018,.006*math.sin(j*1.4+i),z+.004) for j in range(6)]
 for j,p in enumerate(pts):
  node=box('LAYER_Node_%d_%d'%(i,j),p,(.0025,.0025,.0025),bpy.data.materials['MVEC_'+key],'05_LAYER_STACK');node['view']='STACK_PHYSICAL'
 d=bpy.data.curves.new('LAYER_Links_'+str(i),'CURVE');d.dimensions='3D';d.bevel_depth=.00035;sp=d.splines.new('POLY');sp.points.add(5)
 for p,co in zip(sp.points,pts):p.co=(*co,1)
 o=bpy.data.objects.new(d.name,d);cols['05_LAYER_STACK'].objects.link(o);d.materials.append(MUTED);o['view']='STACK_PHYSICAL'
text(master,'LABEL_LanguageNote','Language is a high-level interface, not the base layer.',1260,618,19,MUTED)
principles=[('Predictive','anticipates possible future states.'),('Adaptive','updates internal models from prediction error.'),('Multi-modal','combines sensory and internal signals.'),('Hierarchical','operates across abstraction levels and timescales.'),('Embodied','grounded in a body interacting with an environment.'),('Goal-directed','shaped by needs, values, and context.')]
for i,(a,b) in enumerate(principles):text(master,'LEGEND_Principle_'+str(i),a+' — '+b,1260,661+i*26,17,MUTED,col='08_LEGENDS')
# Eight-stage prediction loop, seven solid primary connections and one feedback curve.
text(master,'LABEL_LoopHeading','PREDICTION → ACTION → FEEDBACK',65,855,22)
steps=['Perceive','Encode','Predict','Compare','Update','Plan & Decide','Act','Environment']
for i,s in enumerate(steps):
 x=65+i*245;card(master,'CTRL_Prediction_'+str(i),x,880,210,53);text(master,'LABEL_Prediction_'+str(i),s,x+105,913,24,align='CENTER')
 if i<7:line(master,'FLOW_Primary_'+str(i),[(x+214,906),(x+238,906)],INK,2,'04_FLOW_ARROWS',True)
line(master,'FLOW_Feedback',[(1895,937),(1895,967),(171,967),(171,937)],INK,1.6,'04_FLOW_ARROWS',True)
text(master,'LABEL_Feedback','Environment feedback',1024,986,17,MUTED,'CENTER')
ctrl=['Environment','Perception','Internal Model','Comparison','Update','Decision','Action','Environment']
text(master,'LABEL_ClosedLoop','CLOSED-LOOP CONTROL',65,1040,16,MUTED)
for i,s in enumerate(ctrl):
 x=420+i*199;text(master,'LABEL_Control_'+str(i),s,x,1040,16,MUTED)
 if i<7:line(master,'CTRL_Link_'+str(i),[(x+140,1034),(x+180,1034)],MUTED,1,'06_CONTROL_LOOP',True)
# dashed modulation lines, labels make their purpose explicit
for i,s in enumerate(['memory','emotion','attention','goals/values']):
 x=470+i*175
 for j in range(5):line(master,'FLOW_Mod_%d_%d'%(i,j),[(x,809+j*5),(x,811+j*5)],TEAL,1,'04_FLOW_ARROWS')
 text(master,'LABEL_Mod_'+str(i),s,x+8,824,15,MUTED)
# All overlays have independent per-camera visibility; no label is allowed to float edge-on.
for o in sc.objects:
 if o.get('view'):o.hide_render=o.get('view')!=master.name
sc.camera=master;sc.cycles.samples=32;sc.render.resolution_x=2048;sc.render.resolution_y=1152;sc.render.resolution_percentage=60;sc.render.filepath=str(OUT/'master_preview_rgba.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'working.blend'))
bpy.ops.render.render(write_still=True,scene=sc.name)
print('LAYOUT_READY')
