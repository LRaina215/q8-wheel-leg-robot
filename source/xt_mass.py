"""Install R3 mass inputs and compile the fitted-quantity mass ledger."""
from common import *
import csv,re
D=ROOT/'data'
wheel='https://item.taobao.com/item.htm?id=764659136242&skuId=6021439206463'
bat='https://www.tattuworld.cn/products/tattu-r-line-5-0-2200mah-6s1p-22-2v-150c-fpv-lipo-battery.html'
green='https://daygreen.com/products/24v-to-12v-30a-360w-dc-dc-step-down-converter-voltage-regulator'
# Values with two sources or ambiguous inclusions retain their provenance.
records={
'M01':('厂家标重','达妙 DM-J4310M-2EC，约370 g，含减速器和驱动。','https://github.com/dmBots/DM-J4310M-2EC'),
'M02':('厂家标重','FIT0403 12 V，含减速箱和编码器。','https://wiki.dfrobot.com/fit0403'),
'H03':('同尺寸参照','以 SKF 608-2RSH 12 g 为同尺寸双密封轴承参照；采购为国产 608-2RS。','https://www.tme.eu/Document/83a59906c97cb2ff6c50c795411b45d2/SKF608-2RSH.pdf'),
'Wheel':('商品标重','塔克参数图外径100 mm、宽35 mm、六角对边12 mm、约78 g。配件可以另选，图中未说明78 g是否含铜接头。',wheel),
'XT8_Coupler':('同尺寸参照','同类 Ø8/AF12 公布11.5 g；塔克未给重量，取12 g。参照件紧固件计重范围也未说明。','https://www.open-electronics.org/product/8-mm-shaft-wheel-coupler-12-mm-hex/'),
'XT8_Screw':('装车估算','中心M4紧固螺钉与径向顶丝合留2 g；按实物决定与铜接头是否合称。','https://www.handsontec.com/dataspecs/Hex%20wheel%20coupling.pdf'),
'Jetson_Orin_Nano':('厂家标重','按 NVIDIA Orin Nano 8GB 开发套件参考装车，整套174 g；用户板卡版本及存储组合未独立识别。','https://forums.developer.nvidia.com/t/jetson-orin-nano-hw-faq/249118'),
'SSD':('装车估算','为当前Jetson账中未确认的SSD及随附件留12 g；无SSD则扣12 g。',''),
'MC02':('厂家标重','达妙MC02 V1.1手册第2页；19.5 g。','https://github.com/dmBots/DM-MC02'),
'XT_M60':('厂家标重','芯探 XT-M60 基础版123 g；Pro、Neo有各自独立规格。外接线束单列。','https://www.toffuture.com/products/m60'),
'Astra_Pro_Plus':('装车估算','奥比给 Astra 系列标准形态310 g；厂家未拆分底座、线缆与机头。工程账保留去底座机头150 g，不能认作厂家标重。','https://www.orbbec.com/products/structured-light-camera/astra-series/'),
'Tattu_2200_6S':('厂家标重','国网页同货号358 g、含电池端XT60；国际页346±20 g。不再另计电池端插头。',bat),
'MID360':('厂家标重','Livox MID-360 约265 g，首车只预留。','https://www.livoxtech.com/cn/mid-360/specs'),
'Daygreen_B30':('厂家标重有分歧','B30-24-12A标准款中英文规格500/550 g，布局中值525 g；淘宝30 A所选子项铭牌仍待对应。',green+' | '+green.replace('/products/','/zh-hans/products/')),
'AuxBuck':('装车估算','恩珀15 V/5 A淘宝有对应选项；未查到能对应这个壳体及子项的净重，沿用82 g。','https://detail.tmall.com/item.htm?id=836129375401'),
'ANS_H':('装车估算','ANS-H无引线保险座和40 A MIDI保险片合计留56 g。公开尺寸可匹配，未公开这套净重。','https://www.ampfort.net/product/cn/baoxiansizuo.html'),
'Wago615':('厂家标重','221-615 五位，单只7.1 g。','https://assets.cef.co.uk/downloads/pdg/wago_221-615_datasheet/wago_221-615_datasheet.pdf'),
'AuxDist':('厂家标重','221-415 五位，单只4 g。','https://eurotech.com.au/wp-content/uploads/2023/12/WAGO_221-415en_AU.pdf'),
'ZC7112A':('装车估算','吉门 ZC-7112A 公开尺寸45×14×29.2 mm，12 AWG。盒体及插片暂计24 g/路，保留的线尾归入总线束。','https://www.zeeman.cn/zh/cproduct/holder/2021-06-16/578.html'),
'Driver':('厂家标重','DFRobot DRI0041 每块32 g。','https://wiki.dfrobot.com/dri0041/'),
'TXS0108E':('装车估算','厂家给的是芯片规格，整块含排针转接板暂计4 g。','https://item.taobao.com/item.htm?id=534591846020'),
'FFC24_65':('装车估算','24P、0.5 mm转接板含装车短排线按一组留6 g；商品无该组合净重。',read(D/'FFC24_淘宝入口.json')['url']),
'USBnet':('装车估算','选装RTL8153带壳网卡，所选具体批次净重未知。',''),
'Loom':('装车估算','未裁线。含上车的主线、CAN、编码器线、转接头、USB和网线及保险尾线；电池自带线归电池。合计留153 g。',''),
'Hardware':('装车估算','其余设备安装螺钉、盖板螺钉和嵌件、绑带、胶垫、扎带等合留67 g。四角已列的螺栓、隔套及轴承不再计入。',''),
'MidHarness':('装车估算','选装原厂分线缆与增量紧固件，装车留84 g，未见裁线净重。','')}
screw_table='https://www.fullerkr.com/collections/din-912-weight-chart'
records.update(YourCee20=('同类板估重','商品外形60×53×30 mm；两块独立调12 V，每块参考80–100 g，取90 g；自带散热片。','data/taobao/优信300W_规格.jpg | https://www.qixinwei-pcba.com/300w-20a-dc-dc-buck-converter-cc-cv-led-driver-module-p6980165.html'),
               Loom=('路长估算','按固定线长度、线规、原装成品线长度情景及端接余量计算，电池和FFC自带线另项。','data/线材用量.json'),
               LegHarness=('路长估算','四角活动束各含2根18AWG和4根26AWG及护套；计入轮腿质心。','整车线束与裁线.csv'),
               Hardware=('装车估算','原有安装附件67 g及本版两套托架固定件、四角软垫与绑扎等增量11 g。',''))
for key in ['S01','S02','S03','S04','S05','S06','B5bolt']:
    note={'S03':'M3×7 在6与8 mm之间插值。','B5bolt':'M5×22 在20与25 mm之间插值，约4.32 g。'}.get(key,'按对应规格千只重折算。')
    records[key]=('同尺寸参照','DIN 912/ISO 4762 标准件质量表。'+note,screw_table)
def apply():
    d=read(D/'layout.json')
    for k,vals in {'B5bolt':(4.32,4,4.8),'Daygreen_B30':(525,500,550),'Wago615':(7.1,7.1,7.1),'AuxDist':(4,4,4),'Astra_Pro_Plus':(150,120,310),'Tattu_2200_6S':(358,326,366)}.items():
        p=d['parts'][k];p.update(zip(('mass','low','high'),[x/1000 for x in vals]))
    for k,p in d['parts'].items():
        if k in records:p['source']=records[k][1]
    write(D/'layout.json',d)
def ledger():
    import loads
    d=loads.spec;printed={}
    for plate in read(D/'a1_filament.json'):
        for name,w in plate['object_grams'].items():
            key=Path(name).stem.removeprefix('LH_')
            key=key.split('_')[0] if key.startswith('P') else re.sub(r'\d+$','',key)
            printed.setdefault(key,[]).append(w)
    rows=[]
    def row(k,label,n,unit,where,cat,default):
        grade,note,link=records.get(k,default)
        rows.append(dict(id=k,name=label,config=where,group=cat,qty=n,g=round(unit,4),total=round(n*unit,4),grade=grade,note=note,link=link))
    cad=('尺寸推算','按所列材料密度与CAD净体积估重；螺纹和内部特征简化。','')
    filament=('A1切片','PETG HF，按成品路径长度、1.75 mm料径及1.27 g/cm³计算；排除支撑、裙边及备件。','data/a1_filament.json')
    for optional in [False,True]:
        where='MID增装' if optional else '首车'
        for k,n in Counter(i['id'] for i in d['instances'] if bool(i['optional'])==optional).items():
            p=d['parts'][k];unit=p['mass']*1000;default=cad
            cat='车身五金及装车辅料'
            if k in printed:unit=np.mean(printed[k]);default=filament;cat='A1打印结构'
            elif p['kind']=='PETG':default=('尺寸推算','选装横架按CAD净体积 × 1.04 g/cm³估重；当前首车未打印。','');cat='A1打印结构'
            elif k in ['YourCee20','AuxBuck','Tattu_2200_6S','Wago615','AuxDist','ANS_H','ZC7112A']:cat='电池与供配电'
            elif k in ['USBnet','MC02','Jetson_Orin_Nano','XT_M60','Astra_Pro_Plus','MID360','Driver','TXS0108E','FFC24_65']:cat='感知、计算与控制'
            if k=='Jetson_Orin_Nano':
                row('SSD','SSD及随附件留量',n,12,where,cat,cad);unit-=12
            row(k,'Orin Nano 8GB 开发套件' if k=='Jetson_Orin_Nano' else p['name'],n,unit,where,cat,default)
    for k,n in Counter(t['id'] for t in leg.INST).items():
        if k=='XT100_Rim':continue
        n*=4;t=next(t for t in leg.INST if t['id']==k)
        cat='轮端及轮腿五金';default=cad;label=leg.PARTS[k]['label'];unit=loads.engine.mass(t)*1000
        if k=='XT100_Tyre':k='Wheel';label='塔克100 mm外胎、海绵和ABS轮辋';unit=78
        elif k in ['M01','M02']:cat='八台电机'
        elif k in printed:unit=np.mean(printed[k]);cat='A1打印结构';default=filament
        row(k,label,n,unit,'首车',cat,default)
    a=read(D/'analysis.json')
    base=sum(r['total'] for r in rows if r['config']=='首车')
    assert abs(base-a['slice']['mass']*1000)<.02,(base,a['slice']['mass'])
    assert abs(sum(r['total'] for r in rows)-a['slice_mid']['mass']*1000)<.02
    write(D/'质量审计.json',rows)
    with (ROOT/'逐项质量审计.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow('部件编号 装车项目 配置 归类 装车数量 单件估重g 合计g 证据类型 依据与计量边界 来源'.split())
        w.writerows(r.values() for r in rows)
if __name__=='__main__':
    if '--ledger' in sys.argv:ledger()
    else:apply()

