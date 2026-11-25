"""Place known finished lead lengths and an explicitly assumed 1 m Astra lead in the model."""
from wire_space import *
from wire_check import dense
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from scipy.interpolate import CubicSpline
D=data;db=read(D/'整车线束.json');stat,sweep=fields()
def length(p):return np.linalg.norm(np.diff(p,axis=0),axis=1).sum()
def arclen(p):return np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()]
def store_points(r,p,target,label):
    arc=arclen(p);t=np.linspace(0,arc[-1],int(arc[-1]/2)+1)
    r['points']=np.column_stack([np.interp(t,arc,p[:,k]) for k in range(3)]).round(3).tolist()
    r['fixed_mm']=round(length(np.array(r['points'])),1);r['stock_target']=target;r['service']=label
    r['detail']=(r['detail']+'；' if r['detail'] else '')+label
    r['cut']=target;print(r['id'],r['fixed_mm'],label,flush=True)
for r in db['routes']:
    if r['id'] not in ['W28','W29','W30','W35']:continue
    p=dense(r['points']);a=arclen(p)
    if r['id']=='W29':
        # Incoming and outgoing leads both follow the tangents on the left side of the coil.
        u=int(np.argmin(np.linalg.norm(p-[33,72,60],axis=1)));v=int(np.argmin(np.linalg.norm(p-[25,15,63],axis=1)))
        best=None
        for cx in [53,58,60,63,51]:
            for cy in [48,39,44,53]:
                for z in [59,63,66,70,74]:
                    def candidate(radius):
                        angle=np.linspace(np.pi-.68,np.pi+.68+8*np.pi,650)
                        turns=np.column_stack([cx+radius*np.cos(angle),cy+radius*np.sin(angle),z+np.linspace(0,24,len(angle))]);return np.vstack([p[:u],turns,p[v:]])
                    radius=brentq(lambda rad:length(candidate(rad))-1000,20,34)
                    arr=candidate(radius);g=float(distances(sweep,dense(arr[u-2:-(len(p)-v-2)])).min())-r['dia']/2-2.6
                    if best is None or g>best[0]:best=(g,arr,cx,cy,z,radius)
        assert best[0]>1,best[0];r['coil_design']=list(best[2:]);store_points(r,best[1],1000,'示例按 1 m 原线，在右侧设备层盘四圈扎牢；实物长度决定圈数')
    else:
        target={'W28':250,'W30':200,'W35':200}[r['id']]
        # A broad service bow keeps the plug approaches undisturbed.
        best=None
        for u,v in [(.18,.78),(.25,.72),(.18,.66),(.27,.80)]:
            k=np.sin(np.pi*np.clip((a/a[-1]-u)/(v-u),0,1))**2
            for direction in [[0,0,1],[1,0,.6],[.3,0,1],[0,-1,.8],[.8,0,1],[-.45,0,1]]:
                d=np.array(direction);d=d/np.linalg.norm(d)
                def make(h):return p+k[:,None]*h*d
                amp=brentq(lambda h:length(make(h))-target,0,110)
                arr=make(amp);mask=k>.005;score=float(distances(sweep,arr[mask]).min()-r['dia']/2-2.6)-.012*amp
                if best is None or best[0]<score:best=(score,arr,amp)
        assert best[0]>0,(r['id'],best[0]);store_points(r,best[1],target,'成品线按所选长度在设备层留服务弯')
write(D/'整车线束.json',db)
