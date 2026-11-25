"""CPU joint control calibration and held-out flat-ground tests. No CAD dependencies."""
from pathlib import Path
from itertools import product
import argparse
import json
import math
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

HERE=Path(__file__).resolve().parent
LEGS=("FL","FR","RL","RR")

def indices(model, role):
    return [model.joint(n+"_"+role).id for n in LEGS]

def set_pose(m,d,deg):
    for role,sign in [("hip",1),("follower",1),("carrier",-1)]:
        d.qpos[m.jnt_qposadr[indices(m,role)]]=np.radians(deg)*sign
    mj.mj_forward(m,d)

def geometry_check():
    model=mj.MjModel.from_xml_string((HERE/"q8_r5.xml").read_text(encoding="utf8"))
    ur=ET.parse(HERE/"q8_r5.urdf").getroot()
    assert model.nu==8 and model.neq==4
    worst=0.
    for angles in [[-36]*4,[-7]*4,[22]*4,[-36,-7,-7,-7],[-36,22,22,-36]]:
        d=mj.MjData(model)
        set_pose(model,d,angles)
        # Wheel centres in R5 chassis frame (x forward, y left, z up), directly from CAD.
        for leg,angle in zip(LEGS,angles):
            f=1 if leg[0]=="F" else -1
            y=1 if leg[1]=="L" else -1
            a=math.radians(angle)
            target=np.array([f*(.112+.110*math.cos(a)),y*.205,-.110-.110*math.sin(a)])
            actual=d.body(leg+"_wheel").xpos-d.body("chassis").xpos
            pin=d.site(leg+"_pin").xpos-d.site(leg+"_bore").xpos
            # Evaluate the URDF tree, including its mimic joints.
            frames={"chassis":(np.eye(3),np.zeros(3))}
            for j in ur.findall("joint"):
                name=j.get("name")
                if not name.startswith(leg):continue
                R,t=frames[j.find("parent").get("link")]
                offset=np.fromstring(j.find("origin").get("xyz"),sep=" ")
                axis=np.fromstring(j.find("axis").get("xyz"),sep=" ")[1]
                mimic=j.find("mimic")
                if mimic is not None:assert mimic.get("joint")==leg+"_hip"
                value=0 if name.endswith("wheel") else a*(float(mimic.get("multiplier")) if mimic is not None else 1)
                co,si=math.cos(axis*value),math.sin(axis*value)
                frames[name]=(R@np.array([[co,0,si],[0,1,0],[-si,0,co]]),t+R@offset)
            worst=max(worst,np.linalg.norm(actual-target),np.linalg.norm(pin),np.linalg.norm(frames[leg+"_wheel"][1]-target))
    assert worst<1e-7,worst
    return float(worst*1000)

def episode(gains, motion, mass=6., friction=.75, amplitude=1.):
    m=mj.MjModel.from_xml_string((HERE/"q8_r5.xml").read_text(encoding="utf8"))
    trunk=m.body("chassis").id
    old=m.body_mass[trunk]
    m.body_mass[trunk]+=mass-6.
    m.body_inertia[trunk]*=m.body_mass[trunk]/old
    m.geom_friction[:,0]=friction
    d=mj.MjData(m)
    mj.mj_setConst(m,d)
    mj.mj_resetData(m,d)
    init=-7.
    set_pose(m,d,[init]*4)
    d.qpos[2]=.160+.110*math.sin(math.radians(init))
    mj.mj_forward(m,d)
    hips=indices(m,"hip");wheels=indices(m,"wheel")
    hq=m.jnt_qposadr[hips];hv=m.jnt_dofadr[hips];wv=m.jnt_dofadr[wheels]
    ha=[m.actuator(n+"_hip").id for n in LEGS];wa=[m.actuator(n+"_wheel").id for n in LEGS]
    pin=[m.site(n+"_pin").id for n in LEGS];bore=[m.site(n+"_bore").id for n in LEGS]
    tyres={m.geom(n+"_tyre").id for n in LEGS}
    ground=m.geom("ground").id;belly=m.geom("belly").id
    lift_clearance=[];tripod=[];errs=[];v_trace=[];height=[];tilts=[];contacts=[];gap=0.;belly_hit=False;hip_peak=0.;wheel_peak=0.
    kp,kd=gains
    for step in range(2000):
        t=step*m.opt.timestep
        qref=init;vref=0.
        if motion=="squat" and .6<t<3.6:
            # A smooth cycle from cruise down 16 deg, back through cruise, then up 10 deg.
            phase=(t-.6)/1.5
            if phase<1:qref-=16*amplitude*math.sin(math.pi*phase)**2
            else:qref+=10*amplitude*math.sin(math.pi*(phase-1))**2
        if motion in ("forward","reverse"):
            vref=(.17 if motion=="forward" else -.12)*min(1,max(0,(t-.6)/.5),max(0,(3.5-t)/.5))
        desired=np.full(4,float(qref))
        if motion=="lift_FL":
            # Hold all other hips at cruise. Smooth ramp, hold, and lower the front-left wheel.
            u=min(1.,max(0.,(t-.6)/.8),max(0.,(3.4-t)/.8))
            desired[0]-=20*(3*u*u-2*u*u*u)
        q,qd=d.qpos[hq],d.qvel[hv];speed=d.qvel[wv]
        demand=kp*(np.radians(desired)-q)-kd*qd+1.15*np.cos(q)
        cap=5.2*np.clip((232-np.abs(qd)*60/(2*math.pi)*24/22.2)/112,0,1)
        d.ctrl[ha]=np.clip(demand,-cap,cap)
        wheel_request=.22*(vref/.05-speed)
        cap_w=np.minimum(1.,3.73*np.clip(1-np.abs(speed)/(122*2*math.pi/60),0,1))
        d.ctrl[wa]=np.clip(wheel_request,-cap_w,cap_w)
        hip_peak=max(hip_peak,float(np.max(abs(d.ctrl[ha]))));wheel_peak=max(wheel_peak,float(np.max(abs(d.ctrl[wa]))))
        mj.mj_step(m,d)
        if t>=.6 and step%5==0:
            errs.extend(np.degrees(d.qpos[hq])-desired)
            if 1.3<t<2.9:v_trace.append(float(d.qvel[0]))
            height.append(float(d.qpos[2]))
            tilts.append(math.degrees(math.acos(np.clip(d.xmat[trunk,8],-1,1))))
            gap=max(gap,float(np.linalg.norm(d.site_xpos[pin]-d.site_xpos[bore],axis=1).max()))
            touching=set()
            for c in d.contact:
                pair={c.geom1,c.geom2}
                if ground in pair and c.dist<=0:
                    touching.update(pair&tyres)
                    if belly in pair:belly_hit=True
            contacts.append(len(touching))
            if motion=="lift_FL" and 1.5<t<2.5:
                tyre=m.geom("FL_tyre").id
                cz=abs(d.geom_xmat[tyre,8])
                bottom=d.geom_xpos[tyre,2]-.0175*cz-.05*math.sqrt(max(0.,1-cz**2))
                lift_clearance.append(1000*bottom)
                tripod.append(touching==(tyres-{tyre}))
    out=dict(hip_rmse_deg=float(np.mean(np.square(errs))**.5),min_wheels_touching=min(contacts),
             max_tilt_deg=max(tilts),belly_contact=bool(belly_hit),max_closure_mm=1000*gap,
             height_span_mm=1000*(max(height)-min(height)),mean_vx_mps=float(np.mean(v_trace)),
             hip_peak_Nm=hip_peak,wheel_peak_Nm=wheel_peak)
    goal={"forward":.17,"reverse":-.12}.get(motion,0.)
    out["pass"]=bool(all(np.isfinite(x) for x in errs) and max(tilts)<5 and gap<.0008
                     and not belly_hit and min(contacts)==4 and out["hip_rmse_deg"]<2
                     and abs(out["mean_vx_mps"]-goal)<.035 and (motion!="squat" or out["height_span_mm"]>25))
    if motion=="lift_FL":
        out.update(min_hold_clearance_mm=min(lift_clearance),tripod_hold_fraction=sum(tripod)/len(tripod))
        out["pass"]=bool(min(lift_clearance)>5 and all(tripod) and not belly_hit and gap<.0008
                         and max(tilts)<5 and out["hip_rmse_deg"]<2)
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=HERE/"pilot_results.json")
    args=parser.parse_args()
    geometry=geometry_check()
    candidates=[]
    for kp,kd in product((18.,36.,54.),(.4,.8)):
        r=episode((kp,kd),"squat")
        score=r["hip_rmse_deg"]+.03*r["hip_peak_Nm"]+10*(r["min_wheels_touching"]<4 or r["belly_contact"])
        candidates.append(dict(kp=kp,kd=kd,score=score))
    best=min(candidates,key=lambda r:r["score"])
    held={}
    for name,motion,mass,mu,a in [
        ("stand","stand",6.,.75,1.),("squat","squat",6.,.75,1.),
        ("forward","forward",6.,.75,1.),("reverse_heavier","reverse",6.6,.5,1.),
        ("squat_heavier","squat",6.6,.5,1.2),("lift_FL","lift_FL",6.,.75,1.)]:
        held[name]=dict(mass_kg=mass,friction=mu,**episode((best["kp"],best["kd"]),motion,mass,mu,a))
    result=dict(mujoco=mj.__version__,geometry_max_error_mm=geometry,search=candidates,best=best,episodes=held)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(held,indent=2))
if __name__=="__main__":main()
