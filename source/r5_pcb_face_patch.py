from pathlib import Path
p=Path('r5_rack_patterns.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace('def run():','''def pcb_hole(c,x,y,r):
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
def run():''')
s=s.replace("mate(m,a,name,[face(c,'c',local),", "mate(m,a,name,[(pcb_hole(c,*local) if k=='MC02' else face(c,'c',local)),")
p.write_text(s,encoding='utf8')

