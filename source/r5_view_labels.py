from pathlib import Path
p=Path('r5_report.py');s=p.read_text(encoding='utf8').replace('from r5_static import proto','from r5_static import proto\nfrom module_catalog import GROUPS\nfunctions={k:purpose for entries in GROUPS.values() for k,title,purpose in entries}\nfunctions["Tattu_2200_6S"]="6S 主电池，分别供髋电机、两路轮驱降压和电子设备电源。"').replace("else entry.get('source','')","else functions.get(k,entry.get('source',''))")
s=s.replace(" v['pairs'] += [[h[0]",''' pairqa=read(ROOT/'data/R5_wire_pairs.json');gap,k1,k2=pairqa['fixed_min']
 v['pairs'].append(['固定线最小名义间隙',[k1,k2],f"{k1} 与 {k2} 计算最近相距 {gap:.2f} mm。实体装配时按实际线径分开固定。"])
 v['pairs'] += [[h[0]''');p.write_text(s,encoding='utf8')
p=Path('r5_view.html');s=p.read_text(encoding='utf8').replace("if(d?.opt)get('mid').checked=true}","if(d?.opt)get('mid').checked=true;if(d?.line)get('wire').checked=true}").replace('线束沿用项目布线路径。','六条固定线路已按新支架重新绕行。');p.write_text(s,encoding='utf8')
p=Path('r5_delivery.py');s=p.read_text(encoding='utf-8-sig').replace('from r5_vehicle_names import NAME\n','').replace('沿','沿').replace('；','。')
s=s.replace("## 使用边界", "## 使用边界")
s=s.replace(",'','## 使用边界'",",f\"- 固定线间最小名义间隙 {wirepair['fixed_min'][0]:.2f} mm，位于 {wirepair['fixed_min'][1]} 与 {wirepair['fixed_min'][2]}。活动线与固定线的最小抽样间隙 {wiremin[0]:.2f} mm。\",'','## 使用边界'")
p.write_text(s,encoding='utf8')

