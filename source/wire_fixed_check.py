from wire_check import Surface,dense
from wire_space import *
D=ROOT/'data';db=read(D/'整车线束.json');layout=read(D/'layout.json');body=meshes('bodymesh.bin')
def owned(node,k):
    if node in ('BAT','BAL'):return k=='Tattu_2200_6S'
    if node.startswith(('F40','Fw','Fe')):return k==('ANS_H' if node.startswith('F40') else 'ZC7112A')
    if node.startswith(('HP','HN','AP','AN')):return k==('Wago615' if node[0]=='H' else 'AuxDist')
    if node[:2] in ('Bi','Bo','Fi','Fo'):return k=='YourCee20'
    if node[:2] in ('Ai','Ao'):return k=='AuxBuck'
    if node.startswith(('JUSB','JDC','JLAN')):return k=='Jetson_Orin_Nano'
    if node in ('MCp','MCusb','FFC1','MC3','MC5','Lpwm','Rpwm','Lcan','Rcan'):return k=='MC02'
    if node in ('LV+','LV-','RV+','RV-','LM1','LM2','RM1','RM2','Lctrl','Rctrl'):return k=='Driver'
    if node.startswith('TX'):return k=='TXS0108E'
    if node in ('Break','Bhdr'):return k=='FFC24_65'
    if node=='XTtail':return k=='XT_M60'
    if node=='AST':return k=='Astra_Pro_Plus'
    if node=='MID':return k=='MID360'
    if node in ('NetU','NetE'):return k=='USBnet'
    return False
parts={k:Surface(p,i) for k,(p,i) in body.items()}
notes=[]
for r in db['routes']:
    if 'frames' in r:continue
    pp=dense(r['points']);rad=r['dia']/2
    for t in layout['instances']:
        k=t['id']
        if k not in parts:continue
        keep=np.ones(len(pp),bool)
        for n,pt in [(r['a'],pp[0]),(r['b'],pp[-1])]:
            if owned(n,k):keep &= np.linalg.norm(pp-pt,axis=1)>20
        sel=pp[keep]
        if not len(sel):continue
        v=parts[k].gap((sel-t['pos'])@xyzrot(t['rz']),rad+1)-rad
        if v<0:notes.append([r['id'],r['a'],r['b'],t['name'],round(v,2)])
write(D/'固定线束复核.json',dict(separation_exceptions=notes,step_mm=1,plug_zone_mm=20))
print('fixed contacts',notes,flush=True)
