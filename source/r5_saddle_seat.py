from r5_native_parts import folder,asif,api,sw,save,open_doc,ROOT,activate
from r5_instances import filepath
from pathlib import Path
def run():
 path=filepath('Astra_saddle');m=open_doc(path,1);activate(m)
 feat=asif(asif(m,api.IPartDoc).FeatureByName('Sketch_Flat_head_90deg'),api.IFeature)
 dim=feat.GetFirstDisplayDimension();changed=[]
 while dim:
  dd=asif(dim,api.IDisplayDimension);v=asif(dd.GetDimension2(0),api.IDimension)
  if abs(float(v.SystemValue)-.0034)<.000001 or abs(float(v.SystemValue)-.003)<.000001:
   v.SystemValue=.003;changed.append(v.FullName)
  dim=feat.GetNextDisplayDimension(dd)
 assert len(changed)==2,changed
 m.EditRebuild3();m.ForceRebuild3(False);save(m,path);save(m,ROOT/'source/body_step/R5_Astra_saddle.step');sw.CloseDoc(m.GetTitle());print(changed,flush=True)
if __name__=='__main__':run()

