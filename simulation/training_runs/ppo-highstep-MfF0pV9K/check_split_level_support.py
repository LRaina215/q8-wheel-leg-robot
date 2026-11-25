"""Can the axle-split pose support the loaded robot? Starts on both planes."""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np
from pilot import HERE, LEGS, indices, set_pose


def split(height_mm,extra,mu,scale):
    tree=ET.parse(HERE/"q8_r5_fitted.xml")
    tree.find(".//geom[@name='step']").set("size",".8 .46 .16")
    m=mj.MjModel.from_xml_string(ET.tostring(tree.getroot(),encoding="unicode"))
    m.opt.ccd_iterations=256
    trunk=m.body("chassis").id
    old=m.body_mass[trunk]
    m.body_mass[trunk]+=extra
    m.body_inertia[trunk]*=m.body_mass[trunk]/old
    m.geom_friction[:,0]=mu
    d=mj.MjData(m)
    mj.mj_setConst(m,d)
    mj.mj_resetData(m,d)
    h=height_mm/1000
    # Equal and opposite excursions from cruise, up to both actual travel limits.
    span=math.asin(min(math.sin(math.radians(29)),h/(.220*math.cos(math.radians(7)))))
    ref=np.radians([-7.]*4)+np.array([-span,-span,span,span])
    set_pose(m,d,np.degrees(ref))
    tyres=[m.geom(l+"_tyre").id for l in LEGS]
    centres=d.geom_xpos[tyres]-d.xpos[trunk]
    dx,_,dz=centres[0]-centres[2]
    theta=math.asin(h/math.hypot(dx,dz))-math.atan2(dz,dx)
    d.qpos[:3]=[.38,0.,.05-centres[2,0]*math.sin(theta)-centres[2,2]*math.cos(theta)]
    d.qpos[3:7]=[math.cos(theta/2),0.,-math.sin(theta/2),0.]
    d.mocap_pos[0]=[1.18,0.,h-.16]
    mj.mj_forward(m,d)
    initial_z_error=float(np.max(np.abs(d.geom_xpos[tyres,2]-.05-np.array([h,h,0.,0.]))))
    ih,iw=indices(m,"hip"),indices(m,"wheel")
    hq,hv,wv=m.jnt_qposadr[ih],m.jnt_dofadr[ih],m.jnt_dofadr[iw]
    ha=[m.actuator(l+"_hip").id for l in LEGS]
    wa=[m.actuator(l+"_wheel").id for l in LEGS]
    pin=[m.site(l+"_pin").id for l in LEGS]
    bore=[m.site(l+"_bore").id for l in LEGS]
    ground=m.geom("ground").id
    step=m.geom("step").id
    grounded={tyres[j]:step if j<2 else ground for j in range(4)}
    force=np.zeros(6)
    late=[]
    for k in range(1000):
        angle,dhip,dwheel=d.qpos[hq],d.qvel[hv],d.qvel[wv]
        cap=scale*5.2*np.clip((232-np.abs(dhip)*9.5492966*24/22.2)/112,0,1)
        wcap=scale*np.minimum(1.,3.73*np.clip(1-np.abs(dwheel)/12.77581,0,1))
        d.ctrl[ha]=np.clip(54*(ref-angle)-.4*dhip+1.15*np.cos(angle),-cap,cap)
        d.ctrl[wa]=np.clip(-.22*dwheel,-wcap,wcap)
        mj.mj_step(m,d)
        if k<750: continue
        wheel_forces=np.zeros(4)
        hull=0.
        for ci,c in enumerate(d.contact):
            floor,part=int(c.geom1),int(c.geom2)
            if part in (step,ground): floor,part=part,floor
            if floor not in (step,ground): continue
            mj.mj_contactForce(m,d,ci,force)
            if part not in grounded: hull+=max(0.,force[0])
            elif floor==grounded[part] and abs(c.frame[2])>.85: wheel_forces[tyres.index(part)]+=max(0.,force[0])
        gap=1000*np.linalg.norm(d.site_xpos[pin]-d.site_xpos[bore],axis=1).max()
        pitch=math.degrees(math.asin(np.clip(d.xmat[trunk,6],-1,1)))
        late.append([min(wheel_forces),np.linalg.norm(d.qvel[:3]),hull,gap,pitch,max(abs(d.ctrl[ha]))])
    a=np.asarray(late)
    supported=bool(a[:,0].min()>1 and a[:,1].max()<.1 and a[:,2].max()<2 and a[:,3].max()<.8
                   and np.ptp(a[:,4])<1 and all(w.number==0 for w in d.warning))
    return dict(height_mm=height_mm,mass_kg=m.body_mass.sum(),mu=mu,scale=scale,front_deg=np.degrees(ref[0]),
                rear_deg=np.degrees(ref[2]),initial_nose_up_deg=math.degrees(theta),
                initial_tire_height_error_mm=1000*initial_z_error,settled_pitch_deg=a[:,4].mean(),
                min_each_wheel_normal_N=a[:,0].min(),max_speed_mps=a[:,1].max(),max_hull_N=a[:,2].max(),
                max_closure_mm=a[:,3].max(),max_hip_torque_Nm=a[:,5].max(),supported=supported)


if __name__=="__main__":
    rows=[split(h,*c) for c in ((.14,.64,.97),(.34,.47,.89)) for h in (60,75,90,100,120,140,150)]
    (HERE/"split_level_support.json").write_text(json.dumps(rows,indent=2))
    for r in rows:
        print(r["height_mm"],round(r["mass_kg"],3),round(r["initial_nose_up_deg"],2),r["supported"],
              round(r["min_each_wheel_normal_N"],2),round(r["max_closure_mm"],3),round(r["max_hip_torque_Nm"],2))
