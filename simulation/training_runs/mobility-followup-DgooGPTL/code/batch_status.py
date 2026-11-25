"""Read live, project-scoped worker and artifact state, with wall-clock ETA."""
import json,time,subprocess,statistics
from datetime import datetime,timezone,timedelta
from pathlib import Path
root=Path(__file__).resolve().parent.parent
other=root.parent/'stage-climb-y1o529Z5'
china=timezone(timedelta(hours=8))
now=datetime.now(china)
def read(path):return json.loads(path.read_text()) if path.is_file() else {}
def observe(path):
    state=read(path/'state.json')
    spec=read(path/'run_spec.json');best=read(path/'best_eval.json')
    info=read(path/'progress.json')
    history=[]
    if (path/'learning.jsonl').is_file():
        for line in (path/'learning.jsonl').read_text().splitlines()[-12:]:
            try:history.append(json.loads(line))
            except ValueError:pass
    k=info.get('iteration',0);goal=spec.get('updates',0);pid=state.get('pid')
    alive=bool(pid and Path(f'/proc/{pid}').exists() and 'exit' not in state)
    # Exclude periodic model export/eval and the long initial warm-up; extrapolate only.
    seconds=[v['seconds'] for v in history if v['iteration']>1]
    if len(seconds)>=2 and alive and state['stage']=='train':
        pace=statistics.median(seconds);eta=now+timedelta(seconds=pace*max(0,goal-k))
    else:pace=None;eta=None
    return dict(stage=state.get('stage'),exit=state.get('exit'),pid=pid,alive=alive,worlds=spec.get('worlds'),updates=k,planned=goal,transitions=info.get('transitions'),actor_updated=info.get('actor_delta'),best_iteration=best.get('iteration'),rolling_s=pace,rough_training_end_china=eta.isoformat(timespec='minutes') if eta else None,checkpoint=(path/'checkpoint_latest.npz').is_file(),best_onnx=(path/'actor_best.onnx').is_file())
def main():
    targets={'original_direct':other/'direct','original_phase':other/'phase'}
    targets.update({k:root/k for k in ('climb','handover','down','double_down','lift','forward_jump')})
    targets['handover_plate']=root/'plate_ab'/'handover'
    out=dict(china_time=now.isoformat(timespec='seconds'),directory=str(root),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used','--format=csv,noheader'],text=True).strip(),runs={k:observe(v) for k,v in targets.items()})
    (root/'training_receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(out['china_time'],out['gpu'])
    for k,v in out['runs'].items():print(k,v['stage'],v['alive'],v['updates'],'/',v['planned'],v['checkpoint'],v['rough_training_end_china'])
if __name__=='__main__':main()
