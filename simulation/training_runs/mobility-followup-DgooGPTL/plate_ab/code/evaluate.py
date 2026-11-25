"""Paired, prospective split-start validation. Both simulators run the identical frozen ONNX."""
import gc,json,os,sys
from pathlib import Path
import numpy as np
from onnx import load
from onnx.reference import ReferenceEvaluator
from night_tasks import configuration
from stage_task import Sim
from stage_native import replay

root=Path(__file__).resolve().parent.parent
def evaluate(label,protocol,n):
    model_dir=root/label
    session=ReferenceEvaluator(load(str(model_dir/'actor_best.onnx')))
    def actor(x):return session.run(None,{'obs':x})[0]
    seed={'pilot':6503129,'final':7231567}[protocol]
    rows=[]
    for dom in (0,1):
        cfg=configuration('soft_up',dom,True)
        env=Sim('soft_up',n,cfg)
        o=env.reset(seed+dom*131)
        for _ in range(env.H):o,_=env.step(actor(o))
        for j in range(n):
            c={k:v[j:j+1] for k,v in env.c.items()}
            native,signals=replay('soft_up',cfg,c,actor)
            gpu={k:v[j].item() for k,v in env.result.items()}
            rows.append(dict(domain=dom,case=j,kg=env.mass,mu=cfg[1],
                        case_values={k:v[0].item() for k,v in c.items()},gpu=gpu,native=native,signals=signals,
                        split_both=bool(gpu['split_start'] and native['split_start']),
                        reached_both=bool(gpu['reached'] and native['reached']),
                        clean_both=bool(gpu['clean'] and native['clean'])))
        del env
        gc.collect()
    dest=root/(label+'_'+protocol+'.json')
    tmp=dest.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(label=label,mode=os.environ.get('STAGE_MODE'),seed=seed,n_per_domain=n,
                             source=str(model_dir.resolve()),rows=rows),allow_nan=False))
    tmp.replace(dest)
    print(label,protocol,len(rows),'starts',sum(r['split_both'] for r in rows),'reached',sum(r['reached_both'] for r in rows),'strict',sum(r['clean_both'] for r in rows),flush=True)

if __name__=='__main__':evaluate(sys.argv[1],sys.argv[2],int(sys.argv[3]))
