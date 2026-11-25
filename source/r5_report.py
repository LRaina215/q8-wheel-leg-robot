from common import *
from r5_instances import records,old,ids
from r5_parts import changed
from r5_static import proto
from module_catalog import GROUPS
functions={k:purpose for entries in GROUPS.values() for k,title,purpose in entries}
functions["Tattu_2200_6S"]="6S 主电池，分别供髋电机、两路轮驱降压和电子设备电源。"
import base64,zlib,csv,shutil
from collections import Counter
from pathlib import Path
import cadquery as cq
src=Path(__file__).parent
labels={'JetClamp':'Jetson 底座边缘压爪','B4x16':'M4×16 内六角圆柱头螺钉','B4x10':'M4×10 内六角圆柱头螺钉','B3x22':'M3×22 内六角圆柱头螺钉','B3x12':'M3×12 内六角圆柱头螺钉','B3x8':'M3×8 内六角圆柱头螺钉','B2x16':'M2×16 内六角圆柱头螺钉','Flat3x10':'M3×10 沉头螺钉','Nut4':'M4 六角螺母','Nut3':'M3 六角螺母','Nut2':'M2 六角螺母'}
printed=['Deck','Chassis','BuckTray','Bridge_tray','JetClamp','XT_saddle','Astra_saddle','MID_fit']
desc={'JetClamp':'四个压爪承托底壳并限制上抬，前后挡块在上板上。','Deck':'六个 M4 通孔与底盆凸耳同轴；螺母从凸耳下方装入六角窝。','Chassis':'六个上板凸耳、四角髋座横孔和下层托盘安装孔。','BuckTray':'两块 12 V 板用扎带压在轨面上。三个 M3 螺钉固定托架。','Bridge_tray':'外伸耳上的两个 M3 螺钉固定托盘，束带固定轮驱板。','XT_saddle':'四根 36 mm 双通隔柱支承雷达鞍座，上下各四枚 M3×8。','Astra_saddle':'四枚 M3 沉头螺钉齐平装入两个相机托块。','MID_fit':'四根选装支柱安装试配横架。雷达底部四个螺孔中心距 36 × 48 mm。'}
def data():
 body=json.loads(zlib.decompress((ROOT/'data/bodymesh.bin').read_bytes()));legs=json.loads(zlib.decompress((ROOT/'data/legmesh.bin').read_bytes()))
 meta={};sd=ROOT/'A1_STL';sd.mkdir(exist_ok=True)
 oldlegs=Path('D:/Desktop/SOC FPGA/Structure/Q8_整车_R4/A1_STL/legs')
 if oldlegs.is_dir():shutil.copytree(oldlegs,sd/'legs',dirs_exist_ok=True)
 for k in {t['id'] for t in records}:
  entry=old['parts'].get(k,{})
  if k in ids:
   s=proto(k);pts,faces=s.tessellate(.1,.18);array=lambda l,t:base64.b64encode(np.array(l,dtype=t).tobytes()).decode('ascii')
   body[k]=[array([v.toTuple() for v in pts],'<f4'),array(faces,'<u4')]
   if k in printed:
    b=s.BoundingBox();cq.exporters.export(s.translate((-b.xmin,-b.ymin,-b.zmin)),str(sd/(k+'.stl')),tolerance=.055)
  is_fast=k in labels and k!='JetClamp' or k in ['B5bolt','B5nut','B5washer']
  meta[k]=[labels.get(k,entry.get('name',k)),desc.get(k,'装配中使用的标准紧固件。' if is_fast else functions.get(k,entry.get('source',''))),entry.get('color','#528c75' if k in printed else '#89999e'),is_fast]
 wiring=read(ROOT/'data/R5_wiring.json')
 rows=read(ROOT/'data/R5_static.json');sw=read(ROOT/'data/R5_sweep.json')
 hits=[h for h in rows['hits'] if not intended(h)]
 v=dict(mesh={**{k:body[k] for k in meta},**legs},items=records,meta=meta,legmeta={k:[p['label'],p['color']] for k,p in leg.PARTS.items()},inst=leg.INST,wiring=wiring,note=f"髋角 −36° 到 +22° 取 {sw['angles']} 个位置。轮腿与整车固定件有 {len(sw['hits'])} 组实体穿透。静态检查有 {len(hits)} 组非螺纹重叠超过 0.12 mm³。")
 def leg_instance(k):return 'FL_'+k+'_'+str(next(i for i,t in enumerate(leg.INST) if t['id']==k))
 v['pairs']=[
  ['上板与左侧凸耳',['Deck_1','Chassis_1','Deck_S1','Deck_N1'],'M4×16 穿过上板和底盆凸耳，底部六角窝约束螺母。'],
  ['左前轮胎与轮架紧固件',[leg_instance('XT100_Tyre'),leg_instance('S06')],'Ø100×35 胎体完整旋转包络到 S06 最近为 6.5 mm。'],
  ['左前电机输出法兰与主动臂',[leg_instance('Rotor4310'),leg_instance('P02'),leg_instance('S02')],'输出法兰、连接螺钉与主动臂同步转动。'],
  ['左侧雷达柱与上板',['Deck_1','Xsp_1','XT_lower_S1','XT_saddle_1','XT_upper_S1'],'隔柱两端各用一枚 M3×8，减重窗边缘留有完整承托环。']]
 pairqa=read(ROOT/'data/R5_wire_pairs.json');gap,k1,k2=pairqa['fixed_min']
 v['pairs'].append(['固定线最小名义间隙',[k1,k2],f"{k1} 与 {k2} 计算最近相距 {gap:.2f} mm。实体装配时按实际线径分开固定。"])
 v['pairs'] += [[h[0]+' / '+h[1],h[:2],('名义螺纹啮合' if intended(h) else '几何重叠')+'，模型相交体积 '+str(h[2])+' mm³。'] for h in rows['hits']]
 template=(src/'r5_view.html').read_text(encoding='utf-8-sig')
 (ROOT/'R5_装配与运动审阅.html').write_text(template.replace('__THREE__',(src/'three.min.js').read_text(encoding='utf8')).replace('__DATA__',json.dumps(v,separators=(',',':'),ensure_ascii=False)),encoding='utf8')
 counts=Counter((t['id'],t['optional']) for t in records)
 with (ROOT/'R5_安装件明细.csv').open('w',encoding='utf-8-sig',newline='') as f:
  out=csv.writer(f);out.writerow(['零件','名称','首车数量','MID选装增量','装配实例'])
  for k in sorted(set(ids)|{'Msp','B5bolt','B5nut','B5washer'}):out.writerow([k,meta[k][0],counts[k,False],counts[k,True],' / '.join(t['name'] for t in records if t['id']==k)])
 with (ROOT/'R5_配合检查.csv').open('w',encoding='utf-8-sig',newline='') as f:
  out=csv.writer(f);out.writerow(['部件A','部件B','X mm','Y mm','支承环覆盖率','孔内侵入 mm³','相交 mm³','判读'])
  for r in rows['support_rings']:out.writerow(r+['','安装孔及承托截面'])
  for h in rows['hits']:out.writerow(h[:2]+['','','','',h[2],'名义螺纹啮合' if intended(h) else '实体干涉'])
def intended(h):
 a,b,_=h
 return (a.startswith('B5bolt_') and b=='B5nut_'+a.split('_')[-1]) or (a=='MID360_1' and b.startswith('MID_sensor_S'))
if __name__=='__main__':data()

