from vehicle_sw import *
def install():
 folder=OUT/'R5_parts'
 for k,filename in [('M01','R5_4310_Stator'),('Rotor4310','R5_4310_Output')]:
  if not (folder/(filename+'.SLDPRT')).exists():fixedpart(filename,leg.PARTS[k],folder)
 for mirrored in [False,True]:
  for g,k in [('base','R5_4310_Stator'),('drive','R5_4310_Output')]:
   path=(OUT/'LH'/('LH_'+g+'.SLDASM')) if mirrored else OUT/'R1'/'groups'/(g+'.SLDASM')
   m=open_doc(path,2);activate(m);a=asif(m,api.IAssemblyDoc)
   old=[c for c in direct(a) if Path(c.GetPathName()).stem=='M01']
   for c in old:
    m.ClearSelection2(True);assert c.Select4(False,None,False)
    assert asif(m.Extension,api.IModelDocExtension).DeleteSelection2(0)
   if not any(Path(c.GetPathName()).stem==k for c in direct(a)):insert(m,a,folder/(k+'.SLDPRT'),1,k,tr(),True)
   m.ForceRebuild3(False);save(m,path);sw.CloseDoc(m.GetTitle());print('output flange',path.name,flush=True)

