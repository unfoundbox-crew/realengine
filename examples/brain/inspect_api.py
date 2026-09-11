import bpy,json
sc=bpy.data.scenes['MVEC_FINAL']
print('COMPOSITING',[(p.identifier,p.type) for p in sc.bl_rna.properties if 'compo' in p.identifier or 'node' in p.identifier])
print('GEOMETRY',[(o.name,len(o.data.vertices)) for o in sc.objects if o.type=='MESH'])
