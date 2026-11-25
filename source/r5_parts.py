"""R5 constructive design in millimetres. Sketches are grouped by mounting interface."""
from math import cos,sin,pi
from shapely.geometry import box as polygon_box
from shapely.ops import unary_union
from itertools import product
parts={}
def rect(x,y,a,b):return polygon_box(x-a/2,y-b/2,x+a/2,y+b/2)
def polyloops(polys):
 u=unary_union(polys);out=[]
 for p in (u.geoms if u.geom_type=='MultiPolygon' else [u]):
  for ring in [p.exterior,*p.interiors]:
   coords=list(ring.coords)[:-1]
   # Remove straight subdivisions produced by the planar union.
   pts=[q for i,q in enumerate(coords) if abs((q[0]-coords[i-1][0])*(coords[(i+1)%len(coords)][1]-q[1])-(q[1]-coords[i-1][1])*(coords[(i+1)%len(coords)][0]-q[0]))>1e-8]
   out.append(('p',pts))
 return out
def R(*rects):return polyloops([rect(*v) for v in rects])
def C(pts,d):return [('c',x,y,d/2) for x,y in pts]
def Hex(pts,af):
 r=af/(2*cos(pi/6))
 return [('p',[(x+r*cos(k*pi/3),y+r*sin(k*pi/3)) for k in range(6)]) for x,y in pts]
def op(name,z,h,loops,cut=False,axis='z',draft=0):
 return dict(name=name,z=z,h=h,loops=loops,cut=cut,axis=axis,draft=draft)
def holes(name,pts,d,z,h):return op(name,z,h,C(pts,d),True)
deckpts=list(product([-106.5,106.5],[-65,-15,65]))
midpts=list(product([-108,108],[-73,-4]))
mc=list(product([53.8,89.8],[-70,-34]));xt=list(product([-25,25],[73,101]))
jc=list(product([-106.5,6.5],[-54,14]))
drivers=[(-65,65),(63,58)]
traypts=[(x+dx,y+34) for x,y in drivers for dx in [-18,18]]
astra=list(product([-74,74],[111,142]))
floor_windows=[(-72,-2,31,29),(48,-35,43,30),(48,1,43,18),(-28,-38,15,21),(-28,3,15,21),(0,60,18,16),(-86,49,20,16),(86,52,18,14)]
floor_slots=[(x,y,4,18) for x,y in product([-51,-11],[-49,17])]+[(x+dx*s/2,y,3.2,11) for x,y,dx in [(-81,-37,31),(-68,62,60),(12,59,39),(67,58,42)] for s in [-1,1]]
parts['Chassis']=[op('Bottom_pan',-49,4,R((0,0,236,166))),op('Side_rails',-69,101,R((-115,0,6,166),(115,0,6,166))),op('Floor_vents_and_strap_slots',-50,7,R(*(floor_slots+floor_windows)),True),op('Rail_windows',-42,55,R(*[(x,y,9,40) for x,y in product([-115,115],[-35,35])]),True),op('Hip_M5_cross_bores',-120,240,C([(-z,y) for y,z in product([-75,-60,60,75],[-62,12])],5.3),True,'x'),op('Six_deck_bosses',22,10,R(*[(x/abs(x)*108, y,20,16) for x,y in deckpts])),holes('Power_tray_M3',[(11,-30),(107.5,-30),(72,52)],3.4,-50,7),holes('Deck_M4_clearance',deckpts,4.5,21,12),holes('MID_head_and_tool_passages',midpts,8.2,21,12),op('M4_hex_capture_AF7p3',21,4.4,Hex(deckpts,7.3),True)]
vents=[(-50,-18,75,60),(63,-50,25,18),(0,25,25,22),(-68,60,27,23),(63,58,25,23),(0,78,34,22),(0,-68,44,14),(-85,-76,28,8)]
# Retain front clamp screw land near (6.5,14); split the adjacent cable window.
vents[2]=(-6,29,17,18)
parts['Deck']=[op('Equipment_deck',32,4,R((0,0,236,170),(0,115,192,66))),op('Equipment_and_cable_windows',31,6,R(*vents),True)]
for name,pts,d in [('Chassis_M4',deckpts,4.5),('MID_posts_M4',midpts,4.5),('Jetson_clamps_M3',jc,3.4),('MC02_M2',mc,2.3),('XT_posts_M3',xt,3.4),('Driver_trays_M3',traypts,3.4),('Camera_M3',astra,3.4)]:
 parts['Deck'].append(holes(name,pts,d,31,6))
parts['Deck'].append(op('Logic_and_FFC_strap_slots',31,6,R((5.8,-20,3.2,6),(42.2,-20,3.2,6),(68,-8.6,6,3.2),(68,22.6,6,3.2)),True))
parts['Deck'].append(op('Jetson_longitudinal_stops',36,8,R(*[(x,y,6,2) for x,y in product([-92,-30],[-66.25,27.4])])))
parts['JetClamp']=[op('Foot_and_support_shelf',0,5,R((3.5,0,16,8))),op('Clamp_upright',5,6.7,R((0,0,9.2,8))),op('Corner_retaining_lip',11.7,2.8,R((1.5,0,12.2,8))),holes('M3_through',[(0,0)],3.4,-1,17)]
parts['XT_saddle']=[op('Radar_seat',0,4,R((0,-9,65,68))),op('Lateral_stops',4,9,R((-21.4,0,3,31),(21.4,0,3,31))),holes('Post_M3',[(x,y-110) for x,y in xt],3.4,-1,7),holes('Top_screw_head_reliefs',[(-25,-9),(25,-9)],6.4,4,3.7),op('Retention_strap_slots',-1,7,R((-25,0,3,12),(25,0,3,12)),True)]
parts['Astra_saddle']=[op('Camera_seat',0,3,R((0,0,16,38))),op('Front_lip',3,7,R((0,-18.8,16,2.3))),op('Rear_lip',3,4,R((0,18.8,16,2.3))),op('Strap_slots',-1,5,R((0,-10,8,2.5),(0,10,8,2.5)),True),holes('M3_through',[(0,-15.5),(0,15.5)],3.4,-1,5),op('Flat_head_90deg',1.5,1.5,C([(0,-15.5),(0,15.5)],3.0),True,'z',45)]
parts['Bridge_tray']=[op('Board_support_and_lugs',0,2.5,R((0,0,64,63),(-18,31.5,10,14),(18,31.5,10,14))),op('PCB_edge_stops',2.5,6,R((-29,0,2.5,56),(29,0,2.5,56))),op('Board_strap_slots',-1,4,R((-27,0,2.8,10),(27,0,2.8,10)),True),holes('External_M3_mounts',[(-18,34),(18,34)],3.4,-1,5)]
parts['MID_fit']=[op('Sensor_bridge',0,4,R((0,0,78,86),(0,-34.5,226,13),(0,34.5,226,13))),holes('Deck_columns_M4',[(x,y+38.5) for x,y in midpts],4.5,-1,6),holes('MID360_mount',list(product([-18,18],[-24,24])),3.3,-1,6)]
base=[]; stops=[];lip=[]
for y in [-32,32]:
 base.extend([(-28,y,6,58),(28,y,6,58),(0,y-24,69,7),(0,y+24,69,7)])
 stops.extend([(x,y,2,22) for x in [-31.2,31.2]])
 lip.extend([(x,y+dy,6,2) for x,dy in product([-18,18],[-28,28])])
base.extend([(0,0,5,67),(-1,-17,102,8),(11,61,10,17)])
parts['BuckTray']=[op('Connected_support_rails',0,3,R(*(base+stops+lip))),op('Side_stops',3,1.6,R(*stops)),op('End_stops',3,1.7,R(*lip)),op('Strap_passages',-1,5,R(*[(x,y,2.9,4.2) for x,y in product([-32,32],[-56,-8,8,56])]),True),holes('Floor_M3', [(-50,-17),(46.5,-17),(11,65)],3.4,-1,6),op('Under_strap_recess',-.15,1.3,R(*[(0,y,67,3.2) for y in [-56,-8,8,56]]),True)]
def bolt(key,d,length,head,hh,flat=False):
 # Bearing plane is at local z=0; shank points down. Flat head is included in nominal length.
 parts[key]=[op('Nominal_shank',-length,length-(1.5 if flat else 0),C([(0,0)],d)),op('Head',-1.5 if flat else 0,1.5 if flat else hh,C([(0,0)],d if flat else head),False,'z',45 if flat else 0)]
for k,s in {'B4x16':(4,16,7,4),'B3x22':(3,22,5.5,3),'B3x12':(3,12,5.5,3),'B3x8':(3,8,5.5,3),'B2x16':(2,16,3.8,2),'Flat3x10':(3,10,6,1.5,True)}.items():bolt(k,*s)
for d,af,h in [(4,7,3.2),(3,5.5,2.4),(2,4,1.6)]:
 parts['Nut'+str(d)]=[op('Hex_blank',0,h,Hex([(0,0)],af)),holes('Nominal_thread_envelope',[(0,0)],d+.04,-1,h+2)]
parts['Xsp']=[op('36mm_post',0,36,C([(0,0)],7)),holes('M3_nominal_thread_envelope',[(0,0)],3.04,-1,38)]


bolt('B4x10',4,10,7,4)
parts['Lsp100']=[op('Expansion_column',0,100,C([(0,0)],9)),holes('M4_thread_envelope',[(0,0)],4.04,-1,102)]

changed={'Chassis','Deck','BuckTray','XT_saddle','Bridge_tray'}
def native_name(k):return ('R5F_' if k in changed else 'R5_')+k+'.SLDPRT'
