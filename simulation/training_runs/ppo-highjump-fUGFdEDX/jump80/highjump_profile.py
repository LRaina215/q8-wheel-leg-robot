"""A phase reference with pitch feedback. Outputs the standard 8-channel residual interface."""
import numpy as np
from flatjump_policy_io import smooth,reference_deg

BOUNDS=np.array([[-35.,-18.],[11.,22.],[.060,.145],[-32.,-6.],[.00,.07],[.045,.18],
                 [-29.,5.],[.055,.22],[.04,.22],[-5.,5.],[0.,60.]])
NAMES=["squat_deg","extension_deg","push_s","tuck_deg","delay_s","pull_s","landing_deg",
       "air_hold_s","land_ramp_s","front_bias_deg","pitch_feedback_deg_per_unit"]
def action(params,obs):
    p=np.broadcast_to(params,(len(obs),len(BOUNDS))).T
    dep,ext,push,tuck,delay,pull,land,hold,ramp,bias,kp=p
    t=obs[:,23]*2.
    u=t-.70
    pre=-7.+(dep+7.)*smooth((t-.12)/.38)
    v=dep+(ext-dep)*smooth(u/push)
    v+=(tuck-v)*smooth((u-push-delay)/pull)
    v+=(land-v)*smooth((u-push-delay-pull-hold)/ramp)
    v+=(-7.-v)*smooth((t-1.32)/.31)
    ref=np.where(t<.70,pre,v)
    phase=smooth((t-.4)/.18)*(1.-smooth((t-1.32)/.25))
    differential=bias*phase-kp*obs[:,2]+.45*kp*obs[:,8]
    residual=(ref-reference_deg(t))/16.
    out=np.zeros((len(obs),8),np.float32)
    out[:,:2]=np.clip(residual+differential/16.,-1.,1.)[:,None]
    out[:,2:4]=np.clip(residual-differential/16.,-1.,1.)[:,None]
    out[:,4:]=np.clip(-1.5*obs[:,5],-.70,.70)[:,None]
    return out

def gates(s):
    return (s["valid"]&s["stable"]&(s["residual_mm"]<.8)&(s["hull_N"]<2.)
            &(s["rebound_ms"]<=30)&(s["flight_ms"]>=20)&(s["tire_mm"]>=10))
