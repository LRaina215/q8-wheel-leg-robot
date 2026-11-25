from pathlib import Path
p=Path('r5_motion_release.py');s=p.read_text(encoding='utf8')
s=s.replace(" solve_rig(m,a,poses['Motion'])",""" for cfg,qs in poses.items():
  m.ShowConfiguration2(cfg);C=solve_rig(m,a,qs)
  dev=measure(C,qs);assert max(dev.values())<.04,(cfg,dev)
  print('restored',cfg,flush=True)
 m.ShowConfiguration2('Motion');m.ForceRebuild3(True)""")
s=s.replace("m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();save(m,topfile)\n write(ROOT/'data/R5_motion.json'","m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2()\n write(ROOT/'data/R5_motion.json'")
p.write_text(s,encoding='utf8')

