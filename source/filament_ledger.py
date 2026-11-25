from common import ROOT,write
from zipfile import ZipFile
from collections import Counter
import re,math,json
from xml.etree import ElementTree as ET
rows=[]
for p in sorted((ROOT/'A1_3MF').glob('*.3mf'))+sorted((ROOT/'A1_3MF'/'legs').glob('*.3mf')):
    with ZipFile(p) as z:
        current='Custom';roll=Counter();by_object=Counter();obj=None
        names={s.get('identify_id'):s.get('name') for s in ET.fromstring(z.read('Metadata/slice_info.config')).findall('.//object')}
        rgx=re.compile(rb'(?:^| )E(-?[.\d]+)')
        for line in z.open('Metadata/plate_1.gcode'):
            if line.startswith(b'; OBJECT_ID:'):
                obj=names.get(line.split(b':',1)[1].strip().decode());continue
            if line.startswith(b'; FEATURE: '):current=line[11:].strip().decode();continue
            if current=='Custom' or not line.startswith((b'G1 ',b'G2 ',b'G3 ')):continue
            code=line.split(b';')[0];k=rgx.search(code)
            if k and (b' X' in code or b' Y' in code):
                grams=max(0,float(k[1]))*math.pi*(1.75/2)**2*1.27/1000
                roll[current]+=grams
                if not current.startswith(('Support','Brim','Skirt','Prime','Wipe')):by_object[obj]+=grams
        baseline=sum(v for k,v in roll.items() if not k.startswith(('Support','Brim','Skirt','Prime','Wipe')))
        assert None not in by_object and len(by_object)==len(names)
        rows.append(dict(plate=p.stem,path_grams=round(baseline,2),all_deposition_grams=round(sum(roll.values()),2),object_grams={k:round(v,3) for k,v in by_object.items()},features={k:round(v,2) for k,v in roll.items()}))
print([(r['plate'],r['path_grams'],r['all_deposition_grams']) for r in rows])
write(ROOT/'data'/'a1_filament.json',rows)
