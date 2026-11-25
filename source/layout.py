from common import *
import cadquery as cq
from OCP.gp import gp_Trsf
from collections import OrderedDict
D=OrderedDict();items=[]
def box(sx,sy,sz,x=0,y=0,z=0):return cq.Solid.makeBox(sx,sy,sz,cq.Vector(x-sx/2,y-sy/2,z))
def cyl(x,y,z,r,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def along_x(x,y,z,r,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),cq.Vector(1,0,0))
def holes(s,xy,r,z,h):
    for x,y in xy:s=s.cut(cyl(x,y,z,r,h))
    return s
def both(xs,ys):return [(x,y) for x in xs for y in ys]
def fuse(*sh):return sh[0].fuse(*sh[1:]).clean()
def define(id,name,kind,shape,color,source='设计尺寸',mass=None,low=None,high=None,com=None):
    D[id]=dict(name=name,kind=kind,shape=shape,color=color,source=source,mass=mass,low=low,high=high,com=com)
def put(id,x=0,y=0,z=0,rz=0,optional=False,name=None):
    items.append(dict(id=id,pos=[x,y,z],rz=rz,optional=optional,name=name or id+'_'+str(1+sum(v['id']==id for v in items))))
def four(x,y,dx,dy):return both([x-dx/2,x+dx/2],[y-dy/2,y+dy/2])
deckbolts=both([-113,113],[-65,0,65]);midpost=both([-108,108],[-73,-4])
jet=[(x-50,y-20) for x in [-49.2,49.2] for y in [-42.2,43.7]]
mc=[(64+x,-52+y) for x in [-10.2,25.8] for y in [-18,18]]
# Driver torqueless snap-in trays use a strap, deliberately independent of PCB hole pitch.
drivers=[(-65,65),(63,58)]
xtp=four(0,87,50,28)
def build():
    floor=box(236,166,4,z=-49)
    for x,y,sx,sy in [(-72,-2,31,29),(48,-35,43,30),(48,1,43,18),(-28,-38,15,21),(-28,3,15,21),(0,60,18,16),(-86,49,20,16),(86,52,18,14)]:
        floor=floor.cut(box(sx,sy,7,x,y,-50))
    for x in [-51,-11]:
        for y in [-49,17]:floor=floor.cut(box(4,18,7,x,y,-50))
    # Through slots retain the power converters, fuse and terminals under vibration.
    for x,y,dx in [(-81,-37,31),(60,-30,98),(-68,62,60),(12,59,39),(67,58,42)]:
        for xx in [x-dx/2,x+dx/2]:floor=floor.cut(box(3.2,11,8,xx,y,-50))
    rails=[]
    for sign in [-1,1]:
        rail=box(6,166,101,115*sign,0,-69)
        for y in [-75,-60,60,75]:
            for z in [-62,12]:rail=rail.cut(along_x(-121 if sign<0 else 110,y,z,2.65,12))
        for y in [-35,35]:rail=rail.cut(box(9,40,55,115*sign,y,-42))
        for x,y in deckbolts:
            if x*sign>0:rail=rail.fuse(box(11,13,7,sign*112.5,y,25))
        rail=holes(rail,[(x,y) for x,y in deckbolts if x*sign>0],2.0,24,10)
        rails.append(rail)
    base=fuse(floor,*rails);define('Chassis','一体底盆与四角侧耳','PETG',base,'#42626d');put('Chassis')
    deck=box(236,170,4,0,0,32).fuse(box(192,66,4,0,115,32))
    for x,y,sx,sy in [(-50,-18,75,60),(63,-50,25,18),(0,25,29,29),(-68,60,27,23),(63,58,25,23),(0,78,60,22),(0,-68,44,14),(-85,-76,28,8)]:
        deck=deck.cut(box(sx,sy,8,x,y,30))
    deck=holes(deck,deckbolts,2.25,30,9);deck=holes(deck,midpost,2.25,30,9)
    deck=holes(deck,jet,1.7,30,9);deck=holes(deck,mc,1.15,30,9)
    deck=holes(deck,xtp,1.7,30,9)
    for x,y in drivers:
        deck=holes(deck,[(x-21,y),(x+21,y)],1.7,30,9)
    for x in [-74,74]:deck=holes(deck,[(x,111),(x,142)],1.7,30,9)
    define('Deck','上层设备板与前伸相机座','PETG',deck.clean(),'#69828a');put('Deck')
    # Rear of beam is open for the XT cable; posts stand behind the camera.
    xtbridge=box(65,68,4,0,-9,0)
    xtbridge=holes(xtbridge,[(x,y-110) for x,y in xtp],1.7,-1,7)
    xtbridge=fuse(xtbridge,box(3,31,9,-21.4,0,4),box(3,31,9,21.4,0,4))
    for x in [-25,25]:xtbridge=xtbridge.cut(box(3,12,7,x,0,-1))
    define('XT_saddle','竖装雷达鞍座与扎带槽','PETG',xtbridge,'#548f86');put('XT_saddle',0,110,72)
    astr=box(16,38,3)
    astr=holes(astr,[(0,-15.5),(0,15.5)],1.7,-1,7)
    astr=fuse(astr,box(16,2.3,7,0,-18.8,3),box(16,2.3,4,0,18.8,3))
    for y in [-10,10]:astr=astr.cut(box(8,2.5,5,0,y,-1))
    define('Astra_saddle','相机端部承托块','PETG',astr,'#548f86')
    for x in [-74,74]:put('Astra_saddle',x,126.5,36)
    tray=box(64,63,2.5)
    tray=holes(tray,[(-21,0),(21,0)],1.7,-1,6)
    for x in [-29,29]:tray=tray.fuse(box(2.5,56,6,x,0,2.5)).cut(box(2.8,10,4,x+(-2 if x>0 else 2),0,-1))
    define('Bridge_tray','55 mm 双路轮驱板托盘','PETG',tray.clean(),'#609184')
    for x,y in drivers:put('Bridge_tray',x,y,36)
    def tube(id,name,h,r,ri,kind='标准件',color='#b6c0c4'):
        define(id,name,kind,cyl(0,0,0,r,h).cut(cyl(0,0,-1,ri,h+2)),color)
    for id,label,h,r,ri,pts,z,opt in [('Jsp','Jetson M3 隔套',5,3,1.55,jet,36,False),('Msp','MC02 M2 隔套',8,2.4,1.05,mc,36,False),('Xsp','雷达 M3 双通隔柱',36,3.5,1.25,xtp,36,False),('Lsp100','扩展 M4 铝支柱 100 mm',100,4.5,1.65,midpost,36,True)]:
        tube(id,label,h,r,ri)
        for x,y in pts:put(id,x,y,z,optional=opt)
    # Four mounting points, open peripheral space and rear cable clearance.
    # The optional printed bridge is a fit-check piece for the future sensor.
    bridge=fuse(box(78,86,4),box(226,13,4,0,-34.5),box(226,13,4,0,34.5))
    bridge=holes(bridge,[(x,y+38.5) for x,y in midpost],2.25,-1,7)
    bridge=holes(bridge,four(0,0,36,48),1.65,-1,7)
    define('MID_fit','MID360 孔位试装横架','PETG',bridge,'#669089');put('MID_fit',0,-38.5,136,optional=True)
    sensors=[('Jetson_Orin_Nano','Orin Nano 8GB 套件含 SSD',(-50,-20,41),.186,.174,.215,'项目质量账，套件174g加存储及附件','#719654'),('MC02','达妙 MC02 H7',(64,-52,44),.030,.022,.045,'原厂 PCB，项目估重','#4b956b'),('XT_M60','XT-M60 竖装含尾部',(0,112,76),.123,.118,.135,'项目库厂商名义质量','#3d555d'),('Astra_Pro_Plus','Astra Pro Plus 去底座',(0,126.5,39),.150,.120,.200,'项目无底座估重','#444d58'),('Tattu_2200_6S','格氏 Tattu 6S 2200 mAh',(-31,-26,-44),.358,.344,.375,'厂商名义，接口与绑带另列','#ce8d39'),('MID360','Livox MID360',(0,-38.5,140),.265,.255,.275,'原厂约265g','#6c777e')]
    for id,name,pos,wt,lo,hi,ref,col in sensors:
        md=read(LIB/id/'model.json');bb=[md['min_mm'],md['max_mm']];c=((np.array(bb[0])+bb[1])/2).tolist()
        if id=='XT_M60':c=[0,-3,32.5]
        define(id,name,'设备',None,col,ref,wt,lo,hi,c);D[id]['bbox']=bb
        put(id,*pos,optional=id=='MID360')
    def unit(id,n,w,h,t,col,m,lo,hi,where,typ='布置包络'):
        sh=box(w,h,t);define(id,n,typ,sh,col,'按选型外廓留位，质量估算',m,lo,hi);put(id,*where)
    from buck_geometry import add_pair
    add_pair(define,put,box,cyl,fuse)
    D['MC02'].update(mass=.0195,low=.0185,high=.023,source='达妙 MC02 V1.1 说明书第2页 19.5 g，外接线计在线束')
    unit('AuxBuck','电子 15 V / 5 A 恩珀降压',25,58,20,'#95a0a1',.082,.065,.125,(-81,-37,-45))
    unit('ANS_H','ANS-H 主保险座与 40 A MIDI 保险片',30.5,53,25.8,'#b36144',.056,.038,.082,(-92,49,-45))
    for side in [0,1]:
        if side==0:unit('Wago615','WAGO 221-615 五位',36.5,21.3,9.8,'#dc9c49',.018,.013,.026,(-51,50,-45))
        else:put('Wago615',-51,72,-45,180)
    for x in [11,49]:
        if x==11:unit('AuxDist','五线辅助分线端 221-415',29.8,18.3,8.15,'#d69e58',.007,.005,.011,(x,64,-45))
        else:put('AuxDist',x,64,-45)
    unit('ZC7112A','吉门 ZC-7112A · ATN 插片座',45,14,29.2,'#a16754',.024,.016,.035,(-3,28,-45))
    items[-1]['rz']=90
    put('ZC7112A',16,28,-45,90)
    D['ZC7112A']['source']='吉门图纸 45×14×29.2 mm；含插片壳体估重，尾线另入线束'
    for i,(x,y) in enumerate(drivers):
        if i==0:
            driver=fuse(box(55,55,1.6),box(49,10,13,0,20,1.6),box(32,12,12,0,-15,1.6),box(30,20,5,0,0,1.6))
            define('Driver','DFRobot DRI0041 双路 7 A','接口简模',driver,'#4f8f64','DFRobot 中文手册 55×55 mm、32 g；端子高度估算',.032,.030,.035)
        put('Driver',x,y,38.5)
    unit('TXS0108E','TXS0108E 八路成品电平转换板',32,22,12,'#527e9c',.004,.002,.008,(24,-20,36))
    unit('FFC24_65','24P FFC 0.5 mm 至 2.54 mm 焊线转接板',65,27,12,'#708c58',.006,.003,.014,(68,7,36))
    # Optional second Ethernet via USB, and the dedicated Livox harness.
    define('USBnet','USB3 千兆网络适配器','布置包络',box(55,21,15),'#59626a','选装估重',.032,.020,.050)
    put('USBnet',-35,-73,121,optional=True)
    # Standard hip-to-body bolts (16 stacks), axis +X outward on the right.
    bolt=fuse(along_x(-22,0,0,2.5,22),along_x(0,0,0,4.25,5))
    nut=cq.Workplane('YZ').polygon(6,8/math.cos(math.pi/6)).extrude(5).val().cut(along_x(-1,0,0,2.05,7))
    washer=along_x(0,0,0,5,1).cut(along_x(-1,0,0,2.65,3))
    for id,n,shape in [('B5bolt','M5×22 髋座螺栓',bolt),('B5nut','M5 锁母',nut),('B5washer','M5 平垫',washer)]:
        define(id,n,'钢制紧固件',shape,'#a3b1b8')
    for s in [-1,1]:
        for y in [-75,-60,60,75]:
            for z in [-62,12]:
                for id,x in [('B5bolt',127),('B5washer',126),('B5washer',111),('B5nut',106)]:
                    put(id,s*x,y,z,0 if s==1 else 180)
    for id,n,wt,lo,hi,com,opt in [
        ('Loom','全车动力/CAN/USB/以太网线与接头',.153,.100,.230,[0,0,14],False),
        ('Hardware','其余设备紧固件、扎带、胶垫及板卡固定',.067,.044,.102,[0,0,1],False),
        ('MidHarness','MID360 分线缆与增量紧固件',.084,.052,.140,[0,-26,94],True)]:
        define(id,n,'分布质量',None,'#777777','线长及件数估算',wt,lo,hi,[0,0,0]);put(id,*com,optional=opt)
    return D,items
if not D:build()

