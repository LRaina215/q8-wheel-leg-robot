from r5_static import proto
from r5_instances import records,ids,matrix
from wire_space import *
import wire_space as ws
ws.cache=ROOT/'data'/'R5_routing_grid.npz'
def make_field():
 mask=np.zeros(dims,bool);mes=meshes('bodymesh.bin')
 for k in ids:
  pts,idx=proto(k).tessellate(.10,.18);mes[k]=(np.array([p.toTuple() for p in pts]),np.array(idx))
 for t in records:
  k=t['id'];p,idx=mes[k];world=p@matrix(t).T+t['pos'];voxel(mask,world,idx)
  if k in ['Jetson_Orin_Nano','MC02','Tattu_2200_6S']:
   lo=np.floor((world.min(0)-origin)/step).astype(int);hi=np.ceil((world.max(0)-origin)/step).astype(int)
   mask[tuple(slice(i,j+1) for i,j in zip(lo,hi))]=True
 st=distance_transform_edt(~mask,sampling=step).astype('f');groups=leg_clouds()
 for n,side,f in corner_order:
  M=leg_basis(side)@np.diag([side*f,1,1]);off=[side*HX,f*HY,0]
  for g,parts in groups.items():
   pp=np.concatenate([p for p,i in parts]);ii=np.concatenate([a+sum(len(p) for p,_ in parts[:i]) for i,(_,a) in enumerate(parts)])
   for q in ([-7] if g=='base' else range(-36,35,5)):
    x,y,a=leg.group_pose(g,q);voxel(mask,(pp@xyzrot(a).T+[x,y,0])@M.T+off,ii)
 np.savez_compressed(ws.cache,static=st,swept=distance_transform_edt(~mask,sampling=step).astype('f'))
if not ws.cache.exists():make_field()
import wire_route as wr
db=read(ROOT/'data/整车线束.json');wr.nodes=db['nodes']
for n in ['NetU','NetE']:db['nodes'][n]['p'][1]-=5.5
for r in db['routes']:
 if r['b']=='NetE' or r['a']=='NetU':
  seq=r['points'] if r['a']=='NetU' else list(reversed(r['points']));distance=0.;prev=seq[0].copy()
  for p in seq:
   distance+=math.dist(prev,p);prev=p.copy();p[1]-=5.5*max(0,1-distance/25)
reroute={'W21','W24','W25','W48','W57','W59'}
def reserve(seq,r):
 for p in wr.samples(seq,2.):
  v=np.rint((p-origin)/step).astype(int);sl=tuple(slice(i-4,i+5) for i in v);u=np.ogrid[-4:5,-4:5,-4:5];off=origin+v*step-p
  d=np.sqrt(sum((u[k]*step+off[k])**2 for k in range(3)))-r
  wr.occupied[sl]=np.minimum(wr.occupied[sl],d)
for r in db['routes']:
 if r['id'] not in reroute:
  for path in (r['frames'][::8] if 'frames'in r else [r['points']]):reserve(path,r['dia']/2)
for r in db['routes']:
 if r['id'] in reroute:
  wr.fixed(r);print('route',r['id'],r['fixed_mm'],flush=True)
for r in db['routes']:
 r['fixed_mm']=round(wr.length(np.array(r['points'])),1) if 'frames' not in r else r['fixed_mm']
 if r['id'] in reroute or r['a']=='NetU' or r['b']=='NetE':r['cut']=int(np.ceil((r['fixed_mm']*1.07+16)/10)*10)
write(ROOT/'data/R5_wiring.json',db)

