"""Independent, resumable jobs. Only project-local run directories and the existing venv."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import json,sys,subprocess,time,os,traceback
code=Path(__file__).resolve().parent
root=code.parent
jobs={'climb':('soft_up',0,800,192),'handover':('soft_up',1,800,192),
      'down':('down',1,540,128),'double_down':('double_down',0,540,128),
      'lift':('lift',1,580,160),'forward_jump':('forward_jump',0,600,160)}
def state(path,record):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(record));tmp.replace(path)
def run(lane,stage,cmd,env):
    run=root/lane
    with (run/(stage+'.log')).open('a',buffering=1) as log:
        child=subprocess.Popen(cmd,cwd=run,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        state(run/'state.json',dict(stage=stage,pid=child.pid,started=time.time()))
        count=0
        for line in child.stdout:
            if 'Warning: opt.ccd_iterations' in line:
                count+=1
                if count==1 or count%5000==0:log.write(line)
            else:log.write(line)
        rc=child.wait()
        log.write(f'exit {rc}; CCD warnings {count}\n')
        return rc
def lane(job):
    task,variant,updates,n=jobs[job]
    run_dir=root/job;run_dir.mkdir(exist_ok=True)
    seed=63112500+list(jobs).index(job)
    env=dict(os.environ,FOLLOW_LANE=job,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'export_deps'))
    args=[task,'--variant',str(variant),'--seed',str(seed),'--updates',str(updates),'--worlds',str(n)]
    for stage,mode,control in [('train','train',0),('evaluation','validate',0),('baseline','validate',1)]:
        artifact={'train':'finished.json','evaluation':'acceptance.json','baseline':'control_acceptance.json'}[stage]
        if (run_dir/artifact).is_file():continue
        cmd=[sys.executable,'-u',str(code/'follow_ppo.py'),mode,*args]
        for attempt in range(2):
            rc=run(job,stage,cmd,dict(env,FOLLOW_CONTROL=str(control),FOLLOW_EVAL=str(int(mode=='validate'))))
            if not rc:break
            time.sleep(2)
        if rc:
            state(run_dir/'state.json',dict(stage=stage,exit=rc));raise RuntimeError(job+' '+stage)
    state(run_dir/'state.json',dict(stage='finished',time=time.time()))
if __name__=='__main__':
    keys=sys.argv[1:] or list(jobs)
    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        todo=[pool.submit(lane,k) for k in keys]
        for f in as_completed(todo):
            try:f.result()
            except Exception:traceback.print_exc()
