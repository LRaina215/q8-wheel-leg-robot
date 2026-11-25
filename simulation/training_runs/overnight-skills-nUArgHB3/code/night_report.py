"""Summarize the overnight policies, independent acceptance and active training rate."""
from pathlib import Path
import json
import statistics
import time

root=Path(__file__).resolve().parent.parent
def read(path):
    return json.loads(path.read_text()) if path.exists() else {}
def main():
    plan=read(root/"night_plan.json")
    jobs=read(root/"manifest.json")["jobs"]+read(root/"wheel_over_manifest.json")["jobs"]
    rows=[]
    for j in jobs:
        task,seed,variant=j["task"],j["seed"],j["variant"]
        run=root/task/str(seed)
        p=read(run/"progress.json")
        target=plan["tasks"][task][variant]
        hist=run/"learning.jsonl"
        samples=[json.loads(r)["seconds"] for r in hist.read_text().splitlines()[-12:] if r.endswith("}")] if hist.exists() else []
        speed=round(statistics.median(samples),2) if samples else None
        process=read(run/"process.json")
        probe=read(run/"startup_check"/"smoke_native.json")
        marker=read(run/"done.json")
        fail=read(run/"failed.json")
        early=read(run/"interim_acceptance.json")
        final=read(run/"acceptance.json") if marker else {}
        row=dict(task=task,seed=seed,variant=variant,target=target,worlds=j["worlds"],
                 horizon=135 if task.startswith("double_") else 100,
                 current=p.get("iteration",0),seconds_per_update=speed,stage="done" if marker else "failed" if fail else process.get("stage","queued"),
                 live=bool(process and (Path("/proc")/str(process["pid"])).exists()),delta=p.get("actor_delta"),
                 best_onnx=(run/"actor_best.onnx").is_file(),probe_cases=probe.get("cases",0),failure=fail or None)
        for name,result in (("interim",early),("final",final)):
            if result:row[name]={k:result[k] for k in ("cases","gpu","native","passed_both","selected_iteration")}
        rows.append(row)
    print(json.dumps(dict(directory=str(root),unix=time.time(),first_midpoint=plan["interim_first_seed"],jobs=rows,
                         planned_transitions=sum(r["worlds"]*r["target"]*r["horizon"] for r in rows),
                         status_command="cd "+str(root)+" && ../.venv/bin/python code/night_report.py"),ensure_ascii=False))
if __name__=="__main__":main()
