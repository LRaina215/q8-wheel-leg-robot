from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,sys,json,shutil
root=Path.cwd()
jobs=[j for j in json.loads((root/"manifest.json").read_text())["jobs"] if not j["variant"]]
def test(j):
 run=root/j["task"]/str(j["seed"])
 snap=run/"startup_check";snap.mkdir(exist_ok=True)
 for f in ("actor_best.onnx","best_eval.json"):shutil.copy2(run/f,snap/f)
 with (snap/"probe.log").open("w") as log:
  rc=subprocess.call([sys.executable,"-u",str(root/"code"/"night_train.py"),"validate",j["task"],"--variant","0","--seed",str(j["seed"]),"--probe"],cwd=snap,stdout=log,stderr=log)
 print(j["task"],rc,flush=True)
 return rc
with ThreadPoolExecutor(max_workers=2) as ex: codes=list(ex.map(test,jobs))
raise SystemExit(int(any(codes)))
