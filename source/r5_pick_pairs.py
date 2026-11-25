from pathlib import Path
p=Path('r5_report.py');s=p.read_text(encoding='utf8')
i=s.index(" template=(src/'r5_view")
s=s[:i]+""" def leg_instance(k):return 'FL_'+k+'_'+str(next(i for i,t in enumerate(leg.INST) if t['id']==k))
 v['pairs']=[
  ['上板与左侧凸耳',['Deck_1','Chassis_1','Deck_S1','Deck_N1'],'M4×16 穿过上板和底盆凸耳，底部六角窝约束螺母。'],
  ['左前轮胎与轮架紧固件',[leg_instance('XT100_Tyre'),leg_instance('S06')],'Ø100×35 胎体完整旋转包络到 S06 最近为 6.5 mm。'],
  ['左前电机输出法兰与主动臂',[leg_instance('Rotor4310'),leg_instance('P02'),leg_instance('S02')],'输出法兰、连接螺钉与主动臂同步转动。'],
  ['左侧雷达柱与上板',['Deck_1','Xsp_1','XT_lower_S1','XT_saddle_1','XT_upper_S1'],'隔柱两端各用一枚 M3×8，减重窗边缘留有完整承托环。']]
 v['pairs'] += [[h[0]+' / '+h[1],h[:2],('名义螺纹啮合' if intended(h) else '几何重叠')+'，模型相交体积 '+str(h[2])+' mm³。'] for h in rows['hits']]
"""+s[i:]
p.write_text(s,encoding='utf8')
p=Path('r5_view.html');s=p.read_text(encoding='utf8').replace('<p id="results"></p>','<select id="pairs" aria-label="检查零件组合"><option value="">查看整车</option></select><p id="results"></p>')
i=s.index('function select(id)')
s=s[:i]+"""let focusIds=null;for(const [i,v] of V.pairs.entries())get('pairs').append(new Option(v[0],i));get('pairs').onchange=()=>{let k=get('pairs').value;focusIds=k===''?null:new Set(V.pairs[k][1]);if(focusIds){for(let id of focusIds){let d=tag.get(id)?.userData;if(d?.opt)get('mid').checked=true}get('cover').checked=false;get('screws').checked=true;get('detail').textContent=V.pairs[k][2]}draw()};
"""+s[i:];s=s.replace("selected=tag.get(id);if(selected)","focusIds=null;get('pairs').value='';selected=tag.get(id);if(selected)")
s=s.replace("(!d.line||get('wire').checked)}","(!d.line||get('wire').checked);if(focusIds&&!focusIds.has(d.id)){o.material.transparent=true;o.material.opacity=.055;o.material.depthWrite=false}else{o.material.transparent=false;o.material.opacity=1;o.material.depthWrite=true}}")
p.write_text(s,encoding='utf8')

