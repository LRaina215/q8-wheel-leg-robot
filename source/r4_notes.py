from common import *
D=ROOT/'data'
a=read(D/'analysis.json');b=a['slice'];j=read(D/'20mm质心低跳.json');short=read(D/'四配置20mm动作.json')
wa=read(D/'线材用量.json');qa=read(D/'线束间隙.json');pair=read(D/'线对线复核.json')
cost=read(D/'首车造价.json');native=read(D/'R4原生装配验证.json');m=b['mass'];cf=b['static']['-7']['kg']
ledger=read(D/'质量审计.json');cats=Counter()
for r in ledger:
    if r['config']=='首车':cats[r['group']]+=r['total']
def cases(target,kit):
    d=(short if target==20 else a)[kit];n=d['heaviest']
    return '| '+ ' | '.join([f'{target} mm',('首车' if kit=='slice' else '加装 MID-360'),n,*[f"{d['cases'][case][n]['factor']:.3f} / {d['cases'][case][n]['speed_factor']:.3f}" if d['cases'][case][n]['factor']>=1 else f"{d['cases'][case][n]['factor']:.3f} / 扭矩超限" for case in ['22V2','loss_diagonal']]])+' |'
report=f"""# Q8 R4 整车装配与线束

首车包含八台电机、6S 2200 mAh 电池和自有三件感知、计算设备。双板自然冷却，首车只预留 MID-360。装车估重 **{m:.3f} kg**，超 6 kg **{(m-6)*1000:.0f} g**。整包备料 **¥{cost['total']:.2f}**，其中 ¥{cost['basis']['预算']:.2f} 是预算单价。两块降压板各 ¥16 包邮。其余运费按订单，选装另计。

[交互整车](整车动作与载荷.html) · [SolidWorks 原生总装](SolidWorks/Q8_Full_Vehicle.SLDASM) · [裁线表](整车线束与裁线.csv) · [采购](整车淘宝采购清单.csv) · [逐项质量](逐项质量审计.csv)

## 下舱安装

- 将电池沿车身向后移 8 mm。髋正极排在电池前方，进线面与电池模型之间约 11.35 mm，负极排的进线面朝前。两个支路保险座转 90°。拆装电池时，从车尾取出 XT60 及平衡插头。
- 打印双板共用 PETG 托架。沿车右将两块板前后排开，板底距底盆内面 3 mm，两块板相邻边之间 11 mm。托架用两套 M3×14 螺栓和锁母固定于底盆原孔槽（车身坐标 X=11、109，Y=−30 mm），前侧止翘带穿原通风口。每块板由边挡限位，两道 2.5 mm 扎带穿侧槽，压在散热器边缘，下方用槽沉带，避开线端和调压螺钉。托架的 A1 切片成品质量为 13.27 g。[可打印托架](A1_3MF/04_BuckTray.3mf)
- 后板供左侧两轮，前板供右侧两轮。各板按实物 IN+/IN− 及 OUT+/OUT− 丝印校对，从 6S 保险后取电，各调至 12.0 V，独立接各自 DRI0041。两路共用电池输入，12 V 正输出彼此分开；两板均为非隔离降压。四台髋电机使用 6S。[商品参数](data/taobao/优信300W_规格.jpg) · [原厂驱动接口](https://wiki.dfrobot.com/dri0041)
- 绿端子孔距、插头壳、供应商尾线长短待实物确定。板体 CAD 锁定商品外廓 60×53×30 mm，托架靠边定位，允许替换批次时实测。已有 Jetson 以 Orin Nano 开发套件接口为基准。

## 线束与绑点

HTML 默认展示首车 {qa['base']} 条路线。点击线或搜索线号，红点和蓝点分别标出两端，可隔离一条线。切换到部件目录、选中具体模块或它的前后实例，点击“查看关联走线”可只看这个模块的接线。切到 MID-360 后显示另外 {qa['option']} 条。线材含电池与保险、双板输入输出、四髋供电与 CAN、轮机动力与编码器、主控方向及 PWM、15 V 配电、传感器与上位机的电源和数据。[按芯数及接点裁线](整车线束与裁线.csv)

| 支路 | 装车连接 |
|---|---|
| 6S | 电池 XT60 → 40 A 主保险 → 髋正极排、25 A 轮驱保险、7.5 A 设备保险。负极分点回电池，髋正负排各留四孔给四角。平衡插头绝缘收纳。 |
| 12 V × 2 | 轮驱保险后一分二，分别送两块板输入。后板 → 左 DRI0041，前板 → 右 DRI0041，OUT1/2 接前轮，OUT3/4 接后轮。 |
| 15 V | 恩珀 15 V/5 A → 五孔正负排 → Jetson、MC02、XT-M60，末孔预留 MID-360。自有 Jetson 实物的输入、DC 插头极性及尺寸应与所选载板一致。 |
| 编码器 | 每轮 5V/GND 与 A/B。其中 A/B 经 TXS0108E 的 B1…B8 变换为 3.3 V，通过 FFC1 的 6/4、3/5、7/11、9/13 脚回主控，顺序为左前、右前、左后、右后。按插座 1 脚认向。 |
| 轮驱命令 | 左板 IN1…4 来自 FFC1 的 8/12/18/19，右板为 16/17/20/22。左 ENA/ENB 用 PE13/PA2，右用 PE9/PA0。DRI0041 标注 +5V 的参考输入兼容 3.3 V，接主控 3.3 V。 |
| 数据与 CAN | 每侧 MC02 CAN → 前髋 → 后髋，末端按实际板载电阻配置 120 Ω。Jetson USB 分别接 MC02、Astra；原生网口接 XT；选装网卡独立接 MID。 |

在底盆装入电池和降压托架后敷设粗线，然后接上层控制与传感器。Astra 的 1 m 假设线长在右侧上层盘成四圈，模型中圈径约 56 mm，用现有扎带固定在设备层，避开散热片、Jetson 进气口及雷达出光面。XT 至 Jetson 的 250 mm 网线、MC02 至 Jetson 的 200 mm USB 线和 200 mm FFC 已按所选整线走弯。实际雷达分线缆的模压分叉位置和余长需以手上原线调整。[MC02 资料](https://github.com/dmBots/DM-MC02) · [Jetson 接口](https://developer.nvidia.com/embedded/learn/jetson-orin-nano-devkit-user-guide/hardware_spec.html)

四条活动束沿固定侧耳下排 M5 上方引出，用四层 1 mm 硅胶片将根部护套从 P01 外表面垫开，再经从动臂外侧两处软垫绑点，绕过轮架后到达电机定子。每角护套外径约 8 mm，内含两根 18 AWG 动力线与四根 26 AWG 信号线。模型活动中心线约 {next(r["fixed_mm"] for r in read(D/"整车线束.json")["routes"] if "frames" in r):.0f} mm，裁线约 400 mm/角，端接与留量分配在两端。腿根标号是绑点，固定段与活动段可以使用同一根连续导线。编码器与 PWM 动力同束可能引入干扰，实装时成对整理，按布线路长核对最远一轮的 A/B 沿与计数。TI 特别指出 TXS0108E 对连线负载及电容敏感。[TI 器件手册](https://www.ti.com/lit/ds/symlink/txs0108e.pdf)

## 干涉复核的结果

SolidWorks 六个配置均已重建，首车含 {native['Ride']['resolved']} 个展开实例，选装含 {native['Ride_MID360']['resolved']} 个，均含两块优信和一件托架。整车刚体在 −36° 至 +33° 范围按 1° 检查，未发现目标部件相交。成品轮全外径包络至轮架的最小模型间隙 6.5 mm。[原生总装核对](data/R4原生装配验证.json) · [轮架复核](data/轮架净距.json)

| 项目 | 名义模型最小净距 |
|---|---:|
| 活动束至轮胎 | {min(p['tyre'] for p in qa['poses']):.2f} mm |
| 活动束至所在轮腿的刚件 | {min(p['leg_gap'] for p in qa['poses']):.2f} mm，{min(qa["poses"],key=lambda p:p["leg_gap"])["part"]} |
| 活动束至机身固定件（网格保守值） | {min(p['body_bound'] for p in qa['poses']):.2f} mm |
| 活动束与固定线 | {pair['moving_fixed_min'][0]:.2f} mm |
| 固定线之间 | {pair['fixed_min'][0]:.2f} mm，{pair['fixed_min'][1]} / {pair['fixed_min'][2]} |

固定线对设备及底盆按约 1 mm 采样，连接器自己的 20 mm 扇出区按接线处理。线线复核同样单列端接区；表内净距已扣除模型线径。打印尺寸、插头实体、扎带扣头、柔性线挠曲和落地甩动会消耗模型间隙。实装时四角手动走满行程，特别留意下蹲时 P05 与护套接近处。[固定线复核](data/固定线束复核.json) · [线对线](data/线对线复核.json) · [逐姿态](data/线束间隙.json)

## 重量、预算与动作

| 构成 | 首车 g |
|---|---:|
"""+'\n'.join(f'| {k} | {v:,.1f} |' for k,v in cats.most_common())+f"""

原 R3 账 6.524 kg；两板合计按 180 g 参考，替换原 525 g 降压器，板件减 345 g。新增托架 13.27 g，紧固、软垫与绑扎预留多 11 g。固定线端估 {wa['fixed_g']:.1f} g，加四条活动束各 {wa['moving_per_leg_g']:.2f} g，线束合计约 {wa['fixed_g']+4*wa['moving_per_leg_g']:.0f} g，比旧留量 153 g 多约 {wa['fixed_g']+4*wa['moving_per_leg_g']-153:.0f} g。整车净减约 {(6.52352-m)*1000:.0f} g。两块板和线束均待称重。Astra 去底座机头按 150 g，商品轮 78 g 是否含 8 mm 铜头仍未明。选装后整车估 {a['slice_mid']['mass']:.3f} kg。[质量证据和边界](逐项质量审计.csv)

巡航时左前、右前、左后、右后分别为 {'、'.join(f'{cf[k]:.3f}' for k in ['FL','FR','RL','RR'])} kg，按水平地面、四角等效刚度与预紧一致估算。离地后 20 mm 质心上升对应起跳竖向质心速度约 0.626 m/s。模型对整车计算质心与势能，对各髋按簧上、轮端和连杆的载荷与惯性分别求扭矩；倍率为当时可用输出与需求之比。[逐角模型](data/四配置20mm动作.json)

| 质心上升目标 | 配置 | 最重角 | 22.2 V 扭矩 / 转速倍率 | 20.7 V、偏载 +0.15 kg、高损耗 |
|---|---|---|---:|---:|
""" + '\n'.join(cases(x,y) for y in ['slice','slice_mid'] for x in [20,30])+f"""

满载首车、20 mm 目标，在名义工况左前髋峰值 {j['nominal']['peak']:.2f} N·m，不利工况 {j['adverse']['peak']:.2f} N·m，对应最低扭矩余量 {(j['adverse']['factor']-1)*100:.1f}%。24 / 32 ms 空中停髋对应轮胎净空 {j['clear24_mm']:.1f} / {j['clear32_mm']:.1f} mm。电机数据基于 24 V 曲线，22.2 V 与 20.7 V 为外推。塔克图标四轮负载 5 kg，低于本车估重，且未提供落地冲击额定值；满载跳跃目前仅有电机模型结果。[塔克商品参数](data/塔克100卖家参数图.png) · [达妙电机资料](https://github.com/dmBots/DM-J4310M-2EC)

两轮堵转参照合计约 14 A/板，已接近卖家“长时间 15 A 以内”的上限。原配散热片随板，首车专用风扇数量为 0。能否在实际机舱自然冷却下持续工作取决于负载及环境，按卖家功率管 65 °C 条件判定。优信无输出防反灌，双板未提供吸收回馈能力规格。轮驱急减速要观察左右两条 12 V 轨，四髋减速另观察 6S 母线；单加串联隔离二极管也不会吸收驱动侧能量。首车采购未计泄放模块，满电急刹及低跳制动的电压峰值尚待采集。[商品参数](data/taobao/优信300W_规格.jpg) · [轮机数据](https://wiki.dfrobot.com/fit0403)
"""
(ROOT/'整车装配与核算.md').write_text(report,encoding='utf8')
research=(ROOT.parent/'Q8_整车_R3'/'12V轮驱降压板选型调研.md').read_text(encoding='utf8').split('## R3 机舱空间')[0]
research=research.replace('Q8 R3 首车选型调研','Q8 R4 首车选型依据').replace('双板试装方案采用','首车采用').replace('双板候选','R4 双板')
(ROOT/'12V轮驱降压板选型调研.md').write_text(research+'\n## R4 装车\n\n'+f'首车采购 ¥{cost["total"]:.2f}，含两块降压板 ¥32。托架切片成品 13.27 g。电池、保险和端子排根据完整布线调整。安装方法、估重和动作余量见[整车装配与核算](整车装配与核算.md)。\n',encoding='utf8')
