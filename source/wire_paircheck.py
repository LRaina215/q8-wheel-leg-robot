"""Independent 1 mm centerline sampling for fixed/fixed and fixed/flex cable pairs."""
from wire_check import dense
from wire_space import data,read,write,np
from scipy.spatial import cKDTree
db=read(data/'整车线束.json');allr=db['routes']
def cloud(r,p):
    a=dense(p);keep=(np.linalg.norm(a-a[0],axis=1)>20)&(np.linalg.norm(a-a[-1],axis=1)>20)
    return (r,a[keep],a[[0,-1]],cKDTree(a[keep]),a.min(0),a.max(0))
def best(x,y):
    r,p,xend,_,lo,hi=x;s,q,yend,tree,yl,yh=y
    if not len(p) or not len(q) or np.any(lo-10>yh) or np.any(hi+10<yl):return 999
    d,i=tree.query(p);ok=np.ones(len(p),bool)
    for e in yend:ok &= np.linalg.norm(p-e,axis=1)>20
    for e in xend:ok &=np.linalg.norm(q[i]-e,axis=1)>20
    return float(d[ok].min()-(r['dia']+s['dia'])/2) if ok.any() else 999
fixed=[cloud(r,r['points']) for r in allr if 'frames' not in r];gap=(999,'','');findings=[];dynamic=(999,'','',0)
for k,x in enumerate(fixed):
    for y in fixed[:k]:
        d=best(x,y);gap=min(gap,(d,x[0]['id'],y[0]['id']))
        if d<0:findings.append((x[0]['id'],y[0]['id'],round(d,2)))
for r in allr:
    if 'frames' not in r:continue
    for i,p in enumerate(r['frames']):
        x=cloud(r,p)
        for y in fixed:
            d=best(x,y);dynamic=min(dynamic,(d,r['id'],y[0]['id'],i-36))
write(data/'线对线复核.json',dict(fixed_min=gap,fixed_overlap=findings,moving_fixed_min=dynamic,sampling_mm=1,terminal_fanout_mm=20))
print('wire clearance',gap,dynamic,findings,flush=True)
