from pathlib import Path
p=Path('r5_rack.py');s=p.read_text(encoding='utf8');i=s.index(' if key not in cache:');j=s.index(' return asif(c.GetCorrespondingEntity',i)
s=s[:i]+''' if path not in cache:
  catalogue={'p':[],'c':[]};doc=asif(c.GetModelDoc2(),api.IPartDoc)
  for raw in doc.GetBodies2(0,False):
   for rawf in asif(raw,api.IBody2).GetFaces():
    f=asif(rawf,api.IFace2);surf=asif(f.GetSurface(),api.ISurface)
    if surf.IsCylinder():
     v=surf.CylinderParams
     if abs(v[5])>.9999:catalogue['c'].append(((v[0]*1000,v[1]*1000,v[6]*1000),f))
    elif surf.IsPlane():
     v=surf.PlaneParams
     if abs(v[2])>.9999:catalogue['p'].append(((v[5]*1000,),f))
  cache[path]=catalogue
 if key not in cache:
  match=next((f for vals,f in cache[path][mode] if max(abs(a-b) for a,b in zip(vals,data))<.015),None)
  if match is None:raise RuntimeError(('face',path,mode,data))
  cache[key]=match
'''+s[j:]
p.write_text(s,encoding='utf8')

