from r5_vehicle import *
def run():
 m=open_doc(topfile,2);activate(m);m.ShowConfiguration2('Motion');a=asif(m,api.IAssemblyDoc);C=parts(a)
 def ang(n):
  v=coords(C[n,'carrier']);return round(math.degrees(math.asin(-v[11]*1000/110)),5)
 print('start',ang('FL'),flush=True)
 for q in [-15,6,-7]:
  c=C['FL','carrier'];xf_target=placement('FL','carrier',q)
  ok=c.SetTransformAndSolve2(xf_target);print('carrier solver',q,ok,ang('FL'),flush=True)
 op=asif(a.GetDragOperator(),api.IDragOperator);op.ApplyToThisConfiguration=True
 print('defaults',op.DragMode,op.TransformType,op.UseAbsoluteTransform,flush=True)
 op.CollisionDetectionEnabled=False;op.GraphicsRedrawEnabled=False;op.UseAbsoluteTransform=False
 c=C['FL','carrier'];print('select',op.AddComponent(c,False),'begin',op.BeginDrag(),flush=True)
 try:
  for q in [-36,-15,22,-7]:
   v=coords(c);target=asif(placement('FL','carrier',q),api.IMathTransform).ArrayData;delta=(np.array(target[9:12])-v[9:12])*1000
   ok=op.Drag(xf(delta,np.eye(3)));print('drag',q,delta.tolist(),ok,ang('FL'),flush=True)
 finally:print('end',op.EndDrag(),flush=True)
 print('final',ang('FL'),flush=True)
if __name__=='__main__':run()

