from vehicle_sw import *
from r5_instances import records,filepath,matrix
from r5_parts import jc,mc,xt,deckpts,drivers,astra,midpts
from collections import defaultdict
rack=OUT/'Q8_R5_设备机架.SLDASM'
def mate(m,a,name,refs,kind):
 m.ClearSelection2(True);sel=asif(m.SelectionManager,api.ISelectionMgr);sd=asif(sel.CreateSelectData(),api.ISelectData);sd.Mark=1
 for i,v in enumerate(refs):
  if isinstance(v,api.IFeature):ok=v.Select2(i>0,1)
  elif isinstance(v,api.IComponent2):ok=v.Select4(i>0,sd,False)
  else:ok=v.Select4(i>0,sd)
  if not ok:raise RuntimeError(('select',name,i))
 res,err=a.AddMate5(kind,2,False,0,0,0,1,1,0,0,0,False,False,0,0)
 if not res or err!=1:raise RuntimeError(('mate',name,err))
 f=asif(asif(m.Extension,api.IModelDocExtension).GetLastFeatureAdded(),api.IFeature)
 if f.GetTypeName2().startswith('Mate') and f.GetTypeName2()!='MateGroup':f.Name=name
 m.ClearSelection2(True)
cache={}
def face(c,mode,data):
 path=c.GetPathName();key=(path,mode,tuple(data))
 if path not in cache:
  catalogue={'p':[],'c':[]};doc=asif(c.GetModelDoc2(),api.IPartDoc)
  for raw in doc.GetBodies2(0,False):
   for rawf in asif(raw,api.IBody2).GetFaces():
    f=asif(rawf,api.IFace2);surf=asif(f.GetSurface(),api.ISurface)
    if surf.IsCylinder():
     v=surf.CylinderParams
     if abs(v[5])>.9999:catalogue['c'].append(((v[0]*1000,v[1]*1000,v[6]*1000),f))
    elif surf.IsPlane():
     v=surf.PlaneParams
     if abs(v[2])>.9999:catalogue['p'].append(((v[5]*1000,),f))
  cache[path]=catalogue
 if key not in cache:
  match=next((f for vals,f in cache[path][mode] if max(abs(a-b) for a,b in zip(vals,data))<.015),None)
  if match is None:raise RuntimeError(('face',path,mode,data))
  cache[key]=match
 return asif(c.GetCorrespondingEntity(cache[key]),api.IEntity)
def plane(c,idx):
 d=asif(c.GetModelDoc2(),api.IModelDoc2)
 return asif(c.FeatureByName(planes(d)[idx]),api.IFeature)
def build():
 if rack.exists():
  m=open_doc(rack,2);a=asif(m,api.IAssemblyDoc)
 else:m,a=swb.new_ass(rack)
 activate(m);available=[asif(v,api.IComponent2) for v in (a.GetComponents(True) or [])]
 C={};index=defaultdict(list);T={};opt=[]
 def attach(k,parent,kxy,pxy,kz,pz,clock=True):
  mate(m,a,k+'_axis',[face(C[k],'c',kxy),face(C[parent],'c',pxy)],1)
  mate(m,a,k+'_seat',[face(C[k],'p',[kz]),face(C[parent],'p',[pz])],0)
  if clock:mate(m,a,k+'_clock',[plane(C[k],2),plane(C[parent],2)],3)
 def lock(k,parent):mate(m,a,k+'_locate',[C[parent],C[k]],16)
 # Existing hip hardware consists of 64 standard components held in one fixed-pattern assembly.
 entries=[t for t in records if not t['id'].startswith('B5')]
 entries.insert(1,dict(id='HipStack',name='HipStack',pos=[0,0,0],rz=0,up=False,optional=False))
 order=['Chassis','Deck','BuckTray','XT_saddle','Xsp','Astra_saddle','Bridge_tray','JetClamp','Msp','Lsp100','MID_fit']
 entries.sort(key=lambda t:order.index(t['id']) if t['id'] in order else len(order))
 for t in entries:
  k=t['name'];id=t['id'];path=OUT/'body'/'Hip_hardware.SLDASM' if id=='HipStack' else filepath(id)
  c=next((v for v in available if Path(v.GetPathName())==path and np.max(np.abs(np.array(asif(v.Transform2,api.IMathTransform).ArrayData[9:12])*1000-t['pos']))<.07),None)
  existed=c is not None
  if existed:available.remove(c)
  else:c=insert(m,a,path,2 if id=='HipStack' else 1,k,xf(t['pos'],matrix(t)),id=='Chassis')
  C[k]=c;index[id].append(k);T[k]=t
  if t['optional']:opt.append(k)
  x,y,z=t['pos']
  if id=='Chassis' or existed:continue
  if id=='Deck':attach(k,index['Chassis'][0],(*deckpts[0],2.25),(*deckpts[0],2.25),32,32)
  elif id=='BuckTray':attach(k,index['Chassis'][0],(-50,-17,1.7),(11,-30,1.7),0,-45)
  elif id in ['Astra_saddle','Bridge_tray','JetClamp','Msp','Xsp','Lsp100']:
   h={'Astra_saddle':(0,-15.5,1.7),'Bridge_tray':(-18,34,1.7),'JetClamp':(0,0,1.7),'Msp':(0,0,1.05),'Xsp':(0,0,1.52),'Lsp100':(0,0,2.02)}[id]
   r={'Msp':1.15,'Lsp100':2.25}.get(id,1.7)
   attach(k,index['Deck'][0],h,(x+h[0],y+h[1],r),0,36,id not in ['Msp','Xsp','Lsp100'])
  elif id=='XT_saddle':pass
  elif id=='MID_fit':attach(k,index['Lsp100'][0],(-108,-34.5,2.25),(0,0,2.02),0,100)
  elif k.startswith(('Deck_S','Jet_S','MC_S','XT_upper_S','XT_lower_S','Driver_S','Astra_S','Power_S','MID_columns_lower_S','MID_columns_upper_S','MID_sensor_S')):
   if k.startswith('Deck_S'):parent=index['Deck'][0];p=(x,y,2.25);seat=36
   elif k.startswith('Jet_S'):parent=next(key for key in index['JetClamp'] if T[key]['pos'][:2]==[x,y]);p=(0,0,1.7);seat=14.5
   elif k.startswith(('MC_S','XT_lower_S','MID_columns_lower_S')):parent=index['Deck'][0];p=(x,y,1.15 if id=='B2x16' else 2.25 if id=='B4x10' else 1.7);seat=32
   elif k.startswith('XT_upper_S'):parent=index['XT_saddle'][0];p=(x,y-110,1.7);seat=4
   elif k.startswith('Driver_S'):
    parent=min(index['Bridge_tray'],key=lambda n:abs(y-34-T[n]['pos'][1]));p=(x-T[parent]['pos'][0],34,1.7);seat=2.5
   elif k.startswith('Astra_S'):
    parent=next(n for n in index['Astra_saddle'] if T[n]['pos'][0]==x);p=(0,y-126.5,1.7);seat=3
   elif k.startswith('Power_S'):parent=index['BuckTray'][0];p=(x-61,y+13,1.7);seat=3
   else:parent=index['MID_fit'][0];p=(x,y+38.5,2.25 if id=='B4x10' else 1.65);seat=0 if k.startswith('MID_sensor') else 4
   radius=2 if id.startswith('B4') else 1 if id.startswith('B2') else 1.5
   attach(k,parent,(0,0,radius),p,0,seat,False)
  elif '_N' in k and id.startswith('Nut'):
   if k.startswith('Deck_'):parent=index['Chassis'][0];r=2.25;p=(x,y,r);seat=25.4;kz=3.2
   elif k.startswith('Power_'):parent=index['Chassis'][0];p=(x,y,1.7);seat=-49;kz=2.4
   elif k.startswith('MC_'):lock(k,index['MC02'][0]);continue
   else:parent=index['Deck'][0];p=(x,y,1.7);seat=32;kz=2.4
   attach(k,parent,(0,0,int(id[-1])/2+.02),p,kz,seat,k.startswith('Deck_'))
  elif id=='MC02':lock(k,index['Msp'][0])
  elif id=='Jetson_Orin_Nano':lock(k,index['JetClamp'][0])
  elif id=='MID360':lock(k,index['MID_fit'][0])
  elif id=='Driver':lock(k,min(index['Bridge_tray'],key=lambda n:abs(x-T[n]['pos'][0])))
  elif id=='YourCee20':lock(k,index['BuckTray'][0])
  elif id=='Astra_Pro_Plus':lock(k,index['Astra_saddle'][0])
  elif id=='XT_M60':lock(k,index['XT_saddle'][0])
  elif id=='USBnet':lock(k,index['MID_fit'][0])
  else:lock(k,index['Deck' if id in ['TXS0108E','FFC24_65'] else 'Chassis'][0])
  if len(C)%15==0:save(m,rack);print('mounted',len(C),k,flush=True)
 k=index['XT_saddle'][0];attach(k,index['Xsp'][0],(-25,-37,1.7),(0,0,1.52),0,36)
 m.ForceRebuild3(False)
 errors=[]
 for k,c in C.items():
  vals=asif(c.Transform2,api.IMathTransform).ArrayData;t=T[k]
  xyz=np.array(vals[9:12])*1000
  if np.max(np.abs(xyz-t['pos']))>.06:errors.append([k,xyz.tolist(),t['pos']])
 assert not errors,errors[:12]
 m.AddConfiguration3('MID','With MID fixture','',0);m.ShowConfiguration2('MID');m.EditRebuild3();save(m,rack)
 m.AddConfiguration3('Base','As assembled','',0);m.ShowConfiguration2('Base')
 from r5_optional import ensure
 ensure(m)
 m.EditRebuild3();m.ForceRebuild3(False);m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,rack);sw.CloseDoc(m.GetTitle())
 write(ROOT/'data'/'R5_mounts.json',{'components':len(C),'optional':len(opt),'position_errors':errors})
if __name__=='__main__':
 flag=sw.CommandInProgress
 try:sw.CommandInProgress=True;build()
 finally:sw.CommandInProgress=flag

