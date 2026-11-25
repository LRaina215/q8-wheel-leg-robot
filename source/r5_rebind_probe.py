from r5_pose_reference import *
import shutil
dest=ROOT/'data'/'reference_probe';dest.mkdir(exist_ok=True)
p=dest/('Q8R5_'+refpath.name);r=dest/('Q8R5_'+rack.name)
shutil.copy2(refpath,p);shutil.copy2(rack,r)
deps=lambda t:list(sw.GetDocumentDependencies2(str(t),False,False,False) or [])
print('before',deps(p)[:10],flush=True);print('edit',sw.ReplaceReferencedDocument(str(p),str(rack),str(r)),flush=True);print('after',deps(p)[:10],flush=True)
