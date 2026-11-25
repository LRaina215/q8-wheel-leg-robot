from common import *
# The corner API helper expects its part/group directory at import.
(LEG/'SolidWorks').mkdir(exist_ok=True)
import build_sw as swb
from build_sw import api,sw,asif,tr,save,open_doc,activate,insert,planes
swb.ROOT=ROOT
def xf(pos,matrix):
    return swb.mu.CreateTransform(swb.arr(list(np.asarray(matrix).T.ravel())+[v/1000 for v in pos]+[1,0,0,0]))
def fixedpart(key,part,dir):
    swb.pd=dir;swb.PARTS[key]=part
    return swb.make_part(key)
def do_mirror():
    d=OUT/'LH';partdir=OUT/'R1'/'parts';asym={'P01','P02','P03','P04','P05'}
    for id in asym:
        if not (d/('LH_'+id+'.SLDPRT')).exists():fixedpart('LH_'+id,mirrored(leg.PARTS[id]),d)
    for g,axes in swb.axes.items():
        p=d/('LH_'+g+'.SLDASM')
        if p.exists():continue
        m,a=swb.new_ass(p);children={}
        for i,t in enumerate(v for v in leg.INST if v['g']==g):
            id=t['id'];path=d/('LH_'+id+'.SLDPRT') if id in asym else partdir/(id+'.SLDPRT')
            c=insert(m,a,path,1,'M_'+id+'_'+str(i+1),tr(-t['x'],t['y'],t['z'],-t['rot'],t['flip']),True)
            children.setdefault(id,c)
        ext=asif(m.Extension,api.IModelDocExtension)
        for key,id,x,y,r in axes:
            ent=swb.child_cylinder(children[id],-x,y,r);m.ClearSelection2(True);assert ent.Select4(False,None)
            assert m.InsertAxis2(True);asif(ext.GetLastFeatureAdded(),api.IFeature).Name='Axis_'+key
        m.ClearSelection2(True);m.ForceRebuild3(False);save(m,p);sw.CloseDoc(m.GetTitle())
    p=d/'Q8_Corner_Mirror.SLDASM';m,a=swb.new_ass(p);C={}
    for g in swb.axes:
        x,y,ang=pose(g,0,-1);C[g]=insert(m,a,d/('LH_'+g+'.SLDASM'),2,g,tr(x,y,0,ang),g=='base')
    for key,g1,g2,axial in [('A','base','drive',True),('B','base','passive',True),('C','drive','carrier',True),('D','passive','carrier',False),('W','carrier','wheel',True)]:
        ff=lambda g:asif(C[g].FeatureByName('Axis_'+key),api.IFeature)
        swb.add_mate(m,a,'Hinge_'+key,ff(g1),ff(g2),0)
        if axial:
            plane=lambda g:asif(C[g].FeatureByName(planes(asif(C[g].GetModelDoc2(),api.IModelDoc2))[0]),api.IFeature)
            swb.add_mate(m,a,'Axial_'+g2,plane('base'),plane(g2),0)
    set_poses(p,m,a)
def set_poses(p,m,a):
    for name,q in [('Crouch',-36),('Midstroke',-7),('Liftoff',22)]:
        if not m.GetConfigurationByName(name):m.AddConfiguration3(name,'','',0)
        m.ShowConfiguration2(name)
        C={Path(c.GetPathName()).stem[3:]:c for raw in a.GetComponents(True) for c in [asif(raw,api.IComponent2)]}
        for g,c in C.items():
            if g!='base':
                x,y,ang=pose(g,q,-1);c.Transform2=tr(x,y,0,ang)
        m.EditRebuild3();m.ForceRebuild3(False);save(m,p)
    m.ShowConfiguration2('Midstroke');m.ViewZoomtofit2();save(m,p);sw.CloseDoc(m.GetTitle())
    m=open_doc(p,2);a=asif(m,api.IAssemblyDoc);qa={}
    for name,q in [('Crouch',-36),('Midstroke',-7),('Liftoff',22)]:
        m.ShowConfiguration2(name);m.ForceRebuild3(False)
        c=next(c for raw in a.GetComponents(True) for c in [asif(raw,api.IComponent2)] if Path(c.GetPathName()).stem=='LH_carrier')
        v=asif(c.Transform2,api.IMathTransform).ArrayData;x,y,_=pose('carrier',q,-1)
        err=math.hypot(v[9]*1000-x,v[10]*1000-y);assert err<.02,(name,err);qa[name]=err
    write(ROOT/'data'/'mirror.json',qa);sw.CloseDoc(m.GetTitle());swb.log('Mirror validated')
if __name__=='__main__':
    sw.CommandInProgress=True
    try:
        p=OUT/'LH'/'Q8_Corner_Mirror.SLDASM'
        if p.exists():
            m=open_doc(p,2);activate(m);set_poses(p,m,asif(m,api.IAssemblyDoc))
        else:do_mirror()
    finally:sw.CommandInProgress=False
