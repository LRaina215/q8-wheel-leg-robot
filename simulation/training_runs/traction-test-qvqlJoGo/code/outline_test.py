"""Replicate the stalled-route force experiment with the CAD outline for P01."""
import json,os,sys
from pathlib import Path
import night_model as model
from pull_test import ARCHIVE,ROOT,rollout,get_actor,configuration,cases

def run(arm):
    model.SRC=Path(os.environ['PLATE_CODE'])
    play=rollout()
    app,stage=get_actor('original'),get_actor('phase')
    archive=json.loads((ARCHIVE/'phase_route.json').read_text())
    rows=[]
    for dom in range(2):
        batch=cases('soft_up',12,archive['seed_base']+129*dom,0)
        for i in range(12):
            sample={k:v[i:i+1] for k,v in batch.items()}
            x=play('soft_up',configuration('soft_up',dom,True),sample,app,stage,'phase',arm)
            rows.append(dict(case=i,domain=dom,**x))
    (ROOT/f'outline_{arm}.json').write_text(json.dumps(rows,allow_nan=False))
    print(arm,'fork',sum(r['fork_s'] is not None for r in rows),'reached',sum(r['score']['reached'] for r in rows),flush=True)
if __name__=='__main__':run(sys.argv[1])
