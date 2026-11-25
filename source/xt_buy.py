from common import ROOT,read,write
import csv
D=ROOT/'data'
# The saved R2 BOM is an input; R3 is always rebuilt from that baseline.
base=read(ROOT.parent/'Q8_整车_R2'/'data'/'procurement.json')
rows=[]
for old in base:
    r=old.copy();name=r['name']
    if name.startswith(('轮毂凹端紧定','H13 ','M3 铜嵌件与 M4 顶丝')):continue
    if name.startswith('H04 '):
        r.update(name='塔克 100 mm 成品越野轮与 Ø8 铜接头',choice='100mm红圈橡胶轮 + 8mm铜制联轴器',qty='4套',status='项目已留存选中子规格',basis='同型号核价',packs=4,unit=20.70,amount=82.80,
        url='https://item.taobao.com/item.htm?id=764659136242&skuId=6021439206463',title='塔克创新品牌店 100mm 红圈橡胶轮 + 8mm 铜制联轴器',note='参数图约78 g；四轮负载标5 kg；满载低跳能力未获卖家数据支持。')
    if name.startswith('H05 '):r.update(qty='装12，买2包（每包10只）',packs=2,amount=16,note='每角轴承之间1只，外侧向轮毂叠2只。同规格铝隔套，Ø8.2×12×8。')
    if name.startswith('H06/H07/'):r.update(qty='需36，备50片',note='每角H06用1、H07用2、H12用6，共四角36片。')
    if name.startswith('S01 '):r.update(qty='髋座装24，另取8颗用于设备柱；买一批',note='原轮辋的24颗M3×8已取消，设备柱从同一包余量取用。')
    if name.startswith('PETG '):r['note']='两卷1 kg，首车七种打印盘、两对镜像腿；实际用料见装配说明。'
    rows.append(r)
fields=['group','name','choice','qty','packs','unit','amount','basis','status','note','url']
with (ROOT/'整车淘宝采购清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['类别','物品','应选型号或规格','装车或采购量','采购计价单位数','每计价单位元','行金额元','价格依据','货源核查','说明','淘宝商品链接'])
    w.writerows([[r[k] for k in fields] for r in rows])
basis={}
for r in rows:basis[r['basis']]=round(basis.get(r['basis'],0)+r['amount'],2)
money=dict(total=round(sum(basis.values()),2),basis=basis,estimated_rows=sum(r['basis']=='预算' for r in rows),dated='2026-11-23',currency='CNY',shipping_included=False)
write(D/'procurement.json',rows);write(D/'首车造价.json',money)
print(money)

