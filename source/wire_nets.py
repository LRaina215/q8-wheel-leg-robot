"""Q8 R4 design pin/net schedule; nominal lead exits in chassis mm."""
import numpy as np
nodes={};routes=[]
def port(key,label,p,d=(0,0,1),lead=5):
    nodes[key]=dict(label=label,p=list(p),d=list(d),lead=lead)
def net(a,b,group,cores,dia,stock,via=(),optional=False,detail=''):
    assert a in nodes and b in nodes
    routes.append(dict(id='W%02d'%(len(routes)+1),a=a,b=b,group=group,cores=cores,dia=dia,stock=stock,via=list(via),optional=optional,detail=detail))
def pin(key,label,x,y,z,dx=0,dy=0,dz=1,lead=6):
    port(key,label,(x,y,z),(dx,dy,dz),lead)
P='6S 动力';W='12V 轮驱';A='15V 设备';L='控制与编码';C='CAN';U='USB / 以太网';M='腿部活动束'
pin('BAT','电池自带主线根部',-31,-80,-20,0,-1,0)
pin('XT','XT60 车端',-51,-78,-12,-1,0,0)
net('BAT','XT',P,'红正、黑负（原厂双芯）',6,'随电池')
pin('BAL','电池平衡口根部',-38,-80,-14,0,-1,0)
pin('PARK','7P 平衡插头停车绑位',-61,-70,1)
net('BAL','PARK',P,'B−、B1–B6，共 7 芯，行驶时绝缘收妥',4,'随电池')
pin('F40i','40A 主保险 · 电池端',-92,31,-19)
pin('F40o','40A 主保险 · 负载端',-92,67,-19)
pin('JP','保险后正极绝缘压接点',-74,42,-6)
pin('JN','电池负极绝缘压接点',-74,27,-7)
net('XT','F40i',P,'正极',4.3,'12AWG')
net('XT','JN',P,'负极',4.3,'12AWG')
net('F40o','JP',P,'正极',4.3,'12AWG')
for tag,x,rating in [('Fw',-3,'25A 轮驱'),('Fe',16,'7.5A 设备')]:
    pin(tag+'i',rating+'保险输入',x,5.5,-31,0,-1,0)
    pin(tag+'o',rating+'保险输出',x,50.5,-31,0,1,0)
    net('JP',tag+'i',P,'正极',4.3 if tag=='Fw' else 2.8,'12AWG' if tag=='Fw' else '18AWG')
pin('J12','轮驱保险后正极一分二',15,53,-13)
net('Fwo','J12',P,'正极',4.3,'12AWG')
for tag,y in [('B',-45),('F',19)]:
    for end,x,d,sgn in [('i',31,-1,-1),('o',91,1,1)]:
        for pol,off in [('+',4),('-',-4)]:
            pin(tag+end+pol,('后板' if tag=='B' else '前板')+(' IN' if end=='i' else ' OUT')+pol,x,y+off*sgn,-34,d,0,0,7)
    net('J12',tag+'i+',P,'输入正极',3.1,'16AWG');net('JN',tag+'i-',P,'输入负极',3.1,'16AWG')
# WAGO five independent positions on each rail. Plane of terminal openings is approximate.
for base,y in [('HP',50),('HN',72),('AP',64),('AN',64)]:
    for i in range(5):
        x=(-51+(i-2)*6.5) if base[0]=='H' else ((11 if base=='AP' else 49)+(i-2)*5.2)
        pin(base+str(i),{'HP':'髋正排','HN':'髋负排','AP':'15V 正排','AN':'15V 负排'}[base]+f' · 孔{i+1}',x,y+(10.65 if base=='HN' else -10.65 if base=='HP' else -9.15),-40,0,1 if base=='HN' else -1,0,5)
net('JP','HP0',P,'6S 正极',4.3,'12AWG');net('JN','HN0',P,'6S 负极',4.3,'12AWG')
for key,y in [('Ai',-66),('Ao',-8)]:
    for sign,dx in [('+',-4),('-',4)]:pin(key+sign,'恩珀 '+('输入' if key=='Ai' else '15V 输出')+sign,-81+dx,y,-35,0,-1 if key=='Ai' else 1,0,7)
net('Feo','Ai+',A,'输入正极',2.6,'18AWG');net('JN','Ai-',A,'输入负极',2.6,'18AWG')
net('Ao+','AP0',A,'15V 正极',2.6,'18AWG');net('Ao-','AN0',A,'15V 返回',2.6,'18AWG')
for k,x in [('JDC',-93),('JUSB1',-57),('JUSB2',-40),('JUSB3',-57),('JLAN',-23)]:
    label={'JDC':'Jetson DC5525','JUSB1':'Jetson USB-A 1 · 相机','JUSB2':'Jetson USB-A 2 · 主控','JUSB3':'Jetson USB-A 3 · 选装网卡','JLAN':'Jetson RJ45'}
    pin(k,label[k],x,-65,60 if k=='JUSB3' else 51,0,-1,0,16)
pin('MCp','MC02 电源入口',36,-69,49,-1,0,0,10)
pin('MCusb','MC02 USB-C 数据口',61,-32,47,0,1,0,12)
pin('XTtail','XT-M60 原厂尾接头',0,53,99,0,-1,0,12)
pin('XTsplit','XT-M60 原厂分线缆分叉点',11,35,86)
pin('AST','Astra 原装 USB 出线（定位估计）',32,109.2,52,0,-1,0,10)
pin('MID','MID-360 M12',0,-79,154,0,-1,0,18)
pin('MIDsplit','MID-360 原厂一分三分叉点',6,-94,115)
pin('MIDs','MID 同步/备用尾线绝缘收纳点',20,-80,106)
pin('NetU','RTL8153 · USB 线端',-62.5,-73,128,-1,0,0)
pin('NetE','RTL8153 · RJ45',-7.5,-73,128,1,0,0,12)
for i,(dock,label) in enumerate([('JDC','Jetson DC 插头'),('MCp','MC02 电源插头'),('XTsplit','XT 原厂供电'),('MIDsplit','MID 原厂供电')],1):
    for root,sign in [('AP','+'),('AN','−')]:
        net(root+str(i),dock,A,'15V '+sign+('，中心正' if dock=='JDC' else ''),2.6,'18AWG',optional=i==4,detail=label)
net('XTtail','XTsplit',U,'原厂供电＋以太网复合干线',5,'成品')
net('XTsplit','JLAN',U,'XT 以太网，RJ45',5.4,'网线')
net('AST','JUSB1',U,'USB 2.0 数据、5V、GND，原装线',4.8,'成品')
net('MCusb','JUSB2',U,'USB D+/D−、VBUS、GND，主控与上位机双向数据',3.8,'USB数据')
net('MID','MIDsplit',U,'原厂 M12 复合线',6.2,'成品',optional=True)
net('MIDsplit','NetE',U,'雷达以太网',5.5,'网线',optional=True)
net('MIDsplit','MIDs',U,'未启用的时间同步支线，末端绝缘',3,'成品',optional=True)
net('NetU','JUSB3',U,'USB 3 数据与总线供电',4.5,'成品',optional=True)
pin('FFC1','MC02 FFC1 相机扩展口',80,-72,49,0,-1,0,7)
pin('Break','24P 细距排线座',68,-6.5,43,0,-1,0)
net('FFC1','Break',L,'24P 0.5 mm 同向 FFC；沿右后设备板留平缓服务弯',12.5,'FFC',via=[(95,-91,69),(103,-58,88),(103,8,88),(79,12,72)])
pin('MC3','MC02 SWD 3V3 + GND',75,-34,48,0,1,0)
pin('MC5','MC02 受控 5V + GND',47,-33,50,0,1,0)
pin('E5','5V 编码器电源星点',16,-28,58)
pin('TXa','TXS0108E A 侧',9,-20,44,0,0,1,20)
pin('TXb','TXS0108E B 侧',40,-20,44,1,0,0)
pin('Bhdr','24P 转接输出排针',68,20.5,44,0,1,0)
net('MC3','TXa',L,'3V3→VCCA、OE 本端接 VCCA；GND',2.3,'信号2')
net('MC5','E5',L,'可控 5V、GND',2.3,'信号2')
net('E5','TXb',L,'5V→VCCB、GND',2.3,'信号2')
net('TXa','Bhdr',L,'A1–A8→FFC1 6/4、3/5、7/11、9/13，共8芯',4.0,'信号8')
for side,x,y,buck in [('L',-65,65,'B'),('R',63,58,'F')]:
    for key,dx in [('V+',-20),('V-',-12),('M1',0),('M2',16)]:
        pin(side+key,('左' if side=='L' else '右')+' DRI0041 '+{'V+':'电源＋','V-':'PGND','M1':'OUT1/2 前轮','M2':'OUT3/4 后轮'}[key],x+dx,y+25,47,0,1,0,9)
    net(buck+'o+',side+'V+',W,'12V 正极，独立支路',3.1,'16AWG')
    net(buck+'o-',side+'V-',W,'PGND，独立支路',3.1,'16AWG')
    pin(side+'ctrl',('左' if side=='L' else '右')+' DRI0041 控制排针',x,y-21,47,0,-1,0,6)
    net('Bhdr',side+'ctrl',L,'IN1/2/3/4 ← FFC1 '+('8/12/18/19' if side=='L' else '16/17/20/22'),3,'信号4')
    net('MC3',side+'ctrl',L,'单芯 VREF 3V3 → 光耦公共参考脚；PGND 从本路降压板返回',1.5,'信号1')
    pin(side+'pwm','MC02 '+('PE13、PA2' if side=='L' else 'PE9、PA0')+' 两路 PWM',82 if side=='L' else 85,-32,48,0,1,0,6)
    net(side+'pwm',side+'ctrl',L,'ENA/ENB：'+('PE13/PA2' if side=='L' else 'PE9/PA0'),2.3,'信号2')
    s=-1 if side=='L' else 1
    pin(side+'can','MC02 CAN'+('1' if side=='L' else '2')+' H/L',36,-59 if side=='L' else -48,49,-1,0,0,7)
    for f,t in [(1,'F'),(-1,'R')]:
        tag=t+side;order=['FL','FR','RL','RR'].index(tag)
        for sign,dy,g in [('+',-4,'HP'),('-',4,'HN')]:
            pin(tag+sign,tag+' 髋尾线 XT30(2+2) '+sign,s*65.7,f*(112+dy),-2,-s,0,0,7)
            net(g+str(order+1),tag+sign,P,'髋动力 '+sign,3.1,'16AWG')
        pin(tag+'can',tag+' 髋 CAN H/L 线束接续',s*61,f*112,7,-s,0,0,5)
        pin(tag+'root',tag+' 固定侧耳下排 M5 上方软垫绑点',s*134,f*75,-52,0,-f,0,5)
        net(side+('M1' if f==1 else 'M2'),tag+'root',W,'轮机 M+、M−，分色标记',4.3,'动力2')
        net('TXb',tag+'root',L,'编码器 A/B → B'+str(order*2+1)+'/B'+str(order*2+2),2.5,'信号2')
        net('E5',tag+'root',L,'编码器 5V / GND',2.5,'信号2')
        pin(tag+'motor',tag+' FIT0403 电机尾部电枢及编码器',s*54,f*(112+110),-117,-s,0,0)
        net(tag+'root',tag+'motor',M,'同行护套：M+/M−、5V/GND、A/B，6芯',8,'活动6',detail='两端绑点、随从动臂摆动；端接电机定子')
    net(side+'can','F'+side+'can',C,'CAN-H、CAN-L 双绞，MC02 端终端按实装配置',2.4,'CAN2')
    net('F'+side+'can','R'+side+'can',C,'H 对 H、L 对 L；后髋线束末端 120Ω，确认内置端接后配置',2.4,'CAN2')
