from common import *
import zlib,base64
from module_catalog import GROUPS
d=read(ROOT/'data'/'layout.json')
a=read(ROOT/'data'/'analysis.json');proc=read(ROOT/'data'/'procurement.json') if (ROOT/'data'/'procurement.json').exists() else []
v=dict(body=json.loads(zlib.decompress((ROOT/'data'/'bodymesh.bin').read_bytes())),parts=d['parts'],items=d['instances'],legs=json.loads(zlib.decompress((ROOT/'data'/'legmesh.bin').read_bytes())),inst=leg.INST,col={k:p['color'] for k,p in leg.PARTS.items()},loads=a,bom=proc,ledger=read(ROOT/'data'/'质量审计.json'),small=read(ROOT/'data'/'20mm质心低跳.json'))
v['modules']=GROUPS
v['wiring']=read(ROOT/'data'/'整车线束.json')
v['wireQA']=read(ROOT/'data'/'线束间隙.json')
v['fixedQA']=read(ROOT/'data'/'固定线束复核.json')
v['pairQA']=read(ROOT/'data'/'线对线复核.json')
v['wireMass']=read(ROOT/'data'/'线材用量.json')
catalog=[entry[0] for group in GROUPS.values() for entry in group]
drawn={t['id'] for t in v['items'] if t['id'] in v['body']} | {t['id'] for t in v['inst']}
in_ledger={r['id'] for r in v['ledger']}
assert len(catalog)==len(set(catalog))
assert set(catalog)==drawn | {'Loom','LegHarness','MidHarness','Hardware','SSD'}
assert set(catalog)-{'XT100_Tyre','XT100_Rim'}==in_ledger-{'Wheel'}
v['twenty']=read(ROOT/'data'/'四配置20mm动作.json')
v['cost']=read(ROOT/'data'/'首车造价.json')
v['ref6']=read(ROOT/'data'/'reference_6kg.json')
t=(Path(__file__).parent/'vehicle_template.html').read_text(encoding='utf8').replace('__THREE__',(Path(__file__).parent/'three.min.js').read_text(encoding='utf8')).replace('__VEHICLE__',json.dumps(v,ensure_ascii=False,separators=(',',':')))
for marker,file in [('__INSPECTOR_CSS__','module_inspector.css'),('__INSPECTOR_JS__','module_inspector.js'),('__WIRE_JS__','wire_view.js')]:
    t=t.replace(marker,(Path(__file__).parent/file).read_text(encoding='utf8'))
t=t.replace('__SW_IMAGE__',base64.b64encode((ROOT/'data'/'SW_Ride.png').read_bytes()).decode())
(ROOT/'整车动作与载荷.html').write_text(t,encoding='utf8')

