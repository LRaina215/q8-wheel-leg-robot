from r5_motion_release import *
def run():
 dest=ROOT/'交付'/'SolidWorks';pa=read(ROOT/'data/R5_pack.json');rackf=dest/('Q8R5_'+rack.name);r=open_doc(rackf,2);ra=asif(r,api.IAssemblyDoc);state={}
 for k in ['Base','MID']:
  r.ShowConfiguration2(k);r.ForceRebuild3(False);mf=mate_errors(r);assert len(mf)==227 and not any(e for _,e in mf),(k,[row for row in mf if row[1]]);state[k]=len(mf)
 r.ShowConfiguration2('Base');m=open_doc(dest/pa['main'],2);a=asif(m,api.IAssemblyDoc);activate(m);m.ShowConfiguration2('Motion');m.ForceRebuild3(False)
 live_counts={}
 for cfg,wanted,expected in [('Motion_MID','MID',True),('Motion','Base',False)]:
  r.ShowConfiguration2(wanted);m.ShowConfiguration2(cfg);m.ForceRebuild3(False)
  eq=next(c for c in direct(a) if Path(c.GetPathName())==rackf)
  assert eq.ReferencedConfiguration==wanted,(cfg,eq.ReferencedConfiguration)
  rawkids=[asif(x,api.IComponent2) for x in eq.GetChildren() or []]
  mids=[c for c in rawkids if Path(c.GetPathName()).stem.removeprefix('Q8R5_')=='MID360']
  assert any(not c.IsSuppressed() for c in mids)==expected,(cfg,[c.IsSuppressed() for c in mids])
  live_counts[cfg]=sum(not asif(x,api.IComponent2).IsSuppressed() for x in a.GetComponents(False))
 pa['reopened']=live_counts;pa['optional_rack_instances']=read(ROOT/'data/R5_optional.json')
 # The independent posture assembly references the Base rack in each of its five configurations.
 ref=open_doc(dest/pa['pose'],2);activate(ref);aa=asif(ref,api.IAssemblyDoc)
 for cfg in pa['reference_reopened']:
  ref.ShowConfiguration2(cfg);ref.ForceRebuild3(True)
  eq=next(c for c in direct(aa) if Path(c.GetPathName())==rackf);assert eq.ReferencedConfiguration=='Base'
  kids=[asif(raw,api.IComponent2) for raw in eq.GetChildren() or []]
  assert not any(not c.IsSuppressed() and Path(c.GetPathName()).stem.removeprefix('Q8R5_')=='MID360' for c in kids),cfg
  pa['reference_reopened'][cfg]=sum(not asif(raw,api.IComponent2).IsSuppressed() for raw in aa.GetComponents(False))
 ref.ShowConfiguration2('Ride');save(ref,dest/pa['pose']);sw.CloseDoc(ref.GetTitle());activate(m)
 write(ROOT/'data/R5_pack.json',pa)
 C={}
 for c in direct(a):
  stem=Path(c.GetPathName()).stem.removeprefix('Q8R5_')
  if stem==rack.stem:continue
  v=coords(c);n=('F' if v[10]>0 else 'R')+('R' if v[9]>0 else 'L');C[n,stem.removeprefix('LH_')]=c
 assert len(C)==20;qs=dict.fromkeys(names,-7);assert max(measure(C,qs).values())<.04;results=[]
 for n,u,t in [('FL',-7,-36),('RR',-7,22),('FL',-36,-7),('RR',22,-7)]:
  drag_segment(m,a,C,n,u,t);qs[n]=t;e=max(measure(C,qs).values());d=max(pin_offsets(C).values());assert max(e,d)<.04,(n,e,d);results.append([n,t,e,d])
 m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();m.GraphicsRedraw2();save(m,dest/pa['main'])
 write(ROOT/'data/R5_shipped_qa.json',dict(rack_mates=state,diagonal_drag=results));print('portable rack and two independent native hips checked',state,results,flush=True)
if __name__=='__main__':
 flag=sw.CommandInProgress
 try:sw.CommandInProgress=True;run()
 finally:sw.CommandInProgress=flag
