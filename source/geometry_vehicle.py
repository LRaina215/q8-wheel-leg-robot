from layout import *
import base64,zlib
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkFiltersCore import vtkTriangleFilter,vtkQuadricDecimation,vtkCleanPolyData
from vtkmodules.util.numpy_support import vtk_to_numpy
import tempfile
def mesh_array(pts,idx):
    return [base64.b64encode(np.array(pts,dtype='<f4').tobytes()).decode(),base64.b64encode(np.array(idx,dtype='<u4').tobytes()).decode()]
def stl_mesh(path,target=11000):
    r=vtkSTLReader();r.SetFileName(str(path));r.Update();mesh=r.GetOutput()
    if mesh.GetNumberOfPolys()>target:
        d=vtkQuadricDecimation();d.SetInputData(mesh);d.SetTargetReduction(1-target/mesh.GetNumberOfPolys());d.Update();mesh=d.GetOutput()
    return mesh_array(vtk_to_numpy(mesh.GetPoints().GetData()),vtk_to_numpy(mesh.GetPolys().GetConnectivityArray()))
def make_geometry():
    cache=ROOT/'source'/'body_step';cache.mkdir(exist_ok=True);meta={};meshes={}
    for id,p in D.items():
        s=p['shape'];entry={k:v for k,v in p.items() if k!='shape'}
        if s is not None:
            s=s.clean();sol=s.Solids();assert s.isValid() and len(sol)==1,(id,len(sol))
            b=s.BoundingBox();entry['bbox']=[[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]]
            entry['com']=list(s.Center().toTuple());entry['volume_mm3']=s.Volume()
            cq.exporters.export(sol[0],str(cache/(id+'.step')))
            if p['kind']=='PETG':
                flat=s.translate((-b.xmin,-b.ymin,-b.zmin));cq.exporters.export(flat,str(ROOT/'A1_STL'/(id+'.stl')),tolerance=.07,angularTolerance=.15)
            pts,idx=s.tessellate(.20,.26);meshes[id]=mesh_array([v.toTuple() for v in pts],idx)
            if p['mass'] is None:
                rho={'PETG':1.04,'标准件':2.7,'铝板':2.70,'钢制紧固件':7.85}[p['kind']]
                entry['mass']=s.Volume()*rho/1e6;entry['low']=entry['mass']*(.82 if p['kind']=='PETG' else .90);entry['high']=entry['mass']*(1.22 if p['kind']=='PETG' else 1.1);entry['source']='CAD 体积 × 有效密度 '+str(rho)+' g/cm³'
        elif p['kind']=='设备':
            meshes[id]=stl_mesh(LIB/'simulation'/'meshes'/(id+'_visual.stl'),16000 if id=='Jetson_Orin_Nano' else 11000)
        meta[id]=entry
    write(ROOT/'data'/'layout.json',dict(parts=meta,instances=items))
    (ROOT/'data'/'bodymesh.bin').write_bytes(zlib.compress(json.dumps(meshes,separators=(',',':')).encode(),7))
    print('central base & extra',*[round(sum(meta[t['id']]['mass'] for t in items if t['optional']==op),4) for op in [False,True]],flush=True)
if __name__=='__main__':make_geometry()

