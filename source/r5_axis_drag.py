from r5_vehicle import *
def solve_rig(m,a,qs):
 C=parts(a)
 for (n,g),c in C.items():
  if g not in ('body','base'):c.Transform2=placement(n,g,qs[n])
 m.EditRebuild3();m.ForceRebuild3(True);return C
def drag(m,a,C,n,steps):
 _,side,front=next(v for v in corner_order if v[0]==n)
 c=C[n,'drive'];carrier=C[n,'carrier']
 def angle():
  v=coords(carrier);return math.degrees(math.atan2(-v[11]*1000,front*(v[10]*1000-front*HY)))
 x=swb.mu.CreatePoint(swb.arr([side*HX/1000,front*HY/1000,0]));v=swb.mu.CreateVector(swb.arr([1,0,0]))
 op=asif(a.GetDragOperator(),api.IDragOperator);op.TransformType=1;op.DragMode=2;op.UseAbsoluteTransform=False;op.ApplyToThisConfiguration=True;op.GraphicsRedrawEnabled=False
 assert op.AddComponent(c,False);assert op.BeginDrag()
 rows=[]
 try:
  for q in steps:
   before=angle();theta=-front*math.radians(q-before)
   rot=swb.mu.CreateTransformRotateAxis(x,v,theta)
   ok=op.DragAsUI(rot);actual=angle();rows.append((q,before,actual,ok,c.GetConstrainedStatus()))
   print('axis',n,rows[-1],flush=True)
 finally:op.EndDrag()
 return rows
if __name__=='__main__':
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);m.ShowConfiguration2('Motion');C=solve_rig(m,a,{n:-7 for n in names})
 print('aligned',[(g,c.GetConstrainedStatus()) for (n,g),c in C.items() if n=='FL'],flush=True)
 drag(m,a,C,'FL',[-8,-10,-16,-7,7,22])

