"""Learn a height-conditioned flat-ground jump with clipped PPO and a calibrated reference."""
import argparse
import json
import time
import numpy as np
from ppo_flatjump_env import JumpEnv
from flatjump_policy_io import GOALS,HORIZON,DT,DECIMATION
from train_highstep_ppo import (HERE,Adam,advantages,checkpoint,chol,export_onnx,forward,
                                logprob,make_net,train_update,write_json)


def report(env):
    r=env.result
    out={}
    for h in GOALS:
        m=env.goals==h
        def med(key): return round(float(np.median(np.nan_to_num(r[key][m]))),3)
        out[str(h)]=dict(n=int(m.sum()),valid=int(r["valid"][m].sum()),
            airborne=int(((r["flight_ms"][m]>=20)&r["valid"][m]).sum()),
            stable=int((r["stable"][m]&r["valid"][m]).sum()),clean=int(r["clean"][m].sum()),
            com_rise_median_mm=med("com_rise_mm"),tire_median_mm=med("tire_mm"),
            flight_median_ms=med("flight_ms"),rebound_median_ms=med("rebound_ms"),
            peak_landing_force_median_N=med("contact_peak_N"),closure_median_mm=med("residual_mm"))
    return out


def evaluate(env,actor=None):
    o=env.reset_jump(np.random.default_rng(783909))
    for _ in range(HORIZON):
        a=np.zeros((env.n,8),np.float32) if actor is None else np.tanh(forward(actor,o)[0])
        o,_=env.step_jump(a)
    return report(env)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",required=True,type=int)
    parser.add_argument("--worlds",type=int,default=256)
    parser.add_argument("--updates",type=int,default=1200)
    parser.add_argument("--extra",type=float,required=True)
    parser.add_argument("--friction",type=float,required=True)
    opt=parser.parse_args()
    rng=np.random.default_rng(opt.seed)
    env=JumpEnv(opt.worlds,opt.extra,opt.friction)
    actor=make_net(rng,8,.055)
    critic=make_net(rng,1,1.)
    ao,co=Adam(actor),Adam(critic)
    best=-np.inf
    spec=dict(task="standing vertical jump on flat ground",seed=opt.seed,worlds=env.n,updates=opt.updates,
              mass_kg=env.mass,extra_kg=opt.extra,friction=opt.friction,torque_scale=[.89,1.0],
              goals_com_rise_from_liftoff_mm=GOALS.tolist(),physics_dt=DT,controller_dt=DT*DECIMATION,
              episode_s=HORIZON*DECIMATION*DT,algorithm="clipped PPO, GAE, 2x64 tanh, 8 actions",
              interface="flatjump_policy_io.py: observations at 50 Hz, residual ONNX then commands at 500 Hz",
              acceptance="first completed >=20 ms all-wheels-off contact interval; COM goal within max(3 mm,20%); all four tyre clearance >=10 mm; rebound <=30 ms; no non-wheel terrain force >=2 N; closure <0.8 mm; last 350 ms >95% four tyres loaded, tilt <=5 deg, speed <.1 m/s, lateral/longitudinal drift norm <.075 m")
    write_json("run_spec.json",spec)
    write_json("reference_eval.json",evaluate(env))
    begin=time.monotonic()
    for it in range(1,opt.updates+1):
        tic=time.monotonic()
        obs=env.reset_jump(rng)
        buffers=[[] for _ in range(5)]
        sd=.22+.29*max(0.,1.-(it-1)/(.85*opt.updates))
        for _ in range(HORIZON):
            mu=forward(actor,obs)[0]
            v=forward(critic,obs)[0][:,0]
            u=mu+sd*(rng.standard_normal(mu.shape,dtype=np.float32)@chol.T)
            lp=logprob(u-mu,sd)
            next_obs,reward=env.step_jump(np.tanh(u))
            for b,item in zip(buffers,(obs,u,lp,v,reward)): b.append(item)
            obs=next_obs
        x,u,lp,val,rew=map(np.stack,buffers)
        adv,ret=advantages(rew,val)
        saved=actor[4].copy()
        diag=train_update(actor,critic,ao,co,x,u,lp,adv,ret,rng,sd)
        delta=float(np.linalg.norm(actor[4]-saved))
        if delta==0. or not np.isfinite([delta,*diag.values()]).all(): raise ValueError("invalid PPO update")
        item=dict(iteration=it,transitions=it*env.n*HORIZON,training=report(env),
                  mean_return=float(rew.sum(0).mean()),actor_output_layer_delta_l2=delta,**diag)
        if it==1 or it%20==0 or it==opt.updates:
            e=evaluate(env,actor)
            item["heldout"]=e
            score=sum(v["clean"]*1000+v["airborne"]*.1-abs(float(h)-v["com_rise_median_mm"]) for h,v in e.items())
            if score>best:
                best=score
                checkpoint(actor,critic,ao,co,rng,it,best,"best")
                item["best_export_abs_error"]=export_onnx(actor,"jump_residual_best.onnx",x[0,:8])
                write_json("best_eval.json",dict(iteration=it,by_height=e))
        if it<=2 or it%5==0 or it==opt.updates:
            checkpoint(actor,critic,ao,co,rng,it,best,"latest")
            item["export_abs_error"]=export_onnx(actor,"jump_residual_latest.onnx",x[0,:8])
        item["seconds"]=round(time.monotonic()-tic,3)
        item["elapsed_s"]=round(time.monotonic()-begin,3)
        item["timestamp_unix"]=time.time()
        with open(HERE/"learning.jsonl","a") as f: f.write(json.dumps(item,allow_nan=False)+"\n")
        write_json("progress.json",item)
        print("update",it,"return",round(item["mean_return"],2),"KL",round(diag["approx_kl"],5),
              "seconds",item["seconds"],flush=True)
    write_json("finished.json",dict(updates=opt.updates,transitions=opt.updates*env.n*HORIZON,heldout=e))


if __name__=="__main__": main()
