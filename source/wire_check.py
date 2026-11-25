"""Independent distance checks against displayed rigid triangles at all 70 leg angles."""
from wire_space import *
from wire_nets import M
from vtkmodules.vtkFiltersCore import vtkImplicitPolyDataDistance
from vtkmodules.vtkCommonCore import vtkDoubleArray
from scipy.spatial.distance import cdist
class Surface:
    def __init__(self,p,i):
        self.lo=p.min(0);self.hi=p.max(0)
        po=vtkPoints();po.SetData(numpy_to_vtk(np.ascontiguousarray(p,dtype=float),deep=True))
        ca=vtkCellArray();ca.SetData(numpy_to_vtkIdTypeArray(np.arange(0,i.size+1,3,dtype='int64'),deep=True),numpy_to_vtkIdTypeArray(np.ascontiguousarray(i.ravel(),dtype='int64'),deep=True))
        poly=vtkPolyData();poly.SetPoints(po);poly.SetPolys(ca)
        self.fn=vtkImplicitPolyDataDistance();self.fn.SetInput(poly)
    def gap(self,points,dist=14):
        near=points[((points>self.lo-dist)&(points<self.hi+dist)).all(1)]
        if not len(near):return 1000.
        # Evaluate at <=1 mm intervals on the wire; signed distance uses the original triangle winding.
        return min(self.fn.EvaluateFunction(p) for p in near)
def dense(p):
    p=np.array(p);ds=np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()]
    t=np.linspace(0,ds[-1],int(ds[-1])+2)
    return np.column_stack([np.interp(t,ds,p[:,k]) for k in range(3)])
def main():
    doc=read(data/'整车线束.json');ms={k:Surface(*v) for k,v in meshes('legmesh.bin').items()}
    stat,_=fields();records=[]
    # Legs are exact mirrors in Y and X. Check one local leg for its own mesh, every leg for the body.
    motion=[r for r in doc['routes'] if r['group']==M]
    for i,q in enumerate(range(-36,34)):
        p=dense(motion[0]['frames'][i]);p[:,0]*=-1
        local=np.column_stack([p[:,1]-HY,p[:,2],p[:,0]-HX])
        best=(1e3,'');closest_tyre=1e3
        for t in leg.INST:
            k=t['id'];x,y,ang=leg.group_pose(t['g'],q)
            a=(local-[x,y,0])@xyzrot(ang)-[t['x'],t['y'],t['z']]
            a=a@xyzrot(t['rot'])@np.diag([1,-1 if t['flip'] else 1,-1 if t['flip'] else 1])
            if k=='M02':a=a[:-12] # last 12 mm are the intended encoder plug approach, only for its own body
            d=ms[k].gap(a,55 if k=='XT100_Tyre' else 16)-4
            best=min(best,(d,k))
            if k=='XT100_Tyre':closest_tyre=d
        bd=min(float(distances(stat,dense(r['frames'][i])).min())-4-2.6 for r in motion)
        records.append(dict(q=q,leg_gap=round(best[0],2),part=best[1],tyre=round(closest_tyre,2),body_bound=round(bd,2)))
    print(min(records,key=lambda a:a['leg_gap']),min(r['tyre'] for r in records),min(r['body_bound'] for r in records),flush=True)
    rows=doc['routes']
    qa=dict(poses=records,base=sum(not r['optional'] for r in rows),option=sum(r['optional'] for r in rows),fixed_core_min=min(r['core_gap'] for r in rows if 'core_gap'in r),
       longest_exit=max(max(r['exit_mm']) for r in rows if 'exit_mm'in r),legs=4,wire_diameter=8)
    write(data/'线束间隙.json',qa)
if __name__=='__main__':main()
