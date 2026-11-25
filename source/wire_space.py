"""Voxelized assembly for routing, using the displayed part meshes in vehicle coordinates."""
from common import *
import base64,zlib,tempfile
from vtkmodules.vtkCommonDataModel import vtkPolyData,vtkCellArray
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkImagingStencil import vtkPolyDataToImageStencil,vtkImageStencilToImage
from vtkmodules.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
from scipy.ndimage import distance_transform_edt,map_coordinates
origin=np.array([-174.,-285.,-231.]);step=3.;dims=(117,191,153)
data=ROOT/'data'
cache=Path(tempfile.gettempdir())/'q8_r4_space1.npz'
def meshes(filename):
    packed=json.loads(zlib.decompress((data/filename).read_bytes()))
    return {k:(np.frombuffer(base64.b64decode(a),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(b),'<u4').reshape(-1,3)) for k,(a,b) in packed.items()}
def voxel(mask,pts,idx):
    lo=np.maximum(0,np.floor((pts.min(0)-origin)/step).astype(int)-1);hi=np.minimum(np.array(dims)-1,np.ceil((pts.max(0)-origin)/step).astype(int)+1)
    if np.any(hi<lo):return
    points=vtkPoints();points.SetData(numpy_to_vtk(np.ascontiguousarray(pts,dtype=float),deep=True))
    cell=vtkCellArray();cell.SetData(numpy_to_vtkIdTypeArray(np.arange(0,idx.size+1,3,dtype='int64'),deep=True),numpy_to_vtkIdTypeArray(np.ascontiguousarray(idx.flatten(),dtype='int64'),deep=True))
    poly=vtkPolyData();poly.SetPoints(points);poly.SetPolys(cell)
    raster=vtkPolyDataToImageStencil();raster.SetInputData(poly);raster.SetOutputOrigin(*origin);raster.SetOutputSpacing(step,step,step)
    raster.SetOutputWholeExtent(*np.column_stack([lo,hi]).ravel().tolist());im=vtkImageStencilToImage();im.SetInputConnection(raster.GetOutputPort());im.SetInsideValue(1);im.SetOutsideValue(0);im.SetOutputScalarTypeToUnsignedChar();im.Update()
    a=vtk_to_numpy(im.GetOutput().GetPointData().GetScalars()).reshape(tuple(hi-lo+1),order='F')
    mask[tuple(slice(i,j+1) for i,j in zip(lo,hi))] |= a.astype(bool)
def leg_clouds():
    ms=meshes('legmesh.bin');groups={}
    for t in leg.INST:
        p,ind=ms[t['id']];rot=xyzrot(t['rot'])@np.diag([1,-1 if t['flip'] else 1,-1 if t['flip'] else 1])
        groups.setdefault(t['g'],[]).append((p@rot.T+np.array([t['x'],t['y'],t['z']]),ind))
    return groups
def build():
    b=meshes('bodymesh.bin');d=read(data/'layout.json');mask=np.zeros(dims,bool)
    for t in d['instances']:
        if t['id'] not in b:continue
        p,i=b[t['id']];world=p@xyzrot(t['rz']).T+t['pos'];voxel(mask,world,i)
        if t['id'] in ['Jetson_Orin_Nano','MC02','Tattu_2200_6S']:
            # Keep the full equipment envelope out of through-routes, including
            # internal air spaces open in the vendor's tessellation.
            lo=np.floor((world.min(0)-origin)/step).astype(int);hi=np.ceil((world.max(0)-origin)/step).astype(int)
            mask[tuple(slice(i,j+1) for i,j in zip(lo,hi))]=True
    static=distance_transform_edt(~mask,sampling=step).astype('f')
    groups=leg_clouds()
    for n,side,f in corner_order:
        M=leg_basis(side)@np.diag([side*f,1,1]);off=[side*HX,f*HY,0]
        for grp,parts in groups.items():
            pp=np.concatenate([p for p,ii in parts]);ii=np.concatenate([a+sum(len(p) for p,_ in parts[:i]) for i,(_,a) in enumerate(parts)])
            for q in ([-7] if grp=='base' else range(-36,35,5)):
                x,y,a=leg.group_pose(grp,q);P=(pp@xyzrot(a).T+[x,y,0])@M.T+off
                voxel(mask,P,ii)
    swept=distance_transform_edt(~mask,sampling=step).astype('f');np.savez_compressed(cache,static=static,swept=swept)
def fields():
    if not cache.exists():build()
    d=np.load(cache);return d['static'],d['swept']
def distances(field,points):
    return map_coordinates(field,((np.array(points)-origin)/step).T,order=1,mode='nearest')
if __name__=='__main__':build()
