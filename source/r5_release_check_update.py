from pathlib import Path
p=Path('r5_motion_release.py');s=p.read_text(encoding='utf8');i=s.index(" m.ShowConfiguration2('Motion')\n if m.GetConfigurationByName");j=s.index(" m=open_doc(topfile,2);activate(m);a=asif(m,api.IAssemblyDoc);result",i)
s=s[:i]+s[j:];s=s.replace("len(mf)==40","len(mf)==44").replace("mates=len(mf),rack=","mates=len(mf),active_mates=40 if k.startswith('Motion') else 44,rack=")
s=s.replace("m.ShowConfiguration2('Motion');m.ForceRebuild3(True);C=parts(a);qs=poses['Motion'].copy()","m.ShowConfiguration2('Motion');m.ForceRebuild3(True);C=parts(a);qs=poses['Motion'].copy()")
p.write_text(s,encoding='utf8')
p=Path('r5_delivery.py');s=p.read_text(encoding='utf8').replace('顶层四个轮腿运动链共有 40 个配合。','顶层四个轮腿运动链共有 40 个连接配合，另有 4 个姿态距离配合。在 Motion 与 Motion_MID 中压缩这 4 个距离配合，保留手动拖动自由度。');p.write_text(s,encoding='utf8')

