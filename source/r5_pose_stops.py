from r5_motion_release import *
from r5_rack import plane
def spacing(q):return (.100-.110*math.sin(math.radians(q)))
def ffeature(a,n):return asif(a.FeatureByName(n+'_Pose_Height'),api.IFeature)
def stops():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('Ride');C=solve_rig(m,a,poses['Ride'])
 datum=a.FeatureByName('Hip_height_datum_Zminus100')
 if not datum:
  m.ClearSelection2(True);sm=asif(m.SketchManager,api.ISketchManager);sm.Insert3DSketch(True)
  pt=asif(sm.CreatePoint(0,0,-.1),api.ISketchPoint);m.ClearSelection2(True);pt.Select4(False,None);m.SketchAddConstraints('sgFIXED');m.ClearSelection2(True)
  feat=asif(asif(m.Extension,api.IModelDocExtension).GetLastFeatureAdded(),api.IFeature);feat.Name='Hip_height_datum_Zminus100';sm.Insert3DSketch(True)
 datum=asif(a.FeatureByName('Hip_height_datum_Zminus100'),api.IFeature)
 sk=asif(datum.GetSpecificFeature2(),api.ISketch);point=asif(sk.GetSketchPoints2()[0],api.ISketchPoint)
 for n in names:
  key=n+'_Pose_Height'
  if a.FeatureByName(key):continue
  two=plane(C[n,'carrier'],1);sd=asif(asif(m.SelectionManager,api.ISelectionMgr).CreateSelectData(),api.ISelectData);sd.Mark=1
  m.ClearSelection2(True);assert point.Select4(False,sd) and two.Select2(True,1)
  val=spacing(-7);res,err=a.AddMate5(5,2,False,val,0,0,1,1,0,0,0,False,False,0,0)
  assert res and err==1,(n,err);ff=asif(asif(m.Extension,api.IModelDocExtension).GetLastFeatureAdded(),api.IFeature);ff.Name=key
  m.ClearSelection2(True);print('pose datum',key,flush=True)
 for k,qs in poses.items():
  m.ShowConfiguration2(k);m.ClearSelection2(True)
  for n in names:
   ff=ffeature(a,n);ff.SetSuppression2(1,1,None)
   dim=asif(asif(ff.GetFirstDisplayDimension(),api.IDisplayDimension).GetDimension2(0),api.IDimension)
   err=dim.SetSystemValue3(spacing(qs[n]),1,None);assert err==0,(n,k,err)
  m.EditRebuild3();m.ForceRebuild3(True);C=parts(a);test=measure(C,qs)
  if max(test.values())>.05:
   C=solve_rig(m,a,qs);test=measure(C,qs)
  print('held',k,max(test.values()),flush=True);assert max(test.values())<.05,(k,test)
  if k.startswith('Motion'):
   for n in names:ffeature(a,n).SetSuppression2(0,1,None)
   m.ForceRebuild3(True);assert max(measure(C,qs).values())<.05
  save(m,topfile)
 m.ShowConfiguration2('Motion');m.ForceRebuild3(True);m.ViewZoomtofit2();save(m,topfile);sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 old=sw.CommandInProgress
 try:sw.CommandInProgress=True;stops()
 finally:sw.CommandInProgress=old

