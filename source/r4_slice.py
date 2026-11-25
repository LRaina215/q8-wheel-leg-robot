from common import ROOT
import os,subprocess,tempfile,shutil
from pathlib import Path
p=ROOT/'source'/'slicer'; studio=Path(os.environ.get('Q8_BAMBU','E:/Bambu Studio'))
tmp=Path(tempfile.mkdtemp(prefix='q8_r4_tray_'))
args=[studio/'bambu-studio.exe','--load-settings',str(p/'machine.json')+';'+str(p/'process.json'),'--load-filaments',p/'filament.json','--curr-bed-type','Textured PEI Plate','--orient','0','--arrange','1','--slice','0','--outputdir',tmp,'--export-3mf','04_BuckTray.3mf',ROOT/'A1_STL'/'BuckTray.stl']
with (tmp/'slice.log').open('wb') as f:subprocess.run(list(map(str,args)),check=True,cwd=studio,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
shutil.copy2(tmp/'04_BuckTray.3mf',ROOT/'A1_3MF'/'04_BuckTray.3mf')
import filament_ledger
