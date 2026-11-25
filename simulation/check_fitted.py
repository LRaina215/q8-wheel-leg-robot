"""Verify masses, local centres/tensors and cruise COM from the serialized files."""
from pathlib import Path
import csv,json,math
import xml.etree.ElementTree as ET
import mujoco as mj
import numpy as np
from pilot import set_pose
H=Path(__file__).resolve().parent
u=ET.parse(H/"q8_r5_fitted.urdf").getroot()
m=mj.MjModel.from_xml_string((H/"q8_r5_fitted.xml").read_text(encoding="utf8"))
links={l.get('name'):l for l in u.findall('link')}
assert len(links)==len(u.findall('link'))
fixed={}
for j in u.findall('joint'):
    if j.get('type')=='fixed':
        fixed[j.find('child').get('link')]=(j.find('parent').get('link'),np.fromstring(j.find('origin').get('xyz'),sep=' '))
groups={}
for name,l in links.items():
    target,delta=fixed.get(name,(name,np.zeros(3)))
    i=l.find('inertial');p=np.fromstring(i.find('origin').get('xyz'),sep=' ')+delta
    mass=float(i.find('mass').get('value'));a=i.find('inertia');T=np.array([[float(a.get('i'+''.join(sorted((x,y))))) for y in 'xyz'] for x in 'xyz'])
    groups.setdefault(target,[]).append((mass,p,T))
d=mj.MjData(m);set_pose(m,d,[-7]*4);errs=[];sum_world=np.zeros(3)
for name,rr in groups.items():
    b=m.body(name).id;mass=sum(a for a,_,_ in rr);c=sum(a*p for a,p,_ in rr)/mass
    T=sum(t+a*(np.dot(p-c,p-c)*np.eye(3)-np.outer(p-c,p-c)) for a,p,t in rr)
    R=np.zeros(9);mj.mju_quat2Mat(R,m.body_iquat[b]);R=R.reshape(3,3)
    errs.append([abs(mass-m.body_mass[b]),np.linalg.norm(c-m.body_ipos[b]),np.max(abs(T-R@np.diag(m.body_inertia[b])@R.T))])
    sum_world+=mass*(d.xpos[b]+d.xmat[b].reshape(3,3)@c)
em,ec,ei=np.max(errs,axis=0);assert em<1e-8 and ec<1e-8 and ei<1e-7,(em,ec,ei)
rows=list(csv.DictReader((H/'R5_装车质量明细.csv').open(encoding='utf-8-sig')))
by={};per_part_g=[];per_part_mm=[]
for r in rows:
    if r['配置']!='首车':continue
    by[r['部件']]=by.get(r['部件'],0)+float(r['质量g'])/1000
    name=r['URDF链接名'];i=links[name].find('inertial');target,offset=fixed.get(name,(name,np.zeros(3)))
    assert target==r['刚体']
    per_part_g.append(abs(1000*float(i.find('mass').get('value'))-float(r['质量g'])))
    c=np.fromstring(i.find('origin').get('xyz'),sep=' ')+offset
    per_part_mm.append(np.linalg.norm(1000*c-[float(r[k]) for k in ['局部质心x mm','y mm','z mm']]))
assert max(per_part_g)<.00001 and max(per_part_mm)<.00015
total=sum(m.body_mass);assert len(links)==sum(r['配置']=='首车' for r in rows) and abs(sum(by.values())-total)<1e-5
cg=sum_world/total-d.xpos[m.body('chassis').id]
err=np.linalg.norm(cg-(d.subtree_com[m.body('chassis').id]-d.xpos[m.body('chassis').id]));assert err<5e-8
report=dict(total_kg=total,optional_mid_delta_kg=sum(float(r['质量g']) for r in rows if r['配置']!='首车')/1000,
    cruise_CG_mm=(cg*1000).tolist(),URDF_inertial_parts=len(links),equivalent_rigid_bodies=len(groups),
    max_mass_error_kg=em,max_local_cg_error_mm=ec*1000,max_inertia_error_kgm2=ei,
    max_part_to_ledger_g=max(per_part_g),max_part_to_ledger_cg_mm=max(per_part_mm),
    parts_kg=by,links_kg={n:float(m.body_mass[m.body(n).id]) for n in groups},
    mass_scope='Base fitted estimate, MID excluded; simulated agreement, no physical weigh-in.')
(H/'mass_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(total,cg,em,ec,ei)

