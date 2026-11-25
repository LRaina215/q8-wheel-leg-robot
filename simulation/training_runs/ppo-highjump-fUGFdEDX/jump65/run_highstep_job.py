"""Run the Q8 policy training and report simulator CCD warnings without flooding logs."""
import json
from pathlib import Path
import subprocess
import sys
import time

root=Path(__file__).resolve().parent
def run(name,args):
    warnings=0
    with (root/(name+".log")).open("a",buffering=1) as log:
        proc=subprocess.Popen([sys.executable,"-u",*args],cwd=root,stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,text=True,errors="replace")
        (root/(name+".pid")).write_text(str(proc.pid))
        for line in proc.stdout:
            if "Warning: opt.ccd_iterations" in line:
                warnings+=1
                if warnings==1 or warnings%1000==0: log.write(f"CCD iteration warnings: {warnings}\n")
            else: log.write(line)
        code=proc.wait()
        log.write(f"exit={code} CCD iteration warnings={warnings}\n")
    (root/(name+"_exit.json")).write_text(json.dumps(dict(exit=code,ccd_warnings=warnings,time=time.time())))
    return code

if __name__=="__main__":
    jump=sys.argv[1:2]==["flat-jump"]
    trainer="train_flatjump_ppo.py" if jump else "train_highstep_ppo.py"
    native="native_flatjump_policy.py" if jump else "native_highstep_policy.py"
    status=run("ppo",[trainer,*(sys.argv[2:] if jump else sys.argv[1:])])
    if status==0 and (root/native).exists():
        status=run("native_replay",[native])
    sys.exit(status)
