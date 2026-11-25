"""Additional independent lane for deliberate unloaded wheel crossing."""
from concurrent.futures import ThreadPoolExecutor
import os,time
from night_queue import ROOT,WORLDS,STRETCH,MID,emit,collect,lane
from night_tasks import horizon
task="wheel_over"
jobs=[dict(task=task,seed=25112520+v,variant=v,worlds=WORLDS,updates=STRETCH,
           transitions=STRETCH*WORLDS*horizon(task)) for v in range(2)]
manifest=dict(created=time.time(),directory=str(ROOT),parallel_lanes=1,mid_update=MID,jobs=jobs)
emit(ROOT/"wheel_over_manifest.json",manifest)
with ThreadPoolExecutor(max_workers=1) as ex:
    future=ex.submit(lane,task,jobs)
    while not future.done():
        emit(ROOT/"wheel_over_status.json",collect(manifest))
        time.sleep(10)
    future.result()
emit(ROOT/"wheel_over_status.json",collect(manifest))
