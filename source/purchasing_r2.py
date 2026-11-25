"""One first-car shopping list. Price evidence is independent of model selection."""
import csv
import json
from pathlib import Path
from decimal import Decimal
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
def item(number):
    if number.startswith('https:'): return number
    return 'https://'+('detail.tmall.com' if number.startswith('m:') else 'item.taobao.com')+'/item.htm?id='+number.removeprefix('m:')

def assemble(old):
    result=[]
    market={}
    for f in (DATA/'taobao').glob('*.json'):
        for card in json.loads(f.read_text(encoding='utf-8-sig')).get('cards',[]):
            if isinstance(card,dict): market[card['url'].split('&skuId=')[0]]=card['title']
    def add(i, choice, qty, count, price, basis='预算', url=None, note=None, name=None, status=None, group=None):
        ref=old[i].copy()
        link=item(url) if url else ref['url']
        is_old=link.split('&skuId=')[0]==ref['url'].split('&skuId=')[0]
        title=market.get(link.split('&skuId=')[0],ref['title'] if is_old else '')
        ref.update(group=group or ref['group'],name=name or ref['name'],choice=choice,qty=qty,url=link,
                   title=title,status=status or (ref['status'] if is_old else '设计规格已定，商品规格仍需逐项核对'),
                   note=note if note is not None else ref['note'],packs=count,unit=price,
                   amount=float(Decimal(str(price))*Decimal(str(count))),basis=basis)
        result.append(ref)
    add(0,'达妙 DM-J4310M-2EC 24 V 后出线，含驱动','4台',4,629,'同型号核价','1053672308488&skuId=6114323144260',status='项目留存 24 V 选项，¥629/台')
    for i,n,p in [(1,4,119),(2,1,199),(3,2,99)]:
        add(i,old[i]['choice'],str(n)+'件',n,p,'型号商品卡',note='淘宝对应型号商品卡价。')
    battery=DATA/'用户确认电池价格.json'
    amount=json.loads(battery.read_text(encoding='utf-8-sig'))['price'] if battery.exists() else 360
    add(4,old[4]['choice'],'1块',1,amount,'用户核价' if battery.exists() else '预算',
        note='选项已见；商品卡 11.1 V 的 ¥235.26 未计入。'+('价格由用户从选项页确认。' if battery.exists() else '¥360 为整块采购留额。'))
    add(5,'Daygreen 德格林，标准 30 A / 360 W，24 V 转 12 V；设计对照 B30-24-12A','1只',1,78,'用户核价','589143283343',
        '用户回报所选 30 A 为 ¥78。厂家标准款 18–35 V，100×80×39 mm；中英文净重分别 500/550 g。该淘宝页的整页型号为 40 A 款，30 A 子项铭牌后缀未见。','轮驱 12 V 降压','品牌店 30 A 选项已见，价格用户核实')
    add(6,old[6]['choice'],'1只',1,19,'同型号核价',note='同店同选项历史优惠前 ¥19、优惠后 ¥9.13；首车采用优惠前价格。')
    add(7,'TXS0108E 八路双电源电平转换成品模块，整板已焊芯片','1块',1,5,'预算','534591846020',
        '旧采购记录给出这件成品淘宝链接。低压 A 侧 3.3 V，高压 B 侧 5 V，OE 拉到 3.3 V。整板外廓留位，首车无需订制 PCB。','编码器电平转换板','已确定成品，当前价格、库存待核')
    ffc=json.loads((DATA/'FFC24_淘宝入口.json').read_text(encoding='utf-8-sig'))
    add(8,ffc['name'],'1块',1,6,'预算',ffc['url'],'选择焊好插座、24P、0.5 mm 间距的转 2.54 mm 板；排线另列。','MC02 摄像头口 FFC 转接板','已找到对应淘宝商品入口，24P 所选价待核')
    cable=json.loads((DATA/'FFC软排线_淘宝入口.json').read_text(encoding='utf-8-sig'))
    add(8,cable['name'],'1条',1,2,'预算',cable['url'],
        '摄像头座 HC-FPC-05-09-24RLTAG 支持上下接触。按转接板与板端实际脚号逐线通断确认，再供电。','FFC 排线','已找到同规格淘宝商品入口，成交价待核')
    add(9,'ANS-H 小号 MIDI 带盖螺栓保险座，选盒子，不带线','1座',1,4.30,'同型号核价','590460155787&skuId=4199117393513','项目已核选项；53×30.5×25.8 mm，M5 螺柱。','主保险座','同选项历史核价')
    add(9,'Littelfuse 0498 系列 40 A / 32 V MIDI 螺栓片','1片',1,9,note='该店已见 40 A 片，额定档作为首件选型。验证线规、脉冲及熔断曲线。',name='主保险片')
    add(10,'吉门 ZC-7112A，UL1015 12 AWG 引线','2座',2,9.50,'同型号核价','815254026265','轮驱和电子各用一个单路座；45×14×29.2 mm。','支路保险座','已核型号历史单价')
    add(10,'吉门 ATN 7.5 A 棕色 58 V DC','1片',1,.40,'同型号核价','5846954866&skuId=35391479071','电子支路满额 75 W，在 18 V、效率 90% 假设下输入 4.63 A。','电子支路保险片','选中规格历史价')
    add(10,'吉门 ATN 25 A 白色 58 V DC','1片',1,1,'预算','5846954866','轮驱输入端；360 W、18 V、效率 90% 假设下为 22.2 A。短线 12 AWG、同座兼容，热态和持续电流须验证。','轮驱支路保险片','厂家确有 25 A，淘宝该档价待核')
    add(11,'WAGO 221-615 单只','2只',2,12,'同型号核价','m:593551337906&skuId=6032517176430','项目 11 月 19 日同 SKU ¥12/只。',status='已留存五位 SKU')
    add(12,'WAGO 221-415 单只','2只',2,3.45,'同型号核价','10740601478788','项目留存同规格单只价；运费另计。',status='已留存五位选项')
    add(13,'首车未配置独立吸能模块','0',0,0,'不采购',note='轮驱使用 DRI0041 本地制动；髋关节直连 6S。近满电、电池断路及落地条件见说明。',status='首车数量已定')
    for i,n,u,p in [(14,4,'只',6),(15,1,'包（10根）',12),(16,1,'包（20只）',22),(17,4,'只',27.8)]:
        add(i,old[i]['choice'],str(n)+u,n,p,('活动回执' if i==17 else '型号商品卡' if i==14 else '预算'))
    add(18,'DIN 916 / GB/T 80，45H，M3×10 凹端内六角紧定','装8，备10只',1,4,note='须选凹端；原商品名同时包含平端词，按实选核对。')
    add(19,old[19]['choice'],'1包（10只）',1,8,note='四角各用一只；铝合金，质量账按 Ø8.2×12×8 算。')
    # A two-thickness purchase supplies every shim stack. No charge twice for a reused pack.
    add(20,'精密钢调整片，内径 8.1、外径 12、厚 0.5 mm','需4，备10片',1,8,'预算','817613298867','H06 每角 1.0+0.5。所链接商品有 0.5/1 mm，8.1×12 的尺寸组合未见已选截图。','H06 调整垫片 0.5 mm')
    add(21,'精密钢调整片，内径 8.1、外径 12、厚 1.0 mm','需44，备50片',1,25,'预算','817613298867','H06 用4片、H07 两片一组用16片、H12 用24片，共44片。','H06/H07/H12 共用 1.0 mm 调整片')
    for i,n,unit,pr in [(23,4,'包（5根）',6),(24,12,'只',3),(25,3,'包（5只）',6)]:
        add(i,old[i]['choice'],str(n)+unit,n,pr)
    for i,thread in [(26,'M6'),(27,'M3')]:
        add(i,'坤也 DIN 934 A2-70 '+thread+' 粗牙','装12，备20只',1,4,'预算','m:1044096690721',note='DIN 934 普通六角规格。')
    add(28,old[28]['choice'],'1包（10只）',1,12,note='商品选项确认内径95、线径5；供货批次硬度 70A 尚无证据。')
    for i,qty in [(29,48),(30,24),(31,24),(32,16),(33,16),(34,12),(38,6)]:
        choice=old[i]['choice'] if i!=38 else 'DIN 912 / 12.9 级 M4×12，全牙'
        add(i,choice,f'装{qty}，按对应长度买足一批',1,10 if i==31 else 6,note='计划批次金额，独立长度分别计价；包装和该长度成交价待核。')
    for i,ch,q,pr in [(35,old[35]['choice'],'1包（50颗）',12),(36,'GB/T 97.1，304，M5 / 5.3×10×1','装32，备50片',5),(37,'DIN 985 A2，M5 粗牙，AF8','装16，备20只',5),(39,'M4×6×6（螺纹×外径×长）短款直纹热熔黄铜螺母','装6，备10只',6)]:
        add(i,ch,q,1,pr,note='按目标规格备料；嵌件按实际滚花外径修整先导孔。' if i==39 else '按对应规格备料。')
    for size,q in [('M3 通孔 ID3.2×OD6×L5','Jetson'),('M2 通孔 ID2.2×OD5×L8','MC02'),('M3 双内牙 L36','XT-M60')]:
        add(40,size+'，铝合金','装4，备一批',1,6,name=q+' 隔柱',note='通孔柱配贯穿螺钉，双内牙柱配两端螺钉。链接仅核到柱类，具体长度及通孔形式待核。')
    for spec,q in [('M3×14',4),('M2×16',4),('M3×10',8),('M3 DIN985 锁母',8),('M2 DIN934 螺母',4)]:
        add(41,spec+'，钢制粗牙','装'+str(q)+'，备一批',1,4,name='设备板紧固件 '+spec,
            url='m:1044096690721' if 'DIN934' in spec else old[37]['url'] if '985' in spec else None,note='另有雷达柱 M3×8 八颗、Jetson M3 普通螺母四只，从同规格已购余量取用。')
    add(42,'Bambu Lab PETG HF 1.75 mm，1 kg，灰色；需有可复用料盘或选带盘','2卷',2,65,'预算',note='计划买两整卷；单车含支撑约消耗 1.68 kg。商品卡 ¥51 未核灰色带盘价格。')
    add(43,'达妙原厂 4310M 用 XT30(2+2) 动力/CAN 成品配线，车身侧出散线；另配 MC02 GH1.25 CAN','4路+1包',1,48,note='按4路尾缆及控制端插线整批留额；商品卡 ¥1 对应小配件。')
    add(44,'RISYM 120 Ω CAN 金属膜终端电阻，100只','1包',1,2.14,'型号商品卡','m:692848600520','CAN 一条总线仅两端各120 Ω，已有终端抵扣。',status='标题明确 120 Ω、100只')
    add(45,'AMASS XT60U-M 黄色，焊线式车端公头带护套','1只',1,4,note='配现有电池 XT60U-F；充电线独立。')
    for awg,length,pr in [(12,1,16),(16,2,14),(18,2,10),(22,2,7)]:
        add(46,f'镀锡铜特软硅胶线 {awg} AWG，红黑各 {length} m','1批',1,pr,url='m:1060126279458' if awg<=18 else None,name=f'{awg} AWG 硅胶线',
            note='12 AWG 用于主干、两块驱动板前的共用 12 V 线；16 AWG 髋支路，18 AWG 辅助，22 AWG 信号。')
    add(47,'M5 环端 RV5.5-5 与 RV2-5 各一批','各1批',1,12,url='855145289066',note='主保险使用 M5 螺柱。主正负支线在绝缘压接接续点分出，每个万可夹口只压一根线。')
    add(48,'汇尔速 DC5525 公头单头线、1.5 mm²、中心正','1条',1,10,note='Orin Nano P3768 供电。')
    add(49,'CAT6 UTP RJ45 成品跳线 0.25 m；沿用 XT-M60 专用尾线及 Astra 原装 USB 线','1条',1,8,note='专用线按已有设备随附件计。')
    add(50,'Astra 使用原装线直连 Jetson','0',0,0,'不采购',note='首车无独立 USB 延长。')
    add(51,'FPV 反扣电池绑带 15×200 mm','2条',2,5,note='底板绑带孔长18 mm；电池截面 34×50 mm，200 mm 留约32 mm 搭接，实配计扣具和底板厚度。')
    add(52,'RJXHOBBY 电池防滑硅胶垫 1 mm，裁至底面','1片',1,3,url='944433444831',note='现货胶垫。')
    add(53,'山泽 PA66 黑色 2.5×100 mm，100根','1包',1,4.12,'同型号核价','997764425934&skuId=6145247619816','历史 SKU 优惠前 ¥4.12。','扎带','已核同规格')
    add(53,'双壁带胶热缩管，收缩前 Ø4 / Ø8 mm 各0.5 m','1批',1,8,url='636799099285',name='热缩管',note='两种规格计划批次。')
    add(53,'开口纺织护套，内径8 mm，1 m','1段',1,6,url='695730545355',name='护线套',note='运动线束接触处用。')
    add(54,'Loctite 243 中强度蓝色，10 mL','1瓶',1,35,note='仅用于适用金属螺纹。')
    for i,ch in [(55,'格氏 iMars D300 Plus，6S 平衡充电器'),(56,'达妙 USB2CAN 调试器，配 GH1.25 通讯线'),(57,'MGN12H 单滑块、300 mm 导轨，配重按台架制作'),(58,'5 kg / 1 g 平台秤，以等高垫块轮换四角'),(59,'用户已有，装车计重'),(60,'Livox MID-360 原版'),(61,'原版 MID-360 M12 一分三原厂线'),(62,'品胜 USB-A 3.0 RTL8153 千兆有线网卡'),(63,'M4×100 铝合金双通柱×4，M4×10×8、M3×8×4'),(64,'打印备用轮毂的 M3 嵌件、M4 紧定及螺母')]:
        add(i,ch,'首车新增采购0',0,0,'已有或单列',note='此栏不进入首车新增采购。台架工具按自有或另购，MID360 仅预留。')
    return result

def publish(rows):
    fields=['group','name','choice','qty','packs','unit','amount','basis','status','note','url']
    columns=['类别','物品','应选型号或规格','装车或采购量','采购计价单位数','每计价单位元','行金额元','价格依据','货源核查','说明','淘宝商品或官方活动链接']
    with (ROOT/'整车淘宝采购清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(columns);w.writerows([[r[k] for k in fields] for r in rows])
    by={}
    for r in rows:
        by[r['basis']]=round(by.get(r['basis'],0)+r['amount'],2)
    money=dict(total=round(sum(by.values()),2),basis=by,estimated_rows=sum(r['basis']=='预算' for r in rows),
               dated='2026-11-23',currency='CNY',shipping_included=False)
    (DATA/'首车造价.json').write_text(json.dumps(money,ensure_ascii=False,indent=2),encoding='utf8')
    report=ROOT/'整车装配与核算.md'
    paragraphs=report.read_text(encoding='utf8').splitlines()
    marker=paragraphs.index('## 买一台需要多少钱')+2
    assert paragraphs[marker]=='__MONEY__' or paragraphs[marker].startswith('**首车新增备料预算')
    details='，'.join(f'{kind} ¥{value:,.2f}' for kind,value in by.items() if value)
    paragraphs[marker]=f"**首车新增备料预算 ¥{money['total']:,.2f}（未含运费）。** {details}。其中 {money['estimated_rows']} 行采用预算单价，尚无整单实时报价。"
    report.write_text('\n'.join(paragraphs)+'\n',encoding='utf8')
    return money
