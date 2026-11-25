"""Generate editable sketch/extrude parts, rigid groups and a revolute SolidWorks assembly."""
import os,sys,math,time,traceback,json
from pathlib import Path
import pythoncom,win32com.client
from design import *
binding=Path(os.environ.get('SW_PY_BINDINGS',r'F:\YunTuo_CAD_Work_20261029\sw_bindings'))
if not (binding/'sw_api.py').exists():
    import gzip,tempfile
    binding=Path(tempfile.gettempdir())/'q8_sw2024_bindings'
    binding.mkdir(exist_ok=True)
    (binding/'sw_api.py').write_bytes(gzip.decompress((Path(__file__).parent/'sw_api.py.gz').read_bytes()))
sys.path.insert(0,str(binding))
import sw_api as api
from datetime import datetime
pythoncom.CoInitialize()
sw=api.ISldWorks(win32com.client.dynamic.Dispatch('SldWorks.Application')._oleobj_)
def asif(raw,typ):return typ(raw._oleobj_.QueryInterface(typ.CLSID,pythoncom.IID_IDispatch))
def arr(data):return win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,data)
def log(s):
    with (ROOT/'build_log.txt').open('a',encoding='utf8') as f:f.write(str(datetime.now())+' '+str(s)+'\n')
    print(s,flush=True)
base=ROOT/'SolidWorks'; pd=base/'parts'; sub=base/'groups'; sub.mkdir(exist_ok=True)
part_tpl=sw.GetUserPreferenceStringValue(8); ass_tpl=sw.GetUserPreferenceStringValue(9)
mu=asif(sw.GetMathUtility(),api.IMathUtility)
def tr(x=0,y=0,z=0,a=0,flip=False):
    u=math.radians(a);c,s=math.cos(u),math.sin(u);f=-1 if flip else 1
    return mu.CreateTransform(arr([c,s,0,-s*f,c*f,0,0,0,f,x/1000,y/1000,z/1000,1,0,0,0]))
def planes(m):
    f=m.FirstFeature();out=[]
    while f and len(out)<3:
        f=asif(f,api.IFeature)
        if f.GetTypeName2()=='RefPlane':out.append(f.Name)
        f=f.GetNextFeature()
    return out
def save(m,path):
    code=m.SaveAs3(str(path),0,1)
    if code or not path.is_file():raise RuntimeError(f'Save {path.name} {code}')
def open_doc(path,typ):
    raw=sw.GetOpenDocumentByName(str(path))
    if raw is None:
        raw,e,w=sw.OpenDoc6(str(path),typ,1,'',0,0)
        if raw is None or e:raise RuntimeError(f'Open {path} {e} {w}')
    return asif(raw,api.IModelDoc2)
def activate(m):sw.ActivateDoc3(m.GetTitle(),False,0,0)
def make_part(id):
    p=PARTS[id];m=asif(sw.NewDocument(part_tpl,0,0,0),api.IModelDoc2);sm=asif(m.SketchManager,api.ISketchManager);fm=asif(m.FeatureManager,api.IFeatureManager);ext=asif(m.Extension,api.IModelDocExtension);pl=planes(m)[0]
    color=[int(p['color'][i:i+2],16)/255 for i in (1,3,5)];m.MaterialPropertyValues=arr(color+[.55,.65,.2,.25,0,0])
    try:
        for i,opn in enumerate(p['ops']):
            m.ClearSelection2(True);assert ext.SelectByID2(pl,'PLANE',0,0,0,False,0,None,0)
            sm.InsertSketch(True);sm.AddToDB=True
            try:
                for loop in opn['loops']:
                    if loop[0]=='c':
                        _,x,y,r=loop;sm.CreateCircleByRadius(x/1000,y/1000,0,r/1000)
                    else:
                        ps=loop[1]
                        for a,b in zip(ps,ps[1:]+ps[:1]):sm.CreateLine(a[0]/1000,a[1]/1000,0,b[0]/1000,b[1]/1000,0)
            finally:sm.AddToDB=False
            sketch=asif(ext.GetLastFeatureAdded(),api.IFeature);sketch.Name='Profile_'+str(i+1)
            sm.InsertSketch(True);m.ClearSelection2(True);sketch.Select2(False,0)
            z=opn['z']/1000;h=opn['h']/1000
            if opn['cut']:
                f=fm.FeatureCut3(True,False,True,0,0,h,0,False,False,False,False,0,0,False,False,False,False,False,False,True,False,False,False,3,abs(z),z<0)
            else:
                f=fm.FeatureExtrusion3(True,False,False,0,0,h,0,False,False,False,False,0,0,False,False,False,False,True,False,True,3,abs(z),z<0)
            if f is None:raise RuntimeError(f"{id} feature {opn['label']}")
            feat=asif(f,api.IFeature);feat.Name=opn['label'];error=feat.GetErrorCode2(False)
            if error[0]:raise RuntimeError(f'{id} {opn["label"]} {error}')
        m.ForceRebuild3(False);bodies=asif(m,api.IPartDoc).GetBodies2(0,False)
        if len(bodies)!=1:raise RuntimeError(f'{id} bodies {len(bodies)}')
        m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,pd/(id+'.SLDPRT'))
        vol=asif(bodies[0],api.IBody2).GetMassProperties(1)[3]*1e9
        return vol
    finally:sw.CloseDoc(m.GetTitle())
def new_ass(path):
    m=asif(sw.NewDocument(ass_tpl,0,0,0),api.IModelDoc2);save(m,path);return m,asif(m,api.IAssemblyDoc)
def insert(m,a,path,typ,name,transform,fixed):
    open_doc(path,typ);activate(m)
    c=asif(a.AddComponent5(str(path),0,'',False,'',0,0,0),api.IComponent2)
    m.ClearSelection2(True);c.Select4(False,None,False);a.UnfixComponent();m.ClearSelection2(True);c.Transform2=transform;c.Name2=name
    if fixed:
        c.Select4(False,None,False);a.FixComponent();m.ClearSelection2(True)
    return c
def make_group(g):
    path=sub/(g+'.SLDASM');m,a=new_ass(path)
    for i,t in enumerate(v for v in INST if v['g']==g):
        insert(m,a,pd/(t['id']+'.SLDPRT'),1,t['id']+'_'+str(i+1),tr(t['x'],t['y'],t['z'],t['rot'],t['flip']),True)
    m.ForceRebuild3(False);m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,path);sw.CloseDoc(m.GetTitle());log('group '+g)
def child_cylinder(child,x,y,r):
    part=asif(child.GetModelDoc2(),api.IPartDoc)
    for body in part.GetBodies2(0,False):
        for raw in asif(body,api.IBody2).GetFaces():
            face=asif(raw,api.IFace2);sf=asif(face.GetSurface(),api.ISurface)
            if sf.IsCylinder():
                p=sf.CylinderParams
                if abs(p[5])>.999 and max(abs(p[0]*1000-x),abs(p[1]*1000-y),abs(p[6]*1000-r))<.015:
                    return asif(child.GetCorrespondingEntity(face),api.IEntity)
    raise RuntimeError(f'cyl {child.Name2} {x} {y} {r}')
axes={'base':[('A','P01',0,0,20),('B','P01',0,-AB,3.25)],'drive':[('A','P02',0,0,5),('C','P02',L,0,5.05)],
      'passive':[('B','P03',0,0,5.05),('D','P03',L,0,5.05)],'carrier':[('C','P04',0,0,3.25),('D','P04',0,-AB,3.25),('W','P05',0,0,11.05)],'wheel':[('W','H02',0,0,4)]}
def make_axes(g):
    path=sub/(g+'.SLDASM');m=open_doc(path,2);activate(m);a=asif(m,api.IAssemblyDoc);ext=asif(m.Extension,api.IModelDocExtension)
    for key,id,x,y,r in axes[g]:
        if a.FeatureByName('Axis_'+key):continue
        child=next(asif(c,api.IComponent2) for c in a.GetComponents(True) if Path(asif(c,api.IComponent2).GetPathName()).stem==id)
        face=child_cylinder(child,x,y,r);m.ClearSelection2(True);assert face.Select4(False,None)
        if not m.InsertAxis2(True):raise RuntimeError('axis '+g+' '+key)
        ft=asif(ext.GetLastFeatureAdded(),api.IFeature);ft.Name='Axis_'+key;m.ClearSelection2(True)
    save(m,path);sw.CloseDoc(m.GetTitle());log('axis datums '+g)
def add_mate(m,a,name,one,two,kind):
    m.ClearSelection2(True)
    ok=one.Select2(False,1) and two.Select2(True,1)
    if not ok:raise RuntimeError('select '+name)
    mgr=asif(m.SelectionManager,api.ISelectionMgr)
    log('selection '+name+' '+str([(mgr.GetSelectedObjectType3(i,-1),mgr.GetSelectedObjectMark(i)) for i in range(1,mgr.GetSelectedObjectCount2(-1)+1)]))
    res,err=a.AddMate5(kind,2,False,0,0,0,1,1,0,0,0,False,False,0,0)
    if res is None or err!=1:raise RuntimeError(f'mate {name} {err}')
    latest=asif(m.Extension,api.IModelDocExtension).GetLastFeatureAdded()
    if latest:
        f=asif(latest,api.IFeature)
        if f.GetTypeName2().startswith('Mate') and f.GetTypeName2()!='MateGroup':f.Name=name
    m.ClearSelection2(True);m.ForceRebuild3(False);log('mate '+name)
def top():
    path=base/'Q8_Single_Corner.SLDASM';m,a=new_ass(path);C={}
    for g in ['base','drive','passive','carrier','wheel']:
        x,y,ang=group_pose(g,0);C[g]=insert(m,a,sub/(g+'.SLDASM'),2,g,tr(x,y,0,ang),g=='base')
    def ax(name,g1,id1,x1,y1,r1,g2,id2,x2,y2,r2):
        key='W' if name=='Wheel_axis' else name[-1]
        add_mate(m,a,name,asif(C[g1].FeatureByName('Axis_'+key),api.IFeature),asif(C[g2].FeatureByName('Axis_'+key),api.IFeature),0)
    def plane(g):
        cp=C[g];doc=asif(cp.GetModelDoc2(),api.IModelDoc2);return asif(cp.FeatureByName(planes(doc)[0]),api.IFeature)
    def axial(g):add_mate(m,a,'Axial_'+g,plane('base'),plane(g),0)
    ax('Hip_A','base','P01',0,0,20,'drive','P02',0,0,5);axial('drive')
    ax('Pivot_B','base','P01',0,-AB,3.25,'passive','P03',0,0,5.05);axial('passive')
    ax('Pivot_C','drive','P02',L,0,5.05,'carrier','P04',0,0,3.25);axial('carrier')
    ax('Close_D','passive','P03',L,0,5.05,'carrier','P04',0,-AB,3.25)
    ax('Wheel_axis','carrier','P05',0,0,11.05,'wheel','H02',0,0,4);axial('wheel')
    m.ForceRebuild3(False);m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,path)
    solve_poses(m,a,C,path)
def solve_poses(m,a,C,path):
    activate(m);m.ClearSelection2(True)
    configs=[('Crouch',Q0),('Midstroke',-7.),('Liftoff',Q1)]
    def components(assembly):
        return {Path(c.GetPathName()).stem:c for raw in assembly.GetComponents(True) for c in [asif(raw,api.IComponent2)]}
    def verify(doc,groups,q):
        doc.ForceRebuild3(False);error=0.
        for g,c in groups.items():
            x,y,ang=group_pose(g,q);v=asif(c.Transform2,api.IMathTransform).ArrayData
            error=max(error,math.dist([x,y,0],[v[i]*1000 for i in [9,10,11]]))
            if g!='wheel':error=max(error,L*abs(math.atan2(v[1],v[0])-math.radians(ang)))
        return error
    for title,q in configs:
        if not m.GetConfigurationByName(title):
            if not m.AddConfiguration3(title,'Leg angle '+str(q),'',0):raise RuntimeError('create '+title)
        m.ShowConfiguration2(title)
        groups=components(a)
        for g,c in groups.items():
            if g!='base':
                x,y,ang=group_pose(g,q);c.Transform2=tr(x,y,0,ang)
        m.EditRebuild3();err=verify(m,groups,q)
        if err>.02:raise RuntimeError(f'{title} positioning {err}')
        save(m,path)
    m.ShowConfiguration2('Midstroke');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,path)
    sw.CloseDoc(m.GetTitle());m=open_doc(path,2);activate(m);a=asif(m,api.IAssemblyDoc)
    poses=[];errors=[];cc=[]
    for title,q in configs:
        m.ShowConfiguration2(title);active=asif(asif(m.ConfigurationManager,api.IConfigurationManager).ActiveConfiguration,api.IConfiguration).Name
        err=verify(m,components(a),q);poses.append(dict(configuration=active,q=q,reopened_error_mm=err))
        log('reopened pose '+str(poses[-1]))
        if active!=title or err>.02:raise RuntimeError('reopened configuration pose')
        cc=[asif(c,api.IComponent2) for c in a.GetComponents(False)]
        assert len(cc)==len(INST)+5 and all(c.GetModelDoc2() is not None and Path(c.GetPathName()).is_relative_to(base) for c in cc)
        feat=m.FirstFeature();count=0
        while feat:
            f=asif(feat,api.IFeature)
            if f.GetTypeName2()=='MateGroup':
                item=f.GetFirstSubFeature()
                while item:
                    k=asif(item,api.IFeature);ec=k.GetErrorCode2(False)
                    if k.GetTypeName2().startswith('Mate'):count+=1
                    if ec[0]:errors.append([title,k.Name,ec])
                    item=k.GetNextSubFeature()
            feat=f.GetNextFeature()
        if errors or count!=9:raise RuntimeError(str((errors,count)))
    m.ShowConfiguration2('Midstroke');m.ForceRebuild3(False);m.ViewZoomtofit2();save(m,path)
    (ROOT/'data'/'solidworks.json').write_text(json.dumps(dict(revision=sw.RevisionNumber(),parts=len(PARTS),instances=len(INST),mates=9,reopen_components=len(cc),mate_errors=errors,poses=poses),indent=2))
    log('BUILD_COMPLETE')
if __name__=='__main__':
    flag=sw.CommandInProgress
    try:
        sw.CommandInProgress=True;log('SW '+sw.RevisionNumber()+' '+part_tpl+' '+ass_tpl)
        vf=ROOT/'data'/'sw_volumes.json';vol=json.loads(vf.read_text()) if vf.exists() else {}
        # Only this output directory is owned by the builder.
        for owned in [base/'Q8_Single_Corner.SLDASM', *sub.glob('*.SLDASM'),*pd.glob('*.SLDPRT')]:
            old=sw.GetOpenDocumentByName(str(owned))
            if old:sw.CloseDoc(asif(old,api.IModelDoc2).GetTitle())
        if '--poses' in sys.argv:
            path=base/'Q8_Single_Corner.SLDASM';m=open_doc(path,2);a=asif(m,api.IAssemblyDoc)
            C={Path(c.GetPathName()).stem:c for raw in a.GetComponents(True) for c in [asif(raw,api.IComponent2)]}
            solve_poses(m,a,C,path);sys.exit(0)
        for id in PARTS:
            if not (pd/(id+'.SLDPRT')).exists() or id not in vol or '--redo-'+id in sys.argv:
                vol[id]=make_part(id);vf.write_text(json.dumps(vol,indent=2));log('part '+id)
        for g in ['base','drive','passive','carrier','wheel']:
            if not (sub/(g+'.SLDASM')).exists() or '--groups' in sys.argv or '--redo-'+g in sys.argv:make_group(g)
            make_axes(g)
        top()
    except Exception as e:log('Stopped '+repr(e));traceback.print_exc();sys.exit(1)
    finally:sw.CommandInProgress=flag
