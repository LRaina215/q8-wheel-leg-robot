"""Task definitions shared by the GPU trainer and independent native replay."""
import numpy as np

OPTIONS={
 "soft_up":[60,90,120,140,150], "down":[40,60,90,120],
 "double_up":[40,60,80], "double_down":[40,60,80], "leap_step":[40,60,80],
 "lift":[0,1,2,3], "brake":[-1,1], "recover":[-1,1], "drive":[-1,1],
 "forward_jump":[60,100,140],"wheel_over":[40,60,75,90]}
TERRAIN={"soft_up","down","double_up","double_down","leap_step","wheel_over"}
DESC={"down","double_down"}
DOUBLE={"double_up","double_down"}
PRETRAIN={"soft_up","double_up","leap_step","wheel_over"}
DT=.002
DEC=20
PERIOD=DT*DEC

def horizon(task): return 135 if task in DOUBLE else 100

def casebank(task,n,seed,grade,blind_recovery=False):
    r=np.random.default_rng(seed)
    key=np.resize(OPTIONS[task],n).copy()
    r.shuffle(key)
    edge=r.uniform(.34,.43,n) if task!="leap_step" else r.uniform(.43,.53,n)
    yaw=r.uniform(-6,6,n)
    sign=r.choice([-1.,1.],n)
    return dict(key=key,h=(key*.001 if task in TERRAIN else np.zeros(n)),
                edge=edge,edge_obs=edge+r.uniform(-.009,.009,n),
                h_obs=(key*.001+r.uniform(-.004,.004,n) if task in TERRAIN else np.zeros(n)),
                tread=r.uniform(.30,.38,n),yaw=yaw,scale=r.uniform(.89,1.,n),
                pulse=(key*r.uniform(18.,32.,n) if task=="recover" else sign*r.uniform(3.,7.,n)),
                pulse_x=r.uniform(-9.,9.,n) if task=="recover" else np.zeros(n),
                grade=np.full(n,grade),blind=np.full(n,bool(blind_recovery)),
                kick_start=(r.integers(19,29,n) if blind_recovery else np.full(n,24)))

def mocaps(task,c):
    n=len(c["key"])
    pos=np.zeros((n,2,3),np.float32)
    pos[:,:,0]=5.
    pos[:,:,2]=-.5
    if task not in TERRAIN:return pos
    h,e,w=c["h"],c["edge"],c["tread"]
    if task in DESC:
        pos[:,0,0]=e-.8
        pos[:,0,2]=(2 if task in DOUBLE else 1)*h-.24
        if task in DOUBLE:
            # Second box covers the lower tread; its overlap lies wholly beneath the top block.
            pos[:,1,0]=e+w-.8
            pos[:,1,2]=h-.24
    else:
        pos[:,0,0]=e+.8
        pos[:,0,2]=h-.24
        if task in DOUBLE:
            pos[:,1,0]=e+w+.8
            pos[:,1,2]=2*h-.24
    return pos

def smooth(x):
    u=np.clip(x,0.,1.)
    return u*u*(3.-2.*u)

def drive_refs(t,key):
    v=.26*smooth((t-.12)/.45)*(1-smooth((t-1.28)/.36))-.14*smooth((t-1.7)/.35)*(1-smooth((t-2.73)/.30))
    yaw=key*(.45*smooth((t-.46)/.32)*(1-smooth((t-1.22)/.33))-.30*smooth((t-1.75)/.3)*(1-smooth((t-2.60)/.27)))
    return np.broadcast_arrays(v,yaw)

def observation(task,raw,c,i,last):
    x=np.empty((len(raw),33),np.float32)
    x[:,:22]=raw[:,:22]
    x[:,0]=(c["edge_obs"]-raw[:,0])*2 if task in TERRAIN else raw[:,0]*2
    x[:,1]=raw[:,1]*3
    x[:,22]=c["h_obs"]*10 if task in TERRAIN else c["key"]/(100. if task=="forward_jump" else 3. if task=="lift" else 1.)
    x[:,23]=i/horizon(task)
    x[:,24:32]=last
    if task=="recover":
        mask=c["blind"].astype(bool)
        x[mask,22]=0.
        x[mask,23]=0.
    if task in DOUBLE:x[:,32]=c["tread"]*3.
    elif task=="brake":x[:,32]=c["grade"]/10.
    else:x[:,32]=np.maximum(0.,1.-np.abs(x[:,0]-.40)*3.) if task in TERRAIN else 0.
    return np.clip(np.nan_to_num(x),-5.,5.)

def commands(task,x,neural):
    """Return servo inputs: hip = -7+29*a degrees, wheel tread speed = .22+.40*a m/s."""
    if task in PRETRAIN:return neural.astype(np.float32)
    t=x[:,23]*horizon(task)*PERIOD
    hip=np.full((len(x),4),-7.,np.float32)
    v=np.zeros_like(hip)
    gain=.46
    if task in DESC:
        e=x[:,0]/2.
        w=x[:,32]/3. if task in DOUBLE else 0.
        target=e+w+.34
        v[:]=(.37*smooth((t-.10)/.32)*np.clip(target/.13,0,1))[:,None]
        # Extend the pair dangling past the edge until the lower floor takes load.
        fore=np.array([1,1,-1,-1])
        wheel_dx=(.112+.11*np.cos(x[:,10:14]/2.-.12217305))*fore-e[:,None]
        phase=smooth((wheel_dx+.04)/.10)*(1.-smooth((wheel_dx-.10)/.12))
        if task in DOUBLE:
            dx2=wheel_dx-w[:,None]
            phase+=smooth((dx2+.04)/.10)*(1.-smooth((dx2-.10)/.12))
        hip+=12*phase
    elif task=="lift":
        corner=np.rint(x[:,22]*3).astype(int)
        lift=smooth((t-.55)/.45)*(1-smooth((t-2.3)/.45))
        preload=smooth((t-.18)/.42)*(1-smooth((t-2.75)/.42))
        row=np.arange(len(x))
        hip[row,corner]-=22*lift
        hip[row,corner^1]+=2*preload
        hip[row,corner^2]+=2*preload
        hip[row,corner^3]-=2*preload
        gain=.40
    elif task=="drive":
        speed,yaw=drive_refs(t,x[:,22])
        speed=speed+.35*(speed-x[:,5])
        yaw=yaw+.5*(yaw-x[:,9]*4.)
        v[:]=speed[:,None]+yaw[:,None]*np.array([-.205,.205,-.205,.205])
        gain=.32
    elif task=="brake":
        direction=x[:,22]
        speed=direction*.32*smooth((t-.12)/.32)*(1-smooth((t-1.35)/.14))
        v[:]=(speed+.55*(speed-x[:,5])+.20*np.sin(np.deg2rad(x[:,32]*10.)))[:,None]
        gain=.32
    elif task=="recover":
        v[:]=np.clip(-.8*x[:,5]-.9*x[:,0]/2.,-.20,.20)[:,None]
        gain=.42
    elif task=="forward_jump":
        target=x[:,22]*100.
        u=t-.90
        prep=-7.-21.*smooth((t-.24)/.40)
        ref=-28.+48.*smooth(u/.11)
        ref+=(-24.-ref)*smooth((u-.13)/.075)
        ref+=(-7.-ref)*smooth((u-.31)/.21)
        hip[:]=np.where(t<.90,prep,ref)[:,None]
        v[:]=((.28+.0017*target)*smooth((t-.12)/.4)*(1-smooth((t-1.03)/.39)))[:,None]
        gain=.48
    hip=np.clip(hip+29.*gain*neural[:,:4],-36.,22.)
    v=np.clip(v+.40*gain*neural[:,4:],-.60,.62)
    return np.concatenate(((hip+7.)/29.,(v-.22)/.40),axis=1).astype(np.float32)

def pulse(task,c,i):
    t=i*PERIOD
    if task not in ("lift","recover"):return np.zeros((len(c["key"]),2),np.float32)
    mask=(32<=i<35) if task=="lift" else ((i>=c["kick_start"])&(i<c["kick_start"]+3))
    return np.column_stack((c["pulse_x"]*mask,c["pulse"]*mask)).astype(np.float32)

def configuration(task,variant,validation=False):
    if validation:
        extra,mu,shift=[(.10,.61,(.003,-.002,.002)),(.32,.49,(-.004,.003,.004))][variant%2]
        grade=[-8.,8.,-4.,4.][variant%4] if task=="brake" else 0.
    else:
        extra,mu,shift=[(.14,.64,(0.,0.,0.)),(.34,.47,(.004,-.003,.003))][variant%2]
        grade=(-6.,6.)[variant%2] if task=="brake" else 0.
    return extra,mu,shift,grade

def flight_stats(tr,key,task):
    n=tr.shape[1]
    out=np.zeros(n)
    reach=np.zeros(n,bool)
    duration=np.zeros(n)
    com=np.zeros(n)
    clearance=np.zeros(n)
    rebound=np.zeros(n)
    air=(tr[:,:,:13].sum(2)<.5)&(tr[:,:,13:17].min(2)>0.)
    air[:100]=False
    changes=np.diff(np.pad(air.astype(np.int8),((1,1),(0,0))),axis=0)
    for w in range(n):
        starts=np.flatnonzero(changes[:,w]==1); ends=np.flatnonzero(changes[:,w]==-1)
        for a,b in zip(starts,ends):
            if b-a<10 or b+10>=len(tr):continue
            delta=1000.*(tr[b,w,27]-tr[a,w,27])
            rise=1000.*(tr[a:b,w,22].max()-tr[a,w,22])
            if not duration[w]:
                out[w]=delta; duration[w]=(b-a)*2.; com[w]=rise
                clearance[w]=tr[a:b,w,13:17].min(1).max()
            else:rebound[w]=max(rebound[w],(b-a)*2.)
            if task=="leap_step":
                lo=tr[max(0,a-60):a,w]
                contact=np.flatnonzero(tr[b:,w,:12].sum(1)>1.)
                if len(lo) and len(contact):
                    land=b+contact[0]
                    if (lo[:,:4].sum(1).max()>1. and tr[:a,w,4:8].sum(1).max()<1.
                        and tr[land:land+5,w,4:8].sum(1).max()>1. and tr[land:,w,:4].sum(1).max()<1.
                        and tr[a:b,w,13:17].min(1).max()>2.):
                        reach[w]=True
    return out,duration,com,reach,rebound,clearance

def score(task,tr,c):
    # tr is the full 2 ms physical trace, including contact forces, not policy ticks.
    active=tr[100:];late=tr[-175:]
    valid=np.isfinite(tr).all(axis=(0,2))&(tr[:,:,29].max(0)==0)
    gap=active[:,:,26].max(0);hull=active[:,:,12].max(0)
    speed=np.linalg.norm(late[:,:,[23,30,31]],axis=2).max(0)
    tilt=late[:,:,21].max(0)
    stable=(speed<.10)&(tilt<=5)&(np.ptp(late[:,:,21],axis=0)<1)
    base=valid&(gap<.8)&(hull<2.)
    key=c["key"];n=len(key)
    floor=late[:,:,:4];top=late[:,:,4:8]
    four=((floor+top)>1).all(2).mean(0)>.95
    result=dict(valid=valid,gap_mm=gap,hull_N=hull,stable=stable,speed=speed)
    if task in TERRAIN:
        last_edge=c["edge"]+(c["tread"] if task in DOUBLE else 0.)
        on=((floor if task in DESC else top)>1.).all(2).mean(0)>.95
        reached=on&(late[:,:,19:21].min((0,2))>=last_edge+.05)
        # Route width is 0.92 m; the chassis stays well inside the two side edges.
        route=np.max(np.abs(tr[:,:,28]),axis=0)<.20
        reached &= route
        extra=np.ones(n,bool)
        if task in DESC:
            start=(tr[70:95,:,4:8]>1.).all(2).mean(0)>.95
            supports=((active[:,:,:4]+active[:,:,4:8])>1).sum(2).min(0)
            extra &= start&(supports>=2)&(active[:,:,21].max(0)<=12.)
            result.update(min_support=supports)
        if task in DOUBLE:
            # Probe the lower/first tread by horizontal location and tyre bottom height.
            in_tread=(tr[:,:,17:21]>c["edge"][None,:,None]+.012)&(tr[:,:,17:21]<(c["edge"]+c["tread"])[None,:,None]-.012)
            correct_z=np.abs(tr[:,:,13:17]-1000*c["h"][None,:,None])<5.
            # double_down: the midpoint is the second box; double_up: the first box.
            mid_force=tr[:,:,:4] if task=="double_up" else tr[:,:,4:8]
            touched=(in_tread&correct_z&(mid_force>1.)).sum(0)>=5
            extra &= touched.all(1)
            result.update(mid_wheels=touched.sum(1))
        if task=="leap_step":
            dx,ms,h,leap,_,_=flight_stats(tr,key,task)
            extra &= leap
            result.update(single_flight=leap,flight_ms=ms,air_travel_mm=dx)
        if task=="wheel_over":
            x=tr[:,:,17:21]-c["edge"][None,:,None]
            crossing=(x[:-1]<0)&(x[1:]>=0)
            unloaded=(tr[:,:,:4]+tr[:,:,4:8]+tr[:,:,8:12])<1.
            clear=tr[:,:,13:17]>1000*c["h"][None,:,None]+1.
            cleared=(crossing&unloaded[:-1]&unloaded[1:]&clear[:-1]&clear[1:]).any(0)
            extra &= cleared.all(1)
            result.update(cleared_wheels=cleared.sum(1))
        success=base&stable&reached&extra
        result.update(reached=reached,rear_margin_mm=1000*(late[:,:,19:21].min((0,2))-last_edge))
    elif task=="lift":
        hold=tr[550:1050]
        idx=np.arange(n)
        clear=hold[:,idx,13+key].min(0)
        load=np.stack([hold[:,idx,key^i] for i in (1,2,3)]).min((0,1))
        target=(clear>=23)&(load>=1.)&(active[:,:,21].max(0)<=5.)
        success=base&stable&four&target
        result.update(reached=target,held_clear_mm=clear,min_other_N=load)
    elif task=="brake":
        ref=tr[675,:,27]
        sign=key
        v=(tr[425:650,:,23]*sign).mean(0)
        overshoot=abs(tr[675:,:,27]-ref).max(0)
        creep=np.ptp(tr[1300:,:,27],axis=0)
        target=(v>=.25)&(overshoot<=.07)&(creep<=.03)&(speed<.035)
        success=base&stable&four&target
        result.update(reached=target,braking_m=overshoot,creep_m=creep,approach_mps=v)
    elif task=="drive":
        times=np.arange(len(tr))[:,None]*DT
        v,y=drive_refs(times,key[None,:])
        vr=np.mean((tr[:,:,23]-v)**2,axis=0)**.5
        yr=np.mean((tr[:,:,24]-y)**2,axis=0)**.5
        target=(vr<.035)&(yr<.10)
        success=base&stable&four&target
        result.update(reached=target,linear_rmse=vr,yaw_rmse=yr)
    elif task=="recover":
        early=tr[865:1000]
        pos=np.linalg.norm(early[:,:,[27,28]],axis=2).max(0)
        settled=(np.linalg.norm(early[:,:,[23,30,31]],axis=2).max(0)<.05)&(early[:,:,21].max(0)<3.)
        target=settled&(pos<.06)&(np.linalg.norm(late[:,:,[27,28]],axis=2).max(0)<.06)
        success=base&stable&four&target
        result.update(reached=target,recovery_drift_m=pos)
    else:
        dx,ms,h,_,rebound,clear=flight_stats(tr,key,task)
        target=(dx>=key)&(ms>=20)&(h>=10)&(rebound<=30)&(clear>=10)
        success=base&stable&four&target
        result.update(reached=target,flight_ms=ms,air_travel_mm=dx,com_rise_mm=h)
    result["clean"]=success
    return result
