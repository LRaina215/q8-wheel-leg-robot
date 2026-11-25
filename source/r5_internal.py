"""Axial-section sweep of all installed part instances in one four-bar, including hardware."""
from common import *
from geometry import position,slice_op
from shapely import affinity
from shapely.geometry import Polygon
from itertools import combinations
def layers(t):
 ops=leg.PARTS[t['id']]['ops'];levels=sorted({round(z,7) for o in ops for z in (o['z'],o['z']+o['h'])});ans=[]
 for lo,hi in zip(levels,levels[1:]):
  g=Polygon()
  for o in ops:
   if o['z']<(lo+hi)/2<o['z']+o['h']:
    k=slice_op(o);g=g.difference(k) if o['cut'] else g.union(k)
  if g.is_empty:continue
  if t['flip']:g=affinity.scale(g,1,-1,origin=(0,0));lo,hi=-hi,-lo
  ans.append((lo+t['z'],hi+t['z'],g))
 return ans
def run():
 ins=leg.INST;secs=[layers(t) for t in ins];pairs=[]
 for i,j in combinations(range(len(ins)),2):
  if ins[i]['g']==ins[j]['g']:continue
  tiles=[(u,v,min(b,d)-max(a,c)) for u,(a,b,_) in enumerate(secs[i]) for v,(c,d,_) in enumerate(secs[j]) if min(b,d)-max(a,c)>.002]
  if tiles:pairs.append((i,j,tiles))
 hits={}
 for q in range(-36,23):
  gs=[]
  for t,ls in zip(ins,secs):
   x,y,_,a=position(t,q);r=math.radians(a);trans=[math.cos(r),-math.sin(r),math.sin(r),math.cos(r),x,y]
   group=[]
   for _,__,g in ls:
    h=affinity.affine_transform(g,trans);group.append((h,h.bounds))
   gs.append(group)
  for i,j,tiles in pairs:
   vol=0
   for u,v,dz in tiles:
    g,A=gs[i][u];h,B=gs[j][v]
    if A[0]>=B[2] or B[0]>=A[2] or A[1]>=B[3] or B[1]>=A[3]:continue
    vol+=dz*g.intersection(h).area
   if vol>.12:
    key=f"{ins[i]['g']}/{ins[i]['id']}#{i} - {ins[j]['g']}/{ins[j]['id']}#{j}"
    r=hits.setdefault(key,{'first':q,'last':q,'max_mm3':0.,'angle':q});r['last']=q
    if vol>r['max_mm3']:r.update(max_mm3=round(vol,4),angle=q)
 print('internal',len(ins),len(pairs),hits,flush=True)
 write(ROOT/'data/R5_internal_sweep.json',dict(angles=59,instances=len(ins),pairs_after_axial_test=len(pairs),hits=hits))
if __name__=='__main__':run()

