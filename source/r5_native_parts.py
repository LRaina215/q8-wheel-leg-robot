from native import *
from r5_parts import parts,native_name
import time
folder=OUT/'R5_parts';folder.mkdir(exist_ok=True)
def part(k):
 ops=parts[k];path=folder/native_name(k)
 m=asif(sw.NewDocument(swb.part_tpl,0,0,0),api.IModelDoc2)
 sm=asif(m.SketchManager,api.ISketchManager);fm=asif(m.FeatureManager,api.IFeatureManager);ext=asif(m.Extension,api.IModelDocExtension);ps=planes(m)
 rgb=[.36,.55,.57] if k in ['Deck','Chassis'] else ([.28,.6,.47] if k in ['JetClamp','Astra_saddle','XT_saddle','BuckTray','Bridge_tray','MID_fit'] else [.64,.68,.7])
 m.MaterialPropertyValues=swb.arr(rgb+[.6,.7,.25,.2,0,0])
 try:
  for o in ops:
   m.ClearSelection2(True);assert ext.SelectByID2(ps[2 if o['axis']=='x' else 0],'PLANE',0,0,0,False,0,None,0)
   sm.InsertSketch(True);sm.AddToDB=True;cir=[]
   try:
    for kind,*data in o['loops']:
     if kind=='c':
      x,y,r=data; seg=sm.CreateCircleByRadius(x/1000,y/1000,0,r/1000)
      cir.append((asif(seg,api.ISketchSegment),x,y,r))
     else:
      coords=data[0]
      for a,b in zip(coords,coords[1:]+coords[:1]): assert sm.CreateLine(a[0]/1000,a[1]/1000,0,b[0]/1000,b[1]/1000,0)
   finally:sm.AddToDB=False
   sk=asif(ext.GetLastFeatureAdded(),api.IFeature);sk.Name='Sketch_'+o['name']
   if o['axis']=='z':
    for seg,x,y,r in cir:
     m.ClearSelection2(True);assert seg.Select4(False,None)
     dim=m.AddDiameterDimension2((x+r+2)/1000,(y+r+2)/1000,0)
     if dim is None:raise RuntimeError((k,o['name'],'diameter'))
     if (x or y) and k in ['Deck','Chassis','XT_saddle','Bridge_tray','Astra_saddle','MID_fit']:
      pc=asif(asif(seg,api.ISketchArc).GetCenterPoint2(),api.ISketchPoint)
      for horiz,coordinate in [(True,x),(False,y)]:
       if abs(coordinate)<1e-8:continue
       m.ClearSelection2(True)
       first=ext.SelectByID2('Point1@原点','EXTSKETCHPOINT',0,0,0,False,0,None,0)
       if not first:first=ext.SelectByID2('Point1@Origin','EXTSKETCHPOINT',0,0,0,False,0,None,0)
       if first and pc.Select4(True,None):
        fun=m.AddHorizontalDimension2 if horiz else m.AddVerticalDimension2
        fun((x-3)/1000,(y-3)/1000,0)
   m.ClearSelection2(True);sm.InsertSketch(True);m.ClearSelection2(True);sk.Select2(False,0)
   z=o['z']/1000;h=o['h']/1000;draft=bool(o['draft']);rad=math.radians(o['draft'])
   args=[True,False,o['cut'],0,0,h,0,draft,False,True,False,rad,0,False,False,False,False]
   if o['cut']:f=fm.FeatureCut3(*args,False,False,True,False,False,False,3,abs(z),z<0)
   else:f=fm.FeatureExtrusion3(*args,True,False,True,3,abs(z),z<0)
   if not f:raise RuntimeError((k,o['name'],'feature failed'))
   f=asif(f,api.IFeature);f.Name=o['name']
   if f.GetErrorCode2(False)[0]:raise RuntimeError((k,o['name'],f.GetErrorCode2(False)))
  m.ForceRebuild3(False);b=asif(m,api.IPartDoc).GetBodies2(0,False)
  assert len(b)==1,(k,len(b))
  v=asif(b[0],api.IBody2).GetMassProperties(1)[3]*1e9
  m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,path)
  step=ROOT/'source'/'body_step'/('R5_'+k+'.step')
  save(m,step)
  print(k,round(v,3),flush=True)
  return v
 finally:sw.CloseDoc(m.GetTitle())
if __name__=='__main__':
 old=sw.CommandInProgress;pref=sw.GetUserPreferenceToggle(10)
 try:
  sw.CommandInProgress=True;sw.SetUserPreferenceToggle(10,False)
  for key in sys.argv[1:] or parts:
   if not (folder/native_name(key)).exists():part(key)
 finally:sw.CommandInProgress=old;sw.SetUserPreferenceToggle(10,pref)

