"""Native screening of heading correction and command timing against fixed Q8 controllers."""
import json
import sys
from pathlib import Path
from native_holdout import replay
from campaign_tasks import metrics
from train_actions import assess, save

def run(campaign,output):
    def params(group,name,seed):
        info=json.loads((campaign/group/"final.json").read_text())
        return info["coefficients"][seed][name]
    step=params("terrain","two_stage_step","reference")
    jump=params("handling","soft_jump_landing","38117")
    rows=[]
    def collect(tag,p,h,yaw,gain,period,delay):
        telemetry={}
        trace=replay(tag,p,h,.16,.57,ccd=256,yaw_deg=yaw,approach_gain=gain,command_period_steps=period,
                     command_delay_steps=delay,telemetry=telemetry)
        rows.append(dict(task="two_stage" if tag==10 else "low_jump",height_mm=round(h*1000),
                         yaw_deg=yaw,heading_gain=gain,period_ms=period*2,delay_ms=delay*2,
                         **telemetry,metrics=metrics(trace,tag,h,0.,assess)))
    for mm in (20,30):
        for yaw in (-9,-5,-2,0,2,5,9):
            for gain in (0.,3.,8.):
                collect(10,step,mm/1000,yaw,gain,1,0)
    for tag,p,h in ((2,jump,0.),(10,step,.020),(10,step,.030)):
        for period,delay in ((1,0),(5,0),(5,5),(5,10),(10,10)):
            collect(tag,p,h,0.,0.,period,delay)
    save(output,dict(engine="native MuJoCo",mass_kg=6.588505742216554,friction=.57,
         timing_scope="Setpoint sampling and transmission only. Local joint PD and edge event detection remain at 500 Hz.",
         heading_scope="Simulated known edge normal; differential wheel commands before the leading wheel is within 45 mm of the estimated edge. No pose reset.",cases=rows))
if __name__=="__main__":run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]))
