"""Reflect only FL observations/actions into the FR policy's coordinates."""
import numpy as np

def mirror_actor(actor,obs):
    mask=np.rint(obs[:,22]*3).astype(int)==0
    if not np.any(mask):return actor(obs)
    o=obs.copy()
    left=o[mask].copy()
    # Y, R21, R10, lateral velocity, local roll rate and yaw rate change sign.
    left[:,[1,3,4,6,7,9]]*=-1
    order=[1,0,3,2]
    for start in (10,14,18,24,28):left[:,start:start+4]=left[:,start:start+4][:,order]
    left[:,22]=1./3.
    o[mask]=left
    result=actor(o).copy()
    swapped=result[mask].copy()
    swapped[:,:4]=swapped[:,:4][:,order]
    swapped[:,4:]=swapped[:,4:][:,order]
    result[mask]=swapped
    return result
