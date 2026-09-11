import bpy, math, json
from mathutils import Vector
from pathlib import Path
OUT=Path('/Users/saurabh/code/unfoundbox-crew/blender-mcp-examples/final')
OUT.mkdir(exist_ok=True)
# Preserve every existing draft. Rename colliding datablocks, never delete them.
CN=['00_REFERENCE','01_HEAD','02_BRAIN_CORTEX','03_SUBCORTICAL','04_FLOW_ARROWS','05_LAYER_STACK','06_CONTROL_LOOP','07_LABELS','08_LEGENDS','09_CAMERAS','10_LIGHTS']
for n in CN:
 if bpy.data.collections.get(n): bpy.data.collections[n].name='DRAFT_'+n
for o in list(bpy.data.objects):
 if o.name.startswith(('HEAD_','CTX_','SUB_','CAM_','LIGHT_')):o.name='DRAFT_'+o.name
sc=bpy.data.scenes.new('MVEC_FINAL'); sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
cols={}
for n in CN:
 c=bpy.data.collections.new(n);sc.collection.children.link(c);cols[n]=c
def mesh(name,v,f,col,material=None):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);cols[col].objects.link(o)
 for p in me.polygons:p.use_smooth=True
 if material:o.data.materials.append(material)
 return o
def linear(h):
 rgb=[int(h[i:i+2],16)/255 for i in(1,3,5)]
 return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb)
def material(n,h,alpha=1,rough=.45):
 m=bpy.data.materials.new('MVEC_'+n);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');rgba=(*linear(h),alpha);p.inputs['Base Color'].default_value=rgba;p.inputs['Alpha'].default_value=alpha;p.inputs['Roughness'].default_value=rough;m.diffuse_color=rgba;m['sRGB_hex']=h;m['specified_alpha']=alpha
 if alpha<1:m.surface_render_method='DITHERED'
 return m
pal={'Frontal':'#7EA6FF','Parietal':'#82D6A4','Temporal':'#F0C96C','Occipital':'#A989D8','Thalamus':'#52BECD','Hippocampus':'#339A91','Amygdala':'#74B580','BasalGanglia':'#E58982','Cerebellum':'#DE9559','Brainstem':'#8D99A5','ACC':'#BC788B'}
M={n:material(n,h,.62 if n in ['Frontal','Parietal','Temporal','Occipital'] else 1) for n,h in pal.items()}
M['Head']=material('Head','#E8EEF3',.10,.55)
# Continuous bilateral envelope. Deterministic sinuous grooves model schematic folds,
# without claiming that individual sulci match a medical atlas.
v=[];fs={n:[] for n in ['Frontal','Parietal','Temporal','Occipital']};nt=240;np=180
for side in(-1,1):
 offset=len(v)
 for i in range(nt+1):
  t=.002+(math.pi-.004)*i/nt
  for j in range(np+1):
   p=math.pi*j/np
   phase=13*t+2.2*math.sin(3*p+1.5*t)+.65*math.sin(8*p-2*t)
   phase2=10*p+1.8*math.sin(4*t)+.6*math.sin(9*t+2*p)
   groove=math.exp(-(math.sin(phase)/.23)**2)
   groove2=math.exp(-(math.sin(phase2)/.20)**2)
   r=1-.045*groove-.026*groove2
   x=side*(.0013+.0737*math.sin(t)*math.sin(p)*r)
   y=-.0875*math.cos(t)*r
   z=.060+.0675*math.sin(t)*math.cos(p)*r
   v.append((x,y,z))
 for i in range(nt):
  for j in range(np):
   a=offset+i*(np+1)+j;b=a+np+1
   f=(a,b,b+1,a+1) if side==1 else(a+1,b+1,b,a)
   x,y,z=v[a]
   if y>.050:region='Occipital'
   elif z<.049 and y>-.045:region='Temporal'
   elif y>-.006+.012*(abs(x)/.075):region='Parietal'
   else:region='Frontal'
   fs[region].append(f)
for n,f in fs.items():
 used=sorted({i for face in f for i in face});idx={a:b for b,a in enumerate(used)}
 o=mesh('CTX_'+n,[v[i] for i in used],[tuple(idx[i] for i in face) for face in f],'02_BRAIN_CORTEX',M[n]);o['schematic_anatomy']=True
# Horizontal loft of a neutral head, including forehead, nose, mouth and chin silhouette.
rings=[(-.112,.032,-.028,.035),(-.095,.037,-.030,.038),(-.078,.042,-.052,.043),(-.061,.054,-.063,.047),(-.040,.063,-.069,.052),(-.022,.069,-.067,.060),(-.008,.073,-.081,.070),(.008,.076,-.072,.080),(.026,.079,-.077,.092),(.045,.083,-.084,.099),(.070,.0875,-.081,.101),(.093,.081,-.070,.090),(.111,.063,-.050,.067),(.124,.034,-.015,.035),(.128,.001,.009,.011)]
hv=[];hf=[];nr=128
for z,w,front,back in rings:
 for j in range(nr):
  a=2*math.pi*j/nr; yy=(front+back)/2+(back-front)/2*math.cos(a)
  if -.02<z<.03:yy-=.026*math.exp(-((a-math.pi)/.18)**2)*(1-abs(z-.005)/.03)
  hv.append((w*math.sin(a),yy,z))
for i in range(len(rings)-1):
 for j in range(nr):a=i*nr+j;b=i*nr+(j+1)%nr;hf.append((a,b,b+nr,a+nr))
head=mesh('HEAD_Shell',hv,hf,'01_HEAD',M['Head']);sub=head.modifiers.new('Smooth shell','SUBSURF');sub.levels=2
# Scale the declared head envelope exactly using base-mesh bounds.
for axis,target in enumerate((.175,.215,.240)):
 vals=[p.co[axis] for p in head.data.vertices];lo=min(vals);hi=max(vals);mid=(hi+lo)/2
 for p in head.data.vertices:p.co[axis]=(p.co[axis]-mid)*target/(hi-lo)+mid
def ellipsoid(n,loc,dims,ma,fold=False):
 vv=[];ff=[];a,b,c=[x/2 for x in dims];N=80;K=48
 for i in range(K+1):
  t=.001+(math.pi-.002)*i/K
  for j in range(N):
   p=2*math.pi*j/N;r=1-(.035*math.exp(-(math.sin(22*t+1.6*math.sin(2*p))/.28)**2) if fold else 0)
   vv.append((loc[0]+a*math.sin(t)*math.cos(p)*r,loc[1]+b*math.sin(t)*math.sin(p)*r,loc[2]+c*math.cos(t)*r))
 for i in range(K):
  for j in range(N):a0=i*N+j;b0=i*N+(j+1)%N;ff.append((a0,b0,b0+N,a0+N))
 return mesh(n,vv,ff,'03_SUBCORTICAL',ma)
def tube(n,points,radii,ma,col='03_SUBCORTICAL'):
 vv=[];ff=[];N=16
 for i,pt in enumerate(points):
  tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)]);tangent.normalize();axis=tangent.cross(Vector((1,0,0)))
  if axis.length<.1:axis=tangent.cross(Vector((0,0,1)))
  axis.normalize();b=tangent.cross(axis)
  for j in range(N):vv.append(Vector(pt)+radii[i]*(axis*math.cos(j*2*math.pi/N)+b*math.sin(j*2*math.pi/N)))
 for i in range(len(points)-1):
  for j in range(N):a=i*N+j;bb=i*N+(j+1)%N;ff.append((a,bb,bb+N,a+N))
 ff.extend([tuple(reversed(range(N))),tuple((len(points)-1)*N+j for j in range(N))]);return mesh(n,vv,ff,col,ma)
ellipsoid('SUB_Thalamus',(0,.003,.048),(.035,.028,.025),M['Thalamus'])
pts=[(-.025+.009*math.sin(t),.012+.019*math.cos(t),.023+.009*math.sin(t)) for t in [i*math.pi*1.25/64 for i in range(65)]]
tube('SUB_Hippocampus',pts,[.0038+.001*math.sin(i*math.pi/64) for i in range(65)],M['Hippocampus'])
ellipsoid('SUB_Amygdala',(-.020,-.022,.022),(.014,.014,.014),M['Amygdala'])
ellipsoid('SUB_BasalGanglia',(-.013,-.018,.055),(.028,.025,.026),M['BasalGanglia'])
ellipsoid('SUB_Cerebellum',(0,.055,-.018),(.050,.030,.035),M['Cerebellum'],True)
pts=[(0,.014+.007*i/32,-.007-.036*i/32) for i in range(33)]
bs=tube('SUB_Brainstem',pts,[.009*(1-.35*i/32) for i in range(33)],M['Brainstem'])
# normalize brainstem bounds to specified dimensions
for axis,target in enumerate((.020,.018,.045)):
 vals=[p.co[axis] for p in bs.data.vertices];lo=min(vals);hi=max(vals);mid=(hi+lo)/2
 for p in bs.data.vertices:p.co[axis]=(p.co[axis]-mid)*target/(hi-lo)+mid
pts=[(-.004,-.004+.030*math.cos(t),.058+.021*math.sin(t)) for t in [math.pi*i/64 for i in range(65)]]
tube('SUB_ACC',pts,[.0032]*65,M['ACC'])
world=bpy.data.worlds.new('MVEC White');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;sc.world=world
def cam(n,loc,ortho=False):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);cols['09_CAMERAS'].objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.020))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=62;d.clip_start=.001;d.clip_end=100
 if ortho:d.type='ORTHO';d.ortho_scale=.35
 return o
cams=[cam('CAM_Master',(-.38,-.52,.23)),cam('CAM_LeftOrthographic',(-.6,0,.02),True),cam('CAM_FrontOrthographic',(0,-.6,.02),True),cam('CAM_TopOrthographic',(0,0,.65),True),cam('CAM_ExplodedLayers',(-.45,-.55,.29)),cam('CAM_Detail',(-.34,-.4,.18))]
for n,loc,power,size in [('Key',(-.3,-.3,.5),12,.35),('Fill',(.3,-.05,.2),5,.3),('Rim',(0,.4,.35),8,.25)]:
 d=bpy.data.lights.new('LIGHT_'+n,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new('LIGHT_'+n,d);cols['10_LIGHTS'].objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.04))-o.location).to_track_quat('-Z','Y').to_euler()
sc.camera=cams[1];sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=900;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=True;sc.view_settings.view_transform='AgX'
sc.use_nodes=True;tree=sc.node_tree;tree.nodes.clear();rl=tree.nodes.new('CompositorNodeRLayers');rl.scene=sc;ao=tree.nodes.new('CompositorNodeAlphaOver');ao.inputs[1].default_value=(1,1,1,1);tree.links.new(rl.outputs['Image'],ao.inputs[2]);co=tree.nodes.new('CompositorNodeComposite');tree.links.new(ao.outputs[0],co.inputs[0])
bpy.context.window.scene=sc
sc.render.filepath=str(OUT/'stage_anatomy_left.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'working.blend'))
bpy.ops.render.render(write_still=True,scene=sc.name)
print('ANATOMY_STAGE_READY')
