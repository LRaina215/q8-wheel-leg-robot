from pathlib import Path
for fn in ['r5_parts.py','r5_instances.py','r5_static.py']:
 p=Path(fn);s=p.read_text(encoding='utf8').replace('(54,52)','(72,52)').replace('(-7,65)','(11,65)').replace('(-7,61,10,17)','(11,61,10,17)')
 if fn=='r5_instances.py':s=s.replace("put(k,t['pos'],t['name']", "put(k,[-35,-78.5,121] if k=='USBnet' else t['pos'],t['name']")
 p.write_text(s,encoding='utf8')

