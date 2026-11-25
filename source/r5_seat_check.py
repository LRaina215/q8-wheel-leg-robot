from r5_static import *
from common import write,ROOT
camera=next(t for t in records if t['id']=='Astra_Pro_Plus')
def actual(t):return rigid(proto(t['id']),matrix(t),t['pos'])
camera=actual(camera);out=[]
for s in (t for t in records if t['id']=='Astra_saddle'):
 seat=actual(s)
 for b in (t for t in records if t['id']=='Flat3x10' and t['pos'][0]==s['pos'][0]):
  bolt=actual(b);nom=abs(seat.intersect(bolt).Volume());push=abs(seat.intersect(bolt.translate((0,0,-.10))).Volume())
  cv=sum(abs(v.intersect(bolt).Volume()) for v in camera.Solids() if meet(bounds(v),bounds(bolt)))
  assert nom<.01 and push>.4 and cv<.01,(nom,push,cv)
  out.append([b['name'],round(nom,5),round(push,5),round(cv,5)])
write(ROOT/'data/R5_countersink.json',out);print(out)

