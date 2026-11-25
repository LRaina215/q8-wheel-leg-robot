from r5_axis_drag import *
from r5_rack import mate,plane
def drop(m,f):
 m.ClearSelection2(True);assert f.Select2(False,0);assert asif(m.Extension,api.IModelDocExtension).DeleteSelection2(0);m.ClearSelection2(True)
def run():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('Ride')
 for name,ec in mate_errors(m):
  if name.endswith(('_Pose_Height','_pivot_D')) or ec:drop(m,asif(a.FeatureByName(name),api.IFeature))
 C=solve_rig(m,a,poses['Ride']);measurements=measure(C,poses['Ride']);print('initialized',max(measurements.values()),flush=True)
 for n in names:
  for label,first,second in [('Parallel_arms','drive','passive'),('Upright_carrier','base','carrier')]:
   key=n+'_'+label
   if a.FeatureByName(key):continue
   mate(m,a,key,[plane(C[n,first],2),plane(C[n,second],2)],3)
 m.ForceRebuild3(True);e=measure(C,poses['Ride']);print('parallelogram',max(e.values()),[(g,c.GetConstrainedStatus()) for (n,g),c in C.items() if n=='FL'],flush=True);assert max(e.values())<.04,e
 save(m,topfile)
if __name__=='__main__':run()

