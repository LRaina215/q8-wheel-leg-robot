"""Add terrain collision proxies to the flat-ground Q8 without changing its mass."""
import base64
import json
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"source/corner/source"))
import design as leg

def xyz(v):return " ".join(f"{i:.8g}" for i in v)

def box(body,name,low,high):
    ET.SubElement(body,"geom",name=name,type="box",pos=xyz((high+low)/2),size=xyz((high-low)/2),
                  contype="2",conaffinity="1",rgba=".32 .48 .48 .72")

def build():
    root=ET.parse(HERE/"q8_r5.xml").getroot()
    mesh=json.loads(zlib.decompress((HERE.parent/"data/legmesh.bin").read_bytes()))
    trunk=root.find(".//body[@name='chassis']")
    for l,f,s in [("FL",1,-1),("FR",1,1),("RL",-1,-1),("RR",-1,1)]:
        for id,group in [("P01",None),("P02","hip"),("P03","follower"),("P04","carrier"),("P05","carrier"),("M02","carrier")]:
            item=next(i for i in leg.INST if i["id"]==id)
            p=np.frombuffer(base64.b64decode(mesh[id][0]),"<f4").reshape(-1,3).astype(float)
            assert not item["rot"] and not item["flip"]
            p+=np.array([item["x"],item["y"],item["z"]])
            v=p[:,[0,2,1]]*np.array([f,-s,1])/1000
            parent=root.find(f".//body[@name='{l}_{group}']") if group else trunk
            if group is None:v+=np.array([f*.112,-s*.119,0])
            box(parent,l+"_"+id,v.min(0),v.max(0))
    for side in [-1,1]:
        c=np.array([0,side*.115,-.0185]);h=np.array([.083,.003,.0505])
        box(trunk,"rail_"+str(side),c-h,c+h)
    box(trunk,"front_deck",np.array([.082,-.096,.032]),np.array([.148,.096,.036]))
    # One movable terrain box. Its top is level, approach edge x=.38 m.
    platform=ET.SubElement(root.find("worldbody"),"body",name="platform",mocap="true",pos="1.18 0 -.2")
    ET.SubElement(platform,"geom",name="step",type="box",size=".8 .46 .05",
                  contype="1",conaffinity="2",friction=".75 .005 .0001")
    ET.indent(root)
    ET.ElementTree(root).write(HERE/"q8_r5_terrain.xml",encoding="utf-8",xml_declaration=True)
if __name__=="__main__":build()
