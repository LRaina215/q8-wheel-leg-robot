from common import *
from geometry import shape
import cadquery as cq,shutil
dest=ROOT/'A1_STL'/'legs'
dest.mkdir(exist_ok=True)
src=ROOT.parent/'Q8_单轮腿_R1'/'A1_STL'
for p in src.glob('*.stl'):shutil.copyfile(p,dest/p.name)
for id in ['P01','P02','P03','P04','P05']:
    s=shape(mirrored(leg.PARTS[id]))
    if id=='P02':s=s.rotate((0,0,0),(1,0,0),180)
    b=s.BoundingBox();s=s.translate((3-b.xmin,3-b.ymin,-b.zmin))
    assert max(b.xlen,b.ylen)<250
    cq.exporters.export(s,str(dest/('LH_'+id+'.stl')),tolerance=.045,angularTolerance=.12)
