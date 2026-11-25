from common import *
import loads,re
d=ROOT/'data'
s=read(d/'a1_filament.json');mass={}
for plate in s:
    for name,g in plate['object_grams'].items():
        key=Path(name).stem.removeprefix('LH_')
        key=re.sub(r'\d+$','',key) if not key.startswith('P') else key.split('_')[0]
        mass.setdefault(key,[]).append(g/1000)
avg={k:float(np.mean(v)) for k,v in mass.items()}
eng=loads.engine
old=eng.mass
eng.mass=lambda t:avg[t['id']] if t['id'] in avg else old(t)
eng.links=[eng.mean_link(k) for k in ['drive','passive']]
loads.mu=eng.mu=sum(eng.mass(t) for t in leg.INST if t['g'] in ['wheel','carrier'])+loads.loop_mass*loads.moving_fraction
for k,m in avg.items():
    if k in loads.parts:
        p=loads.parts[k];p.update(mass=m,low=m*.94,high=m*1.06,source='A1 切片成品挤出路径；含 ±6% 估值区间')
old_csv=loads.csvwrite
loads.csvwrite=lambda name,head,rows:old_csv(name.replace('_base','_slice').replace('_MID','_slice_MID'),head,rows)
r=loads.report(False);a=read(d/'analysis.json');a['slice']=r;a['slice_mid']=loads.report(True);write(d/'analysis.json',a)
small=loads.report(False,target_h=.020,emit=False)
n=small['heaviest']
write(d/'20mm质心低跳.json',dict(target_mm=20,heaviest=n,mass=small['mass'],nominal=small['cases']['22V2'][n],adverse=small['cases']['loss_diagonal'][n],clear24_mm=small['brake']['clearance'],clear32_mm=small['slow_brake']['clearance']))
print(r['mass'],r['central'],r['static']['-7']['kg'],r['cases']['22V2']['FL'],r['cases']['loss_diagonal']['FL']['factor'],r['brake']['clearance'],r['slow_brake']['clearance'],flush=True)
