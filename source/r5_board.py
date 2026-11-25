from common import *
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
for k in ['Jetson_Orin_Nano','MC02']:
 s=cq.Shape.importBrep(str(LIB/k/(k+'_layout.brep')));hits=[]
 for f in s.Faces():
  ad=BRepAdaptor_Surface(f.wrapped,True)
  if ad.GetType()!=GeomAbs_Cylinder:continue
  c=ad.Cylinder(); ax=c.Axis();pt=ax.Location(); r=c.Radius();b=f.BoundingBox()
  if abs(ax.Direction().Z())<.999 or not .84<=r<3.1 or b.zmin>2 or b.zmax-b.zmin<.65:continue
  hits.append(tuple(round(x,2) for x in (pt.X(),pt.Y(),r,b.zmin,b.zmax,ad.LastUParameter()-ad.FirstUParameter())))
 print(k,sorted(set(hits)),flush=True)

