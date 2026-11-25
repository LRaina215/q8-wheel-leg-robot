"""Long Q8 terrain campaign. Launch 'queue' once; train workers and independent holdouts follow."""
from pathlib import Path
import json
import subprocess
import sys
import time
import numpy as np
from campaign_tasks import Condition, metrics
from train_actions import Batch, assess, save
from native_holdout import replay

ROOT=Path(__file__).resolve().parent
SEEDS=(230611,340817,561023,771209)
GENERATIONS,POP,BLOCK=1200,128,20
TAGS=(15,11)
TASKS=("individual_trigger_ascent","controlled_descent")
KNOTS=(.015,.0225,.030)
LIMITS=np.array([
    [(.24,.52),(.025,.17),(.025,.17),(.045,.18),(.045,.19),(10,22)],
    [(.25,.47),(0,18),(-.045,.08),(.04,.18),(-3,3),(0,.50)]])
TRAIN=(Condition(.04,.74),Condition(.30,.50,cg_shift=(.005,-.003,.004),torque_scale=.92))
DEV=Condition(.18,.60,cg_shift=(.001,.002,.002),torque_scale=.96)
# (physical height, heading, true minus estimated edge, estimated height) in metres and degrees.
DEV_CASES=[(h,y,b,h+err) for h in (.016,.021,.026,.030)
           for y,b,err in ((0.,0.,0.),(-4.,.003,-.001),(4.,-.003,.001))]
CHALLENGES=(Condition(.14,.64,cg_shift=(-.003,.002,.003),torque_scale=.97),
            Condition(.34,.47,cg_shift=(.004,.003,.005),torque_scale=.89))
TEST_CASES=[(h,y,b,h+err) for h in (.015,.020,.025,.030,.032)
            for y,b,err in ((0.,0.,0.),(-2.,.002,-.001),(2.,-.002,.001),
                             (-6.,-.004,.002),(6.,.004,-.002),(-9.,.006,-.003),(9.,-.006,.003))]

def setup():
    import warp as wp
    from mujoco_warp._src import collision_convex
    wp.config.quiet=True;wp.config.kernel_cache_dir=str(ROOT.parent.parent/".warp_cache")
    collision_convex.MJ_MAX_EPAHORIZON=96;wp.init();wp.set_device("cuda:0")

def baselines():
    terrain=json.loads((ROOT/"training_campaign_terrain_final.json").read_text())["coefficients"]
    short=json.loads((ROOT/"individual_trigger_final.json").read_text())["coefficients"]
    fixed=np.array([short,terrain["38117"]["controlled_descent"]])
    return np.repeat(fixed[:,None,:],3,axis=1),np.array(terrain["reference"]["two_stage_step"])

def settings(seed,gen,env):
    block=gen//BLOCK
    rng=np.random.default_rng([seed,block,env,1407])
    max_yaw=min(9.,4.+block*.20)
    out=[]
    for i in range(4):
        h=rng.uniform(.014+i*.004,.018+i*.004)
        yaw=(0. if i==block%4 else (-1 if (i+env+block)%2 else 1)*rng.uniform(1.,max_yaw))
        bias=rng.uniform(-.007,.007); dh=rng.uniform(-.003,.003)
        out.append((h,yaw,bias,h+dh))
    return out

def interpolate(bank,estimate):
    u=np.clip((estimate-KNOTS[0])/(KNOTS[1]-KNOTS[0]),0.,2.)
    j=min(1,int(u));w=u-j
    return (1.-w)*bank[...,j,:]+w*bank[...,j+1,:]

def simulate(batch,bank,tags,cases,keep=False):
    # Each candidate sees identical physical conditions. Only estimated height enters its gain schedule.
    nt,pop=bank.shape[:2];count=nt*pop
    coeff=np.stack([interpolate(bank,c[3]) for c in cases]).reshape(-1,6)
    h,y,b=[np.repeat([c[i] for c in cases],count) for i in (0,1,2)]
    tr,invalid=batch.run(coeff,np.tile(np.repeat(tags,pop),len(cases)),h,yaw_deg=y,edge_bias=b,return_invalid=True)
    paths=np.ascontiguousarray(tr.transpose(1,0,2));del tr
    shape=(len(cases),nt,pop);score=np.empty(shape);passed=np.empty(shape,dtype=bool);details={}
    for ci,(height,_,bias,_) in enumerate(cases):
        for ti,tag in enumerate(tags):
            for p in range(pop):
                idx=ci*count+ti*pop+p
                r=(dict(passed=False,score=-10000.,invalid_reason=str(invalid[idx])) if invalid[idx]
                   else metrics(paths[idx],tag,height,bias,assess))
                score[ci,ti,p]=r["score"];passed[ci,ti,p]=r["passed"]
                if keep:details[ci,ti,p]=r
    return score,passed,details

def rank(scores,passes):
    return 120*passes.mean(axis=0)+.5*scores.mean(axis=0)+.5*np.quantile(scores,.15,axis=0)

def make_batch(worlds,cond):
    return Batch(worlds,**cond.options(),nconmax=64,njmax=384)

def train(seed, stop_at=None, auxiliary=False, yield_file=None):
    import fcntl
    prefix=ROOT/f"seed_{seed}";prefix.mkdir(exist_ok=True)
    owner=(prefix/"worker.lock").open("a");fcntl.flock(owner,fcntl.LOCK_EX)
    if (prefix/"final.json").is_file():return
    if yield_file is not None and yield_file.exists():return
    setup()
    ref,_=baselines();lo,hi=LIMITS[:,None,:,0],LIMITS[:,None,:,1];span=hi-lo
    mean=ref.copy();std=np.broadcast_to(.18*span,mean.shape).copy()
    incumbent=ref.copy();champion=ref.copy();champion_rank=np.full(2,-1e6)
    start=0;recent=[];rng=np.random.default_rng(seed);ck=prefix/"optimizer.json"
    if ck.exists():
        s=json.loads(ck.read_text());start=s["completed"];rng.bit_generator.state=s["rng"]
        mean,std,incumbent,champion,champion_rank=[np.array(s[k]) for k in ("mean","std","incumbent","champion","champion_rank")]
        recent=s["recent"]
    batches=[make_batch(4*2*POP,c) for c in TRAIN]
    dev_batch=make_batch(len(DEV_CASES)*2*4,DEV)
    end=GENERATIONS if stop_at is None else min(stop_at,GENERATIONS)
    for gen in range(start,end):
        tick=time.monotonic()
        if gen%BLOCK==0:std=np.maximum(std,.095*span)
        # Half of the sampled change is shared between adjacent height anchors.
        noise=(.70*rng.normal(size=(2,POP,1,6))+.72*rng.normal(size=(2,POP,3,6)))
        bank=np.clip(mean[:,None]+std[:,None]*noise,lo[:,None],hi[:,None])
        bank[:,0]=ref;bank[:,1]=incumbent;bank[:,2]=champion;bank[:,3]=mean
        scores=[];passes=[]
        for env,batch in enumerate(batches):
            vals,ok,_=simulate(batch,bank,TAGS,settings(seed,gen,env));scores.append(vals);passes.append(ok)
        ok=np.concatenate(passes);fitness=rank(np.concatenate(scores),ok)
        for j in range(2):
            order=np.argsort(fitness[j]);elite=bank[j,order[-16:]]
            mean[j]=.24*mean[j]+.76*elite.mean(axis=0)
            std[j]=np.maximum(.035*span[j],.24*std[j]+.76*elite.std(axis=0))
            incumbent[j]=bank[j,order[-1]]
        if gen==0 or (gen+1)%BLOCK==0:
            finalists=np.stack([ref,champion,incumbent,mean],axis=1)
            scores_dev,p_dev,_=simulate(dev_batch,finalists,TAGS,DEV_CASES)
            # One additional passed development case outweighs sub-threshold score improvements.
            quality=1000*p_dev.sum(axis=0)+np.clip(rank(scores_dev,p_dev),-400,400)
            for j,k in enumerate(quality.argmax(axis=1)):
                if quality[j,k]>=champion_rank[j]:
                    champion[j]=finalists[j,k];champion_rank[j]=quality[j,k]
        recent=(recent+[time.monotonic()-tick])[-20:];sec=float(np.median(recent))
        save(ck,dict(completed=gen+1,mean=mean.tolist(),std=std.tolist(),incumbent=incumbent.tolist(),
                     champion=champion.tolist(),champion_rank=champion_rank.tolist(),recent=recent,rng=rng.bit_generator.state))
        snap=dict(seed=seed,completed=gen+1,target=GENERATIONS,seconds_per_gen=sec,epoch=time.time(),
                  remaining_all_generations=(len(SEEDS)-SEEDS.index(seed))*GENERATIONS-gen-1,
                  training_best_passes_of_8={name:int(ok[:,j,fitness[j].argmax()].sum()) for j,name in enumerate(TASKS)})
        save(prefix/"progress.json",snap)
        if not auxiliary:save(ROOT/"progress.json",snap)
        if gen==0 or (gen+1)%50==0:print("generation",gen+1,"seconds",round(sec,2),flush=True)
        if yield_file is not None and yield_file.exists() and gen+1<GENERATIONS:return
    if end==GENERATIONS:
        save(prefix/"final.json",dict(seed=seed,anchors_m=KNOTS,champion=champion.tolist(),development_rank=champion_rank.tolist()))

def validate():
    setup();ref,axle=baselines()
    seeds=[json.loads((ROOT/f"seed_{s}"/"final.json").read_text()) for s in SEEDS]
    winners=np.argmax(np.array([s["development_rank"] for s in seeds]),axis=0)
    selected=np.array([seeds[k]["champion"][j] for j,k in enumerate(winners)])
    tags=(10,15,15,11,11);labels=("axle_reference","short_ascent","long_ascent","short_descent","long_descent")
    bank=np.stack([np.tile(axle,(3,1)),ref[0],selected[0],ref[1],selected[1]])[:,None]
    rows=[]
    for cond in CHALLENGES:
        batch=make_batch(len(TEST_CASES)*len(tags),cond)
        _,_,records=simulate(batch,bank,tags,TEST_CASES,True)
        for ci,(h,y,b,est) in enumerate(TEST_CASES):
            opts=interpolate(bank,est);result={}
            for ti,(tag,label) in enumerate(zip(tags,labels)):
                native=metrics(replay(tag,opts[ti,0],h,**cond.options(),yaw_deg=y,edge_bias=b),tag,h,b,assess)
                gpu=records[ci,ti,0];result[label]=dict(native=native,gpu=gpu,passed_both=bool(native["passed"] and gpu["passed"]))
            rows.append(dict(dynamics=cond.options(),height_m=h,yaw_deg=y,edge_bias_m=b,estimated_height_m=est,policies=result))
            save(ROOT/"validation_progress.json",dict(cases_done=len(rows),cases_total=len(TEST_CASES)*len(CHALLENGES)))
        del batch
    save(ROOT/"final.json",dict(episodes=GENERATIONS*len(SEEDS)*POP*2*8,
         selected_seeds={name:SEEDS[k] for name,k in zip(TASKS,winners)},anchors_m=KNOTS,coefficients=selected.tolist(),cases=rows))

def queue(auxiliary=False, extra_seed=None):
    import fcntl
    lane=f"extra_{extra_seed}" if extra_seed is not None else "parallel_queue" if auxiliary else "queue"
    lock=(ROOT/f"{lane}.lock").open("a");fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    jobs=([str(extra_seed)] if extra_seed is not None else
          [str(s) for s in reversed(SEEDS[2:])] if auxiliary else [str(s) for s in SEEDS]+["validate"])
    yield_file=ROOT/f"{lane}.yield" if extra_seed is not None else None
    state=dict(submitted_epoch=time.time(),jobs={j:"queued" for j in jobs},episodes=GENERATIONS*len(SEEDS)*POP*2*8)
    def publish():save(ROOT/f"{lane}.json",state)
    publish()
    for job in jobs:
        if job=="validate" and any(state["jobs"][str(s)]!="complete" for s in SEEDS):
            state["jobs"][job]="blocked_by_failed_seed";publish();break
        done=ROOT/"final.json" if job=="validate" else ROOT/f"seed_{job}"/"final.json"
        for attempt in range(2):
            if done.exists():break
            state["jobs"][job]="running";publish()
            log_name=f"{lane}.log" if extra_seed is not None else f"parallel_{job}.log" if auxiliary else f"{job}.log"
            args=["extra-worker",job] if extra_seed is not None else ["parallel",job] if auxiliary else [job]
            with (ROOT/log_name).open("a",buffering=1) as log:
                process=subprocess.Popen([sys.executable,"-u",str(Path(__file__).resolve()),*args],
                                         stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                warnings=0
                for line in process.stdout:
                    if "Warning: opt.ccd_iterations" in line:
                        warnings+=1
                        if warnings==1 or warnings%1000==0:log.write(f"CCD iteration warnings: {warnings}\n")
                    else:log.write(line)
                code=process.wait();log.write(f"exit={code}, CCD iteration warnings={warnings}\n")
            if code==0 and done.exists():break
            if code==0 and yield_file is not None and yield_file.exists():break
        state["jobs"][job]=("complete" if done.exists() else "parked" if yield_file is not None and yield_file.exists() else "failed");publish()
    return int(any(v not in ("complete","parked") for v in state["jobs"].values()))

def status():
    files=[ROOT/"queue.json",ROOT/"parallel_queue.json",*(ROOT/f"extra_{s}.json" for s in SEEDS)]
    lanes=[json.loads(p.read_text())["jobs"] for p in files if p.exists()]
    seeds={}
    for s in SEEDS:
        base=ROOT/f"seed_{s}"
        progress=json.loads((base/"progress.json").read_text()) if (base/"progress.json").exists() else {}
        states=[lane.get(str(s)) for lane in lanes]
        state="complete" if (base/"final.json").exists() else "running" if "running" in states else "failed" if "failed" in states else "queued"
        seeds[s]=dict(state=state,completed=progress.get("completed",0),target=GENERATIONS)
    print(json.dumps(dict(seeds=seeds,validation=lanes[0].get("validate") if lanes else None,
                          final_report=(ROOT/"final.json").is_file()),indent=2))

if __name__=="__main__":
    action=sys.argv[1]
    if action=="queue":sys.exit(queue())
    if action=="assist":sys.exit(queue(auxiliary=True))
    if action in ("extra","extra-worker"):
        seed=int(sys.argv[2])
        if seed not in SEEDS:raise ValueError("Unknown campaign seed")
        if action=="extra":sys.exit(queue(auxiliary=True,extra_seed=seed))
        train(seed,auxiliary=True,yield_file=ROOT/f"extra_{seed}.yield");sys.exit(0)
    if action=="status":status();sys.exit(0)
    if action=="validate":validate()
    elif action=="parallel":train(int(sys.argv[2]),stop_at=int(sys.argv[3]) if len(sys.argv)>3 else None,auxiliary=True)
    else:train(int(action))
