from r5_vehicle import *
import pythoncom
m=open_doc(topfile,2);activate(m);ext=asif(m.Extension,api.IModelDocExtension);o=ext._oleobj_
for name in ['GetPackAndGo','SavePackAndGo','GetDependencies','SelectByID2']:
 try:print('id',name,o.GetIDsOfNames(name),flush=True)
 except Exception as e:print(e)
for flags in [pythoncom.DISPATCH_METHOD,pythoncom.DISPATCH_PROPERTYGET,3]:
 try:
  raw=o.Invoke(o.GetIDsOfNames('GetPackAndGo'),0,flags,True);print('get',flags,type(raw),flush=True)
  if raw:break
 except Exception as e:print('failed',flags,e,flush=True)
