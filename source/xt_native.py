"""Retain the shaft's original concentric mate; replace its fixed outboard components."""
from vehicle_sw import *
from finalize_native import verify
from geometry import shape
from collections import Counter

def localise():
    for assembly in OUT.rglob('*.SLDASM'):
        if assembly.name.startswith('~$'):continue
        for ref in set((sw.GetDocumentDependencies2(str(assembly),False,False,False) or [])[1::2]):
            source=Path(ref)
            if source.is_relative_to(OUT):continue
            idx=[i for i,x in enumerate(source.parts) if x.lower()=='solidworks']
            assert idx,source
            new=OUT.joinpath(*source.parts[idx[-1]+1:])
            if not new.exists() and (OUT/'R1'/new.relative_to(OUT)).exists():new=OUT/'R1'/new.relative_to(OUT)
            assert new.exists() and sw.ReplaceReferencedDocument(str(assembly),str(source),str(new)),(assembly,source,new)

def update():
    localise()
    folder=OUT/'R1'/'parts'
    for key,p in leg.PARTS.items():
        if not key.startswith('XT'):continue
        path=folder/(key+'.SLDPRT')
        if not path.exists():fixedpart(key,p,folder)
        m=open_doc(path,1)
        assert Path(m.GetPathName()).resolve()==path.resolve()
        solids=asif(m,api.IPartDoc).GetBodies2(0,False)
        assert len(solids)==1
        actual=asif(solids[0],api.IBody2).GetMassProperties(1)[3]*1e9
        assert abs(actual-shape(p).Volume())<.08,(key,actual)
        sw.CloseDoc(m.GetTitle())
    for path in [OUT/'R1'/'groups'/'wheel.SLDASM',OUT/'LH'/'LH_wheel.SLDASM']:
        m=open_doc(path,2);assert Path(m.GetPathName()).resolve()==path.resolve()
        activate(m);a=asif(m,api.IAssemblyDoc)
        old=[c for c in direct(a) if Path(c.GetPathName()).stem in ['P06','H04','H13','S01']]
        if old:
            m.ClearSelection2(True)
            for c in old:assert c.Select4(True,None,False)
            assert asif(m.Extension,api.IModelDocExtension).DeleteSelection2(0)
        existing={(Path(c.GetPathName()).stem,round(asif(c.Transform2,api.IMathTransform).ArrayData[11]*1000,2)) for c in direct(a)}
        for t in leg.INST:
            k=t['id']
            if t['g']!='wheel' or not (k.startswith('XT') or k=='H05') or (k,t['z']) in existing:continue
            insert(m,a,folder/(k+'.SLDPRT'),1,k+'_'+str(int(t['z'])),tr(0,t['y'],t['z']),True)
        m.ForceRebuild3(False)
        assert Counter(Path(c.GetPathName()).stem for c in direct(a))==Counter(t['id'] for t in leg.INST if t['g']=='wheel')
        save(m,path);sw.CloseDoc(m.GetTitle())
    verify()
    from sw_centres import run
    run()
    from pose_view import main
    main()
    swb.log('BUILD_COMPLETE')

if __name__=='__main__':
    original=sw.CommandInProgress
    try:
        sw.CommandInProgress=True
        update()
    finally:sw.CommandInProgress=original
