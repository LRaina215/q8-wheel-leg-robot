from pathlib import Path
p=Path('r5_motion_release.py');s=p.read_text(encoding='utf8').replace('len(mf)==44','len(mf)==48').replace('active_mates=40 if k.startswith(\'Motion\') else 44','active_mates=44 if k.startswith(\'Motion\') else 48')
i=s.index('def release():');s=s[:i]+'''def pin_offsets(C):
 def map_point(c,p):
  v=coords(c);return np.array(p)@np.array(v[:9]).reshape(3,3)+1000*np.array(v[9:12])
 out={}
 for n,side,fore in corner_order:
  p=map_point(C[n,'passive'],[side*fore*110,0,0])
  q=map_point(C[n,'carrier'],[0,-62,0])
  out[n]=round(float(np.linalg.norm(p-q)),6)
 return out
'''+s[i:]
s=s.replace("result[k]=dict(angles=qs,","pins=pin_offsets(C);assert max(pins.values())<.035,(k,pins)\n  result[k]=dict(pin_D_axis_offset_mm=pins,angles=qs,")
s=s.replace("assert err<.06 and state==2","assert err<.06 and state==2 and max(pin_offsets(C).values())<.035")
p.write_text(s,encoding='utf8')
p=Path('r5_delivery.py');s=p.read_text(encoding='utf8').replace('共有 40 个连接配合','共有 44 个连接配合').replace('展开四角中任一主动臂组件','两根 110 mm 连杆采用平行配合，轮架与基座保持平行。D 销与轮架孔的同轴偏差已逐姿态独立计算。展开四角中任一主动臂组件')
p.write_text(s,encoding='utf8')

