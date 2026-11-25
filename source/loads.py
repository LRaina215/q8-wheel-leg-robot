from common import *
import csv, types
engine=types.ModuleType('single_leg_model')
ref=(LEG/'source'/'engineering.py').read_text(encoding='utf8')
exec(compile(ref.split('scenarios=[')[0],'single_leg_dynamics','exec'),engine.__dict__)
spec=read(ROOT/'data'/'layout.json');parts=spec['parts'];inst=spec['instances'];gm=read(LEG/'data'/'geometry.json')
g=9.81;ell=.110;mu=engine.mu
cables=read(ROOT/'data'/'整车线束.json')
loops={r['a'][:2]:np.array([np.mean(frame,axis=0) for frame in r['frames']]) for r in cables['routes'] if 'frames' in r}
loop_mass=parts.get('LegHarness',{}).get('mass',0)
moving_fraction=(loops['FL'][0,2]-loops['FL'][-1,2])/(110*(math.sin(math.radians(33))-math.sin(math.radians(-36))))
mu=engine.mu=engine.mu+loop_mass*moving_fraction
def csvwrite(name,head,rows):
    with (ROOT/'data'/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(head);w.writerows(rows)
def get_center(t):
    return np.asarray(t['pos'])+xyzrot(t['rz']) @ np.array(parts[t['id']]['com'])
def legcom(q,side,fwd):
    points=[];masses=[];h=side*fwd
    for t in leg.INST:
        grp=t['g'];x,y,ang=leg.group_pose(grp,q);c=np.array(gm[t['id']]['center'],dtype=float)
        if t['flip']:c[1:]*=-1
        c=xyzrot(t['rot'])@c+np.array([t['x'],t['y'],t['z']])
        c=xyzrot(ang)@c+np.array([x,y,0]);c[0]*=h
        points.append(leg_basis(side)@c+np.array([side*HX,fwd*HY,0]));masses.append(engine.mass(t))
    tag=('F' if fwd>0 else 'R')+('R' if side>0 else 'L')
    curve=loops[tag];points.append([np.interp(q,np.arange(-36,34),curve[:,i]) for i in range(3)]);masses.append(loop_mass)
    return np.average(points,axis=0,weights=masses),sum(masses)
def budget(opt):
    rows=[];xyz=np.zeros(3);central=np.zeros(3);mass=0
    for t in inst:
        if t['id']=='LegHarness':continue
        if t['optional'] and not opt:continue
        p=parts[t['id']];c=get_center(t);mass+=p['mass'];central+=p['mass']*c
        rows.append([t['name'],p['name'],p['kind'],t['optional'],p['mass'],p['low'],p['high'],*c,p['source']])
    xyz=central.copy()
    for n,s,f in corner_order:
        c,w=legcom(-7,s,f);xyz+=w*c;mass+=w
        rows.append([n,'Q8 R3 成品轮轮腿','轮腿',False,w,w-.055,w+.055,*c,'手册、切片或体积、近似铜接头；±55g/角为参数敏感性'])
    return mass,xyz/mass,central,rows
def feet(q):
    return np.array([HX+leg.TYRE_CENTRE,HY+110*np.cos(np.radians(q))])
def report(opt,target_h=.030,emit=True):
    m,c,C,rows=budget(opt);tag='MID' if opt else 'base'
    if emit:csvwrite('质量与质心_'+tag+'.csv',['实例','部件','类别','选装','名义kg','下限kg','上限kg','X右mm','Y前mm','Z相对髋mm','依据'],rows)
    static={}
    for q in [-36,-7,22]:
        X,Y=feet(q);cg=(C+sum(legcom(q,s,f)[0]*legcom(q,s,f)[1] for _,s,f in corner_order))/m
        vals={n:float(m/4*(1+s*cg[0]/X+f*cg[1]/Y)) for n,s,f in corner_order}
        static[str(q)]=dict(kg=vals,center=cg.tolist(),foot=[X,Y])
    assert abs(sum(static['-7']['kg'].values())-m)<1e-8
    name=max(static['-7']['kg'],key=static['-7']['kg'].get)
    def trace(V,loss=.83,extra=.0007,drag=.12,d=.0):
        base,_,r=engine.study(total=m,share=.25,h=target_h,V=V,loss=loss,extra_I=extra,drag=drag)
        q=np.radians(r[:,1]);acc_com=r[:,5]/(m/4)-g;acc_body=acc_com/base['beta']
        rpm=r[:,8];cap=r[:,10];X,Y=HX+leg.TYRE_CENTRE,HY+110*np.cos(q)
        results={};history={}
        for n,s,f in corner_order:
            sign=1 if n==name or (n[0]!=name[0] and n[1]!=name[1]) else -1
            correction=(g+acc_body)*(s*C[0]/X+f*C[1]/Y)/4+sign*d*(g+acc_com)
            force=r[:,5]+correction
            tau=r[:,6]+correction*ell*np.cos(q)
            demand=abs(tau)/loss+.12+abs(ell*np.sin(q)/engine.radius)*drag
            fac=cap/demand;idx=int(np.argmin(fac));speedlimit=(232-112*np.clip(demand/5.2,0,1))*V/24
            negative=np.flatnonzero(force<-.01)
            results[n]=dict(peak=float(max(demand)),factor=float(min(fac)),speed_factor=float(min(speedlimit/np.maximum(.001,rpm))),speed_peak=float(max(rpm)),critical_rpm=float(rpm[idx]),critical_ms=float(r[idx,0]),critical_q=float(r[idx,1]),critical_cap=float(cap[idx]),maxforce=float(max(force)),first_negative_ms=float(r[negative[0],0]) if len(negative) else None)
            history[n]=np.vstack([force,demand,fac]).T
        return base,r,results,history
    cases={};chron=None
    for label,args in [('24V',(24,)),('22V2',(22.2,)),('20V7',(20.7,)),('diagonal',(20.7,.83,.0007,.12,.15)),('loss_diagonal',(20.7,.72,.0015,.25,.15))]:
        b,r,stats,hist=trace(*args);cases[label]=stats
        if label=='22V2':
            base=b;chron=r
            head=['t_ms','hip_deg','body_rise_mm','com_rise_mm','com_mps','hip_rpm','wheel_rpm']
            zz=[r[:,i] for i in [0,1,2,3,4,8,9]]
            for n,_,_ in corner_order:head+=['F_'+n,'Nm_'+n,'factor_'+n];zz.extend(hist[n].T)
            arr=np.column_stack(zz)
            if emit:csvwrite('整车蹬伸_'+tag+'.csv',head,arr.round(6))
            motion=arr[::3].round(5).tolist()
    def flight(dt):
        q0=math.radians(22);v=base['takeoff_mps'];w=base['at_takeoff_rpm']*math.tau/60
        d=base['beta']*ell*(math.sin(q0+w*dt/2)-math.sin(q0));end=(v+math.sqrt(v*v-2*g*d))/g
        tt=np.linspace(0,end,101);t1=np.minimum(dt,tt);q=q0+w*(t1-t1*t1/2/dt)
        c=v*tt-g*tt**2/2;z=c-base['beta']*ell*(np.sin(q)-math.sin(q0))
        # Vertical momentum is free after liftoff. Opposing wheels cancel longitudinal momentum
        # in the symmetric case; the wheel spin is free rather than constrained to roll on a floor.
        am=m/4;mb=am-mu-sum(k[0] for k in engine.links)
        A=mb*ell**2+sum(j*(ell-r)**2 for j,r,I in engine.links)-am*(base['beta']*ell)**2
        B=mu*ell**2+sum(j*r*r for j,r,I in engine.links)
        j0=.0007+sum(I for j,r,I in engine.links)
        sample=np.linspace(0,dt,151);ang=q0+w*(sample-sample**2/(2*dt));speed=w*(1-sample/dt)
        tau=-(A*np.cos(ang)**2+B*np.sin(ang)**2+j0)*w/dt+(B-A)*np.sin(ang)*np.cos(ang)*speed**2
        req=np.abs(tau)/.83+.12;cap=engine.bounds(speed,22.2)
        absorbed=4*np.maximum(-tau*speed,0)
        work=float(np.sum((absorbed[1:]+absorbed[:-1])/2*np.diff(sample)))
        return dict(stop=dt*1000,qstop=math.degrees(q0+w*dt/2),clearance=(v*v/2/g-d)*1000,landing=end*1000,brake_peak=float(max(req)),brake_factor=float(min(cap/req)),four_hip_negative_work_J=work,peak_negative_mechanical_W=float(max(absorbed)),brake_model='symmetric free flight; 22.2V motoring envelope used as unverified braking ceiling',
           samples=np.column_stack([tt*1000,np.degrees(q),z*1000,c*1000]).round(5).tolist())
    return dict(mass=m,central=sum(row[4] for row in rows[:-4]),range=[sum(r[5] for r in rows),sum(r[6] for r in rows)],cog=c.tolist(),static=static,heaviest=name,cases=cases,motion=motion,ms=base['ms'],beta=base['beta'],wheel_rpm=base['peak_wheel_rpm'],wheel_factor=base['wheel_factor'],brake=flight(.024),slow_brake=flight(.032))
if __name__=='__main__':
    data={key:report(opt) for key,opt in [('base',False),('mid',True)]}
    write(ROOT/'data'/'analysis.json',data)
    for k,v in data.items():
        n=v['heaviest'];print(k,v['mass'],v['range'],n,v['static']['-7']['kg'],v['cases']['24V'][n],v['cases']['loss_diagonal'][n]['factor'],v['brake']['clearance'])

