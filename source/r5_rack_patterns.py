from r5_rack import *
def pcb_hole(c,x,y,r):
 d=asif(c.GetModelDoc2(),api.IPartDoc)
 for raw in d.GetBodies2(0,False):
  body=asif(raw,api.IBody2);box=body.GetBodyBox()
  if not (box[0]<=x/1000<=box[3] and box[1]<=y/1000<=box[4] and box[2]<=.001<=box[5]):continue
  for raw in body.GetFaces():
   f=asif(raw,api.IFace2);s=asif(f.GetSurface(),api.ISurface)
   if s.IsCylinder():
    val=s.CylinderParams
    if abs(val[5])>.999 and max(abs(val[0]*1000-x),abs(val[1]*1000-y),abs(val[6]*1000-r))<.02:return asif(c.GetCorrespondingEntity(f),api.IEntity)
 raise RuntimeError('PCB pilot')
def run():
 m=open_doc(rack,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('MID');m.ForceRebuild3(True)
 def comp(k,pos=None):
  for c in direct(a):
   if Path(c.GetPathName())!=filepath(k):continue
   loc=np.array(asif(c.Transform2,api.IMathTransform).ArrayData[9:12])*1000
   if pos is None or np.linalg.norm(loc-pos)<.04:return c
  raise RuntimeError((k,pos))
 # Second real hole in each pattern clocks the supported device around its first post.
 for k,pos,local,post,r in [('XT_saddle',[25,101,36],(25,-9,1.7),'Xsp',1.52),('MC02',[89.8,-34,36],(25.8,18,1.2),'Msp',1.05),('MID_fit',[108,-4,36],(108,34.5,2.25),'Lsp100',2.02)]:
  name=k+'_second_mount';c=comp(k)
  if not a.FeatureByName(name):
   mate(m,a,name,[(pcb_hole(c,*local) if k=='MC02' else face(c,'c',local)),face(comp(post,pos),'c',(0,0,r))],1)
  print('pattern',k,c.GetConstrainedStatus(),flush=True)
 for cfg in ['MID','Base']:
  m.ShowConfiguration2(cfg);m.ForceRebuild3(True)
  for k in (['XT_saddle','MC02','MID_fit'] if cfg=='MID' else ['XT_saddle','MC02']):
   c=comp(k);print(cfg,k,c.GetConstrainedStatus(),flush=True);assert c.GetConstrainedStatus()==3
 save(m,rack);sw.CloseDoc(m.GetTitle())
if __name__=='__main__':run()

