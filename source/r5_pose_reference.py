from r5_vehicle import *
refpath=OUT/'Q8_R5_姿态参考.SLDASM'
angles={'Ride':[-7]*4,'Crouch':[-36]*4,'Liftoff':[22]*4,'FL_Raised':[-36,-7,-7,-7],'Diagonal':[-36,22,22,-36]}
sub={-7:'Midstroke',-36:'Crouch',22:'Liftoff'}
def legname(c):
 return suffix(c) if Path(c.GetPathName())!=rack else 'body'
def run():
 if not refpath.exists():
  m,a=swb.new_ass(refpath);activate(m);r=insert(m,a,rack,2,'Equipment',tr(),True);r.ReferencedConfiguration='Base'
  for n,side,f in corner_order:
   lf=OUT/'R1'/'Q8_Single_Corner.SLDASM' if f*side==1 else OUT/'LH'/'Q8_Corner_Mirror.SLDASM'
   insert(m,a,lf,2,n,xf([side*HX,f*HY,0],leg_basis(side)),True)
  save(m,refpath)
 else:m=open_doc(refpath,2);activate(m);a=asif(m,api.IAssemblyDoc)
 for cfg,qs in angles.items():
  if not m.GetConfigurationByName(cfg):m.AddConfiguration3(cfg,'','',0)
  m.ShowConfiguration2(cfg);assert asif(asif(m.ConfigurationManager,api.IConfigurationManager).ActiveConfiguration,api.IConfiguration).Name==cfg,cfg
  for c in direct(a):
   n=legname(c)
   if n!='body':c.ReferencedConfiguration=sub[qs[names.index(n)]]
   else:c.ReferencedConfiguration='Base'
  m.EditRebuild3();m.ForceRebuild3(False);save(m,refpath)
 m.ShowConfiguration2('Ride')
 for k in list(m.GetConfigurationNames()):
  if k not in angles:assert m.DeleteConfiguration2(k),k
 m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,refpath);sw.CloseDoc(m.GetTitle())
 m=open_doc(refpath,2);activate(m);a=asif(m,api.IAssemblyDoc);qa={}
 for cfg,qs in angles.items():
  m.ShowConfiguration2(cfg);assert asif(asif(m.ConfigurationManager,api.IConfigurationManager).ActiveConfiguration,api.IConfiguration).Name==cfg,cfg;m.ForceRebuild3(False);obs={};C={}
  for c in direct(a):
   n=legname(c)
   if n=='body':continue
   assert c.ReferencedConfiguration==sub[qs[names.index(n)]],(cfg,n,c.ReferencedConfiguration)
   for raw in c.GetChildren() or []:
    child=asif(raw,api.IComponent2);g=Path(child.GetPathName()).stem.removeprefix('LH_')
    if g in groups:C[n,g]=child
  assert len(C)==20,(cfg,list(C));dev=measure(C,dict(zip(names,qs)));err=max(dev.values());print(cfg,err,flush=True);assert err<.05,(cfg,dev)
  live=[asif(raw,api.IComponent2) for raw in a.GetComponents(False)];bad=[c.GetPathName() for c in live if not c.IsSuppressed() and (not c.GetModelDoc2() or not Path(c.GetPathName()).is_relative_to(OUT))]
  assert not bad,(cfg,bad[:6]);qa[cfg]=dict(angles=dict(zip(names,qs)),error_mm=err)
 m.ShowConfiguration2('Ride');save(m,refpath);sw.CloseDoc(m.GetTitle());write(ROOT/'data/R5_pose_reference.json',qa)
if __name__=='__main__':
 old=sw.CommandInProgress
 try:sw.CommandInProgress=True;run()
 finally:sw.CommandInProgress=old
