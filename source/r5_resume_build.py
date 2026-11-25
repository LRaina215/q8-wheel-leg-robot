from pathlib import Path
p=Path('r5_instances.py');s=p.read_text(encoding='utf-8-sig').replace("if k in ['Jsp','Loom','Hardware','MidHarness']:continue","if k=='Jsp' or old['parts'][k]['kind']=='分布质量':continue");p.write_text(s,encoding='utf8')
p=Path('r5_rack.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace('m,a=swb.new_ass(rack);activate(m)',"""if rack.exists():
  m=open_doc(rack,2);a=asif(m,api.IAssemblyDoc)
 else:m,a=swb.new_ass(rack)
 activate(m);available=direct(a)""")
before="c=insert(m,a,path,2 if id=='HipStack' else 1,k,xf(t['pos'],matrix(t)),id=='Chassis');C[k]=c;index[id].append(k);T[k]=t"
s=s.replace(before,"""c=next((v for v in available if Path(v.GetPathName())==path and np.max(np.abs(np.array(asif(v.Transform2,api.IMathTransform).ArrayData[9:12])*1000-t['pos']))<.07),None)
  existed=c is not None
  if existed:available.remove(c)
  else:c=insert(m,a,path,2 if id=='HipStack' else 1,k,xf(t['pos'],matrix(t)),id=='Chassis')
  C[k]=c;index[id].append(k);T[k]=t""")
s=s.replace("if id=='Chassis':continue","if id=='Chassis' or existed:continue")
s=s.replace("if len(C)%15==0:print('mounted',len(C),k,flush=True)","if len(C)%15==0:save(m,rack);print('mounted',len(C),k,flush=True)")
p.write_text(s,encoding='utf8')

