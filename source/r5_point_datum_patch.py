from pathlib import Path
p=Path('r5_pose_stops.py');s=p.read_text(encoding='utf-8-sig').replace('(.062-.110','(.100-.110').replace("_Pose_B_to_C","_Pose_Height")
s=s.replace(' for n in names:\n  key=',""" datum=a.FeatureByName('Hip_height_datum_Zminus100')
 if not datum:
  m.ClearSelection2(True);sm=asif(m.SketchManager,api.ISketchManager);sm.Insert3DSketch(True)
  pt=asif(sm.CreatePoint(0,0,-.1),api.ISketchPoint);m.ClearSelection2(True);pt.Select4(False,None);m.SketchAddConstraints('sgFIXED');m.ClearSelection2(True)
  feat=asif(asif(m.Extension,api.IModelDocExtension).GetLastFeatureAdded(),api.IFeature);feat.Name='Hip_height_datum_Zminus100';sm.Insert3DSketch(True)
 datum=asif(a.FeatureByName('Hip_height_datum_Zminus100'),api.IFeature)
 sk=asif(datum.GetSpecificFeature2(),api.ISketch);point=asif(sk.GetSketchPoints2()[0],api.ISketchPoint)
 for n in names:
  key=""")
s=s.replace("one=asif(C[n,'base'].FeatureByName('Axis_B'),api.IFeature);two=plane(C[n,'carrier'],1)","two=plane(C[n,'carrier'],1);sd=asif(asif(m.SelectionManager,api.ISelectionMgr).CreateSelectData(),api.ISelectData);sd.Mark=1")
s=s.replace("assert one.Select2(False,1) and two.Select2(True,1)","assert point.Select4(False,sd) and two.Select2(True,1)").replace('5,2,False,val,val,val','5,2,False,val,0,0')
p.write_text(s,encoding='utf8')

