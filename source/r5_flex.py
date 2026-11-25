from vehicle_sw import *
review=OUT/'Q8_R5_运动审阅.SLDASM'
def flex():
 m=open_doc(review if review.is_file() else OUT/'Q8_Full_Vehicle.SLDASM',2);activate(m)
 if Path(m.GetPathName())!=review:save(m,review)
 a=asif(m,api.IAssemblyDoc)
 print([(c.Name2,suffix(c),c.GetPathName()) for c in direct(a)],flush=True)
 for name,opt in [('Motion',False),('Motion_MID',True)]:
  if not m.GetConfigurationByName(name):
   m.ShowConfiguration2('Ride_MID360' if opt else 'Ride');m.AddConfiguration3(name,'Independent leg motion','',0)
  m.ShowConfiguration2(name)
  for c in direct(a):
   k=suffix(c)
   if k=='opt':c.SetSuppression2(3 if opt else 0);continue
   if k=='body':continue
   m.ClearSelection2(True);assert c.Select4(False,None,False)
   ok=a.CompConfigProperties5(3,1,True,True,'Midstroke',False,False)
   print(k,ok,c.Solving,flush=True)
   assert ok and c.Solving==1
  m.ClearSelection2(True);m.ForceRebuild3(False);save(m,review)
 m.ShowConfiguration2('Motion');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,review);sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 prev=sw.CommandInProgress
 try:sw.CommandInProgress=True;flex()
 finally:sw.CommandInProgress=prev

