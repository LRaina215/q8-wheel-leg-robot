from pathlib import Path
p=Path(__file__).with_name('r5_bundle.py');s=p.read_text(encoding='utf-8-sig')
a="for v in children:\n   assert sw.ReplaceReferencedDocument"
b="""if all(v.suffix.lower() in ['.step','.stp'] for v in children):
   # Retain the purchased interface solid in the native part; include its STEP source in the review package.
   path=target(p);m=open_doc(path,1);activate(m);part=asif(m,api.IPartDoc)
   volumes=lambda:sorted(asif(b,api.IBody2).GetMassProperties(1)[3]*1e9 for b in part.GetBodies2(0,False))
   before=volumes();f=m.FirstFeature()
   while f:
    f=asif(f,api.IFeature)
    if f.GetTypeName2().lower()=='mbimport':
     assert f.BreakLink(True,True)==0,p
     break
    f=f.GetNextFeature()
   m.ForceRebuild3(False);after=volumes();assert len(before)==len(after) and max(abs(a-b) for a,b in zip(before,after))<.01,p
   save(m,path);sw.CloseDoc(m.GetTitle());assert not references(path),(p,references(path))
   continue
  for v in children:
   assert sw.ReplaceReferencedDocument"""
assert a in s;p.write_text(s.replace(a,b),encoding='utf8')
