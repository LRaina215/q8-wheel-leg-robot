from r5_vehicle import *
m=open_doc(topfile,2);activate(m);m.ShowConfiguration2('Motion')
if not m.GetConfigurationByName('SolveProbe'):m.AddConfiguration3('SolveProbe','','',0)
m.ShowConfiguration2('SolveProbe');a=asif(m,api.IAssemblyDoc);C=parts(a)
for n in names:
 f=asif(a.FeatureByName(n+'_mount_to_chassis'),api.IFeature);print('remove lock',n,f.SetSuppression2(0,1,None),flush=True)
 c=C[n,'base'];m.ClearSelection2(True);c.Select4(False,None,False);a.FixComponent();m.ClearSelection2(True)
m.ForceRebuild3(True)
print('ground',[(g,c.IsFixed(),c.GetConstrainedStatus()) for (n,g),c in C.items() if n=='FL'],flush=True)
for q in [-12,9,-7]:
 c=C['FL','carrier'];ok=c.SetTransformAndSolve2(placement('FL','carrier',q));m.EditRebuild3()
 v=coords(C['FL','carrier']);print('carrier pose',q,ok,round(math.degrees(math.asin(-v[11]*1000/110)),4),c.GetConstrainedStatus(),flush=True)

