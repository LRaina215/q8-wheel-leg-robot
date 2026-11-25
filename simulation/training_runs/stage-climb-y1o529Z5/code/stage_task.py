"""150 mm split-level start, shared by the GPU and native simulator."""
from functools import lru_cache
import os
import numpy as np
from night_model import build
from pilot import set_pose
from night_tasks import casebank as original_cases,mocaps,score as old_score,smooth
from night_env import Sim as Original
import night_env

HOLD=.24
HEIGHT=.150
def cases(task,n,seed,grade,blind=False):
    c=original_cases(task,n,seed,grade,blind)
    c['h_obs']+=HEIGHT-c['h']
    c['h'][:]=HEIGHT
    c['key'][:]=150
    c['depth']=np.random.default_rng(int(seed)+438015).uniform(.08,.18,n)
    return c

@lru_cache(maxsize=1)
def template():
    m,d,ix,trunk=build('soft_up',(.14,.64,(0.,0.,0.),0.))
    set_pose(m,d,[-36,-36,22,22])
    centres=d.geom_xpos[ix[5]]-d.xpos[trunk]
    dx,_,dz=centres[0]-centres[2]
    pitch=np.arcsin(HEIGHT/np.hypot(dx,dz))-np.arctan2(dz,dx)
    height=.05-centres[2,0]*np.sin(pitch)-centres[2,2]*np.cos(pitch)
    front_x=centres[0,0]*np.cos(pitch)-centres[0,2]*np.sin(pitch)
    return d.qpos.copy(),pitch,height,front_x

def pose(task,q0,c):
    neutral,pitch,z,fore=template()
    yaw=np.deg2rad(c['yaw']);cy,sy=np.cos(yaw/2),np.sin(yaw/2)
    cp,sp=np.cos(pitch/2),np.sin(pitch/2)
    q=np.repeat(neutral[None],len(yaw),axis=0)
    q[:,0]=c['edge']+c['depth']-fore*np.cos(yaw)
    q[:,1]=0.;q[:,2]=z
    q[:,3:7]=np.column_stack((cy*cp,sy*sp,-cy*sp,sy*cp))
    return q,mocaps(task,c)

def decode(task,o,u,mode=None):
    mode=mode or os.environ.get('STAGE_MODE','direct')
    t=o[:,23]*4.
    still=t<HOLD-.0001
    if mode=='direct':
        out=u.copy()
    else:
        # Approximate edge distance of each rear wheel using measured pitch, hip and yaw.
        pitch=np.arcsin(np.clip(o[:,2],-1,1))
        hips=o[:,12:14]/2-np.deg2rad(7.)
        xb=-.112-.11*np.cos(hips);zb=-.11-.11*np.sin(hips)
        yaw_s=o[:,4:5]
        rear=(xb*np.cos(pitch[:,None])-zb*np.sin(pitch[:,None]))*np.sqrt(np.maximum(0,1-yaw_s**2))-np.array([.205,-.205])*yaw_s-o[:,:1]/2
        abreast=smooth((rear+.11)/.085)
        over=smooth((rear-.015)/.095)
        both=np.min(over,axis=1)
        front=-36.+48.*smooth((t-HOLD)/.42)-19.*both
        rear_ref=22.-56.*abreast+27.*over
        drive=(.49*smooth((t-HOLD)/.20)*np.clip((o[:,0]/2+.39)/.11,0,1))[:,None]
        hip=np.column_stack((front,front,rear_ref))+12.*u[:,:4]
        v=drive+.13*u[:,4:]
        out=np.column_stack(((np.clip(hip,-36,22)+7.)/29.,(np.clip(v,-.18,.62)-.22)/.40))
    out[still]=[-1,-1,1,1,-.55,-.55,-.55,-.55]
    return out.astype(np.float32)

def score(task,tr,c):
    result=old_score(task,tr,c)
    check=tr[90:120]
    initial=((check[:,:,4:6]>1.).all(2)&(check[:,:,2:4]>1.).all(2)).all(0)
    initial &= (check[:,:,17:19]>(c['edge'][None,:,None]+.01)).all((0,2))
    initial &= (check[:,:,19:21]<c['edge'][None,:,None]).all((0,2))
    result['split_start']=initial
    result['clean'] &= initial
    result['reached'] &= initial
    return result

class Sim(Original):
    def __init__(self,*args,**kw):
        night_env.casebank=cases
        night_env.pose=pose
        night_env.commands=decode
        night_env.score=score
        super().__init__(*args,**kw)

    def reset(self,seed):
        self.bad_world=np.zeros(self.n,dtype=bool)
        return super().reset(seed)

    def step(self,neural):
        obs,reward=super().step(neural)
        if self.i<=6:return obs,reward
        block=self.history[(self.i-1)*20:self.i*20]
        dx=block[:,:,19:21]-self.c['edge'][None,:,None]
        near=np.exp(-((dx+.040)/.070)**2)
        terrain=block[:,:,2:4]+block[:,:,6:8]+block[:,:,10:12]
        z=np.clip(block[:,:,15:17]/150.,0,1)
        # Clearance earns credit approaching the edge; a two-wheel landing and parking
        # still require the unchanged original score.
        reward+=.45*np.mean(near*z,axis=(0,2))
        reward+=.18*np.mean(near*z*(terrain<2.),axis=(0,2))
        rear_top=(block[:,:,6:8]>1.)&(dx>.01)
        reward+=.18*rear_top.mean((0,2))
        self.bad_world |= ~np.isfinite(reward)
        if self.i==self.H:
            valid=self.result['valid'] & ~self.bad_world
            self.result['valid']=valid
            self.result['clean'] &= valid
            self.result['reached'] &= valid
            reward+=18.*self.result['reached']+24.*self.result['clean']
        reward=np.where(self.bad_world,-40.,reward)
        return obs,reward.astype(np.float32)
