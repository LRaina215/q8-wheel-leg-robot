"""PPO with clipped Gaussian policy updates and generalized advantage estimation."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from ppo_highstep_env import Env, HEIGHTS, HERE, HORIZON, NOBS, PERIOD, TICKS


def write_json(name,data):
    tmp=HERE/(name+".tmp")
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf8")
    os.replace(tmp,HERE/name)


def make_net(rng,nout,output_gain):
    widths=[NOBS,64,64,nout]
    net=[]
    for i,(a,b) in enumerate(zip(widths,widths[1:])):
        gain=output_gain if i==2 else np.sqrt(2.)
        net.extend([(rng.normal(size=(a,b))*gain/np.sqrt(a)).astype(np.float32),np.zeros(b,np.float32)])
    return net


def forward(net,x):
    h=np.tanh(x@net[0]+net[1])
    k=np.tanh(h@net[2]+net[3])
    return k@net[4]+net[5],(x,h,k)


def backward(net,cache,dy):
    x,h,k=cache
    dk=(dy@net[4].T)*(1-k*k)
    dh=(dk@net[2].T)*(1-h*h)
    return [x.T@dh,dh.sum(0),h.T@dk,dk.sum(0),k.T@dy,dy.sum(0)]


class Adam:
    def __init__(self,net):
        self.m=[np.zeros_like(p) for p in net]
        self.v=[np.zeros_like(p) for p in net]
        self.step=0

    def apply(self,net,grads,lr):
        self.step+=1
        norm=np.sqrt(sum(float(np.square(g).sum()) for g in grads))
        factor=min(1.,.5/max(1e-10,norm))
        for p,g,m,v in zip(net,grads,self.m,self.v):
            g=g*factor
            m*=.9
            m+=.1*g
            v*=.999
            v+=.001*g*g
            p-=lr*(m/(1.-.9**self.step))/(np.sqrt(v/(1.-.999**self.step))+1e-7)


# Adjacent left/right actuators explore common and differential motions. The
# covariance is fixed inside each PPO update, including in the log density.
cov=np.eye(8,dtype=np.float32)
for i in (0,2,4,6):
    cov[i,i+1]=cov[i+1,i]=.64
chol=np.linalg.cholesky(cov)
precision=np.linalg.inv(cov)


def logprob(diff,sd):
    # The additive normalizer is the same for old and new policies.
    return -.5*((diff@precision)*diff).sum(axis=-1)/(sd*sd)


def advantages(rew,val):
    gae=np.zeros_like(rew[0])
    out=np.empty_like(rew)
    next_value=np.zeros_like(gae)
    for t in reversed(range(len(rew))):
        gae=rew[t]+.99*next_value-val[t]+(.99*.95)*gae
        out[t]=gae
        next_value=val[t]
    return out,(out+val)


def train_update(actor,critic,aopt,copt,obs,u,old,adv,ret,rng,sd):
    obs=obs.reshape(-1,NOBS)
    u=u.reshape(-1,8)
    old=old.ravel()
    ret=ret.ravel()
    adv=adv.ravel()
    adv=(adv-adv.mean())/(adv.std()+1e-7)
    diag=[]
    for epoch in range(4):
        order=rng.permutation(len(old))
        for start in range(0,len(order),1024):
            ids=order[start:start+1024]
            x=obs[ids]
            mu,cache=forward(actor,x)
            diff=u[ids]-mu
            shift=logprob(diff,sd)-old[ids]
            ratio=np.exp(np.clip(shift,-20.,20.))
            a=adv[ids]
            active=((a>=0)&(ratio<=1.2))|((a<0)&(ratio>=.8))
            dy=(-a*ratio*active/len(ids))[:,None]*(diff@precision)/(sd*sd)
            aopt.apply(actor,backward(actor,cache,dy),.00020)
            v,vc=forward(critic,x)
            err=v[:,0]-ret[ids]
            copt.apply(critic,backward(critic,vc,np.clip(err,-5,5)[:,None]/len(ids)),.00065)
            diag.append([np.mean((ratio-1.)-shift),np.mean(abs(ratio-1.)>.2),np.mean(err*err)])
        if np.mean(np.asarray(diag)[-(len(order)+1023)//1024:,0])>.035: break
    return dict(zip(("approx_kl","clip_fraction","value_mse"),np.mean(diag,axis=0).tolist()))


def export_onnx(actor,name,obs):
    # ONNX dependencies live in the job directory. Keep the physics environment intact.
    sys.path.append(str(HERE/"export_deps"))
    import onnx
    from onnx import helper, numpy_helper, TensorProto
    from onnx.reference import ReferenceEvaluator
    nodes=[]
    tensors=[]
    x="obs"
    for i in range(3):
        w,b="W%d"%i,"B%d"%i
        tensors.extend([numpy_helper.from_array(actor[2*i],w),numpy_helper.from_array(actor[2*i+1],b)])
        out="a%d"%i
        y="action" if i==2 else "h%d"%i
        nodes.extend([helper.make_node("Gemm",[x,w,b],[out]),helper.make_node("Tanh",[out],[y])])
        x=y
    graph=helper.make_graph(nodes,"q8_highstep",
              [helper.make_tensor_value_info("obs",TensorProto.FLOAT,["batch",NOBS])],
              [helper.make_tensor_value_info("action",TensorProto.FLOAT,["batch",8])],tensors)
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid("",13)])
    model.ir_version=8
    onnx.checker.check_model(model)
    expected=np.tanh(forward(actor,obs)[0])
    actual=ReferenceEvaluator(model).run(None,{"obs":obs})[0]
    error=float(np.max(np.abs(expected-actual)))
    if error>1e-5: raise ValueError("ONNX numerical mismatch %g"%error)
    tmp=HERE/(name+".tmp")
    onnx.save(model,str(tmp))
    os.replace(tmp,HERE/name)
    return error


def checkpoint(actor,critic,aopt,copt,rng,iteration,best,tag):
    data={"actor%d"%i:x for i,x in enumerate(actor)}
    data.update({"critic%d"%i:x for i,x in enumerate(critic)})
    for label,opt in (("a",aopt),("c",copt)):
        for group,seq in (("m",opt.m),("v",opt.v)):
            data.update({label+group+str(i):v for i,v in enumerate(seq)})
        data[label+"step"]=opt.step
    data.update(iteration=iteration,best=best,rng=json.dumps(rng.bit_generator.state))
    path=HERE/("checkpoint_"+tag+".npz")
    with open(str(path)+".tmp","wb") as f: np.savez(f,**data)
    os.replace(str(path)+".tmp",path)


def breakdown(env):
    s=env.result
    by={}
    for h in HEIGHTS:
        mask=env.height_mm==h
        by[str(h)]=dict(n=int(mask.sum()),atop=int(s["atop"][mask].sum()),
                        clean=int(s["clean"][mask].sum()),invalid=int(s["invalid"][mask].sum()),
                        mean_front_past_edge_mm=round(float(np.nan_to_num(s["terminal_front_x"][mask]).mean()*1000),1))
    return by


def evaluate(env,actor):
    # Fixed, separate seed. Deterministic action, held-out edge/yaw/actuator variations.
    rng=np.random.default_rng(970214)
    o=env.reset(rng)
    for _ in range(HORIZON): o,_=env.step(np.tanh(forward(actor,o)[0]))
    return breakdown(env)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--worlds",type=int,default=224)
    parser.add_argument("--updates",type=int,default=1200)
    parser.add_argument("--seed",type=int,default=241106)
    parser.add_argument("--resume",action="store_true")
    opt=parser.parse_args()
    rng=np.random.default_rng(opt.seed)
    env=Env(opt.worlds)
    actor=make_net(rng,8,.055)
    critic=make_net(rng,1,1.)
    aopt,copt=Adam(actor),Adam(critic)
    best=-np.inf
    start=0
    if opt.resume:
        f=np.load(HERE/"checkpoint_latest.npz",allow_pickle=False)
        for i in range(len(actor)):
            actor[i][:]=f["actor%d"%i]
            critic[i][:]=f["critic%d"%i]
        for label,optimizer in (("a",aopt),("c",copt)):
            optimizer.step=int(f[label+"step"])
            for group,seq in (("m",optimizer.m),("v",optimizer.v)):
                for i,p in enumerate(seq): p[:]=f[label+group+str(i)]
        rng.bit_generator.state=json.loads(str(f["rng"]))
        start=int(f["iteration"])
        best=float(f["best"])
    write_json("run_spec.json",dict(worlds=env.n,updates=opt.updates,seed=opt.seed,mass_kg=env.mass,
        heights_mm=HEIGHTS.tolist(),physics_s=PERIOD/TICKS,policy_s=PERIOD,episode_s=PERIOD*HORIZON,
        friction=.64,torque_scale=[.90,1.0],yaw_deg=[-3,3],edge_estimate_error_mm=[-8,8],
        height_estimate_error_mm=[-4,4],control="33 inputs, two 64-unit tanh layers, eight normalized outputs",
        annotations="single square step; terminal hold 360 ms; 0.8 mm solver residual; 2 N structure contact",
        observation="0:(estimated edge minus estimated base x)*2; 1:y*3; 2:4:R20,R21,R10; 5:6:vx,vy world; 7:9:local angular velocity * .25; 10:13:(hip angle + .12217305)*2; 14:17:hip speed*.2; 18:21:wheel speed*.08; 22:estimated height*10; 23:elapsed/4; 24:31:previous action; 32:max(0,1-abs(obs[0]-.40)*3); clip all to [-5,5]",
        actions="FL FR RL RR; indices 0..3 set hip degrees = -7+29*a; indices 4..7 wheel tread speed m/s = .22+.40*a"))
    last_eval=None
    begin=time.monotonic()
    print("initialized",env.mass,"kg;",env.n,"parallel worlds",flush=True)
    for iteration in range(start+1,opt.updates+1):
        tic=time.monotonic()
        obs=env.reset(rng)
        buf=[[] for _ in range(5)]
        sd=.40+.30*max(0.,1.-(iteration-1)/(.80*opt.updates))
        for t in range(HORIZON):
            mu=forward(actor,obs)[0]
            v=forward(critic,obs)[0][:,0]
            u=mu+sd*(rng.standard_normal(mu.shape,dtype=np.float32)@chol.T)
            action=np.tanh(u)
            lp=logprob(u-mu,sd)
            nobs,reward=env.step(action)
            for b,item in zip(buf,(obs,u,lp,v,reward)): b.append(item)
            obs=nobs
        x,u,lp,val,rew=map(np.stack,buf)
        adv,ret=advantages(rew,val)
        old_w=actor[4].copy()
        diagnostics=train_update(actor,critic,aopt,copt,x,u,lp,adv,ret,rng,sd)
        delta=float(np.linalg.norm(actor[4]-old_w))
        if not np.isfinite(delta) or delta==0 or not np.isfinite(list(diagnostics.values())).all():
            raise RuntimeError("invalid PPO update")
        metrics=dict(iteration=iteration,transitions=iteration*env.n*HORIZON,mean_return=float(rew.sum(0).mean()),
                     actor_output_layer_delta_l2=delta,**diagnostics,training=breakdown(env))
        if iteration==1 or iteration%20==0 or iteration==opt.updates:
            last_eval=evaluate(env,actor)
            metrics["heldout"]=last_eval
            # Treat invalid worlds as failures. Break pass-count ties by partial progress.
            score=sum(10000*r["clean"]+100*r["atop"]+.001*r["mean_front_past_edge_mm"] for r in last_eval.values())
            if score>best:
                best=score
                checkpoint(actor,critic,aopt,copt,rng,iteration,best,"best")
                metrics["best_export_abs_error"]=export_onnx(actor,"actor_best.onnx",x[0,:8])
                write_json("best_eval.json",dict(iteration=iteration,by_height=last_eval))
        if iteration<=2 or iteration%5==0 or iteration==opt.updates:
            checkpoint(actor,critic,aopt,copt,rng,iteration,best,"latest")
            metrics["export_abs_error"]=export_onnx(actor,"actor_latest.onnx",x[0,:8])
        metrics["seconds"]=round(time.monotonic()-tic,3)
        metrics["elapsed_s"]=round(time.monotonic()-begin,3)
        metrics["timestamp_unix"]=time.time()
        with open(HERE/"learning.jsonl","a",encoding="utf8") as f:
            f.write(json.dumps(metrics,allow_nan=False)+"\n")
        write_json("progress.json",metrics)
        print("update",iteration,"return",round(metrics["mean_return"],2),"KL",round(diagnostics["approx_kl"],4),
              "atop",sum(r["atop"] for r in metrics["training"].values()),"seconds",metrics["seconds"],flush=True)
    write_json("finished.json",dict(updates=opt.updates,transitions=opt.updates*env.n*HORIZON,heldout=last_eval))


if __name__=="__main__": main()
