"""Independent replay of a fixed-height PPO correction on the Q8 phase profile."""
import json
from pathlib import Path
import sys
import numpy as np
from native_flatjump_policy import replay
from highjump_profile import action
from validate_highjump_profile import BASE,UNSEEN,mech

def main():
    sys.path.append(str(Path("export_deps").resolve()))
    import onnx
    from onnx.reference import ReferenceEvaluator
    actor=ReferenceEvaluator(onnx.load("highjump_best.onnx"))
    p=np.asarray(json.loads(Path("verified_profile.json").read_text())["params"])
    g=json.loads(Path("run_spec.json").read_text())["target_mm"]
    def pi(x):return np.clip(action(p,x)+.72*actor.run(None,{"obs":x})[0],-1,1)
    rows=[replay(pi,g,*c) for c in BASE+UNSEEN]
    for r in rows:r["target_and_mechanical"]=bool(mech(r) and r["com_rise_mm"]>=g)
    Path("native_final.json").write_text(json.dumps(dict(target_mm=g,rows=rows),indent=2))
    print("native",sum(r["target_and_mechanical"] for r in rows),"/",len(rows))
if __name__=="__main__":main()
