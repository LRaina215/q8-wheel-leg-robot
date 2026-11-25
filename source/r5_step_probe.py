from r5_bundle import *
folder=ROOT/'交付'/'SolidWorks';pa=folder/'Q8R5_USBnet.SLDPRT';ps=folder/'Q8R5_USBnet.step'
m=open_doc(pa,1);activate(m);f=m.FirstFeature()
while f:
 f=asif(f,api.IFeature);typ=f.GetTypeName2()
 print('tree',f.Name,typ,flush=True)
 if 'Import' in typ or 'inter' in typ.lower() or 'Model' in typ or 'step' in f.Name.lower():
  print(f.Name,typ,f.GetImportedFileName(),flush=True)
  try:print('change',f.SetImportedFileName(str(ps)),f.GetImportedFileName(),flush=True)
  except Exception as e:print('change err',e)
  save(m,pa);print('refs1',references(pa),flush=True)
  if ps not in references(pa):
   print('break',f.BreakLink(True,True),flush=True);m.ForceRebuild3(False);save(m,pa);print('refs2',references(pa),flush=True)
  break
 f=f.GetNextFeature()
sw.CloseDoc(m.GetTitle())
