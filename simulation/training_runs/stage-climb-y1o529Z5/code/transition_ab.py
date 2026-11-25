"""Change only the handover slew on the archived controller, in the same 16 pilot cases."""
from pathlib import Path
import json, numpy as np
from onnx import load
from onnx.reference import ReferenceEvaluator
import stage_native
from collision_detail import Detailed
from night_tasks import configuration,smooth
from stage_task import decode,cases

root=Path(__file__).resolve().parent.parent
session=ReferenceEvaluator(load(str(root/'original'/'actor_best.onnx')))
def policy(o):return session.run(None,{'obs':o})[0]
hold=np.array([-1,-1,1,1,-.55,-.55,-.55,-.55],np.float32)
stage_native.Signals=Detailed
def main():
    rows=[]
    for ramp in (.20,.40):
        def cmd(task,o,u):
            phase=smooth((o[:,23]*4.-.24)/ramp)
            return (hold+phase[:,None]*(decode(task,o,u,'direct')-hold)).astype(np.float32)
        stage_native.commands=cmd
        for dom in [0,1]:
            cfg=configuration('soft_up',dom,True)
            bank=cases('soft_up',8,6503129+dom*131,0)
            for i in range(8):
                c={k:v[i:i+1] for k,v in bank.items()}
                score,detail=stage_native.replay('soft_up',cfg,c,policy)
                rows.append(dict(ramp=ramp,domain=dom,index=i,score=score,detail=detail))
        print('native ramp',ramp,flush=True)
    (root/'ramp_ab.json').write_text(json.dumps(rows,allow_nan=False))
if __name__=='__main__':main()
