"""Replay the successful GPU holdout worlds in native MuJoCo with the same initial state."""
import json
import sys
from pathlib import Path
import numpy as np
from native_highstep_policy import replay
from ppo_highstep_env import Env,HERE,HORIZON
from train_highstep_ppo import forward


def main():
    archive=np.load(HERE/"milestone.npz")
    actor=[archive["actor%d"%i] for i in range(6)]
    env=Env(448)
    o=env.reset(np.random.default_rng(970214))
    # qpos is still the commanded, unstepped orientation.
    yaw=np.rad2deg(2*np.arctan2(env.d.qpos.numpy()[:,6],env.d.qpos.numpy()[:,3]))
    scale=env.scale.numpy()
    def policy(obs): return np.tanh(forward(actor,obs)[0])
    for _ in range(HORIZON): o,_=env.step(policy(o))
    ids=np.flatnonzero(env.result["atop"])
    sys.path.append(str(HERE/"export_deps"))
    import onnx
    from onnx.reference import ReferenceEvaluator
    session=ReferenceEvaluator(onnx.load(str(HERE/"milestone.onnx")))
    def exported(x): return session.run(None,{"obs":x})[0]
    parity=float(np.max(np.abs(policy(o[:16])-exported(o[:16]))))
    if parity>1e-5: raise ValueError("policy snapshots differ")
    rows=[]
    for w in ids:
        if len(rows)>=16: break
        native=replay(exported,int(env.height_mm[w]),.14,.64,float(scale[w]),float(yaw[w]),env.true_edge[w]-.38,
                      env.estimated_edge[w],env.estimated_height[w]*1000.)
        rows.append(dict(world=int(w),gpu_clean=bool(env.result["clean"][w]),native=native))
    result=dict(iteration=int(archive["iteration"]),gpu_atop=len(ids),gpu_clean=int(env.result["clean"].sum()),
                by_height={str(h):int(((env.height_mm==h)&env.result["atop"]).sum()) for h in np.unique(env.height_mm)},
                onnx_max_abs_error=parity,matched_native=rows)
    (HERE/"milestone_replay.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,allow_nan=False),flush=True)


if __name__=="__main__": main()
