from common import *
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
import cadquery as cq
s=cq.Shape.importBrep(str(LIB/'MID360'/'MID360_layout.brep'))
a=set()
for f in s.Faces():
 ad=BRepAdaptor_Surface(f.wrapped,True)
 if ad.GetType()!=GeomAbs_Cylinder:continue
 c=ad.Cylinder();p=c.Axis().Location();b=f.BoundingBox()
 if abs(c.Axis().Direction().Z())>.999 and c.Radius()<4 and b.zmin<1 and b.zmax-b.zmin>.8:a.add(tuple(round(q,2) for q in (p.X(),p.Y(),c.Radius(),b.zmin,b.zmax,ad.LastUParameter()-ad.FirstUParameter())))
print(sorted(a))

