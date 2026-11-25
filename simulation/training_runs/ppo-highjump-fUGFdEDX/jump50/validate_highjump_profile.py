"""Select a phase profile on two native conditions then evaluate it on four additional conditions."""
import json
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from native_flatjump_policy import replay
from highjump_profile import action

BASE=[(.14,.64,.97,0.),(.34,.47,.89,-3.)]
UNSEEN=[(.14,.55,.91,2.),(.34,.60,.94,-1.),(.24,.50,.90,3.),(.28,.67,.98,-2.)]
def run(arg):
    params,cond=arg
    return replay(lambda x:action(np.asarray(params),x),50,*cond)
def mech(r):
    return bool(r["valid"] and r["stable"] and r["residual_mm"]<.8 and r["hull_N"]<2. and
                r["rebound_ms"]<=30. and r["flight_ms"]>=20. and r["tire_mm"]>=10.)
if __name__=="__main__":
    proposals=json.loads(Path("profiles.json").read_text())["top"][:16]
    with Pool(4) as pool:
        rows=pool.map(run,[(p["params"],c) for p in proposals for c in BASE])
        groups=[rows[2*i:2*i+2] for i in range(len(proposals))]
        winner=max(range(len(groups)),key=lambda i:(all(map(mech,groups[i])),
                   min(r["com_rise_mm"] for r in groups[i]) if all(map(mech,groups[i])) else -max(r["residual_mm"] for r in groups[i])))
        params=proposals[winner]["params"]
        extra=pool.map(run,[(params,c) for c in UNSEEN])
    for r in groups[winner]+extra:
        r["mechanical_pass"]=mech(r)
        r["at_least_50mm"]=mech(r) and r["com_rise_mm"]>=50.
    record=dict(params=params,goal_mm=50,selected_on=groups[winner],holdout=extra)
    Path("verified_profile.json").write_text(json.dumps(record,indent=2))
    print([(round(r["com_rise_mm"],1),round(r["residual_mm"],3),r["mechanical_pass"]) for r in groups[winner]+extra])
