"""Wheel rolling versus commanded hip extension on the same square step."""
import json
from pathlib import Path
import numpy as np
from native_holdout import replay

root=Path(__file__).resolve().parent
p=json.loads((root/"training_campaign_terrain_final.json").read_text())["coefficients"]["reference"]["two_stage_step"]
rows=[]
for extra,mu,scale in ((.14,.64,.97),(.34,.47,.89)):
    for mode,speed in (("wheel_cruise",.32),("wheel_matched",p[0]),("wheel_fast",.62),("staged",p[0])):
        for mm in (15,20,25,30,32,35,40,45,50,55,60):
            coeff=list(p);coeff[0]=speed
            trace=replay(10,coeff,mm/1000,extra,mu,ccd=256,torque_scale=scale,
                         fixed_hip_target_deg=None if mode=="staged" else -7.)
            last=trace[-175:];active=trace[100:]
            atop=np.mean((last[:,4:8]>1).all(axis=1))>.95 and last[:,19:21].min()>=.43
            stable=(last[:,21].max()<=5 and np.ptp(last[:,21])<1 and
                    np.max(np.linalg.norm(last[:,[23,30,31]],axis=1))<.10)
            hull=float(active[:,12].max());gap=float(active[:,26].max())
            near=np.flatnonzero(trace[:,17:19].max(axis=1)>.32)
            rows.append(dict(extra_kg=extra,mu=mu,torque_scale=scale,mode=mode,command_mps=speed,height_mm=mm,
                        approach_mps=float(trace[near[0],23]) if len(near) else None,
                        atop=bool(atop),stable=bool(stable),peak_structure_N=hull,closure_mm=gap,
                        pass_common=bool(atop and stable and hull<2 and gap<.8)))
out=root/"wheel_vs_staged_step.json"
out.write_text(json.dumps(rows,indent=2),encoding="utf8")
for cond in (.14,.34):
    for mode in ("wheel_cruise","wheel_matched","wheel_fast","staged"):
        cases=[r for r in rows if r["extra_kg"]==cond and r["mode"]==mode]
        print(cond,mode,"atop",[r["height_mm"] for r in cases if r["atop"]],"pass",[r["height_mm"] for r in cases if r["pass_common"]],flush=True)
