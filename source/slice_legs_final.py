from pathlib import Path
import tempfile,shutil,subprocess,os
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from common import ROOT,write
studio=Path(os.environ.get('Q8_BAMBU','E:/Bambu Studio'))
d=ROOT/'A1_3MF'/'legs';d.mkdir(exist_ok=True)
s=Path(tempfile.mkdtemp(prefix='q8_a1_mirror_'));profiles=ROOT/'source'/'slicer'
rows=[]
for tag,ids in [('LH_02_Bearings',['LH_P05','P07','P07']),('R1_02_Bearings',['P05','P07','P07'])]:
    f=[]
    for i,id in enumerate(ids):
        p=s/(id+'_'+str(i)+'.stl');shutil.copyfile(ROOT/'A1_STL'/'legs'/(id+'.stl'),p);f.append(p)
    cmd=[studio/'bambu-studio.exe','--load-settings',f'{profiles/"machine.json"};{profiles/"process.json"}','--load-filaments',profiles/'filament.json','--curr-bed-type','Textured PEI Plate','--orient','0','--arrange','1','--slice','0','--outputdir',d,'--export-3mf',tag+'.3mf',*f]
    with (s/(tag+'.log')).open('wb') as log:r=subprocess.run(list(map(str,cmd)),cwd=studio,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError((tag,r.returncode,s))
    with ZipFile(d/(tag+'.3mf')) as z:
        plate,=ET.fromstring(z.read('Metadata/slice_info.config')).findall('plate')
        stats={a.get('key'):a.get('value') for a in plate.findall('metadata')};objs=plate.findall('object')
        assert stats['outside']=='false' and len(objs)==len(f) and all(o.get('skipped')=='false' for o in objs)
        rows.append(dict(plate=tag,grams=float(stats['weight']),seconds=int(stats['prediction'])))
write(ROOT/'data'/'mirror_prints.json',rows)
print(rows)
