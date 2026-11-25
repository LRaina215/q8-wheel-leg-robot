from vehicle_sw import *
import tempfile
from collections import Counter
stash=Path(tempfile.gettempdir())/'q8_r1_vehicle_previous'
stash.mkdir(exist_ok=True)
def close_owned():
    paths=list(OUT.rglob('*.SLDASM'))+list(OUT.rglob('*.SLDPRT'))
    for path in sorted(paths,key=lambda p:(p.suffix!='.SLDASM',len(p.parts))):
        r=sw.GetOpenDocumentByName(str(path))
        if r:sw.CloseDoc(asif(r,api.IModelDoc2).GetTitle())
def retire(path):
    if path.exists():shutil.move(str(path),str(stash/path.name))
def replace_hub():
    dest=OUT/'R1'/'parts'/'H04.SLDPRT'
    vol=read(ROOT/'data'/'selected_hub.json')['volume_mm3']
    def volume(m):return asif(asif(m,api.IPartDoc).GetBodies2(0,False)[0],api.IBody2).GetMassProperties(1)[3]*1e9
    m=open_doc(dest,1);v=volume(m);sw.CloseDoc(m.GetTitle())
    if abs(v-vol)>.08:
        retire(dest)
        src=ROOT/'source'/'body_step'/'W08_installed.step'
        raw,e=sw.LoadFile4(str(src),'',sw.GetImportFileData(str(src)),0);assert raw and not e
        m=asif(raw,api.IModelDoc2);m.MaterialPropertyValues=swb.arr([.63,.68,.70,.65,.72,.15,.1,0,0])
        save(m,dest);sw.CloseDoc(m.GetTitle())
    m=open_doc(dest,1);assert abs(volume(m)-vol)<.08;sw.CloseDoc(m.GetTitle())
def fasteners():
    f=OUT/'body'/'Hip_hardware.SLDASM'
    if not f.exists():
        m,a=swb.new_ass(f)
        for t in items:
            if t['id'].startswith('B5'):
                insert(m,a,bodypath(t['id']),1,t['name'],xf(t['pos'],xyzrot(t['rz'])),True)
        m.ForceRebuild3(False);save(m,f);sw.CloseDoc(m.GetTitle())
    p=OUT/'Q8_Chassis_Equipment.SLDASM';m=open_doc(p,2);a=asif(m,api.IAssemblyDoc)
    if not any(Path(c.GetPathName())==f for c in direct(a)):
        insert(m,a,f,2,'Hip_mounting_hardware',tr(),True);m.ForceRebuild3(False);save(m,p)
    sw.CloseDoc(m.GetTitle())
def new_mid():
    f=OUT/'Q8_MID_kit.SLDASM'
    if f.exists():
        m=open_doc(f,2);a=asif(m,api.IAssemblyDoc)
        ok=any(Path(c.GetPathName()).stem=='MID_fit' for c in direct(a));sw.CloseDoc(m.GetTitle())
        if not ok:retire(f)
    make_rack(True)
    for ident in ['MID_plate','Lsp']:
        for path in [OUT/'body'/(ident+'.SLDPRT'),ROOT/'source'/'body_step'/(ident+'.step')]:retire(path)
def verify():
    path=OUT/'Q8_Full_Vehicle.SLDASM';m=open_doc(path,2);activate(m);a=asif(m,api.IAssemblyDoc);qa={}
    for name,subconfig,opt in configs:
        assert m.ShowConfiguration2(name);m.ForceRebuild3(False);cs=direct(a);obs={}
        for c in cs:
            key=suffix(c)
            if key=='opt':
                obs[key]=not c.IsSuppressed();assert obs[key]==opt
            elif key!='body':
                obs[key]=c.ReferencedConfiguration;assert obs[key]==subconfig
        deep=[c for raw in a.GetComponents(False) for c in [asif(raw,api.IComponent2)] if not c.IsSuppressed()]
        bad=[c.Name2 for c in deep if not c.GetModelDoc2() or not Path(c.GetPathName()).is_relative_to(OUT)];assert not bad,bad
        count=Counter(Path(c.GetPathName()).stem for c in deep)
        for k,num in [('H04',0),('P06',0),('H13',0),('XT100_Tyre',4),('XT100_Rim',4),('XT8_Coupler',4),('XT8_Screw',4),('H05',12),('B5bolt',16),('B5washer',32),('B5nut',16),('MID_fit',int(opt)),('Lsp100',4*int(opt)),('MID_plate',0)]:
            assert count[k]==num,(name,k,count[k],num)
        qa[name]=dict(legs=obs,resolved_components=len(deep),missing=bad,mount_counts={k:count[k] for k in ['XT100_Tyre','XT100_Rim','XT8_Coupler','H05','B5bolt','B5washer','B5nut','MID_fit','Lsp100']})
        if name in ['Ride','Ride_MID360','Crouch','Liftoff']:
            m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();m.GraphicsRedraw2()
            m.SaveBMP(str(ROOT/'data'/('SW_'+name+'.bmp')),1400,900)
        print(name,len(deep),flush=True)
    m.ShowConfiguration2('Ride');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,path);sw.CloseDoc(m.GetTitle())
    write(ROOT/'data'/'solidworks.json',dict(revision=sw.RevisionNumber(),configs=qa))
    swb.log('BUILD_COMPLETE')
if __name__=='__main__':
    prev=sw.CommandInProgress;sw.CommandInProgress=True
    try:
        close_owned();replace_hub();print('hub done',flush=True);buildparts();fasteners();new_mid();verify()
    finally:sw.CommandInProgress=prev
