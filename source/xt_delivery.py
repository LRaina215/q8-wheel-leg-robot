from common import ROOT,read
from zipfile import ZipFile,ZIP_DEFLATED
from PIL import Image
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import tempfile
D=ROOT/'data'
frames=sorted((Path(tempfile.gettempdir())/'q8_whole_frames').glob('f??.png'));assert len(frames)==35
images=[]
for f in frames:
    with Image.open(f) as im:
        images.append(im.convert('RGB').resize((650,round(650*im.height/im.width)),Image.Resampling.LANCZOS).convert('P',palette=Image.Palette.ADAPTIVE,colors=128))
images[0].save(ROOT/'整车低跳动作.gif',save_all=True,append_images=images[1:],duration=[600]+[100]*33+[650],loop=0,optimize=True)
native=read(D/'原生依赖清单.json')
assert all(Path(n).stem not in ['P06','H13','H04','Brake'] for n in native)
assert len(native)==len(set(native))
kit=read(D/'solidworks.json')['configs'];assert len(kit)==6 and all(not c['missing'] for c in kit.values())
assert all(v['mount_counts']['XT100_Tyre']==4 for v in kit.values())
purch=read(D/'procurement.json');assert abs(sum(r['amount'] for r in purch)-read(D/'首车造价.json')['total'])<.001
assert all(not r['url'] or urlparse(r['url']).hostname in ['item.taobao.com','detail.tmall.com','s.taobao.com','uland.taobao.com'] for r in purch)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.refs=set()
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            h=dict(attrs).get('href','')
            if h and not h.startswith('#') and not urlparse(h).scheme:self.refs.add(unquote(h))
html=ROOT/'整车动作与载荷.html';anchors=Links();anchors.feed(html.read_text(encoding='utf8'))
files=set(native)|anchors.refs|{'整车低跳动作.gif','成品轮试配.md','整车动作与载荷.html','source/THREE-LICENSE.txt'}
for pat in ['A1_STL/**/*.stl','A1_3MF/**/*.3mf']:files.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pat))
data=['轮架净距','clearance','a1_filament','analysis','layout','procurement','reference_6kg','20mm质心低跳','四配置20mm动作','solidworks','native_wheel_centres','设备板减重试切','原生依赖清单','首车造价','质量审计']
files.update('data/'+n+'.json' for n in data)
for pattern in ['SW_*.png','HTML_*.png','整车蹬伸*.csv','质量与质心*.csv','塔克100卖家参数图.png']:
    files.update(p.relative_to(ROOT).as_posix() for p in D.glob(pattern))
out=ROOT/'Q8_整车R3_首件设计包.zip'
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=4) as z:
    for name in sorted(files):
        p=ROOT/name;assert p.is_file(),name
        z.write(p,name)
with ZipFile(out) as z:
    names=set(z.namelist());assert names==files and len([n for n in names if n.endswith('.3mf')])==7
    print(len(names),len(native),round(out.stat().st_size/1e6,1))

