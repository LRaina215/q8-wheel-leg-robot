"""Q8 jump ONNX interface. SI units unless otherwise noted; order FL, FR, RL, RR."""
import numpy as np

DT=.002
DECIMATION=10
HORIZON=100
GOALS=np.array([10,20,30,40],dtype=np.int32)


def smooth(u):
    s=np.clip(u,0.,1.)
    return s*s*(3.-2.*s)


def reference_deg(t):
    # Prior calibrated soft landing reference, shifted to a 2-second episode.
    t=np.asarray(t)
    start=.70
    depth,peak,push,tuck,delay,recovery=(-20.,12.39249,.107843,-12.84725,.010,.111925)
    pre=-7.+(depth+7.)*smooth((t-.12)/.38)
    u=t-start
    lift=depth+(peak-depth)*smooth(u/push)
    retract=lift+(tuck-lift)*smooth((u-push-delay)/.075)
    land=retract+(-7.-retract)*smooth((u-push-delay-.075-recovery)/.28)
    return np.where(t<start,pre,land)


def observations(raw,vz,goal_mm,step,last):
    # raw[0:22] is odometry x,y, R20,R21,R10, base vx,vy, body gyro/4,
    # (hip angle +7 deg)*2 in rad, hip speed/5, and wheel speed*.08.
    x=np.empty((len(raw),33),np.float32)
    x[:,:22]=raw[:,:22]
    x[:,0]*=3.
    x[:,1]*=3.
    x[:,22]=np.asarray(goal_mm)/30.
    x[:,23]=step/HORIZON
    x[:,24:32]=last
    x[:,32]=vz
    return np.clip(np.nan_to_num(x),-5.,5.)


def commands(seconds,normalized):
    # Hold neural output for 20 ms. Advance the phase reference every 2 ms.
    hip=np.clip(reference_deg(seconds)+16.*normalized[...,0:4],-36.,22.)
    tread=.18*normalized[...,4:8]
    return np.deg2rad(hip),tread


def metrics(trace,goals):
    """T x N x 10. Pick the first continuous flight >=20 ms followed by touchdown.
    Both the COM rise and simultaneous minimum wheel clearance refer to that one flight."""
    t,n,_=trace.shape
    f,clear,com,tilt,v,hull,gap,ground,capacity,drift=trace.transpose(2,0,1)
    valid=np.isfinite(trace).all(axis=(0,2)) & (capacity.max(0)==0)
    # Ignore initial placement transient. Contacts include every robot-ground pair.
    air=(f<.5)&(clear>0.)
    air[:100]=False
    changes=np.diff(np.pad(air.astype(np.int8),((1,1),(0,0))),axis=0)
    starts,ws=np.nonzero(changes==1)
    stops,wend=np.nonzero(changes==-1)
    # Each world's starts and stops align when sorted by world, then time.
    order=np.argsort(ws,kind="stable")
    ends=np.argsort(wend,kind="stable")
    a,b,w=starts[order],stops[ends],ws[order]
    keep=(b-a>=10)&(b<t)
    a,b,w=a[keep],b[keep],w[keep]
    duration=np.zeros(n)
    apex=np.zeros(n)
    height=np.zeros(n)
    rebound=np.zeros(n)
    landing=np.zeros(n)
    # Most episodes have one significant flight. Process ragged slices at touchdown only.
    for first,end,idx in zip(a,b,w):
        dt=2.*(end-first)
        if duration[idx]:
            rebound[idx]=max(rebound[idx],dt)
            continue
        duration[idx]=dt
        apex[idx]=max(0.,float(clear[first:end,idx].max()))
        height[idx]=max(0.,float(com[first:end,idx].max()-com[first,idx]))
        landing[idx]=float(f[end:min(t,end+125),idx].max())
    late=slice(t-175,t)
    stable=(ground[late].mean(0)>.95)&(tilt[late].max(0)<=5.)&(v[late].max(0)<.1)&(drift[late].max(0)<.075)
    clean=(valid&stable&(hull[100:].max(0)<2.)&(gap[100:].max(0)<.8)&(rebound<=30.)&
           (duration>=20.)&(apex>=10.)&(np.abs(height-goals)<=np.maximum(3.,.20*goals)))
    return dict(valid=valid,flight_ms=duration,tire_mm=apex,com_rise_mm=height,
                contact_peak_N=landing,rebound_ms=rebound,stable=stable,clean=clean,
                residual_mm=gap[100:].max(0),hull_N=hull[100:].max(0))
