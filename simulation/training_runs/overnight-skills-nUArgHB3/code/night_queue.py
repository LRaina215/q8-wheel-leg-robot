"""One foreground supervisor, one independent lane per motion, persistent logs and resumable checkpoints."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from night_tasks import OPTIONS,horizon

ROOT=Path(__file__).resolve().parent.parent
CODE=ROOT/"code"
STRETCH=900
MID=240
WORLDS=160

def emit(path,data):
    temp=path.with_name(path.name+".tmp")
    temp.write_text(json.dumps(data,indent=2,allow_nan=False))
    os.replace(temp,path)

def read(path,default=None):
    try:return json.loads(path.read_text())
    except (FileNotFoundError,ValueError):return default

def call(run,stem,args):
    with (run/(stem+".log")).open("a",buffering=1) as log:
        child=subprocess.Popen([sys.executable,"-u",str(CODE/"night_train.py"),*args],cwd=run,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace")
        emit(run/"process.json",dict(pid=child.pid,stage=stem,started=time.time()))
        warnings=0
        for line in child.stdout:
            if "Warning: opt.ccd_iterations" in line:
                warnings+=1
                if warnings==1 or warnings%2000==0:log.write(f"CCD warnings {warnings}\n")
            else:log.write(line)
        code=child.wait()
        log.write(f"exit {code}; CCD warnings {warnings}\n")
    return code

def segment(run,stem,args):
    for attempt in range(2):
        if call(run,stem,args)==0:return
        time.sleep(2)
    raise RuntimeError(stem+" failed twice; see "+str(run/(stem+".log")))

def lane(task,jobs):
    for job in jobs:
        run=ROOT/task/str(job["seed"])
        run.mkdir(parents=True,exist_ok=True)
        if (run/"done.json").exists():continue
        args=[task,"--seed",str(job["seed"]),"--variant",str(job["variant"]),"--updates",str(STRETCH),
              "--worlds",str(WORLDS)]
        try:
            if job["variant"]==0 and not (run/"interim_acceptance.json").exists():
                segment(run,"train_early",["train",*args,"--stop-at",str(MID)])
                segment(run,"validate_early",["validate",*args])
                os.replace(run/"acceptance.json",run/"interim_acceptance.json")
                shutil.copy2(run/"actor_best.onnx",run/"interim_actor_best.onnx")
            if not (run/"finished.json").exists():segment(run,"train",["train",*args])
            segment(run,"validate_final",["validate",*args])
            acceptance=read(run/"acceptance.json")
            emit(run/"done.json",dict(unix=time.time(),cases=acceptance["cases"],passed_both=acceptance["passed_both"]))
        except Exception as exc:
            emit(run/"failed.json",dict(error=str(exc),unix=time.time()))
            # The other training variant has independent initial weights and conditions.
    return task

def collect(manifest):
    result=[]
    for j in manifest["jobs"]:
        run=ROOT/j["task"]/str(j["seed"])
        rec=read(run/"progress.json",{})
        done=read(run/"done.json");failed=read(run/"failed.json")
        proc=read(run/"process.json",{})
        row=dict(**j,stage="done" if done else "failed" if failed else proc.get("stage","queued"),
                 iteration=rec.get("iteration",0),recent_seconds=rec.get("seconds"),current_pid=proc.get("pid"),
                 final=done,failed=failed)
        if (run/"interim_acceptance.json").exists():
            a=read(run/"interim_acceptance.json")
            row["interim"]=dict(passed_both=a["passed_both"],cases=a["cases"],selected=a["selected_iteration"])
        result.append(row)
    return dict(updated=time.time(),jobs=result)

def main():
    lock=(ROOT/"supervisor.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    jobs=[dict(task=t,seed=25112500+i*2+v,variant=v,worlds=WORLDS,updates=STRETCH,
               transitions=STRETCH*WORLDS*horizon(t))
          for i,t in enumerate(OPTIONS) for v in range(2)]
    manifest=dict(created=time.time(),directory=str(ROOT),parallel_lanes=len(OPTIONS),mid_update=MID,jobs=jobs)
    emit(ROOT/"manifest.json",manifest)
    emit(ROOT/"supervisor_pid.json",dict(pid=os.getpid()))
    with ThreadPoolExecutor(max_workers=len(OPTIONS)) as ex:
        future=[ex.submit(lane,t,[j for j in jobs if j["task"]==t]) for t in OPTIONS]
        while not all(f.done() for f in future):
            emit(ROOT/"status.json",collect(manifest))
            time.sleep(10)
        for f in future:f.result()
    summary=collect(manifest)
    emit(ROOT/"status.json",summary)
    emit(ROOT/"night_complete.json",summary)

if __name__=="__main__":main()
