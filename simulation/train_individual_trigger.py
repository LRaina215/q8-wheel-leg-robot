"""Focused CEM search for four independent wheel triggers on a 20 mm step."""
import gc
import json
import time
from pathlib import Path
import numpy as np
import warp as wp
from mujoco_warp._src import collision_convex
from train_actions import Batch, save, assess
from train_campaign import evaluate
from campaign_tasks import Condition, metrics
from native_holdout import replay

POP,GEN=96,72
BOUNDS=np.array([(.24,.52),(.025,.17),(.025,.17),(.045,.18),(.045,.19),(10,22)])
TRAIN=[(Condition(.08,.70),[(.020,0.,0.),(.020,-3.,0.),(.020,3.,0.),(.020,0.,.004)]),
       (Condition(.28,.52,cg_shift=(.003,-.002,.002),torque_scale=.94),
        [(.020,0.,0.),(.020,-5.,.003),(.020,5.,-.003),(.020,0.,-.004)])]

def main():
    root=Path(__file__).resolve().parent
    collision_convex.MJ_MAX_EPAHORIZON=96;wp.config.kernel_cache_dir=str(root.parent.parent/".warp_cache")
    wp.config.quiet=True;wp.init();wp.set_device("cuda:0")
    ref=np.array(json.loads((root.parent/"terrain"/"final.json").read_text())["coefficients"]["reference"]["two_stage_step"])
    lo,hi=BOUNDS.T;span=hi-lo
    rng=np.random.default_rng(67231);mean=ref.copy();std=.22*span
    best=ref.copy();best_score=-1e9;first=0;times=[];ck=root/"optimizer.json"
    if ck.exists():
        s=json.loads(ck.read_text());mean,std,best=[np.array(s[k]) for k in ("mean","std","best")]
        best_score=s["best_score"];first=s["generation"];times=s["times"];rng.bit_generator.state=s["rng"]
    batches=[Batch(4*POP,**cond.options(),nconmax=64,njmax=384) for cond,_ in TRAIN]
    for gen in range(first,GEN):
        t=time.monotonic();draw=np.clip(rng.normal(mean,std,(POP,6)),lo,hi)
        draw[:3]=[ref,best,mean];records=[]
        for batch,(_,settings) in zip(batches,TRAIN):
            records.extend(row[0] for row in evaluate(batch,draw[None],(15,),settings))
        sc=np.array([[r["score"] for r in row] for row in records]);ps=np.array([[r["passed"] for r in row] for row in records])
        robust=40*ps.sum(axis=0)+.6*sc.min(axis=0)+.4*sc.mean(axis=0)
        order=np.argsort(robust);k=int(order[-1]);elite=draw[order[-12:]]
        if robust[k]>=best_score:best_score=float(robust[k]);best=draw[k].copy()
        mean=.25*mean+.75*elite.mean(axis=0);std=np.maximum(.045*span,.25*std+.75*elite.std(axis=0))
        times.append(time.monotonic()-t)
        save(ck,dict(generation=gen+1,mean=mean.tolist(),std=std.tolist(),best=best.tolist(),best_score=best_score,times=times,rng=rng.bit_generator.state))
        recent=float(np.median(times[-5:]))
        save(root/"progress.json",dict(generation=gen+1,total=GEN,secs_per_gen=recent,eta_training_seconds=round(recent*(GEN-gen-1)),winner_passes_of_eight=int(ps[:,k].sum()),utc_epoch=time.time()))
        if gen%10==0:print("generation",gen+1,round(recent,2),flush=True)
    del batches,batch;gc.collect()
    cond=Condition(.16,.57)
    settings=[(.020,y,b) for y in (-6.,-4.,0.,4.,6.) for b in (-.002,0.,.002)]
    settings.extend((h,y,0.) for h in (.018,.025,.030) for y in (-3.,0.,3.))
    tags=(10,15,15);policies=np.array([ref,ref,best]);labels=("axle_reference","individual_reference","individual_trained")
    hold=Batch(len(tags)*len(settings),**cond.options(),nconmax=64,njmax=384)
    rows=evaluate(hold,policies[:,None],tags,settings)
    results=[]
    for (h,y,b),group in zip(settings,rows):
        policies_out={}
        for tag,p,label,record in zip(tags,policies,labels,group):
            n=metrics(replay(tag,p,h,**cond.options(),yaw_deg=y,edge_bias=b),tag,h,b,assess)
            policies_out[label]=dict(native=n,gpu=record[0],passed_both=bool(n["passed"] and record[0]["passed"]))
        results.append(dict(height_mm=round(h*1000),yaw_deg=y,edge_bias_mm=b*1000,policies=policies_out))
    save(root/"final.json",dict(episodes=POP*GEN*8,training_conditions=[(c.options(),s) for c,s in TRAIN],
         holdout=cond.options(),coefficients=best.tolist(),cases=results))
    print("complete",flush=True)
if __name__=="__main__":main()
