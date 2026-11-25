from common import *
from wire_check import dense
from scipy.spatial import cKDTree
db=read(ROOT/'data/R5_wiring.json');w=next(r for r in db['routes'] if r['id']=='W25')
p=np.array(w['points']);x=np.array([38.65,53.33,-18.02]);d=np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()];j=np.argmin(np.linalg.norm(p-x,axis=1));near=[]
for r in db['routes']:
 if r==w:continue
 seq=dense(r['points']);ends=seq[[0,-1]]
 ok=(np.linalg.norm(seq-ends[0],axis=1)>20)&(np.linalg.norm(seq-ends[1],axis=1)>20)&(np.linalg.norm(seq-p[0],axis=1)>20)&(np.linalg.norm(seq-p[-1],axis=1)>20)
 if ok.any() and np.linalg.norm(seq[ok]-x,axis=1).min()<38:near.append((cKDTree(seq[ok]),ends,(r['dia']+w['dia'])/2))
best=None
for width in [18,24,32]:
 wt=np.maximum(0,1-((d-d[j])/width)**2)**2;idx=np.flatnonzero(wt)
 for rad in [1.,2.,3.,4.,5.,6.]:
  for a in np.linspace(-1,1,11):
   b=math.sqrt(max(0.,1-a*a))
   for theta in np.linspace(0,2*math.pi,16,endpoint=False):
    off=rad*np.array([b*math.cos(theta),b*math.sin(theta),a]);new=p+wt[:,None]*off
    points=dense(new[max(0,idx[0]-1):idx[-1]+2]);points=points[(np.linalg.norm(points-p[0],axis=1)>20)&(np.linalg.norm(points-p[-1],axis=1)>20)]
    gap=12
    for tr,ends,r in near:
     q=points[(np.linalg.norm(points-ends[0],axis=1)>20)&(np.linalg.norm(points-ends[1],axis=1)>20)]
     if len(q):gap=min(gap,tr.query(q)[0].min()-r)
     if gap<.3:break
    if gap>.3:
     score=min(gap,1.4)-.035*rad-.002*width
     if best is None or score>best[0]:best=(score,new,gap,off,width)
assert best is not None
_,new,gap,off,width=best;print('W25',gap,off,width,flush=True);w['points']=new.round(2).tolist();w['fixed_mm']=round(np.linalg.norm(np.diff(new,axis=0),axis=1).sum(),1);w['cut']=int(np.ceil((w['fixed_mm']*1.07+16)/10)*10);write(ROOT/'data/R5_wiring.json',db)

