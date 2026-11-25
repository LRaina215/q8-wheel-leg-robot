from common import *
import cadquery as cq
def hub():
    # Wheel axis is +Z. R1 mating faces for shaft stack and rim remain at z58 and z72.
    h=cq.Solid.makeCylinder(15,8.5,cq.Vector(0,0,58)).fuse(cq.Solid.makeCylinder(18,5.5,cq.Vector(0,0,66.5)))
    h=h.cut(cq.Solid.makeCylinder(4.05,16,cq.Vector(0,0,57)))
    for x,y in leg.wh:
        h=h.cut(cq.Solid.makeCylinder(2.05,5.1,cq.Vector(x,y,67)))
    for ang in [45,135]:
        # Hex nut slides axially into this open slot. Its faces normal to the screw axis
        # bear on the inner and outer walls; the 7.2-mm slot stops nut rotation.
        block=cq.Solid.makeBox(3.45,7.18,8.12,cq.Vector(6.2,-3.59,57.94))
        bore=cq.Solid.makeCylinder(2.12,13,cq.Vector(3,0,62),cq.Vector(1,0,0))
        h=h.cut(block.rotate((0,0,0),(0,0,1),ang)).cut(bore.rotate((0,0,0),(0,0,1),ang))
    return h.clean()
def main():
    h=hub();assert h.isValid() and len(h.Solids())==1
    d=ROOT/'source'/'body_step';cq.exporters.export(h,str(d/'Q8_Printed_Hub.step'))
    out=ROOT/'source'/'CNC_candidate';out.mkdir(exist_ok=True)
    # Coupon uses preferred 12 mm stock, planar clamping faces on all four sides.
    # A catalog 2 mm shim restores the 14 mm original wheel stack.
    metal=cq.Solid.makeBox(28,28,12,cq.Vector(-14,-14,0))
    metal=metal.cut(cq.Solid.makeCylinder(4.01,14,cq.Vector(0,0,-1)))
    for x,y in leg.wh:metal=metal.cut(cq.Solid.makeCylinder(1.25,6.1,cq.Vector(x,y,6)))
    for direction in [(1,0,0),(0,1,0)]:
        metal=metal.cut(cq.Solid.makeCylinder(1.25,15,cq.Vector(0,0,3.4),cq.Vector(*direction)))
    assert metal.isValid();cq.exporters.export(metal.clean(),str(out/'W08_6061_hub.step'))
    cq.exporters.export(h.rotate((0,0,0),(1,0,0),180).translate((0,0,72)),str(ROOT/'A1_STL'/'W08_printed_hub.stl')), 
    from geometry_vehicle import mesh_array
    import zlib
    pts,idx=h.tessellate(.10,.20);p=LEG/'data'/'mesh.bin';mesh=json.loads(zlib.decompress(p.read_bytes()));mesh['H04']=mesh_array([v.toTuple() for v in pts],idx)
    (ROOT/'data'/'legmesh.bin').write_bytes(zlib.compress(json.dumps(mesh,separators=(',',':')).encode(),7))
    old=read(LEG/'data'/'geometry.json')['H04']['volume_mm3']*2.7e-6
    hard=.0022*2+.00065*2+.0006*6
    write(ROOT/'data'/'hub.json',dict(plastic_mm3=h.Volume(),old_mass=old,new_mass=h.Volume()*1.04e-6+hard,metal_allowance=hard,delta=h.Volume()*1.04e-6+hard-old,
               com=list(h.Center().toTuple()),material='PETG body, two captured M4 nuts and M4x8 cup screws, six M3x5 brass inserts'))
if __name__=='__main__':main()

