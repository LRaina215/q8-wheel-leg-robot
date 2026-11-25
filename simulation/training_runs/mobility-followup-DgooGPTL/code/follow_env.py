"""Whole-route PPO policies and identical native/GPU command decoding."""
import json,os
from pathlib import Path
import numpy as np
import night_env
from night_env import Sim as BaseSim
from night_tasks import commands as old_commands,casebank as old_cases,score as old_score,smooth,OPTIONS
from train_highstep_ppo import forward
from stage_task import decode as split_decode
from lift_profile import add_profile
from lift_mirror import mirror_actor

ROOT=Path(__file__).resolve().parent.parent
LANE=os.environ['FOLLOW_LANE']
TASK={'climb':'soft_up','handover':'soft_up','down':'down','double_down':'double_down','lift':'lift','forward_jump':'forward_jump'}[LANE]
HEIGHTS={'climb':[90,120,135,150],'handover':[120,135,150]}.get(LANE,OPTIONS[TASK])
FRESH=bool(int(os.environ.get('FOLLOW_EVAL','0')))
CONTROL=bool(int(os.environ.get('FOLLOW_CONTROL','0')))
SOURCE=ROOT/('original' if TASK=='soft_up' else 'frozen/'+TASK)
class Controller:
    def __init__(self):
        if LANE in ('handover','lift'):
            with np.load(SOURCE/'checkpoint_best.npz') as f:self.net=[f['actor%d'%i].copy() for i in range(6)]
        if LANE=='lift':
            right=json.loads((ROOT/'frozen'/'lift_profile.json').read_text())['parameters'][1]
            self.profile=np.array([right,right,[0.]*6,[0.]*6])
    def reset(self,n):
        self.old_u=np.zeros((n,8),np.float32)
        self.last_approach=self.old_u.copy()
        self.switched=np.zeros(n,bool);self.age=np.zeros(n,int)
    def contacts(self,b,edge):
        if LANE!='handover' or CONTROL:return
        split=((b[:,:,4:6]>1).all(2)&(b[:,:,2:4]>1).all(2)&
               (b[:,:,17:19]>edge[None,:,None]+.01).all(2)&(b[:,:,19:21]<edge[None,:,None]).all(2))
        self.age+=self.switched.astype(int)
        self.switched |= split.all(0)
    def frozen(self,x):return np.tanh(forward(self.net,x)[0])
    def __call__(self,task,o,u):
        if CONTROL and LANE!='lift':return old_commands(task,o,u)
        if LANE=='climb':return u
        if LANE=='lift':
            x=o.copy();x[:,24:32]=self.old_u
            self.old_u=mirror_actor(self.frozen,x)
            nominal=add_profile(x,old_commands(task,x,self.old_u),self.profile[np.rint(x[:,22]*3).astype(int)])
            if CONTROL:return nominal
            out=nominal.copy();out[:,:4]=np.clip(out[:,:4]+.36*u[:,:4],-1,1)
            out[:,4:]=np.clip(out[:,4:]+.27*u[:,4:],-2.05,1)
            return out.astype(np.float32)
        if LANE=='handover':
            x=o.copy();x[:,24:32]=self.old_u
            self.old_u=self.frozen(x)
            mask=self.switched
            prev=self.last_approach.copy()
            self.last_approach[~mask]=self.old_u[~mask]
            x[:,23]=(np.minimum(self.age+6,99)/100.)
            stage=split_decode(task,x,u,'phase')
            # Limit front-wheel overspeed after takeover using measured wheel and base speed.
            # No terrain contact signal is fed to the actor.
            speed=.22+.40*stage[:,4:6]
            spin=o[:,18:20]*.05/.08-o[:,5:6]
            blend=smooth((spin-.06)/.12)
            speed-=blend*np.maximum(0.,speed-(o[:,5:6]+.07))
            stage[:,4:6]=np.clip((speed-.22)/.40,-2.05,1.)
            ramp=smooth((self.age+.5)*.04/.32)[:,None]
            return np.where(mask[:,None],prev+ramp*(stage-prev),self.old_u).astype(np.float32)
        if LANE in ('down','double_down'):
            normal=old_commands(task,o,u)
            yaw=o[:,4:5];pitch=np.arcsin(np.clip(o[:,2:3],-1,1))
            ang=o[:,10:14]/2.-np.deg2rad(7)
            xb=(.112+.11*np.cos(ang))*np.array([1,1,-1,-1])
            zb=-.11-.11*np.sin(ang)
            dx=(xb*np.cos(pitch)-zb*np.sin(pitch))*np.sqrt(np.maximum(0,1-yaw*yaw))-yaw*np.array([.205,-.205,.205,-.205])-o[:,:1]/2
            if LANE=='double_down':
                next_dx=dx-o[:,32:33]/3
                dx=np.where(abs(next_dx)<abs(dx),next_dx,dx)
            near=np.exp(-((dx+.010)/.068)**2)
            v=.22+.40*normal[:,4:]
            v-=.14*near.max(1)[:,None]
            v=np.where(o[:,23:24]<.04,np.maximum(0,v),v)
            # Begin extending each individual leg before its centre crosses the lip.
            bias=(13.+np.array([4,-3,-3,4]))*smooth((dx+.065)/.07)*(1.-smooth((dx-.065)/.09))
            normal[:,:4]=np.clip(normal[:,:4]+bias/29.,-1,1)
            normal[:,4:]=np.clip((v-.22)/.40,-2.05,1);return normal
        # A crouch/push/tuck/soft-landing sequence, with forward speed commanded before take-off.
        t=o[:,23]*4.;dt=t-.9
        ref=-7.-15.*smooth((t-.20)/.45)
        ref=np.where(dt<0,ref,-22.+44.*smooth(dt/.085))
        ref+=(-21.-ref)*smooth((dt-.11)/.095)
        ref+=(-9.-ref)*smooth((dt-.31)/.22)
        hip=ref[:,None]+12.*u[:,:4]
        v=((.25+.00125*(o[:,22]*100.))*smooth((t-.08)/.5)*(1.-smooth((t-1.14)/.42)))[:,None]+.12*u[:,4:]
        return np.column_stack(((np.clip(hip,-36,22)+7)/29.,(np.clip(v,-.18,.62)-.22)/.4)).astype(np.float32)

def sample(task,n,seed,grade,blind,iteration):
    c=old_cases(task,n,seed,grade,blind)
    if TASK=='soft_up':
        heights=HEIGHTS
        if LANE=='climb' and not FRESH and seed!=812570:
            heights=([90,110,120,135] if iteration<100 else [110,120,135,140,150] if iteration<260 else [120,135,140,150,150])
        key=np.resize(heights,n)
        np.random.default_rng(seed+1703).shuffle(key)
        c['h_obs']+=key*.001-c['h'];c['h']=key*.001;c['key']=key
    return c

def scored(task,tr,c):
    r=old_score(task,tr,c)
    if task in ('down','double_down'):
        a=tr[100:];support=((a[:,:,:4]+a[:,:,4:8])>1).sum(2)
        r['under_two_ms']=2*(support<2).sum(0)
        r['zero_ms']=2*(support==0).sum(0)
    return r

class Sim(BaseSim):
    def __init__(self,*args,**kw):
        self.iteration=0
        self.controller=Controller()
        night_env.commands=self.controller
        night_env.casebank=lambda t,n,s,g,b:sample(t,n,s,g,b,self.iteration)
        night_env.score=scored
        super().__init__(*args,**kw)
    def reset(self,seed):
        self.controller.reset(self.n)
        self.bad=np.zeros(self.n,bool)
        return super().reset(seed)
    def step(self,u):
        obs,reward=super().step(u)
        b=self.history[(self.i-1)*20:self.i*20]
        self.controller.contacts(b,self.c['edge'])
        if self.i>5:
            normal=b[:,:,:4]+b[:,:,4:8]
            if TASK=='soft_up':
                dx=b[:,:,19:21]-self.c['edge'][None,:,None]
                near=np.exp(-((dx+.05)/.08)**2)
                z=np.clip(b[:,:,15:17]/self.c['key'][None,:,None],0,1)
                reward+=.48*(near*z).mean((0,2))+.30*((dx>.01)&(b[:,:,6:8]>1)).mean((0,2))
                reward-=.4*np.clip((b[:,:,26].max(0)-.65)/.8,0,3)
                reward-=.30*np.clip(b[:,:,12].max(0)/25,0,3)
            elif TASK in ('down','double_down'):
                second=np.sort(normal,axis=2)[:,:,-2]
                reward-=1.6*np.clip((2.-second)/2.,0,1).mean(0)+.65*(second.min(0)<1.)
                reward-=.35*(normal.max(2)<=1.).mean(0)
            elif TASK=='lift' and 27<=self.i<=54:
                k=self.c['key'];w=np.arange(self.n)
                z=np.clip(b[:,w,13+k]/23.,0,1)
                load=np.minimum.reduce([b[:,w,k^j] for j in (1,2,3)])
                together=np.minimum(z,np.clip(load/2.,0,1))
                reward+=.65*together.mean(0)+.8*together.min(0)
            elif TASK=='forward_jump':
                air=(b[:,:,:13].sum(2)<.5)&(b[:,:,13:17].min(2)>0.)
                reward+=1.25*(air*np.clip(b[:,:,23]/.42,0,1)).mean(0)
                if self.i>34:reward-=.18*np.clip((b[:,:,21].max(0)-4.)/8,0,2)
        self.bad |= ~np.isfinite(reward)
        if self.i==self.H:
            r=self.result;r['valid'] &= ~self.bad;r['clean'] &= r['valid'];r['reached'] &= r['valid']
            reward+=20*r['clean']+6*r['reached']
        return obs,np.where(self.bad,-40.,reward).astype(np.float32)
