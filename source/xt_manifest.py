from vehicle_sw import *
p=OUT/'Q8_Full_Vehicle.SLDASM'
m=open_doc(p,2);a=asif(m,api.IAssemblyDoc);ext=asif(m.Extension,api.IModelDocExtension)
analysis=read(ROOT/'data'/'analysis.json');files={p};configs=read(ROOT/'data'/'solidworks.json')['configs']
try:
    for name in configs:
        assert m.ShowConfiguration2(name)
        for raw in a.GetComponents(False):
            c=asif(raw,api.IComponent2)
            if c.IsSuppressed():continue
            path=Path(c.GetPathName());assert path.is_file() and path.is_relative_to(OUT);files.add(path)
        mgr=asif(ext.CustomPropertyManager(name),api.ICustomPropertyManager)
        val=analysis['slice_mid' if 'MID' in name else 'slice']['mass']
        for key,value in {'Q8_AsBuiltEstimate_kg':f'{val:.4f}','Q8_MassBasis':'A1 sliced PETG + catalog + installed estimates; see mass ledger','Q8_Wheel':'XTARK 100x35 AF12, 8 mm adapter; catalog four-wheel load 5 kg'}.items():
            mgr.Add3(key,30,value,2)
    m.ShowConfiguration2('Ride');m.ForceRebuild3(False);save(m,p)
finally:sw.CloseDoc(m.GetTitle())
write(ROOT/'data'/'原生依赖清单.json',sorted(x.relative_to(ROOT).as_posix() for x in files))
print(len(files),flush=True)

