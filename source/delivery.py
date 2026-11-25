from common import *
from zipfile import ZipFile,ZIP_DEFLATED
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from PIL import Image
import tempfile
class Anchor(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,t,attrs):
        if t=='a' and 'href' in dict(attrs):self.links.append(dict(attrs)['href'])
def main():
    html=ROOT/'整车动作与载荷.html';content=html.read_text(encoding='utf-8')
    pars=Anchor();pars.feed(content)
    links={p for p in pars.links if p and not p.startswith('#') and not urlparse(p).scheme}
    for p in links:assert (ROOT/unquote(p)).is_file(),p
    assert '__SW_IMAGE__' not in content and '__VEHICLE__' not in content
    ms=read(ROOT/'data'/'analysis.json');sw=read(ROOT/'data'/'solidworks.json')
    assert len(sw['configs'])==6 and all(not s['missing'] for s in sw['configs'].values())
    assert all(abs(sum(p['static']['-7']['kg'].values())-p['mass'])<1e-7 for p in ms.values())
    assert len(read(ROOT/'data'/'native_wheel_centres.json'))==3 and not read(ROOT/'data'/'clearance.json')['intersections']
    proc=read(ROOT/'data'/'procurement.json')
    cost=read(ROOT/'data'/'首车造价.json')
    assert abs(sum(x['amount'] for x in proc)-cost['total'])<.005
    rack=sw.get('powertrain',{})
    assert rack.get('removed_brake') and rack['installed'].get('ZC7112A')==2 and rack['installed'].get('FFC24_65')==1
    allowed={'item.taobao.com','detail.tmall.com','s.taobao.com','uland.taobao.com','gy2025.com'}
    for b in proc:
        assert not b['url'] or urlparse(b['url']).hostname in allowed
    frames=sorted((Path(tempfile.gettempdir())/'q8_whole_frames').glob('f??.png'));assert len(frames)==35
    imgs=[]
    for f in frames:
        with Image.open(f) as i:
            imgs.append(i.convert('RGB').resize((650,round(650*i.height/i.width)),Image.Resampling.LANCZOS).convert('P',palette=Image.Palette.ADAPTIVE,colors=128))
    imgs[0].save(ROOT/'整车低跳动作.gif',save_all=True,append_images=imgs[1:],duration=[600]+[100]*33+[650],loop=0,optimize=True)
    selected={row['url'].split('&skuId=')[0] for row in proc if row['title']}
    bodyparts=set(read(ROOT/'data'/'layout.json')['parts'])
    output=ROOT/'Q8_整车R2_首件设计包.zip'
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=4) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file():continue
            r=p.relative_to(ROOT)
            if r.parts[:2]==('SolidWorks','body') and p.suffix.lower()=='.sldprt' and p.stem not in bodyparts:continue
            if r.parts[:2]==('source','body_step') and p.stem not in bodyparts and p.stem!='W08_installed':continue
            if p.name.startswith(('~$','.')) or '__pycache__' in r.parts or p.suffix.lower() in ['.pyc','.zip','.bmp','.gcode']:continue
            if 'taobao' in r.parts:
                d=json.loads(p.read_text(encoding='utf-8-sig'))
                d['cards']=[c for c in d.get('cards',[]) if isinstance(c,dict) and c['url'].split('&skuId=')[0] in selected]
                if d['cards'] and p.stem not in ['Astra','JET','XT','H04','H04_r','H04alt','H04alt_r','cut_r','plate']:z.writestr(r.as_posix(),json.dumps(d,ensure_ascii=False))
                continue
            if p.name in ['单腿采购清单.csv','result.json','build_log.txt'] or p.name.endswith('_view.ps1') or p.suffix=='.txt' and p.stem in ['queries','extra_queries']:continue
            z.write(p,r.as_posix())
    with ZipFile(output) as z:
        names=set(z.namelist())
        for link in links:assert link in names,link
        for p in (ROOT/'SolidWorks').rglob('*'):
            if p.parent==ROOT/'SolidWorks'/'body' and p.suffix.lower()=='.sldprt' and p.stem not in bodyparts:continue
            if p.is_file() and p.suffix.lower() in ['.sldasm','.sldprt'] and not p.name.startswith('~$'):assert p.relative_to(ROOT).as_posix() in names
        for n in ['整车低跳动作.gif','data/native_wheel_centres.json','data/铨洲轮毂活动回执.json','A1_3MF/legs/LH_02_Wheel_stack.3mf']:assert n in names,n
        print('files',len(names),'native',sum(n.lower().endswith(('.sldprt','.sldasm')) for n in names),'A1 plates',sum(n.endswith('.3mf') for n in names),'zip MB',round(output.stat().st_size/1e6,2))
if __name__=='__main__':main()
