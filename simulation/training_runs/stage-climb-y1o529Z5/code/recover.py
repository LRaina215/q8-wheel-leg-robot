"""Resume only this experiment's failed training stage from its latest finite checkpoint."""
from pathlib import Path
import json,time,sys
from launch import lane
root=Path(__file__).resolve().parent.parent
label=sys.argv[1]
if label not in ('phase','direct'):raise ValueError(label)
while True:
    state=json.loads((root/label/'state.json').read_text())
    if state.get('stage')=='finished' or state.get('stage') not in ('train',):break
    if state.get('exit'):
        print('Resuming from checkpoint',time.time(),state,flush=True)
        lane(label,label,0 if label=='phase' else 1,5112502 if label=='phase' else 5112501,650,224)
        break
    time.sleep(15)
