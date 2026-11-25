from r5_rack import mate,plane,rack
from vehicle_sw import *
from itertools import product
topfile=OUT/'Q8_R5_整车.SLDASM'
groups=['base','drive','passive','carrier','wheel']
def placement(name,g,q):
 _,side,front=next(c for c in corner_order if c[0]==name)
 x,y,theta=pose(g,q,side*front)
 return xf(np.array([side*HX,front*HY,0.])+leg_basis(side)@np.array([x,y,0.]),leg_basis(side)@xyzrot(theta))
def label(c):
 k=Path(c.GetPathName()).stem
 if k==rack.stem:return ('body','body')
 g=k.removeprefix('LH_');v=asif(c.Transform2,api.IMathTransform).ArrayData
 # A carrier can sit beyond the hip but the mirrored linkage extends outwards along Y.
 return (('F' if v[10]>0 else 'R')+('R' if v[9]>0 else 'L'),g)
def parts(a):return {label(c):c for c in direct(a)}
def coords(c):return list(asif(c.Transform2,api.IMathTransform).ArrayData)
def measure(C,qs):
 out={}
 for (n,g),c in C.items():
  if n=='body':continue
  exp=asif(placement(n,g,qs[n]),api.IMathTransform).ArrayData;act=coords(c)
  err=math.dist(act[9:12],exp[9:12])*1000
  if g!='wheel':err=max(err,100*np.max(np.abs(np.array(act[:9])-exp[:9])))
  out[n+'_'+g]=round(float(err),6)
 return out
def mate_errors(m):
 f=m.FirstFeature();entries=[]
 while f:
  f=asif(f,api.IFeature)
  if f.GetTypeName2()=='MateGroup':
   s=f.GetFirstSubFeature()
   while s:
    s=asif(s,api.IFeature)
    if s.GetTypeName2().startswith('Mate'):entries.append([s.Name,int(s.GetErrorCode2(False)[0])])
    s=s.GetNextSubFeature()
  f=f.GetNextFeature()
 return entries
names=[v[0] for v in corner_order]
poses={key:dict(zip(names,angles)) for key,angles in [('Ride',[-7]*4),('Crouch',[-36]*4),('Liftoff',[22]*4),('FL_Raised',[-36,10,10,10]),('Diagonal',[-36,22,22,-36]),('Motion',[-7]*4),('Motion_MID',[-7]*4)]}
def build():
 m,a=swb.new_ass(topfile);activate(m);C={}
 body=insert(m,a,rack,2,'Equipment',tr(),True);body.ReferencedConfiguration='Base'
 for name,side,front in corner_order:
  for g in groups:
   path=OUT/'R1'/'groups'/(g+'.SLDASM') if side*front==1 else OUT/'LH'/('LH_'+g+'.SLDASM')
   c=insert(m,a,path,2,name+'_'+g,placement(name,g,-7),False);C[name,g]=c
  b=C[name,'base'];mate(m,a,name+'_mount_to_chassis',[body,b],16)
  for axis,g,h,axial in [('A','base','drive',True),('B','base','passive',True),('C','drive','carrier',True),('D','passive','carrier',False),('W','carrier','wheel',True)]:
   mate(m,a,name+'_pivot_'+axis,[asif(C[name,k].FeatureByName('Axis_'+axis),api.IFeature) for k in (g,h)],0)
   if axial:mate(m,a,name+'_shoulder_'+h,[plane(b,0),plane(C[name,h],0)],0)
  print('loop',name,flush=True)
 m.ForceRebuild3(False);save(m,topfile)
 for k,qs in poses.items():
  if not m.GetConfigurationByName(k):m.AddConfiguration3(k,'R5 mechanism','',0)
  m.ShowConfiguration2(k);cc=parts(a);cc['body','body'].ReferencedConfiguration='MID' if k.endswith('MID') else 'Base'
  for (n,g),c in cc.items():
   if g not in ['base','body']:c.Transform2=placement(n,g,qs[n])
  m.EditRebuild3();m.ForceRebuild3(False);obs=measure(cc,qs)
  assert max(obs.values())<.035,(k,obs);save(m,topfile);print('configuration',k,flush=True)
 m.ShowConfiguration2('Motion');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,topfile);sw.CloseDoc(m.GetTitle())
def validate():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);results={};drag=[]
 for k,qs in poses.items():
  m.ShowConfiguration2(k);m.ForceRebuild3(False);C=parts(a);test=measure(C,qs);errors=mate_errors(m)
  assert max(test.values())<.035,(k,test)
  assert len(errors)==40 and not any(v for n,v in errors),(k,errors)
  deep=[asif(v,api.IComponent2) for v in a.GetComponents(False)]
  missing=[c.Name2 for c in deep if not c.IsSuppressed() and (not c.GetModelDoc2() or not Path(c.GetPathName()).is_relative_to(OUT))]
  assert not missing,(k,missing)
  results[k]=dict(angles=qs,error_mm=max(test.values()),mates=len(errors),resolved=sum(not c.IsSuppressed() for c in deep),rack=C['body','body'].ReferencedConfiguration)
 m.ShowConfiguration2('Motion');m.ForceRebuild3(False);C=parts(a)
 qs=poses['Motion'].copy()
 for n in names:
  for q in [-36,22,-7]:
   qs[n]=q;ok=C[n,'drive'].SetTransformAndSolve2(placement(n,'drive',q));m.EditRebuild3()
   out=measure(C,qs);err=max(out.values());drag.append([n,q,bool(ok),err])
   print('drag',drag[-1],flush=True)
   assert ok and err<.06,(n,q,ok,out)
 m.ForceRebuild3(False);m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,topfile)
 write(ROOT/'data'/'R5_motion.json',dict(reopened=results,drag=drag))
 sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 flag=sw.CommandInProgress
 try:
  sw.CommandInProgress=True
  if '--check' not in sys.argv:
   from r5_saddle_seat import run
   run()
   from r5_drive_split import install
   install();build()
  validate()
 finally:sw.CommandInProgress=flag

