"""Replay the R5 route and fork only the rear-climbing controller, at 25 Hz."""
import json,os,sys
from pathlib import Path
import numpy as np
import night_model
from pull_test import ARCHIVE,ContactPull,change,get_actor,stalled
from stage_task import cases,decode
from night_tasks import configuration,smooth

OUT=Path(__file__).resolve().parent
def branch(k,tr,edge,switch):
    if os.environ.get('FORK_MODE')!='approach':
        return stalled(k,tr,edge,switch)
    if switch is None or k-switch<40 or k>1400:return False
    w=tr[k-20:k,0]
    return (w[-1,19:21].max()>=edge-.105 and w[-1,19:21].max()<edge and
            (w[:,17:19]>edge+.01).all())
class Controller:
    def __init__(self):
        self.lead=None
        self.start=None
        self.second=None
        self.landing=None
        self.level=None
        self.load_spans=[]
        self.old=ContactPull()
    def command(self,arm,t,cmd,h,edge,front_angles):
        if self.lead is None:
            self.lead=int(np.argmax(h[-1,19:21]))
            if arm=='far':self.lead=1-self.lead
            self.start=cmd.copy()
        lead=self.lead
        other=1-lead
        if arm=='reference':
            return change(cmd,t,'lift_pull',self.old,h,edge,front_angles)
        settle=arm in ('settle','settle_slow')
        new=arm in ('press','anchor','steer_in','hold_speed') or settle
        on=(h[:,6+lead]>1.)&(h[:,19+lead]>edge+.010)
        self.load_spans.append((on.mean(),h[:,6+lead].mean(),(h[:,19+lead]>edge+.010).all()))
        established=on.all()
        if new and len(self.load_spans)>=2:
            recent=np.array(self.load_spans[-2:])
            established=established or (recent[:,0].mean()>=.75 and recent[:,1].mean()>=5. and recent[:,2].all())
        if self.second is None and established:
            self.second=t
        # Keep the unlifted rear hip extended until the first tyre holds on the tread.
        angle=np.full(4,22.)
        speed=np.full(4,.51)
        shift=float(smooth((t-.16)/.16))
        tilt=0. if arm=='straight' else (1. if arm in ('reverse_roll','inside_yaw') or new else -1.)
        angle[lead]=(1-shift)*18.+shift*np.clip(-18.+32.*tilt,-36.,22.)
        angle[other]=(1-shift)*18.+shift*np.clip(-18.-32.*tilt,-36.,22.)
        angle[2+lead]=22.-58.*smooth((t-.10)/.15)
        # Once the wheel is over the tread and unloaded, lower it to acquire purchase.
        if h[-1,19+lead]>edge+.012 and h[-1,15+lead]>145.:
            angle[2+lead]=-13.
        if arm in ('yaw','inside_yaw') or new:
            speed[[lead,2+lead]]=.62
            speed[[other,2+other]]=.20
        if new and self.landing is None:
            dx=h[-1,19+lead]-edge
            if dx>.002 and h[-1,15+lead]>143.:
                self.landing=t
        if new and self.landing is not None:
            land=float(smooth((t-self.landing+.04)/.16))
            angle[2+lead]=-36.+land*57.
            # Reduce differential drive and move the second corner forward while
            # the first rear tyre is planted rather than returning it to swing.
            if arm!='hold_speed':
                speed[[lead,2+lead]]=(1-land)*.62+land*(.14 if arm=='anchor' else .42)
                speed[[other,2+other]]=(1-land)*.20+land*.56
            if arm=='steer_in' or settle:
                angle[lead]-=30.*land
                angle[other]+=20.*land
        if self.second is not None:
            s=t-self.second
            angle[2+lead]=18. if new else 8.
            angle[2+other]=22.-58.*smooth(s/(.32 if new else .16))
            angle[:2]=[-22.,-22.]
            if new:
                angle[other]=17.
                speed[[other,2+other]]=.62
                speed[[lead,2+lead]]=.34
            if h[-1,19+other]>edge+.012:angle[2+other]=-8.
            if settle:
                if self.level is None and h[-1,19+other]>edge+(-.012 if arm=='settle_slow' else .012):
                    self.level=t
                    self.level_hip=angle.copy()
                if self.level is not None:
                    blend=smooth((t-self.level+.04)/.24)
                    angle=(1-blend)*self.level_hip-blend*7.
                    trailing=min(h[-1,19:21])-edge
                    speed[:]=np.clip(2.6*(.10-trailing),0.,.34)
        out=np.r_[(angle+7.)/29.,(speed-.22)/.40]
        u=smooth((t+.04)/.16)
        return np.clip((1-u)*self.start+u*out,-1.,1.)

def support_time(mask,num=20):
    run=0
    for i,hit in enumerate(mask):
        run=run+1 if hit else 0
        if run>=num:return round((i-num+1)*.002,3)
    return None

class Audit:
    def __init__(self,n):
        self.body=np.zeros((n,12))
        self.force=np.zeros((n,2))
        self.com=np.zeros(n)
    def reaction(self,k,name,x):
        if name in ('RL_P01','RR_P01'):
            self.force[k,int(name=='RR_P01')]+=x
    def result(self,fork,switch,ctrl,tr,edge,score):
        result=dict(fork_s=None if fork is None else fork*.002,switch_s=None if switch is None else switch*.002,score=score)
        if fork is None:return result
        a=tr[fork:,0];lead=ctrl.lead;other=1-lead
        top=(a[:,6:8]>1.)&(a[:,19:21]>edge+.01)
        dist=(a[:,19:21]-edge)*1000.
        hs=a[:,15+lead]
        p=int(hs.argmax())
        x=int(dist[:,lead].argmax())
        # The worst force and its triangles are taken at the same 2 ms physical tick.
        worst=int(np.argmin(self.force[fork:fork+500].sum(1)))
        states={}
        for name,idx in [('stall',0),('peak_plate',worst),('lead_high',p),('lead_forward',x)]:
            states[name]=dict(t=idx*.002,body=self.body[fork+idx].tolist(),plate_fx=self.force[fork+idx].tolist())
        until=len(a) if ctrl.second is None else max(1,round(ctrl.second/.002))
        ground=a[:until,2+other]>1.
        occupied=np.diff(np.r_[0,top[:,lead].astype(int),0])
        spans=np.where(occupied==-1)[0]-np.where(occupied==1)[0]
        w=40
        duty=np.convolve(top[:,lead],np.ones(w)/w,mode='valid')
        result.update(longest_lead_support_ms=int(2*spans.max()) if len(spans) else 0,
                      total_lead_support_ms=int(2*top[:,lead].sum()),best_80ms_duty=float(duty.max()),
                      landing_start_s=ctrl.landing,mate_max_x_mm=float(dist[:,other].max()),
                      front_tread_at_end=float((a[-175:,4:6]>1.).all(1).mean()))
        result.update(mate_any_contact=support_time(top[:,other],1),rear_together_s=support_time(top.all(1)),
            all_four_s=support_time(((a[:,4:8]>1.)&(a[:,17:21]>edge+.01)).all(1)),level_command_s=ctrl.level,
            rear_final_x_mm=dist[-1].tolist(),rear_final_z_mm=a[-1,15:17].tolist(),max_lateral_mm=float(1000*abs(tr[:,0,28]).max()),
            final_base_y_mm=float(1000*a[-1,28]),final_tilt_deg=float(a[-1,21]),final_350ms_wheel_support=(a[-175:,4:8]>1.).mean(0).tolist())
        result.update(lead=['RL','RR'][lead],second_command_s=ctrl.second,lead_load_s=support_time(top[:,lead]),mate_load_s=support_time(top[:,other]),
            first_any_load_s=support_time(top[:,lead],1),any_tyre_top_tick=bool(top.any()),lead_center_cross=bool((dist[:,lead]>=0.).any()),
            mate_lower_support_fraction=float(ground.mean()),max_lead_x_mm=float(dist[x,lead]),z_at_max_x_mm=float(hs[x]),
            max_lead_z_mm=float(hs[p]),x_at_max_z_mm=float(dist[p,lead]),min_front_normal_fraction=float((a[:until,4:6]>1.).all(1).mean()),
            net_com_1s_mm=float(1000*(self.com[fork+499]-self.com[fork-1])),peak_pitch_deg=float(a[:,21].max()),poses=states)
        return result

def engine():
    ns={'__file__':str(ARCHIVE/'code'/'route.py'),'__name__':'route_ref'}
    key="    exec(compile(script,'<flat-handover>','exec'),scope)"
    source=(ARCHIVE/'code'/'route.py').read_text()
    assert source.count(key)==1
    exec(source.replace(key,'    return script'),ns)
    src=ns['generate']()
    def replace(old,new):
        nonlocal src
        assert src.count(old)==1,old
        src=src.replace(old,new)
    replace('def replay(task,config,c,approach,stage,mode):','def replay(task,config,c,approach,stage,mode,arm):')
    replace('    for k in range(H*DEC):','    ctrl=Controller();audit=Audit(H*DEC);fork=None;edge=c["edge"][0]\n    for k in range(H*DEC):')
    replace('            ref=np.deg2rad','''            if fork is None and stalled(k,trace,edge,switch_tick):fork=k
            if fork is not None:cmd=ctrl.command(arm,(k-fork)*.002,cmd,trace[k-DEC:k,0],edge,np.rad2deg(d.qpos[ix[0][:2]]))
            ref=np.deg2rad''')
    replace('            a[index]+=max(0.,force[0])','''            a[index]+=max(0.,force[0])
            if fork is not None and geom==one and j is None:
                sign=1. if part==int(ct.geom2) else -1.
                audit.reaction(k,m.geom(part).name,sign*float(ct.frame.reshape(3,3)[:,0]@force[:3]))''')
    replace('        a[30:]=d.qvel[1:3]','''        a[30:]=d.qvel[1:3]
        audit.body[k]=np.r_[d.xpos[ti],d.xmat[ti]]
        audit.com[k]=d.subtree_com[ti,0]''')
    idx=src.rindex('    return dict(score=')
    src=src[:idx]+"    return audit.result(fork,switch_tick,ctrl,trace,edge,{k:v[0].item() for k,v in score(task,trace,c).items()})\n"
    env=dict(Controller=Controller,Audit=Audit,stalled=branch,decode=decode)
    exec(compile(src,'<single-rear>','exec'),env)
    return env['replay']
def run(arm):
    night_model.SRC=Path(os.environ['PLATE_CODE'])
    seed=int(os.environ.get('CASES_SEED',6031441))
    play=engine();ap=get_actor('original');act=get_actor('phase');rows=[]
    for dom in range(2):
        batch=cases('soft_up',12,seed+129*dom,0)
        for j in range(12):
            case={k:v[j:j+1] for k,v in batch.items()}
            x=play('soft_up',configuration('soft_up',dom,True),case,ap,act,'phase',arm)
            rows.append(dict(domain=dom,case=j,edge=float(case['edge'][0]),**x))
    file=OUT/(os.environ.get('FORK_MODE','late')+'_'+arm+'_'+str(seed)+'.json')
    file.write_text(json.dumps(rows,allow_nan=False))
    print(arm,len(rows),sum(r.get('first_any_load_s') is not None for r in rows),sum(r['score']['reached'] for r in rows),flush=True)
if __name__=='__main__':run(sys.argv[1])
