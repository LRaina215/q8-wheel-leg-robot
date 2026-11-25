from common import *
db=read(ROOT/'data/R5_wiring.json');w=next(r for r in db['routes'] if r['id']=='W25')
points=np.array(w['points']);length=np.linalg.norm(np.diff(points,axis=0),axis=1)
d=np.r_[0,length.cumsum()];anchor=np.argmin(np.linalg.norm(points-[38.65,53.33,-18.02],axis=1))
weight=np.maximum(0,1-((d-d[anchor])/15)**2)**2
points+=weight[:,None]*np.array([-.36,1.85,.25]);w['points']=points.round(2).tolist();w['fixed_mm']=round(np.linalg.norm(np.diff(points,axis=0),axis=1).sum(),1);w['cut']=int(np.ceil((w['fixed_mm']*1.07+16)/10)*10);write(ROOT/'data/R5_wiring.json',db)

