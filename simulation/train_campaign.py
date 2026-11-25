"""Run independent CEM restarts with four common conditions per candidate, then dual-engine holdouts."""
import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np
import warp as wp
from mujoco_warp._src import collision_convex
from train_actions import Batch, LIMITS, STEPS, assess, save
from campaign_tasks import GROUPS, NAMES, PLAN, SEEDS, initial, training_cases, variants, heldout, metrics
from native_holdout import replay

def evaluate(batch, params, tags, settings):
    candidates=params.shape[1]
    keys=np.repeat(tags,candidates)
    heights,yaws,biases=(np.repeat(values,len(keys)) for values in np.asarray(settings).T)
    raw,invalid=batch.run(np.tile(params.reshape(-1,6),(len(settings),1)),np.tile(keys,len(settings)),heights,
                  yaw_deg=yaws,edge_bias=biases,return_invalid=True)
    traces=np.ascontiguousarray(raw.transpose(1,0,2))
    del raw
    rows=[]
    for v,(height,_,bias) in enumerate(settings):
        offset=v*len(keys)
        batch_rows=[]
        for j,tag in enumerate(tags):
            trials=[]
            for k in range(candidates):
                idx=offset+j*candidates+k
                trials.append(dict(score=-10000.,passed=False,invalid_reason=str(invalid[idx])) if invalid[idx]
                              else metrics(traces[idx],tag,height,bias,assess))
            batch_rows.append(trials)
        rows.append(batch_rows)
    return rows

def optimize(group, root, tags, reference, limits, batches, seed_index, stop_at=None):
    gens,pop=PLAN[group]
    seed=SEEDS[seed_index]; dest=root/f"seed_{seed}";dest.mkdir(exist_ok=True)
    ck=dest/"optimizer.json";rng=np.random.default_rng(seed)
    lo,hi=limits[:,:,0],limits[:,:,1];span=hi-lo
    mean=reference.copy();std=.22*span;best=mean.copy()
    best_score=np.full(len(tags),-np.inf);start=0;times=[]
    if ck.exists():
        s=json.loads(ck.read_text());start=s["generation"];times=s["times"]
        mean,std,best,best_score=(np.array(s[k]) for k in ("mean","std","best","best_score"))
        rng.bit_generator.state=s["rng"]
    for gen in range(start,gens if stop_at is None else min(gens,stop_at)):
        tick=time.monotonic();stage=min(2,gen*4//gens)
        if not gen or stage!=min(2,(gen-1)*4//gens):
            best_score.fill(-np.inf);std=np.maximum(std,.15*span)
        draw=np.clip(rng.normal(mean[:,None],std[:,None],(len(tags),pop,6)),lo[:,None],hi[:,None])
        draw[:,0]=reference;draw[:,1]=best;draw[:,2]=mean
        cond=[]
        for env,batch in enumerate(batches):
            cond.extend(evaluate(batch,draw,tags,variants(group,stage,env)))
        scores=np.array([[[r["score"] for r in row] for row in c] for c in cond])
        successes=np.array([[[r["passed"] for r in row] for row in c] for c in cond])
        robust=.65*scores.min(axis=0)+.35*scores.mean(axis=0)+20*successes.sum(axis=0)
        state={}
        for j,tag in enumerate(tags):
            order=np.argsort(robust[j]);k=order[-1];elite=draw[j,order[-max(6,pop//8):]]
            mean[j]=.25*mean[j]+.75*elite.mean(axis=0)
            std[j]=np.maximum(.04*span[j],.25*std[j]+.75*elite.std(axis=0))
            if robust[j,k]>=best_score[j]:
                best_score[j]=robust[j,k];best[j]=draw[j,k]
            state[NAMES[tag]]=dict(winner_passes_of_four=int(successes[:,j,k].sum()),
                                    invalid_rollouts=sum("invalid_reason" in r for case in cond for r in case[j]),
                                    candidates_passing_all_four=int(successes[:,j].all(axis=0).sum()))
        times.append(time.monotonic()-tick)
        snap=dict(group=group,seed=seed,seed_index=seed_index+1,generation=gen+1,generations=gens,
                  per_task_population=pop,parallel_worlds_per_batch=2*pop*len(tags),scenarios_per_candidate=4,
                  generation_seconds=round(times[-1],2),recent_seconds=round(float(np.median(times[-8:])),2),
                  remaining_training_generations=(gens-gen-1)+(len(SEEDS)-seed_index-1)*gens,
                  last_update_epoch=time.time(),stage=stage+1,tasks=state)
        save(ck,dict(generation=gen+1,mean=mean.tolist(),std=std.tolist(),best=best.tolist(),
                     best_score=best_score.tolist(),rng=rng.bit_generator.state,times=times))
        save(dest/"progress.json",snap);save(root/"progress.json",snap)
        if not gen or (gen+1)%10==0:print(group,seed,gen+1,gens,snap["recent_seconds"],flush=True)
    return best

def validate(group,root,tags,sets):
    rows={}
    for idx,(condition,settings) in enumerate(heldout(group)):
        # One batch per dynamics configuration. Reuse it across geometric variations.
        batch=Batch(len(tags)*len(sets),**condition.options(),nconmax=64,njmax=384);params=np.stack(list(sets.values()),axis=1)
        for h,yaw,bias in settings:
            data=evaluate(batch,params,tags,[(h,yaw,bias)])[0];modes={}
            for j,tag in enumerate(tags):
                trials={}
                for k,(label,p) in enumerate(sets.items()):
                    cpu=metrics(replay(tag,p[j],h,**condition.options(),yaw_deg=yaw,edge_bias=bias),tag,h,bias,assess)
                    gpu=data[j][k]
                    trials[label]=dict(native=cpu,gpu=gpu,passed_both=bool(cpu["passed"] and gpu["passed"]))
                modes[NAMES[tag]]=trials
            key=f"case{idx}_h{h*1000:.0f}_yaw{yaw:+g}_offset{bias*1000:+g}"
            rows[key]=dict(dynamics=condition.options(),height_mm=round(h*1000),yaw_deg=yaw,edge_offset_mm=bias*1000,motions=modes)
            save(root/"holdout_progress.json",dict(completed_cases=list(rows)))
        del batch;gc.collect()
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument("group",choices=GROUPS);ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--first-generations",type=int,help="Save the first seed checkpoint and return it to the queue")
    args=ap.parse_args();root=args.output;root.mkdir(exist_ok=True,parents=True);group=args.group
    import fcntl
    ownership=(root/"worker.lock").open("a")
    fcntl.flock(ownership,fcntl.LOCK_EX)
    if (root/"final.json").exists():
        print("completed results already present",group,flush=True)
        return
    here=Path(__file__).resolve().parent
    collision_convex.MJ_MAX_EPAHORIZON=96;wp.config.kernel_cache_dir=str(here.parent/".warp_cache");wp.config.quiet=True
    wp.init();wp.set_device("cuda:0");device=wp.get_device("cuda:0")
    old,new=(json.loads((here/f).read_text())["coefficients"] for f in ("training_actions_final.json","training_followup_final.json"))
    tags=GROUPS[group];pairs=[initial(tag,old,new,LIMITS) for tag in tags]
    ref=np.array([p for p,_ in pairs],dtype=float);bounds=np.array([b for _,b in pairs],dtype=float)
    gens,pop=PLAN[group];worlds=2*pop*len(tags)
    print("starting",group,device.name,worlds,"worlds per dynamics batch",flush=True)
    capacity=dict(nconmax=64,njmax=384) if group=="terrain" else {}
    models=training_cases(group);batches=[Batch(worlds,**c.options(),**capacity) for c in models]
    if args.first_generations is not None:
        optimize(group,root,tags,ref,bounds,batches,0,args.first_generations)
        print("initial checkpoint saved",group,flush=True)
        return
    sets={"reference":ref}
    for idx,seed in enumerate(SEEDS):sets[str(seed)]=optimize(group,root,tags,ref,bounds,batches,idx)
    del batches;gc.collect()
    hold=validate(group,root,tags,sets)
    save(root/"final.json",dict(group=group,gpu=device.name,seeds=SEEDS,generations_per_seed=gens,population_per_task=pop,
         training_conditions=[c.options() for c in models],training_episodes=gens*pop*len(tags)*4*len(SEEDS),
         coefficients={key:{NAMES[t]:p.tolist() for t,p in zip(tags,arr)} for key,arr in sets.items()},holdouts=hold))
    print("completed",group,flush=True)
if __name__=="__main__":main()
