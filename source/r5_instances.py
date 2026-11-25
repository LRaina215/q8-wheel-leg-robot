from common import *
from r5_parts import parts as design,native_name,deckpts,mc,xt,jc,drivers,astra,midpts
old=read(ROOT/'data'/'layout.json')
ids=set(design);records=[]
def put(k,pos,name,angle=0,up=False,opt=False):
 records.append(dict(id=k,pos=list(pos),name=name,rz=angle,up=up,optional=opt))
for t in old['instances']:
 k=t['id']
 if k=='Jsp' or old['parts'][k]['kind']=='分布质量':continue
 put(k,[-35,-78.5,121] if k=='USBnet' else t['pos'],t['name'],t['rz'],opt=t['optional'])
for i,(x,y) in enumerate(jc):put('JetClamp',(x,y,36),'Jet_clamp_'+str(i+1),180 if x>0 else 0)
def stacks(tag,points,screw,z,nut=None,nz=0,up=False,opt=False):
 for i,(x,y) in enumerate(points,1):
  put(screw,(x,y,z),tag+'_S'+str(i),up=up,opt=opt)
  if nut:put(nut,(x,y,nz),tag+'_N'+str(i),opt=opt)
stacks('Deck',deckpts,'B4x16',36,'Nut4',22.2)
stacks('Jet',jc,'B3x22',50.5,'Nut3',29.6)
stacks('MC',mc,'B2x16',32,'Nut2',45.812,True)
stacks('XT_upper',xt,'B3x8',76)
stacks('XT_lower',xt,'B3x8',32,up=True)
stacks('Driver',[(x+dx,y+34) for x,y in drivers for dx in [-18,18]],'B3x12',38.5,'Nut3',29.6)
stacks('Astra',astra,'Flat3x10',39,'Nut3',29.6)
stacks('Power',[(11,-30),(107.5,-30),(72,52)],'B3x12',-42,'Nut3',-51.4)
def matrix(t):
 return xyzrot(t['rz'])@np.diag([1,-1 if t['up'] else 1,-1 if t['up'] else 1])
def filepath(k):
 if k in ids:return OUT/'R5_parts'/native_name(k)
 return OUT/('equipment' if old['parts'][k]['kind']=='设备' else 'body')/(k+'.SLDPRT')


stacks('MID_columns_lower',midpts,'B4x10',32,up=True,opt=True)
stacks('MID_columns_upper',midpts,'B4x10',140,opt=True)
stacks('MID_sensor',[(x,y-38.5) for x in [-18,18] for y in [-24,24]],'B3x8',136,up=True,opt=True)
