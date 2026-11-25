from r5_vehicle import topfile,mate_errors
from r5_pose_reference import refpath,angles
from native import *
def send(model,dest):
 m=open_doc(model,2);activate(m);e=asif(m.Extension,api.IModelDocExtension)
 pg=asif(e.GetPackAndGo(),api.IPackAndGo);pg.IncludeDrawings=False;pg.IncludeSuppressed=True;pg.FlattenToSingleFolder=True;pg.AddPrefix='Q8R5_'
 assert pg.SetSaveToName(True,str(dest));status=e.SavePackAndGo(pg)
 print('pack',model.name,len(status),set(status),flush=True);assert len(status)>1 and all(v==0 for v in status)
 f=dest/('Q8R5_'+model.name);assert f.is_file(),(str(f),[s.name for s in dest.glob('*')][:6])
 return f,len(status)
def check(f,configs,dest):
 m=open_doc(f,2);activate(m);a=asif(m,api.IAssemblyDoc);checked={}
 for cn in configs:
  m.ShowConfiguration2(cn);m.ForceRebuild3(True)
  rows=[asif(x,api.IComponent2) for x in a.GetComponents(False)]
  live=[c for c in rows if not c.IsSuppressed()];seen=set();bad=[]
  for c in live:
   path=Path(c.GetPathName())
   if path in seen:continue
   seen.add(path)
   if not c.GetModelDoc2() or not path.is_relative_to(dest):bad.append(str(path))
  assert not bad,(cn,bad[:6])
  if cn.startswith('Motion'):
   mf=mate_errors(m);assert len(mf)==44 and not any(v for _,v in mf),(cn,mf)
  checked[cn]=len(live)
 return m,checked
def pack():
 dest=ROOT/'交付'/'SolidWorks';dest.mkdir(parents=True,exist_ok=True)
 f,main_count=send(topfile,dest);r,pose_count=send(refpath,dest)
 scope=[]
 for raw in sw.GetDocuments() or []:
  doc=asif(raw,api.IModelDoc2);original=Path(doc.GetPathName())
  if original.is_relative_to(OUT):scope.append((original.suffix.upper()!='.SLDASM',len(original.parts),doc.GetTitle()))
 for _,__,title in sorted(scope):sw.CloseDoc(title)
 rem,rc=check(r,angles,dest);rem.ShowConfiguration2('Ride');save(rem,r);sw.CloseDoc(rem.GetTitle())
 m,checked=check(f,['Motion_MID','Motion'],dest)
 m.ShowConfiguration2('Motion');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,f);activate(m);m.GraphicsRedraw2()
 n=sum(1 for path in dest.glob('*') if path.suffix.upper() in ['.SLDPRT','.SLDASM'] and not path.name.startswith('~$'))
 write(ROOT/'data/R5_pack.json',dict(main=f.name,pose=r.name,files=n,main_dependency_count=main_count,pose_dependency_count=pose_count,reopened=checked,reference_reopened=rc))
 preview=ROOT/'data/R5_SolidWorks.bmp'
 if m.SaveBMP(str(preview),1400,900) and preview.is_file():
  from PIL import Image
  with Image.open(preview) as im:im.save(ROOT/'data/R5_SolidWorks.png')
if __name__=='__main__':
 flag=sw.CommandInProgress
 try:sw.CommandInProgress=True;pack()
 finally:sw.CommandInProgress=flag
