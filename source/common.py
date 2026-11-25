from pathlib import Path
import sys, os, math, json, copy
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
LEG=ROOT/'source'/'corner'
sys.path.insert(0,str(LEG/'source'))
import design as leg
OUT=ROOT/'SolidWorks'
LIB=Path(os.environ.get('Q8_COMPONENT_LIBRARY',r'E:\Wheel Leg Robot\Structure\Component_Library'))
corner_order=[('FL',-1,1),('FR',1,1),('RL',-1,-1),('RR',1,-1)]
HX,HY=119.,112.
def xyzrot(a=0):
    t=math.radians(a);return np.array([[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1.]])
def leg_basis(side):return np.array([[0,0,side],[side,0,0],[0,1,0]],dtype=float)
def pose(group,q,hand=1):
    x,y,a=leg.group_pose(group,q);return hand*x,y,hand*a
def mirrored(part):
    p=copy.deepcopy(part)
    for o in p['ops']:
        for loop in o['loops']:
            if loop[0]=='c':loop[1]*=-1
            else:loop[1]=[(-x,y) for x,y in reversed(loop[1])]
    return p
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,x):Path(path).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')

