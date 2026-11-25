"""Batched 500 Hz contact dynamics and task rewards. PPO commands at 25 Hz."""
import numpy as np
import warp as wp
import mujoco_warp as mw
from mujoco_warp._src import collision_convex
from ppo_highstep_env import state,servos
from train_actions import record,advance
from night_model import build,pose,SRC
from night_tasks import (casebank,observation,commands,pulse,horizon,score,drive_refs,TERRAIN,DESC,DOUBLE,DT,DEC)


@wp.kernel
def surface(n:wp.array(dtype=int),world:wp.array(dtype=int),pair:wp.array(dtype=wp.vec2i),
            frame:wp.array(dtype=wp.mat33),f:wp.array(dtype=wp.spatial_vector),ix:wp.array2d(dtype=int),
            floor:int,one:int,two:int,stair_up:int,sums:wp.array2d(dtype=float)):
    i=wp.tid()
    if i<n[0]:
        first=pair[i][0]
        other=pair[i][1]
        if other==floor or other==one or other==two:
            first=pair[i][1]
            other=pair[i][0]
        if first==floor or first==one or first==two:
            slot=int(12)
            for j in range(4):
                if other==ix[5,j]:
                    slot=j
                    if first!=floor:
                        slot=j+8
                        if wp.abs(frame[i][0,2])>.85:
                            slot=j+4
                            if stair_up==1 and first==one:slot=j
            wp.atomic_add(sums,world[i],slot,wp.max(f[i][0],0.))


class Sim:
    def __init__(self,task,n,config,blind_recovery=False):
        wp.config.quiet=True
        wp.config.kernel_cache_dir=str(SRC.parent/".warp_cache")
        collision_convex.MJ_MAX_EPAHORIZON=96
        wp.init();wp.set_device("cuda:0")
        self.task,self.n,self.config=task,n,config
        self.blind_recovery=blind_recovery
        self.H=horizon(task)
        m,d,ix,self.ti=build(task,config)
        self.mass=float(sum(m.body_mass))
        self.q0=d.qpos.copy()
        self.model=mw.put_model(m)
        self.g=g=mw.put_data(m,d,nworld=n,nconmax=64,njmax=384)
        self.ix=wp.array(ix)
        self.raw=wp.zeros((n,30))
        self.act=wp.zeros((n,8))
        self.scale=wp.ones(n)
        self.count=wp.zeros(1,dtype=int)
        self.block=wp.zeros((DEC,n,32))
        self.sums=wp.zeros((n,13))
        self.forces=wp.empty(g.naconmax,dtype=wp.spatial_vector)
        self.cids=wp.array(np.arange(g.naconmax,dtype=np.int32))
        self.applied=np.zeros((n,m.nv),np.float32)
        self.history=np.empty((self.H*DEC,n,32),np.float32)
        floor,one,two=[m.geom(name).id for name in ("ground","step","second_step")]
        def tick():
            wp.launch(servos,n,[self.ix,self.act,self.scale,g.qpos,g.qvel,g.ctrl])
            mw.step(self.model,g)
            self.sums.zero_()
            mw.contact_force(self.model,g,self.cids,False,self.forces)
            wp.launch(surface,g.naconmax,[g.nacon,g.contact.worldid,g.contact.geom,g.contact.frame,self.forces,
                      self.ix,floor,one,two,int(task=="double_up"),self.sums])
            wp.launch(record,n,[self.count,self.ix,self.ti,g.njmax,g.naconmax,g.nefc,g.nacon,self.sums,
                      g.qpos,g.qvel,g.geom_xpos,g.geom_xmat,g.xmat,g.subtree_com,g.site_xpos,g.ctrl,self.block])
            wp.launch(advance,1,[self.count])
        tick();wp.synchronize()
        with wp.ScopedCapture() as cap:tick()
        self.graph=cap.graph

    def observe(self):
        g=self.g
        wp.launch(state,self.n,[self.ix,self.ti,g.qpos,g.qvel,g.xmat,g.geom_xpos,self.raw])
        return observation(self.task,self.raw.numpy(),self.c,self.i,self.previous)

    def reset(self,seed):
        self.c=casebank(self.task,self.n,seed,self.config[3],self.blind_recovery)
        q,mc=pose(self.task,self.q0,self.c)
        self.g.qpos.assign(q)
        wp.copy(self.g.mocap_pos,wp.array(mc,dtype=wp.vec3))
        self.scale.assign(self.c["scale"].astype(np.float32))
        for a in (self.g.qvel,self.g.qacc_warmstart,self.g.qfrc_applied,self.g.ctrl,self.g.time):a.zero_()
        mw.forward(self.model,self.g)
        self.i=0
        self.previous=np.zeros((self.n,8),np.float32)
        self.xprev=q[:,0].copy()
        self.peakgap=np.zeros(self.n)
        self.peakhull=np.zeros(self.n)
        self.brake_x=np.zeros(self.n)
        self.obs=self.observe()
        return self.obs

    def step(self,neural):
        task,c=self.task,self.c
        issued=commands(task,self.obs,neural)
        self.act.assign(issued)
        if task in ("lift","recover"):
            self.applied[:,:2]=pulse(task,c,self.i)
            self.g.qfrc_applied.assign(self.applied)
        self.count.zero_()
        for _ in range(DEC):wp.capture_launch(self.graph)
        b=self.block.numpy()
        self.history[self.i*DEC:(self.i+1)*DEC]=b
        t=self.i*DT*DEC
        self.i+=1
        raw=b[-1]
        gap=b[:,:,26].max(0);hull=b[:,:,12].max(0)
        # An instantaneous violation is visible at its physical time, even if it has vanished by the end of the episode.
        if t<.20:gap=gap*0.;hull=hull*0.
        newgap=np.maximum(gap,self.peakgap)
        newhull=np.maximum(hull,self.peakhull)
        reward=-9.*(np.maximum(0.,newgap-.70)-np.maximum(0.,self.peakgap-.70))
        reward-=.10*(np.minimum(newhull,150.)-np.minimum(self.peakhull,150.))
        reward-=.04*np.minimum(4.,np.maximum(0.,gap-.70))
        reward-=.008*np.square(neural-self.previous).mean(1)
        self.peakgap,self.peakhull=newgap,newhull
        x=raw[:,27]
        if task in TERRAIN:
            edge=c["edge"]+(c["tread"] if task in DOUBLE else 0.)
            reward+=19*(np.minimum(x,edge+.35)-np.minimum(self.xprev,edge+.35))
            load=raw[:,:4] if task in DESC else raw[:,4:8]
            reward+=.023*((load>1.)&(raw[:,17:21]>edge[:,None])).sum(1)
            reward-=.06*abs(raw[:,28])+.02*np.clip(raw[:,21]-15.,0.,20.)
            if task in DESC:reward-=.055*np.maximum(0,2-((raw[:,:4]+raw[:,4:8])>1).sum(1))
            reward+=.12*(x>edge+.30)*np.clip(1-abs(raw[:,23])/.2,0,1)
            if task=="leap_step":
                airborne=(b[:,:,:13].sum(2)<.5)&(b[:,:,13:17].min(2)>0)
                near=abs(x-c["edge"])<.37
                reward+=near*.18*airborne.mean(0)
            if task=="wheel_over":
                dx=b[:,:,17:21]-c["edge"][None,:,None]
                near=np.exp(-np.square((dx+.015)/.045))
                lift=np.clip(b[:,:,13:17]/(1000*c["h"][None,:,None]+1.),0.,1.1)
                light=(b[:,:,:4]+b[:,:,4:8]+b[:,:,8:12])<1.
                reward+=.13*(near*lift*light).sum(2).mean(0)
        elif task=="lift":
            rows=np.arange(self.n);k=c["key"]
            if .9<t<2.2:
                h=raw[rows,13+k]
                support=np.min(np.stack([raw[rows,k^j] for j in (1,2,3)]),axis=0)
                reward+=.16*np.clip(h/25.,0.,1.1)+.22*np.clip(support/1.5,0,1)-.035*np.maximum(0,raw[:,21]-3.)
        elif task=="drive":
            v,yaw=drive_refs(t,c["key"])
            reward-=.9*abs(raw[:,23]-v)+.28*abs(raw[:,24]-yaw)
        elif task=="brake":
            if self.i==35:self.brake_x=x.copy()
            if t<1.32:reward+=.16*np.clip(c["key"]*raw[:,23]/.32,0,1.)
            if t>1.4:reward-=1.5*abs(x-self.brake_x)+.5*abs(raw[:,23])
        elif task=="recover":
            reward-=.7*np.linalg.norm(raw[:,[27,28]],axis=1)+.6*np.linalg.norm(raw[:,[23,30]],axis=1)+.022*raw[:,21]
        else:
            airborne=(b[:,:,:13].sum(2)<.5)&(b[:,:,13:17].min(2)>0)
            reward+=.42*airborne.mean(0)*np.clip(raw[:,23]/.4,0.,1.5)
            if t>1.4:reward-=.16*abs(raw[:,23])+.02*raw[:,21]
        self.xprev=x.copy();self.previous=neural.copy()
        self.obs=self.observe()
        if self.i==self.H:
            self.result=score(task,self.history,c)
            r=self.result
            reward+=12.*r["clean"]+2.5*r["reached"]+1.*r["stable"]
            if task=="forward_jump":reward+=.05*np.clip(r["air_travel_mm"],0,c["key"])
            if task=="leap_step":reward+=6.*r["single_flight"]
            if task=="wheel_over":reward+=2.*r["cleared_wheels"]
            reward=np.where(r["valid"],reward,-40.)
        return self.obs,np.clip(np.nan_to_num(reward,nan=-40),-60,60).astype(np.float32)
