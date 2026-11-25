"""Independent 500 Hz native MuJoCo rollout from the same starting case and ONNX actor."""
import mujoco as mj
import numpy as np
from night_model import build,pose,raw_native
from night_tasks import observation,commands,pulse,horizon,score,DEC,DT

from stage_task import pose,decode as commands,score
from stage_signals import Signals

def replay(task,config,c,actor):
    m,d,ix,ti=build(task,config)
    q,mc=pose(task,d.qpos.copy(),c)
    d.qpos[:]=q[0];d.mocap_pos[:]=mc[0]
    mj.mj_forward(m,d)
    H=horizon(task)
    trace=np.empty((H*DEC,1,32))
    floor,one,two=[m.geom(i).id for i in ("ground","step","second_step")]
    surfaces=(floor,one,two)
    wheel={v:i for i,v in enumerate(ix[5])}
    prev=np.zeros((1,8),np.float32)
    force=np.zeros(6);scale=c["scale"][0]
    recorder=Signals(m,H*DEC)
    for k in range(H*DEC):
        if k%DEC==0:
            i=k//DEC
            o=observation(task,raw_native(d,ix,ti),c,i,prev)
            prev=actor(o)
            cmd=commands(task,o,prev)[0]
            ref=np.deg2rad(-7+29*cmd[:4])
            v=.22+.40*cmd[4:]
            d.qfrc_applied[:2]=pulse(task,c,i)[0]
        ang,dh,ws=d.qpos[ix[0]],d.qvel[ix[1]],d.qvel[ix[2]]
        hc=5.2*scale*np.clip((232-np.abs(dh)*9.5492966*24/22.2)/112,0,1)
        wc=scale*np.minimum(1.,3.73*np.clip(1-np.abs(ws)/12.77581,0,1))
        d.ctrl[ix[3]]=np.clip(54*(ref-ang)-.4*dh+1.15*np.cos(ang),-hc,hc)
        d.ctrl[ix[4]]=np.clip(.22*(v/.05-ws),-wc,wc)
        pre_velocity=d.qvel.copy()
        mj.mj_step(m,d)
        a=trace[k,0];a.fill(0)
        for ci,ct in enumerate(d.contact):
            geom,part=int(ct.geom1),int(ct.geom2)
            if part in surfaces:geom,part=part,geom
            if geom not in surfaces:continue
            mj.mj_contactForce(m,d,ci,force)
            j=wheel.get(part)
            index=12
            if j is not None:
                index=j
                if geom!=floor:
                    index=j+8
                    if abs(ct.frame[2])>.85:index=j if task=="double_up" and geom==one else j+4
            a[index]+=max(0.,force[0])
        cz=np.clip(abs(d.geom_xmat[ix[5],8]),0,1)
        a[13:17]=1000*(d.geom_xpos[ix[5],2]-.0175*cz-.05*np.sqrt(1-cz*cz))
        a[17:21]=d.geom_xpos[ix[5],0]
        a[21:29]=[np.rad2deg(np.arccos(np.clip(d.xmat[ti,8],-1,1))),d.subtree_com[ti,2],
                  d.qvel[0],d.qvel[5],max(abs(d.ctrl[ix[3]])),
                  1000*np.linalg.norm(d.site_xpos[ix[6]]-d.site_xpos[ix[7]],axis=1).max(),d.qpos[0],d.qpos[1]]
        a[30:]=d.qvel[1:3]
        recorder.sample(k,m,d,ix,a,wc,pre_velocity,one)
    if any(w.number for w in d.warning):trace[:,0,29]=1
    return {k:v[0].item() for k,v in score(task,trace,c).items()},recorder.results(trace[:,0],c)
