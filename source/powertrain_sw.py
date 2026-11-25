"""Update the R2 equipment rack while preserving the native four-leg configurations."""
from finalize_native import verify
from vehicle_sw import *
from pathlib import Path
from collections import Counter
import base64,zlib

retired = {'WheelBuck', 'Dist', 'Logic', 'Brake', 'BranchFuse', 'MainFuse','FFC24'}
installed = {'Daygreen_B30', 'Wago615', 'ANS_H', 'ZC7112A', 'TXS0108E', 'FFC24_65'}

def update_sleeve():
    from geometry import shape
    sh=shape(leg.PARTS['H05'])
    path=OUT/'R1'/'parts'/'H05.SLDPRT'
    model=open_doc(path,1)
    assert Path(model.GetPathName()).resolve()==path.resolve()
    def volume():
        bodies=asif(model,api.IPartDoc).GetBodies2(0,False)
        assert len(bodies)==1
        return asif(bodies[0],api.IBody2).GetMassProperties(1)[3]*1e9
    if abs(volume()-sh.Volume())>.02:
        activate(model)
        boss=asif(asif(model,api.IPartDoc).FeatureByName('Sleeve'),api.IFeature)
        sketch=asif(boss.GetFirstSubFeature(),api.IFeature)
        assert sketch.GetTypeName2()=='ProfileFeature'
        model.ClearSelection2(True)
        assert sketch.Select2(False,0)
        model.EditSketch()
        active=asif(model.GetActiveSketch2(),api.ISketch)
        circles=[asif(arc,api.ISketchArc) for arc in active.GetSketchSegments()]
        inner=next(arc for arc in circles if abs(arc.GetRadius()-.00405)<1e-6)
        assert inner.SetRadius(.00410)
        asif(model.SketchManager,api.ISketchManager).InsertSketch(True)
        model.ForceRebuild3(False)
        assert abs(volume()-sh.Volume())<.02
        save(model,path)
    sw.CloseDoc(model.GetTitle())
    meta=read(LEG/'data'/'geometry.json')
    meta['H05']['volume_mm3']=sh.Volume()
    write(LEG/'data'/'geometry.json',meta)
    pts,idx=sh.tessellate(.16,.22)
    payload=[base64.b64encode(np.asarray(a,dtype=dtype).tobytes()).decode() for a,dtype in [([v.toTuple() for v in pts],'<f4'),(idx,'<u4')]]
    for filename in [LEG/'data'/'mesh.bin',ROOT/'data'/'legmesh.bin']:
        meshes=json.loads(zlib.decompress(filename.read_bytes()))
        meshes['H05']=payload
        filename.write_bytes(zlib.compress(json.dumps(meshes,separators=(',',':')).encode(),7))
    print('H05 OD12 / ID8.2 / L8 verified',flush=True)

def update_rack():
    # Patch the *closed copies*. Loading every individual part keeps too many
    # SolidWorks graphics documents alive and does not guarantee reference paths.
    prior=ROOT.with_name('Q8_整车_R1')/'SolidWorks'
    for f in OUT.rglob('*.SLDASM'):
        if f.name.startswith('~$'):continue
        refs=sw.GetDocumentDependencies2(str(f),False,False,False) or []
        for name in set(refs[1::2]):
            old=Path(name)
            if old.is_relative_to(prior):
                new=OUT/old.relative_to(prior)
                assert new.is_file(), new
                assert sw.ReplaceReferencedDocument(str(f),str(old),str(new)),(f,old)
    path = OUT/'Q8_Chassis_Equipment.SLDASM'
    model = open_doc(path,2)
    assert Path(model.GetPathName()).resolve() == path.resolve()
    assy = asif(model,api.IAssemblyDoc)
    ext = asif(model.Extension,api.IModelDocExtension)
    activate(model)
    model.ClearSelection2(True)
    old = [c for c in direct(assy) if Path(c.GetPathName()).stem in retired]
    for c in old:
        assert c.Select4(True,None,False), c.Name2
    if old:
        assert ext.DeleteSelection2(0)
    counts = Counter(Path(c.GetPathName()).stem for c in direct(assy))
    wanted = Counter()
    for t in items:
        key = t['id']
        if key not in installed:
            continue
        wanted[key] += 1
        if wanted[key] > counts[key]:
            insert(model,assy,bodypath(key),1,t['name'],xf(t['pos'],xyzrot(t['rz'])),True)
        elif key in ('FFC24_65','TXS0108E'):
            existing=next(c for c in direct(assy) if Path(c.GetPathName()).stem==key)
            model.ClearSelection2(True)
            assert existing.Select4(False,None,False)
            assy.UnfixComponent()
            existing.Transform2=xf(t['pos'],xyzrot(t['rz']))
            model.ClearSelection2(True)
            assert existing.Select4(False,None,False)
            assy.FixComponent()
            model.ClearSelection2(True)
    model.ForceRebuild3(False)
    current = Counter(Path(c.GetPathName()).stem for c in direct(assy))
    assert all(current[k] == n for k,n in wanted.items()) and not (retired & set(current))
    save(model,path)
    for c in direct(assy):
        assert Path(c.GetPathName()).is_relative_to(OUT),c.GetPathName()
        if Path(c.GetPathName()).stem in ('FFC24_65','TXS0108E'):
            p=asif(c.Transform2,api.IMathTransform).ArrayData[9:12]
            expected=next(t['pos'] for t in items if t['id']==Path(c.GetPathName()).stem)
            assert np.max(np.abs(np.array(p)*1000-expected))<.02,(p,expected)
    verify()
    qa=read(ROOT/'data'/'solidworks.json')
    qa['powertrain']=dict(installed=dict(wanted),removed_brake=True)
    write(ROOT/'data'/'solidworks.json',qa)

if __name__=='__main__':
    ok=sw.CommandInProgress
    try:
        sw.CommandInProgress=True
        if not all(bodypath(k).is_file() for k in installed):buildparts()
        update_sleeve()
        update_rack()
    finally:
        sw.CommandInProgress=ok
