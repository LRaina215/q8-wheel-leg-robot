"""Dress crossings outside the termination fan-outs, with the original swept assembly clearance preserved."""
from wire_space import *
from wire_check import dense
from scipy.spatial import cKDTree
D=data; db=read(D/'整车线束.json');rad=lambda r:r['dia']/2
static,sweep=fields();rng=np.random.default_rng(42)
records=[]; lookup={}
def arclen(p):return np.r_[0.,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()]
def score(p,r,peers):
    arc=arclen(p)
    vals=(arc>20)&(arc<arc[-1]-20)
    worst=99.;hit=None;total=0.
    for s,q,tree in peers:
        # Last 20 mm is a connector fan-out requiring actual plug shells.
        pp=p[vals]; pi=np.flatnonzero(vals)
        if not len(pp):continue
        di,ix=tree.query(pp)
        mask=(np.linalg.norm(pp-q[0],axis=1)>20)&(np.linalg.norm(pp-q[-1],axis=1)>20)&(np.linalg.norm(q[ix]-p[0],axis=1)>20)&(np.linalg.norm(q[ix]-p[-1],axis=1)>20)
        mask &= (np.linalg.norm(q[ix]-q[0],axis=1)>20)&(np.linalg.norm(q[ix]-q[-1],axis=1)>20)
        if not mask.any():continue
        v=np.where(mask,di-rad(r)-rad(s),100.);j=v.argmin()
        total+=np.square(np.maximum(0,.35-v)).sum()
        if v[j]<worst:worst=float(v[j]);hit=(int(pi[j]),q[ix[j]],s['id'])
    return total,worst,hit
fixed=[r for r in db['routes'] if 'frames' not in r];fixed.sort(key=lambda r:(r['optional'],0 if r.get('stock_target') else 1))
for r in fixed:
    raw=np.array(r['points']);p=dense(raw)[::2];p=np.vstack([p,raw[-1]]) if np.linalg.norm(p[-1]-raw[-1])>.01 else p
    lo=p.min(0)-18;hi=p.max(0)+18
    peers=[x for x in lookup.values() if (x[1].max(0)>lo).all() and (x[1].min(0)<hi).all()]
    initial,first,hit=score(p,r,peers);total=initial
    for it in range(45):
        if total<.005:break
        j,other,other_id=hit;direction=p[j]-other
        if np.linalg.norm(direction)<.1:direction=rng.normal(size=3)
        direction/=np.linalg.norm(direction);a=arclen(p)
        k=np.exp(-((a-a[j])/(11+it%3*4))**2)*np.minimum(1,np.minimum(a,a[-1]-a)/9)**2
        allowed=np.minimum(rad(r)+3.9,distances(sweep,p)-.01)
        best=None
        for vec in [direction,*np.eye(3),*(-np.eye(3)),*rng.normal(size=(5,3))]:
            vec=vec/np.linalg.norm(vec)
            for amp in [2.2,4.3,6.5]:
                candidate=p+k[:,None]*vec*amp
                if np.any(distances(sweep,candidate)<allowed-.02):continue
                v,w,h=score(candidate,r,peers)
                if v<total-.001 and (best is None or v<best[0]):best=(v,w,h,candidate)
                if v<.005:break
            if best and best[0]<.005:break
        if best is None:break
        total,worst,hit,p=best
    if initial:
        r['points']=p.round(3).tolist();r['fixed_mm']=round(arclen(p)[-1],1)
        r['cut']=int(np.ceil((r['fixed_mm']*1.07+16)/10)*10)
    q=dense(r['points']);lk=(r,q,cKDTree(q));lookup[r['id']]=lk
    _,end,h=score(q,r,peers)
    if initial or end<0:records.append(dict(wire=r['id'],initial=round(first,2),final=round(end,2),neighbour=h[2] if h else None))
    if initial:print(r['id'],round(first,2),round(end,2),flush=True)
write(D/'整车线束.json',db);write(D/'线间整理.json',dict(records=records,end_zone_mm=20,sampling_mm=1))
