"""Vertical take-off screening. Two vertical masses and distributed swinging links."""
from design import *
from collections import Counter
import csv,json
import numpy as np
meta=json.loads((ROOT/'data'/'geometry.json').read_text())
g=9.81;ell=L/1000;radius=.050
# kg, PETG effective occupancy is an estimate; catalog masses override envelope volumes.
def mass(t):
    id=t['id'];v=meta[id]['volume_mm3']*1e-9
    # 78 g for tyre and rim together; 58/20 is a layout split only.
    if id in ('XT100_Tyre','XT100_Rim','XT8_Coupler','XT8_Screw'):
        return {'XT100_Tyre':.058,'XT100_Rim':.020,'XT8_Coupler':.012,'XT8_Screw':.002}[id]
    if id in ('M01','M02','H03'):return {'M01':.370,'M02':.205,'H03':.012}[id]
    screw_g={'S01':0.8,'S02':1.2,'S03':0.75,'S04':1.8,'S05':3.7,'S06':1.9}
    if id in screw_g:return screw_g[id]/1000
    if id=='H05':return math.pi/4*(12**2-8.2**2)*8*2.7e-6
    density=1270*.82 if id.startswith('P') else 1200 if id=='H13' else 2700 if id in ('H01','H04','H08') else 1250 if id=='H09' else 7850
    return v*density
counts=Counter(t['id'] for t in INST)
weight={k:sum(mass(t) for t in INST if t['g']==k) for k in ['base','drive','passive','carrier','wheel']}
def mean_link(g):
    items=[t for t in INST if t['g']==g];m=sum(map(mass,items));r=sum(mass(t)*(t['x']+meta[t['id']]['center'][0])/1000 for t in items)/m
    # Conservative transverse inertia for this thin link, including end hardware separately.
    moment=sum(mass(t)*((t['x']+meta[t['id']]['center'][0])/1000-r)**2+
               mass(t)*(meta[t['id']]['bounds'][0]**2+meta[t['id']]['bounds'][1]**2)*1e-6/12 for t in items)
    return m,r,moment
links=[mean_link(k) for k in ['drive','passive']]
mu=weight['wheel']+weight['carrier']
def bounds(speed,voltage):
    # Screening curve anchored at rated and no-load data; not an OEM efficiency map.
    rpm=np.abs(speed)*60/(2*math.pi);scaled=rpm*24/voltage
    return 5.2*np.clip((232-scaled)/(232-120),0,1)
def study(total=6.,share=.25,h=.03,V=24.,loss=.83,extra_I=.0007,drag=.12):
    # Extra load is assigned to sprung mass, with the same wheel end assembly.
    m=total*share;mb=m-mu-sum(z[0] for z in links);assert mb>0
    beta=(mb+sum(mj*(1-r/ell) for mj,r,I in links))/m
    jrot=.00055  # conservative rolling inertia allowance incl. unmeasured drivetrain; 78 g at R50 alone would give <=0.000195
    A=mb*ell**2+sum(mj*(ell-r)**2 for mj,r,I in links)
    B=mu*ell**2+sum(mj*r*r for mj,r,I in links)+jrot*(ell/radius)**2
    J0=extra_I+sum(I for mj,r,I in links)
    lo,hi=np.radians([Q0,Q1]);stroke=beta*ell*(np.sin(hi)-np.sin(lo));v=np.sqrt(2*g*h)
    T=(-v/2+np.sqrt((v/2)**2+g*stroke/3))/(g/6)
    amp=np.pi/2*(v/T+g/2);u=np.linspace(0,1,301)
    com=T*T*(amp*(u/np.pi-np.sin(np.pi*u)/np.pi**2)-g*u**3/6)
    vel=T*(amp*(1-np.cos(np.pi*u))/np.pi-g*u**2/2)
    acc=amp*np.sin(np.pi*u)-g*u
    q=np.arcsin(np.sin(lo)+com/(beta*ell));qd=vel/(beta*ell*np.cos(q))
    qdd=(acc/(beta*ell)+np.sin(q)*qd**2)/np.cos(q)
    M=A*np.cos(q)**2+B*np.sin(q)**2+J0
    tau=M*qdd+(B-A)*np.sin(q)*np.cos(q)*qd**2+m*g*beta*ell*np.cos(q)
    # Magnitude allowance for bearing/transmission drag. Includes backdrive demand at release.
    demand=np.abs(tau)/loss+.12+np.abs(ell*np.sin(q)/radius)*drag
    rpm=qd*60/(2*np.pi);capacity=bounds(qd,V);min_i=int(np.argmin(capacity/np.maximum(demand,.001)))
    speed_limit=(232-(232-120)*np.clip(demand/5.2,0,1))*V/24
    reserve=speed_limit/np.maximum(rpm,.001);wheel_rpm=ell*np.sin(q)*qd/radius*60/(2*np.pi)
    normal=m*(g+acc)
    # Wheel-only screen for negligible longitudinal ground traction. The reflected
    # gearbox inertia is not published; report the maximum compatible total inertia.
    wheel_acc=ell/radius*(np.cos(q)*qd**2+np.sin(q)*qdd)
    wheel_demand=jrot*np.abs(wheel_acc)+drag
    wheel_cap=38*.0980665*np.clip(1-np.abs(wheel_rpm)/(122*.90),0,1)
    wheel_J_limit=float(np.min((wheel_cap-drag)/np.maximum(np.abs(wheel_acc),.001)))
    keys=['t_ms','q_deg','body_mm','com_mm','com_mps','normal_N','tau_ideal_Nm','demand_Nm','rpm','wheel_rpm','available_Nm','voltage','wheel_alpha_rad_s2','wheel_demand_Nm','wheel_screen_Nm']
    rows=np.column_stack([1000*T*u,np.degrees(q),com/beta*1000,com*1000,vel,normal,tau,demand,rpm,wheel_rpm,capacity,np.full_like(u,V),wheel_acc,wheel_demand,wheel_cap])
    out=dict(total=total,share=share,h_mm=h*1000,V=V,beta=beta,ms=1000*T,stroke_body_mm=stroke*1000/beta,stroke_com_mm=stroke*1000,
        takeoff_mps=v,body_takeoff_mps=v/beta,peak_tau=float(max(demand)),peak_rpm=float(max(rpm)),peak_wheel_rpm=float(max(abs(wheel_rpm))),
        peak_force=float(max(normal)),worst_factor=float(capacity[min_i]/demand[min_i]),speed_factor=float(min(reserve)),
        critical_deg=float(np.degrees(q[min_i])),critical_rpm=float(rpm[min_i]),critical_tau=float(demand[min_i]),critical_cap=float(capacity[min_i]),
        critical_ms=float(1000*T*u[min_i]),max_I=extra_I,efficiency=loss,drag=drag,
        at_takeoff_rpm=float(rpm[-1]),contact_end_force=float(normal[-1]),max_power=float(max(np.abs(qd*demand))),
        release_tau=float(tau[-1]),limit_kind='rated-envelope-assumption',peak_wheel_tau=float(max(wheel_demand)),
        wheel_factor=float(min(wheel_cap/wheel_demand)),wheel_J_limit=wheel_J_limit)
    return out,keys,rows
scenarios=[('nominal',{}),('low_bus',dict(V=20.7)),('heavy_corner',dict(share=.32,V=20.7)),('higher_losses',dict(share=.32,V=20.7,loss=.72,extra_I=.0015,drag=.25)),('20mm',dict(h=.02)),('50mm',dict(h=.05))]
out={};motion={}
for key,settings in scenarios:
    s,head,rows=study(**settings);out[key]=s;motion[key]=rows[::3].round(5).tolist()
    if key=='nominal':
        with (ROOT/'data'/'蹬伸逐时刻.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(head);w.writerows(rows.round(6))
data=dict(groups_kg=weight,module_kg=sum(weight.values()),remaining_kg=6-4*sum(weight.values()),links=links,unsprung_kg=mu,scenarios=out,head=head,series=motion)
# Flight with front/back mirror symmetry. CoM is ballistic; wheel spin is free.
def airborne(s,stop_s=.024):
    m=s['total']*s['share'];mb=m-mu-sum(row[0] for row in links);beta=s['beta']
    A=mb*ell**2+sum(mj*(ell-r)**2 for mj,r,I in links)-m*(beta*ell)**2
    B=mu*ell**2+sum(mj*r**2 for mj,r,I in links)
    J=s['max_I']+sum(I for mj,r,I in links)
    q0=math.radians(Q1);qd0=s['at_takeoff_rpm']*math.tau/60
    stop_q=q0+qd0*stop_s/2;v=s['takeoff_mps']
    cost=beta*ell*(math.sin(stop_q)-math.sin(q0))
    end=(v+math.sqrt(v*v-2*g*cost))/g
    t=np.unique(np.r_[np.linspace(0,end,401),stop_s,v/g]);t1=np.minimum(t,stop_s)
    q=q0+qd0*(t1-t1**2/(2*stop_s));qd=qd0*(1-t1/stop_s);qdd=np.where(t<stop_s,-qd0/stop_s,0.)
    com=v*t-g*t*t/2;clearance=com-beta*ell*(np.sin(q)-math.sin(q0))
    torque=(A*np.cos(q)**2+B*np.sin(q)**2+J)*qdd+(B-A)*np.sin(q)*np.cos(q)*qd**2
    demand=np.abs(torque)/s['efficiency']+.12
    factor=bounds(qd,s['V'])/demand
    with (ROOT/'data'/'离地至触地估算.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['flight_ms','q_deg','rpm','com_rise_mm','wheel_clearance_mm','hip_braking_demand_Nm','assumed_factor'])
        w.writerows(np.column_stack([t*1000,np.degrees(q),qd*60/math.tau,com*1000,clearance*1000,demand,factor]).round(6))
    assert np.min(clearance)>-1e-8 and t[-1]>v/g and abs(clearance[-1])<1e-8
    return dict(stop_ms=stop_s*1000,stop_deg=math.degrees(stop_q),clearance_mm=max(clearance)*1000,
                landing_ms=end*1000,peak_brake_Nm=max(demand),min_factor=min(factor),landing_velocity_mps=v-g*end)
data['flight']=airborne(out['nominal'])
(ROOT/'data'/'dynamics.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
print({k:tuple(round(v[f],3) for f in ['peak_tau','peak_rpm','worst_factor','speed_factor']) for k,v in out.items()})
print('module, available, unsprung',data['module_kg'],data['remaining_kg'],mu)
