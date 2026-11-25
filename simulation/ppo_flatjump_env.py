"""500 Hz closed-chain GPU contact simulation for the Q8 jump policy."""
import numpy as np
import warp as wp
import mujoco_warp as mw

from ppo_highstep_env import Env,state
from train_actions import contacts,advance
from flatjump_policy_io import DT,DECIMATION,HORIZON,GOALS,reference_deg,observations,metrics


@wp.kernel
def jump_motor(ix:wp.array2d(dtype=int),act:wp.array2d(dtype=float),scale:wp.array(dtype=float),
               tick:wp.array(dtype=int),table:wp.array(dtype=float),q:wp.array2d(dtype=float),
               vel:wp.array2d(dtype=float),ctrl:wp.array2d(dtype=float)):
    w=wp.tid()
    base=table[tick[0]]
    for j in range(4):
        pos=q[w,ix[0,j]]
        dh=vel[w,ix[1,j]]
        ws=vel[w,ix[2,j]]
        hc=scale[w]*5.2*wp.clamp((232.-wp.abs(dh)*9.5492966*24./22.2)/112.,0.,1.)
        wc=scale[w]*wp.min(1.,3.73*wp.clamp(1.-wp.abs(ws)/12.77581,0.,1.))
        ref=wp.clamp(base+16.*act[w,j],-36.,22.)*.01745329252
        ctrl[w,ix[3,j]]=wp.clamp(54.*(ref-pos)-.4*dh+1.15*wp.cos(pos),-hc,hc)
        ctrl[w,ix[4,j]]=wp.clamp(.22*(.18*act[w,j+4]/.05-ws),-wc,wc)


@wp.kernel
def detail(ix:wp.array2d(dtype=int),trunk:int,nj:int,nc:int,ne:wp.array(dtype=int),na:wp.array(dtype=int),
           sums:wp.array2d(dtype=float),gx:wp.array2d(dtype=wp.vec3),gr:wp.array2d(dtype=wp.mat33),
           R:wp.array2d(dtype=wp.mat33),com:wp.array2d(dtype=wp.vec3),sites:wp.array2d(dtype=wp.vec3),
           q:wp.array2d(dtype=float),qd:wp.array2d(dtype=float),clock:wp.array(dtype=int),out:wp.array3d(dtype=float)):
    w=wp.tid()
    k=clock[0]%10
    lowest=float(1000.)
    err=float(0.)
    grounded=int(1)
    force=sums[w,12]
    for j in range(4):
        g=ix[5,j]
        axis=wp.clamp(wp.abs(gr[w,g][2,2]),0.,1.)
        bottom=gx[w,g][2]-.0175*axis-.05*wp.sqrt(wp.max(0.,1.-axis*axis))
        lowest=wp.min(lowest,1000.*bottom)
        err=wp.max(err,1000.*wp.length(sites[w,ix[6,j]]-sites[w,ix[7,j]]))
        force+=sums[w,j]+sums[w,j+4]+sums[w,j+8]
        if sums[w,j]<=1.: grounded=0
    out[k,w,0]=force
    out[k,w,1]=lowest
    out[k,w,2]=com[w,trunk][2]*1000.
    out[k,w,3]=wp.acos(wp.clamp(R[w,trunk][2,2],-1.,1.))*57.2957795
    out[k,w,4]=wp.length(wp.vec3(qd[w,0],qd[w,1],qd[w,2]))
    out[k,w,5]=sums[w,12]
    out[k,w,6]=err
    out[k,w,7]=float(grounded)
    out[k,w,8]=float(int(ne[w]>=nj or na[0]>=nc))
    out[k,w,9]=wp.sqrt(q[w,0]*q[w,0]+q[w,1]*q[w,1])


class JumpEnv(Env):
    def __init__(self,n,extra,friction):
        super().__init__(n,extra=extra,friction=friction)
        self.time_index=wp.zeros(1,dtype=int)
        self.ref_table=wp.array(reference_deg(np.arange(HORIZON*DECIMATION)*DT).astype(np.float32))
        self.block=wp.zeros((DECIMATION,n,10))
        self.history=np.empty((HORIZON*DECIMATION,n,10),np.float32)
        g=self.d
        def tick():
            wp.launch(jump_motor,n,[self.ix,self.act,self.scale,self.time_index,self.ref_table,g.qpos,g.qvel,g.ctrl])
            mw.step(self.model,g)
            self.sums.zero_()
            mw.contact_force(self.model,g,self.cids,False,self.force)
            wp.launch(contacts,g.naconmax,[g.nacon,g.contact.worldid,g.contact.geom,g.contact.frame,
                      self.force,self.ix,self.floor,self.step_id,self.sums])
            wp.launch(detail,n,[self.ix,self.ti,g.njmax,g.naconmax,g.nefc,g.nacon,self.sums,g.geom_xpos,
                g.geom_xmat,g.xmat,g.subtree_com,g.site_xpos,g.qpos,g.qvel,self.time_index,self.block])
            wp.launch(advance,1,[self.time_index])
        tick()
        wp.synchronize()
        with wp.ScopedCapture() as graph: tick()
        self.graph=graph.graph

    def observation(self):
        g=self.d
        wp.launch(state,self.n,[self.ix,self.ti,g.qpos,g.qvel,g.xmat,g.geom_xpos,self.raw])
        return observations(self.raw.numpy(),g.qvel.numpy()[:,2],self.goals,self.i,self.last_act)

    def reset_jump(self,rng):
        self.i=0
        g=self.d
        self.goals=np.resize(GOALS,self.n).copy()
        rng.shuffle(self.goals)
        initial=self.q0.copy()
        yaw=np.deg2rad(rng.uniform(-3.,3.,self.n))/2
        initial[:,3]=np.cos(yaw)
        initial[:,6]=np.sin(yaw)
        g.qpos.assign(initial)
        moc=self.moc0.copy()
        moc[:,0,0]=5.
        moc[:,0,2]=-.3
        wp.copy(g.mocap_pos,wp.array(moc,dtype=wp.vec3))
        self.scale.assign(rng.uniform(.89,1.,self.n).astype(np.float32))
        for a in (g.qvel,g.ctrl,g.time,g.qacc_warmstart,g.qfrc_applied,self.time_index): a.zero_()
        mw.forward(self.model,g)
        self.last_act=np.zeros((self.n,8),np.float32)
        return self.observation()

    def step_jump(self,act):
        self.act.assign(np.ascontiguousarray(act,dtype=np.float32))
        for _ in range(DECIMATION): wp.capture_launch(self.graph)
        block=self.block.numpy()
        self.history[self.i*DECIMATION:(self.i+1)*DECIMATION]=block
        self.i+=1
        airborne=(block[:,:,0]<.5)&(block[:,:,1]>0)
        reward=-.025*np.square(act-self.last_act).mean(axis=1)-.003*np.square(act).mean(axis=1)
        reward-=.12*np.clip(block[:,:,6].max(0)-.8,0.,8.)+.03*np.minimum(block[:,:,5].max(0),10.)
        reward-=.012*np.maximum(0.,block[:,:,3].max(0)-5.)+.1*block[:,:,9].mean(0)
        if .65<=self.i*.02<=1.06:
            reward+=.07*np.mean(airborne,axis=0)+.002*np.minimum(40.,np.maximum(0.,block[:,:,1]).max(0))
        elif self.i*.02>1.25:
            reward+=.03*block[:,:,7].mean(0)-.05*block[:,:,4].mean(0)
        self.last_act=act.copy()
        if self.i==HORIZON:
            s=self.result=metrics(self.history,self.goals)
            accuracy=np.exp(-np.abs(s["com_rise_mm"]-self.goals)/8.)
            reward+=np.where(s["flight_ms"]>=20.,3.+12*accuracy+np.minimum(s["tire_mm"],20.)*.07,-3.)
            reward+=3.*s["stable"]+8.*s["clean"]-.08*np.minimum(s["rebound_ms"],100.)
            reward-=.012*np.maximum(0.,s["contact_peak_N"]-180.)
            reward=np.where(s["valid"],reward,-20.)
        return self.observation(),np.nan_to_num(reward,nan=-10.,posinf=-10.,neginf=-10.).astype(np.float32)
