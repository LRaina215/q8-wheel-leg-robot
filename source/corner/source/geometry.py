from design import *
import json,math,base64,zlib
import numpy as np
import cadquery as cq
from shapely.geometry import Point,Polygon
from shapely import affinity
from itertools import combinations

def wire(loop):
    if loop[0]=='c':
        _,x,y,r=loop;return cq.Wire.makeCircle(r,cq.Vector(x,y,0),cq.Vector(0,0,1))
    return cq.Wire.makePolygon([cq.Vector(x,y,0) for x,y in loop[1]],close=True)
def shape(part):
    result=None
    for op in part['ops']:
        if op['cut']:
            # Disjoint cuts can be several circles; annular grooves are nested.
            loops=op['loops']
            nested= len(loops)==2 and all(c[0]=='c' for c in loops) and loops[0][1:3]==loops[1][1:3]
            groups=[loops] if nested else [[c] for c in loops]
        else:groups=[op['loops']]
        for loops in groups:
            ws=[wire(c) for c in loops];s=cq.Solid.extrudeLinear(ws[0],ws[1:],cq.Vector(0,0,op['h'])).translate((0,0,op['z']))
            result=s if result is None else result.cut(s) if op['cut'] else result.fuse(s)
    return result.clean()
def slice_op(op):
    result=Polygon()
    for c in op['loops']:
        s=Point(c[1],c[2]).buffer(c[3],quad_segs=48) if c[0]=='c' else Polygon(c[1])
        result=result.symmetric_difference(s)
    return result
def position(t,q):
    x,y,a=group_pose(t['g'],q);b=math.radians(a)
    return (x+math.cos(b)*t['x']-math.sin(b)*t['y'],y+math.sin(b)*t['x']+math.cos(b)*t['y'],t['z'],a+t['rot'])
def placed(s,t,q):
    x,y,z,a=position(t,q)
    if t['flip']:s=s.rotate((0,0,0),(1,0,0),180)
    if a:s=s.rotate((0,0,0),(0,0,1),a)
    return s.translate((x,y,z))
def qa_layers(start_deg=Q0,end_deg=Q1,samples=61):
    # Exact axial intervals and polygonal circle samples. Exclude fastener thread engagement.
    relevant=[t for t in INST if t['id'].startswith('P') or t['id'] in ['M01','M02','H01','H03','H04','H08','H10','S01','S02','S03','S06']]
    proto={}
    for t in relevant:
        id=t['id']
        if id in proto:continue
        ops=PARTS[id]['ops'];zs=sorted(set(round(x,6) for o in ops for x in (o['z'],o['z']+o['h'])))
        slices=[]
        for lo,hi in zip(zs,zs[1:]):
            g=Polygon()
            for o in ops:
                if o['z']<(lo+hi)/2<o['z']+o['h']:
                    h=slice_op(o);g=g.difference(h) if o['cut'] else g.union(h)
            if not g.is_empty:slices.append((lo,hi,g))
        proto[id]=slices
    pairs=[(i,j) for i,j in combinations(range(len(relevant)),2) if relevant[i]['g']!=relevant[j]['g'] and (relevant[i]['id'].startswith('P') or relevant[j]['id'].startswith('P'))]
    hits={};tested=0
    for q in np.linspace(start_deg,end_deg,samples):
        allparts=[]
        for t in relevant:
            x,y,z,a=position(t,q);sections=[]
            for lo,hi,g in proto[t['id']]:
                if t['flip']:g=affinity.scale(g,1,-1,origin=(0,0));lo,hi=-hi,-lo
                g=affinity.translate(affinity.rotate(g,a,origin=(0,0)),x,y);sections.append((lo+z,hi+z,g,g.bounds))
            allparts.append(sections)
        for i,j in pairs:
            vol=0
            for a,b,g,A in allparts[i]:
                for c,d,h,B in allparts[j]:
                    dz=min(b,d)-max(a,c)
                    if dz<.001 or A[0]>=B[2] or B[0]>=A[2] or A[1]>=B[3] or B[1]>=A[3]:continue
                    vol+=dz*g.intersection(h).area
            if vol>.04:
                k=f"{relevant[i]['id']}/{relevant[j]['id']}";hits[k]=max(hits.get(k,0),round(vol,3))
            tested+=1
    return dict(start_deg=start_deg,end_deg=end_deg,samples=samples,pairs_per_pose=len(pairs),comparisons=tested,interferences_mm3=hits)
def generate():
    meta={};meshes={};shapes={};ass=cq.Assembly()
    for id,p in PARTS.items():
        s=shape(p);assert s.isValid() and len(s.Solids())==1,id;shapes[id]=s
        b=s.BoundingBox();c=s.Center();v=s.Volume();meta[id]=dict(volume_mm3=v,center=list(c.toTuple()),bounds=[b.xlen,b.ylen,b.zlen])
        vertices,faces=s.tessellate(.16,.22)
        pts=np.array([v.toTuple() for v in vertices],dtype='<f4');idx=np.asarray(faces,dtype='<u4')
        meshes[id]=[base64.b64encode(pts.tobytes()).decode(),base64.b64encode(idx.tobytes()).decode()]
        if p['printed']:
            # The drive arm sits with its broad outward face on the bed.
            flat=s.rotate((0,0,0),(1,0,0),180) if id=='P02' else s
            box=flat.BoundingBox();flat=flat.translate((-box.xmin+3,-box.ymin+3,-box.zmin))
            cq.exporters.export(flat,str(ROOT/'A1_STL'/(id+'.stl')),tolerance=.045,angularTolerance=.12)
    for i,t in enumerate(INST):
        id=t['id'];clr=PARTS[id]['color'];rgb=[int(clr[j:j+2],16)/255 for j in (1,3,5)]
        ass.add(placed(shapes[id],t,7),name=f'{id}_{i:02d}',color=cq.Color(*rgb))
    ass.save(str(ROOT/'Q8_Single_Corner.step'))
    (ROOT/'data'/'geometry.json').write_text(json.dumps(meta,indent=2))
    (ROOT/'data'/'mesh.bin').write_bytes(zlib.compress(json.dumps(meshes,separators=(',',':')).encode(),8))
    checks=qa_layers();(ROOT/'data'/'clearance.json').write_text(json.dumps(checks,indent=2));print(checks,flush=True)
if __name__=='__main__':generate()
