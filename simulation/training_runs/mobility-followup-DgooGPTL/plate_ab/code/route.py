"""Native end-to-end check: frozen approach, then switch only on measured split-level support."""
import json,sys,os
from pathlib import Path
from onnx import load
from onnx.reference import ReferenceEvaluator
import numpy as np
from night_tasks import configuration
from stage_task import cases,decode

src=Path(__file__).resolve().parent
root=src.parent
def generate():
    script=(src/'night_native.py').read_text()
    def sub(old,new):
        nonlocal script
        if script.count(old)!=1:raise ValueError(old)
        script=script.replace(old,new)
    sub('def replay(task,config,c,actor):','def replay(task,config,c,approach,stage,mode):')
    sub('    for k in range(H*DEC):','    consecutive=0;ready=False;switch_tick=None;first_ready=None\n    for k in range(H*DEC):')
    sub('            o=observation(task,raw_native(d,ix,ti),c,i,prev)\n            prev=actor(o)\n            cmd=commands(task,o,prev)[0]','''            if ready and first_ready is None:first_ready=k
            if ready and stage is not None and switch_tick is None:
                switch_tick=k
                prev.fill(0)
            if switch_tick is None:
                o=observation(task,raw_native(d,ix,ti),c,i,prev)
                prev=approach(o)
                cmd=commands(task,o,prev)[0]
            else:
                phase_tick=min((k-switch_tick)//DEC+6,H-1)
                o=observation(task,raw_native(d,ix,ti),c,phase_tick,prev)
                prev=stage(o)
                cmd=decode(task,o,prev,mode)[0]''')
    sub('        a[30:]=d.qvel[1:3]','''        a[30:]=d.qvel[1:3]
        e=c["edge"][0]
        split=all(a[4:6]>1.) and all(a[2:4]>1.) and all(a[17:19]>e+.01) and all(a[19:21]<e)
        consecutive=consecutive+1 if split else 0
        # Only issue a handover if the most recent 40 ms still have continuous support.
        ready=consecutive>=20''')
    sub('return {k:v[0].item() for k,v in score(task,trace,c).items()}','return dict(score={k:v[0].item() for k,v in score(task,trace,c).items()},ready_s=None if first_ready is None else first_ready*.002,switch_s=None if switch_tick is None else switch_tick*.002)')
    scope={'decode':decode}
    exec(compile(script,'<flat-handover>','exec'),scope)
    return scope['replay']
def read_actor(path):
    session=ReferenceEvaluator(load(str(path/'actor_best.onnx')))
    return lambda x:session.run(None,{'obs':x})[0]
def main(label):
    replay=generate()
    original=read_actor(root/'original');stage=None if label=='original' else read_actor(root/label)
    rows=[]
    for dom in range(2):
        cfg=configuration('soft_up',dom,True)
        bank=cases('soft_up',12,6031441+129*dom,0.)
        for j in range(12):
            c={k:v[j:j+1] for k,v in bank.items()}
            r=replay('soft_up',cfg,c,original,stage,os.environ['STAGE_MODE'])
            rows.append(dict(domain=dom,case=j,**r))
    (root/(label+'_route.json')).write_text(json.dumps(dict(label=label,seed_base=6031441,rows=rows),allow_nan=False))
    print(label,'native route: ready, reached, clean',sum(r['ready_s'] is not None for r in rows),sum(r['score']['reached'] for r in rows),sum(r['score']['clean'] for r in rows))
if __name__=='__main__': main(sys.argv[1])
