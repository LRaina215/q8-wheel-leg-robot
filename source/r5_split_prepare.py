from pathlib import Path
p=Path('r5_vehicle.py');s=p.read_text(encoding='utf8').replace('run();build()','run()\n   from r5_drive_split import install\n   install();build()');p.write_text(s,encoding='utf8')
p=Path('corner/source/design.py');s=p.read_text(encoding='utf-8-sig');i=s.index("add('M01'");j=s.index("add('M02'",i);s=s[:i]+"""add('M01','DM-J4310M-2EC 定子接口简模','motor',[
    op('Stator_envelope',-53.3,52.3,circ(0,0,28.5),*radial_holes(stat,1.25)),
    op('Rotor_review_recess',-5.2,4.3,circ(0,0,17.65),cut=True)])
add('Rotor4310','髋电机输出法兰 · 随主动臂','drive',[
    op('Rotating_output_interface',-5,5,circ(0,0,17.5),*radial_holes(rotor,1.52))])
"""+s[j:];s+="\nins('Rotor4310','drive',0,0,0)\n";p.write_text(s,encoding='utf8')

