from common import ROOT,read
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from collections import Counter
import os
D=ROOT/'data';db=read(D/'整车线束.json');routes=db['routes'];nodes=db['nodes'];native=read(D/'原生依赖清单.json')
assert len({r['id'] for r in routes})==len(routes)==77
assert sum(not r['optional'] for r in routes)==71
assert {r['a'][:2] for r in routes if 'frames'in r}=={'FL','FR','RL','RR'}
for r in routes:
    assert r['a'] in nodes and r['b'] in nodes and r['fixed_mm']>0 and r['fitted']>0
    if 'frames' in r:assert len(r['frames'])==70 and r['fixed_mm']<r['fitted']
    if 'stock_target' in r:assert abs(r['fixed_mm']-r['stock_target'])<1.5
assert not any('Daygreen' in n for n in native)
assert all(any(n.endswith('/'+key+'.SLDPRT') for n in native) for key in ['YourCee20','BuckTray'])
assert not read(D/'固定线束复核.json')['separation_exceptions'] and not read(D/'线对线复核.json')['fixed_overlap']
assert not read(D/'clearance.json')['intersections']
assert len(read(D/'总装配置质量.json'))==6
assert all(float(v)==round(read(D/'analysis.json')['slice_mid' if 'MID' in k else 'slice']['mass'],4) for k,v in read(D/'总装配置质量.json').items())
purch=read(D/'procurement.json');assert abs(sum(r['amount'] for r in purch)-read(D/'首车造价.json')['total'])<.001
assert all(not r['url'] or urlparse(r['url']).hostname in {'item.taobao.com','detail.tmall.com','s.taobao.com','uland.taobao.com'} for r in purch)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.files=set()
    def handle_starttag(self,tag,attrs):
        h=dict(attrs).get('href','') if tag=='a' else ''
        if h and not h.startswith('#') and not urlparse(h).scheme:self.files.add(unquote(h))
html=ROOT/'整车动作与载荷.html';links=Links();links.feed(html.read_text(encoding='utf8'))
files=set(native)|links.files|{x.name for x in ROOT.glob('*.md')}|{x.name for x in ROOT.glob('*.csv')}|{html.name}
for dir,pat in [('A1_3MF','*.3mf'),('A1_STL','*.stl'),('data/taobao','*')]:
    files.update(p.relative_to(ROOT).as_posix() for p in (ROOT/dir).rglob(pat) if p.is_file())
# The package carries the actual source data for the delivered version and omits superseded selection trials.
skip={'采购选型核对.json','铨洲轮毂活动回执.json','HTML_整车桌面.png','selected_hub.json','hub.json'}
files.update(p.relative_to(ROOT).as_posix() for p in D.iterdir() if p.is_file() and p.suffix!='.bmp' and p.name not in skip)
files.update('source/'+s for s in ['THREE-LICENSE.txt','three.min.js','vehicle_template.html','module_inspector.css','module_inspector.js','wire_view.js','module_catalog.py','report.py','common.py','wire_nets.py','wire_space.py','wire_route.py','wire_slack.py','wire_dress.py','wire_check.py','wire_fixed_check.py','wire_paircheck.py','buck_geometry.py','r4_accounts.py','r4_model.py','r4_slice.py','r4_notes.py','r4_native.py','r4_stamp.py','r4_pack.py','r4_preview.cjs','as_sliced.py','loads.py','xt_heights.py','xt_mass.py','reference_6kg.py','layout.py','geometry_vehicle.py','clearance.py','native.py','vehicle_sw.py','finalize_native.py','pose_view.py','xt_native.py','xt_manifest.py','filament_ledger.py','body_step/YourCee20.step','body_step/BuckTray.step'])
files.update(p.relative_to(ROOT).as_posix() for name in ['source/corner/source','source/corner/data','source/slicer'] for p in (ROOT/name).glob('*') if p.is_file())
files={p for p in files if '/.~' not in p}
assert all((ROOT/p).is_file() for p in files),[p for p in files if not(ROOT/p).is_file()]
z=Path(os.environ.get('Q8_PACKAGE_DIR',str(ROOT)))/'Q8_R4_双降压与整车线束.zip'
z.parent.mkdir(parents=True,exist_ok=True)
with ZipFile(z,'w',ZIP_DEFLATED,compresslevel=3) as f:
    for n in sorted(files):f.write(ROOT/n,n)
with ZipFile(z) as f:
    assert set(native)<=set(f.namelist()) and links.files<=set(f.namelist())
    assert all(f.getinfo(n).file_size for n in native)
print('ZIP',z.stat().st_size,len(files),len(native),len(links.files),flush=True)
