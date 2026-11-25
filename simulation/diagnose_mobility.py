"""One-factor Q8 replays. Preserve policy coefficients except for explicitly labelled lift-depth trials."""
from collections import defaultdict
from dataclasses import asdict, replace
import json
from pathlib import Path
import numpy as np
import warp as wp
from mujoco_warp._src import collision_convex
from native_holdout import replay
from train_actions import Batch, assess, contiguous, save
from campaign_tasks import Condition, metrics

def inspect_trace(x,tag,h,bias):
    r=metrics(x,tag,h,bias,assess)
    if tag==1:
        loads=(x[:,:4]+x[:,4:8])[100:1900,1:]
        k,j=np.unravel_index(np.argmin(loads),loads.shape)
        r.update(weakest_support=("FR","RL","RR")[j],time_of_min_s=(100+int(k))*.002,
                 min_by_support_N={n:float(v) for n,v in zip(("FR","RL","RR"),loads.min(axis=0))})
    if tag==4:
        unloaded=(x[:,:13].sum(axis=1)<.5)&(np.arange(len(x))>350)
        flights=[(a,b) for a,b in contiguous(unloaded) if b-a>=10 and b<len(x)]
        if flights:
            a,b=max(flights,key=lambda ab:ab[1]-ab[0])
            r.update(body_travel_during_flight_mm=float(1000*(x[b,27]-x[a,27])),
                     rear_axle_short_of_edge_at_touch_mm=float(1000*(.38+bias-x[b,19:21].mean())),
                     axle_spacing_at_takeoff_mm=float(1000*(x[a,17:19].mean()-x[a,19:21].mean())))
    return r

def run(campaign,dest):
    groups=defaultdict(list);base=Condition(.16,.57)
    read=lambda group:json.loads((campaign/group/"final.json").read_text())["coefficients"]
    terrain=read("terrain");handling=read("handling")
    lift=np.array(handling["38117"]["lift_FL"])
    def add(label,c,tag,p,h=0.,yaw=0.,bias=0.):
        groups[c].append((label,tag,np.array(p),h,yaw,bias))
    staged=terrain["reference"]["two_stage_step"]
    for mm in (20,30):
        for yaw in (-9,-5,-3,-2,-1,0,1,2,3,5,9):
            add("stair_yaw",base,10,staged,mm*.001,yaw)
        for mm_bias in (-8,-4,4,8):
            add("stair_edge_bias",base,10,staged,mm*.001,0.,mm_bias*.001)
    # Reproduce the two actual stressed cases, then isolate the centre shift and the force.
    for label,c in [
        ("nominal",base),("lateral_force_minus4",replace(base,lateral_force=-4.)),
        ("lateral_force_plus4",replace(base,lateral_force=4.)),
        ("cg_forward3",replace(base,cg_shift=(.003,0.,0.))),
        ("cg_left3",replace(base,cg_shift=(0.,.003,0.))),
        ("cg_back3",replace(base,cg_shift=(-.003,0.,0.))),
        ("cg_right3",replace(base,cg_shift=(0.,-.003,0.))),
        ("torque_88pct",replace(base,torque_scale=.88)),
        ("extra_chassis_340g",replace(base,extra=.34)),
        ("friction_046",replace(base,mu=.46)),
        ("previous_stress_1",Condition(.17,.56,0,(.003,.003,.002),.95,-4.)),
        ("previous_stress_2",Condition(.34,.46,0,(-.004,-.003,.004),.88,4.))]:
        yaw=-5 if label=="previous_stress_1" else 5 if label=="previous_stress_2" else 0
        for depth in (float(lift[2]),14.,16.):
            p=lift.copy();p[2]=depth
            add("lift_"+label,c,1,p,yaw=yaw)
    for mm in (15,30):
        for name in ("reference","38117","90431"):
            add("single_flight_"+name,base,4,terrain[name]["single_flight_step"],mm*.001)
    wp.config.kernel_cache_dir=str(campaign.parent/".warp_cache");wp.config.quiet=True
    collision_convex.MJ_MAX_EPAHORIZON=96;wp.init();wp.set_device("cuda:0")
    rows=[]
    for condition,cases in groups.items():
        tags=np.array([c[1] for c in cases]);ps=np.stack([c[2] for c in cases])
        h,y,b=(np.array([v[i] for v in cases]) for i in (3,4,5))
        batch=Batch(len(cases),**condition.options(),nconmax=64,njmax=384)
        gpu,bad=batch.run(ps,tags,h,yaw_deg=y,edge_bias=b,return_invalid=True)
        for j,(label,tag,p,height,yaw,bias) in enumerate(cases):
            n=inspect_trace(replay(tag,p,height,**condition.options(),yaw_deg=yaw,edge_bias=bias),tag,height,bias)
            g=inspect_trace(gpu[:,j],tag,height,bias) if not bad[j] else dict(passed=False,invalid_reason=str(bad[j]))
            rows.append(dict(label=label,dynamics=asdict(condition),coefficients=p.tolist(),height_mm=height*1000,
                             initial_yaw_deg=yaw,edge_bias_mm=1000*bias,native=n,gpu=g,passed_both=n["passed"] and g["passed"]))
        print("completed",len(rows),"cases",flush=True)
        del batch,gpu
    save(dest,dict(description="Paired native and GPU replays with fixed coefficients; only labelled lift-depth variants change the policy.",cases=rows))
if __name__=="__main__":
    import sys
    run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]))
