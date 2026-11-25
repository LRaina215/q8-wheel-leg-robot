from common import *
from geometry import shape,placed
from geometry_vehicle import mesh_array
import zlib
import cadquery as cq

def prepare():
    geo=read(LEG/'data'/'geometry.json')
    file=ROOT/'data'/'legmesh.bin'
    mesh=json.loads(zlib.decompress(file.read_bytes()))
    for key in [k for k in leg.PARTS if k.startswith('XT')]:
        sh=shape(leg.PARTS[key]);bb=sh.BoundingBox()
        assert len(sh.Solids())==1
        geo[key]=dict(volume_mm3=sh.Volume(),center=list(sh.Center().toTuple()),bounds=[bb.xlen,bb.ylen,bb.zlen])
        vertices,idx=sh.tessellate(.10,.20)
        mesh[key]=mesh_array([v.toTuple() for v in vertices],idx)
    assert np.allclose(geo['XT100_Tyre']['bounds'],[100,100,35])
    write(LEG/'data'/'geometry.json',geo)
    file.write_bytes(zlib.compress(json.dumps(mesh,separators=(',',':')).encode(),7))

def clearance():
    # A solid rotating cylinder bounds all tread, rim and bolt head in the same
    # 35 mm slab; using its entire face also covers any wheel rotational phase.
    cz=leg.TYRE_CENTRE
    wheel=cq.Solid.makeCylinder(50,35,cq.Vector(0,0,cz-17.5))
    fixed={t['id']:shape(leg.PARTS[t['id']]) for t in leg.INST if t['g']!='wheel'}
    qvalues=list(range(-36,34));records=[]
    for q in qvalues:
        x,y,_=leg.group_pose('wheel',q)
        w=wheel.translate((x,y-leg.DROP,0))
        best=(1e3,'')
        for t in leg.INST:
            if t['g']=='wheel':continue
            s=placed(fixed[t['id']],t,q)
            # Axial lower bound is independent of the leg angle. Retain each
            # possible nearest obstacle for the exact OCCT distance query.
            if cz-17.5-s.BoundingBox().zmax>best[0]+.01:continue
            gap=w.distance(s)
            if gap<best[0]:best=(gap,t['id'])
        records.append([q,round(best[0],3),best[1]])
    assert min(r[1] for r in records)>0
    write(ROOT/'data'/'轮架净距.json',dict(angles=qvalues,per_pose=records,nominal_centre=cz,tyre_width=35,
        track=2*(HX+cz),shaft=[22,82],spacers=[[58,66],[66,74]],coupler=[74,92],shaft_engagement=8,
        min_gap_mm=min(r[1] for r in records),min_centre_for_clearance_mm=cz-min(r[1] for r in records),
        scope='Full OD swept cylinder vs all non-rotating leg parts; four corners are rigid mirrors. Excludes elastic deformation, leads and manufacturing variation.'))
if __name__=='__main__':prepare();clearance()
