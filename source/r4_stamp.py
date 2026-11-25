from vehicle_sw import *
from PIL import Image
# The mechanism and six configurations have already been rebuilt. Preserve the fitted-mass ledger
# as a configuration-specific custom property even for vendor parts with envelope geometry.
d=ROOT/'data';mass=read(d/'analysis.json');check=read(d/'solid_check.json')
check={k:v for k,v in check.items() if k in parts and any(t['id']==k for t in items)}
for k in ['YourCee20','BuckTray']:
    p=bodypath(k);m=open_doc(p,1);ss=asif(m,api.IPartDoc).GetBodies2(0,False)
    assert len(ss)==1
    v=asif(ss[0],api.IBody2).GetMassProperties(1)[3]*1e9
    check[k]=round(abs(v-parts[k]['volume_mm3']),5);assert check[k]<.08
    sw.CloseDoc(m.GetTitle())
write(d/'solid_check.json',check)
p=OUT/'Q8_Full_Vehicle.SLDASM';m=open_doc(p,2);ext=asif(m.Extension,api.IModelDocExtension)
stats={}
for name in read(d/'R4原生装配验证.json'):
    value=f"{mass['slice_mid' if 'MID' in name else 'slice']['mass']:.4f}"
    mgr=asif(ext.CustomPropertyManager(name),api.ICustomPropertyManager)
    mgr.Add3('Q8_AsBuiltEstimate_kg',30,value,2)
    values=mgr.Get4('Q8_AsBuiltEstimate_kg',False,'','')
    assert value in str(values),(name,values)
    stats[name]=value
save(m,p);sw.CloseDoc(m.GetTitle());write(d/'总装配置质量.json',stats);print(stats,flush=True)
