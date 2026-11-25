"""Batched closed-chain Q8 high-step environment. Policy period is 40 ms."""
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco as mj
import mujoco_warp as mw
from mujoco_warp._src import collision_convex
import numpy as np
import warp as wp

from pilot import LEGS, indices, set_pose
from train_actions import contacts

HERE = Path(__file__).resolve().parent
HEIGHTS = np.array([60,75,90,100,120,140,150], dtype=np.int32)
TICKS = 20
PERIOD = .040
HORIZON = 100
NOBS = 33


@wp.kernel
def servos(ix: wp.array2d(dtype=int), act: wp.array2d(dtype=float), scale: wp.array(dtype=float),
           q: wp.array2d(dtype=float), vel: wp.array2d(dtype=float), ctrl: wp.array2d(dtype=float)):
    w = wp.tid()
    for j in range(4):
        h = q[w,ix[0,j]]
        dh = vel[w,ix[1,j]]
        ws = vel[w,ix[2,j]]
        hc = scale[w]*5.2*wp.clamp((232.-wp.abs(dh)*9.5492966*24./22.2)/112.,0.,1.)
        wc = scale[w]*wp.min(1.,3.73*wp.clamp(1.-wp.abs(ws)/12.77581,0.,1.))
        ref = (-7.+29.*act[w,j])*.01745329252
        speed = .22+.40*act[w,4+j]
        ctrl[w,ix[3,j]] = wp.clamp(54.*(ref-h)-.4*dh+1.15*wp.cos(h),-hc,hc)
        ctrl[w,ix[4,j]] = wp.clamp(.22*(speed/.05-ws),-wc,wc)


@wp.kernel
def sample(ix: wp.array2d(dtype=int), trunk:int, nj:int, ncon:int,
           nf:wp.array(dtype=int), nc:wp.array(dtype=int), sums:wp.array2d(dtype=float),
           sites:wp.array2d(dtype=wp.vec3), gx:wp.array2d(dtype=wp.vec3),
           R:wp.array2d(dtype=wp.mat33), qd:wp.array2d(dtype=float),
           met:wp.array2d(dtype=float), edge:wp.array(dtype=float)):
    w=wp.tid()
    gap=float(0.)
    top=int(0)
    for j in range(4):
        gap=wp.max(gap,wp.length(sites[w,ix[6,j]]-sites[w,ix[7,j]])*1000.)
        if sums[w,j+4]>1.: top+=1
    tilt=wp.acos(wp.clamp(R[w,trunk][2,2],-1.,1.))*57.2957795
    speed=wp.length(wp.vec3(qd[w,0],qd[w,1],qd[w,2]))
    rear=wp.min(gx[w,ix[5,2]][0],gx[w,ix[5,3]][0])-edge[w]
    met[w,0]=wp.max(met[w,0],gap)
    met[w,1]=wp.max(met[w,1],sums[w,12])
    met[w,2]+=float(int(top==4))
    met[w,3]=wp.min(met[w,3],rear)
    met[w,4]=wp.max(met[w,4],tilt)
    met[w,5]=wp.min(met[w,5],tilt)
    met[w,6]=wp.max(met[w,6],speed)
    met[w,7]=wp.max(met[w,7],float(int(nf[w]>=nj or nc[0]>=ncon)))
    met[w,8]+=float(top)*.05


@wp.kernel
def state(ix:wp.array2d(dtype=int), trunk:int, q:wp.array2d(dtype=float), qd:wp.array2d(dtype=float),
          R:wp.array2d(dtype=wp.mat33), gx:wp.array2d(dtype=wp.vec3), out:wp.array2d(dtype=float)):
    w=wp.tid()
    out[w,0]=q[w,0]
    out[w,1]=q[w,1]
    out[w,2]=R[w,trunk][2,0]
    out[w,3]=R[w,trunk][2,1]
    out[w,4]=R[w,trunk][1,0]
    out[w,5]=qd[w,0]
    out[w,6]=qd[w,1]
    for j in range(3):
        out[w,7+j]=qd[w,3+j]*.25
    for j in range(4):
        out[w,10+j]=(q[w,ix[0,j]]+.12217305)*2.
        out[w,14+j]=qd[w,ix[1,j]]*.20
        out[w,18+j]=qd[w,ix[2,j]]*.08
        out[w,22+j]=gx[w,ix[5,j]][0]
        out[w,26+j]=gx[w,ix[5,j]][2]


class Env:
    def __init__(self,n,*,extra=.14,friction=.64):
        wp.config.quiet=True
        wp.config.kernel_cache_dir=str(HERE.parent/".warp_cache")
        collision_convex.MJ_MAX_EPAHORIZON=96
        wp.init()
        wp.set_device("cuda:0")
        self.n=n
        tree=ET.parse(HERE/"q8_r5_fitted.xml")
        tree.find(".//geom[@name='step']").set("size",".8 .46 .16")
        m=mj.MjModel.from_xml_string(ET.tostring(tree.getroot(),encoding="unicode"))
        m.opt.ccd_iterations=256
        m.geom_friction[:,0]=friction
        self.ti=m.body("chassis").id
        old=m.body_mass[self.ti]
        m.body_mass[self.ti]+=extra
        m.body_inertia[self.ti]*=m.body_mass[self.ti]/old
        self.mass=float(m.body_mass.sum())
        d=mj.MjData(m)
        mj.mj_setConst(m,d)
        mj.mj_resetData(m,d)
        set_pose(m,d,[-7]*4)
        d.qpos[2]=.160+.110*np.sin(np.deg2rad(-7))
        mj.mj_forward(m,d)
        self.model=mw.put_model(m)
        self.d=g=mw.put_data(m,d,nworld=n,nconmax=64,njmax=384)
        self.q0=g.qpos.numpy()
        self.moc0=g.mocap_pos.numpy()
        ih,iw=indices(m,"hip"),indices(m,"wheel")
        self.pose_cols={role:m.jnt_qposadr[indices(m,role)] for role in ("hip","carrier","follower")}
        self.ix=ix=wp.array(np.array([m.jnt_qposadr[ih],m.jnt_dofadr[ih],m.jnt_dofadr[iw],
            [m.actuator(l+"_hip").id for l in LEGS],[m.actuator(l+"_wheel").id for l in LEGS],
            [m.geom(l+"_tyre").id for l in LEGS],[m.site(l+"_pin").id for l in LEGS],
            [m.site(l+"_bore").id for l in LEGS]],dtype=np.int32))
        self.act=wp.zeros((n,8))
        self.scale=wp.full(n,.97)
        self.edge=wp.full(n,.38)
        self.raw=wp.zeros((n,30))
        self.met=wp.zeros((n,9))
        self.blank=np.zeros((n,9),np.float32)
        self.blank[:,[3,5]]=100.
        self.blank_dev=wp.array(self.blank)
        self.sums=wp.zeros((n,13))
        self.force=wp.empty(g.naconmax,dtype=wp.spatial_vector)
        self.cids=wp.array(np.arange(g.naconmax,dtype=np.int32))
        self.floor=m.geom("ground").id
        self.step_id=m.geom("step").id
        def tick():
            wp.launch(servos,n,[ix,self.act,self.scale,g.qpos,g.qvel,g.ctrl])
            mw.step(self.model,g)
            self.sums.zero_()
            mw.contact_force(self.model,g,self.cids,False,self.force)
            wp.launch(contacts,g.naconmax,[g.nacon,g.contact.worldid,g.contact.geom,g.contact.frame,
                self.force,ix,self.floor,self.step_id,self.sums])
            wp.launch(sample,n,[ix,self.ti,g.njmax,g.naconmax,g.nefc,g.nacon,self.sums,g.site_xpos,
                g.geom_xpos,g.xmat,g.qvel,self.met,self.edge])
        tick()
        wp.synchronize()
        with wp.ScopedCapture() as cap: tick()
        self.graph=cap.graph

    def observe(self):
        g=self.d
        wp.launch(state,self.n,[self.ix,self.ti,g.qpos,g.qvel,g.xmat,g.geom_xpos,self.raw])
        raw=self.raw.numpy()
        obs=np.empty((self.n,NOBS),np.float32)
        obs[:,:22]=raw[:,:22]
        obs[:,0]=(self.estimated_edge-raw[:,0])*2.
        obs[:,1]=raw[:,1]*3.
        obs[:,22]=self.estimated_height*10.
        obs[:,23]=self.i/HORIZON
        obs[:,24:32]=self.last_act
        obs[:,32]=np.maximum(0.,1.-np.abs(obs[:,0]-.40)*3.)
        return np.clip(np.nan_to_num(obs),-5.,5.),raw

    def reset(self,rng,start_mode="ground"):
        n=self.n
        self.i=0
        self.height_mm=np.resize(HEIGHTS,n).copy()
        rng.shuffle(self.height_mm)
        self.height=self.height_mm*.001
        self.true_edge=.38+rng.uniform(-.035,.035,n)
        self.estimated_edge=self.true_edge+rng.uniform(-.008,.008,n)
        self.estimated_height=self.height+rng.uniform(-.004,.004,n)
        moc=self.moc0.copy()
        moc[:,0,2]=self.height-.16
        moc[:,0,0]=self.true_edge+.8
        pose=self.q0.copy()
        yaw=np.deg2rad(rng.uniform(-3.,3.,n))/2
        pose[:,3]=np.cos(yaw)
        pose[:,6]=np.sin(yaw)
        if start_mode!="ground":
            # The split start places the front tyres on the step and both rear tyres on the floor.
            # Training also retains full approaches, and uses some four-on-top starts to teach braking.
            mode=rng.choice(3,size=n,p=[.45,.45,.10]) if start_mode=="mixed" else np.ones(n,int)
            ids=np.flatnonzero(mode==1)
            span=np.arcsin(np.minimum(np.sin(np.deg2rad(29)),self.height[ids]/(.220*np.cos(np.deg2rad(7)))))
            front=np.deg2rad(-7)-span
            rear=np.deg2rad(-7)+span
            angles=np.column_stack([front,front,rear,rear])
            for role,cols in self.pose_cols.items():
                pose[np.ix_(ids,cols)]=angles*(-1 if role=="carrier" else 1)
            dx=.224+.110*(np.cos(front)+np.cos(rear))
            dz=.110*(np.sin(rear)-np.sin(front))
            theta=np.arcsin(self.height[ids]/np.hypot(dx,dz))-np.arctan2(dz,dx)
            cy,sy=np.cos(yaw[ids]),np.sin(yaw[ids])
            cp,sp=np.cos(theta/2),np.sin(theta/2)
            pose[ids,3:7]=np.column_stack([cy*cp,sy*sp,-cy*sp,sy*cp])
            pose[ids,0]=self.true_edge[ids]+rng.uniform(-.085,.115,len(ids))
            pose[ids,2]=.05+(.112+.110*np.cos(rear))*np.sin(theta)+(.110+.110*np.sin(rear))*np.cos(theta)
            top=mode==2
            pose[top,0]=self.true_edge[top]+rng.uniform(.285,.35,int(top.sum()))
            pose[top,2]+=self.height[top]
        else:
            mode=np.zeros(n,int)
        g=self.d
        wp.copy(g.mocap_pos,wp.array(moc,dtype=wp.vec3))
        wp.copy(g.qpos,wp.array(pose,dtype=float))
        wp.copy(self.edge,wp.array(self.true_edge.astype(np.float32)))
        self.scale.assign(rng.uniform(.90,1.,n).astype(np.float32))
        for a in (g.qvel,g.ctrl,g.qacc_warmstart,g.time,g.qfrc_applied): a.zero_()
        mw.forward(self.model,g)
        self.last_act=np.zeros((n,8),np.float32)
        if start_mode!="ground":
            self.last_act[ids,:4]=(np.rad2deg(angles)+7.)/29.
            self.last_act[mode!=0,4:]=-.55
        self.max_gap=np.zeros(n)
        self.max_hull=np.zeros(n)
        self.invalid=np.zeros(n,bool)
        self.late=[]
        obs,raw=self.observe()
        self.old_phi=self.potential(raw)
        return obs

    def potential(self,raw):
        dx=raw[:,22:26]-self.true_edge[:,None]
        z=raw[:,26:30]-.05
        # Progress of both axles plus lifting the wheels while close to the riser.
        near=np.exp(-np.square((dx+.035)/.085))
        lift=np.clip(z/self.height[:,None],0,1)
        return (16*np.minimum(raw[:,0],self.true_edge+.355)
                +2.0*np.tanh(dx/.07).sum(axis=1)+1.2*(near*lift).sum(axis=1))

    def step(self,act):
        wp.copy(self.met,self.blank_dev)
        self.act.assign(np.ascontiguousarray(act,dtype=np.float32))
        for _ in range(TICKS): wp.capture_launch(self.graph)
        self.i+=1
        change=np.square(act-self.last_act).mean(axis=1)
        self.last_act=act.copy()
        obs,raw=self.observe()
        m=self.met.numpy()
        self.invalid|=(~np.isfinite(raw).all(axis=1))|(~np.isfinite(m).all(axis=1))|(m[:,7]>0)
        if self.i>5:
            self.max_gap=np.maximum(self.max_gap,m[:,0])
            self.max_hull=np.maximum(self.max_hull,m[:,1])
        phi=self.potential(raw)
        reward=(phi-self.old_phi + .018*m[:,8]-.015*change
                -.10*np.clip((m[:,0]-.8),0,5)-.12*np.clip(m[:,1]/10,0,4)
                -.025*np.maximum(0.,(m[:,4]-30.)/10.)-.02*np.abs(raw[:,1]))
        goal=raw[:,0]>=self.true_edge+.30
        reward+=goal*(.12*np.clip(1.-m[:,6]/.25,0,1))
        self.old_phi=phi
        if self.i>HORIZON-9: self.late.append(m.copy())
        if self.i==HORIZON:
            self.result=self.score()
            reward+=4*self.result["atop"]+10*self.result["clean"]
        return obs,np.where(self.invalid,-1.,np.nan_to_num(reward)).astype(np.float32)

    def score(self):
        a=np.stack(self.late)
        atop=(a[:,:,2].sum(axis=0)>.95*len(a)*TICKS)&(a[:,:,3].min(0)>=.05)&~self.invalid
        stable=(a[:,:,4].max(0)<=5.)&(a[:,:,4].max(0)-a[:,:,5].min(0)<1.)&(a[:,:,6].max(0)<.10)
        return dict(atop=atop,clean=atop&stable&(self.max_gap<.8)&(self.max_hull<2.),
                    invalid=self.invalid.copy(),terminal_front_x=(self.raw.numpy()[:,22:24].min(axis=1)-self.true_edge))
