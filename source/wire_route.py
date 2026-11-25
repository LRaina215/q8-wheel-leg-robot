"""Route insulated harness bundles with 3-D clearance to the assembled chassis and leg sweep."""
from wire_space import *
from wire_nets import nodes,routes,M
from scipy.ndimage import map_coordinates
from scipy.interpolate import PchipInterpolator
from scipy.spatial.distance import cdist
from numba import njit
import heapq,csv
static,swept=fields()
# Discourage excursions from equipment bay, and leave the Jetson fan intake open.
X,Y,Z=np.meshgrid(*(origin[i]+step*np.arange(dims[i]) for i in range(3)),indexing='ij',sparse=True)
extra=(.5*np.maximum(0,np.abs(X)-106)/60+.55*np.maximum(0,np.abs(Y)-90)/60+.4*np.maximum(0,Z-83)/60+1.5*((X>-82)&(X<-20)&(Y>-31)&(Y<14)&(Z>74)&(Z<110))).astype('f')
crowd=np.zeros(dims,np.float32)
occupied=np.full(dims,100.,np.float32)
OFF=np.array([(x,y,z) for x in [-1,0,1] for y in [-1,0,1] for z in [-1,0,1] if (x,y,z)!=(0,0,0)],dtype=np.int64)
DL=np.sqrt(np.sum(OFF**2,axis=1))
@njit
def route_grid(field,extra,crowd,src,dst,radius):
    nx,ny,nz=field.shape
    cost=np.full((nx,ny,nz),np.float32(np.inf),np.float32)
    back=np.full((nx,ny,nz),-1,np.int8)
    closed=np.zeros((nx,ny,nz),np.uint8)
    x,y,z=src;tx,ty,tz=dst;cost[x,y,z]=0
    queue=[(0.,0.,x,y,z)]
    while queue:
        _,g,x,y,z=heapq.heappop(queue)
        if closed[x,y,z]:continue
        closed[x,y,z]=1
        if x==tx and y==ty and z==tz:break
        for j in range(26):
            dx,dy,dz=OFF[j];xx=x+dx;yy=y+dy;zz=z+dz
            if xx<1 or yy<1 or zz<1 or xx>=nx-1 or yy>=ny-1 or zz>=nz-1:continue
            if closed[xx,yy,zz]:continue
            d=field[xx,yy,zz]
            if d<radius+4.8:continue
            ng=g+DL[j]*(1.+extra[xx,yy,zz]+.45*max(0.,radius+8.-d)+crowd[xx,yy,zz])
            if np.float32(ng)>=cost[xx,yy,zz]:continue
            cost[xx,yy,zz]=ng;back[xx,yy,zz]=j
            h=((tx-xx)**2+(ty-yy)**2+(tz-zz)**2)**.5
            heapq.heappush(queue,(ng+h,ng,xx,yy,zz))
    out=[(tx,ty,tz)];x,y,z=dst
    while (x!=src[0] or y!=src[1] or z!=src[2]):
        j=back[x,y,z]
        if j<0:break
        x-=OFF[j,0];y-=OFF[j,1];z-=OFF[j,2];out.append((x,y,z))
    return out
def length(p):return float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
def samples(p,spacing=1.5):
    p=np.array(p,float);ds=np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1).cumsum()]
    keep=np.r_[True,np.diff(ds)>.001];ds=ds[keep];p=p[keep]
    d=np.linspace(0,ds[-1],max(2,1+int(np.ceil(ds[-1]/spacing))))
    return np.column_stack([np.interp(d,ds,p[:,j]) for j in range(3)])
def rounded(p,repeat=2):
    p=np.array(p,float)
    for _ in range(repeat):
        mid=np.stack([.75*p[:-1]+.25*p[1:],.25*p[:-1]+.75*p[1:]],axis=1).reshape(-1,3)
        p=np.vstack([p[0],mid,p[-1]])
    return p
def anchor(n,r):
    p=np.array(n['p']);d=np.array(n['d']);q=p+d*n['lead'];center=np.rint((q-origin)/step).astype(int)
    ii=np.array(np.meshgrid(*[np.arange(v-9,v+10) for v in center],indexing='ij')).reshape(3,-1).T
    ok=(swept[tuple(ii.T)]>=r+5);ii=ii[ok]
    xyz=origin+ii*step;score=np.linalg.norm(xyz-q,axis=1)+5*np.maximum(0,-(xyz-p)@d)
    i=np.argmin(score);return ii[i],xyz[i]
def simplify(xyz,r,field):
    output=[xyz[0]];i=0
    while i<len(xyz)-1:
        end=i+1
        for j in range(i+2,min(i+16,len(xyz))):
            if distances(field,samples([xyz[i],xyz[j]],2)).min()<r+4.5:break
            end=j
        output.append(xyz[end]);i=end
    return np.array(output)
def fixed(net):
    r=net['dia']/2
    n1,n2=nodes[net['a']],nodes[net['b']]
    a,pa=anchor(n1,r);b,pb=anchor(n2,r)
    # Existing harnesses occupy space. At a termination several cores can enter
    # the same connector shell or sleeve. Outside those zones keep separate lanes.
    clearance=np.minimum(swept,occupied+2.8)
    for p in [n1['p'],n2['p']]:
        v=np.rint((np.array(p)-origin)/step).astype(int)
        sl=tuple(slice(i-8,i+9) for i in v)
        clearance[sl]=swept[sl]
    anchors=[a]
    for xyz in net['via']:
        grid,_=anchor(dict(p=xyz,d=[0,0,0],lead=0),r)
        anchors.append(grid)
    anchors.append(b)
    chunks=[]
    for start,end in zip(anchors,anchors[1:]):
        piece=np.array(route_grid(clearance,extra,crowd,start,end,r))[::-1]
        assert np.array_equal(piece[0],start),(net['id'],start,end)
        chunks.append(piece if not chunks else piece[1:])
    indexes=np.vstack(chunks)
    grid=origin+indexes*step
    for off in [(0,0,0),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
        u=indexes+off;np.add.at(crowd,tuple(u.T),.42 if off==(0,0,0) else .13)
    mid=simplify(grid,r,clearance)
    smooth=rounded(mid)
    if distances(clearance,samples(smooth)).min()<r+4.:smooth=mid
    p=np.vstack([n1['p'],smooth,n2['p']])
    net['fixed_mm']=round(length(p),1)
    net['points']=samples(p,3.5).round(2).tolist()
    net['core_gap']=round(float(distances(swept,samples(smooth)).min()-r-2.60),2)
    net['exit_mm']=[round(float(np.linalg.norm(pa-n1['p'])),1),round(float(np.linalg.norm(pb-n2['p'])),1)]
    for pt in samples(p,2.0):
        v=np.rint((pt-origin)/step).astype(int);sl=tuple(slice(i-4,i+5) for i in v)
        u=np.ogrid[-4:5,-4:5,-4:5];off=origin+v*step-pt
        dist=np.sqrt(sum((u[k]*step+off[k])**2 for k in range(3)))-r
        occupied[sl]=np.minimum(occupied[sl],dist)
    return net
def moving(q,side,fore,bulge):
    a=np.radians(q);c=np.cos(a);s=np.sin(a)
    def arm(t,h):return [154 if t<40 or t>95 else 146,112+t*c+h*s,-62-t*s+h*c]
    root=np.array([134,75,-52]);first=np.array(arm(29,0))
    t=np.linspace(0,1,25)[:,None]
    h1=root+[27,6,bulge];h2=first+[0,-12*c,bulge+12*s]
    loop=(1-t)**3*root+3*t*(1-t)**2*h1+3*t*t*(1-t)*h2+t**3*first
    y=112+110*c;z=-110*s
    mid=[arm(62,0),arm(91,0),arm(104,0),[155,y+18,z-64],[154,y+33,z-78],[140,y+37,z-99],
         [103,y+37,z-112],[61,y+33,z-114],[45,y+23,z-117],[43,y+8,z-117],[47,y,z-117],[54,y,z-117]]
    points=rounded(np.vstack([loop,mid]),2);points[:,0]*=side;points[:,1]*=fore;return points
def motion(net):
    tag=net['a'][:2];s=1 if tag[1]=='R' else -1;f=1 if tag[0]=='F' else -1
    qs=list(range(-36,34))
    goal=max(length(moving(q,s,f,12)) for q in qs)+4
    frames=[]
    for q in qs:
        lo,hi=12.,88.
        for _ in range(22):
            v=(lo+hi)/2
            if length(moving(q,s,f,v))<goal:lo=v
            else:hi=v
        pts=moving(q,s,f,(lo+hi)/2)
        assert abs(length(pts)-goal)<.03
        dense=samples(pts,.65);u=np.linspace(0,len(dense)-1,100)
        frames.append(np.column_stack([np.interp(u,np.arange(len(dense)),dense[:,i]) for i in range(3)]).round(2).tolist())
    net.update(frames=frames,points=frames[29],fixed_mm=round(goal,1))
def main():
    for net in routes:
        if net['group']==M:motion(net)
        else:fixed(net)
        # Always retain enough for termination; factory connectors are ordered complete.
        net['cut']=int(np.ceil((net['fixed_mm']*1.07+16)/10)*10)
        print(net['id'],net['a'],net['b'],net['fixed_mm'],flush=True)
    write(data/'整车线束.json',dict(nodes=nodes,routes=routes,step=step,angle=[-36,33]))
if __name__=='__main__':main()
