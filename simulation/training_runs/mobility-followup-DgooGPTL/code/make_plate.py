"""Build four conservative convex prisms enclosing the R5 P01 triangulation."""
import base64,gzip,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

def outline(points):
    pts=sorted(set(map(tuple,points)))
    def chain(items):
        half=[]
        for p in items:
            while len(half)>=2:
                a,b=half[-2:]
                cross=(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
                if cross>0.:break
                half.pop()
            half.append(p)
        return half
    return np.asarray(chain(pts)[:-1]+chain(reversed(pts))[:-1])
def main():
    exp=Path(__file__).resolve().parent.parent
    root=exp/'plate_ab'
    src=root/'code'/'q8_r5_fitted.xml'
    tree=ET.parse(src)
    cad=exp.parent/'ppo-highjump-fUGFdEDX'/'step_video'/'render_meshes.json.gz'
    with gzip.open(cad,'rt') as f:source=json.load(f)
    xyz=np.frombuffer(base64.b64decode(source['mesh']['P01'][0]),'<f4').reshape(-1,3).astype(float)
    hull=outline(xyz[:,:2]);z=xyz[:,2]
    prism=np.concatenate([np.column_stack([hull,np.full(len(hull),v)]) for v in (z.min(),z.max())])
    asset=tree.find('asset')
    if asset is None:
        asset=ET.Element('asset');tree.getroot().insert(1,asset)
    counts={}
    for leg,f,s in [('FL',1,1),('FR',1,-1),('RL',-1,1),('RR',-1,-1)]:
        axes=np.array([[f,0,0],[0,0,s],[0,1,0]])
        x=(prism@axes.T+np.array([f*112,s*119,0]))*.001
        actual=(xyz@axes.T+np.array([f*112,s*119,0]))*.001
        g=tree.find(f".//geom[@name='{leg}_P01']")
        size=np.fromstring(g.attrib.pop('size'),sep=' ');pos=np.fromstring(g.attrib['pos'],sep=' ')
        if max(abs(x.min(0)-pos+size).max(),abs(x.max(0)-pos-size).max())>5.e-6:raise ValueError(leg)
        mesh=leg+'_P01_outline'
        ET.SubElement(asset,'mesh',name=mesh,vertex=' '.join(f'{v:.10f}' for v in (x-pos).ravel()))
        g.set('type','mesh');g.set('mesh',mesh)
        counts[leg]=len(x)
    tree.write(src,encoding='utf-8',xml_declaration=True)
    (root/'plate_spec.json').write_text(json.dumps(dict(vertices_per_plate=counts,source_points=len(xyz),outline_points=len(hull),method='outer planar convex hull extruded across full plate thickness; holes and inward recesses filled',others='all other collision shapes, inertias, joint ranges and motor limits preserved')))
if __name__=='__main__':main()
