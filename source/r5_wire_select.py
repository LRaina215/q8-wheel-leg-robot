from pathlib import Path
p=Path('r5_report.py');s=p.read_text(encoding='utf-8-sig');a=s.index(" wiring=read(");b=s.index(" rows=read",a);s=s[:a]+" wiring=read(ROOT/'data/R5_wiring.json')\n"+s[b:];p.write_text(s,encoding='utf8')
p=Path('r5_wires_fit.py');s=p.read_text(encoding='utf-8-sig').replace("read(ROOT/'data/整车线束.json')","read(ROOT/'data/R5_wiring.json')");a=s.index(" if wire['a']=='NetU'");b=s.index(' frames=',a);p.write_text(s[:a]+s[b:],encoding='utf8')

