from common import ROOT,write
from pathlib import Path
import subprocess,shutil,tempfile,os,ctypes
from xml.etree import ElementTree as ET
from zipfile import ZipFile
scratch=Path(tempfile.mkdtemp(prefix='q8_vehicle_slice_'))
profiles=ROOT/'source'/'slicer'
if not profiles.exists():shutil.copytree(ROOT.parent/'Q8_单轮腿_R1'/'source'/'slicer',profiles)
dst=ROOT/'A1_3MF';dst.mkdir(exist_ok=True)
studio=Path(os.environ.get('Q8_BAMBU','E:/Bambu Studio'))
kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p;kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(),15)
results=[]
for n,k in [('01_Chassis',['Chassis']),('02_Deck',['Deck']),('03_Sensor_and_driver_mounts',['Astra_saddle','Astra_saddle','XT_saddle','Bridge_tray','Bridge_tray'])]:
    files=[]
    for i,id in enumerate(k):
        f=scratch/(id+str(i)+'.stl');shutil.copyfile(ROOT/'A1_STL'/(id+'.stl'),f);files.append(f)
    cmd=[studio/'bambu-studio.exe','--load-settings',f'{profiles/"machine.json"};{profiles/"process.json"}','--load-filaments',profiles/'filament.json','--curr-bed-type','Textured PEI Plate','--orient','0','--arrange','1','--slice','0','--outputdir',dst,'--export-3mf',n+'.3mf',*files]
    with (scratch/(n+'.log')).open('wb') as log:r=subprocess.run(list(map(str,cmd)),cwd=studio,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError((n,r.returncode,str(scratch)))
    with ZipFile(dst/(n+'.3mf')) as z:
        p,=ET.fromstring(z.read('Metadata/slice_info.config')).findall('plate')
        m={a.get('key'):a.get('value') for a in p.findall('metadata')}
        objs=[s.get('name') for s in p.findall('object') if s.get('skipped')=='false']
        assert len(objs)==len(files) and m['outside']=='false' and z.getinfo('Metadata/plate_1.gcode').file_size>100
        results.append(dict(plate=n,grams=float(m['weight']),seconds=int(m['prediction']),objects=objs))
        print(n,m['weight'],m['prediction'],flush=True)
write(ROOT/'data'/'body_prints.json',results)
