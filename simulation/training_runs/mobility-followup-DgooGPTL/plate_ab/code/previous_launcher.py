"""Run independent PPO lanes and validate in the same dedicated project directory."""
import concurrent.futures,json,os,subprocess,sys,time
from pathlib import Path
code=Path(__file__).resolve().parent
root=code.parent
def call(label,mode,stage,script,args):
    run=root/label if label!='original' else root/'baseline-logs'
    run.mkdir(exist_ok=True)
    env=dict(os.environ,STAGE_MODE=mode,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'export_deps'))
    with (run/(stage+'.log')).open('a',buffering=1) as log:
        proc=subprocess.Popen([sys.executable,'-u',str(code/script),*args],cwd=run,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        state=dict(stage=stage,pid=proc.pid,start=time.time())
        (run/'state.json').write_text(json.dumps(state))
        warnings=0
        for line in proc.stdout:
            if 'Warning: opt.ccd_iterations' in line:
                warnings+=1
                if warnings==1 or warnings%2000==0:log.write(f'CCD warnings {warnings}\n')
            else:log.write(line)
        status=proc.wait()
        log.write(f'exit {status}, CCD warnings {warnings}\n')
        if status:
            (run/'state.json').write_text(json.dumps(dict(**state,exit=status)))
            raise RuntimeError((label,stage,status))
def lane(label,mode,variant,seed,updates,worlds):
    proto='pilot' if label=='pilot' else 'final'
    n=8 if proto=='pilot' else 16
    if label=='original':
        call(label,mode,'pilot','evaluate.py',[label,'pilot','8'])
    else:
        call(label,mode,'train','stage_ppo.py',['train','soft_up','--seed',str(seed),'--variant',str(variant),'--worlds',str(worlds),'--updates',str(updates)])
    call(label,mode,'validation','evaluate.py',[label,proto,str(n)])
    if label!='pilot':
        call(label,mode,'route','route.py',[label])
    run=root/label if label!='original' else root/'baseline-logs'
    (run/'state.json').write_text(json.dumps(dict(stage='finished',time=time.time())))
if __name__=='__main__':
    lanes=[('original','direct',0,0,0,0),('pilot','phase',0,5112503,36,128),('direct','direct',1,5112501,650,224),('phase','phase',0,5112502,650,224)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(lanes)) as pool:
        jobs=[pool.submit(lane,*args) for args in lanes]
        for job in concurrent.futures.as_completed(jobs):
            try:job.result()
            except Exception as error:print(error,flush=True)
