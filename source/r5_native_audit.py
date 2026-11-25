from r5_vehicle import topfile,parts,mate_errors,rack
from r5_instances import filepath
from native import *
import csv
print_keys=['Deck','Chassis','BuckTray','Bridge_tray','JetClamp','XT_saddle','Astra_saddle','MID_fit']
def review():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);paths={topfile}
 for config in ['Motion','Motion_MID']:
  m.ShowConfiguration2(config);m.ForceRebuild3(True)
  for raw in a.GetComponents(False):
   c=asif(raw,api.IComponent2)
   if not c.IsSuppressed():
    p=Path(c.GetPathName())
    if p not in paths:assert p.is_relative_to(OUT) and p.exists() and c.GetModelDoc2(),p
    paths.add(p)
 m.ShowConfiguration2('Motion')
 result={}
 for k,path in [(k,filepath(k)) for k in print_keys]+[(p.stem,p) for p in paths if p.suffix.upper()=='.SLDPRT' and p.stem.removeprefix('LH_') in ['P01','P02','P03','P04','P05','P07']]:
  d=open_doc(path,1);f=d.FirstFeature();tree=[];dims=0
  while f:
   f=asif(f,api.IFeature);typ=f.GetTypeName2()
   if typ in ['Boss','Cut','Extrusion','ICE','Imported','ImportedBody']:
    tree.append([f.Name,typ,f.GetErrorCode2(False)[0]])
    sub=f.GetFirstSubFeature()
    while sub:
     sub=asif(sub,api.IFeature)
     if sub.GetTypeName2()=='ProfileFeature':
      dd=sub.GetFirstDisplayDimension()
      while dd:
       dims+=1;dd=sub.GetNextDisplayDimension(asif(dd,api.IDisplayDimension))
     sub=sub.GetNextSubFeature()
   f=f.GetNextFeature()
  assert tree and not any(v or 'Imported' in t for _,t,v in tree),(k,tree)
  result[k]=dict(features=tree,sketch_dimensions=dims)
 d=open_doc(rack,2);a2=asif(d,api.IAssemblyDoc)
 racks={}
 for k in ['Base','MID']:
  d.ShowConfiguration2(k);d.ForceRebuild3(False);errors=mate_errors(d)
  racks[k]={'mates':len(errors),'flagged':[e for e in errors if e[1]]}
 d.ShowConfiguration2('Base')
 print('editable',len(result),'paths',len(paths),'rack',racks,flush=True)
 write(ROOT/'data/R5_native_audit.json',dict(printable=result,dependencies=sorted(str(p.relative_to(OUT)) for p in paths),rack=racks))
if __name__=='__main__':
 flag=sw.CommandInProgress
 try:sw.CommandInProgress=True;review()
 finally:sw.CommandInProgress=flag

