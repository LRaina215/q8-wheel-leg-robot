from pathlib import Path
p=Path('r5_motion_release.py');s=p.read_text(encoding='utf-8-sig')
s=s.replace("old=qs[n];drag_segment(m,a,C,n,old,target);qs[n]=target","""old=qs[n];drag_segment(m,a,C,n,old,target);qs[n]=target
   front=1 if n.startswith('F') else -1
   for correction in range(2):
    v=coords(C[n,'carrier']);qread=math.degrees(math.atan2(-v[11]*1000,front*(v[10]*1000-front*HY)))
    if abs(qread-target)<.008:break
    print('residual',n,target,qread,flush=True);drag_segment(m,a,C,n,qread,target)""")
p.write_text(s,encoding='utf8')

