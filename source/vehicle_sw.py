from native import *
import shutil
layout=read(ROOT/'data'/'layout.json');parts=layout['parts'];items=layout['instances']
def bodypath(id):return OUT/('equipment' if parts[id]['kind']=='设备' else 'body')/(id+'.SLDPRT')
def buildparts():
    check={}
    for id,p in parts.items():
        if 'volume_mm3' not in p:continue
        path=bodypath(id);src=ROOT/'source'/'body_step'/(id+'.step')
        if not path.exists():
            raw,e=sw.LoadFile4(str(src),'',sw.GetImportFileData(str(src)),0)
            if not raw or e:raise RuntimeError((id,e))
            model=asif(raw,api.IModelDoc2)
            rgb=[int(p['color'][i:i+2],16)/255 for i in (1,3,5)]
            model.MaterialPropertyValues=swb.arr(rgb+[.65,.72,.15,.1,0,0]);model.ForceRebuild3(False);save(model,path)
            sw.CloseDoc(model.GetTitle())
        m=open_doc(path,1);bodies=asif(m,api.IPartDoc).GetBodies2(0,False);assert len(bodies)==1,id
        vol=asif(bodies[0],api.IBody2).GetMassProperties(1)[3]*1e9
        err=abs(vol-p['volume_mm3']);assert err<.08,(id,err);check[id]=round(err,5);sw.CloseDoc(m.GetTitle())
    write(ROOT/'data'/'solid_check.json',check);swb.log('Body solids validated '+str(len(check)))
def make_rack(opt):
    f=OUT/('Q8_MID_kit.SLDASM' if opt else 'Q8_Chassis_Equipment.SLDASM')
    if f.exists():return
    m,a=swb.new_ass(f)
    for t in items:
        id=t['id']
        if t['optional']!=opt or parts[id]['kind']=='分布质量':continue
        insert(m,a,bodypath(id),1,t['name'],xf(t['pos'],xyzrot(t['rz'])),True)
    m.ForceRebuild3(False);m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,f);sw.CloseDoc(m.GetTitle());swb.log('Rigid equipment rack '+str(opt))
def direct(a):
    return [asif(raw,api.IComponent2) for raw in a.GetComponents(True)]
def suffix(c):
    p=Path(c.GetPathName()).stem
    if p=='Q8_MID_kit':return 'opt'
    if p=='Q8_Chassis_Equipment':return 'body'
    v=asif(c.Transform2,api.IMathTransform).ArrayData
    return ('F' if v[10]>0 else 'R')+('R' if v[9]>0 else 'L')
configs=[('Crouch','Crouch',False),('Ride','Midstroke',False),('Liftoff','Liftoff',False),('Ride_MID360','Midstroke',True),('Liftoff_MID360','Liftoff',True),('Crouch_MID360','Crouch',True)]
def buildtop():
    p=OUT/'Q8_Full_Vehicle.SLDASM'
    if not p.exists():
        m,a=swb.new_ass(p)
        insert(m,a,OUT/'Q8_Chassis_Equipment.SLDASM',2,'Body',tr(),True)
        for name,side,f in corner_order:
            legfile=OUT/'R1'/'Q8_Single_Corner.SLDASM' if f*side==1 else OUT/'LH'/'Q8_Corner_Mirror.SLDASM'
            insert(m,a,legfile,2,name,xf([side*HX,f*HY,0],leg_basis(side)),True)
        insert(m,a,OUT/'Q8_MID_kit.SLDASM',2,'MID_option',tr(),True)
        m.ForceRebuild3(False);save(m,p)
    else:m=open_doc(p,2);a=asif(m,api.IAssemblyDoc);activate(m)
    for name,subconfig,opt in configs:
        if not m.GetConfigurationByName(name):m.AddConfiguration3(name,'','',0)
        m.ShowConfiguration2(name)
        for c in direct(a):
            kind=suffix(c)
            if kind=='opt':c.SetSuppression2(3 if opt else 0)
            elif kind!='body':c.ReferencedConfiguration=subconfig
        m.EditRebuild3();m.ForceRebuild3(False);save(m,p)
    m.ShowConfiguration2('Ride');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,p);sw.CloseDoc(m.GetTitle())
    m=open_doc(p,2);activate(m);a=asif(m,api.IAssemblyDoc);qa={}
    for name,subconfig,opt in configs:
        m.ShowConfiguration2(name);m.ForceRebuild3(False);comp=direct(a)
        obs={}
        for c in comp:
            k=suffix(c)
            if k=='opt':
                actual=not c.IsSuppressed();assert actual==opt,(name,actual,opt);obs[k]=actual
            elif k!='body':
                assert c.ReferencedConfiguration==subconfig,(name,k,c.ReferencedConfiguration)
                obs[k]=c.ReferencedConfiguration
        deep=[c for raw in a.GetComponents(False) for c in [asif(raw,api.IComponent2)] if not c.IsSuppressed()]
        bad=[c.Name2 for c in deep if not c.GetModelDoc2() or not Path(c.GetPathName()).is_relative_to(OUT)]
        assert not bad,(name,bad[:4])
        qa[name]=dict(legs=obs,resolved_components=len(deep),missing=bad)
        if name in ['Ride','Ride_MID360','Crouch','Liftoff']:
            m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();m.GraphicsRedraw2()
            m.SaveBMP(str(ROOT/'data'/('SW_'+name+'.bmp')),1400,900)
    m.ShowConfiguration2('Ride');m.ViewZoomtofit2();save(m,p);sw.CloseDoc(m.GetTitle())
    write(ROOT/'data'/'solidworks.json',dict(revision=sw.RevisionNumber(),configs=qa))
    swb.log('BUILD_COMPLETE')
if __name__=='__main__':
    flag=sw.CommandInProgress;sw.CommandInProgress=True
    try:
        buildparts();make_rack(False);make_rack(True);buildtop()
    finally:sw.CommandInProgress=flag

