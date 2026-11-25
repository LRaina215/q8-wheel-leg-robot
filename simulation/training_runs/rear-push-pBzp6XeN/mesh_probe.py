"""Measure printed rear side plates in recorded poses, at peak opposing plate reaction."""
from pathlib import Path
import json,sys
import numpy as np
from plate_clearance import read_plate,gap
root=Path(__file__).parent
local,pairs,info=read_plate()
results=[]
for filename in sys.argv[1:]:
    for r in json.loads((root/filename).read_text()):
        if r['push_s'] is None:continue
        ev=r['plate'];pos=np.asarray(ev['body'][:3]);rot=np.asarray(ev['body'][3:]).reshape(3,3)
        sides=[]
        for v in local:
            pts=v@rot.T+pos
            if abs(pts[:,1]).max()>=.46 or pts[:,0].max()>=r['edge']+1.6:
                sides.append(None)
            else:sides.append(gap(pts,pairs,r['edge']))
        results.append(dict(run=filename,case=r['case'],domain=r['domain'],reached=r['score']['reached'],time_s=ev['t_s'],reaction_x_N=ev['force_x'],signed_gap_mm=sides))
(root/'printed_plate_gaps.json').write_text(json.dumps(dict(info=info,rows=results)))
