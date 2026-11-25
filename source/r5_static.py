"""Independent OCCT check of the geometry actually exported from SOLIDWORKS."""
from r5_instances import *
from clearance import rigid,bounds,meet
import cadquery as cq
from itertools import combinations
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from functools import lru_cache
@lru_cache(None)
def proto(k):
 f=ROOT/'source'/'body_step'/('R5_'+k+'.step' if k in ids else k+'.step')
 if k in ids or f.exists():return cq.importers.importStep(str(f)).val()
 return cq.Shape.importBrep(str(LIB/k/(k+'_layout.brep')))
def check():
 models=[];slot=[]
 for t in records:
  s=rigid(proto(t['id']),matrix(t),t['pos']);v=bounds(s);models.append((t,s,v))
 def intersect(a,b):
  if len(a.Solids())==1 and len(b.Solids())==1:return abs(a.intersect(b).Volume())
  aa=[(s,bounds(s)) for s in a.Solids()];bb=[(s,bounds(s)) for s in b.Solids()]
  return sum(abs(s.intersect(t).Volume()) for s,p in aa for t,q in bb if meet(p,q,.003))
 hits=[]
 for (t,a,bb),(u,b,cc) in combinations(models,2):
  if not meet(bb,cc,.005):continue
  vol=intersect(a,b)
  if vol>.12:
   hits.append([t['name'],u['name'],round(vol,3)]);print('hit',hits[-1],flush=True)
 checks=[]
 for t,s,bb in models:
  k=t['id']
  if k not in ['Xsp','Lsp100','Msp','JetClamp','Bridge_tray','BuckTray','Astra_saddle','Deck']:continue
  for x,y in (deckpts if k=='Deck' else [(-50,-17),(46.5,-17),(11,65)] if k=='BuckTray' else [(-18,34),(18,34)] if k=='Bridge_tray' else [(0,-15.5),(0,15.5)] if k=='Astra_saddle' else [(0,0)]):
   wp=matrix(t)@np.array([x,y,0])+np.array(t['pos']);x,y=wp[:2]
   target='Chassis' if k in ['Deck','BuckTray'] else 'Deck';q=proto(target)
   zz=(-47.0 if k=='BuckTray' else 28.5 if k=='Deck' else 34)
   radius=2.25 if k in ['Lsp100','Deck'] else 1.15 if k=='Msp' else 1.7
   # Full load-bearing ring and a separate through-hole probe at working section.
   pin=cq.Solid.makeCylinder(radius-.03,.4,cq.Vector(x,y,zz))
   outer=radius+1.25
   ring=cq.Solid.makeCylinder(outer,.4,cq.Vector(x,y,zz)).cut(cq.Solid.makeCylinder(radius+.03,.4,cq.Vector(x,y,zz)))
   support=q.intersect(ring).Volume()/ring.Volume()
   obstruction=q.intersect(pin).Volume()
   checks.append([t['name'],target,round(x,3),round(y,3),round(support,4),round(obstruction,5)])
   if support<.999 or obstruction>.001:print('hole',checks[-1],flush=True)
 def axis_faces(k):
  out=[]
  for f in proto(k).Faces():
   a=BRepAdaptor_Surface(f.wrapped,True)
   if a.GetType()!=GeomAbs_Cylinder:continue
   c=a.Cylinder();ax=c.Axis();v=ax.Direction();p=ax.Location()
   if abs(v.X())>.999 and abs(c.Radius()-2.65)<.005:out.append((round(p.Y(),3),round(p.Z(),3)))
  return out
 cross=axis_faces('Chassis');print('hip holes',cross,flush=True)
 write(ROOT/'data'/'R5_static.json',dict(hits=hits,support_rings=checks,hip_holes=cross,threshold_mm3=.12))
if __name__=='__main__':check()

