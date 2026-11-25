"""Single-variable PETG trial. Does not replace the production plate."""
from common import ROOT,write
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import tempfile,subprocess,json,math,re,os
from pathlib import Path
studio=Path(os.environ.get('Q8_BAMBU','E:/Bambu Studio'))
src=ROOT/'source'/'slicer'
with tempfile.TemporaryDirectory(prefix='q8_deck_trial_') as temp:
    folder=Path(temp);profile=json.loads((src/'process.json').read_text(encoding='utf8'))
    profile['sparse_infill_density']='20%'
    settings=folder/'trial.json';settings.write_text(json.dumps(profile),encoding='utf8')
    cmd=[studio/'bambu-studio.exe','--load-settings',f'{src/"machine.json"};{settings}','--load-filaments',src/'filament.json','--curr-bed-type','Textured PEI Plate','--orient','0','--arrange','1','--slice','0','--outputdir',folder,'--export-3mf','deck.3mf',ROOT/'A1_STL'/'Deck.stl']
    with (folder/'trial.log').open('wb') as f:subprocess.run(list(map(str,cmd)),cwd=studio,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    rgx=re.compile(rb'(?:^| )E(-?[.\d]+)');net=0
    with ZipFile(folder/'deck.3mf') as z:
        feature='Custom'
        for line in z.open('Metadata/plate_1.gcode'):
            if line.startswith(b'; FEATURE: '):feature=line[11:].strip().decode();continue
            if feature=='Custom' or feature.startswith(('Support','Brim','Skirt','Prime','Wipe')):continue
            code=line.split(b';')[0]
            if code.startswith((b'G1 ',b'G2 ',b'G3 ')) and (b' X' in code or b' Y' in code):
                match=rgx.search(code)
                if match:net+=max(0,float(match[1]))*math.pi*(1.75/2)**2*1.27/1000
    write(ROOT/'data'/'设备板减重试切.json',dict(baseline_40pct_g=153.849,trial_20pct_g=round(net,3),saving_g=round(153.849-net,3),wall_loops=5,installed=False))
    print(net)

