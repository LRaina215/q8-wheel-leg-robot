"""Replay residual ONNX plus the calibrated phase reference in native MuJoCo."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import mujoco as mj
import numpy as np
from pilot import HERE,LEGS,indices,set_pose
from flatjump_policy_io import GOALS,DT,DECIMATION,HORIZON,observations,commands,metrics


def replay(policy,goal,extra,mu,scale,yaw_deg):
    m=mj.MjModel.from_xml_path(str(HERE/"q8_r5_fitted.xml"))
    m.opt.ccd_iterations=256
    torso=m.body("chassis").id
    old=m.body_mass[torso]
    m.body_mass[torso]+=extra
    m.body_inertia[torso]*=m.body_mass[torso]/old
    m.geom_friction[:,0]=mu
    d=mj.MjData(m)
    mj.mj_setConst(m,d)
    mj.mj_resetData(m,d)
    set_pose(m,d,[-7]*4)
    d.qpos[2]=.160+.110*math.sin(math.radians(-7.))
    d.qpos[3]=math.cos(math.radians(yaw_deg)/2)
    d.qpos[6]=math.sin(math.radians(yaw_deg)/2)
    d.mocap_pos[0]=[5.,0.,-.3]
    mj.mj_forward(m,d)
    ih,iw=indices(m,"hip"),indices(m,"wheel")
    hq,hv,wv=m.jnt_qposadr[ih],m.jnt_dofadr[ih],m.jnt_dofadr[iw]
    ha=[m.actuator(l+"_hip").id for l in LEGS]
    wa=[m.actuator(l+"_wheel").id for l in LEGS]
    tyre=[m.geom(l+"_tyre").id for l in LEGS]
    lookup={v:i for i,v in enumerate(tyre)}
    floor=m.geom("ground").id
    pin=[m.site(l+"_pin").id for l in LEGS]
    bore=[m.site(l+"_bore").id for l in LEGS]
    force=np.zeros(6)
    action=np.zeros((1,8),np.float32)
    trace=np.empty((HORIZON*DECIMATION,1,10))
    for k in range(len(trace)):
        if k%DECIMATION==0:
            R=d.xmat[torso].reshape(3,3)
            raw=np.r_[d.qpos[:2],R[2,0],R[2,1],R[1,0],d.qvel[:2],d.qvel[3:6]*.25,
                      (d.qpos[hq]+.12217305)*2.,d.qvel[hv]*.20,d.qvel[wv]*.08]
            obs=observations(raw[None,:],d.qvel[2],goal,k//DECIMATION,action)
            action=policy(obs)
        ref,speed=commands(k*DT,action[0])
        h,dh,ws=d.qpos[hq],d.qvel[hv],d.qvel[wv]
        cap=scale*5.2*np.clip((232-np.abs(dh)*9.5492966*24/22.2)/112,0,1)
        wcap=scale*np.minimum(1.,3.73*np.clip(1-np.abs(ws)/12.77581,0,1))
        d.ctrl[ha]=np.clip(54*(ref-h)-.4*dh+1.15*np.cos(h),-cap,cap)
        d.ctrl[wa]=np.clip(.22*(speed/.05-ws),-wcap,wcap)
        mj.mj_step(m,d)
        normal=np.zeros(4)
        hull=0.
        for ci,c in enumerate(d.contact):
            a,b=int(c.geom1),int(c.geom2)
            if b==floor: a,b=b,a
            if a!=floor: continue
            mj.mj_contactForce(m,d,ci,force)
            if b in lookup: normal[lookup[b]]+=max(0.,force[0])
            else: hull+=max(0.,force[0])
        cz=np.clip(abs(d.geom_xmat[tyre,8]),0.,1.)
        clearance=1000.*(d.geom_xpos[tyre,2]-.0175*cz-.05*np.sqrt(1.-cz*cz)).min()
        tilt=math.degrees(math.acos(np.clip(d.xmat[torso,8],-1,1)))
        trace[k,0]=[normal.sum()+hull,clearance,1000.*d.subtree_com[torso,2],tilt,np.linalg.norm(d.qvel[:3]),
                    hull,1000.*np.linalg.norm(d.site_xpos[pin]-d.site_xpos[bore],axis=1).max(),
                    (normal>1.).all(),int(any(w.number for w in d.warning)),np.linalg.norm(d.qpos[:2])]
    stats=metrics(trace,np.array([goal]))
    return dict(goal_mm=int(goal),mass_kg=float(m.body_mass.sum()),friction=mu,torque_scale=scale,yaw_deg=yaw_deg,
                **{k:v[0].item() for k,v in stats.items()})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--actor",default="jump_residual_best.onnx")
    parser.add_argument("--output",default="native_jump_final.json")
    parser.add_argument("--initial",action="store_true")
    args=parser.parse_args()
    sys.path.append(str(HERE/"export_deps"))
    import onnx
    from onnx.reference import ReferenceEvaluator
    session=ReferenceEvaluator(onnx.load(str(HERE/args.actor)))
    def actor(x): return session.run(None,{"obs":x})[0]
    settings=[(.14,.64,.97,0.),(.34,.47,.93,2.)]
    if not args.initial: settings.extend([(.14,.54,.91,-2.),(.34,.47,.89,-3.)])
    rows=[replay(actor,h,*c) for h in GOALS for c in settings]
    baseline=[replay(lambda _:np.zeros((1,8),np.float32),20,*c) for c in settings]
    dst=HERE/args.output
    tmp=dst.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(actor=args.actor,rows=rows,zero_residual_reference_20mm=baseline),
                              indent=2,allow_nan=False))
    os.replace(tmp,dst)
    print("native replay",len(rows),"cases",sum(r["valid"] and r["flight_ms"]>=20. for r in rows),
          "airborne",sum(r["clean"] for r in rows),"accepted",flush=True)


if __name__=="__main__": main()
