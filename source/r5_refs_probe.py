from r5_vehicle import *
m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);labels={v.Name2:k for k,v in parts(a).items()};f=m.FirstFeature()
while f:
 f=asif(f,api.IFeature)
 if f.GetTypeName2()=='MateGroup':
  s=f.GetFirstSubFeature()
  while s:
   s=asif(s,api.IFeature)
   if s.GetTypeName2().startswith('Mate'):
    v=asif(s.GetSpecificFeature2(),api.IMate2);refs=[]
    for j in range(v.GetMateEntityCount()):
     e=asif(v.MateEntity(j),api.IMateEntity2);c=e.ReferenceComponent
     refs.append(labels.get(asif(c,api.IComponent2).Name2,'?') if c else None)
    if any(c and c[0] not in ('body',s.Name[:2]) for c in refs) or s.Name.startswith('FL_'):print(s.Name,refs,flush=True)
   s=s.GetNextSubFeature()
 f=f.GetNextFeature()

