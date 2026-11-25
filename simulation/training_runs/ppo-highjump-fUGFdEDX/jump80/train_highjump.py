"""Fixed-height PPO for Q8, initialized around a native-validated jump reference."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from flatjump_policy_io import HORIZON
from ppo_flatjump_env import JumpEnv
from highjump_profile import action,gates
from train_highstep_ppo import (Adam,advantages,checkpoint,chol,export_onnx,forward,logprob,make_net,
                                train_update,write_json)

def command(profile,x,neural):
    # The deployed network exports tanh outputs; this is the exact action decoder.
    return np.clip(action(profile,x)+.72*neural,-1.,1.).astype(np.float32)

def describe(s,target):
    ok=gates(s)
    return dict(n=len(ok),mechanical=int(ok.sum()),height_and_mechanical=int((ok&(s["com_rise_mm"]>=target)).sum()),
                stable=int(s["stable"].sum()),rise_median_mm=float(np.median(s["com_rise_mm"])),
                gap_median_mm=float(np.median(s["residual_mm"])),peak_landing_median_N=float(np.median(s["contact_peak_N"])),
                rebound_median_ms=float(np.median(s["rebound_ms"])),invalid=int((~s["valid"]).sum()))

def reset(env,rng,goal):
    env.reset_jump(rng)
    env.goals.fill(goal)
    return env.observation()

def evaluate(env,actor,profile,target):
    obs=reset(env,np.random.default_rng(58309),target)
    for _ in range(HORIZON):
        obs,_=env.step_jump(command(profile,obs,np.tanh(forward(actor,obs)[0])))
    return describe(env.result,target)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--goal",type=int,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--extra",type=float,required=True)
    p.add_argument("--mu",type=float,required=True)
    p.add_argument("--worlds",type=int,default=256)
    p.add_argument("--updates",type=int,default=900)
    a=p.parse_args()
    rng=np.random.default_rng(a.seed)
    env=JumpEnv(a.worlds,a.extra,a.mu)
    profile=np.asarray(json.loads(Path("verified_profile.json").read_text())["params"])
    actor=make_net(rng,8,.02)
    critic=make_net(rng,1,1.)
    ao,co=Adam(actor),Adam(critic)
    spec=dict(target_mm=a.goal,train_mass_kg=env.mass,friction=a.mu,seed=a.seed,worlds=env.n,updates=a.updates,
              interface="33 observations; issued residual = clip(profile(obs) + .72 * ONNX(obs), -1, 1). Use flatjump_policy_io.commands at 500 Hz.",
              full_height_pass="COM rise from first liftoff >= target; all original landing and closure gates")
    write_json("run_spec.json",spec)
    best=None
    for it in range(1,a.updates+1):
        tic=time.monotonic()
        obs=reset(env,rng,a.goal)
        peak_gap=np.zeros(env.n)
        peak_force=np.zeros(env.n)
        first_air_z=np.full(env.n,np.nan)
        in_air=np.zeros(env.n,bool)
        first_done=np.zeros(env.n,bool)
        length=np.zeros(env.n,int)
        rise=np.zeros(env.n)
        prev_action=np.zeros((env.n,8),np.float32)
        buffers=[[] for _ in range(5)]
        sd=.15+.24*max(0.,1.-it/(.85*a.updates))
        for t in range(HORIZON):
            mu=forward(actor,obs)[0]
            val=forward(critic,obs)[0][:,0]
            u=mu+sd*(rng.standard_normal(mu.shape,dtype=np.float32)@chol.T)
            issued=command(profile,obs,np.tanh(u))
            next_obs,_=env.step_jump(issued)
            block=env.history[10*t:10*(t+1)]
            step_rise=rise.copy()
            if t>=10:
                for sample in block:
                    air=(sample[:,0]<.5)&(sample[:,1]>0.)&~first_done
                    start=air & ~in_air
                    first_air_z[start]=sample[start,2]
                    length[air]+=1
                    landed=~air&in_air
                    first_done|=landed&(length>=10)
                    length[landed]=0
                    active=air&(length>=3)
                    rise[active]=np.maximum(rise[active],sample[active,2]-first_air_z[active])
                    in_air=air
            # Credit an actual increase of COM during the first flight. Charge mechanical
            # penalties when they occur so the landing policy receives a local signal.
            reward=.38*(np.minimum(rise,a.goal+3)-np.minimum(step_rise,a.goal+3))
            gap=np.maximum(peak_gap,block[:,:,6].max(0)) if t>=10 else peak_gap
            reward-=35*(np.maximum(0.,gap-.76)-np.maximum(0.,peak_gap-.76))
            peak_gap=gap
            contact=block[:,:,0].max(0)
            force=np.maximum(peak_force,contact) if t>=38 else peak_force
            reward-=.017*(np.maximum(0,force-230)-np.maximum(0,peak_force-230))
            peak_force=force
            reward-=.03*np.square(issued-prev_action).mean(1)+.06*np.minimum(12.,block[:,:,5].max(0))
            if t>55:
                reward+=.04*block[:,:,7].mean(0)-.15*block[:,:,4].mean(0)-.012*block[:,:,3].mean(0)
            if t==HORIZON-1:
                s=env.result
                ok=gates(s)
                reward+=8*ok+10*(ok&(s["com_rise_mm"]>=a.goal))+3*s["stable"]-.07*np.minimum(s["rebound_ms"],80)
                reward=np.where(s["valid"],reward,-25.)
            prev_action=issued
            for b,v in zip(buffers,(obs,u,logprob(u-mu,sd),val,reward.astype(np.float32))):b.append(v)
            obs=next_obs
        x,u,lp,val,r=map(np.stack,buffers)
        adv,ret=advantages(r,val)
        original=actor[4].copy()
        diag=train_update(actor,critic,ao,co,x,u,lp,adv,ret,rng,sd)
        delta=float(np.linalg.norm(actor[4]-original))
        if not np.isfinite([delta,*diag.values()]).all() or delta==0:raise RuntimeError("invalid PPO update")
        row=dict(iteration=it,transitions=it*env.n*HORIZON,actor_delta=delta,**diag,
                 training=describe(env.result,a.goal),mean_return=float(r.sum(0).mean()))
        if it==1 or it%20==0 or it==a.updates:
            e=evaluate(env,actor,profile,a.goal)
            row["heldout"]=e
            # Prefer meeting height and landing simultaneously, then mechanically sound jumps.
            score=(e["height_and_mechanical"],e["mechanical"],min(a.goal,e["rise_median_mm"]))
            if best is None or score>best:
                best=score
                checkpoint(actor,critic,ao,co,rng,it,score[0],"best")
                row["export_error"]=export_onnx(actor,"highjump_best.onnx",x[0,:8])
                write_json("best_eval.json",dict(iteration=it,**e))
        if it<=2 or it%10==0 or it==a.updates:
            checkpoint(actor,critic,ao,co,rng,it,best[0],"latest")
            row["latest_export_error"]=export_onnx(actor,"highjump_latest.onnx",x[0,:8])
        row["seconds"]=round(time.monotonic()-tic,3)
        with open("learning.jsonl","a") as f:f.write(json.dumps(row,allow_nan=False)+"\n")
        write_json("progress.json",row)
        print("update",it,round(row["mean_return"],2),round(delta,5),row["seconds"],flush=True)
    write_json("finished.json",row)

if __name__=="__main__":main()
