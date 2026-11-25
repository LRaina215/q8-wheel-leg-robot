from vehicle_sw import *
def run():
    p=OUT/'Q8_Full_Vehicle.SLDASM';m=open_doc(p,2);a=asif(m,api.IAssemblyDoc)
    out={}
    try:
        for name,q in [('Crouch',-36),('Ride',-7),('Liftoff',22)]:
            m.ShowConfiguration2(name);m.ForceRebuild3(False);wheels=[]
            for raw in a.GetComponents(False):
                c=asif(raw,api.IComponent2)
                if c.IsSuppressed() or Path(c.GetPathName()).stem!='XT100_Tyre':continue
                u=np.array(asif(c.Transform2,api.IMathTransform).ArrayData)
                centre=u[9:12]*1000
                wheels.append(centre)
            assert len(wheels)==4
            errors={}
            for n,s,f in corner_order:
                pred=np.array([s*(HX+leg.TYRE_CENTRE),f*(HY+110*math.cos(math.radians(q))),-110-110*math.sin(math.radians(q))])
                errors[n]=min(float(np.linalg.norm(w-pred)) for w in wheels)
            print(name,errors,flush=True);assert max(errors.values())<.05,(name,wheels)
            out[name]=dict(centres_mm=[x.round(4).tolist() for x in wheels],error_mm=errors)
        write(ROOT/'data'/'native_wheel_centres.json',out)
    finally:
        m.ShowConfiguration2('Ride');sw.CloseDoc(m.GetTitle())
if __name__=='__main__':run()
