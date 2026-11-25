"""Paired native R5 trials. All controls use the same flat approach and actuator limits."""
from pathlib import Path
import json,os,sys
import numpy as np
import mujoco as mj
import night_model
from night_model import pose,raw_native
from night_tasks import DEC,horizon,smooth,configuration,commands,observation,pulse,score
from stage_task import cases,decode
from pull_test import get_actor
from single_rear import Controller,branch,support_time

OUT=Path(__file__).parent
DT=.002
def ramp(x):
    return float(smooth(np.clip(x,0.,1.)))
class Push:
    def __init__(self,mode):
        self.mode=mode
        self.start=None
        self.hip=None
        self.tucked=False
        self.planted=False
        self.delay=.12
        self.duration=.16
        self.complete=.28+(.20 if mode=='tuck' else 0.)
    def update(self,k,switch,fork,tr,edge,angles,nominal):
        if switch is None:return nominal
        mode=self.mode
        close=mode.startswith('near_')
        name=mode.removeprefix('near_')
        if self.start is None and fork is None:
            prev=tr[k-20:k,0]
            trigger_distance={'lip':.155,'tworear':.185}.get(name,.225)
            near=(prev[-1,19:21].max()>=edge-trigger_distance and
                  ((prev[:,2:4]>1.).all(1)).mean()>=.6 and
                  ((prev[:,4:6]>1.).all(1)).mean()>=.4)
            if (close and near) or (not close and switch==k):
                self.start=k;self.hip=angles.copy()
        if self.start is None:return nominal
        t=DT*(k-self.start)
        if name=='tworear' and t>=.28-1e-9:
            # From pulse to landing, both rear legs lift together. There is no
            # handover to the alternating-leg routine on a triggered trial.
            h=tr[k-20:k,0];self.tucked=True
            if (h[-1,19:21]>edge+.012).all():self.planted=True
            if self.planted:
                v=np.clip(2.6*(.10-(h[-1,19:21]-edge).min()),0.,.34)
                return np.r_[np.zeros(4),np.full(4,(v-.22)/.4)]
            r=ramp((t-.28+.04)/.12)
            return np.r_[np.full(2,(-28.+7.)/29.),np.full(2,(22.-58.*r+7.)/29.),np.full(4,(.55-.22)/.4)]
        if t>=self.complete-1e-9 or name=='keep':return nominal
        out=nominal.copy()
        # The two front tyres pull throughout. Rear drives roll forward on the lower floor.
        vfront=.55
        vrear=.52
        if name=='braked' and t>=self.delay:vrear=.0
        u=ramp((t+.04)/.08)
        out[4:6]=(1-u)*nominal[4:6]+u*(vfront-.22)/.4
        out[6:]=(1-u)*nominal[6:]+u*(vrear-.22)/.4
        if name=='roll':return out
        rear0=self.hip[2:]
        crouch={'soft':-3.,'medium':-12.,'soft_hold':-3.}.get(name,-24.)
        if name=='direct':
            target=rear0+(22.-rear0)*ramp((t+.04)/.12)
        elif t<self.delay-1e-9:
            target=rear0+(crouch-rear0)*ramp((t+.04)/self.delay)
        else:
            end=crouch if name in ('hold','soft_hold') else 22.
            target=np.full(2,crouch+(end-crouch)*ramp((t-self.delay+.04)/.12))
            if name=='tuck' and t>=.28-1e-9:
                target[:]=22.-58.*ramp((t-.28+.04)/.12)
        out[2:4]=(target+7.)/29.
        return np.clip(out,-1.,1.)

def simulate(case,dom,approach,stage,mode,model_option='nominal'):
    task='soft_up';cfg=configuration(task,dom,True)
    m,d,ix,ti=night_model.build(task,cfg)
    if model_option=='stiff':
        for leg in ('FL','FR','RL','RR'):
            i=m.equality(leg+'_D').id
            m.eq_solref[i,0]=.004
    elif model_option=='no_rear_plate':
        for name in ('RL_P01','RR_P01'):
            i=m.geom(name).id
            m.geom_contype[i]=m.geom_conaffinity[i]=0
    q,mc=pose(task,d.qpos.copy(),case)
    d.qpos[:]=q[0];d.mocap_pos[:]=mc[0]
    mj.mj_forward(m,d)
    H=horizon(task);n=H*DEC
    tr=np.zeros((n,1,32));contacts=np.zeros((n,8));geom=np.zeros((n,6));joint=np.zeros((n,8));base=np.zeros((n,12))
    floor,one,two=[m.geom(s).id for s in ('ground','step','second_step')]
    surfaces=(floor,one,two);wheel={g:j for j,g in enumerate(ix[5])}
    plates={m.geom('RL_P01').id:0,m.geom('RR_P01').id:1}
    edge=float(case['edge'][0]);scale=case['scale'][0]
    prev=np.zeros((1,8),np.float32);force=np.zeros(6);split_count=0;switch=fork=None
    ctrl=Controller();kick=Push(mode)
    for k in range(n):
        if k%DEC==0:
            i=k//DEC
            if switch is None and split_count>=20:
                switch=k;prev.fill(0)
            if switch is None:
                o=observation(task,raw_native(d,ix,ti),case,i,prev)
                prev=approach(o);cmd=commands(task,o,prev)[0]
            else:
                phase_i=min((k-switch)//DEC+6,H-1)
                o=observation(task,raw_native(d,ix,ti),case,phase_i,prev)
                prev=stage(o);cmd=decode(task,o,prev,'phase')[0]
            if fork is None and branch(k,tr,edge,switch):fork=k
            if fork is not None:cmd=ctrl.command('settle',(k-fork)*DT,cmd,tr[k-DEC:k,0],edge,np.rad2deg(d.qpos[ix[0][:2]]))
            cmd=kick.update(k,switch,fork,tr,edge,np.rad2deg(d.qpos[ix[0]]),cmd)
            ref=np.deg2rad(-7+29*cmd[:4]);v=.22+.40*cmd[4:]
            d.qfrc_applied[:2]=pulse(task,case,i)[0]
        ang,dh,ws=d.qpos[ix[0]],d.qvel[ix[1]],d.qvel[ix[2]]
        hc=5.2*scale*np.clip((232-np.abs(dh)*9.5492966*24/22.2)/112,0,1)
        wc=scale*np.minimum(1.,3.73*np.clip(1-np.abs(ws)/12.77581,0,1))
        d.ctrl[ix[3]]=np.clip(54*(ref-ang)-.4*dh+1.15*np.cos(ang),-hc,hc)
        d.ctrl[ix[4]]=np.clip(.22*(v/.05-ws),-wc,wc)
        joint[k]=np.r_[np.rad2deg(ang),d.ctrl[ix[3]]*dh]
        mj.mj_step(m,d)
        a=tr[k,0]
        for ci,ct in enumerate(d.contact):
            surf,part=int(ct.geom1),int(ct.geom2)
            if part in surfaces:surf,part=part,surf
            if surf not in surfaces:continue
            mj.mj_contactForce(m,d,ci,force)
            j=wheel.get(part)
            top=surf!=floor and abs(ct.frame[2])>.85
            index=12 if j is None else j+(0 if surf==floor else 4 if top else 8)
            a[index]+=max(0.,force[0])
            sign=1 if part==int(ct.geom2) else -1
            xyz=sign*(ct.frame.reshape(3,3).T@force[:3])
            if j is not None and j>=2 and surf==floor:contacts[k,:2]+=xyz[[0,2]]
            if j is not None and j<2 and top and surf==one:contacts[k,2:4]+=xyz[[0,2]]
            if j is not None and j>=2 and surf==one and not top:contacts[k,4:6]+=xyz[[0,2]]
            if part in plates and surf==one:contacts[k,6+plates[part]]+=xyz[0]
        cz=np.clip(abs(d.geom_xmat[ix[5],8]),0,1)
        a[13:17]=1000*(d.geom_xpos[ix[5],2]-.0175*cz-.05*np.sqrt(1-cz*cz))
        a[17:21]=d.geom_xpos[ix[5],0]
        gaps=1000*np.linalg.norm(d.site_xpos[ix[6]]-d.site_xpos[ix[7]],axis=1)
        a[21:29]=[np.rad2deg(np.arccos(np.clip(d.xmat[ti,8],-1,1))),d.subtree_com[ti,2],
                  d.qvel[0],d.qvel[5],max(abs(d.ctrl[ix[3]])),gaps.max(),d.qpos[0],d.qpos[1]]
        a[30:]=d.qvel[1:3]
        geom[k]=np.r_[d.subtree_com[ti,[0,2]],gaps]
        base[k]=np.r_[d.xpos[ti],d.xmat[ti]]
        ok=all(a[4:6]>1.) and all(a[2:4]>1.) and all(a[17:19]>edge+.01) and all(a[19:21]<edge)
        split_count=split_count+1 if ok else 0
    if any(w.number for w in d.warning):tr[:,0,29]=1
    s={k:v[0].item() for k,v in score(task,tr,case).items()}
    out=dict(score=s,switch_s=None if switch is None else switch*DT,fork_s=None if fork is None else fork*DT,
             push_s=None if kick.start is None else kick.start*DT,edge=edge)
    a=tr[:,0];top=(a[:,6:8]>1.)&(a[:,19:21]>edge+.01)
    out['rear_supported']=[support_time(top[:,j]) for j in (0,1)]
    out['synchronous_tuck']=kick.tucked
    out['synchronous_landing_command']=kick.planted
    if kick.start is not None:
        start=kick.start
        t0=start+round(kick.delay/DT);end=start+round((kick.delay+kick.duration)/DT)
        sl=slice(t0,end);hit=(a[sl,2:4]>1.)
        def metrics(w):
            counts=a[w,2:4]>1.;j=joint[w]
            ft=contacts[w,:6].sum(0)*DT
            return dict(rear_floor_Jx=float(ft[0]),rear_floor_Jz=float(ft[1]),front_top_Jx=float(ft[2]),front_top_Jz=float(ft[3]),rear_wall_Jx=float(ft[4]),
                both_rear_loaded=float(counts.all(1).mean()),either_rear_loaded=float(counts.any(1).mean()),
                four_split_loaded=float((counts.all(1)&(a[w,4:6]>1.).all(1)).mean()),
                rear_floor_support_ms=float(1000*DT*counts.any(1).sum()),
                floor_loaded_positive_hip_work_J=float(np.sum(np.maximum(0.,j[:,6:])*counts)*DT))
        out['thrust']=dict(metrics(sl),hip_deg0=joint[t0,2:4].tolist(),hip_deg1=joint[end-1,2:4].tolist(),
            com_dx_mm=float(1000*(geom[end-1,0]-geom[t0-1,0])),com_dz_mm=float(1000*(geom[end-1,1]-geom[t0-1,1])))
        out['whole_pulse']=metrics(slice(start,end))
        out['initial_rear_hip_deg']=kick.hip[2:].tolist()
        out['edge_distance_mm']=float(1000*(edge-max(a[start-1,19:21])))
        out['before_push']=dict(gap_mm=float(a[100:start,26].max()),structure_N=float(a[100:start,12].max()))
        worst=start+np.argmin(contacts[start:,6:8].sum(1))
        gi=100+int(a[100:,26].argmax())
        out['plate']=dict(t_s=worst*DT,force_x=contacts[worst,6:8].tolist(),body=base[worst].tolist())
        out['closure_peak']=dict(t_s=gi*DT,leg=['FL','FR','RL','RR'][int(geom[gi,2:].argmax())],per_leg_mm=geom[gi,2:].tolist())
        out['before_single_any_rear_top']=bool(top[start:fork if fork is not None else n].any())
    return out

def run():
    mode,seed=sys.argv[1],int(sys.argv[2]);option=sys.argv[3] if len(sys.argv)>3 else 'nominal'
    night_model.SRC=Path(os.environ['PLATE_CODE'])
    ap=get_actor('original');st=get_actor('phase');rows=[]
    for dom in (0,1):
        batch=cases('soft_up',12,seed+129*dom,0.)
        for i in range(12):
            c={k:v[i:i+1] for k,v in batch.items()}
            rows.append(dict(domain=dom,case=i,**simulate(c,dom,ap,st,mode,option)))
    suffix='' if option=='nominal' else '_'+option
    (OUT/f"{mode}_{seed}{suffix}.json").write_text(json.dumps(rows,allow_nan=False))
    print(mode,seed,len(rows),sum(x['score']['reached'] for x in rows),flush=True)
if __name__=='__main__':run()
