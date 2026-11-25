from common import *
import csv
D=ROOT/'data';loom=read(D/'整车线束.json');rs=loom['routes'];p=read(D/'layout.json');previous=ROOT.parent/'Q8_整车_R3'/'data'
# grams per installed metre: engineering assumptions include insulation. Cross-section and conductor
# count determine purchasing, while finished cables also include a provision for connectors.
specs={'12AWG':(39,{'12':1}),'16AWG':(17,{'16':1}),'18AWG':(11,{'18':1}),
       '动力2':(22,{'18':2}),'活动6':(38.6,{'18':2,'26':4}), 'CAN2':(4.8,{'26':2}),
       '信号1':(2.4,{'26':1}),'信号2':(4.8,{'26':2}),'信号4':(9.6,{'26':4}),'信号8':(19.2,{'26':8}),
       '成品':(23,{}),'网线':(25,{}),'USB数据':(20,{}),'随电池':(0,{}),'FFC':(0,{})}
looms={'fixed':[],'moving':[],'opt':[]};use=Counter()
def fit(r):
    k=r['stock'];mm=r['cut'];i=r['id'];note=''
    if i=='W28':mm=250;note='采购 250 mm CAT6；余长随 XT 分线缆绑在设备层'
    if i=='W30':mm=200;note='采购 200 mm USB-A 至 USB-C 数据线'
    if i=='W35':mm=200;note='整条 200 mm FFC；质量已计 FFC 转接组件，按原长装'
    if i=='W29':mm=max(mm,1000);note='原装 USB 整线长度待量，本账暂按 1 m；多余部分在上层做可拆服务圈'
    if i=='W27':mm=max(mm,150);note='原厂 XT 分线干线按 150 mm 留量，实物决定余长'
    if k=='随电池':note='电池自带，长度待量，质量归电池'
    if r['optional']:note='选装原厂缆；图为到端路线，其余长度收束，增装质量按原装缆预留'
    if k=='活动6':note='与同角固定段可连续裁线，不在绑点接插件；外层 8 mm 软护套'
    return mm,note
for r in rs:
    k=r['stock'];rate,cores=specs[k];mm,note=fit(r)
    extra=({'W29':8,'W30':6,'W27':5,'W28':8,'W19':3,'W20':3}.get(r['id'],0))
    grams=rate*mm/1000+extra
    r.update(fitted=mm,harness_g=round(grams,2),wire_note=note,awg=cores)
    typ='opt' if r['optional'] else 'moving' if k=='活动6' else 'fixed'
    pts=np.array(r['points']);seg=np.linalg.norm(np.diff(pts,axis=0),axis=1)
    center=np.average((pts[:-1]+pts[1:])/2,weights=seg,axis=0)
    looms[typ].append((grams,center))
    if not r['optional']:
        for gauge,n in cores.items():use[gauge]+=mm*n/1000
def distpart(key,name,grams,c):
    m=grams/1000
    if key not in p['parts']:
        p['parts'][key]=dict(kind='分布质量',color='#878277',name=name)
    p['parts'][key].update(mass=m,low=m*.76,high=m*1.32,com=[0,0,0],source='设计布线路长、假设线密度及接头留量，详见裁线表')
    for t in p['instances']:
        if t['id']==key:t['pos']=list(c)
def masscenter(items):
    m=sum(g for g,_ in items);return m,np.average([x for _,x in items],weights=[g for g,_ in items],axis=0)
# Include terminals, boots, distribution splices & terminations not contained in the finished cable line.
looms['fixed'].append((24,np.array([0,2,2])))
g,c=masscenter(looms['fixed']);distpart('Loom','固定线束与插头',g,c)
motion=next(r for r in rs if r['stock']=='活动6');gm=motion['harness_g']
p['instances']=[t for t in p['instances'] if t['id']!='LegHarness']
distpart('LegHarness','轮腿六芯活动束与护套',gm,[0,0,0])
for r in rs:
    if r['stock']=='活动6':
        p['instances'].append(dict(id='LegHarness',pos=np.mean(r['points'],axis=0).tolist(),rz=0,optional=False,name=r['a'][:2]+'_loom'))
p['parts']['Hardware'].update(mass=.078,low=.054,high=.114,source='R3 基数67 g，托架紧固、扎带和四角切片硅胶软垫合计增量估11 g')
write(D/'layout.json',p);write(D/'整车线束.json',loom)
with (ROOT/'整车线束与裁线.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow('编号 配置 类型 起点 终点 芯线 长度mm 端接留量后mm 整线装车或估算mm 线材 说明'.split())
    for r in rs:w.writerow([r['id'],'MID增装' if r['optional'] else '首车',r['group'],loom['nodes'][r['a']]['label'],loom['nodes'][r['b']]['label'],r['cores'],r['fixed_mm'],r['cut'],r['fitted'],r['stock'],r['wire_note'] or r['detail']])
stats=dict(fixed_g=round(g,1),fixed_center=c.tolist(),moving_per_leg_g=gm,wire_metres=dict(use),connector_allowance_g=24,
           g_per_m={k:v[0] for k,v in specs.items()},optional_harness_allowance_g=84)
write(D/'线材用量.json',stats)
rows=read(previous/'procurement.json')
for r in rows:
    name=r['name']
    if name=='轮驱 12 V 降压':
        r.update(choice='优信电子 300W 20A 绿端子，输出调 12.0V',name='优信双路轮驱独立降压板',qty='2块，无专用风扇',packs=2,unit=16,amount=32,basis='用户核价',status='用户核实所选规格包邮',title='优信绿端子 300W 可调同步降压',note='每只服务一块 DRI0041，两路正输出独立。',url='https://item.taobao.com/item.htm?id=1015010012394&skuId=6182952350834')
    if name.startswith(('12 AWG','16 AWG','18 AWG','22 AWG')):
        gauge=name.split()[0]
        if gauge=='22':
            r.update(name='26 AWG 信号与 CAN 线材',choice='UL3239 26 AWG 镀锡软线，按色备料',unit=3.3,basis='预算',url='https://item.taobao.com/item.htm?id=712823328644',status='淘宝商品卡标题可见 26 AWG；1 m 单价按预算')
            r.update(qty='1 m/份，多色合计',packs=math.ceil(use['26']*1.12))
        else:
            per=2 if gauge=='12' else 4
            r.update(packs=max(1,math.ceil(use[gauge]*1.12/per)),qty=f'每批红黑各{per//2} m，按裁线量备整批')
        r['amount']=round(r['packs']*r['unit'],2);r['note']=f'按裁线表需约 {use["26" if gauge=="22" else gauge]:.2f} m 导体，各色裁线长度按端子分配。'
    if name=='USB 数据延长/转接线':r.update(name='Jetson 到 MC02 USB 数据线',group='线束',choice='深圳优科 USB-A 公至 Type-C 公 · 20 cm 数据款',qty='1条',packs=1,unit=6,amount=6,basis='预算',status='淘宝卡可检索 20/30/50 cm；20 cm 子项未核价',note='保留数据对，连接 USB 全速设备。',url='https://item.taobao.com/item.htm?id=650062440932')
    if name=='护线套':
        metres=sum(r['fitted'] for r in rs if r['stock']=='活动6')/1000
        r.update(packs=math.ceil(metres),amount=math.ceil(metres)*r['unit'],qty=f'装约 {metres:.2f} m，1 m/段')
    if name=='设备板紧固件 M3×14' or name=='设备板紧固件 M3 DIN985 锁母':r['note']+=' 双板托架另用两件，取同包余量。'
    if name=='扎带':r['note']='双板各两道压在散热片边缘，长环用同包扎带接长，扣头在侧面；腿根、从动臂和轮机尾部独立止拉。'
    if '防滑硅胶' in name:
        r.update(packs=2,amount=2*r['unit'],qty='电池1片，四角垫块另备1片',note='1 mm 硅胶片裁约 10×10 mm 小片，腿根每角叠4层，从动臂按束线位置叠垫；扎带包住垫块与护套。')
    if name.startswith('PETG '):r['note']='双板托架另用第八种打印盘；两整卷备料。'
rows.append(dict(group='线束',name='信号排针配套母端子与单排胶壳',choice='TELESKY 2.54 mm 杜邦母端子及单排壳',
    qty='母端至少 80 只，1P/2P/4P/8P 胶壳各一包',packs=1,unit=12,amount=12,basis='预算',
    status='天猫有同系列商品；组合成交价待核',note='仅用于匹配的2.54 mm信号排针。MC02细距接口使用原配线及已列出的GH成品线。',
    url='https://detail.tmall.com/item.htm?id=21105588979',title='TELESKY 2.54 mm 杜邦母头胶壳与端子',
    search='https://s.taobao.com/search?q=TELESKY%202.54mm%20杜邦母端子'))
fields=['group','name','choice','qty','packs','unit','amount','basis','status','note','url']
with (ROOT/'整车淘宝采购清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow('类别 物品 应选规格 装车或采购量 计价单位数 每单位元 行金额元 价格依据 货源核查 说明 淘宝链接'.split());w.writerows([[r[k] for k in fields] for r in rows])
basis=Counter()
for r in rows:basis[r['basis']]+=r['amount']
money=dict(total=round(sum(basis.values()),2),basis={k:round(v,2) for k,v in basis.items()},estimated_rows=sum(r['basis']=='预算' for r in rows),dated='2026-11-23',currency='CNY',shipping_included=False)
write(D/'procurement.json',rows);write(D/'首车造价.json',money);print(stats,money['total'])
