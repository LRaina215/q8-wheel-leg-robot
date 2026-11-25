"""Train fixed Q8 motion skills with clipped PPO and evaluate on untouched cases."""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import train_highstep_ppo as ppo
from night_tasks import configuration,OPTIONS,PRETRAIN,casebank
from night_env import Sim
from night_native import replay

ROOT=Path(__file__).resolve().parent.parent
RUN=Path.cwd()
ppo.HERE=RUN
sys.path.append(str(ROOT/"export_deps"))

def save(name,data):ppo.write_json(name,data)

def summarize(r,c):
    out={}
    for key in np.unique(c["key"]):
        idx=c["key"]==key
        out[str(key)]=dict(n=int(idx.sum()),clean=int(r["clean"][idx].sum()),reached=int(r["reached"][idx].sum()),
            valid=int(r["valid"][idx].sum()),stable=int(r["stable"][idx].sum()),
            median={k:round(float(np.median(np.nan_to_num(v[idx],nan=0.,posinf=0.,neginf=0.))),4)
                    for k,v in r.items() if v.dtype.kind not in "b" and k!="valid"})
    return out

def rollout(env,net,seed):
    o=env.reset(seed)
    total=np.zeros(env.n)
    for _ in range(env.H):
        o,r=env.step(np.tanh(ppo.forward(net,o)[0]))
        total+=r
    return summarize(env.result,env.c),float(total.mean())

def summarize_score(by,avg):
    return (100000*sum(r["clean"] for r in by.values())+
            100*sum(r["reached"] for r in by.values())+np.clip(avg,-99.,99.))

def train(args):
    rng=np.random.default_rng(args.seed)
    config=configuration(args.task,args.variant)
    env=Sim(args.task,args.worlds,config,blind_recovery=args.task=="recover" and args.variant==1)
    actor=ppo.make_net(rng,8,.035)
    critic=ppo.make_net(rng,1,1.)
    if args.task in PRETRAIN:
        with np.load(ROOT/"code"/"step_initial.npz") as init:
            for i,w in enumerate(actor):w[:]=init["actor%d"%i]
    ao,co=ppo.Adam(actor),ppo.Adam(critic)
    start=0; best=-1e20
    if (RUN/"checkpoint_latest.npz").exists():
        with np.load(RUN/"checkpoint_latest.npz") as f:
            start=int(f["iteration"]);best=float(f["best"])
            for i,w in enumerate(actor):
                w[:]=f["actor%d"%i];critic[i][:]=f["critic%d"%i]
            for key,opt in (("a",ao),("c",co)):
                opt.step=int(f[key+"step"])
                for name,seq in (("m",opt.m),("v",opt.v)):
                    for i,w in enumerate(seq):w[:]=f[key+name+str(i)]
            rng.bit_generator.state=json.loads(str(f["rng"]))
        if (RUN/"best_eval.json").exists():best=max(best,json.loads((RUN/"best_eval.json").read_text())["rank"])
    save("run_spec.json",dict(task=args.task,seed=args.seed,worlds=env.n,updates=args.updates,steps_per_episode=env.H,
        mass_kg=env.mass,config=config,policy_period_s=.04,physics_period_s=.002,cases=OPTIONS[args.task],
        initialized_from="12cm successful ascent actor" if args.task in PRETRAIN else "small residual over analytic reference",
        output="actor_best.onnx plus commands() in night_tasks.py; native tests use the same decoder",
        recover_protocol="first variant cued; second variant blind with random impulse time; all final recovery tests are blind"))
    if start==0:
        base,ret=rollout(env,actor,812570)
        save("starting_eval.json",dict(by_command=base,avg_return=ret))
    stop=min(args.stop_at or args.updates,args.updates)
    for it in range(start+1,stop+1):
        tic=time.monotonic()
        o=env.reset(int(rng.integers(0,2**31)))
        buf=[[] for _ in range(5)]
        sd=(.26 if args.task in PRETRAIN else .43)*(.52+.48*max(0.,1.-it/(.8*args.updates)))
        for k in range(env.H):
            mu=ppo.forward(actor,o)[0]
            v=ppo.forward(critic,o)[0][:,0]
            u=mu+sd*(rng.standard_normal(mu.shape,dtype=np.float32)@ppo.chol.T)
            lp=ppo.logprob(u-mu,sd)
            nxt,reward=env.step(np.tanh(u))
            for b,z in zip(buf,(o,u,lp,v,reward)):b.append(z)
            o=nxt
        x,u,lp,val,rew=map(np.stack,buf)
        adv,ret=ppo.advantages(rew,val)
        old=actor[4].copy()
        diag=ppo.train_update(actor,critic,ao,co,x,u,lp,adv,ret,rng,sd)
        delta=float(np.linalg.norm(actor[4]-old))
        if delta==0 or not np.isfinite([delta,*diag.values()]).all():raise RuntimeError("nonfinite or static PPO update")
        rec=dict(iteration=it,transitions=it*env.n*env.H,actor_delta=delta,**diag,
                 mean_return=float(rew.sum(0).mean()),training=summarize(env.result,env.c))
        if it==1 or it%40==0 or it==args.updates:
            by,mean=rollout(env,actor,812570)
            rank=float(summarize_score(by,mean))
            rec["development"]=by
            if rank>best:
                best=rank
                ppo.checkpoint(actor,critic,ao,co,rng,it,best,"best")
                rec["onnx_best_err"]=ppo.export_onnx(actor,"actor_best.onnx",x[0,:8])
                save("best_eval.json",dict(rank=rank,iteration=it,by_command=by))
        if it<=2 or it%10==0 or it==args.updates:
            ppo.checkpoint(actor,critic,ao,co,rng,it,best,"latest")
            rec["onnx_latest_err"]=ppo.export_onnx(actor,"actor_latest.onnx",x[0,:8])
        rec.update(seconds=round(time.monotonic()-tic,3),unix=time.time())
        save("progress.json",rec)
        with open("learning.jsonl","a",encoding="utf8") as f:f.write(json.dumps(rec,allow_nan=False)+"\n")
        print("update",it,round(rec["mean_return"],2),round(delta,5),rec["seconds"],flush=True)
    if stop==args.updates:
        save("finished.json",dict(iteration=stop,transitions=stop*env.n*env.H,unix=time.time()))

def verify(args):
    import onnx
    from onnx.reference import ReferenceEvaluator
    session=ReferenceEvaluator(onnx.load(str(RUN/"actor_best.onnx")))
    def actor(x):return session.run(None,{"obs":x})[0]
    if args.probe:
        domains=[0];n=2
    else:
        domains=range(4 if args.task=="brake" else 2)
        n=4*len(OPTIONS[args.task])
    rows=[]
    for dom in domains:
        cfg=configuration(args.task,dom,True)
        env=Sim(args.task,n,cfg,blind_recovery=args.task=="recover")
        cseed=(378150 if args.probe else 976403)+dom*17
        o=env.reset(cseed)
        for _ in range(env.H):o,_=env.step(actor(o))
        for j in range(n):
            c={k:v[j:j+1] for k,v in env.c.items()}
            native=replay(args.task,cfg,c,actor)
            gpu={k:v[j].item() for k,v in env.result.items()}
            rows.append(dict(domain=dom,mass_kg=env.mass,mu=cfg[1],grade_deg=cfg[3],
                 command=int(c["key"][0]),case={k:float(v[0]) for k,v in c.items()},
                 gpu=gpu,native=native,both=bool(gpu["clean"] and native["clean"])))
        del env
        gc.collect()
    save("smoke_native.json" if args.probe else "acceptance.json",dict(task=args.task,seed=args.seed,
         selected_iteration=json.loads((RUN/"best_eval.json").read_text())["iteration"],
         cases=len(rows),gpu=sum(r["gpu"]["clean"] for r in rows),native=sum(r["native"]["clean"] for r in rows),
         passed_both=sum(r["both"] for r in rows),rows=rows,unix=time.time()))
    print("native validation",len(rows),"matched cases",sum(r["both"] for r in rows),"passed both",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["train","validate"])
    parser.add_argument("task",choices=OPTIONS)
    parser.add_argument("--variant",type=int,required=True)
    parser.add_argument("--seed",type=int,required=True)
    parser.add_argument("--worlds",type=int,default=160)
    parser.add_argument("--updates",type=int,default=1100)
    parser.add_argument("--stop-at",type=int)
    parser.add_argument("--probe",action="store_true")
    args=parser.parse_args()
    if (ROOT/"night_plan.json").exists():
        plan=json.loads((ROOT/"night_plan.json").read_text())
        args.updates=min(args.updates,plan["tasks"][args.task][args.variant])
    if args.mode=="train":train(args)
    else:verify(args)
