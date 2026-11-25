from r5_probe import cq,LIB
s=cq.Shape.importBrep(str(LIB/'Jetson_Orin_Nano'/'Jetson_Orin_Nano_layout.brep'))
for x in [-50,-49,49,50]:
 for y in [-35,-32,32,34,36]:
  probe=cq.Solid.makeCylinder(.12,15,cq.Vector(x,y,-.3))
  b=probe.BoundingBox(); intervals=[]
  for sh in s.Solids():
   a=sh.BoundingBox()
   if a.xmin>b.xmax or a.xmax<b.xmin or a.ymin>b.ymax or a.ymax<b.ymin or a.zmin>b.zmax:continue
   for v in sh.intersect(probe).Solids():
    c=v.BoundingBox();intervals.append((round(c.zmin,2),round(c.zmax,2)))
  print(x,y,intervals,flush=True)

