"""One read of the project's PPO progress and current GPU occupancy."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,statistics,subprocess,time
r=Path(__file__).resolve().parent.parent
clock=datetime.now(timezone(timedelta(hours=8)))
out=dict(directory=str(r),time_china=clock.isoformat(timespec='seconds'),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used','--format=csv,noheader'],text=True).strip(),runs={})
for name in ('pilot','direct','phase'):
    path=r/name
    logs=[json.loads(line) for line in (path/'learning.jsonl').read_text().splitlines() if line.strip()]
    spec=json.loads((path/'run_spec.json').read_text());state=json.loads((path/'state.json').read_text())
    recent=logs[-12:];done=logs[-1]['iteration'];remaining=(spec['updates']-done)*statistics.median(v['seconds'] for v in recent)
    pid=state.get('pid')
    alive=bool(pid and (Path('/proc')/str(pid)).exists() and 'exit' not in state)
    out['runs'][name]=dict(stage=state['stage'],pid=pid,alive=alive,exit=state.get('exit'),iteration=done,goal=spec['updates'],transitions=logs[-1]['transitions'],worlds=spec['worlds'],eta_training_minutes=round(remaining/60,1) if alive else None,best_iteration=json.loads((path/'best_eval.json').read_text())['iteration'],has_onnx=(path/'actor_best.onnx').is_file(),post_training='paired GPU/native split-start 32 cases, then native end-to-end 24 cases' if name!='pilot' else 'paired GPU/native split-start 16 cases')
(r/'status_snapshot.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print(json.dumps(out,ensure_ascii=False))
