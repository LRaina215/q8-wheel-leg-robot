from r5_vehicle import *
m=open_doc(topfile,2);activate(m);m.ShowConfiguration2('Motion');a=asif(m,api.IAssemblyDoc)
def readq():
 c=parts(a)['FL','carrier'];v=coords(c);return round(math.degrees(math.asin(-v[11]*1000/110)),4)
print('initial',readq(),flush=True)
for q in [-32,-26,-7,5,22,-7]:
 c=parts(a)['FL','drive'];ok=c.SetTransformAndSolve2(placement('FL','drive',q))
 print('requested',q,'return',ok,'actual',readq(),flush=True)
 m.EditRebuild3();print('rebuilt',readq(),flush=True)

