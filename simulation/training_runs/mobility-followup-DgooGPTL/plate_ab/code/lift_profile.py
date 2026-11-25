"""Front-wheel preload in servo space. Both replays use this decoder after the ONNX."""
import numpy as np
from night_tasks import commands,smooth

def add_profile(x,base,params):
    k=np.rint(3*x[:,22]).astype(int)
    row=np.arange(len(k))
    front=(k<2)
    t=x[:,23]*4.
    env=smooth((t-.16)/.58)*(1.-smooth((t-2.28)/.65))*front
    lift=smooth((t-.53)/.47)*(1.-smooth((t-2.26)/.50))*front
    ans=base.copy()
    # Keep historical controller unchanged wherever offsets are zero.
    for j in range(4):
        i=k^j
        ans[row,i]=np.clip(ans[row,i]+params[:,j]*(lift if j==0 else env)/29.,-1.,1.)
    for j in range(4):
        i=k^j
        drive=(params[:,4] + (1 if j in (0,2) else -1)*params[:,5])
        ans[row,4+i]=np.clip(ans[row,4+i]+env*drive/.40,(-.6-.22)/.40,1.)
    return ans.astype(np.float32)
