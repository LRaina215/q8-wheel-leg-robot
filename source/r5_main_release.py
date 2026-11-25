from r5_motion_release import *
from r5_planar_chain import drop
def run():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('Motion')
 for name,err in mate_errors(m):
  if name.startswith('距离') or '_Pose_' in name:drop(m,asif(a.FeatureByName(name),api.IFeature))
 sketch=a.FeatureByName('Hip_height_datum_Zminus100')
 if sketch:drop(m,asif(sketch,api.IFeature))
 for cfg in list(m.GetConfigurationNames()):
  if cfg not in ['Motion','Motion_MID']:assert m.DeleteConfiguration2(cfg),cfg
 for cfg in ['Motion_MID','Motion']:
  m.ShowConfiguration2(cfg);C=parts(a);C['body','body'].ReferencedConfiguration='MID' if cfg.endswith('MID') else 'Base'
  C=solve_rig(m,a,poses['Motion']);err=measure(C,poses['Motion']);print('nominal',cfg,max(err.values()),flush=True);assert max(err.values())<.04,err
  save(m,topfile)
 m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,topfile);sw.CloseDoc(m.GetTitle())
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);result={};rows=[]
 for cfg in ['Motion_MID','Motion']:
  m.ShowConfiguration2(cfg);m.ForceRebuild3(True);C=parts(a);qs=poses['Motion'].copy();dev=measure(C,qs);mf=mate_errors(m);pins=pin_offsets(C)
  states={n+'_'+g:c.GetConstrainedStatus() for (n,g),c in C.items()}
  assert len(mf)==44 and not any(e for k,e in mf) and max(dev.values())<.04 and max(pins.values())<.04 and all(v in [2,3] for v in states.values()),(cfg,dev,states,mf)
  result[cfg]=dict(angles=qs.copy(),error_mm=max(dev.values()),pin_D_axis_offset_mm=pins,mates=len(mf),rack=C['body','body'].ReferencedConfiguration)
  print('reopened',cfg,flush=True)
 for n in names:
  for target in [-36,22,-7]:
   q0=qs[n];drag_segment(m,a,C,n,q0,target);qs[n]=target;dev=measure(C,qs);err=max(dev.values());pins=pin_offsets(C)
   print('independent',n,target,err,pins[n],flush=True)
   assert err<.06 and max(pins.values())<.035 and C[n,'drive'].GetConstrainedStatus()==2,(n,target,dev,pins)
   rows.append([n,target,True,err]);write(ROOT/'data/R5_drag_validation.json',rows)
 write(ROOT/'data/R5_motion.json',dict(reopened=result,drag=rows,mode='IDragOperator.DragAsUI applied to each hip, independent of the other three. Verified after EndDrag and native rebuild.'))
 save(m,topfile);sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 old=sw.CommandInProgress
 try:sw.CommandInProgress=True;run()
 finally:sw.CommandInProgress=old

