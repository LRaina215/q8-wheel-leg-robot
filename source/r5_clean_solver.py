from r5_axis_drag import solve_rig
from r5_vehicle import *
def clean():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('Ride')
 orig={n+'_'+s for n in names for s in ['mount_to_chassis','pivot_A','pivot_B','pivot_C','pivot_D','pivot_W','shoulder_drive','shoulder_passive','shoulder_carrier','shoulder_wheel']}
 for name,_ in mate_errors(m):
  if name in orig:continue
  f=asif(a.FeatureByName(name),api.IFeature);m.ClearSelection2(True);assert f.Select2(False,0);assert asif(m.Extension,api.IModelDocExtension).DeleteSelection2(0)
 for k in poses:
  m.ShowConfiguration2(k);C=parts(a)
  cs=[C[n,'base'] for n in names if C[n,'base'].IsFixed()]
  if cs:
   m.ClearSelection2(True)
   for c in cs:assert c.Select4(True,None,False)
   a.UnfixComponent();m.ClearSelection2(True)
  print('grounded only body',k,len(cs),flush=True)
 m.ShowConfiguration2('Ride');C=solve_rig(m,a,poses['Ride'])
 print('clean',[(g,c.IsFixed(),c.GetConstrainedStatus()) for (n,g),c in C.items() if n=='FL'],len(mate_errors(m)),flush=True)
 save(m,topfile)
if __name__=='__main__':clean()

