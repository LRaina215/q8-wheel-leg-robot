from geometry_vehicle import *
from clearance import rigid,meet,bounds
import csv
data=ROOT/'data'
layout=read(data/'layout.json')
meshes=json.loads(zlib.decompress((data/'bodymesh.bin').read_bytes()))
layout['parts'].pop('Daygreen_B30',None);meshes.pop('Daygreen_B30',None)
layout['instances']=items
for key in ['YourCee20','BuckTray']:
    p=D[key];s=p['shape'];sol=s.Solids();b=s.BoundingBox()
    assert len(sol)==1 and s.isValid(),(key,len(sol))
    entry={k:v for k,v in p.items() if k!='shape'}
    entry.update(volume_mm3=s.Volume(),com=s.Center().toTuple(),bbox=bounds(s).tolist())
    if key=='BuckTray':
        m=s.Volume()*1.04/1e6
        entry.update(mass=m,low=m*.82,high=m*1.22)
        cq.exporters.export(s,str(ROOT/'A1_STL'/'BuckTray.stl'),tolerance=.06)
    else:assert np.allclose([b.xlen,b.ylen,b.zlen],[60,53,30])
    layout['parts'][key]=entry
    cq.exporters.export(s,str(ROOT/'source'/'body_step'/(key+'.step')))
    pts,idx=s.tessellate(.15,.22);meshes[key]=mesh_array([v.toTuple() for v in pts],idx)
write(data/'layout.json',layout)
(data/'bodymesh.bin').write_bytes(zlib.compress(json.dumps(meshes,separators=(',',':')).encode(),7))
print('Installed models',[(k,layout['parts'][k]['volume_mm3']) for k in ['YourCee20','BuckTray']],flush=True)
