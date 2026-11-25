from vehicle_sw import *
from finalize_native import verify
from pose_view import main as pictures
from xt_native import localise
from collections import Counter
swb.log('R4 pair replacement start')
flag=sw.CommandInProgress
try:
    sw.CommandInProgress=True
    localise()
    for k in ['YourCee20','BuckTray']:
        path=bodypath(k)
        if not path.exists():
            src=ROOT/'source'/'body_step'/(k+'.step')
            raw,e=sw.LoadFile4(str(src),'',sw.GetImportFileData(str(src)),0);assert raw and not e
            m=asif(raw,api.IModelDoc2)
            rgb=[int(parts[k]['color'][i:i+2],16)/255 for i in (1,3,5)]
            m.MaterialPropertyValues=swb.arr(rgb+[.65,.72,.15,.1,0,0])
            m.ForceRebuild3(False);save(m,path);sw.CloseDoc(m.GetTitle())
        m=open_doc(path,1);ss=asif(m,api.IPartDoc).GetBodies2(0,False)
        assert len(ss)==1 and abs(asif(ss[0],api.IBody2).GetMassProperties(1)[3]*1e9-parts[k]['volume_mm3'])<.08
        sw.CloseDoc(m.GetTitle())
    path=OUT/'Q8_Chassis_Equipment.SLDASM';m=open_doc(path,2);activate(m);a=asif(m,api.IAssemblyDoc)
    assert Path(m.GetPathName())==path
    targets={'Daygreen_B30','YourCee20','BuckTray','ZC7112A','Tattu_2200_6S','Wago615'}
    old=[c for c in direct(a) if Path(c.GetPathName()).stem in targets]
    m.ClearSelection2(True)
    for c in old:assert c.Select4(True,None,False)
    if old:assert asif(m.Extension,api.IModelDocExtension).DeleteSelection2(0)
    for t in items:
        if t['id'] in targets:insert(m,a,bodypath(t['id']),1,t['name'],xf(t['pos'],xyzrot(t['rz'])),True)
    m.ForceRebuild3(False);save(m,path);sw.CloseDoc(m.GetTitle())
    verify()
    import xt_manifest
    pictures()
    p=OUT/'Q8_Full_Vehicle.SLDASM';m=open_doc(p,2);a=asif(m,api.IAssemblyDoc);results={}
    for name,_,_ in configs:
        assert m.ShowConfiguration2(name);m.ForceRebuild3(False)
        arr=[asif(c,api.IComponent2) for c in a.GetComponents(False)]
        cs=[c for c in arr if not c.IsSuppressed()]
        counts=Counter(Path(c.GetPathName()).stem for c in cs)
        assert [counts[k] for k in ['YourCee20','BuckTray','Daygreen_B30','ZC7112A']]==[2,1,0,2]
        for k in ['YourCee20','BuckTray','ZC7112A','Tattu_2200_6S','Wago615']:
            actual=sorted(tuple(round(x*1000,2) for x in asif(c.Transform2,api.IMathTransform).ArrayData[9:12]) for c in cs if Path(c.GetPathName()).stem==k)
            assert actual==sorted(tuple(t['pos']) for t in items if t['id']==k),(k,actual)
        results[name]={'resolved':len(cs),'boards':2,'tray':1,'old_converter':0}
    m.ShowConfiguration2('Ride');save(m,p);sw.CloseDoc(m.GetTitle())
    write(ROOT/'data'/'R4原生装配验证.json',results);swb.log('BUILD_COMPLETE')
finally:sw.CommandInProgress=flag
