from r5_vehicle import *
from r5_instances import records,filepath
def ensure(r):
 ra=asif(r,api.IAssemblyDoc);activate(r);r.ShowConfiguration2('MID');r.ForceRebuild3(False)
 rows=direct(ra);targets={}
 for t in records:
  if not t['optional']:continue
  stem=filepath(t['id']).stem
  match=[c for c in rows if Path(c.GetPathName()).stem.removeprefix('Q8R5_')==stem and not c.IsSuppressed() and np.linalg.norm(np.array(coords(c)[9:12])*1000-np.array(t['pos']))<.06]
  assert len(match)==1,(stem,t['pos']);targets[match[0].Name2]=t['name']
 states={}
 for cfg in ['MID','Base','MID','Base']:
  r.ShowConfiguration2(cfg);r.ForceRebuild3(True);expected=cfg=='Base'
  observed={c.Name2:c.IsSuppressed() for c in direct(ra) if c.Name2 in targets}
  assert len(observed)==19,(cfg,len(observed))
  fixed=0
  for n,s in observed.items():
   if bool(s)!=expected:
    c=asif(ra.GetComponentByName(n),api.IComponent2);ret=c.SetSuppression2(0 if expected else 2);assert ret==2,(cfg,n,ret);fixed+=1
  r.ForceRebuild3(False);after=[c for c in direct(ra) if c.Name2 in targets];assert len(after)==19 and all(bool(c.IsSuppressed())==expected for c in after),cfg
  states[cfg]=sum(not c.IsSuppressed() for c in after);print('optional',cfg,'visible instances',states[cfg],'corrected',fixed,flush=True)
 save(r,Path(r.GetPathName()));return states
if __name__=='__main__':
 old=sw.CommandInProgress
 try:
  sw.CommandInProgress=True;pa=ROOT/'交付'/'SolidWorks'/('Q8R5_'+rack.name);d=open_doc(pa,2);results=ensure(d);write(ROOT/'data/R5_optional.json',results)
 finally:sw.CommandInProgress=old
