from r5_static import proto,rigid,bounds,meet
from r5_instances import records,matrix
from common import *
jet=next(t for t in records if t['id']=='Jetson_Orin_Nano')
s=rigid(proto(jet['id']),matrix(jet),jet['pos']);pairs=[]
solids=[(v,bounds(v)) for v in s.Solids()]
for t in (v for v in records if v['id']=='JetClamp'):
 c=rigid(proto('JetClamp'),matrix(t),t['pos']);b=bounds(c);best=[]
 for displacement in [-.1,.5]:
  test=c.translate((0,0,-displacement));bb=bounds(test);vol=sum(abs(v.intersect(test).Volume()) for v,a in solids if meet(bb,a,.001))
  best.append(round(vol,4))
 pairs.append([t['name'],*best])
print('contact volumes OEM moved -0.1/+0.5 mm',pairs,flush=True);write(ROOT/'data/R5_jet_clamp.json',pairs)

