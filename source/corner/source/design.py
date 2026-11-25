"""Single corner geometry. XY is the leg plane, +Y up, +Z outboard. Units mm."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
L, AB, DROP = 110., 62., 110.
Q0, Q1 = -36., 22.
PARTS, INST = {}, []
COL = {'frame':'#4c677b','drive':'#147d83','follower':'#68a9ab','carrier':'#345675',
       'rim':'#e8a64f','rubber':'#303b44','metal':'#aebac2','dark':'#58616d','motor':'#535d6c','brass':'#c9a66b'}
def circ(x,y,r): return ['c',x,y,r]
def poly(pts): return ['p',list(pts)]
def bolt_circle(x,y,r,n,phase=0):
    return [(x+r*math.cos(math.radians(phase+360*i/n)),y+r*math.sin(math.radians(phase+360*i/n))) for i in range(n)]
def hexagon(x,y,af): return poly(bolt_circle(x,y,af/math.sqrt(3),6,30))
def radial_holes(points,r): return [circ(x,y,r) for x,y in points]
def op(label,z,h,*loops,cut=False):return dict(label=label,z=z,h=h,loops=loops,cut=cut)
def add(id,label,color,ops,printed=False):
    PARTS[id]=dict(id=id,label=label,color=COL[color],ops=ops,printed=printed)
def ins(id,g,x=0,y=0,z=0,rot=0,flip=False):
    INST.append(dict(id=id,g=g,x=x,y=y,z=z,rot=rot,flip=flip))
def outline(nodes):
    # Common external tangents from a sampled convex hull of design stations.
    from scipy.spatial import ConvexHull
    pts=[p for x,y,r in nodes for p in bolt_circle(x,y,r,16,11.25)]
    return poly([pts[i] for i in ConvexHull(pts).vertices])
def ring(x,y,ro,ri):return [circ(x,y,ro),circ(x,y,ri)]
def centered_ring(label,z,h,ro,ri):return op(label,z,h,*ring(0,0,ro,ri))
mount=[(-52,12),(-37,12),(-52,-62),(-37,-62)]
stat=bolt_circle(0,0,25,6,30)
rotor=bolt_circle(0,0,13.5,6)
posts=[(-23,-20),(23,-20),(-23,7),(23,20)]
retainers=bolt_circle(0,0,17,3,90)
wmholes=bolt_circle(0,-7,15.5,6)
def shift(pts,y):return [(x,v+y) for x,v in pts]
def nutseat(name,positions,z,h):
    return op(name,z,h,*[hexagon(x,y,10.35) for x,y in positions],cut=True)
add('P01','机架侧座','frame',[
    op('Frame_and_bench_interface',-1,8,outline([(0,0,33),(0,-AB,14),*[(x,y,7) for x,y in mount]]),
       circ(0,0,20),circ(0,-AB,3.25),*radial_holes(stat,1.65),*radial_holes(mount,2.65)),
    op('Recess_stator_screw_heads',3.1,4,*radial_holes(stat,3.05),cut=True),
    nutseat('Rear_captive_nut_B',[(0,-AB)],-1.01,4.51)],True)
add('P02','主动臂及转子连接盘','drive',[
    op('Arm_web',8,10,outline([(0,0,19),(L,0,11)]),circ(L,0,5.05),*radial_holes(rotor,1.65)),
    op('Rotor_standoff',0,8,circ(0,0,17.2),circ(0,0,5),*radial_holes(rotor,1.65)),
    op('Rotor_screw_spotfaces',12,6.01,*radial_holes(rotor,3),cut=True)],True)
add('P03','从动臂','follower',[op('Passive_arm',8,10,outline([(0,0,11),(L,0,11)]),
    circ(0,0,5.05),circ(L,0,5.05))],True)
add('P04','轮架与偏心电机安装面','carrier',[
    op('Wheel_carrier',0,4,outline([(0,0,13),(0,-AB,13),*[(x,y-DROP,6.6) for x,y in posts],(0,-DROP-7,22)]),
       circ(0,0,3.25),circ(0,-AB,3.25),circ(0,-DROP,6.25),
       *radial_holes(shift(wmholes,-DROP),1.65),*radial_holes(shift(posts,-DROP),2.2)),
    op('Pivot_lands',4,3,outline([(0,0,13),(0,-AB,13)]),circ(0,0,3.25),circ(0,-AB,3.25)),
    nutseat('Nut_seats_C_D',[(0,0),(0,-AB)],-.01,3.01)],True)
add('P05','双608轮轴座','carrier',[
    op('Cartridge_body',34,22,outline([(x,y,6.5) for x,y in posts]+[(0,0,20.5)]),circ(0,0,8.5),*radial_holes(posts,2.2),*radial_holes(retainers,1.65)),
    op('Inboard_608_seat',33.99,7.01,circ(0,0,11.05),cut=True),
    op('Outboard_608_seat',49,7.01,circ(0,0,11.05),cut=True)],True)
wh=bolt_circle(0,0,9.525,6)
add('P06','双胶圈轮辋','rim',[
    op('Wheel_web',72,4,circ(0,0,50.7),circ(0,0,4.6),*radial_holes(wh,1.65),
       *radial_holes(bolt_circle(0,0,29,6,30),9)),
    centered_ring('Rim_inboard',60,12,50.7,42),centered_ring('Rim_outboard',76,8,50.7,42),
    op('Tyre_groove_1',62.2,5.6,*ring(0,0,51,49),cut=True),
    op('Tyre_groove_2',76.2,5.6,*ring(0,0,51,49),cut=True)],True)
add('P07','608外圈压盖','carrier',[op('Outer_race_retainer',0,2,*ring(0,0,20.5,10.3),*radial_holes(retainers,1.65))],True)
# OEM interface models. Threaded holes are represented by tap-drill cylinders.
add('M01','DM-J4310M-2EC 定子接口简模','motor',[
    op('Stator_envelope',-53.3,52.3,circ(0,0,28.5),*radial_holes(stat,1.25)),
    op('Rotor_review_recess',-5.2,4.3,circ(0,0,17.65),cut=True)])
add('Rotor4310','髋电机输出法兰 · 随主动臂','drive',[
    op('Rotating_output_interface',-5,5,circ(0,0,17.5),*radial_holes(rotor,1.52))])
add('M02','FIT0403 轮电机及偏心D轴','motor',[
    op('Gearbox',-24,24,circ(0,-7,18.5)),
    op('Thread_pilots',-3.5,3.51,*radial_holes(wmholes,1.25),cut=True),
    op('Armature',-53,29,circ(0,-7,16.5)),op('Encoder_envelope',-65,12,circ(0,-7,15)),
    op('Nose',0,6,circ(0,0,6)),op('Output',6,15,circ(0,0,3)),
    op('D_flat',9,12.01,poly([(-4,2.5),(4,2.5),(4,4),(-4,4)]),cut=True)])
add('H01','6转8夹紧联轴器 Ø20×25','metal',[
    centered_ring('Six_bore',7.5,12.5,10,3),centered_ring('Eight_bore',20,12.5,10,4)])
add('H02','轮轴 Ø8 h6×60','metal',[op('Ground_shaft',22,60,circ(0,0,4))])
add('H03','608-2RS 8×22×7','dark',[centered_ring('Bearing_envelope',0,7,11,4)])
add('H04','Pololu 2693 六孔M3轮毂','metal',[
    centered_ring('Setscrew_boss',58,9.8,8.7,4),op('Six_hole_flange',67.8,4.2,*ring(0,0,12.7,4),*radial_holes(wh,1.25))])
add('H05','铝制轮轴内圈隔套 8.2×12×8','metal',[centered_ring('Sleeve',0,8,6,4.1)])
add('H06','轮轴内圈调整环 8×12×1.5','metal',[centered_ring('Ring',0,1.5,6,4.05)])
add('H07','轮轴内圈调整环 8×12×2','metal',[centered_ring('Ring',0,2,6,4.05)])
add('H08','M4×30 双通六角隔柱 对边7','brass',[op('Hex_standoff',0,30,hexagon(0,0,7),circ(0,0,1.65))])
add('H09','8×10×10 卷制或聚合物轴套','brass',[centered_ring('Sleeve',8,10,5,4)])
add('H10','Ø8×12 / M6 肩螺钉','metal',[op('Shoulder',7,12,circ(0,0,4)),op('M6_thread',-4,11,circ(0,0,3)),op('Socket_head',19,5.5,circ(0,0,6.5),hexagon(0,0,4))])
add('H11','M6 普通螺母 薄型优先','metal',[op('Hex_nut',0,5,hexagon(0,0,10),circ(0,0,2.5))])
add('H12','Ø8.1×12×1 垫环','metal',[centered_ring('Thrust_ring',0,1,6,4.05)])
add('H13','95×5 NBR胶圈 工作截面近似','rubber',[
    centered_ring('Band_%02d'%i,-2.5+i*.5,.5,51.5+math.sqrt(2.5**2-(-2.25+i*.5)**2),51.5-math.sqrt(2.5**2-(-2.25+i*.5)**2)) for i in range(10)])
def screw(id,d,length):
    add(id,'M%d×%d 内六角圆柱头'%(d,length),'metal',[
        op('Thread_envelope',-length,length,circ(0,0,d/2)),
        op('Socket_head',0,d,circ(0,0,{3:2.75,4:3.5}[d]),hexagon(0,0,{3:2.5,4:3}[d]))])
for id,d,l in [('S01',3,8),('S02',3,16),('S03',3,7),('S04',4,10),('S05',4,30)]:screw(id,d,l)
screw('S06',3,30)
add('H14','M3 普通螺母','metal',[op('Hex_nut',0,2.4,hexagon(0,0,5.5),circ(0,0,1.25))])
for id,g in [('P01','base'),('M01','base'),('P02','drive'),('P03','passive'),('P04','carrier')]:ins(id,g)
TYRE_CENTRE=86.
add('XT100_Tyre','塔克 100×35 软胶海绵胎包络','rubber',[
    op('Tyre_swept_envelope',-17.5,35,*ring(0,0,50,27.5))])
add('XT100_Rim','红圈 ABS 轮辋，六角接口','rim',[
    op('Rim_barrel',-14,28,*ring(0,0,27.5,24.5)),
    op('Spoke_web',6,3,circ(0,0,25),circ(0,0,2.25),*radial_holes(bolt_circle(0,0,16,7),5.5)),
    op('AF12_socket',0,6,circ(0,0,9),hexagon(0,0,12.12))])
PARTS['XT100_Rim']['color']='#ab382e'
add('XT8_Coupler','塔克选配 Ø8 铜接头 · 参考包络','brass',[
    op('Shaft_socket',-12,12,*ring(0,0,6,4)),
    op('Drive_hex',0,6,hexagon(0,0,12),circ(0,0,1.65))])
add('XT8_Screw','外侧中心锁紧螺钉 · 示意','metal',[
    op('Thread_envelope',1,8,circ(0,0,1.64)),op('Screw_head',9,3,circ(0,0,3.7))])
for id in ['P05','M02','H01','H02']:
    ins(id,'wheel' if id in ['H01','H02'] else 'carrier',0,-DROP)
for id in ['XT100_Tyre','XT100_Rim','XT8_Coupler','XT8_Screw']:
    ins(id,'wheel',0,-DROP,TYRE_CENTRE)
for z in [58,66]:ins('H05','wheel',0,-DROP,z)
for z in [34,49]:ins('H03','carrier',0,-DROP,z)
for z in [32,56]:ins('P07','carrier',0,-DROP,z)
for x,y in retainers:
    ins('S06','carrier',x,y-DROP,32,flip=True);ins('H14','carrier',x,y-DROP,58)
for id,z in [('H05',41),('H06',32.5),('H07',56)]:ins(id,'wheel',0,-DROP,z)
for x,y in stat:ins('S01','base',x,y,3.1)
for x,y in rotor:ins('S02','drive',x,y,12)
for x,y in wmholes:ins('S03','carrier',x,y-DROP,4)
for x,y in posts:
    ins('H08','carrier',x,y-DROP,4);ins('S04','carrier',x,y-DROP,0,flip=True);ins('S05','carrier',x,y-DROP,56)
for x,y,g,link,rx in [(0,-AB,'base','passive',0),(0,0,'carrier','drive',L),(0,-AB,'carrier','passive',L)]:
    ins('H10',g,x,y);ins('H11',g,x,y,-1.5 if g=='base' else -2)
    for z in [7,18]:ins('H12',g,x,y,z)
    ins('H09',link,rx,0)
def group_pose(g,q):
    a=math.radians(q)
    if g=='base':return (0,0,0)
    if g=='drive':return (0,0,-q)
    if g=='passive':return (0,-AB,-q)
    return (L*math.cos(a),-L*math.sin(a),0)

ins('Rotor4310','drive',0,0,0)
