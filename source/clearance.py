from layout import *
from geometry import shape as legshape
from itertools import combinations
from OCP.gp import gp_Trsf
def rigid(s,M,p):
    tr=gp_Trsf();a=np.column_stack([M,p]).ravel();tr.SetValues(*map(float,a));return s.located(cq.Location(tr))
def bounds(s):
    b=s.BoundingBox();return np.array([[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]])
def meet(a,b,tol=.015):return min(np.minimum(a[1],b[1])-np.maximum(a[0],b[0]))>tol
def main():
    body=[];meta=read(ROOT/'data'/'layout.json')['parts'];entries={};risk=[]
    for t in items:
        id=t['id'];sh=D[id]['shape'];p=meta[id]
        if sh is None:
            if p['kind']=='分布质量':continue
            if id in ['XT_M60','Astra_Pro_Plus','Tattu_2200_6S']:sh=cq.Shape.importBrep(str(LIB/id/(id+'_layout.brep')))
            else:
                l,h=np.array(p['bbox']);sh=box(*(h-l),*(.5*(h+l))[:2],l[2])
        s=rigid(sh,xyzrot(t['rz']),t['pos']);body.append((t['name'],s,bounds(s)))
    for (ida,sa,a),(idb,sb,b) in combinations(body,2):
        if meet(a,b):
            # Detailed kit CAD conservatively boxed above; board standoffs terminate at the PCB plane.
            if {ida.split('_')[0],idb.split('_')[0]}=={'Msp','MC02'}:continue
            if {ida.split('_')[0],idb.split('_')[0]}=={'B5bolt','B5nut'} and np.max(np.abs(a.mean(0)[1:]-b.mean(0)[1:]))<.1:continue
            volume=sa.intersect(sb).Volume()
            if volume>.25:risk.append([ida,idb,round(volume,2)])
    print('central',risk,flush=True)
    # All leg solids; using conservative oriented boxes as broad phase, then exact BRep.
    solids={id:legshape(p) for id,p in leg.PARTS.items()};keys={};top=0;contacts=0
    leg_gaps=[1e6,1e6]
    for q in np.linspace(-36,33,70):
        ext={}
        for name,side,front in corner_order:
            hand=side*front;M=leg_basis(side)@np.diag([hand,1,1]);pos=np.array([side*HX,front*HY,0])
            for i,t in enumerate(leg.INST):
                id=t['id'];g=t['g'];x,y,ang=leg.group_pose(g,q);R=xyzrot(ang);J=R@xyzrot(t['rot'])@np.diag([1,-1 if t['flip'] else 1,-1 if t['flip'] else 1])
                P=M@(np.array([x,y,0])+R@np.array([t['x'],t['y'],t['z']]))+pos;T=M@J
                proto=solids[id];bb=entries.setdefault(id,bounds(proto)) if id not in entries else entries[id]
                ends=np.array([[xx,yy,zz] for xx in bb[:,0] for yy in bb[:,1] for zz in bb[:,2]])@T.T+P
                ab=np.array([ends.min(0),ends.max(0)])
                if name not in ext:ext[name]=ab.copy()
                else:ext[name]=np.array([np.minimum(ext[name][0],ab[0]),np.maximum(ext[name][1],ab[1])])
                for bid,bs,bbox in body:
                    if not meet(ab,bbox):continue
                    if id=='S01' and bid.startswith('Chassis') and t['g']=='base':pass
                    sig=(name,i,bid,round(q,1) if g!='base' else 'base')
                    if sig in keys:continue
                    keys[sig]=1;top+=1
                    if np.linalg.det(T)<0:s=rigid(proto.mirror('YZ'),T@np.diag([-1,1,1]),P)
                    else:s=rigid(proto,T,P)
                    vol=s.intersect(bs).Volume()
                    if vol>.25:risk.append([name,id,bid,round(q,1),round(vol,2)])
        leg_gaps[0]=min(leg_gaps[0],*(ext[b][0,0]-ext[a][1,0] for a,b in [('FL','FR'),('RL','RR')]))
        leg_gaps[1]=min(leg_gaps[1],*(ext[a][0,1]-ext[b][1,1] for a,b in [('FL','RL'),('FR','RR')]))
    assert min(leg_gaps)>0,leg_gaps
    print('narrow',top,'hits',risk[:28],flush=True);write(ROOT/'data'/'clearance.json',dict(poses=70,range=[-36,33],narrow_phase_tests=top,body_pairs=len(body)*(len(body)-1)//2,between_legs_min_separating_bounds_mm=leg_gaps,intersections=risk,scope='Rigid chassis/cargo against the selected wheel legs; fastener thread engagement and MC02 standoff-to-board fit excluded. Cable sweeps, deflection and manufacturing variability not modelled.'))
if __name__=='__main__':main()

