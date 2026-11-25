"""Fork final 150 mm route rollouts at a pre-defined supported stall, preserving the full approach."""
from pathlib import Path
import os,json,sys
import numpy as np
import mujoco as mj
from onnx import load
from onnx.reference import ReferenceEvaluator
from night_tasks import configuration,smooth
from stage_task import cases,decode
from stage_signals import intervals

ROOT=Path(__file__).resolve().parent.parent
ARCHIVE=ROOT.parent/'stage-climb-y1o529Z5'
MODES=('baseline','coast','fast','posture','posture_rear','rock')
def get_actor(label):
    net=ReferenceEvaluator(load(str(ARCHIVE/label/'actor_best.onnx')))
    return lambda o:net.run(None,{'obs':o})[0]

class ContactPull:
    """Support and wheel speed feedback sampled over the preceding control tick."""
    def __init__(self):
        self.angles=None
        self.ready=False
        self.started=None
        self.weak_time=0.
        self.pull_age=0.
        self.pull_ticks=0

    def apply(self,cmd,t,arm,history,edge,angles):
        normal=history[:,4:6]
        planted=(normal>1.) & (history[:,17:19]>edge+.01)
        supported=planted.all(1).mean()>=.70 and normal.mean(0).min()>=3.
        if self.angles is None:self.angles=angles.copy()
        if supported and not self.ready:
            self.ready=True
            self.pull_age=0.
            if self.started is None:self.started=float(t)
        self.weak_time=0. if supported else self.weak_time+.04
        if self.weak_time>=.20:self.ready=False
        # Positive hip rotation extends these front legs. Rate-limit planting to
        # avoid commanding an abrupt pitch change at the instant contact returns.
        load=normal.mean(0)
        rate=np.clip(3.*(12.-load),-26.,50.) if self.ready else np.full(2,50.)
        self.angles=np.clip(self.angles+.04*rate,-36.,22.)
        speed=.035
        if self.ready:
            self.pull_ticks+=1
            self.pull_age+=.04
            speed=.09+.43*smooth(self.pull_age/.20)
        out=cmd.copy()
        out[:2]=(self.angles+7.)/29.
        out[4:6]=(speed-.22)/.4
        if arm=='plant_rear' and self.ready:
            for j,delay in enumerate((.08,.22)):
                w=smooth((self.pull_age-delay)/.18)
                out[2+j]=(1-w)*cmd[2+j]-w
        return np.clip(out,-1.,1.)

def change(cmd,t,arm,controller,history,edge,angles):
    if arm in ('plant','plant_rear'):
        return controller.apply(cmd,t,arm,history,edge,angles)
    if arm in ('baseline','coast'):return cmd
    out=cmd.copy()
    u=float(smooth((t+.04)/.24))
    if arm=='fast':
        out[4:6]=(1-u)*cmd[4:6]+u # 0.62 m/s
        return out
    # Front plants and extends first. Then it rolls with a lower reference speed.
    # A second profile also retracts the rear legs in succession while the front pulls.
    front=20.;speed=.27
    if arm in ('rock','lift_pull'):
        # Front raises the chassis, then lowers the nose and slows the wheels briefly
        # to encourage forward load transfer before continuing to roll.
        shift=smooth((t-.28)/.20)*(1-smooth((t-.73)/.22))
        front-=54.*shift;speed-=.23*shift
        if arm=='lift_pull':
            # Match the height gain with a forward pull while both front tyres carry load.
            high=np.median(history[:,15:17].min(1))>=90.
            supported=((history[:,4:6]>1.)&(history[:,17:19]>edge+.01)).all(1).mean()>=.35
            if controller.started is None and high and supported:
                controller.started=float(t)
            if controller.started is not None:
                controller.pull_ticks+=1
                speed+=float(smooth((t-controller.started+.04)/.12))*(.54-speed)
    out[:2]=(1-u)*cmd[:2]+u*(front+7.)/29
    out[4:6]=(1-u)*cmd[4:6]+u*(speed-.22)/.4
    if arm in ('posture_rear','rock','lift_pull'):
        for j,on in enumerate((.24,.44)):
            ramp=smooth((t-on)/.16)
            out[2+j]=(1-ramp)*cmd[2+j]-ramp
    return np.clip(out,-1.,1.)
def stalled(k,tr,edge,switch):
    if os.environ.get('FORK_MODE')=='early':return switch is not None and k==switch
    if switch is None or k-switch<120 or k>1400:return False
    w=tr[k-60:k,0]
    rear=w[-1,19:21]-edge
    return rear.min()>-.14 and rear.max()<.01 and abs(w[-1,27]-w[0,27])<.010

class Metrics:
    def __init__(self,n):
        self.y=np.zeros((n,12));self.commands=np.zeros((n,8));self.poses={}
    def force(self,k,ct,world,j,top,riser,structure):
        if top and j is not None and j<2:self.y[k,:2]+=world[[0,2]]
        if riser and j is not None and j>=2:self.y[k,2:4]+=world[[0,2]]
        if structure:self.y[k,4:6]+=world[[0,2]]
    def tick(self,k,d,ix,ti,cmd):
        self.y[k,6:]=[np.rad2deg(np.arcsin(np.clip(d.xmat[ti,6],-1,1))),d.subtree_com[ti,0],d.subtree_com[ti,2],np.mean(d.qpos[ix[0][:2]])*180/np.pi,np.mean(d.ctrl[ix[4][:2]]),np.mean(d.qvel[ix[2][:2]])*.05]
        self.commands[k]=cmd
    def finish(self,fork,tr,edge,score,switch):
        out=dict(score=score,switch_s=None if switch is None else .002*switch,fork_s=None if fork is None else .002*fork)
        if fork is None:return out
        edge=float(edge);t=tr[:,0]
        w=slice(fork,fork+500);a=t[w];b=self.y[w]
        # Peak of the lower of the rear tyres, plus individual peaks for sequential lifting.
        # This metric includes any roll/yaw computed by the simulator.
        pre=t[fork-60:fork]
        peak=int(np.argmax(a[:,15:17].min(1)))
        out['rear_at_peak_x_mm']=(1000*(a[peak,19:21]-edge)).tolist()
        out['com_advance_at_peak_mm']=float(1000*(b[peak,7]-self.y[fork-1,7]))
        out['peak_at_s']=float(.002*peak)
        out.update(pre_both_loaded_fraction=float(((pre[:,4:6]>1.)&(pre[:,17:19]>edge+.01)).all(1).mean()),pre_front_mean_N=float(pre[:,4:6].sum(1).mean()),front_fx_N=float(b[:,0].mean()),front_fz_N=float(b[:,1].mean()),rear_wall_fx_N=float(b[:,2].mean()),rear_wall_fz_N=float(b[:,3].mean()),body_contact_fx_N=float(b[:,4].mean()),
                   peak_pitch_change_deg=float(np.max(abs(b[:,6]-self.y[fork-1,6]))),pitch_initial=float(self.y[fork-1,6]),pitch_range=b[:,6].ptp().item() if hasattr(np.ndarray,'ptp') and int(np.__version__.split('.')[0])<2 else float(np.ptp(b[:,6])),
                   initial_rear_dx_mm=((t[fork-1,19:21]-edge)*1000).tolist(),
                   com_max_advance_mm=float(1000*(b[:,7].max()-self.y[fork-1,7])),
                   com_net_advance_mm=float(1000*(b[-1,7]-self.y[fork-1,7])),
                   com_peak_rise_mm=float(1000*(b[:,8].max()-self.y[fork-1,8])),
                   rear_both_peak_mm=float(a[:,15:17].min(1).max()),rear_individual_peak_mm=a[:,15:17].max(0).tolist(),
                   initial_front_hip_deg=float(self.y[fork-1,9]),avg_front_hip_deg=float(b[:,9].mean()),avg_front_torque_Nm=float(b[:,10].mean()),
                   avg_front_speed_mps=float(b[:,11].mean()),avg_front_reference_mps=float((.22+.4*self.commands[w,4:6]).mean()),
                   front_both_support_fraction=float((a[:,4:6]>1).all(1).mean()),any_rear_top=bool(((t[fork:,6:8]>1)&(t[fork:,19:21]>edge+.01)).any()),
                   rear_progress_max_mm=float(1000*(a[:,19:21].min(1).max()-t[fork-1,19:21].min())))
        return out

def rollout():
    # Export exactly the already-validated full-route stepping implementation to a
    # process-local string, then add force measurements and the experimental branch.
    namespace={'__file__':str(ARCHIVE/'code'/'route.py'),'__name__':'frozen_route'}
    source=(ARCHIVE/'code'/'route.py').read_text()
    a="    exec(compile(script,'<flat-handover>','exec'),scope)"
    assert source.count(a)==1
    exec(source.replace(a,'    return script'),namespace)
    code=namespace['generate']()
    def sub(a,b):
        nonlocal code
        if code.count(a)!=1:raise ValueError(a)
        code=code.replace(a,b)
    sub('def replay(task,config,c,approach,stage,mode):','def replay(task,config,c,approach,stage,mode,arm):')
    sub('    for k in range(H*DEC):','    metrics=Metrics(H*DEC);ctrl=ContactPull();parts={};fork=None;edge=float(c["edge"][0])\n    for k in range(H*DEC):')
    sub('            ref=np.deg2rad','''            if fork is None and stalled(k,trace,edge,switch_tick):fork=k
            if fork is not None:cmd=change(cmd,(k-fork)*.002,arm,ctrl,trace[k-DEC:k,0],edge,np.rad2deg(d.qpos[ix[0][:2]]))
            ref=np.deg2rad''')
    sub('        mj.mj_step(m,d)','''        if arm=="coast" and fork is not None:d.ctrl[ix[4][:2]]=0.
        mj.mj_step(m,d)''')
    sub('            a[index]+=max(0.,force[0])','''            a[index]+=max(0.,force[0])
            if fork is not None:
                sgn=1. if int(ct.geom2)==part else -1.
                world=sgn*(ct.frame.reshape(3,3).T@force[:3])
                top=(geom==one and abs(ct.frame[2])>.85)
                metrics.force(k,ct,world,j,top,geom==one and not top,j is None)
                if j is None and geom==one and k-fork<500:
                    name=m.geom(part).name
                    parts[name]=parts.get(name,0.)+float(world[0])/500.''')
    sub('        a[30:]=d.qvel[1:3]','        a[30:]=d.qvel[1:3]\n        metrics.tick(k,d,ix,ti,cmd)')
    old='return dict(score={k:v[0].item() for k,v in score(task,trace,c).items()},ready_s=None if first_ready is None else first_ready*.002,switch_s=None if switch_tick is None else switch_tick*.002)'
    sub(old,'return dict(metrics.finish(fork,trace,edge,{k:v[0].item() for k,v in score(task,trace,c).items()},switch_tick),first_pull_s=ctrl.started,pull_control_ticks=ctrl.pull_ticks,step_structure_x_N=parts)')
    ns=dict(Metrics=Metrics,ContactPull=ContactPull,stalled=stalled,change=change,decode=decode)
    exec(compile(code,'<traction-test>','exec'),ns)
    return ns['replay']

def main(arm):
    replay=rollout();app=get_actor('original');act=get_actor('phase')
    archived=json.loads((ARCHIVE/'phase_route.json').read_text())
    out=[]
    for src in archived['rows']:
        j,dom=src['case'],src['domain']
        bank=cases('soft_up',12,archived['seed_base']+129*dom,0)
        c={k:v[j:j+1] for k,v in bank.items()}
        if arm!='baseline' and src['switch_s'] is None:
            out.append(dict(case=j,domain=dom,fork_s=None,switch_s=None,score=src['score']));continue
        x=replay('soft_up',configuration('soft_up',dom,True),c,app,act,'phase',arm)
        if arm=='baseline' and (x['switch_s']!=src['switch_s'] or not all(np.isclose(x['score'][k],v,atol=1e-6) for k,v in src['score'].items())):raise ValueError(('not reproduced',src,x))
        out.append(dict(case=j,domain=dom,**x))
    (ROOT/(os.environ.get('FORK_MODE','late')+'_'+arm+'.json')).write_text(json.dumps(out,allow_nan=False))
    print(arm,'eligible',sum(x['fork_s'] is not None for x in out),'reached',sum(x['score']['reached'] for x in out),flush=True)
if __name__=='__main__':main(sys.argv[1])
