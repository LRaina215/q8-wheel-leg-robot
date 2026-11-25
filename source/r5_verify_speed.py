from pathlib import Path
p=Path('r5_native_audit.py');s=p.read_text(encoding='utf-8-sig').replace('m.ForceRebuild3(False)','m.ForceRebuild3(True)').replace('assert p.is_relative_to(OUT) and p.exists(),p','if p not in paths:assert p.is_relative_to(OUT) and p.exists() and c.GetModelDoc2(),p');p.write_text(s,encoding='utf8')
p=Path('r5_portable.py');s=p.read_text(encoding='utf8').replace('m.ForceRebuild3(False)','m.ForceRebuild3(True)').replace("['Motion','Motion_MID','Diagonal']","['Motion','Motion_MID']")
s=s.replace("bad=[c.GetPathName() for c in rows if not c.IsSuppressed() and (not c.GetModelDoc2() or not Path(c.GetPathName()).is_relative_to(dest))]","""live=[c for c in rows if not c.IsSuppressed()];seen=set();bad=[]
  for c in live:
   path=Path(c.GetPathName())
   if path in seen:continue
   seen.add(path)
   if not c.GetModelDoc2() or not path.is_relative_to(dest):bad.append(str(path))""").replace('sum(not c.IsSuppressed() for c in rows)','len(live)');p.write_text(s,encoding='utf8')

