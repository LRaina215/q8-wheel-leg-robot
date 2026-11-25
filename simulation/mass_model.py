"""Build the fitted R5 mass ledger, part-explicit URDF and equivalent rigid-body MJCF."""
from pathlib import Path
import base64,csv,json,re,sys,zlib
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from functools import lru_cache
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"source"))
from r5_instances import records,old,ids,matrix
from common import leg
from build_model import vec
def load(n):return json.loads((ROOT/"data"/n).read_text(encoding="utf8"))
ledger={i["id"]:i for i in load("质量审计.json")}
body=json.loads(zlib.decompress((ROOT/"data/bodymesh.bin").read_bytes()))
limb=json.loads(zlib.decompress((ROOT/"data/legmesh.bin").read_bytes()))
cad_to_ros=np.array([[0,1,0],[-1,0,0],[0,0,1]])
printed={"Deck","Chassis","BuckTray","JetClamp","Bridge_tray","XT_saddle","Astra_saddle","MID_fit"}
rows=[]
@lru_cache(None)
def geom(k,location):
    if location=="new":
        import cadquery as cq
        sh=cq.importers.importStep(str(ROOT/"source/body_step"/("R5_"+k+".step"))).val()
        vertices,tri=sh.tessellate(.04,.12)
        mesh=trimesh.Trimesh([v.toTuple() for v in vertices],np.array(tri),process=True)
        exact=sh.Volume(); center=np.array(sh.Center().toTuple())/1000
    else:
        raw=(limb if location=="leg" else body)[k]
        verts=np.frombuffer(base64.b64decode(raw[0]),"<f4").reshape(-1,3)
        faces=np.frombuffer(base64.b64decode(raw[1]),"<u4").reshape(-1,3)
        mesh=trimesh.Trimesh(verts,faces,process=True)
        exact=abs(mesh.volume);center=mesh.center_mass/1000
    I=mesh.moment_inertia/max(abs(mesh.volume),1e-10)*1e-6*np.sign(mesh.volume)
    if not np.all(np.isfinite(center)) or min(np.linalg.eigvalsh(I))<=0:
        center=mesh.bounds.mean(axis=0)/1000;v=(mesh.extents/1000)**2;I=np.diag((v.sum()-v)/12)
    return exact,center,I
def put(k,name,link,m,c,I,grade,note,opt=False):
    if m<=0:return
    rows.append(dict(key=k,name=name,link=link,kg=float(m),c=np.array(c),I=np.array(I)*m,grade=grade,note=note,opt=opt))
def grade(k):return ledger.get(k,{}).get("grade","项目估算")
def boxI(v):
    v=np.array(v)**2
    return np.diag((v.sum()-v)/12)
def form():
    for t in records:
        k=t["id"];p=old["parts"].get(k,{})
        volume,c,I=geom(k,"new" if k in ids else "body")
        rot=cad_to_ros@matrix(t)
        if k in ids:
            density=1.04 if k in printed else 2.7 if k in ["Xsp","Lsp100"] else 7.85
            m=volume*density/1e6
            g="R5 STEP体积估算";note=f"有效密度 {density} g/cm³；无实物称重"
        else:
            m=p["mass"];g=grade(k);note=ledger.get(k,{}).get("note",p.get("source",""))
            if k=="Jetson_Orin_Nano":note+="；本行包含12 g SSD留量"
            c=np.array(p["com"])/1000
        put(k,t["name"],"chassis",m,cad_to_ros@np.array(t["pos"])/1000+rot@c,rot@I@rot.T,g,note,t["optional"])
    for n,f,s in [("FL",1,-1),("FR",1,1),("RL",-1,-1),("RR",-1,1)]:
        axes=np.array([[f,0,0],[0,0,-s],[0,1,0]])
        for i,t in enumerate(leg.INST):
            k=t["id"];grp=t["g"]
            if k=="Rotor4310":volume,c,I=1.,np.array([0,0,-.0025]),boxI([.035,.035,.005])
            else:volume,c,I=geom(k,"leg")
            rot=Rotation.from_euler("z",t["rot"],degrees=True).as_matrix()@np.diag([1,-1,-1] if t["flip"] else [1,1,1])
            rr=axes@rot
            local=axes@(np.array([t["x"],t["y"],t["z"]])/1000)+rr@c
            if grp=="base":local+=np.array([f*.112,-s*.119,0])
            elif grp=="wheel":local-=np.array([0,-s*.086,-.110])
            link="chassis" if grp=="base" else n+"_"+dict(drive="hip",passive="follower",carrier="carrier",wheel="wheel")[grp]
            if k in ("M01","Rotor4310"):
                m=.350 if k=="M01" else .020;g="厂家整机质量的工程拆分";note="每角合计370 g，输出法兰暂分20 g"
            elif k in ("XT100_Tyre","XT100_Rim"):
                m=.058 if k.endswith("Tyre") else .020;g="商品标重的工程拆分";note="软胎与ABS轮辋合计78 g，铜接头另计"
            else:
                r=ledger[k];m=r["g"]/1000;g=r["grade"];note=r["note"]
            put(k,n+"_"+k+"_"+str(i),link,m,local,rr@I@rr.T,g,note)
    wiring=load("R5_wiring.json")["routes"]
    oldroutes=load("整车线束.json")["routes"]
    for r in wiring:
        m=r["harness_g"]/1000
        if not m:continue
        p=np.array(r["points"])@cad_to_ros.T/1000
        if "frames" in r:
            frames=r["frames"];p=np.array(frames[min(29,len(frames)-1)])@cad_to_ros.T/1000
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1);mid=(p[:-1]+p[1:])/2
        slices=[(np.ones(len(ds),bool),"chassis",np.zeros(3))]
        if "frames" in r:
            n=r["a"][:2];f=1 if n[0]=="F" else -1;s=-1 if n[1]=="L" else 1
            a=np.radians(-7);C=np.array([f*(.112+.110*np.cos(a)),-s*.119,-.11*np.sin(a)])
            mask=(np.cumsum(ds)-ds/2)<ds.sum()/2
            slices=[(mask,"chassis",np.zeros(3)),(~mask,n+"_carrier",C)]
        for mask,link,offset in slices:
            if not np.any(mask):continue
            seg=mid[mask];c=np.average(seg,axis=0,weights=ds[mask]);v=seg-c
            cov=(v.T*ds[mask])@v/ds[mask].sum();I=cov.trace()*np.eye(3)-cov+np.eye(3)*1e-6
            put("Wire",r["id"]+"_"+link,link,m*ds[mask].sum()/ds.sum(),c-offset,I,"线束估算","R5走线质量；活动束按弧长对半分配到车身和轮架",r["optional"])
    oldfixed=sum(r["harness_g"] for r in oldroutes if not r["optional"] and "frames" not in r)/1000
    residual=max(0,old["parts"]["Loom"]["mass"]-oldfixed)
    put("Connectors","Fixed_loom_allowance","chassis",residual,[.011,0,.024],boxI([.16,.19,.04]),"装车估算","原固定线束总计扣除路径质量后的接插件余量")
    explicit=sum(r["kg"] for r in rows if not r["opt"] and (r["key"].startswith(("Nut","Flat")) or re.fullmatch(r"B[234]x\d+",r["key"])))
    remaining=max(0.,old["parts"]["Hardware"]["mass"]-explicit)
    put("Misc","Straps_pads_misc","chassis",remaining,[0,0,.001],boxI([.16,.2,.04]),"装车估算","78 g原安装辅料包扣除本版已单列的新增螺钉、螺母；含软垫和绑带")
    mid_budget=next(t for t in old["instances"] if t["id"]=="MidHarness")
    mid_explicit=sum(r["kg"] for r in rows if r["opt"] and (r["key"]=="Wire" or re.fullmatch(r"B[234]x\d+",r["key"])))
    put("MidHarness","Optional_stock_cable_allowance","chassis",max(0,old["parts"]["MidHarness"]["mass"]-mid_explicit),
        cad_to_ros@np.array(mid_budget["pos"])/1000,boxI([.16,.12,.04]),"装车估算",
        "选装原厂线及增量紧固件原留84 g，扣除已单列的选装布线和紧固件",True)
def combined(rr):
    m=sum(r["kg"] for r in rr);c=sum(r["kg"]*r["c"] for r in rr)/m
    I=sum(r["I"]+r["kg"]*(np.dot(r["c"]-c,r["c"]-c)*np.eye(3)-np.outer(r["c"]-c,r["c"]-c)) for r in rr)
    return m,c,I
def six(I):return np.array([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]])
def update():
    form()
    base=[r for r in rows if not r["opt"]]
    root=ET.parse(HERE/"q8_r5_terrain.xml").getroot()
    ur=ET.parse(HERE/"q8_r5.urdf").getroot()
    # Match the terrain-contact proxies on the same kinematic links in both robot files.
    for body_node in root.iter("body"):
        parent=ur.find(f"link[@name='{body_node.get('name')}']")
        if parent is None:continue
        for geom_node in body_node.findall("geom"):
            key=geom_node.get("name","")
            if key=="belly" or geom_node.get("type")!="box":continue
            coll=ET.SubElement(parent,"collision",name=key)
            ET.SubElement(coll,"origin",xyz=geom_node.get("pos","0 0 0"))
            ET.SubElement(ET.SubElement(coll,"geometry"),"box",size=vec(2*np.fromstring(geom_node.get("size"),sep=" ")))
    for name in dict.fromkeys(r["link"] for r in base):
        group=[r for r in base if r["link"]==name]
        m,c,I=combined(group);node=root.find(f".//body[@name='{name}']/inertial")
        node.attrib=dict(mass=str(m),pos=vec(c),fullinertia=vec(six(I)))
        link=ur.find(f"link[@name='{name}']");link.remove(link.find("inertial"))
        for j,r in enumerate(group):
            if j:
                child="item_"+re.sub(r'[^a-zA-Z0-9_]','_',r["name"])
                sub=ET.SubElement(ur,"link",name=child)
                joint=ET.SubElement(ur,"joint",name="mount_"+child,type="fixed")
                ET.SubElement(joint,"parent",link=name);ET.SubElement(joint,"child",link=child)
                ET.SubElement(joint,"origin",xyz=vec(r["c"]))
            else:sub=link
            r["urdf_link"]=sub.get("name")
            node=ET.SubElement(sub,"inertial");ET.SubElement(node,"origin",xyz="0 0 0" if j else vec(r["c"]))
            ET.SubElement(node,"mass",value=str(r["kg"]))
            ET.SubElement(node,"inertia",**dict(zip(("ixx","iyy","izz","ixy","ixz","iyz"),map(str,six(r["I"])))))
    for r,n in [(root,"q8_r5_fitted.xml"),(ur,"q8_r5_fitted.urdf")]:
        ET.indent(r);ET.ElementTree(r).write(HERE/n,encoding="utf8",xml_declaration=True)
    with (HERE/"R5_装车质量明细.csv").open("w",encoding="utf-8-sig",newline="") as f:
        out=csv.writer(f);out.writerow(["部件","实例","刚体","质量g","局部质心x mm","y mm","z mm","依据类型","备注","配置","URDF链接名","项目来源"])
        for r in rows:
            k=r["key"];reference={"Rotor4310":"M01","XT100_Rim":"Wheel","XT100_Tyre":"Wheel","Wire":"Loom","Misc":"Hardware"}.get(k,k)
            src=ledger.get(reference,{}).get("link","")
            if k in ids:src="source/body_step/R5_"+k+".step"
            if k=="Wire":src="data/R5_wiring.json"
            out.writerow([k,r["name"],r["link"],round(r["kg"]*1000,5),*np.round(r["c"]*1000,4),r["grade"],r["note"],"MID选装" if r["opt"] else "首车",r.get("urdf_link",""),src])
    print("base",sum(r["kg"] for r in base),"MID delta",sum(r["kg"] for r in rows if r["opt"]),len(base),flush=True)
if __name__=="__main__":update()
