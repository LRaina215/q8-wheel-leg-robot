from common import *
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
for k,sites in [('Jetson_Orin_Nano',[(x,y) for x in [-49.2,49.2] for y in [-42.2,43.7]]),('MC02',[(x,y) for x in [-10.2,25.8] for y in [-18,18]])]:
 s=cq.Shape.importBrep(str(LIB/k/(k+'_layout.brep')))
 found=set()
 for f in s.Faces():
  ad=BRepAdaptor_Surface(f.wrapped,True)
  if ad.GetType()!=GeomAbs_Cylinder:continue
  cylinder=ad.Cylinder();ax=cylinder.Axis();p=ax.Location(); r=cylinder.Radius()
  if abs(ax.Direction().Z())<.999 or not .75<r<3:continue
  pt=(p.X(),p.Y());near=min(math.dist(pt,site) for site in sites)
  if near<6:
   b=f.BoundingBox();found.add(tuple(round(n,3) for n in (*pt,r,b.zmin,b.zmax)))
 print(k,sorted(found),flush=True)

