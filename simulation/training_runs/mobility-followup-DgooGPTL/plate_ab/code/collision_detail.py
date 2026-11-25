"""Locate the first structure contact and the strongest contact in each pilot replay."""
from pathlib import Path
import json,sys,os
import mujoco as mj
import numpy as np
from onnx import load
from onnx.reference import ReferenceEvaluator
from night_tasks import configuration
import stage_native
from stage_signals import Signals
from stage_task import cases

class Detailed(Signals):
    def __init__(self,m,n):
        super().__init__(m,n)
        self.first=None;self.peak=None;self.touched={}
    def sample(self,k,m,d,ix,a,limit,velocity,platform):
        super().sample(k,m,d,ix,a,limit,velocity,platform)
        if k<120 or a[12]<=2.:return
        floor=m.geom('ground').id
        terrain={floor,platform,m.geom('second_step').id}
        hit=[]
        for ci,ct in enumerate(d.contact):
            g1,g2=int(ct.geom1),int(ct.geom2)
            if g2 in terrain:g1,g2=g2,g1
            if g1 not in terrain or g2 in ix[5]:continue
            mj.mj_contactForce(m,d,ci,self.force)
            name=m.geom(g2).name or str(g2)
            part='floor' if g1==floor else ('top' if abs(ct.frame[2])>.85 else 'riser_or_edge')
            item=(float(self.force[0]),name,part)
            hit.append(item)
        if not hit:return
        strongest=max(hit)
        event=dict(t_s=k*.002,total_N=float(a[12]),part=strongest[1],surface=strongest[2],
                    strongest_N=strongest[0],rear_x_mm=(1000*a[19:21]).tolist(),
                    rear_z_mm=a[15:17].tolist())
        if self.first is None:self.first=event
        if self.peak is None or a[12]>self.peak['total_N']:self.peak=event
        for item in {(n,p) for f,n,p in hit if f>1}:
            name='/'.join(item);self.touched[name]=self.touched.get(name,0)+2
    def results(self,tr,c):
        r=super().results(tr,c)
        for event in (self.first,self.peak):
            if event is not None and 'rear_x_mm' in event:
                event['rear_dx_mm']=[round(x-1000*c['edge'][0],1) for x in event.pop('rear_x_mm')]
        r.update(first_structure=self.first,peak_structure=self.peak,contact_ms_by_part=self.touched)
        return r
def main(label):
    root=Path(__file__).resolve().parent.parent
    session=ReferenceEvaluator(load(str(root/label/'actor_best.onnx')))
    actor=lambda o:session.run(None,{'obs':o})[0]
    rows=[]
    stage_native.Signals=Detailed
    for dom in (0,1):
        cfg=configuration('soft_up',dom,True)
        bank=cases('soft_up',8,6503129+dom*131,0)
        for j in range(8):
            c={k:v[j:j+1] for k,v in bank.items()}
            s,z=stage_native.replay('soft_up',cfg,c,actor)
            rows.append(dict(domain=dom,index=j,score=s,detail=z))
    (root/(label+'_contacts.json')).write_text(json.dumps(rows,allow_nan=False))
if __name__=='__main__':main(sys.argv[1])
