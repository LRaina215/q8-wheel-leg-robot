from common import *
from wire_check import Surface,dense
from wire_space import meshes
from r5_static import proto
from r5_instances import ids,records,matrix
from pathlib import Path
import ast,csv
src=Path(__file__).parent
f=(src/'wire_fixed_check.py').read_text(encoding='utf-8-sig');exec(ast.get_source_segment(f,next(v for v in ast.parse(f).body if isinstance(v,ast.FunctionDef) and v.name=='owned')))
db=read(ROOT/'data/R5_wiring.json')
tri=meshes('bodymesh.bin')
for k in ids:
 pts,index=proto(k).tessellate(.08,.18);tri[k]=(np.array([x.toTuple() for x in pts]),np.array(index))
surfaces={k:Surface(p,i) for k,(p,i) in tri.items()};hit={}
for wire in db['routes']:
 if 'frames' in wire:continue
 line=dense(wire['points']);r=wire['dia']/2
 for item in records:
  k=item['id'];keep=np.ones(len(line),bool)
  for n,pos in [(wire['a'],line[0]),(wire['b'],line[-1])]:
   if owned(n,k):keep&=np.linalg.norm(line-pos,axis=1)>20
  if not keep.any():continue
  d=surfaces[k].gap((line[keep]-item['pos'])@matrix(item),r+1)-r
  if d<-.02:hit[wire['id']+'/'+item['name']]=round(d,3)
write(ROOT/'data/R5_fixed_wires.json',hit);print('fixed wires',hit,flush=True)
s=(src/'wire_paircheck.py').read_text(encoding='utf-8-sig').replace('整车线束.json','R5_wiring.json').replace('线对线复核.json','R5_wire_pairs.json');exec(compile(s,'R5_wire_pairs','exec'))
with (ROOT/'R5_线束裁线.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['线号','从','到','线型','根数','路径长 mm','建议裁线长 mm','选装'])
 for t in db['routes']:w.writerow([t['id'],db['nodes'][t['a']]['label'],db['nodes'][t['b']]['label'],t['stock'],t['cores'],t['fixed_mm'],t['cut'],t['optional']])

