from pathlib import Path
p=Path('r5_portable.py');s=p.read_text(encoding='utf-8-sig');s=s.replace(" f=dest/('Q8R5_'+topfile.name)", """ # Release only the working copy and the intermediate R5 documents opened by this build.
 scope=[]
 for raw in sw.GetDocuments() or []:
  doc=asif(raw,api.IModelDoc2);original=Path(doc.GetPathName())
  if original.is_relative_to(OUT):scope.append((original.suffix.upper()!='.SLDASM',len(original.parts),doc.GetTitle()))
 for _,__,title in sorted(scope):
  sw.CloseDoc(title)
 f=dest/('Q8R5_'+topfile.name)""")
s=s.replace('save(m,f);sw.CloseDoc(m.GetTitle())','save(m,f);activate(m)')
p.write_text(s,encoding='utf8')

