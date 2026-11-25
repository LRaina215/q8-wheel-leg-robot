from common import ROOT,read,write
import csv,re,urllib.parse
from pathlib import Path
dest=ROOT/'data';files=dest/'taobao'
rows=[]
def row(group,name,qty,keys,patterns,note='',status='检索到同类商品；店内子规格未核'):
    cards=[];quer=[]
    for k in keys.split('/'):
        fn=files/(k+'.json')
        if not fn.exists():continue
        j=__import__('json').loads(fn.read_text(encoding='utf-8-sig'));quer.append(j['query'])
        cards.extend((c,j['query'],j.get('observed','')) for c in j.get('cards',[]) if isinstance(c,dict))
    hit=None
    for pat in patterns.split(';;'):
        if pat:hit=next((x for x in cards if re.search(pat,x[0]['title'],re.I)),None)
        if hit:break
    q=hit[1] if hit else (quer[0] if quer else name)
    url='https://s.taobao.com/search?q='+urllib.parse.quote(q)
    rows.append(dict(group=group,name=name,qty=qty,status=status if hit else '已查淘宝；未核准匹配商品',note=note,url=hit[0]['url'] if hit else url,title=hit[0]['title'] if hit else '',search=url,observed=hit[2] if hit else ''))
def info(*args):
    group,name,qty,status,note,url=args
    rows.append(dict(group=group,name=name,qty=qty,status=status,note=note,url=url,title='',search='',observed=''))
r=row
r('执行器','DM-J4310M-2EC 后出线 24 V','4','hip','4310M.*24V.*达妙智能','商品卡 ¥629；选双编码器 M 型，确认插头方向。','型号/品牌店已见')
r('执行器','DFRobot FIT0403 12 V / 122 rpm 6 mm D 轴','4','wheel','FIT0403.*122rpm','商品卡 ¥119。随件编码器线算入线束。','型号已见')
r('控制','达妙 DM-MC02 H723','1','MC02','MC02.*H723.*达妙智能|H723.*MC02.*达妙智能','商品卡 ¥199。','型号/品牌店已见')
r('控制','DFRobot DRI0041 双路有刷驱动 7 A/路','2','DRV_r','7A.*双路.*DFRobot官方','对应原厂规格和外形；品牌店商品卡 ¥99。','品牌店规格已见')
r('能源','格氏 Tattu R-Line V5 6S 2200 mAh 150C XT60','1','battery/BAT2_r','5.0.*2200mAh.*150C.*6S','多规格商品卡。核选 6S/2200/V5、插头与外廓，标价可能为小容量。')
r('能源','18–35 V 输入、12 V / 30 A 轮驱降压','1','bw/BUCK','24V转12V30A.*18-35V;;24V转12V.*30A','散热片与引线须装进 88×98×38 mm，实核连续 30 A。')
r('能源','15 V / 5 A 电子支路降压','1','AUX/aux15','18-40V变15V.*恩珀;;24V转15V.*uenPO','按 25×58×20 mm 预留，确认 5 A 连续、散热和接口。')
r('控制','74LVC2G17 双通道缓冲','4','level','74LVC2G17','MC02 手册标有可控 5 V / 2 A 对外输出；使能后供四轮编码器，按实物核总电流。缓冲芯片按 3.3 V 供电并共地。','芯片型号已见')
r('控制','编码器转接 PCB/焊接载板与元件','1 套','board','双面.*线路板|线路板.*双面|PCB.*双面','单独电气实现，电压与连接器确认后制板。')
r('配电','MIDI/ANS 带盖主保险座及 32 V 保险片','1 座＋1 片','FUSE','MIDI.*40A.*座','40 A 仅作台架起点；需按导线、主连接器和实测脉冲选配。')
r('配电','支路保险座、保险片','1 组','f2/FUSE','保险.*7.5A|保险片.*15A','轮驱和电子分路，额定电流按对应线径与变换器输入确定。')
r('配电','WAGO 221-615 五位大电流分线端','2','dist_r','221-612/613/615','正负各一，供髋电机；从主保险后端另分出降压支路。')
r('配电','WAGO 221-415 五位辅助分线端','2','term_r','221-412/413/415','正负各一。')
r('配电','刹车回馈吸能模块','1 个预留','wbr','电机刹车放电模块|Brake Resistor Module','已见同类；触发电压、脉冲能量、反向电流路径和 37×23×16 mm 匹配未确认。','同类已见；型号未定')
r('轮腿','H01 夹紧式 6→8 联轴器，外径≤20，长25 mm','4','H01_r','D20L25.*6.*8','需同一只两端异径，注意锁紧头外廓。')
r('轮腿','H02 Ø8 h6 成品钢轴，长60 mm','4','H02_r','轴承钢.*60|精密光轴.*8','优先标准磨光轴；核轴径、端面和轮毂紧定位置。')
r('轮腿','H03 608-2RS 8×22×7 轴承','8','H03_r','608-2RS','内外圈分开支撑。','型号已见')
info('轮腿','H04 6061 方轮毂 W08','4','铨洲活动试价 ¥111.20','淘宝未找到同接口标准件。模型 S7010205；单件 ¥27.80，未下单。','https://gy2025.com/#/home/proofing')
r('轮腿','轮毂凹端紧定 M3×10','8','grub','12.9级凹端.*M3','每只两颗，端部作用于钢轴；先检查长度及顶紧后外露。')
r('轮腿','H05 内圈隔套 ID8.05–8.2 / OD12 / L8.00','4','sleeve2/sleeve/H05_r','8[×x*]12[×x*]8;;铝合金空心轴套','现货尺寸未核准；可用同内外径现货精密垫环配足 8 mm，实测两轴承座肩。无需非标加工。','仅确认隔套/垫环品类')
for code,h,qty in [('H06',1.5,4),('H07',2,8),('H12',1,24)]:
    r('轮腿',f'{code} ID8.1 / OD12 / 厚{h} mm 调整环',str(qty),'H06_r','轴承垫圈.*内径8|调整.*内8.*外12','可由多片组合，须顶住内圈；H07 含新轮毂每轴多加的一片。')
r('轮腿','H08 M4×30 双内牙铝柱 AF7','16','H08_r','双通.*铝.*M4','内端有效牙≥6、外端≥8 mm。')
r('轮腿','H09 8×10×10 无凸缘塑料滑动轴套','12','bush','JSM-0810.*10','选 JSM-0810-10，打印座按实物试配。')
r('轮腿','H10 Ø8×12 肩螺钉 / M6','12','H10_r','12.9级.*塞打.*M6|塞打.*Φ8','核光杆长12、牙长11、头径≤13 mm。')
for sz,qty in [(6,12),(3,12)]:
    r('轮腿',f'M{sz} 六角螺母，标准高度',str(qty),'H11_r','六角螺母.*M2M3M4M5','分别配合肩轴及压盖。')
r('轮腿','H13 丁腈 NBR 70A，内径95 × 线径5 mm','8','H13_r','线径5.*95|95.*线径5','各轮双 O 圈，核内径、截面及硬度。')
for c,sz,l,qty in [('S01',3,8,48),('S02',3,16,24),('S03',3,7,24),('S04',4,10,16),('S05',4,30,16),('S06',3,30,12)]:
    r('轮腿',f'{c} M{sz}×{l} 圆柱头内六角，≥8.8级',str(qty),'S03_r' if c=='S03' else 'steel/S_r','12.9级.*[x*]7' if c=='S03' else '12.9级.*杯头|12.9级.*圆柱头','S01 24颗用于髋定子、24颗用于轮辋。轮辋盲孔先量有效牙，浅孔另备 M3×7（24颗）。' if c=='S01' else '选对应长度；轮电机有效旋入≤3.5 mm。' if c=='S03' else '按对应 SKU 采购。')
r('装车','M5×22 圆柱头内六角，钢','16','c5/steel','内六角螺栓.*M5.*X22|12.9级.*杯头','四角每角四套；配 32 片平垫与16只锁母。')
r('装车','M5 平垫，外径10、厚1 mm','32','washer','304不锈钢平垫圈.*M5','每根髋座贯穿螺栓两片。')
r('装车','M5 金属尼龙圈锁母，AF8','16','lock','不锈钢.*锁紧螺母.*M5','配 22 mm 螺栓，核尼龙圈完全咬合。')
r('装车','M4×12 上盖螺钉','6','steel','12.9级.*杯头','六个 Ø4.0 底孔为可调整先导孔，按实选 M4 短铜嵌件扩孔再热熔；勿把 Ø4.0 当成嵌件最终孔径。')
r('装车','M4 热熔铜嵌件，长度≤6 mm','6','nut_r','热熔.*M3M4','支座7 mm高，按实物外径选底孔，保留端面和边距。')
r('装车','隔套/双通柱：Jetson M3×5、MC02 M2×8、雷达 M3×36','各4','post_r/H08_r','M2-10.*双通|M2.*铝.*M3','36 mm 可用 30 mm 双通柱和 6 mm 标准垫柱叠装。')
r('装车','设备安装紧固包 M2 / M3','1 套','steel/m2','12.9级.*杯头','Jetson 4 套 M3×14+螺母，MC02 4 套 M2×16+螺母；雷达柱上下各4颗 M3×8；相机托与双驱动托各4套 M3×10+锁母。按实物板厚复核。')
r('打印','PETG 1.75 mm，A1 / 0.4 mm','2×1 kg 备料','PETG_r','拓竹PETG HF.*1kg','覆盖四条轮腿、底盆、设备板、托座和试配。','材料商品已见')
r('线束','达妙 XT30(2+2) 动力/CAN 线、GH 对插','4 路＋控制线','can_r','达妙科技关节电机配线','核电机版本针脚；CAN 两端各120 Ω，板上已有终端时扣除。')
r('线束','120 Ω CAN 终端','2，板载时扣除','canend/can_r','120.*[欧Ω]|终端电阻','普通120 Ω电阻也可；不在每个电机并端接。')
r('线束','XT60U 电池接头与可拔断电接头','1 组','plug_r','正品Amass.*XT60','按电池插头配对，核实际持续/脉冲电流，主支路负载共用。')
r('线束','主接线硅胶线 14/16 AWG，支路18–22 AWG','各色约1–2 m','line_r','14.*12.*10|16.*18.*20','长度为备料，按电流温升与实车裁线。')
r('线束','环端子、配电压接端头','1 包','lug','冷压.*鼻|冷压.*端子','按保险座螺柱和线截面积选型。')
r('线束','Jetson DC 5.5×2.5 电源线','1','sock_r','DC5.5.*2.5|DC5525','以手中载板插座极性、尺寸核对。')
r('线束','Astra 原配 USB、XT-M60 原配线及短网线','各1，随件已有则扣除','ether_r','网线.*Cat6|六类.*短','购买前看自有设备线尾；上架的短网线不能替代雷达专用线。')
r('线束','USB 数据延长/转接线','按实物0–1','usb_r','USB3.0.*短线|usb3.0.*短','确认相机接头与 USB 口，优先使用原线。')
r('装车','电池魔术绑带','2条','belt_r','电池绑带魔术','绑带沿底板两道槽走线；匹配槽宽和电池周长。')
r('装车','1 mm 电池防滑硅胶片','1','foot','硅胶.*1mm|防滑贴硅胶','垫在电池与底板之间。')
r('装车','线束护套、尼龙扎带、热缩管','1 组','strap','线束套管|线束胶布','相机与雷达用窄扎带；保留接插件应力释放。')
r('装车','金属螺纹用中强度螺纹胶','1 小瓶','screwpaste','243|中强度','仅用于适合的金属紧固副。')
r('台架','6S 平衡充电器、XT60 充电线','1，若已有扣除','balance_r','格氏.*平衡充电器','不计车重。')
r('台架','CAN 调试器','1，若已有扣除','bkup_r','CAN分析仪.*达妙','不计车重。')
r('台架','导轨滑台、可调配重、标尺','1 组，若已有扣除','bench','MGN12|直线导轨','导轨仅用于首腿载荷和位移验证。')
r('台架','四角称重用秤','4 台或等高顺次测','scale','电子秤|厨房秤','手机慢动作可用于轮胎离地观察。')
info('已有','XT-M60、Astra Pro Plus、Jetson','各1','用户已有','装入总装、计质量；采购金额为零。按项目 Orin Nano 8GB 载板与去底座相机建模。','')
r('选装','Livox MID360 原版','将来1；首车0','MID_r','mid360 非mid360s','仅预留；选装载荷中计入265 g。','原版型号已见')
r('选装','原版 MID360 M12 一分三线','将来1','optharness','M12.*[mM]id360无人机','不要选无原版兼容说明的 S 版。')
r('选装','USB3.0 千兆网卡 RTL8153','将来1','optnet','USB3.0.*RTL8153','为同时接两路以太网留位。')
r('选装','M4×100 双通铝柱、M4×10、M3×8','4柱＋8颗＋4颗','post_r','M2-10.*双通','支柱锁上下两端；4 mm 打印架下方 M3 螺钉进入雷达约4 mm，须复核有效牙深。')
r('打印后备','M3 铜嵌件与 M4 顶丝、M4 六角螺母','每只6＋2＋2，首车0','nut_r','热熔.*M3M4','只随打印备用轮毂采购；牙套外形和顶丝长度按备用 STL 试配。')
review=read(dest/'采购选型核对.json')
for b in rows:
    b['choice']=b['name']
    fastener=re.match(r'S0[1-6] (M\d+×\d+) 圆柱头',b['name'])
    if fastener:
        b['choice']='12.9 级合金钢圆柱头内六角 '+fastener[1]+'，全牙'
        b['status']='设计规格已定；该店长度选项未核'
    # Search cards frequently preselect a low-price, differently sized SKU.
    b['url']=b['url'].split('&skuId=')[0]
    for prefix,choice,status,note in review['条目']:
        if b['name'].startswith(prefix):
            b.update(choice=choice,status=status,note=note)
            override=review['固定商品'].get(prefix,{})
            if override:
                b.update(url=override['url'],title=override['title'],observed=review['核对日期'])
                if 'search' in override:b['search']=override['search']
                if 'note' in override:b['note']+=' '+override['note']
            if prefix=='18–35 V 输入':b['name']='轮驱降压 18–32 V 输入、12 V / 30 A 输出'
            break
    if b['group'] in ('装车','台架','线束','打印后备','选装') and b['status'].startswith('检索到同类') and '套' in b['qty']:
        b['status']='组合用料；链接只核到部分品类'
write(dest/'procurement.json',rows)
with (ROOT/'整车淘宝采购清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['类别','规格','整车数量','设计料号或店内目标选项','核查状态','选型说明','商品、检索或活动链接','实际商品标题（价格可能为其他SKU）','淘宝检索链接','观察时间']);w.writerows([b[k] for k in ['group','name','qty','choice','status','note','url','title','search','observed']] for b in rows)
from purchasing_r2 import assemble,publish
rows=assemble(rows)
money=publish(rows)
write(dest/'procurement.json',rows)
print(len(rows),'R2 rows',money)
