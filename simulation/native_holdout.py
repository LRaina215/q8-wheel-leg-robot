"""Independent native MuJoCo replay of learned controls on unseen payload and friction."""
import math
from collections import deque
import numpy as np
import mujoco as mj

from pilot import HERE,LEGS,indices,set_pose

def smooth(x):
    u=min(1.,max(0.,x));return u*u*(3.-2.*u)

def push(dt,d,p,s,tuck,delay,recover):
    v=d+(p-d)*smooth(dt/s)
    v+=(tuck-v)*smooth((dt-s-delay)/.075)
    return v+(-7.-v)*smooth((dt-s-delay-.075-recover)/.28)

def replay(task,coeff,height,extra=.12,mu=.62,*,grade_deg=0.,cg_shift=(0.,0.,0.),torque_scale=1.,ccd=128,yaw_deg=0.,edge_bias=0.,lateral_force=0.,
           approach_gain=0.,command_period_steps=1,command_delay_steps=0,telemetry=None,fixed_hip_target_deg=None):
    m=mj.MjModel.from_xml_string((HERE/"q8_r5_fitted.xml").read_text(encoding="utf8"))
    i=m.body("chassis").id;old=m.body_mass[i];m.body_mass[i]+=extra
    m.body_inertia[i]*=m.body_mass[i]/old;m.geom_friction[:,0]=mu;m.opt.ccd_iterations=ccd
    m.body_ipos[i]+=np.asarray(cg_shift);grade=math.radians(grade_deg)
    m.opt.gravity[:]=[-9.81*math.sin(grade),0.,-9.81*math.cos(grade)]
    d=mj.MjData(m);mj.mj_setConst(m,d);mj.mj_resetData(m,d);set_pose(m,d,[-7]*4)
    d.qpos[2]=.16+.11*math.sin(math.radians(-7))
    yaw=math.radians(yaw_deg)/2;d.qpos[3]=math.cos(yaw);d.qpos[6]=math.sin(yaw)
    d.mocap_pos[0,2]=height-.05 if task in (3,4,5,9,10,11,12,15) else -.2
    if task==11:
        d.mocap_pos[0,0]=.38-.8;d.qpos[2]+=height
    d.mocap_pos[0,0]+=edge_bias
    mj.mj_forward(m,d)
    hip,w=indices(m,"hip"),indices(m,"wheel")
    hq,hv,wv=m.jnt_qposadr[hip],m.jnt_dofadr[hip],m.jnt_dofadr[w]
    ha=[m.actuator(l+"_hip").id for l in LEGS];wa=[m.actuator(l+"_wheel").id for l in LEGS]
    tyre=[m.geom(l+"_tyre").id for l in LEGS];lookup={v:j for j,v in enumerate(tyre)}
    pin=[m.site(l+"_pin").id for l in LEGS];bore=[m.site(l+"_bore").id for l in LEGS]
    floor=m.geom("ground").id;box=m.geom("step").id;a,b,c,e,f,g=coeff
    start=[None,None];side=np.array([-1,1,-1,1]);force=np.zeros(6);out=np.zeros((2000,32))
    wheel_start=[None]*4
    if command_period_steps<1 or command_delay_steps<0:raise ValueError("Invalid command timing")
    timed=command_period_steps!=1 or command_delay_steps!=0
    pipeline=deque()
    held_ref=np.full(4,-7.);held_v=np.zeros(4)
    for k in range(2000):
        pulse_start=650 if task==2 else 900
        d.qfrc_applied[1]=lateral_force if pulse_start<=k<pulse_start+30 else 0.
        t=k*.002;ref=np.full(4,-7.);v=np.zeros(4);kp=54.;kd=.4;wk=.22
        x=d.qpos[0];wheel_x=d.geom_xpos[tyre,0]
        ax=[np.mean(wheel_x[:2]),np.mean(wheel_x[2:])]
        heading=math.atan2(d.xmat[i,3],d.xmat[i,0])
        if telemetry is not None and "heading_near_edge_deg" not in telemetry and max(wheel_x)>=.38+edge_bias-.045:
            telemetry["heading_near_edge_deg"]=math.degrees(heading)
        if task in (13,14) and k==750:start[0]=x
        if task in (4,5,10) and t>=.55 and ax[0]>=.38-b and start[0] is None:start[0]=t
        if task in (5,10) and start[0] is not None and ax[1]>=.38-(c if task==10 else b) and start[1] is None:start[1]=t
        if task==0:
            kp,kd,wk=a,b,c
            cmd=.22*smooth((t-.4)/.45)*(1-smooth((t-1.35)/.45))-.12*smooth((t-2)/.4)*(1-smooth((t-3)/.4))
            yaw=.35*smooth((t-.65)/.3)*(1-smooth((t-1.4)/.3))
            v=cmd+e*(cmd-d.qvel[0])+side*(.205*yaw+f*(yaw-d.qvel[5]))
            ref+=g*180/math.pi*d.xmat[i,6]
        elif task in (1,6,7,8):
            corner=0 if task==1 else task-5
            pre=smooth(min((t-.2)/.4,(3.8-t)/.4))
            ref[corner]-=c*smooth(min((t-.6)/b,(3.4-t)/b))
            ref[1^corner]+=(e+g)*pre;ref[2^corner]+=(e-g)*pre
            diag=(1 if corner<2 else -1)*d.xmat[i,6]+(1 if corner%2==0 else -1)*d.xmat[i,7]
            ref[3^corner]+=a*pre+math.degrees(f)*pre*diag/math.sqrt(2)
        elif task==2:
            ref[:]=push(t-1.1,a,b,c,e,f,g) if t>=1.1 else -7+(a+7)*smooth((t-.30)/.60)
        elif task==3:
            v[:]=a*smooth((t-.20)/.36)*np.clip((.735-x)/.07,0,1)
            for j in range(4):
                dx=wheel_x[j]-.38;lift=smooth((dx+c-side[j]*f)/.05)*(1-smooth((dx-.052)/e))
                ref[j]-=b*lift
                ref[j]+=g*np.clip((x-.15)/.1,0,1)*(1-smooth((x-.60)/.10))*(1-lift)
        elif task in (4,5):
            v[:]=a*smooth((t-.20)/.38)*np.clip((.735-x)/.07,0,1)
            for j in range(4):
                pair=0 if task==4 else j//2
                if start[pair] is None:
                    pre=smooth((t-.20)/.35) if task==4 else smooth((ax[pair]-(.38-b-.14))/.13)*smooth((t-.12)/.28)
                    ref[j]=-7+(c+7)*pre
                else:ref[j]=push(t-start[pair],c,e,f,g,.045 if task==4 else .035,.13 if task==4 else .09)
        elif task==9:
            v[:]=a*smooth((t-.20)/.36)*np.clip((.735-x)/.07,0,1)
            for foot,wx in enumerate(wheel_x):
                dx=wx-.38+(f if foot in (0,3) else -f)
                phase=smooth((dx+(c if foot<2 else e))/.065)*(1-smooth((dx-.055)/.09))
                ref[foot]-=b*phase;ref[foot^3]-=g*phase
                ref[foot^1]+=.5*g*phase;ref[foot^2]+=.5*g*phase
        elif task==10:
            v[:]=a*smooth((t-.20)/.38)*np.clip((.735-x)/.07,0,1)
            for pair in (0,1):
                ref[2*pair:2*pair+2]=(-7-11*smooth((ax[pair]-(.38-(b if pair==0 else c)-.14))/.13)*smooth((t-.12)/.28)
                    if start[pair] is None else push(t-start[pair],-18,g,e if pair==0 else f,-17.5,.035,.09))
        elif task==15:
            v[:]=a*smooth((t-.20)/.38)*np.clip((.735-x)/.07,0,1)
            for j,pos in enumerate(wheel_x):
                lead=b if j<2 else c
                if t>=.55 and pos>=.38-lead and wheel_start[j] is None:wheel_start[j]=t
                ref[j]=(-7-11*smooth((pos-(.38-lead-.14))/.13)*smooth((t-.12)/.28)
                        if wheel_start[j] is None else push(t-wheel_start[j],-18,g,e if j<2 else f,-17.5,.035,.09))
        elif task==11:
            near=min(abs(xw-.38) for xw in ax)
            v[:]=a*smooth((t-.20)/.38)*np.clip((.735-x)/.075,0,1)*(1-g*smooth((.11-near)/.10))
            for j,wx in enumerate(wheel_x):
                dx=wx-.38;phase=smooth((dx+c)/.075)*(1-smooth((dx-.06)/e))
                ref[j]+=b*phase-f*(1 if j<2 else -1)*math.degrees(d.xmat[i,6])
        elif task==12:
            v[:]=a*smooth((t-.18)/.36)*np.clip((.735-x)/.075,0,1)
            for foot,wx in enumerate(wheel_x):
                dx=wx-.38;stagger=e if foot in (0,3) else -e
                recover=smooth((t-.20)/.28)*(1-smooth((dx-g+stagger)/.055))
                pre=smooth((dx+c+stagger+.035)/.040)*recover
                swing=smooth((dx+c+stagger)/.042)*recover
                ref[foot]-=b*swing;ref[foot^1]+=f*pre;ref[foot^3]-=f*pre
        elif task in (13,14):
            cmd=(1 if task==13 else -1)*.32*smooth((t-.25)/.35)
            if k>=750:cmd=np.clip(e*(start[0]-x),-.13,.13)
            v[:]=cmd+a*(cmd-d.qvel[0])+b*math.sin(grade)-side*f*d.qvel[5]
            ref[:2]+=g*math.sin(grade);ref[2:]-=g*math.sin(grade);wk=c
        if task==10 and approach_gain and t>=.15 and max(wheel_x)<.38-.045:
            # Edge-normal heading is supplied by the simulation for this experiment.
            # Differential wheel speeds rotate the robot under the usual torque limits.
            reduction=np.clip((math.radians(5)-abs(heading))/math.radians(4),0.,1.)
            command=np.clip(-approach_gain*heading-.28*d.qvel[5]-.22*math.tanh(heading/.026),-.95,.95)
            v=v*reduction+side*.205*command
        if fixed_hip_target_deg is not None:ref.fill(fixed_hip_target_deg)
        if timed:
            if k%command_period_steps==0:pipeline.append((k+command_delay_steps,ref,v))
            if pipeline and pipeline[0][0]<=k:_,held_ref,held_v=pipeline.popleft()
            ref,v=held_ref,held_v
        q,qd,ws=d.qpos[hq],d.qvel[hv],d.qvel[wv]
        hc=torque_scale*5.2*np.clip((232-abs(qd)*9.5492966*24/22.2)/112,0,1)
        wc=torque_scale*np.minimum(1.,3.73*np.clip(1-abs(ws)/12.77581,0,1))
        d.ctrl[ha]=np.clip(kp*(np.radians(np.clip(ref,-36,22))-q)-kd*qd+1.15*np.cos(q),-hc,hc)
        d.ctrl[wa]=np.clip(wk*(v/.05-ws),-wc,wc)
        mj.mj_step(m,d)
        for ci,ct in enumerate(d.contact):
            tgeom,rgeom=ct.geom1,ct.geom2
            if rgeom in (floor,box):tgeom,rgeom=rgeom,tgeom
            if tgeom not in (floor,box):continue
            j=lookup.get(rgeom)
            idx=12 if j is None else j+(0 if tgeom==floor else 4 if abs(ct.frame[2])>.85 else 8)
            mj.mj_contactForce(m,d,ci,force);out[k,idx]+=max(0,force[0])
        cz=np.clip(abs(d.geom_xmat[tyre,8]),0,1)
        out[k,13:17]=1000*(d.geom_xpos[tyre,2]-.0175*cz-.05*np.sqrt(1-cz**2))
        out[k,17:21]=d.geom_xpos[tyre,0]
        out[k,21:29]=[math.degrees(math.acos(np.clip(d.xmat[i,8],-1,1))),d.subtree_com[i,2],d.qvel[0],d.qvel[5],
                     max(abs(d.ctrl[ha])),1000*np.linalg.norm(d.site_xpos[pin]-d.site_xpos[bore],axis=1).max(),d.qpos[0],d.qpos[1]]
        out[k,30:32]=d.qvel[1:3]
    return out

