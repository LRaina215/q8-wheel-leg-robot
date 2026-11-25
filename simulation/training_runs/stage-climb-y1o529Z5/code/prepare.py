"""Adapt private copies of the established PPO and native rollout entry points."""
from pathlib import Path
p=Path(__file__).resolve().parent
def edit(src,dst,replacements):
    s=(p/src).read_text()
    for a,b in replacements:
        if s.count(a)!=1:raise ValueError(a)
        s=s.replace(a,b)
    (p/dst).write_text(s)
edit('night_train.py','stage_ppo.py',[
    ('from night_env import Sim','from stage_task import Sim'),
    ('if args.task in PRETRAIN:\n        with np.load(ROOT/"code"/"step_initial.npz") as init:',
     'if os.environ.get("STAGE_MODE")=="direct":\n        with np.load(ROOT/"original"/"checkpoint_best.npz") as init:'),
    ('cases=OPTIONS[args.task]','cases=[150],mode=os.environ["STAGE_MODE"],settle_s=.24,front_axle_top_depth_m=[.08,.18]'),
    ('initialized_from="12cm successful ascent actor" if args.task in PRETRAIN else "small residual over analytic reference"',
     'initialized_from=str((ROOT/"original").resolve()) if os.environ["STAGE_MODE"]=="direct" else "small residual over phased rear lift"'),
    ('plus commands() in night_tasks.py','plus decode() in stage_task.py'),
    ('812570','812570') if False else ('if it==1 or it%40==0','if it==1 or it%20==0'),
    ('save("starting_eval.json",dict(by_command=base,avg_return=ret))','''save("starting_eval.json",dict(by_command=base,avg_return=ret))
        best=float(summarize_score(base,ret))
        ppo.checkpoint(actor,critic,ao,co,rng,0,best,"best")
        ppo.export_onnx(actor,"actor_best.onnx",env.obs[:8])
        save("best_eval.json",dict(rank=best,iteration=0,by_command=base))''')])
edit('night_native.py','stage_native.py',[
    ('def replay(task,config,c,actor):','''from stage_task import pose,decode as commands,score
from stage_signals import Signals

def replay(task,config,c,actor):'''),
    ('    for k in range(H*DEC):','    recorder=Signals(m,H*DEC)\n    for k in range(H*DEC):'),
    ('        mj.mj_step(m,d)','        pre_velocity=d.qvel.copy()\n        mj.mj_step(m,d)'),
    ('        a[30:]=d.qvel[1:3]','        a[30:]=d.qvel[1:3]\n        recorder.sample(k,m,d,ix,a,wc,pre_velocity,one)'),
    ('return {k:v[0].item() for k,v in score(task,trace,c).items()}','return {k:v[0].item() for k,v in score(task,trace,c).items()},recorder.results(trace[:,0],c)')])
