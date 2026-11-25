from r5_vehicle import *
def obs(m):
 a=asif(m,api.IAssemblyDoc)
 print('state',m.GetTitle(),[(c.Name2,c.IsFixed(),c.GetConstrainedStatus()) for c in direct(a)][:28],flush=True)
 ext=asif(m.Extension,api.IModelDocExtension)
 try:
  bad=ext.GetWhatsWrong()
  print('warnings',str(bad)[:1200],flush=True)
 except Exception as ex:print(str(ex)[:130],flush=True)
m=open_doc(topfile,2);activate(m);print('top before',flush=True);obs(m)
for p in [OUT/'R1'/'Q8_Single_Corner.SLDASM',rack]:
 d=open_doc(p,2);activate(d);d.EditRebuild3();obs(d)
activate(m)

