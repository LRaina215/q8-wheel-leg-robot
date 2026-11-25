from pathlib import Path
import shutil
p=Path('r5_parts.py');p.write_text(p.read_text(encoding='utf8')+"\nchanged={'Chassis','Deck','BuckTray','XT_saddle','Bridge_tray'}\ndef native_name(k):return ('R5F_' if k in changed else 'R5_')+k+'.SLDPRT'\n",encoding='utf8')
p=Path('r5_native_parts.py');p.write_text(p.read_text(encoding='utf-8-sig').replace('from r5_parts import parts','from r5_parts import parts,native_name').replace("folder/('R5_'+k+'.SLDPRT')",'folder/native_name(k)').replace("folder/('R5_'+key+'.SLDPRT')",'folder/native_name(key)'),encoding='utf8')
p=Path('r5_instances.py');p.write_text(p.read_text(encoding='utf8').replace('import parts as design,','import parts as design,native_name,').replace("('R5_'+k+'.SLDPRT')",'native_name(k)'),encoding='utf8')
shutil.copyfile('../data/R5_static.json','../data/R5_static_iteration1.json')

