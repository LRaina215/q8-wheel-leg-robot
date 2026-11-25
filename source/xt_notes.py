from common import *
import re
D=ROOT/'data'
a=read(D/'analysis.json');b=a['slice'];n=b['heaviest'];low=read(D/'20mm质心低跳.json')
f=b['cases']['22V2'][n];bad=b['cases']['loss_diagonal'][n];cost=read(D/'首车造价.json')
rows=read(D/'质量审计.json');cats=Counter();grades=Counter()
for r in rows:
    if r['config']=='首车':cats[r['group']]+=r['total'];grades[r['grade']]+=r['total']
m=b['mass'];printing=read(D/'a1_filament.json');cons=sum(p['all_deposition_grams']*(2 if p['plate'].startswith(('R1','LH')) else 1) for p in printing)/1000
battery='https://www.tattuworld.cn/products/tattu-r-line-5-0-2200mah-6s1p-22-2v-150c-fpv-lipo-battery.html'
deck=read(D/'设备板减重试切.json')
wheel="""## 成品轮与安装尺寸

塔克红圈款为橡胶外胎、海绵内胎和 ABS 轮辋，外径 100 mm、胎宽 35 mm、轮辋六角对边 12 mm，商品图标重约 78 g。8 mm 指铜接头的轴孔。卖家未明确 78 g 是否包括所选铜接头。独立型号同类接头参考重 11.5 g，计算取 12 g，另留 2 g 给紧固件，按 92 g/套装车；若塔克的 78 g 已包含全部附件，四角合计可扣 56 g。[卖家标注图](data/塔克100卖家参数图.png) · [塔克淘宝所选规格](https://item.taobao.com/item.htm?id=764659136242&skuId=6021439206463) · [同尺寸铜接头参考](https://www.open-electronics.org/product/8-mm-shaft-wheel-coupler-12-mm-hex/)

从外侧 608 轴承往轮外依次是 2 mm 调整环、两个 Ø8.2×12×8 mm 铝隔套、轮侧铜接头、12 mm 六角轮辋、中心压紧螺钉。每条腿另有一个位于两轴承之间的同规格隔套。沿局部轮轴，自腿基面量，轴承外端 56 mm，调整片到 58 mm，两个隔套到 74 mm，Ø8×60 mm 钢轴末端在 82 mm，接头套筒设计套入 8 mm。模型用同类 HT12SH-D8 的 18 mm 总长、12 mm 套筒及径向 M4 固定；名义顶丝轴线距入口 5 mm，轴端越过顶丝中心 3 mm。模型中的径向顶丝为装配位置说明；到货需核套入深度、顶丝有效压紧及光轴防滑。成品轮顶丝、端螺钉是否随选项配齐也需核对。[同类接头厂家图纸，第 2 页](https://www.handsontec.com/dataspecs/Hex%20wheel%20coupling.pdf)

轮心距腿基面 86 mm，轮胎内侧 68.5 mm，设计轮距 410 mm。把含胎纹的轮胎包络按 Ø100×35 mm 的完整圆柱检查，对左右镜像轮腿在 −36° 至 +33° 每 1° 计算与所有非旋转轮腿件的距离。最近点始终为 S06 压盖紧固螺钉，刚体名义间隙 6.5 mm。轮心低于 79.5 mm 会进入其几何边界；若要保留 3 mm 余隙，轮心至少在 82.5 mm。实际轮辋六角靠面相对胎宽中心的偏距未知。受载鼓胀、轴弯曲、端面摆动及运动线束会消耗间隙。厂家也未给轴向载荷及落地冲击额定值。[70 个姿态的净距](data/轮架净距.json) · [整车刚体干涉](data/clearance.json)

卖家写“双轮负载 2.5 kg、四轮负载 5 kg”，未说明这是整机或额外载荷，也未给测试速度、冲击或载荷分配。若按四轮承受的总质量理解，当前设计在静态就高出约 1.52 kg，6 kg 目标车也高出 1 kg。即使按额外载重理解，资料仍无法推出这辆车的满载低跳余量。"""
(ROOT/'成品轮试配.md').write_text('# Q8 R3 轮侧接口\n\n'+wheel+'\n',encoding='utf8')
existing=(ROOT.parent/'Q8_整车_R2'/'整车装配与核算.md').read_text(encoding='utf8')
electrical=existing[existing.index('## 配电与制动'):existing.index('## 机舱和重量')].replace('1.41 J 机械负功，峰值 112 W','1.35 J 机械负功，峰值 108 W')
gtable='\n'.join(f'| {k} | {v:,.1f} |' for k,v in cats.most_common())
st='\n'.join('| '+lab+' | '+' | '.join(f'{v:.3f}' for v in a[k]['static']['-7']['kg'].values())+' |' for k,lab in [('slice','首车'),('slice_mid','加装 MID-360')])
report=f"""# Q8 R3 成品轮整车

首车含四套 100 mm 轮、8 台电机、6S 2200 mAh 电池，以及自有 Astra Pro Plus、XT-M60 和 Jetson。按 A1 成品切片和装车件核算为 **{m:.3f} kg**，距 6 kg 还需减 **{(m-6)*1000:.0f} g**。首车备料 **¥{cost['total']:,.2f}**。塔克给出的四轮负载为 5 kg，公开资料不足以确认整车满载跳跃。

[整车动作 HTML](整车动作与载荷.html) · [SolidWorks 总装](SolidWorks/Q8_Full_Vehicle.SLDASM) · [淘宝采购清单](整车淘宝采购清单.csv) · [逐件质量证据](逐项质量审计.csv)

## 质量从哪里来

| 首车类别 | 克 |
|---|---:|
{gtable}
| **合计** | **{m*1000:,.1f}** |

本次质量账有 {len(rows)} 行含选装。四条腿合计 {m-b['central']:.3f} kg，每角约 {(m-b['central'])/4:.3f} kg。由此可给机身的额度是 {6-m+b['central']:.3f} kg，实际机身含设备及附件估重 {b['central']:.3f} kg。加装 MID-360、网卡、架柱和线束后约 {a['slice_mid']['mass']:.3f} kg，其中雷达原厂 265 g，四根柱约 59.5 g，打印横架约 43.5 g，网卡及线束紧固合留 116 g。首车只预留 MID-360 安装孔。

与 R2 的 6.683 kg 同口径比较，轮端改动含新增隔套约减 71.4 g，两类 WAGO 按原厂数据减 27.8 g，德格林取中英文中值减 25 g，圆柱头螺钉改用标准重量表合计减 35.5 g，合计约 160 g。估算中仍有 {grades['装车估算']:.0f} g 属于工程留量，包含去底座相机、电子转换器、保险、实际线长和安装附件。另有同规格件参考与按尺寸推算的五金。四轮的 78 g 与 Jetson 的 174 g 都有公开数据，各自附件是否已含，账中逐行列出。[厂家和估算逐项来源](逐项质量审计.csv)

- 达妙髋电机含驱动，4×370 g；FIT0403 含编码器，4×205 g；八台合计 2.300 kg。[达妙资料](https://github.com/dmBots/DM-J4310M-2EC) · [FIT0403 原厂规格](https://wiki.dfrobot.com/fit0403)
- XT-M60 基础款 123 g。Jetson 按 Orin Nano 8GB 开发套件 174 g，未识别的 SSD 和随附件另留 12 g。MC02 为 19.5 g，DRI0041 两块共 64 g。[芯探](https://www.toffuture.com/products/m60) · [NVIDIA](https://forums.developer.nvidia.com/t/jetson-orin-nano-hw-faq/249118) · [达妙](https://github.com/dmBots/DM-MC02) · [DFRobot](https://wiki.dfrobot.com/dri0041/)
- Astra 系列官网标 310 g；当前去底座机头 150 g 缺少相同配置的净重记录。如果实际留在车上的机头重 310 g，保持其他项不变会使整车多 160 g。只有明确 310 g 包含哪些线缆后，才能把它与线束账合并。[奥比中光](https://www.orbbec.com/products/structured-light-camera/astra-series/)
- Tattu TAA22006S15X6 国内页 358 g，含电池插头及引线；同货号海外原厂规格 346±20 g。德格林 B30 厂家中英文给出 500/550 g；525 g 为计算中值。15 V 恩珀 82 g、ANS-H 含片 56 g、吉门含片 24 g/路均属留量，公开页面未能确认完全一致的装车重量。[格氏国内](https://www.tattuworld.cn/products/tattu-r-line-5-0-2200mah-6s1p-22-2v-150c-fpv-lipo-battery.html) · [格氏同货号国际规格](https://www.genstattu.com/tattu-r-line-version-5-0-2200mah-6s-150c-22-2v-lipo-battery-pack-with-xt60-plug/) · [吉门产品图](https://www.zeeman.cn/zh/cproduct/holder/2021-06-16/578.html)
- PETG 装车约 1.159 kg。底盆 268.4 g，上盖 153.8 g；两对镜像轮腿打印件共约 687.3 g，其余为机身托架。每盘按 G-code 中实际成品挤出量折算，另外耗用的支撑和裙边不会留在车上。所有首车打印盘的路径耗材约 {cons:.2f} kg，预算仍按两整卷。[A1 各盘挤出量](data/a1_filament.json)
- 线束 153 g 包含实际裁切的电源、信号、USB、以太网和接头，厂商已含的电池引线留在电池项。其余五金与辅料 67 g 中，设备轴向螺钉和盖板螺钉按规格约 38 g，其余为嵌件、设备螺母、绑带、胶垫等。两项都随最终走线和用料改变，采购整包重量没有算作整车重量。[标准螺钉质量表](https://www.fullerkr.com/collections/din-912-weight-chart)

## 有多少可减

若 78 g 已含轮侧全套，且 12 V 降压实物取 500 g，首车约 **{m-.056-.025:.3f} kg**。若另换同系列 6S 1400 mAh 参考电池（222 g），可再减 136 g，标称能量由 48.84 Wh 降到 31.08 Wh；需重核舱内固定和大电流压降。单改设备上盖的 A1 填充从 40% 至 20%，保留五圈壁和原厚度，成品试切由 153.85 降到 {deck['trial_20pct_g']:.2f} g，仅省 {deck['saving_g']:.1f} g；该试切未装车或验证刚度。上述有利条件全部合计仍约 {m-.056-.025-.136-deck['saving_g']/1000:.3f} kg。单换更轻的轮子或调低填充不足以达到 6 kg。[格氏同系列参数](https://www.tattuworld.cn/products/tattu-r-line-5-0-2200mah-6s1p-22-2v-150c-fpv-lipo-battery.html) · [设备板试切数据](data/设备板减重试切.json)

{wheel}

## 四角载荷与低跳

| 巡航工况，kg/角 | 左前 | 右前 | 左后 | 右后 |
|---|---:|---:|---:|---:|
{st}

按水平地面、相同预紧和相同竖向刚度计算。右前与左前仅差约 6 g，实车可换序。四点同时支撑为静不定问题。首车右前轮在 30 mm 目标的蹬伸阶段峰值轮地反力约 {f['maxforce']:.1f} N，组合不利工况约 {bad['maxforce']:.1f} N；落地峰值还取决于轮胎变形、地面和减速行程。

| 离地后质心目标 | 右前髋名义扭矩 / 倍率 | 峰值转速 / 名义速度倍率 | 组合不利工况扭矩 / 倍率 | 轮胎净空，24 ms 停髋 |
|---|---|---|---|---|
| 20 mm | {low['nominal']['peak']:.2f} N·m / {low['nominal']['factor']:.2f}× | {low['nominal']['speed_peak']:.1f} rpm / {low['nominal']['speed_factor']:.2f}× | {low['adverse']['peak']:.2f} N·m / {low['adverse']['factor']:.2f}× | {low['clear24_mm']:.1f} mm |
| 30 mm | {f['peak']:.2f} N·m / {f['factor']:.2f}× | {f['speed_peak']:.1f} rpm / {f['speed_factor']:.2f}× | {bad['peak']:.2f} N·m / {bad['factor']:.2f}× | {b['brake']['clearance']:.1f} mm |

倍率为可用量除以需求量，1.00 为模型边界。30 mm 时右前髋名义扭矩余量约 {5.2-f['peak']:.2f} N·m，20.7 V、对角增载 0.15 kg、效率从 0.83 降至 0.72 及附加惯量、阻力同时提高时，缺约 {bad['peak']-5.2:.2f} N·m。20 mm 时，组合不利工况仍约有 {5.2-low['adverse']['peak']:.2f} N·m。24 V 额定工作点 5.2 N·m、120 rpm 与 232 rpm 空载构成估算包络；22.2 V、20.7 V 超出了 24 V 电机标示的 24–28 V 工作范围，降压外推及制动扭矩需实测。该筛选没有借用峰值扭矩。

运动学按各件位置和速度给机身、连杆、轮端分配运动质量。接地时轮心几乎不升高，髋关节的惯性项取决于正在运动的质量；离地后所有零件随整车质心作抛体运动，使用 v²/(2g) 得到质心相对离地点的弹道上升。20、30 mm 分别要求质心离地速度约 0.626、0.767 m/s。前后轮腿镜像，假定水平、无显著打滑，支撑末个采样点前角略早卸载；模型未求解四轮非同时离地、机身俯仰和弹性落地。停髋若从 24 延至 32 ms，20 mm 目标的轮胎净空由 {low['clear24_mm']:.1f} 降到 {low['clear32_mm']:.1f} mm，30 mm 由 {b['brake']['clearance']:.1f} 降到 {b['slow_brake']['clearance']:.1f} mm。两种高度都是指定动作的计算值；真实最高跳高和可靠满载跳跃尚无实测。[蹬伸数据](data/整车蹬伸_slice.csv) · [20 mm 工况](data/20mm质心低跳.json) · [达妙手册](https://github.com/dmBots/DM-J4310M-2EC)

## 采购与装配

含八台电机（四髋 ¥2,516、四轮驱 ¥476，合计 ¥2,992），四套成品轮与铜接头 ¥82.80，用户核实的 12 V / 30 A 降压 ¥78，打印耗材按两整卷。首车合计 **¥{cost['total']:,.2f}，未含运费**，其中 {cost['estimated_rows']} 行共 ¥{cost['basis']['预算']:.2f} 为预算单价。已有的 XT-M60、Jetson 和 Astra 新增采购为零，MID-360 及台架工具单列。首车无须加工轮毂。

SolidWorks 2024 SP5 六个配置按下蹲、巡航、蹬伸及加装 MID-360 分组。解压整个包后打开总装，轮腿保留配合。基础配置确认 419 个展开实例，选装 427 个；三种姿态的四轮中心与解析位置吻合。每套镜像腿各用两盘，左右型各打印两套；底盆、上盖、电子托架各一盘。实际可安装界面中，未见厂家图的铜接头偏距、电子小板壳体、线束和软胎仍按说明中的假设处理。总装配置的 Q8_AsBuiltEstimate_kg 为估算属性，配套质量表给出计算依据。[原生验证结果](data/solidworks.json) · [轮心检查](data/native_wheel_centres.json)

"""
(ROOT/'整车装配与核算.md').write_text(report+electrical,encoding='utf8')

