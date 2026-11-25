from common import *
import cadquery as cq,zlib
from geometry_vehicle import mesh_array
from wheelhub import hub
def main():
    d=ROOT/'data';q=read(d/'铨洲轮毂活动回执.json');assert q['all_thread_groups_selected'] and q['quantity']==4
    s=cq.importers.importStep(str(ROOT/'source'/'CNC_candidate'/'W08_6061_hub.step')).val().translate((0,0,60))
    ring=cq.Solid.makeCylinder(6,2,cq.Vector(0,0,58)).cut(cq.Solid.makeCylinder(4.05,4,cq.Vector(0,0,57)))
    nominal=s.Volume()*2.70e-6+ring.Volume()*7.85e-6+.00088
    center=(np.array(s.Center().toTuple())*s.Volume()*2.70e-6+np.array(ring.Center().toTuple())*ring.Volume()*7.85e-6+np.array([4,4,63.4])*.00088)/nominal
    h=s.fuse(ring).clean();assert len(h.Solids())==1
    cq.exporters.export(h,str(ROOT/'source'/'body_step'/'W08_installed.step'))
    pts,idx=h.tessellate(.10,.2);mesh=json.loads(zlib.decompress((LEG/'data'/'mesh.bin').read_bytes()))
    mesh['H04']=mesh_array([v.toTuple() for v in pts],idx);(d/'legmesh.bin').write_bytes(zlib.compress(json.dumps(mesh,separators=(',',':')).encode(),7))
    initial=read(d/'hub.json')['old_mass']
    write(d/'selected_hub.json',dict(route='铨洲6061活动打样',price=111.2,model='S7010205',old_mass=initial,new_mass=nominal,delta=nominal-initial,
          com=center.tolist(),volume_mm3=h.Volume(),color='#9eacaf',note='R1 轮辋孔距保留。四只 28×28×12 mm 方轮毂采用有回执的 6061 活动打样，六个端面 M3、两个侧面 M3。每轴多装一片 2 mm 垫环，使胎面和轮距保持原设计值。'))
if __name__=='__main__':main()

