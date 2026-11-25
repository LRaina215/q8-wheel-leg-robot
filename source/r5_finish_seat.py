from pathlib import Path
p=Path('r5_parts.py');s=p.read_text(encoding='utf8');s=s.replace("C([(0,-15.5),(0,15.5)],3.4),True,'z',45)","C([(0,-15.5),(0,15.5)],3.0),True,'z',45)");p.write_text(s,encoding='utf8')
p=Path('r5_instances.py');s=p.read_text(encoding='utf8').replace("astra,'Flat3x10',38.95","astra,'Flat3x10',39");p.write_text(s,encoding='utf8')
p=Path('r5_vehicle.py');s=p.read_text(encoding='utf-8-sig').replace("if '--check' not in sys.argv:build()","if '--check' not in sys.argv:\n   from r5_saddle_seat import run\n   run();build()");p.write_text(s,encoding='utf8')

