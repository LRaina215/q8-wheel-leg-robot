"""Signed separation of the exported rear P01 triangles and the finite step.
Positive = gap, negative = geometric overlap in the recorded assembly pose.
"""
import base64,gzip,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).parent
CAD=ROOT.parent/'ppo-highjump-fUGFdEDX'/'step_video'/'render_meshes.json.gz'
def read_plate():
    data=(ROOT/'P01.stl').read_bytes()
    rec=np.dtype([('normal','<f4',3),('v','<f4',(3,3)),('attr','<u2')])
    tri=np.frombuffer(data,dtype=rec,offset=84)['v'].astype(float)
    v,inv=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True)
    f=inv.reshape(-1,3)
    pairs=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[0,2]]]);pairs=np.unique(np.sort(pairs,axis=1),axis=0)
    with gzip.open(CAD,'rt') as stream:scene=json.load(stream)
    inst=next(item for item in scene['inst'] if item['id']=='P01')
    assert [inst[k] for k in ('x','y','z','rot','flip')]==[0,0,0,0,False]
    ref=np.frombuffer(base64.b64decode(scene['mesh']['P01'][0]),'<f4').reshape(-1,3).astype(float)
    # The print export of P01 translates the original shape onto the print bed.
    v+=.5*(ref.max(0)+ref.min(0)-v.max(0)-v.min(0))
    theta=np.arange(64)*np.pi/32
    direct=np.stack([np.cos(theta),np.sin(theta)],-1)
    registration=float(np.max(abs((v[:,:2]@direct.T).max(0)-(ref[:,:2]@direct.T).max(0))))
    assert registration<.15,registration
    local=[(np.column_stack([-v[:,0],s*v[:,2],v[:,1]])+[-112.,s*119.,0.])*.001 for s in (1,-1)]
    return local,pairs,dict(triangles=len(tri),projected_outer_boundary_difference_mm=registration)
def gap(points,pairs,edge,height=.15):
    if abs(points[:,1]).max()>=.46 or points[:,0].max()>=edge+1.6:
        raise ValueError('other platform sides need clipping')
    # In x-z the solid occupies the negative-negative quadrant in these coordinates.
    a=np.column_stack([edge-points[:,0],points[:,2]-height])
    def sd(q):
        return np.linalg.norm(np.maximum(q,0.),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0.)
    minimum=sd(a).min()
    p=a[pairs[:,0]];delta=a[pairs[:,1]]-p
    # On an edge the signed distance is piecewise linear or distance to the corner.
    # Check regime boundaries and the closest point on the corner-distance piece.
    for num,den in [(-p[:,0],delta[:,0]),(-p[:,1],delta[:,1]),(p[:,1]-p[:,0],delta[:,0]-delta[:,1]),
                    (-(p*delta).sum(1),(delta*delta).sum(1))]:
        t=np.divide(num,den,out=np.zeros_like(num),where=abs(den)>1.e-16)
        mask=(t>0.)&(t<1.)
        if mask.any():minimum=min(minimum,sd(p[mask]+t[mask,None]*delta[mask]).min())
    return float(minimum*1000.)
def analyze(path,local,pairs,info):
    rows=[]
    for r in json.loads(path.read_text()):
        if r['fork_s'] is None:continue
        for event,frame in r['poses'].items():
            t=np.asarray(frame['body'][:3]);rot=np.asarray(frame['body'][3:]).reshape(3,3)
            g=[gap(v@rot.T+t,pairs,r['edge']) for v in local]
            rows.append(dict(domain=r['domain'],case=r['case'],event=event,t=frame['t'],gap_mm=g,step_fx_N=frame['plate_fx']))
    (ROOT/(path.stem+'_mesh.json')).write_text(json.dumps(dict(registration=info,rows=rows)))
if __name__=='__main__':
    local,pairs,info=read_plate()
    for arg in sys.argv[1:]:analyze(Path(arg),local,pairs,info)
