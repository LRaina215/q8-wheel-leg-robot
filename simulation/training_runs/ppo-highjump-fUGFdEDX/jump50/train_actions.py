"""Batched derivative-free training of five closed-loop control policies on the Q8."""
import argparse
import json
import math
import os
import time
from pathlib import Path
from importlib.metadata import version

import mujoco as mj
import mujoco_warp as mw
import numpy as np
import warp as wp

from pilot import HERE,LEGS,indices,set_pose

DT=.002
STEPS=2000
EDGE=.38
TASKS=("drive_turn","lift_FL","low_jump","roll_step","jump_step","two_stage_step")
# Columns are per-task, radians/degree conversions are in the controller.
LIMITS=np.array([
 [[14,64],[.25,1.8],[.10,.65],[0,.20],[0,.4],[.02,.15]],
 [[-12,12],[.60,1.0],[18,27],[-7,7],[-4,4],[-4,4]],
 [[-35,-20],[12,22],[.045,.18],[-35,-12],[.01,.10],[.08,.23]],
 [[.23,.52],[10,28],[.035,.145],[.045,.16],[-.055,.055],[-8,6]],
 [[.25,.53],[.025,.17],[-35,-18],[12,22],[.045,.17],[-35,-10]],
 [[.23,.52],[.025,.14],[-35,-18],[12,22],[.045,.17],[-35,-10]]],float)
SEED=np.array([[54,.4,.22,.05,.15,.05],[0,.8,20,0,0,0],
              [-30,20,.10,-27,.045,.13],[.34,18,.09,.09,.015,0],
              [.41,.09,-30,20,.095,-26],[.34,.07,-27,20,.09,-25]],float)
def save(path,document):
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(document,indent=2,allow_nan=False),encoding="utf8")
    os.replace(tmp,path)

@wp.func
def smooth(x:float):
    u=wp.clamp(x,0.,1.)
    return u*u*(3.-2.*u)

@wp.func
def squat_push(dt:float,depth:float,peak:float,push:float,tuck:float,delay:float,recover:float):
    rise=smooth(dt/push)
    pull=smooth((dt-push-delay)/.075)
    land=smooth((dt-push-delay-.075-recover)/.28)
    v=depth+(peak-depth)*rise
    v=v+(tuck-v)*pull
    return v+(-7.-v)*land

@wp.kernel
def control(count:wp.array(dtype=int),tags:wp.array(dtype=int),p:wp.array2d(dtype=float),
            ix:wp.array2d(dtype=int),trunk:int,trigger:wp.array(dtype=float),rear_trigger:wp.array(dtype=float),wheel_trigger:wp.array2d(dtype=float),
            q:wp.array2d(dtype=float),qd:wp.array2d(dtype=float),gx:wp.array2d(dtype=wp.vec3),
            R:wp.array2d(dtype=wp.mat33),ctrl:wp.array2d(dtype=float),torque_scale:float,grade_sin:float):
    w=wp.tid();t=float(count[0])*.002;task=tags[w]
    a=p[w,0];b=p[w,1];c=p[w,2];e=p[w,3];f=p[w,4];g=p[w,5]
    front=.5*(gx[w,ix[5,0]][0]+gx[w,ix[5,1]][0]);x=q[w,0]
    rear=.5*(gx[w,ix[5,2]][0]+gx[w,ix[5,3]][0])
    if (task==13 or task==14) and count[0]==750:trigger[w]=x
    if (task==4 or task==5 or task==10) and t>=.55 and front>=.38-b and trigger[w]<0.:
        trigger[w]=t
    rlead=b
    if task==10:rlead=c
    if (task==5 or task==10) and rear>=.38-rlead and trigger[w]>=0. and rear_trigger[w]<0.:
        rear_trigger[w]=t
    for j in range(4):
        ref=float(-7.);v=float(0.);kp=float(54.);kd=float(.4);wheel_k=float(.22)
        if task==0:
            kp=a;kd=b;wheel_k=c
            speed=.22*smooth((t-.4)/.45)*(1.-smooth((t-1.35)/.45))-.12*smooth((t-2.)/.4)*(1.-smooth((t-3.)/.4))
            yaw=.35*smooth((t-.65)/.3)*(1.-smooth((t-1.4)/.3))
            s=float(-1.)
            if j==1 or j==3:s=1.
            v=speed+e*(speed-qd[w,0])+s*(.205*yaw+f*(yaw-qd[w,5]))
            ref+=g*57.2957795*R[w,trunk][2,0]
        elif task==1 or (task>=6 and task<=8):
            corner=int(0)
            if task>=6:corner=task-5
            relative=j^corner
            forward=float(1.);left=float(1.)
            if corner>=2:forward=-1.
            if corner==1 or corner==3:left=-1.
            pre=smooth(wp.min((t-.2)/.4,(3.8-t)/.4))
            lift=smooth(wp.min((t-.6)/b,(3.4-t)/b))
            if relative==0:ref-=c*lift
            elif relative==3:ref+=a*pre+57.2957795*f*pre*(forward*R[w,trunk][2,0]+left*R[w,trunk][2,1])*.70710678
            elif relative==1:ref+=(e+g)*pre
            else:ref+=(e-g)*pre
        elif task==2:
            ref=-7.+(a+7.)*smooth((t-.30)/.60)
            if t>=1.10:ref=squat_push(t-1.10,a,b,c,e,f,g)
        elif task==3:
            v=a*smooth((t-.20)/.36)*wp.clamp((.735-x)/.07,0.,1.)
            side=float(1.)
            if j==1 or j==3:side=-1.
            dx=gx[w,ix[5,j]][0]-.38
            lift=smooth((dx+c+side*f)/.050)*(1.-smooth((dx-.052)/e))
            ref-=b*lift
            ref+=g*wp.clamp((x-.15)/.1,0.,1.)*(1.-smooth((x-.60)/.10))*(1.-lift)
        elif task==4:
            v=a*smooth((t-.20)/.38)*wp.clamp((.735-x)/.07,0.,1.)
            ref=-7.+(c+7.)*smooth((t-.20)/.35)
            if trigger[w]>=0.:
                ref=squat_push(t-trigger[w],c,e,f,g,.045,.13)
        elif task==5:
            v=a*smooth((t-.20)/.38)*wp.clamp((.735-x)/.07,0.,1.)
            pos=front;start=trigger[w]
            if j>=2:pos=rear;start=rear_trigger[w]
            ref=-7.+(c+7.)*smooth((pos-(.38-b-.14))/.13)*smooth((t-.12)/.28)
            if start>=0.:ref=squat_push(t-start,c,e,f,g,.035,.09)
        elif task==9:
            v=a*smooth((t-.20)/.36)*wp.clamp((.735-x)/.07,0.,1.)
            for foot in range(4):
                lead=c
                if foot>=2:lead=e
                stagger=f
                if foot==1 or foot==2:stagger=-f
                dx=gx[w,ix[5,foot]][0]-.38+stagger
                phase=smooth((dx+lead)/.065)*(1.-smooth((dx-.055)/.09))
                if j==foot:ref-=b*phase
                elif j==(foot^3):ref-=g*phase
                else:ref+=.5*g*phase
        elif task==10 or task==15:
            v=a*smooth((t-.20)/.38)*wp.clamp((.735-x)/.07,0.,1.)
            pos=front;lead=b;start=trigger[w];push_time=e
            if j>=2:pos=rear;lead=c;start=rear_trigger[w];push_time=f
            if task==15:
                pos=gx[w,ix[5,j]][0]
                if t>=.55 and pos>=.38-lead and wheel_trigger[w,j]<0.:wheel_trigger[w,j]=t
                start=wheel_trigger[w,j]
            ref=-7.-11.*smooth((pos-(.38-lead-.14))/.13)*smooth((t-.12)/.28)
            if start>=0.:ref=squat_push(t-start,-18.,g,push_time,-17.5,.035,.09)
        elif task==11:
            near=wp.min(wp.abs(front-.38),wp.abs(rear-.38))
            v=a*smooth((t-.20)/.38)*wp.clamp((.735-x)/.075,0.,1.)*(1.-g*smooth((.11-near)/.10))
            dx=gx[w,ix[5,j]][0]-.38
            phase=smooth((dx+c)/.075)*(1.-smooth((dx-.060)/e))
            fore=float(1.)
            if j>=2:fore=-1.
            ref+=b*phase-f*fore*57.2957795*R[w,trunk][2,0]
        elif task==12:
            v=a*smooth((t-.18)/.36)*wp.clamp((.735-x)/.075,0.,1.)
            for foot in range(4):
                wx=gx[w,ix[5,foot]][0]
                sign=float(1.)
                if foot==1 or foot==2:sign=-1.
                dx=wx-.38
                enable=smooth((t-.20)/.28)
                pre=enable*smooth((dx+c+sign*e+.035)/.040)*(1.-smooth((dx-g+sign*e)/.055))
                swing=enable*smooth((dx+c+sign*e)/.042)*(1.-smooth((dx-g+sign*e)/.055))
                if j==foot:ref-=b*swing
                elif j==(foot^1):ref+=f*pre
                elif j==(foot^3):ref-=f*pre
        elif task==13 or task==14:
            direction=float(1.)
            if task==14:direction=-1.
            cmd=direction*.32*smooth((t-.25)/.35)
            if t>=1.5:cmd=wp.clamp(e*(trigger[w]-x),-.13,.13)
            v=cmd+a*(cmd-qd[w,0])+b*grade_sin
            if j<2:ref+=g*grade_sin
            else:ref-=g*grade_sin
            if j==0 or j==2:v+=f*qd[w,5]
            else:v-=f*qd[w,5]
            wheel_k=c
        ref=wp.clamp(ref,-36.,22.)*.01745329252
        h=q[w,ix[0,j]];dh=qd[w,ix[1,j]];ws=qd[w,ix[2,j]]
        hc=torque_scale*5.2*wp.clamp((232.-wp.abs(dh)*9.5492966*24./22.2)/112.,0.,1.)
        wc=torque_scale*wp.min(1.,3.73*wp.clamp(1.-wp.abs(ws)/12.77581,0.,1.))
        ctrl[w,ix[3,j]]=wp.clamp(kp*(ref-h)-kd*dh+1.15*wp.cos(h),-hc,hc)
        ctrl[w,ix[4,j]]=wp.clamp(wheel_k*(v/.05-ws),-wc,wc)

@wp.kernel
def contacts(n:wp.array(dtype=int),worldid:wp.array(dtype=int),geoms:wp.array(dtype=wp.vec2i),
             frame:wp.array(dtype=wp.mat33),forces:wp.array(dtype=wp.spatial_vector),
             ids:wp.array2d(dtype=int),floor:int,step:int,sums:wp.array2d(dtype=float)):
    i=wp.tid()
    if i<n[0]:
        z=forces[i][0]
        if z>.0:
            pair=geoms[i];terr=pair[0];robot=pair[1]
            if robot==floor or robot==step:
                robot=pair[0];terr=pair[1]
            if terr==floor or terr==step:
                slot=int(12)
                for j in range(4):
                    if robot==ids[5,j]:
                        slot=j
                        if terr==step:
                            slot=j+8
                            if wp.abs(frame[i][0,2])>.85:slot=j+4
                wp.atomic_add(sums,worldid[i],slot,z)

@wp.kernel
def record(counter:wp.array(dtype=int),ids:wp.array2d(dtype=int),trunk:int,nj:int,nconcap:int,
           nf:wp.array(dtype=int),nc:wp.array(dtype=int),sums:wp.array2d(dtype=float),q:wp.array2d(dtype=float),
           qd:wp.array2d(dtype=float),gx:wp.array2d(dtype=wp.vec3),gr:wp.array2d(dtype=wp.mat33),
           R:wp.array2d(dtype=wp.mat33),com:wp.array2d(dtype=wp.vec3),sites:wp.array2d(dtype=wp.vec3),
           ctrl:wp.array2d(dtype=float),out:wp.array3d(dtype=float)):
    w=wp.tid();k=counter[0]
    for j in range(13):out[k,w,j]=sums[w,j]
    peak=float(0.);gap=float(0.)
    for j in range(4):
        gid=ids[5,j];cz=wp.clamp(wp.abs(gr[w,gid][2,2]),0.,1.)
        out[k,w,13+j]=(gx[w,gid][2]-.0175*cz-.05*wp.sqrt(wp.max(0.,1.-cz*cz)))*1000.
        out[k,w,17+j]=gx[w,gid][0]
        peak=wp.max(peak,wp.abs(ctrl[w,ids[3,j]]))
        gap=wp.max(gap,wp.length(sites[w,ids[6,j]]-sites[w,ids[7,j]])*1000.)
    out[k,w,21]=wp.acos(wp.clamp(R[w,trunk][2,2],-1.,1.))*57.2957795
    out[k,w,22]=com[w,trunk][2];out[k,w,23]=qd[w,0];out[k,w,24]=qd[w,5]
    out[k,w,25]=peak;out[k,w,26]=gap;out[k,w,27]=q[w,0];out[k,w,28]=q[w,1]
    out[k,w,29]=float(int(nf[w]>=nj)+2*int(nc[0]>=nconcap))
    out[k,w,30]=qd[w,1];out[k,w,31]=qd[w,2]

@wp.kernel
def advance(count:wp.array(dtype=int)):
    count[0]+=1

@wp.kernel
def disturb(count:wp.array(dtype=int),tags:wp.array(dtype=int),force:float,applied:wp.array2d(dtype=float)):
    w=wp.tid();start=int(900)
    if tags[w]==2:start=650
    applied[w,1]=0.
    if count[0]>=start and count[0]<start+30:applied[w,1]=force

class Batch:
    def __init__(self,n,extra,mu,*,grade_deg=0.,cg_shift=(0.,0.,0.),torque_scale=1.,ccd=128,lateral_force=0.,nconmax=40,njmax=180):
        self.n=n
        m=mj.MjModel.from_xml_string((HERE/"q8_r5_fitted.xml").read_text(encoding="utf8"))
        m.opt.ccd_iterations=ccd
        grade=math.radians(grade_deg)
        m.opt.gravity[:]=[-9.81*math.sin(grade),0.,-9.81*math.cos(grade)]
        ti=m.body("chassis").id;old=m.body_mass[ti];m.body_mass[ti]+=extra
        m.body_inertia[ti]*=m.body_mass[ti]/old
        m.body_ipos[ti]+=np.asarray(cg_shift)
        m.geom_friction[:,0]=mu
        d=mj.MjData(m);mj.mj_setConst(m,d);mj.mj_resetData(m,d);set_pose(m,d,[-7]*4)
        d.qpos[2]=.16+.11*math.sin(math.radians(-7));mj.mj_forward(m,d)
        self.mass=sum(m.body_mass);self.model=mw.put_model(m);self.d=mw.put_data(m,d,nworld=n,nconmax=nconmax,njmax=njmax)
        g=self.d;self.q0=wp.clone(g.qpos);self.q0_cpu=g.qpos.numpy();self.moc0=g.mocap_pos.numpy()
        ih,iw=indices(m,"hip"),indices(m,"wheel")
        ix=wp.array(np.array([m.jnt_qposadr[ih],m.jnt_dofadr[ih],m.jnt_dofadr[iw],
            [m.actuator(l+"_hip").id for l in LEGS],[m.actuator(l+"_wheel").id for l in LEGS],
            [m.geom(l+"_tyre").id for l in LEGS],[m.site(l+"_pin").id for l in LEGS],
            [m.site(l+"_bore").id for l in LEGS]],dtype=np.int32))
        self.tags=wp.zeros(n,dtype=int);self.params=wp.zeros((n,6));self.counter=wp.zeros(1,dtype=int)
        self.trig=wp.zeros(n);self.rear_trig=wp.zeros(n);self.sums=wp.zeros((n,13));self.out=wp.zeros((STEPS,n,32))
        self.wheel_trig=wp.zeros((n,4))
        self.forces=wp.empty(g.naconmax,dtype=wp.spatial_vector)
        contact_ids=wp.array(np.arange(g.naconmax,dtype=np.int32))
        # Captured kernels store device addresses; retain their backing objects for the full run.
        self.fixed_inputs=(ix,contact_ids,m,d)
        self.first=True
        def timestep():
            if lateral_force:wp.launch(disturb,n,[self.counter,self.tags,lateral_force,g.qfrc_applied])
            wp.launch(control,n,[self.counter,self.tags,self.params,ix,ti,self.trig,self.rear_trig,self.wheel_trig,g.qpos,g.qvel,g.geom_xpos,g.xmat,g.ctrl,torque_scale,math.sin(grade)])
            mw.step(self.model,g)
            self.sums.zero_()
            mw.contact_force(self.model,g,contact_ids,False,self.forces)
            wp.launch(contacts,g.naconmax,[g.nacon,g.contact.worldid,g.contact.geom,g.contact.frame,self.forces,
                      ix,m.geom("ground").id,m.geom("step").id,self.sums])
            wp.launch(record,n,[self.counter,ix,ti,g.njmax,g.naconmax,g.nefc,g.nacon,self.sums,g.qpos,g.qvel,
                      g.geom_xpos,g.geom_xmat,g.xmat,g.subtree_com,g.site_xpos,g.ctrl,self.out])
            wp.launch(advance,1,[self.counter])
        timestep();wp.synchronize()
        with wp.ScopedCapture() as cap:timestep()
        self.graph=cap.graph
    def run(self,params,tags,height,*,yaw_deg=0.,edge_bias=0.,return_invalid=False):
        g=self.d
        poses=self.moc0.copy()
        heights=np.broadcast_to(np.asarray(height),(self.n,))
        bias=np.broadcast_to(np.asarray(edge_bias),(self.n,))
        poses[:,0,2]=np.where(np.isin(tags,[3,4,5,9,10,11,12,15]),heights-.05,-.2)
        poses[:,0,0]+=bias
        poses[tags==11,0,0]=EDGE-.8+bias[tags==11]
        wp.copy(g.mocap_pos,wp.array(poses,dtype=wp.vec3))
        if np.any(tags==11) or np.any(yaw_deg):
            initial=self.q0_cpu.copy();initial[tags==11,2]+=heights[tags==11]
            yaw=np.deg2rad(yaw_deg)/2
            initial[:,3]=np.cos(yaw);initial[:,6]=np.sin(yaw)
            wp.copy(g.qpos,wp.array(initial,dtype=float))
        else:wp.copy(g.qpos,self.q0)
        g.qvel.zero_();g.qacc_warmstart.zero_();g.time.zero_();g.ctrl.zero_()
        g.qfrc_applied.zero_()
        if return_invalid:mw.forward(self.model,g)
        self.counter.zero_();self.trig.fill_(-1.);self.rear_trig.fill_(-1.);self.wheel_trig.fill_(-1.)
        wp.copy(self.tags,wp.array(tags.astype(np.int32)));wp.copy(self.params,wp.array(params.astype(np.float32)))
        for k in range(STEPS):
            wp.capture_launch(self.graph)
            if (k+1)%100==0:
                wp.synchronize()
                if self.first and (k+1) in (100,1000,2000):print("GPU rollout",round(self.mass,3),k+1,"steps",flush=True)
        self.first=False
        out=self.out.numpy()
        flags=out[:,:,29]
        if np.any(flags>=2):raise RuntimeError("Shared contact buffer exhausted during rollout")
        finite=np.isfinite(out).all(axis=(0,2))
        saturated=np.any(flags==1,axis=0)
        if not return_invalid and (not finite.all() or np.any(saturated)):
            raise RuntimeError(f"Invalid rollouts: {sum(~finite)} nonfinite and {sum(saturated)} at constraint capacity")
        weight=out[65:90,:,:8].sum(axis=2).mean(axis=0)
        bad_weight=np.abs(weight-self.mass*9.81)>self.mass*9.81*.25
        if return_invalid:
            invalid=np.select([~finite,saturated,bad_weight],["nonfinite","constraint_capacity","initial_normal_force"],default="")
            if np.all(invalid!=""):raise RuntimeError(f"All simulated worlds invalid: {np.unique(invalid,return_counts=True)}")
            return out,invalid
        if bad_weight.any():
            worst=int(np.argmax(np.abs(weight-self.mass*9.81)))
            raise RuntimeError(f"Invalid initial weight reaction for policy {tags[worst]} world {worst}: {weight[worst]} N, expected {self.mass*9.81}")
        return out

def contiguous(mask):
    changes=np.diff(np.r_[False,mask,False].astype(int))
    return zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1))

def assess(trace,task,height):
    t=np.arange(STEPS)*DT;last=t>=3.65;active=t>=.2
    floor=trace[:,:4];top=trace[:,4:8];side=trace[:,8:12];support=floor+top
    z=trace[:,13:17];x=trace[:,17:21]
    hull=float(trace[active,12].max());tilt=float(trace[active,21].max());gap=float(trace[active,26].max())
    tilt_end=float(trace[last,21].max())
    speed_end=float(np.max(np.linalg.norm(trace[last][:,[23,30,31]],axis=1)))
    stable=tilt_end<=5 and speed_end<.10 and (tilt_end-float(trace[last,21].min()))<1.
    hard=(hull<2 and gap<.8)
    penalty=1.5*max(0,tilt-5)+.35*max(0,hull-1)+30*max(0,gap-.5)
    fields=dict(peak_structure_contact_N=hull,max_tilt_deg=tilt,closure_mm=gap,end_speed_mps=speed_end,
                hip_peak_Nm=float(trace[active,25].max()),end_stable=bool(stable))
    if task==0:
        def sm(u):
            u=np.clip(u,0,1);return u*u*(3-2*u)
        v=.22*sm((t-.4)/.45)*(1-sm((t-1.35)/.45))-.12*sm((t-2.)/.4)*(1-sm((t-3.)/.4))
        yaw=.35*sm((t-.65)/.3)*(1-sm((t-1.4)/.3))
        e=float(np.mean((trace[:,23]-v)**2)**.5);ey=float(np.mean((trace[:,24]-yaw)**2)**.5)
        passed=hard and stable and e<.035 and ey<.10
        score=12-90*e-20*ey-penalty;fields.update(vx_rmse_mps=e,yaw_rmse_rad_s=ey)
    elif task==1:
        window=(t>=.2)&(t<3.8);hold=(t>=1.65)&(t<2.35)
        loads=support[window,1:];minimum=float(loads.min())
        bad=float(np.any(loads<1,axis=1).sum()*DT*1000)
        clear=float(z[hold,0].min());passed=hard and stable and tilt<=5 and clear>=23 and bad==0
        score=25-.025*bad+2*min(minimum,6)+min(clear-23,0)*3-penalty
        fields.update(min_three_support_N=minimum,below_1N_ms=bad,hold_FL_clearance_mm=clear)
    else:
        airborne=((support+side).sum(axis=1)<.5)&(trace[:,12]<.5)&(t>.7)
        flights=[];valid_landing=False
        for a,b in contiguous(airborne):
            if b-a<10 or b>=STEPS:continue
            zrel=z[a:b]-np.where((x[a:b]>=EDGE)&(task>=3),height*1000,0.)
            wheel=float(zrel.min(axis=1).max());rise=float((trace[a:b,22].max()-trace[a,22])*1000)
            flights.append(((b-a)*DT*1000,wheel,rise))
            pre=slice(max(0,a-50),a)
            from_ground=(floor[pre]>1).sum(axis=1).max()>=3 and top[pre].sum(axis=1).max()<1
            contact=np.flatnonzero((floor[b:]+top[b:]+side[b:]).sum(axis=1)>1)
            if contact.size and from_ground and wheel>=2.:
                touch=b+int(contact[0])
                if top[touch:touch+5].sum(axis=1).max()>1 and floor[touch:].sum(axis=1).max()<1:
                    valid_landing=True
        duration,wheel,rise=max(flights,key=lambda v:v[1],default=(0.,0.,0.))
        fields.update(flight_ms=float(duration),min_four_wheel_apex_mm=wheel,com_rise_after_takeoff_mm=rise)
        if task==2:
            grounded=float(((support[last]>1).sum(axis=1)==4).mean())
            passed=hard and stable and duration>=20 and wheel>=10 and rise>=5 and grounded>.95
            score=1.1*min(30,wheel)+.25*min(35,rise)+.06*min(190,duration)+4*grounded-penalty-12*speed_end
        else:
            top_fraction=float((top[last]>1).mean());all_top=float(np.all(top[last]>1,axis=1).mean())
            rear=float(x[last,2:].min());cleared=0
            for k in range(4):
                near=(x[:,k]>EDGE-.045)&(x[:,k]<=EDGE+.001)
                if np.any(near&(z[:,k]>height*1000+1)&(support[:,k]+side[:,k]<1)):cleared+=1
            atop=all_top>.95 and rear>=EDGE+.05
            axle_times=[]
            for sl in [slice(0,2),slice(2,4)]:
                near=((x[:,sl].mean(axis=1)>EDGE-.15)&(x[:,sl].mean(axis=1)<EDGE+.055))
                unloaded=(support[:,sl]+side[:,sl]).sum(axis=1)<1
                when=None
                for a,b in contiguous(unloaded&near):
                    if (b-a)>=8 and z[a:b,sl].min(axis=1).max()>height*1000+1 and np.max(z[a:b,sl].mean(axis=1))-z[a,sl].mean()>3:
                        when=float(t[a]);break
                axle_times.append(when)
            staged=all(v is not None for v in axle_times) and axle_times[1]-axle_times[0]>.12
            passed=(hard and stable and atop and (cleared==4 if task==3 else valid_landing if task==4 else staged))
            score=30*top_fraction+45*np.clip(rear-EDGE,-.5,.12)+4*cleared-penalty-15*speed_end
            if task==4:score+=.10*min(duration,150)+.4*min(30,wheel)+15*valid_landing
            if task==5:score+=12*sum(v is not None for v in axle_times)+15*staged
            fields.update(all_four_atop_fraction=all_top,minimum_final_rear_x_m=rear,
                          unloaded_wheels_clear_at_edge=cleared,from_floor_to_top_in_one_flight=bool(valid_landing),
                          peak_tyre_riser_contact_N=float(side.sum(axis=1).max()),step_height_mm=round(height*1000,2),
                          separate_axle_liftoff_s=axle_times)
    fields.update(score=float(score+30*passed),passed=bool(passed))
    return fields

def evaluation_batch(batch,samples,height,policy_ids,metric):
    tags=np.repeat(policy_ids,samples.shape[1])
    out=batch.run(samples.reshape(-1,6),tags,height)
    return [[metric(out[:,j*samples.shape[1]+k,:],tag,height) for k in range(samples.shape[1])] for j,tag in enumerate(policy_ids)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--population",type=int,default=64);ap.add_argument("--generations",type=int,default=32)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--resume",action="store_true")
    ap.add_argument("--warm-start",type=Path)
    ap.add_argument("--followup",action="store_true")
    options=ap.parse_args();out=options.output;out.mkdir(exist_ok=True)
    tasks,limits,seed=TASKS,LIMITS,SEED
    policy_ids,metric=tuple(range(len(tasks))),assess
    hold_extra,hold_mu=.12,.62
    hold_heights=(.010,.020,.030)
    if options.followup:
        from functools import partial
        import followup_tasks as extra
        if not options.warm_start:ap.error("--followup requires --warm-start")
        prior=json.loads(options.warm_start.read_text(encoding="utf8"))["coefficients"]
        tasks,limits,seed=extra.NAMES,extra.BOUNDS,extra.seeds(prior)
        policy_ids,metric=extra.TAGS,partial(extra.assess,base_assess=assess)
        hold_extra,hold_mu=.16,.57
        hold_heights=(.015,.020,.025,.030,.032)
    wp.config.kernel_cache_dir=str((HERE.parent if options.followup else HERE)/".warp_cache");wp.config.quiet=True
    # 3.6.0 allocates a 24-edge EPA scratch horizon; wheel/step contact exhausted it in the pilot.
    # This is a process-local scratch allocation parameter, not an edit to the installed SDK.
    from mujoco_warp._src import collision_convex
    collision_convex.MJ_MAX_EPAHORIZON=96
    wp.init();device=wp.get_device("cuda:0");wp.set_device(device)
    print("Device",device.name,"MuJoCo",mj.__version__,"MuJoCo Warp",version("mujoco-warp"),flush=True)
    pop=options.population;gens=options.generations
    if pop<12 or gens<3:raise ValueError("population >=12 and generations >=3")
    lo,hi=limits[:,:,0],limits[:,:,1];bounds=hi-lo
    rng=np.random.default_rng(248412 if options.followup else 248411);mean=seed.copy();std=bounds*.23
    best=seed.copy();best_scores=np.full(len(tasks),-np.inf)
    if options.warm_start and not options.followup:
        prior=json.loads(options.warm_start.read_text(encoding="utf8"))["coefficients"]
        for j,k in enumerate(TASKS):
            if k in prior:mean[j]=np.clip(prior[k],lo[j],hi[j])
        best=mean.copy()
    history=[];start=time.monotonic();start_gen=0
    statefile=out/"optimizer.json"
    if options.resume and statefile.exists():
        state=json.loads(statefile.read_text(encoding="utf8"))
        if state["population"]!=pop or state["generations"]!=gens:raise ValueError("Checkpoint configuration differs")
        mean,std,best,best_scores=[np.array(state[k]) for k in ("mean","std","best","best_scores")]
        start_gen=state["completed"];history=state["times"];rng.bit_generator.state=state["rng"]
    batches=[Batch(pop*len(tasks),delta,mu) for delta,mu in [(0.,.75),(.25,.50)]]
    ready=time.monotonic();print("GPU graphs ready",round(ready-start,1),"seconds",flush=True)
    for gen in range(start_gen,gens):
        tick=time.monotonic()
        # Curriculum stages share the same optimizers, with a variance floor for new step heights.
        stages=4 if options.followup else 3
        level=min(2,stages*gen//gens);height=([.020,.025,.030] if options.followup else [.010,.020,.030])[level]
        if gen==0 or level!=min(2,stages*(gen-1)//gens):
            best_scores[:]=-np.inf; std=np.maximum(std,.13*bounds)
        samples=np.clip(rng.normal(mean[:,None,:],std[:,None,:],(len(tasks),pop,6)),lo[:,None,:],hi[:,None,:])
        samples[:,0]=seed;samples[:,1]=best;samples[:,2]=mean
        scenarios=[evaluation_batch(b,samples,height,policy_ids,metric) for b in batches]
        scores=np.array([[[s["score"] for s in task] for task in cond] for cond in scenarios])
        robust=.7*scores.min(axis=0)+.3*scores.mean(axis=0)
        summary={}
        for j,task in enumerate(tasks):
            order=np.argsort(robust[j]);winner=int(order[-1]);elite=samples[j,order[-max(5,pop//7):]]
            mean[j]=.25*mean[j]+.75*elite.mean(axis=0);std[j]=np.maximum(.045*bounds[j],.25*std[j]+.75*elite.std(axis=0))
            if robust[j,winner]>=best_scores[j]:
                best_scores[j]=robust[j,winner];best[j]=samples[j,winner]
            summary[task]=dict(winner=samples[j,winner].tolist(),robust_score=float(robust[j,winner]),
                  nominal=scenarios[0][j][winner],heavy=scenarios[1][j][winner],
                  nominal_passes=sum(v["passed"] for v in scenarios[0][j]),
                  heavy_passes=sum(v["passed"] for v in scenarios[1][j]))
        elapsed=time.monotonic()-tick;history.append(elapsed)
        report=dict(generation=gen+1,generations=gens,population=pop,step_mm=1000*height,gpu=device.name,
                    nominal_mass_kg=batches[0].mass,heavy_mass_kg=batches[1].mass,
                    generation_seconds=round(elapsed,3),physics_steps=int((gen+1)*pop*len(tasks)*2*STEPS),
                    remaining_training_seconds=round(float(np.median(history[-5:]))*(gens-gen-1)),
                    task_results=summary,best_coefficients=dict(zip(tasks,best.tolist())))
        save(out/f"generation_{gen+1:03}.json",report);save(out/"progress.json",report)
        save(statefile,dict(population=pop,generations=gens,completed=gen+1,mean=mean.tolist(),std=std.tolist(),
                            best=best.tolist(),best_scores=best_scores.tolist(),times=history,rng=rng.bit_generator.state))
        print("generation",gen+1,"/",gens,"s",round(elapsed,1),"remaining training seconds",report["remaining_training_seconds"],flush=True)
    # Holdout: changed mass and friction, both fitted reference and trained policies, all step heights.
    hold=Batch(2*len(tasks),hold_extra,hold_mu);final={}
    for h in hold_heights:
        pp=np.stack([seed,best],axis=1)
        result=evaluation_batch(hold,pp,h,policy_ids,metric)
        final[str(round(1000*h))]={task:dict(reference=r[0],trained=r[1]) for task,r in zip(tasks,result)}
    from native_holdout import replay
    native={}
    for h in hold_heights:
        for j,name in enumerate(tasks):
            if j<3 and h!=hold_heights[0]:continue
            key=f"{name}_{round(h*1000) if j>=3 else 0}mm"
            tag=policy_ids[j]
            stats=metric(replay(tag,best[j],h,hold_extra,hold_mu),tag,h)
            gpu_stats=final[str(round(1000*h))][name]["trained"]
            native[key]=dict(native=stats,gpu=gpu_stats,passed_both=bool(stats["passed"] and gpu_stats["passed"]))
    save(out/"final.json",dict(gpu=device.name,generations=gens,nominal_mass_kg=batches[0].mass,
        holdout_mass_kg=hold.mass,holdout_friction=hold_mu,coefficients=dict(zip(tasks,best.tolist())),
        holdout=final,native_crosscheck=native,elapsed_seconds=time.monotonic()-start))
    print("Completed, final.json saved",flush=True)
if __name__=="__main__":main()


