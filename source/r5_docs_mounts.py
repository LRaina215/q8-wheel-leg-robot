from pathlib import Path
p=Path('r5_delivery.py');s=p.read_text(encoding='utf8').replace('上端四枚 M3×8 固定鞍座。','上端四枚 M3×8 固定鞍座。第二根柱的同心配合约束鞍座的转角。').replace('四枚 M2×16 和 M2 螺母。','四枚 M2×16 和 M2 螺母。装配体取两个真实板孔定位，保留 8 mm 隔高。')
s=s.replace('配置管理器中选择 Motion。','配置管理器中选择 Motion。设计行程为 −36° 至 +22°。')
s=s.replace(",'零件树、依赖清单",",'零件树、依赖清单")
s=s.replace(" (base/'审阅与装配说明.md').write_text"," lines.extend(['','操作参考见 [SolidWorks 动态间隙](https://help.solidworks.com/2024/English/SolidWorks/sldworks/t_Dynamic_Clearance_SWassy.htm)。'])\n (base/'审阅与装配说明.md').write_text")
p.write_text(s,encoding='utf8')

