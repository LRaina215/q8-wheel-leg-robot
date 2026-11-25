"""Q8 robustness campaign. All distances are measured in the ground-aligned frame."""
from dataclasses import dataclass, asdict
import numpy as np
from followup_tasks import BOUNDS as EXTRA_BOUNDS, assess as followup_assess

@dataclass(frozen=True)
class Condition:
    extra: float = 0.
    mu: float = .75
    grade_deg: float = 0.
    cg_shift: tuple = (0.,0.,0.)
    torque_scale: float = 1.
    lateral_force: float = 0.
    ccd: int = 256

    def options(self):
        return asdict(self)

NAMES = {0:"drive_turn", 1:"lift_FL", 2:"soft_jump_landing", 4:"single_flight_step",
         6:"lift_FR", 7:"lift_RL", 8:"lift_RR", 10:"two_stage_step",
         11:"controlled_descent", 12:"individual_wheel_step", 13:"forward_grade_stop", 14:"reverse_grade_stop"}
GROUPS = {"terrain":(10,11,12,4), "handling":(2,1,6,7,8,0), "grade":(13,14)}
PLAN = {"terrain":(224,160), "handling":(160,112), "grade":(128,224)}
SEEDS = (38117,90431)
GRADE_LIMITS = [(0,.9),(0,.35),(.15,.9),(.5,9),(0,.45),(-12,12)]

def initial(tag,old,new,old_bounds):
    if tag in (13,14):return [0.3,.10,.45,3,.10,0], GRADE_LIMITS
    if tag==12:
        p=new["roll_step_v2"]
        return [p[0],p[1],.095,.04,8,.045],[(.22,.49),(14,30),(.025,.17),(-.095,.095),(-14,14),(.0,.11)]
    if tag in (10,11,6,7,8):
        name="two_stage_step_v2" if tag==10 else NAMES[tag]
        return new[name],EXTRA_BOUNDS[tag-6]
    name={0:"drive_turn",1:"lift_FL",2:"low_jump",4:"jump_step"}[tag]
    return old[name],old_bounds[tag]

def training_cases(group):
    if group=="grade":
        return [Condition(.08,.72,-6,(.002,-.002,0),.98),Condition(.30,.49,6,(-.004,.003,.004),.90)]
    if group=="handling":
        return [Condition(0,.70,0,(.002,-.002,0),1.,3.),Condition(.32,.48,0,(-.005,.004,.005),.9,-5.)]
    return [Condition(0,.75),Condition(.32,.50,0,(.006,-.004,.006),.90)]

def variants(group,stage,env):
    if group=="terrain":
        small=(.015,.020,.020)[stage];large=(.025,.030,.032)[stage]
        angle=(4,7,10)[stage];bias=(.003,.006,.008)[stage]
        return [(small,0. if env==0 else angle,bias if env else 0.),
                (large,-angle if env==0 else 0.,-bias if env==0 else bias)]
    # Vary initial heading for driving and braking. Vertical lift/jump also see
    # opposite force and changed mass between the two dynamics models.
    return [(0.,0.,0.),(0.,(4.,6.,8.)[stage]*(1 if env==0 else -1),0.)]

def heldout(group):
    if group=="terrain":
        return [(Condition(.16,.57,ccd=128),[(h,0.,0.) for h in (.015,.020,.025,.030,.032)]),
                (Condition(.19,.61,0,(.003,.003,.002),.95),
                 [(h,y,b) for h in (.018,.028,.035) for y,b in ((-9.,.005),(9.,-.005))]),
                (Condition(.36,.46,0,(-.004,-.003,.004),.88),[(.020,0.,0.),(.030,-5.,.004),(.030,5.,-.004)])]
    if group=="handling":
        return [(Condition(.16,.57),[(0.,0.,0.)]),
                (Condition(.17,.56,0,(.003,.003,.002),.95,-4.),[(0.,-5.,0.)]),
                (Condition(.34,.46,0,(-.004,-.003,.004),.88,4.),[(0.,5.,0.)])]
    return [(Condition(.16,.57,grade,(.002,-.002,.002),.94),[(0.,0.,0.),(0.,5.,0.)]) for grade in (-8,-4,0,4,8)]

def metrics(trace,tag,height,bias,base):
    if tag in (10,11,12,4,15):
        # The controller uses its estimate x=.38. Evaluate against the actual edge.
        if bias:
            trace=trace.copy();trace[:,17:21]-=bias
        if tag==4:return base(trace,4,height)
        r=followup_assess(trace,{12:9,15:10}.get(tag,tag),height,base)
        if tag==12:
            loaded=trace[:,:4]+trace[:,4:8]+trace[:,8:12]
            cleared=[]
            for j in range(4):
                x=trace[:,17+j]
                crossed=np.flatnonzero((x[:-1]<.38)&(x[1:]>=.38))+1
                cleared.append(any(trace[k-1:k+1,13+j].min()>height*1000+1 and
                                   loaded[k-1:k+1,j].max()<1 for k in crossed))
            r["score"]+=5*sum(cleared)-30*(r["passed"] and not all(cleared))
            r["passed"]=bool(r["passed"] and all(cleared))
            r["clear_while_crossing_edge"]=[bool(c) for c in cleared]
        return r
    if tag in (6,7,8):return followup_assess(trace,tag,0.,base)
    if tag in (0,1):return base(trace,tag,0.)
    if tag==2:
        r=base(trace,2,0.);support=trace[:,:8].reshape(-1,2,4).sum(axis=1)
        airborne=(support.sum(axis=1)+trace[:,8:13].sum(axis=1)<.5)
        # Locate the commanded jump and assess impact/rebound from first touchdown.
        intervals=np.flatnonzero(np.diff(np.r_[False,airborne & (np.arange(len(trace))>=550),False].astype(int))).reshape(-1,2)
        flights=[(a,b) for a,b in intervals if b-a>=10 and b<len(trace)]
        a,b=flights[0] if flights else (0,0)
        impact=float(support[b:b+125].max()) if flights else 0.
        rebound=max((2*(end-start) for start,end in flights[1:]),default=0)
        clear=float(trace[a:b,13:17].min(axis=1).max()) if flights else 0.
        passed=r["passed"] and clear>=20 and rebound<=30
        r.update(first_flight_wheel_apex_mm=clear,peak_landing_wheel_N=impact,rebound_ms=int(rebound),
                 passed=bool(passed),score=float(r["score"]+15*passed-.27*impact-.12*rebound))
        return r
    sign=1 if tag==13 else -1
    speed=sign*trace[:,23];x=sign*trace[:,27]
    approach=float(speed[400:720].mean())
    origin=x[750];stop_distance=float(np.max(np.abs(x[750:]-origin)))
    creep=float(np.max(np.abs(x[1500:]-origin)))
    lateral=float(np.max(np.abs(trace[750:,28]-trace[750,28])))
    final_speed=float(np.max(np.linalg.norm(trace[1825:][:,[23,30,31]],axis=1)))
    gap=float(trace[100:,26].max());hull=float(trace[100:,12].max())
    ground=float(np.mean(np.all(trace[1825:,:4]>1,axis=1)))
    tilt=float(trace[100:,21].max())
    passed=approach>=.25 and stop_distance<=.07 and creep<=.03 and final_speed<.035 and lateral<.05 and ground>.95 and gap<.8 and hull<2 and tilt<8
    score=(35-100*abs(approach-.32)-180*stop_distance-100*creep-60*final_speed-40*lateral
           -25*max(0.,gap-.5)-hull+5*ground+30*passed)
    return dict(score=float(score),passed=bool(passed),approach_speed_mps=approach,stop_excursion_mm=stop_distance*1000,
                final_hold_error_mm=creep*1000,final_speed_mps=final_speed,side_drift_after_stop_mm=lateral*1000,
                four_wheels_loaded_fraction=ground,closure_mm=gap,peak_structure_contact_N=hull,tilt_to_surface_deg=tilt)
