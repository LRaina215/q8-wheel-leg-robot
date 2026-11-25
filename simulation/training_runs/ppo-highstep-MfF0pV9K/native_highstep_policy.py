"""Independent 500 Hz native MuJoCo replay of the exported Q8 PPO policy."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np
from pilot import HERE,LEGS,indices,set_pose


def replay(actor,mm,extra,mu,scale,yaw,offset,estimated_edge=.38,estimated_height_mm=None):
    tree=ET.parse(HERE/"q8_r5_fitted.xml")
    tree.find(".//geom[@name='step']").set("size",".8 .46 .16")
    m=mj.MjModel.from_xml_string(ET.tostring(tree.getroot(),encoding="unicode"))
    m.opt.ccd_iterations=256
    i=m.body("chassis").id
    old=m.body_mass[i]
    m.body_mass[i]+=extra
    m.body_inertia[i]*=m.body_mass[i]/old
    m.geom_friction[:,0]=mu
    d=mj.MjData(m)
    mj.mj_setConst(m,d)
    mj.mj_resetData(m,d)
    set_pose(m,d,[-7]*4)
    d.qpos[2]=.160+.11*math.sin(math.radians(-7))
    d.qpos[3]=math.cos(math.radians(yaw)/2)
    d.qpos[6]=math.sin(math.radians(yaw)/2)
    edge=.38+offset
    d.mocap_pos[0]=[edge+.8,0.,mm*.001-.16]
    mj.mj_forward(m,d)
    hip,wh=indices(m,"hip"),indices(m,"wheel")
    hq,hv,wv=m.jnt_qposadr[hip],m.jnt_dofadr[hip],m.jnt_dofadr[wh]
    ha=[m.actuator(l+"_hip").id for l in LEGS]
    wa=[m.actuator(l+"_wheel").id for l in LEGS]
    tyre=[m.geom(l+"_tyre").id for l in LEGS]
    lookup={gid:j for j,gid in enumerate(tyre)}
    pin=[m.site(l+"_pin").id for l in LEGS]
    bore=[m.site(l+"_bore").id for l in LEGS]
    floor=m.geom("ground").id
    riser=m.geom("step").id
    last=np.zeros(8,np.float32)
    force=np.zeros(6)
    peak_hull=0.
    hull_part=None
    peak_gap=0.
    front_clear=-1.
    front_support_seconds=0.
    first_front_pair=None
    near_ticks=0
    hip_limited=0
    wheel_limited=0
    late=[]
    for k in range(2000):
        if k%20==0:
            R=d.xmat[i].reshape(3,3)
            distance=2*(estimated_edge-d.qpos[0])
            height_input=(mm if estimated_height_mm is None else estimated_height_mm)*.01
            o=np.r_[distance,3*d.qpos[1],R[2,0],R[2,1],R[1,0],
                    d.qvel[:2],.25*d.qvel[3:6],(d.qpos[hq]+.12217305)*2,d.qvel[hv]*.2,
                    d.qvel[wv]*.08,height_input,k/2000,last,max(0.,1-abs(distance-.40)*3)]
            last=actor(np.clip(o.astype(np.float32),-5.,5.)[None,:])[0]
            ref=np.deg2rad(-7+29*last[:4])
            speed=.22+.4*last[4:]
        h,dh,ws=d.qpos[hq],d.qvel[hv],d.qvel[wv]
        hc=scale*5.2*np.clip((232-np.abs(dh)*9.5492966*24/22.2)/112,0,1)
        wc=scale*np.minimum(1.,3.73*np.clip(1-np.abs(ws)/12.77581,0,1))
        request=54*(ref-h)-.4*dh+1.15*np.cos(h)
        w_request=.22*(speed/.05-ws)
        d.ctrl[ha]=np.clip(request,-hc,hc)
        d.ctrl[wa]=np.clip(w_request,-wc,wc)
        mj.mj_step(m,d)
        top=np.zeros(4)
        structure={}
        for ci,ct in enumerate(d.contact):
            terrain,part=int(ct.geom1),int(ct.geom2)
            if part in (floor,riser): terrain,part=part,terrain
            if terrain not in (floor,riser): continue
            mj.mj_contactForce(m,d,ci,force)
            f=max(0.,float(force[0]))
            j=lookup.get(part)
            if j is None: structure[part]=structure.get(part,0.)+f
            elif terrain==riser and abs(ct.frame[2])>.85: top[j]+=f
        if k>=100:
            hull=sum(structure.values())
            if hull>peak_hull:
                peak_hull=hull
                hull_part=m.geom(max(structure,key=structure.get)).name
            gap=1000*np.linalg.norm(d.site_xpos[pin]-d.site_xpos[bore],axis=1).max()
            peak_gap=max(peak_gap,float(gap))
        pos=d.geom_xpos[tyre]
        if np.max(np.abs(pos[:2,0]-edge))<.075:
            near_ticks+=1
            hip_limited+=int(np.any(np.abs(request[:2])>=hc[:2]-.001))
            wheel_limited+=int(np.any(np.abs(w_request[:2])>=wc[:2]-.001))
            cz=np.clip(abs(d.geom_xmat[tyre[:2],8]),0,1)
            lower=pos[:2,2]-.0175*cz-.05*np.sqrt(1-cz*cz)
            front_clear=max(front_clear,float(lower.min()))
        if (top[:2]>1.).all() and pos[:2,0].min()>edge:
            front_support_seconds+=.002
            if first_front_pair is None: first_front_pair=k*.002
        if k>=1820:
            late.append([(top>1.).all(),pos[2:,0].min()-edge,
                         math.degrees(math.acos(np.clip(d.xmat[i,8],-1,1))),np.linalg.norm(d.qvel[:3])])
    a=np.asarray(late)
    atop=bool(a[:,0].mean()>.95 and a[:,1].min()>=.05)
    stable=bool(a[:,2].max()<=5 and np.ptp(a[:,2])<1 and a[:,3].max()<.10)
    valid=bool(np.isfinite(a).all() and not any(w.number for w in d.warning))
    return dict(height_mm=mm,mass_kg=float(m.body_mass.sum()),friction=mu,torque_scale=scale,
                yaw_deg=yaw,edge_offset_mm=offset*1000,valid=valid,atop=atop and valid,
                stable=stable,clean=valid and atop and stable and peak_gap<.8 and peak_hull<2,
                peak_gap_mm=peak_gap,peak_hull_N=peak_hull,peak_contact_part=hull_part,
                both_front_on_top_s=round(front_support_seconds,3),first_front_pair_s=first_front_pair,
                near_riser_front_tire_bottom_mm=round(1000*front_clear,2) if near_ticks else None,
                near_riser_front_hip_limit_fraction=hip_limited/near_ticks if near_ticks else None,
                near_riser_front_drive_limit_fraction=wheel_limited/near_ticks if near_ticks else None,
                terminal_rear_center_beyond_edge_mm=round(1000*float(a[:,1].min()),1))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--actor",default="actor_best.onnx")
    parser.add_argument("--output",default="native_highstep_final.json")
    parser.add_argument("--heights",nargs="+",type=int,default=[60,75,90,100,120,140,150])
    parser.add_argument("--nominal-only",action="store_true")
    args=parser.parse_args()
    sys.path.append(str(HERE/"export_deps"))
    import onnx
    from onnx.reference import ReferenceEvaluator
    session=ReferenceEvaluator(onnx.load(str(HERE/args.actor)))
    def inference(x): return session.run(None,{"obs":x})[0]
    conds=[(.14,.64,.97,0.,0.)]
    if not args.nominal_only:
        conds +=[(.14,.64,.93,2.,.006),(.34,.47,.89,0.,0.),(.34,.47,.89,-3.,-.008)]
    results=[replay(inference,h,*cond) for h in args.heights for cond in conds]
    tmp=HERE/(args.output+".tmp")
    tmp.write_text(json.dumps(dict(actor=args.actor,results=results),indent=2,allow_nan=False))
    os.replace(tmp,HERE/args.output)
    print("native ONNX replay",len(results),"cases, four atop",sum(r["atop"] for r in results),
          "clean",sum(r["clean"] for r in results),flush=True)


if __name__=="__main__": main()
