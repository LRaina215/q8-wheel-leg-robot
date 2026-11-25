"""At an archived collision time, compare the actual P01 display triangles with the plane over the step footprint."""
import json,gzip,base64,sys
from pathlib import Path
import numpy as np
from onnx import load
from onnx.reference import ReferenceEvaluator
from stage_task import cases
from night_tasks import configuration
from record_native import replay
from stage_task import pose,decode
import record_native

def clearance(points,faces,edge,height):
    # The other three sides of the finite platform enclose the entire side plate.
    if np.abs(points[:,1]).max()>=.46 or points[:,0].max()>=edge+1.6:raise ValueError('clip other sides')
    inside=points[:,0]>=edge
    if not inside.any():return None
    zmin=points[inside,2].min()
    for i,j in [(0,1),(1,2),(2,0)]:
        a,b=points[faces[:,i]],points[faces[:,j]]
        mask=(a[:,0]>=edge)!=(b[:,0]>=edge)
        a,b=a[mask],b[mask]
        if len(a):
            z=a[:,2]+(b[:,2]-a[:,2])*(edge-a[:,0])/(b[:,0]-a[:,0])
            zmin=min(zmin,z.min())
    return float((zmin-height)*1000.)
def main():
    root=Path(__file__).resolve().parent.parent
    archive=root.parent/'stage-climb-y1o529Z5'
    source=root.parent/'ppo-highjump-fUGFdEDX'/'step_video'/'render_meshes.json.gz'
    with gzip.open(source,'rt') as f:scene=json.load(f)
    vertices,faces=scene['mesh']['P01']
    xyz=np.frombuffer(base64.b64decode(vertices),'<f4').reshape(-1,3)
    tri=np.frombuffer(base64.b64decode(faces),'<u4').reshape(-1,3)
    instance=next(i for i in scene['inst'] if i['id']=='P01')
    assert [instance[k] for k in ('x','y','z','rot','flip')]==[0,0,0,0,False]
    parts={}
    for name,side in [('FL_P01',1),('FR_P01',-1)]:
        matrix=np.array([[1,0,0],[0,0,side],[0,1,0]])
        parts[name]=(xyz@matrix.T+np.array([112,side*119,0]))*.001
    saved=json.loads((archive/'original_contacts.json').read_text())
    session=ReferenceEvaluator(load(str(archive/'original'/'actor_best.onnx')))
    actor=lambda x:session.run(None,{'obs':x})[0]
    record_native.pose=pose;record_native.commands=lambda t,x,u:decode(t,x,u,'direct')
    out=[]
    for r in saved:
        events={}
        for typ in ('first_structure','peak_structure'):
            event=r['detail'][typ]
            if event and event['part'] in parts:
                events.setdefault(round(event['t_s']/.002),[]).append((typ,event))
        if not events:continue
        dom,j=r['domain'],r['index']
        cfg=configuration('soft_up',dom,True)
        bank=cases('soft_up',8,6503129+dom*131,0)
        c={k:v[j:j+1] for k,v in bank.items()}
        def hook(k,m,d,ix,body,a,surfaces):
            for typ,event in events.get(k,[]):
                # Kinematic xmat/xpos and force agree with the archived 500 Hz frame.
                if not np.isclose(a[12],event['total_N'],atol=.01):raise ValueError('frame mismatch')
                name=event['part'];loc=parts[name];g=m.geom(name).id
                bound_err=max(abs((loc.min(0)+loc.max(0))*.5-m.geom_pos[g]).max(),abs((loc.max(0)-loc.min(0))*.5-m.geom_size[g]).max())
                # The collision proxy may be padded. Store differences explicitly.
                points=loc@d.xmat[body].reshape(3,3).T+d.xpos[body]
                gap=clearance(points,tri,c['edge'][0],c['h'][0])
                out.append(dict(domain=dom,case=j,event=typ,part=name,t_s=k*.002,collision_model_total_N=event['total_N'],actual_mesh_gap_mm=gap,bound_difference_mm=1000*bound_err))
        replay('soft_up',cfg,c,actor,hook)
    (root/'p01_mesh_check.json').write_text(json.dumps(out,allow_nan=False))
    print('P01 samples',len(out),flush=True)
if __name__=='__main__':main()
