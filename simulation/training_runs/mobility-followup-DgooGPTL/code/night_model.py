"""Physical model and native observation mapping for Q8 overnight motion skills."""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import mujoco as mj
import numpy as np
from pilot import indices,set_pose,LEGS
from night_tasks import DESC,DOUBLE,mocaps

SRC=Path(__file__).resolve().parent

def build(task,config):
    extra,mu,shift,grade=config
    tree=ET.parse(SRC/"q8_r5_fitted.xml")
    tree.find(".//geom[@name='step']").set("size",".8 .46 .24")
    block=ET.SubElement(tree.find("worldbody"),"body",name="second_platform",mocap="true",pos="5 0 -.5")
    ET.SubElement(block,"geom",name="second_step",type="box",size=".8 .46 .24",contype="1",conaffinity="2")
    m=mj.MjModel.from_xml_string(ET.tostring(tree.getroot(),encoding="unicode"))
    ti=m.body("chassis").id
    m.opt.ccd_iterations=256
    theta=math.radians(grade)
    m.opt.gravity[:]=[-9.81*math.sin(theta),0.,-9.81*math.cos(theta)]
    old=m.body_mass[ti]
    m.body_mass[ti]+=extra
    m.body_inertia[ti]*=m.body_mass[ti]/old
    m.body_ipos[ti]+=shift
    m.geom_friction[:,0]=mu
    d=mj.MjData(m)
    mj.mj_setConst(m,d)
    mj.mj_resetData(m,d)
    set_pose(m,d,[-7]*4)
    d.qpos[2]=.16+.11*math.sin(math.radians(-7))
    mj.mj_forward(m,d)
    hip,wh=indices(m,"hip"),indices(m,"wheel")
    ix=np.array([m.jnt_qposadr[hip],m.jnt_dofadr[hip],m.jnt_dofadr[wh],
       [m.actuator(l+"_hip").id for l in LEGS],[m.actuator(l+"_wheel").id for l in LEGS],
       [m.geom(l+"_tyre").id for l in LEGS],[m.site(l+"_pin").id for l in LEGS],
       [m.site(l+"_bore").id for l in LEGS]],np.int32)
    return m,d,ix,ti

def pose(task,q0,c):
    poses=np.repeat(q0[None,:],len(c["key"]),axis=0)
    yaw=np.deg2rad(c["yaw"])/2
    poses[:,3]=np.cos(yaw)
    poses[:,6]=np.sin(yaw)
    if task in DESC:poses[:,2]+=c["h"]*(2 if task in DOUBLE else 1)
    return poses,mocaps(task,c)

def raw_native(d,ix,ti):
    r=d.xmat[ti].reshape(3,3)
    return np.r_[d.qpos[:2],r[2,0],r[2,1],r[1,0],d.qvel[:2],d.qvel[3:6]*.25,
                 (d.qpos[ix[0]]+.12217305)*2.,d.qvel[ix[1]]*.20,d.qvel[ix[2]]*.08,
                 d.geom_xpos[ix[5],0],d.geom_xpos[ix[5],2]][None,:].astype(np.float32)
