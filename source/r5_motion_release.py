from r5_axis_drag import solve_rig
from r5_vehicle import *
def drag_segment(m,a,C,n,q1,q2):
 _,s,f=next(z for z in corner_order if z[0]==n);c=C[n,'drive']
 axis=swb.mu.CreateVector(swb.arr([1,0,0]));origin=swb.mu.CreatePoint(swb.arr([s*HX/1000,f*HY/1000,0]))
 steps=max(2,math.ceil(abs(q2-q1)/4));increment=-f*math.radians(q2-q1)/steps
 xf=swb.mu.CreateTransformRotateAxis(origin,axis,increment)
 op=asif(a.GetDragOperator(),api.IDragOperator);op.TransformType=1;op.DragMode=2;op.UseAbsoluteTransform=False;op.ApplyToThisConfiguration=True;op.GraphicsRedrawEnabled=False
 assert op.AddComponent(c,False) and op.BeginDrag()
 try:
  for _ in range(steps):assert op.DragAsUI(xf)
 finally:assert op.EndDrag()
 m.ForceRebuild3(True)
def pin_offsets(C):
 def map_point(c,p):
  v=coords(c);return np.array(p)@np.array(v[:9]).reshape(3,3)+1000*np.array(v[9:12])
 out={}
 for n,side,fore in corner_order:
  p=map_point(C[n,'passive'],[side*fore*110,0,0])
  q=map_point(C[n,'carrier'],[0,-62,0])
  out[n]=round(float(np.linalg.norm(p-q)),6)
 return out
def release():
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc)
 m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);result={};rows=[]
 for k,qs in poses.items():
  m.ShowConfiguration2(k);m.ForceRebuild3(True);C=parts(a);dev=measure(C,qs);mf=mate_errors(m)
  states={(n,g):c.GetConstrainedStatus() for (n,g),c in C.items()};invalid={str(i):v for i,v in states.items() if v not in (2,3)}
  assert max(dev.values())<.035 and len(mf)==48 and not any(v for _,v in mf) and not invalid,(k,dev,invalid)
  assert C['body','body'].ReferencedConfiguration==('MID' if k.endswith('MID') else 'Base')
  pins=pin_offsets(C);assert max(pins.values())<.035,(k,pins)
  result[k]=dict(pin_D_axis_offset_mm=pins,angles=qs,error_mm=max(dev.values()),mates=len(mf),active_mates=44 if k.startswith('Motion') else 48,rack=C['body','body'].ReferencedConfiguration,underconstrained=[n+'_'+g for (n,g),v in states.items() if v==2])
  print('reopened',k,flush=True)
  write(ROOT/'data/R5_pose_validation.json',result)
 m.ShowConfiguration2('Motion');m.ForceRebuild3(True);C=parts(a);qs=poses['Motion'].copy()
 for n in names:
  for target in [-36,22,-7]:
   old=qs[n];drag_segment(m,a,C,n,old,target);qs[n]=target
   front=1 if n.startswith('F') else -1
   for correction in range(2):
    v=coords(C[n,'carrier']);qread=math.degrees(math.atan2(-v[11]*1000,front*(v[10]*1000-front*HY)))
    if abs(qread-target)<.008:break
    print('residual',n,target,qread,flush=True);drag_segment(m,a,C,n,qread,target)
   actual=measure(C,qs);err=max(actual.values());state=C[n,'drive'].GetConstrainedStatus()
   print('drag completed',n,target,err,state,flush=True)
   assert err<.06 and state==2 and max(pin_offsets(C).values())<.035,(n,target,actual,state)
   rows.append([n,target,True,err]);write(ROOT/'data/R5_drag_validation.json',rows)
 m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2()
 write(ROOT/'data/R5_motion.json',dict(reopened=result,drag=rows,mode='IDragOperator.DragAsUI, incremental rotation about the vehicle hip axis, independently measured after EndDrag and top-level rebuild.'))
 sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 old=sw.CommandInProgress
 try:sw.CommandInProgress=True;release()
 finally:sw.CommandInProgress=old

