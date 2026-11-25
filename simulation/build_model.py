"""Regenerate the portable flat-ground models from the R5 corner geometry."""
from pathlib import Path
import json
import math
import sys
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CORNER = PROJECT / "source" / "corner"
sys.path.insert(0, str(CORNER / "source"))
import design as leg

# Reuse the item mass estimator only. The older dynamics module runs reports on import.
ns = {}
spec = (CORNER / "source" / "engineering.py").read_text(encoding="utf8")
exec(compile(spec.split("counts=Counter")[0], "project_item_masses", "exec"), ns)
add = ET.SubElement
def vec(x):
    return " ".join(f"{v:.9g}" for v in x)

def group_properties(group, fore, side):
    rows = []
    for item in leg.INST:
        if item["g"] != group:
            continue
        key = item["id"]
        if key == "Rotor4310":
            mass, center, extent = .020, [0, 0, -2.5], [35, 35, 5]
        else:
            mass = ns["mass"](item) - (.020 if key == "M01" else 0)
            shape = ns["meta"][key]
            center, extent = shape["center"], shape["bounds"]
        a = math.radians(item["rot"])
        c, s = math.cos(a), math.sin(a)
        orient = np.array([[c,-s,0],[s,c,0],[0,0,1]]) @ np.diag([1,-1,-1] if item["flip"] else [1,1,1])
        axes = np.array([[fore,0,0],[0,0,-side],[0,1,0]])
        v = (axes @ (orient @ center + np.array([item[k] for k in ("x","y","z")]))) / 1000
        if group == "wheel":
            v -= np.array([0,-side*leg.TYRE_CENTRE,-leg.DROP])/1000
        variance = ((np.asarray(extent)/1000)**2)/12
        covariance = axes @ orient @ np.diag(variance) @ orient.T @ axes.T
        inertia = mass * (np.eye(3)*covariance.trace()-covariance)
        rows.append((mass,v,inertia))
    mass = sum(row[0] for row in rows)
    center = sum(m*p for m,p,_ in rows)/mass
    tensor = sum(I+m*((p-center)@(p-center)*np.eye(3)-np.outer(p-center,p-center)) for m,p,I in rows)
    return mass,center,np.diag(tensor)

def inertia(b, props):
    mass, center, diag = props
    add(b,"inertial",mass=str(mass),pos=vec(center),diaginertia=vec(diag))

def build():
    root=ET.Element("mujoco",model="Q8 R5 flat ground")
    add(root,"compiler",angle="radian",inertiafromgeom="false")
    add(root,"option",timestep=".002",integrator="implicitfast",iterations="60",tolerance="1e-9")
    world=add(root,"worldbody")
    add(world,"light",pos="0 0 1.5",dir="0 0 -1")
    add(world,"geom",name="ground",type="plane",contype="1",conaffinity="2",size="0 0 .05",friction=".75 .005 .0001",rgba=".62 .64 .60 1")
    base=add(world,"body",name="chassis",pos="0 0 .16")
    add(base,"freejoint",name="floating_base")
    trunk_i=add(base,"inertial")
    add(base,"geom",name="belly",type="box",contype="2",conaffinity="1",pos="0 0 -.025",size=".083 .118 .024",rgba=".2 .4 .42 1")
    eq=add(root,"equality")
    act=add(root,"actuator")
    moving_mass=0
    moment=np.zeros(3)
    nominal=math.radians(-7)
    for prefix,fore,side in [("FL",1,-1),("FR",1,1),("RL",-1,-1),("RR",-1,1)]:
        hip=np.array([fore*.112,-side*.119,0])
        L, ab, drop, offset = (leg.L/1000,leg.AB/1000,leg.DROP/1000,leg.TYRE_CENTRE/1000)
        end=np.array([fore*L,0,0])
        dy=np.array([0,0,-ab])
        axle=np.array([0,-side*offset,-drop])
        axis=vec([0,fore,0])
        def body(parent,suffix,at,ax,group):
            name=prefix+"_"+suffix
            b=add(parent,"body",name=name,pos=vec(at))
            kw={"range":vec(np.radians([leg.Q0,leg.Q1]))} if suffix=="hip" else {}
            add(b,"joint",name=name,type="hinge",axis=ax,damping=".015" if suffix=="wheel" else ".025",
                armature=".0005" if suffix=="hip" else ".00012",**kw)
            props=group_properties(group,fore,side)
            inertia(b,props)
            return b,props
        drive,p=body(base,"hip",hip,axis,"drive")
        carrier,r=body(drive,"carrier",end,axis,"carrier")
        follower,k=body(base,"follower",hip+dy,axis,"passive")
        wheel,w=body(carrier,"wheel",axle,"0 1 0","wheel")
        for b,p0,p1 in [(drive,np.zeros(3),end),(follower,np.zeros(3),end),(carrier,np.zeros(3),axle)]:
            add(b,"geom",type="capsule",fromto=vec([*p0,*p1]),size=".006",contype="0",conaffinity="0",rgba=".25 .55 .51 1")
        add(wheel,"geom",name=prefix+"_tyre",type="cylinder",contype="2",conaffinity="1",size=".05 .0175",quat=".707106781 -.707106781 0 0",friction=".75 .005 .0001",rgba=".16 .16 .18 1")
        for b,s,point in [(follower,"pin",end),(carrier,"bore",dy)]:
            add(b,"site",name=prefix+"_"+s,pos=vec(point),size=".002")
        add(eq,"connect",name=prefix+"_D",site1=prefix+"_pin",site2=prefix+"_bore",solref=".006 1")
        for role,limit in [("hip",5.2),("wheel",1.)]:
            add(act,"motor",name=prefix+"_"+role,joint=prefix+"_"+role,ctrlrange=vec([-limit,limit]))
        co,si=math.cos(nominal),math.sin(nominal)*fore
        rot=np.array([[co,0,si],[0,1,0],[-si,0,co]])
        C=hip+rot@end
        for prop,origin,rotmat in [(p,hip,rot),(k,hip+dy,rot),(r,C,np.eye(3)),(w,C+axle,np.eye(3))]:
            moving_mass+=prop[0]
            moment+=prop[0]*(origin+rotmat@prop[1])
    # Target load case, legacy nominal CG is a prior. Fixed hip stators are part of the trunk.
    target=6.
    cog_mm=json.loads((PROJECT/"data/analysis.json").read_text(encoding="utf8"))["base"]["cog"]
    cg=np.array([cog_mm[1],-cog_mm[0],cog_mm[2]])/1000
    trunk=target-moving_mass
    dims=np.array([.27,.30,.14])
    trunk_i.attrib.update(mass=str(trunk),pos=vec((target*cg-moment)/trunk),
                          diaginertia=vec(trunk*(np.sum(dims**2)-dims**2)/12))
    ET.indent(root)
    ET.ElementTree(root).write(HERE/"q8_r5.xml",encoding="utf-8",xml_declaration=True)
    return root

def urdf(root):
    """Represent the parallelogram motion for ROS consumers that implement mimic."""
    robot=ET.Element("robot",name="q8_r5")
    def visit(b,parent=None):
        name=b.get("name")
        link=add(robot,"link",name=name)
        i=b.find("inertial")
        node=add(link,"inertial")
        add(node,"origin",xyz=i.get("pos"))
        add(node,"mass",value=i.get("mass"))
        ix,iy,iz=i.get("diaginertia").split()
        add(node,"inertia",ixx=ix,iyy=iy,izz=iz,ixy="0",ixz="0",iyz="0")
        if parent:
            mj=b.find("joint")
            iswheel=name.endswith("_wheel")
            j=add(robot,"joint",name=name,type="continuous" if iswheel else "revolute")
            add(j,"origin",xyz=b.get("pos"));add(j,"parent",link=parent);add(j,"child",link=name)
            add(j,"axis",xyz=mj.get("axis"))
            kw={} if iswheel else dict(lower="-.628318531",upper=".383972435")
            if name.endswith("_carrier"):
                kw=dict(lower="-.383972435",upper=".628318531")
            add(j,"limit",effort="1" if iswheel else "5.2" if name.endswith("_hip") else "0",velocity="12.78" if iswheel else "24.3",**kw)
            if name.endswith(("_carrier","_follower")):
                add(j,"mimic",joint=name[:2]+"_hip",multiplier="-1" if name.endswith("_carrier") else "1")
        for g in b.findall("geom"):
            kind=g.get("type")
            for tag in (["visual"] if kind=="capsule" else ["visual","collision"]):
                node=add(link,tag);geom=ET.Element("geometry")
                if kind=="box":
                    add(node,"origin",xyz=g.get("pos"));add(geom,"box",size=vec(2*np.fromstring(g.get("size"),sep=" ")))
                elif kind=="cylinder":
                    add(node,"origin",xyz="0 0 0",rpy="1.570796327 0 0");add(geom,"cylinder",radius=".05",length=".035")
                else:
                    a,tip=np.fromstring(g.get("fromto"),sep=" ").reshape(2,3);v=tip-a
                    add(node,"origin",xyz=vec((a+tip)/2),rpy=vec([0,math.atan2(np.linalg.norm(v[:2]),v[2]),math.atan2(v[1],v[0])]))
                    add(geom,"cylinder",radius=".006",length=str(np.linalg.norm(v)))
                node.append(geom)
        for child in b.findall("body"):visit(child,name)
    visit(root.find("worldbody/body"))
    ET.indent(robot)
    ET.ElementTree(robot).write(HERE/"q8_r5.urdf",encoding="utf-8",xml_declaration=True)

if __name__=="__main__":
    urdf(build())
