from r5_static import proto,records,matrix
from clearance import rigid,bounds,meet
from common import *
from geometry import shape,qa_layers
import cadquery as cq
from itertools import product
def run():
 hist={};legsh={};bs=[]
 for t in records:
  s=rigid(proto(t['id']),matrix(t),t['pos']);bs.append((t,s,bounds(s)))
 boxes=np.array([b for _,_,b in bs]);cache=set()
 parts={k:shape(v) for k,v in leg.PARTS.items()}
 corners={}
 for k,s in parts.items():
  lo,hi=bounds(s);corners[k]=np.array(list(product(*zip(lo,hi))))
 swept={};tested=0
 for q in range(-36,23):
  for n,side,front in corner_order:
   basis=leg_basis(side)@np.diag([side*front,1,1]);root=np.array([side*HX,front*HY,0])
   for i,t in enumerate(leg.INST):
    k=t['id'];g=t['g'];x,y,a=leg.group_pose(g,q);R=xyzrot(a)
    P=basis@(np.array([x,y,0])+R@np.array([t['x'],t['y'],t['z']]))+root
    T=basis@R@xyzrot(t['rot'])@np.diag([1,-1 if t['flip'] else 1,-1 if t['flip'] else 1])
    corners_xyz=corners[k]@T.T+P;lo=corners_xyz.min(0);hi=corners_xyz.max(0)
    if n not in swept:swept[n]=[lo,hi]
    else:swept[n]=[np.minimum(swept[n][0],lo),np.maximum(swept[n][1],hi)]
    candidates=np.flatnonzero(np.all(np.minimum(boxes[:,1],hi)-np.maximum(boxes[:,0],lo)>.012,axis=1))
    for j in candidates:
     b,other,_=bs[j];sig=(n,i,int(j),None if g=='base' else q)
     if sig in cache:continue
     cache.add(sig);tested+=1;f=parts[k]
     if np.linalg.det(T)<0:
      if k not in legsh:legsh[k]=f.mirror('YZ')
      f=rigid(legsh[k],T@np.diag([-1,1,1]),P)
     else:f=rigid(f,T,P)
     v=abs(f.intersect(other).Volume())
     if v>.12:
      key=n+'/'+k+'/'+b['name']
      rec=hist.setdefault(key,{'from':q,'to':q,'peak_mm3':0});rec['to']=q;rec['peak_mm3']=round(max(rec['peak_mm3'],v),4)
  if q%15==0:print('checked',q,tested,len(hist),flush=True)
 bounds_gaps=[min(swept[b][0][0]-swept[a][1][0] for a,b in [('FL','FR'),('RL','RR')]),min(swept[a][0][1]-swept[b][1][1] for a,b in [('FL','RL'),('FR','RR')])]
 write(ROOT/'data'/'R5_sweep.json',dict(range=[-36,22],step=1,angles=59,body_pairs_exact=tested,hits=hist,independent_corner_bounds_gaps=bounds_gaps,leg_layers=qa_layers(-36,22,59)))
if __name__=='__main__':run()

