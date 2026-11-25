"""Rolling-direction contact speed relative to the fixed top, wheel effort, and rear contact events."""
import mujoco as mj
import numpy as np

def intervals(mask,minimum=1):
    delta=np.diff(np.r_[False,mask,False].astype(int))
    return [(int(a),int(b)) for a,b in zip(np.where(delta==1)[0],np.where(delta==-1)[0]) if b-a>=minimum]
def start_t(mask,minimum=10):
    e=intervals(mask,minimum)
    return None if not e else round(e[0][0]*.002,3)
class Signals:
    def __init__(self,m,n):
        self.slip=np.full((n,2),np.nan)
        self.ratio=np.zeros((n,4))
        self.eligible=np.zeros((n,4),bool)
        self.torque=np.zeros((n,4))
        self.jac=np.empty((3,m.nv))
        self.force=np.zeros(6)

    def sample(self,k,m,d,ix,a,limit,velocity,platform):
        self.torque[k]=d.ctrl[ix[4]]
        self.eligible[k]=limit>.03
        self.ratio[k]=np.abs(self.torque[k])/np.maximum(.03,limit)
        total=np.zeros(2);weighted=np.zeros(2)
        geomids=ix[5][:2]
        for j in range(2):
            if a[4+j]<=1.:continue
            wid=int(geomids[j])
            axis=d.geom_xmat[wid].reshape(3,3)[:,2]
            forward=np.array([axis[1],-axis[0],0.])
            forward/=max(1e-8,np.linalg.norm(forward))
            for ci,ct in enumerate(d.contact):
                if not ((ct.geom1==platform and ct.geom2==wid) or (ct.geom2==platform and ct.geom1==wid)):continue
                if abs(ct.frame[2])<=.85:continue
                mj.mj_contactForce(m,d,ci,self.force)
                weight=max(0.,self.force[0])
                if weight<=0:continue
                mj.mj_jac(m,d,self.jac,None,ct.pos,int(m.geom_bodyid[wid]))
                weighted[j]+=weight*abs(forward@(self.jac@velocity))
                total[j]+=weight
        good=total>1.
        self.slip[k,good]=weighted[good]/total[good]

    def results(self,tr,c):
        edge=float(c['edge'][0]);start=120
        top=(tr[:,6:8]>1)&(tr[:,19:21]>edge+.01)
        complete=intervals(top.all(1),20)
        end=complete[0][0] if complete else len(tr)
        active=(np.arange(len(tr))>=start)&(np.arange(len(tr))<end)
        loaded=np.isfinite(self.slip)&active[:,None]
        vals=self.slip[loaded]
        def distribution(v):return None if not len(v) else [float(np.median(v)),float(np.percentile(v,95))]
        def sat(sl,mask):
            eligible=self.eligible[:,sl]&mask
            return float((self.ratio[:,sl][eligible]>=.95).mean()) if eligible.any() else None
        releases=[]
        for j in range(2):
            floor=tr[:,2+j]
            total=floor+tr[:,6+j]+tr[:,10+j]
            releases.append(dict(floor_release_s=start_t((floor<=1.)&(np.arange(len(tr))>=start)),
                                 all_surfaces_release_s=start_t((total<=1.)&(np.arange(len(tr))>=start)),
                                 top_s=start_t(top[:,j]&(np.arange(len(tr))>=start),20)))
        return dict(window_s=[start*.002,end*.002],front_slip_mps_median_p95=distribution(vals),
                    loaded_front_wheel_samples=int(loaded.sum()),
                    front_slip_over_0p10_fraction=float((vals>.10).mean()) if len(vals) else None,
                    front_saturation_fraction=sat(slice(0,2),loaded),
                    rear_saturation_fraction=sat(slice(2,4),active[:,None]),
                    front_abs_torque_peak_Nm=float(np.abs(self.torque[:,0:2][loaded]).max()) if loaded.any() else None,
                    rear_floor_to_top=releases,both_rear_top_s=start_t(top.all(1),20),
                    max_rear_tire_bottom_mm=tr[start:,15:17].max(0).tolist(),
                    max_front_top_N=tr[start:,4:6].max(0).tolist(),
                    max_rear_riser_N=tr[start:,10:12].max(0).tolist())
