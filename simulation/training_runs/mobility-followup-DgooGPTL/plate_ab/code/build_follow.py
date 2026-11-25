"""Reuse established PPO, solver and acceptance thresholds in this private experiment."""
from pathlib import Path
p=Path(__file__).resolve().parent
def edit(src,dst,changes):
    s=(p/src).read_text()
    for a,b in changes:
        if s.count(a)!=1:raise ValueError(a)
        s=s.replace(a,b)
    (p/dst).write_text(s)
edit('night_native.py','follow_native.py',[
('def replay(task,config,c,actor):','from follow_env import Controller,scored as score\n\ndef replay(task,config,c,actor):\n    ctrl=Controller();ctrl.reset(1)'),
('cmd=commands(task,o,prev)[0]','cmd=ctrl(task,o,prev)[0]'),
('        a[30:]=d.qvel[1:3]','        a[30:]=d.qvel[1:3]\n        if (k+1)%DEC==0:ctrl.contacts(trace[k-DEC+1:k+1],c["edge"])')])
edit('night_train.py','follow_ppo.py',[
('from night_env import Sim','from follow_env import Sim,LANE,TASK,HEIGHTS,CONTROL,SOURCE,ROOT as EXP'),
('from night_native import replay','from follow_native import replay'),
('if args.task in PRETRAIN:\n        with np.load(ROOT/"code"/"step_initial.npz") as init:',
 'if LANE in ("climb","down","double_down","handover"):\n        source=EXP/"snap_phase" if LANE=="handover" else SOURCE\n        with np.load(source/"checkpoint_best.npz") as init:'),
('cases=OPTIONS[args.task]','cases=HEIGHTS,lane=LANE'),
('initialized_from="12cm successful ascent actor" if args.task in PRETRAIN else "small residual over analytic reference"',
 'initialized_from=str(source) if LANE in ("climb","down","double_down","handover") else "small residual over frozen/reference controller"'),
('output="actor_best.onnx plus commands() in night_tasks.py; native tests use the same decoder"',
 'output="actor_best.onnx plus Controller in follow_env.py with its per-episode state"'),
('        o=env.reset(int(rng.integers','        env.iteration=it\n        o=env.reset(int(rng.integers'),
('if it==1 or it%40==0','if it==1 or it%20==0'),
('return (100000*sum(r["clean"]','''if LANE in ("climb","handover"):
        r=by["150"]
        return (10000000*r["clean"]+100000*r["reached"]+10000*sum(v["clean"] for v in by.values())+
                100*sum(v["reached"] for v in by.values())+np.clip(r["median"]["rear_margin_mm"],-500.,120.)/10+np.clip(avg,-10,10))
    if LANE in ("down","double_down"):
        return 100000*sum(v["clean"] for v in by.values())+100*sum(v["reached"] for v in by.values())-sum(v["median"]["under_two_ms"] for v in by.values())/10+np.clip(avg,-5,5)
    return (100000*sum(r["clean"]'''),
('save("starting_eval.json",dict(by_command=base,avg_return=ret))','''save("starting_eval.json",dict(by_command=base,avg_return=ret))
        best=float(summarize_score(base,ret))
        ppo.checkpoint(actor,critic,ao,co,rng,0,best,"best")
        ppo.export_onnx(actor,"actor_best.onnx",env.obs[:8])
        save("best_eval.json",dict(rank=best,iteration=0,by_command=base))'''),
('RUN/"actor_best.onnx"','(SOURCE if CONTROL else RUN)/"actor_best.onnx"'),
('n=4*len(OPTIONS[args.task])','n=6*len(HEIGHTS)'),
('else 976403','else 64913111'),
('else "acceptance.json"','else ("control_acceptance.json" if CONTROL else "acceptance.json")'),
('selected_iteration=json.loads((RUN/"best_eval.json").read_text())["iteration"]','selected_iteration=None if CONTROL else json.loads((RUN/"best_eval.json").read_text())["iteration"]')])
