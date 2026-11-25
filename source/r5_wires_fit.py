from wire_check import Surface,dense
from r5_static import proto
from r5_instances import records,ids,matrix
from common import *
routed=read(ROOT/'data/R5_wiring.json');checks=0;hits={}
samples={}
for t in records:
 k=t['id']
 if k not in ids:continue
 if k not in samples:
  pts,tri=proto(k).tessellate(.08,.18);samples[k]=Surface(np.array([v.toTuple() for v in pts]),np.array(tri))
for wire in routed['routes']:
 radius=wire['dia']/2
 points=wire['points']
 frames=list(enumerate(wire['frames'][:59],-36)) if 'frames'in wire else [(None,points)]
 for angle,path in frames:
  line=dense(path)
  for t in records:
   k=t['id']
   if k not in samples:continue
   samples_local=(line-t['pos'])@matrix(t)
   gap=samples[k].gap(samples_local,radius+1)-radius;checks+=1
   if gap<-.02:
    key=wire['id']+'/'+t['name'];prev=hits.get(key)
    if prev is None or prev['gap_mm']>gap:hits[key]=dict(gap_mm=round(gap,3),angle=angle)
print('wiring',hits,flush=True);write(ROOT/'data/R5_wires.json',dict(pairs_sampled=checks,step_mm=1,hits=hits))

