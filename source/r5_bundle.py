from r5_portable import check,topfile,refpath,angles
from native import *
import shutil
def references(p):return [Path(t) for t in (sw.GetDocumentDependencies2(str(p),False,False,False) or [])[1::2]]
def run():
 dest=ROOT/'交付'/'SolidWorks';dest.mkdir(parents=True,exist_ok=True)
 graph={};todo=[topfile,refpath]
 while todo:
  p=todo.pop()
  if p in graph:continue
  assert p.is_file() and (p.is_relative_to(OUT) or p.suffix.lower() in ['.step','.stp']),p
  children=references(p) if p.suffix.upper() in ['.SLDPRT','.SLDASM'] else [];graph[p]=children;todo.extend(children)
 print('discovered',len(graph),'edges',sum(map(len,graph.values())),flush=True)
 assert len(graph)>=89
 def target(p):return dest/('Q8R5_'+p.name)
 assert len(set(target(p) for p in graph))==len(graph)
 for p in graph:shutil.copy2(p,target(p))
 for p,children in graph.items():
  if not children:continue
  if all(v.suffix.lower() in ['.step','.stp'] for v in children):
   # Retain the purchased interface solid in the native part; include its STEP source in the review package.
   path=target(p);m=open_doc(path,1);activate(m);part=asif(m,api.IPartDoc)
   volumes=lambda:sorted(asif(b,api.IBody2).GetMassProperties(1)[3]*1e9 for b in part.GetBodies2(0,False))
   before=volumes();f=m.FirstFeature()
   while f:
    f=asif(f,api.IFeature)
    if f.GetTypeName2().lower()=='mbimport':
     assert f.BreakLink(True,True)==0,p
     break
    f=f.GetNextFeature()
   m.ForceRebuild3(False);after=volumes();assert len(before)==len(after) and max(abs(a-b) for a,b in zip(before,after))<.01,p
   save(m,path);sw.CloseDoc(m.GetTitle());assert not references(path),(p,references(path))
   continue
  for v in children:
   assert sw.ReplaceReferencedDocument(str(target(p)),str(v),str(target(v))),(p,v)
  reread=references(target(p));assert set(reread)==set(map(target,children)),(p,reread)
 print('rebound references',flush=True)
 r,f=target(refpath),target(topfile)
 rem,rc=check(r,angles,dest);rem.ShowConfiguration2('Ride');save(rem,r);sw.CloseDoc(rem.GetTitle())
 m,checked=check(f,['Motion_MID','Motion'],dest);m.ShowConfiguration2('Motion');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,f);activate(m);m.GraphicsRedraw2()
 write(ROOT/'data/R5_pack.json',dict(main=f.name,pose=r.name,files=len(graph),reopened=checked,reference_reopened=rc,method='Native ISldWorks.ReplaceReferencedDocument for the full dependency graph; reopened every configuration.',dependency_edges=sum(map(len,graph.values()))))
 preview=ROOT/'data/R5_SolidWorks.bmp'
 if m.SaveBMP(str(preview),1400,900) and preview.is_file():
  from PIL import Image
  with Image.open(preview) as im:im.save(ROOT/'data/R5_SolidWorks.png')
 print('verified delivery',checked,rc,flush=True)
if __name__=='__main__':
 old=sw.CommandInProgress
 try:sw.CommandInProgress=True;run()
 finally:sw.CommandInProgress=old
